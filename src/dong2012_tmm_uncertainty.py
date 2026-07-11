from pathlib import Path

import numpy as np
import pandas as pd

import spectral_pipeline as sp
from dong2012_dielectric_debug import DONG_TABLE2, dong_epsilon_perp, nk_from_epsilon
from dong2012_tmm_coordinate_search import apply_scales
from tmm_air_debug import unpolarized_reflectance


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"

REGION = (1500.0, 4000.0)
THICKNESS_GRID_UM = np.round(np.arange(7.20, 7.701, 0.005), 6)
MAX_POINTS = 1000
RANDOM_SEED = 20260504
BOOTSTRAP_REPLICATES = 120
BLOCK_LENGTH = 40

PROFILE_RELATIVE_THRESHOLDS = [0.01, 0.02, 0.05]


def read_sic_dataset_region(config):
    df = sp.read_dataset(config)
    x = df["wavenumber_cm"].to_numpy(dtype=float)
    y = df["reflectance_pct"].to_numpy(dtype=float) / 100.0
    mask = (x >= REGION[0]) & (x <= REGION[1])
    x = x[mask]
    y = y[mask]
    if len(x) > MAX_POINTS:
        stride = int(np.ceil(len(x) / MAX_POINTS))
        x = x[::stride]
        y = y[::stride]
    return x, y


def load_coordinate_final_state():
    path = OUTPUT_DIR / "dong2012_tmm_coordinate_search_chosen.csv"
    if not path.exists():
        raise FileNotFoundError(
            "Run dong2012_tmm_coordinate_search.py before uncertainty analysis."
        )
    chosen = pd.read_csv(path)
    final = chosen.iloc[-1].to_dict()
    keys = [
        "epi_nu_p_scale",
        "sub_nu_p_scale",
        "epi_gamma_scale",
        "sub_gamma_scale",
        "epi_gamma_l_scale",
        "epi_gamma_t_scale",
        "sub_gamma_l_scale",
        "sub_gamma_t_scale",
    ]
    return {key: float(final[key]) for key in keys}


def affine_fit_fast(model, observed):
    x = np.asarray(model, dtype=float)
    y = np.asarray(observed, dtype=float)
    x_mean = x.mean()
    y_mean = y.mean()
    centered_x = x - x_mean
    denom = float(np.dot(centered_x, centered_x))
    if denom <= 0:
        scale = 0.0
    else:
        scale = float(np.dot(centered_x, y - y_mean) / denom)
    offset = float(y_mean - scale * x_mean)
    fitted = scale * x + offset
    residual = y - fitted
    rmse = float(np.sqrt(np.mean(residual**2)))
    return rmse, scale, offset, fitted, residual


def prepare_angle_data(config, scale_state):
    nu, observed = read_sic_dataset_region(config)
    epi_params = apply_scales("epilayer", scale_state)
    sub_params = apply_scales("substrate", scale_state)
    n_epi = nk_from_epsilon(dong_epsilon_perp(nu, epi_params))
    n_sub = nk_from_epsilon(dong_epsilon_perp(nu, sub_params))
    model_matrix = []
    for thickness_um in THICKNESS_GRID_UM:
        model_matrix.append(
            unpolarized_reflectance(
                nu,
                thickness_um,
                n_epi,
                n_sub,
                config["angle_deg"],
            )
        )
    return {
        "dataset": f'{config["material"]}_{int(config["angle_deg"])}deg',
        "angle_deg": config["angle_deg"],
        "wavenumber_cm": nu,
        "observed": observed,
        "model_matrix": np.asarray(model_matrix),
    }


def profile_objective(angle_data):
    rows = []
    for idx, thickness_um in enumerate(THICKNESS_GRID_UM):
        rmses = []
        for item in angle_data:
            rmse, scale, offset, _, _ = affine_fit_fast(
                item["model_matrix"][idx],
                item["observed"],
            )
            rmses.append(rmse)
            rows.append(
                {
                    "dataset": item["dataset"],
                    "angle_deg": item["angle_deg"],
                    "thickness_um": thickness_um,
                    "rmse": rmse,
                    "affine_scale": scale,
                    "affine_offset": offset,
                }
            )
        rows.append(
            {
                "dataset": "joint",
                "angle_deg": np.nan,
                "thickness_um": thickness_um,
                "rmse": float(np.mean(rmses)),
                "affine_scale": np.nan,
                "affine_offset": np.nan,
            }
        )
    profile = pd.DataFrame(rows)
    joint = profile[profile["dataset"] == "joint"].copy()
    best = joint.sort_values("rmse").iloc[0]
    return profile, float(best["thickness_um"]), float(best["rmse"])


def profile_support_intervals(profile, best_rmse):
    joint = profile[profile["dataset"] == "joint"].copy()
    rows = []
    for rel in PROFILE_RELATIVE_THRESHOLDS:
        threshold = best_rmse * (1.0 + rel)
        selected = joint[joint["rmse"] <= threshold]
        rows.append(
            {
                "relative_rmse_increase": rel,
                "threshold_rmse": threshold,
                "support_min_um": selected["thickness_um"].min(),
                "support_max_um": selected["thickness_um"].max(),
                "support_width_um": selected["thickness_um"].max()
                - selected["thickness_um"].min(),
                "n_grid_points": len(selected),
            }
        )
    return pd.DataFrame(rows)


def moving_block_resample(residual, rng):
    centered = residual - residual.mean()
    n = len(centered)
    starts = rng.integers(0, max(1, n - BLOCK_LENGTH + 1), size=int(np.ceil(n / BLOCK_LENGTH)))
    blocks = [centered[start : start + BLOCK_LENGTH] for start in starts]
    sampled = np.concatenate(blocks)[:n]
    return sampled


def bootstrap_uncertainty(angle_data, best_thickness_um):
    rng = np.random.default_rng(RANDOM_SEED)
    best_idx = int(np.argmin(np.abs(THICKNESS_GRID_UM - best_thickness_um)))
    fitted_parts = []
    residual_parts = []
    for item in angle_data:
        _, _, _, fitted, residual = affine_fit_fast(
            item["model_matrix"][best_idx],
            item["observed"],
        )
        fitted_parts.append(fitted)
        residual_parts.append(residual)

    rows = []
    for replicate in range(BOOTSTRAP_REPLICATES):
        synthetic_by_angle = []
        for fitted, residual in zip(fitted_parts, residual_parts):
            synthetic_by_angle.append(fitted + moving_block_resample(residual, rng))

        grid_rows = []
        for idx, thickness_um in enumerate(THICKNESS_GRID_UM):
            rmses = []
            for item, synthetic in zip(angle_data, synthetic_by_angle):
                rmse, _, _, _, _ = affine_fit_fast(item["model_matrix"][idx], synthetic)
                rmses.append(rmse)
            grid_rows.append((thickness_um, float(np.mean(rmses)), float(np.max(rmses))))

        best = sorted(grid_rows, key=lambda value: (value[1], value[2]))[0]
        rows.append(
            {
                "replicate": replicate,
                "best_thickness_um": best[0],
                "joint_mean_rmse": best[1],
                "joint_max_rmse": best[2],
            }
        )
    return pd.DataFrame(rows)


def summarize_bootstrap(bootstrap):
    values = bootstrap["best_thickness_um"].to_numpy(dtype=float)
    return pd.DataFrame(
        [
            {
                "n_replicates": len(values),
                "mean_um": float(np.mean(values)),
                "std_um": float(np.std(values, ddof=1)),
                "min_um": float(np.min(values)),
                "q025_um": float(np.quantile(values, 0.025)),
                "median_um": float(np.quantile(values, 0.5)),
                "q975_um": float(np.quantile(values, 0.975)),
                "max_um": float(np.max(values)),
            }
        ]
    )


def write_summary(best_thickness, best_rmse, support, bootstrap_summary):
    lines = [
        "# Dong/TMM 精细厚度剖面与不确定性摘要",
        "",
        "本输出用于检查当前 Dong/TMM 候选厚度的局部可识别性和数据扰动不确定性，不是最终置信区间报告。",
        "",
        "## 方法来源",
        "",
        "- 光学模型：Dong2012 介电函数约束下的 Airy/TMM 单层反射模型。",
        "- 厚度剖面：固定材料参数，扫描 $d$ 并记录多角度联合 RMSE，属于 profile objective 思路。",
        "- 数据扰动：在最佳厚度处保留模型拟合曲线，对残差做 moving block bootstrap，再重新搜索 $d$。",
        "- 使用块重采样而不是独立点重采样，是因为相邻波数点的反射率残差通常存在局部相关。",
        "",
        "## 固定口径",
        "",
        f"- 波段：${REGION[0]:.0f}\\text{{--}}{REGION[1]:.0f}\\ cm^{{-1}}$。",
        "- 材料参数：使用分阶段坐标搜索得到的最终缩放状态。",
        f"- 厚度网格：${THICKNESS_GRID_UM.min():.3f}\\text{{--}}{THICKNESS_GRID_UM.max():.3f}\\ \\mu m$，步长 ${THICKNESS_GRID_UM[1]-THICKNESS_GRID_UM[0]:.3f}\\ \\mu m$。",
        f"- Bootstrap 次数：${BOOTSTRAP_REPLICATES}$。",
        f"- 残差块长度：${BLOCK_LENGTH}$ 个采样点。",
        f"- 随机种子：${RANDOM_SEED}$。",
        "",
        "## 厚度剖面最小值",
        "",
        f"- 最小联合 RMSE 对应厚度：$d={best_thickness:.3f}\\ \\mu m$。",
        f"- 最小联合 RMSE：${best_rmse:.6g}$。",
        "",
        "## 近似支持区间",
        "",
        "这里的支持区间不是统计置信区间，只表示联合 RMSE 不超过最小值若干比例时的厚度范围。",
        "",
        sp.markdown_table(support),
        "",
        "## 残差块 Bootstrap 厚度分布",
        "",
        sp.markdown_table(bootstrap_summary),
        "",
        "## 解释",
        "",
        "- 如果 profile support 很窄，说明目标函数在 $d$ 方向比较尖，厚度较容易识别。",
        "- 如果 bootstrap 分布很窄，说明在当前残差扰动口径下，数据噪声不会明显推翻厚度低谷。",
        "- 如果二者都集中在 $7.4\\text{--}7.6\\ \\mu m$ 内，可以增强当前候选区间的可信度。",
        "- 该结果仍依赖固定材料参数、线性反射率标定和残差重采样假设，不能替代独立材料参数测量。",
    ]
    (OUTPUT_DIR / "dong2012_tmm_uncertainty_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scale_state = load_coordinate_final_state()
    configs = [item for item in sp.DATASETS if item["material"] == "SiC"]
    angle_data = [prepare_angle_data(config, scale_state) for config in configs]
    profile, best_thickness, best_rmse = profile_objective(angle_data)
    support = profile_support_intervals(profile, best_rmse)
    bootstrap = bootstrap_uncertainty(angle_data, best_thickness)
    bootstrap_summary = summarize_bootstrap(bootstrap)

    profile.to_csv(OUTPUT_DIR / "dong2012_tmm_uncertainty_profile.csv", index=False, encoding="utf-8-sig")
    support.to_csv(OUTPUT_DIR / "dong2012_tmm_uncertainty_support.csv", index=False, encoding="utf-8-sig")
    bootstrap.to_csv(OUTPUT_DIR / "dong2012_tmm_uncertainty_bootstrap.csv", index=False, encoding="utf-8-sig")
    bootstrap_summary.to_csv(
        OUTPUT_DIR / "dong2012_tmm_uncertainty_bootstrap_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    write_summary(best_thickness, best_rmse, support, bootstrap_summary)
    print(OUTPUT_DIR / "dong2012_tmm_uncertainty_summary.md")


if __name__ == "__main__":
    main()
