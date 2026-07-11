from pathlib import Path

import numpy as np
import pandas as pd

import spectral_pipeline as sp
from dong2012_dielectric_debug import DONG_TABLE2, dong_epsilon_perp, nk_from_epsilon
from tmm_air_debug import affine_fit_error, unpolarized_reflectance


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"

REGION = (1500.0, 4000.0)
THICKNESS_GRID_UM = np.linspace(7.0, 7.8, 81)
SCALES = [0.5, 1.0, 1.5, 2.0]
MAX_POINTS = 1000


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


def apply_scales(role, scale_state):
    params = dict(DONG_TABLE2[role])
    prefix = "epi" if role == "epilayer" else "sub"
    params["nu_p_perp"] *= scale_state[f"{prefix}_nu_p_scale"]
    params["gamma"] *= scale_state[f"{prefix}_gamma_scale"]
    params["gamma_L"] *= scale_state[f"{prefix}_gamma_l_scale"]
    params["gamma_T"] *= scale_state[f"{prefix}_gamma_t_scale"]
    return params


def evaluate_state(scale_state, configs):
    curve_rows = []
    angle_best_rows = []
    for config in configs:
        nu, observed = read_sic_dataset_region(config)
        epi_params = apply_scales("epilayer", scale_state)
        sub_params = apply_scales("substrate", scale_state)
        n_epi = nk_from_epsilon(dong_epsilon_perp(nu, epi_params))
        n_sub = nk_from_epsilon(dong_epsilon_perp(nu, sub_params))
        dataset = f'{config["material"]}_{int(config["angle_deg"])}deg'
        for thickness_um in THICKNESS_GRID_UM:
            predicted = unpolarized_reflectance(
                nu,
                thickness_um,
                n_epi,
                n_sub,
                config["angle_deg"],
            )
            rmse, affine_scale, affine_offset = affine_fit_error(predicted, observed)
            curve_rows.append(
                {
                    "dataset": dataset,
                    "angle_deg": config["angle_deg"],
                    "thickness_um": thickness_um,
                    "rmse": rmse,
                    "affine_scale": affine_scale,
                    "affine_offset": affine_offset,
                }
            )
    curves = pd.DataFrame(curve_rows)
    joint = (
        curves.groupby("thickness_um")["rmse"]
        .agg(["mean", "max", "std"])
        .reset_index()
        .sort_values(["mean", "max"])
        .iloc[0]
    )
    for dataset, group in curves.groupby("dataset"):
        best = group.sort_values("rmse").iloc[0]
        angle_best_rows.append(
            {
                "dataset": dataset,
                "angle_deg": best["angle_deg"],
                "best_thickness_um": best["thickness_um"],
                "best_rmse": best["rmse"],
            }
        )
    return {
        "joint_best_thickness_um": float(joint["thickness_um"]),
        "joint_mean_rmse": float(joint["mean"]),
        "joint_max_rmse": float(joint["max"]),
        "joint_std_rmse": float(joint["std"]),
        "angle_best": angle_best_rows,
    }


def candidate_states(base_state, stage):
    candidates = []
    if stage == "plasma":
        for epi_scale in SCALES:
            for sub_scale in SCALES:
                state = dict(base_state)
                state["epi_nu_p_scale"] = epi_scale
                state["sub_nu_p_scale"] = sub_scale
                candidates.append(state)
    elif stage == "drude_gamma":
        for epi_scale in SCALES:
            for sub_scale in SCALES:
                state = dict(base_state)
                state["epi_gamma_scale"] = epi_scale
                state["sub_gamma_scale"] = sub_scale
                candidates.append(state)
    elif stage == "phonon_layer":
        for epi_scale in SCALES:
            for sub_scale in SCALES:
                state = dict(base_state)
                state["epi_gamma_l_scale"] = epi_scale
                state["epi_gamma_t_scale"] = epi_scale
                state["sub_gamma_l_scale"] = sub_scale
                state["sub_gamma_t_scale"] = sub_scale
                candidates.append(state)
    else:
        raise ValueError(f"Unknown stage: {stage}")
    return candidates


def run_coordinate_search():
    configs = [item for item in sp.DATASETS if item["material"] == "SiC"]
    current_state = {
        "epi_nu_p_scale": 1.0,
        "sub_nu_p_scale": 1.0,
        "epi_gamma_scale": 1.0,
        "sub_gamma_scale": 1.0,
        "epi_gamma_l_scale": 1.0,
        "epi_gamma_t_scale": 1.0,
        "sub_gamma_l_scale": 1.0,
        "sub_gamma_t_scale": 1.0,
    }
    stages = [
        ("baseline", [current_state]),
        ("plasma", None),
        ("drude_gamma", None),
        ("phonon_layer", None),
    ]
    all_rows = []
    angle_rows = []
    chosen_rows = []
    for stage, predefined in stages:
        states = predefined if predefined is not None else candidate_states(current_state, stage)
        stage_rows = []
        for idx, state in enumerate(states):
            result = evaluate_state(state, configs)
            row = {
                "stage": stage,
                "candidate_id": idx,
                **state,
                "joint_best_thickness_um": result["joint_best_thickness_um"],
                "joint_mean_rmse": result["joint_mean_rmse"],
                "joint_max_rmse": result["joint_max_rmse"],
                "joint_std_rmse": result["joint_std_rmse"],
            }
            all_rows.append(row)
            stage_rows.append(row)
            for angle_row in result["angle_best"]:
                angle_rows.append({"stage": stage, "candidate_id": idx, **state, **angle_row})
        chosen = sorted(stage_rows, key=lambda item: (item["joint_mean_rmse"], item["joint_max_rmse"]))[0]
        current_state = {key: chosen[key] for key in current_state}
        chosen_rows.append({"stage": stage, **chosen})
    return pd.DataFrame(all_rows), pd.DataFrame(chosen_rows), pd.DataFrame(angle_rows)


def write_summary(all_candidates, chosen, angle):
    final = chosen.iloc[-1]
    improvement = pd.DataFrame(
        [
            {
                "baseline_joint_mean_rmse": chosen.iloc[0]["joint_mean_rmse"],
                "final_joint_mean_rmse": final["joint_mean_rmse"],
                "absolute_improvement": chosen.iloc[0]["joint_mean_rmse"] - final["joint_mean_rmse"],
                "relative_improvement_pct": 100.0
                * (chosen.iloc[0]["joint_mean_rmse"] - final["joint_mean_rmse"])
                / chosen.iloc[0]["joint_mean_rmse"],
            }
        ]
    )
    lines = [
        "# Dong/TMM 分阶段坐标搜索摘要",
        "",
        "本输出用于探索 Dong/TMM 材料参数联合变化时厚度低谷是否仍稳定。它不是最终全局优化结果，而是可解释的分阶段坐标搜索。",
        "",
        "## 搜索设计",
        "",
        f"- 波段固定为 ${REGION[0]:.0f}\\text{{--}}{REGION[1]:.0f}\\ cm^{{-1}}$，这是前面波段敏感性中误差较低且稳定的高波数区。",
        f"- 厚度搜索区间为 ${THICKNESS_GRID_UM.min():.1f}\\text{{--}}{THICKNESS_GRID_UM.max():.1f}\\ \\mu m$，步长约 ${THICKNESS_GRID_UM[1]-THICKNESS_GRID_UM[0]:.2f}\\ \\mu m$。",
        "- 第一阶段固定全部参数，得到 baseline。",
        "- 第二阶段只搜索外延层/衬底的 $\\nu_p$ 缩放。",
        "- 第三阶段在第二阶段最优基础上搜索外延层/衬底的 $\\gamma$ 缩放。",
        "- 第四阶段在第三阶段最优基础上搜索外延层/衬底的 $\\Gamma_L,\\Gamma_T$ 同比例缩放。",
        "- 每个角度允许独立线性标定 $R_{\\mathrm{obs}}\\approx aR_{\\mathrm{model}}+b$。",
        "- 该方法是顺序坐标搜索，结果依赖阶段顺序，不能当作全局最优。",
        "",
        "## 每阶段被选中的参数",
        "",
        sp.markdown_table(chosen),
        "",
        "## 误差改善",
        "",
        sp.markdown_table(improvement),
        "",
        "## 最终阶段单角度低谷",
        "",
        sp.markdown_table(
            angle[
                (angle["stage"] == final["stage"])
                & (angle["candidate_id"] == final["candidate_id"])
            ]
        ),
        "",
        "## 解释",
        "",
        "- 如果分阶段搜索后 $d$ 仍停留在 $7.4\\text{--}7.6\\ \\mu m$ 附近，说明联合参数调整没有轻易推翻当前候选区间。",
        "- 如果误差改善很小，说明当前 baseline 已经较难通过这些粗网格缩放显著改进。",
        "- 如果某一阶段改变参数后 $d$ 明显漂移，论文中必须把该参数列为主要不确定性来源。",
        "- 本轮只使用粗缩放网格，下一步若要收敛到可报告参数，需要更细网格或连续优化。",
    ]
    (OUTPUT_DIR / "dong2012_tmm_coordinate_search_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_candidates, chosen, angle = run_coordinate_search()
    all_candidates.to_csv(OUTPUT_DIR / "dong2012_tmm_coordinate_search_candidates.csv", index=False, encoding="utf-8-sig")
    chosen.to_csv(OUTPUT_DIR / "dong2012_tmm_coordinate_search_chosen.csv", index=False, encoding="utf-8-sig")
    angle.to_csv(OUTPUT_DIR / "dong2012_tmm_coordinate_search_by_angle.csv", index=False, encoding="utf-8-sig")
    write_summary(all_candidates, chosen, angle)
    print(OUTPUT_DIR / "dong2012_tmm_coordinate_search_summary.md")


if __name__ == "__main__":
    main()
