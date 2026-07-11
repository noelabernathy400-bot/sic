from pathlib import Path

import numpy as np
import pandas as pd

import spectral_pipeline as sp
from dong2012_dielectric_debug import (
    DONG_TABLE2,
    REGION,
    THICKNESS_GRID_UM,
    dong_epsilon_perp,
    nk_from_epsilon,
    read_sic_dataset,
)
from tmm_air_debug import affine_fit_error, unpolarized_reflectance


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"

GAMMA_SCALES = [0.5, 1.0, 1.5, 2.0]


def scaled_params(role, gamma_scale):
    params = dict(DONG_TABLE2[role])
    params["gamma"] = params["gamma"] * gamma_scale
    return params


def angle_error_curve(config, epi_gamma_scale, sub_gamma_scale):
    nu, observed = read_sic_dataset(config)
    epi_params = scaled_params("epilayer", epi_gamma_scale)
    sub_params = scaled_params("substrate", sub_gamma_scale)
    n_epi = nk_from_epsilon(dong_epsilon_perp(nu, epi_params))
    n_sub = nk_from_epsilon(dong_epsilon_perp(nu, sub_params))
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
                "angle_deg": config["angle_deg"],
                "thickness_um": thickness_um,
                "rmse": rmse,
                "affine_scale": scale,
                "affine_offset": offset,
            }
        )
    return pd.DataFrame(rows)


def run_sensitivity():
    rows = []
    angle_rows = []
    configs = [item for item in sp.DATASETS if item["material"] == "SiC"]
    for epi_gamma_scale in GAMMA_SCALES:
        for sub_gamma_scale in GAMMA_SCALES:
            curves = []
            for config in configs:
                curve = angle_error_curve(config, epi_gamma_scale, sub_gamma_scale)
                curve["epi_gamma_scale"] = epi_gamma_scale
                curve["sub_gamma_scale"] = sub_gamma_scale
                curve["dataset"] = f'{config["material"]}_{int(config["angle_deg"])}deg'
                curves.append(curve)
                best_angle = curve.sort_values("rmse").iloc[0]
                angle_rows.append(
                    {
                        "epi_gamma_scale": epi_gamma_scale,
                        "sub_gamma_scale": sub_gamma_scale,
                        "dataset": f'{config["material"]}_{int(config["angle_deg"])}deg',
                        "angle_deg": config["angle_deg"],
                        "best_thickness_um": best_angle["thickness_um"],
                        "best_rmse": best_angle["rmse"],
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
            rows.append(
                {
                    "epi_gamma_scale": epi_gamma_scale,
                    "sub_gamma_scale": sub_gamma_scale,
                    "joint_best_thickness_um": joint["thickness_um"],
                    "joint_mean_rmse": joint["mean"],
                    "joint_max_rmse": joint["max"],
                    "joint_std_rmse": joint["std"],
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(angle_rows)


def write_summary(joint, angle):
    best_rows = joint.sort_values(["joint_mean_rmse", "joint_max_rmse"]).head(12)
    stable = (
        joint.groupby("joint_best_thickness_um")
        .size()
        .reset_index(name="count")
        .sort_values(["count", "joint_best_thickness_um"], ascending=[False, True])
    )
    lines = [
        "# Dong/TMM $\\gamma$ 参数敏感性摘要",
        "",
        "本输出用于检查 Dong2012 介电函数中的等离子体阻尼 $\\gamma$ 改变时，Airy/TMM 厚度低谷是否稳定，不是最终厚度结果。",
        "",
        "## 敏感性设计",
        "",
        "- 固定 Dong2012 声子参数和等离子体频率 $\\nu_{p,\\perp}$。",
        "- 分别缩放外延层和衬底的 $\\gamma$。",
        f"- 缩放系数：{GAMMA_SCALES}。",
        f"- 厚度搜索区间：${THICKNESS_GRID_UM.min():.1f}\\text{{--}}{THICKNESS_GRID_UM.max():.1f}\\ \\mu m$。",
        f"- 波段：${REGION[0]:.0f}\\text{{--}}{REGION[1]:.0f}\\ cm^{{-1}}$。",
        "- 每个角度允许独立线性标定 $R_{\\mathrm{obs}}\\approx aR_{\\mathrm{model}}+b$。",
        "- 联合误差取 10 度和 15 度 RMSE 的均值。",
        "",
        "## 联合误差最小的参数组合",
        "",
        sp.markdown_table(best_rows),
        "",
        "## 厚度低谷出现频次",
        "",
        sp.markdown_table(stable),
        "",
        "## 解释",
        "",
        "- $\\gamma$ 控制 Drude 阻尼，主要影响吸收和谱线形状。",
        "- 如果 $\\gamma$ 缩放后厚度低谷仍稳定，说明当前厚度信号不只是某个阻尼参数偶然造成。",
        "- 该结果仍不能替代最终联合拟合，因为本题样品的真实 $\\gamma$ 未知。",
    ]
    (OUTPUT_DIR / "dong2012_tmm_gamma_sensitivity_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joint, angle = run_sensitivity()
    joint.to_csv(OUTPUT_DIR / "dong2012_tmm_gamma_sensitivity_joint.csv", index=False, encoding="utf-8-sig")
    angle.to_csv(OUTPUT_DIR / "dong2012_tmm_gamma_sensitivity_by_angle.csv", index=False, encoding="utf-8-sig")
    write_summary(joint, angle)
    print(OUTPUT_DIR / "dong2012_tmm_gamma_sensitivity_summary.md")


if __name__ == "__main__":
    main()
