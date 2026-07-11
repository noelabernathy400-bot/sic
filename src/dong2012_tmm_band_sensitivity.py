from pathlib import Path

import numpy as np
import pandas as pd

import spectral_pipeline as sp
from dong2012_dielectric_debug import (
    DONG_TABLE2,
    THICKNESS_GRID_UM,
    dong_epsilon_perp,
    nk_from_epsilon,
)
from tmm_air_debug import affine_fit_error, unpolarized_reflectance


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"

BANDS = [
    {"band_name": "full_measured", "lower_cm": 400.0, "upper_cm": 4000.0},
    {"band_name": "include_reststrahlen_tail", "lower_cm": 800.0, "upper_cm": 4000.0},
    {"band_name": "classic_high", "lower_cm": 1000.0, "upper_cm": 4000.0},
    {"band_name": "moderate_high", "lower_cm": 1200.0, "upper_cm": 4000.0},
    {"band_name": "current_baseline", "lower_cm": 1500.0, "upper_cm": 4000.0},
    {"band_name": "higher_only", "lower_cm": 1800.0, "upper_cm": 4000.0},
    {"band_name": "high_core", "lower_cm": 2000.0, "upper_cm": 4000.0},
    {"band_name": "trim_both_sides", "lower_cm": 1500.0, "upper_cm": 3500.0},
]

RESTSTRAHLEN_APPROX = (797.3, 970.1)
MAX_POINTS_PER_BAND = 1200


def includes_reststrahlen(lower_cm, upper_cm):
    return lower_cm <= RESTSTRAHLEN_APPROX[1] and upper_cm >= RESTSTRAHLEN_APPROX[0]


def read_sic_dataset_region(config, lower_cm, upper_cm):
    df = sp.read_dataset(config)
    x = df["wavenumber_cm"].to_numpy(dtype=float)
    y = df["reflectance_pct"].to_numpy(dtype=float) / 100.0
    mask = (x >= lower_cm) & (x <= upper_cm)
    x = x[mask]
    y = y[mask]
    if len(x) > MAX_POINTS_PER_BAND:
        stride = int(np.ceil(len(x) / MAX_POINTS_PER_BAND))
        x = x[::stride]
        y = y[::stride]
    return x, y


def angle_error_curve(config, band):
    nu, observed = read_sic_dataset_region(config, band["lower_cm"], band["upper_cm"])
    n_epi = nk_from_epsilon(dong_epsilon_perp(nu, DONG_TABLE2["epilayer"]))
    n_sub = nk_from_epsilon(dong_epsilon_perp(nu, DONG_TABLE2["substrate"]))
    rows = []
    for thickness_um in THICKNESS_GRID_UM:
        predicted = unpolarized_reflectance(
            nu,
            thickness_um,
            n_epi,
            n_sub,
            config["angle_deg"],
        )
        rmse, scale, offset = affine_fit_error(predicted, observed)
        rows.append(
            {
                "band_name": band["band_name"],
                "lower_cm": band["lower_cm"],
                "upper_cm": band["upper_cm"],
                "n_points": len(nu),
                "includes_reststrahlen": includes_reststrahlen(band["lower_cm"], band["upper_cm"]),
                "angle_deg": config["angle_deg"],
                "thickness_um": thickness_um,
                "rmse": rmse,
                "affine_scale": scale,
                "affine_offset": offset,
            }
        )
    return pd.DataFrame(rows)


def run_sensitivity():
    joint_rows = []
    angle_rows = []
    curve_rows = []
    configs = [item for item in sp.DATASETS if item["material"] == "SiC"]
    for band in BANDS:
        curves = []
        for config in configs:
            curve = angle_error_curve(config, band)
            dataset = f'{config["material"]}_{int(config["angle_deg"])}deg'
            curve["dataset"] = dataset
            curves.append(curve)
            curve_rows.append(curve)
            best_angle = curve.sort_values("rmse").iloc[0]
            angle_rows.append(
                {
                    "band_name": band["band_name"],
                    "lower_cm": band["lower_cm"],
                    "upper_cm": band["upper_cm"],
                    "includes_reststrahlen": includes_reststrahlen(band["lower_cm"], band["upper_cm"]),
                    "dataset": dataset,
                    "angle_deg": config["angle_deg"],
                    "n_points": best_angle["n_points"],
                    "best_thickness_um": best_angle["thickness_um"],
                    "best_rmse": best_angle["rmse"],
                    "affine_scale": best_angle["affine_scale"],
                    "affine_offset": best_angle["affine_offset"],
                }
            )
        merged = pd.concat(curves, ignore_index=True)
        joint = (
            merged.groupby("thickness_um")["rmse"]
            .agg(["mean", "max", "std"])
            .reset_index()
            .sort_values(["mean", "max"])
            .iloc[0]
        )
        joint_rows.append(
            {
                "band_name": band["band_name"],
                "lower_cm": band["lower_cm"],
                "upper_cm": band["upper_cm"],
                "includes_reststrahlen": includes_reststrahlen(band["lower_cm"], band["upper_cm"]),
                "joint_best_thickness_um": joint["thickness_um"],
                "joint_mean_rmse": joint["mean"],
                "joint_max_rmse": joint["max"],
                "joint_std_rmse": joint["std"],
            }
        )
    return pd.DataFrame(joint_rows), pd.DataFrame(angle_rows), pd.concat(curve_rows, ignore_index=True)


def write_summary(joint, angle):
    stable = (
        joint.groupby("joint_best_thickness_um")
        .size()
        .reset_index(name="count")
        .sort_values(["count", "joint_best_thickness_um"], ascending=[False, True])
    )
    band_span = pd.DataFrame(
        [
            {
                "all_band_min_um": joint["joint_best_thickness_um"].min(),
                "all_band_max_um": joint["joint_best_thickness_um"].max(),
                "all_band_mean_um": joint["joint_best_thickness_um"].mean(),
                "all_band_std_um": joint["joint_best_thickness_um"].std(ddof=1),
            }
        ]
    )
    no_rest = joint[~joint["includes_reststrahlen"]]
    no_rest_span = pd.DataFrame(
        [
            {
                "no_reststrahlen_min_um": no_rest["joint_best_thickness_um"].min(),
                "no_reststrahlen_max_um": no_rest["joint_best_thickness_um"].max(),
                "no_reststrahlen_mean_um": no_rest["joint_best_thickness_um"].mean(),
                "no_reststrahlen_std_um": no_rest["joint_best_thickness_um"].std(ddof=1),
            }
        ]
    )
    lines = [
        "# Dong/TMM 波段敏感性摘要",
        "",
        "本输出用于检查参与拟合的波数区间改变时，Dong2012 介电函数 Airy/TMM 厚度低谷是否稳定，不是最终厚度结果。",
        "",
        "## 敏感性设计",
        "",
        "- 固定 Dong2012 表 2 的外延层和衬底参数。",
        "- 不改变 $\\nu_p$、$\\gamma$、$\\Gamma_L$、$\\Gamma_T$，只改变波段。",
        "- 每个角度允许独立线性标定 $R_{\\mathrm{obs}}\\approx aR_{\\mathrm{model}}+b$。",
        "- 联合误差取 $10^\\circ$ 和 $15^\\circ$ RMSE 的均值，并用最大 RMSE 检查最差角度。",
        "- `includes_reststrahlen` 表示该波段是否覆盖 Dong2012 中约 $797.3\\text{--}970.1\\ cm^{-1}$ 的强晶格振动区。",
        "",
        "## 各波段联合低谷",
        "",
        sp.markdown_table(joint),
        "",
        "## 全部波段低谷范围",
        "",
        sp.markdown_table(band_span),
        "",
        "## 不含 Reststrahlen 区的波段低谷范围",
        "",
        sp.markdown_table(no_rest_span),
        "",
        "## 厚度低谷出现频次",
        "",
        sp.markdown_table(stable),
        "",
        "## 各角度单独低谷",
        "",
        sp.markdown_table(angle),
        "",
        "## 解释",
        "",
        "- 如果不同波段的联合低谷仍集中在同一区间，说明当前厚度识别对数据截取不太敏感。",
        "- 如果包含 Reststrahlen 区的波段明显偏离，而高波数波段稳定，论文中应说明低波数强吸收区可能不适合作为主要拟合证据。",
        "- 如果 $10^\\circ$ 与 $15^\\circ$ 的单角度低谷分歧较大，应优先相信多角度联合误差，而不是单角度最小值。",
        "- 本轮只检查波段选择，不替代材料参数联合优化。",
    ]
    (OUTPUT_DIR / "dong2012_tmm_band_sensitivity_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joint, angle, curves = run_sensitivity()
    joint.to_csv(OUTPUT_DIR / "dong2012_tmm_band_sensitivity_joint.csv", index=False, encoding="utf-8-sig")
    angle.to_csv(OUTPUT_DIR / "dong2012_tmm_band_sensitivity_by_angle.csv", index=False, encoding="utf-8-sig")
    curves.to_csv(OUTPUT_DIR / "dong2012_tmm_band_sensitivity_curves.csv", index=False, encoding="utf-8-sig")
    write_summary(joint, angle)
    print(OUTPUT_DIR / "dong2012_tmm_band_sensitivity_summary.md")


if __name__ == "__main__":
    main()
