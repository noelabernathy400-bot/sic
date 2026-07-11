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

PLASMA_SCALES = [0.0, 0.5, 1.0, 1.5, 2.0]


def scaled_params(role, plasma_scale):
    params = dict(DONG_TABLE2[role])
    params["nu_p_perp"] = params["nu_p_perp"] * plasma_scale
    return params


def angle_error_curve(config, epi_scale, sub_scale):
    nu, observed = read_sic_dataset(config)
    epi_params = scaled_params("epilayer", epi_scale)
    sub_params = scaled_params("substrate", sub_scale)
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
    for epi_scale in PLASMA_SCALES:
        for sub_scale in PLASMA_SCALES:
            curves = []
            for config in configs:
                curve = angle_error_curve(config, epi_scale, sub_scale)
                curve["epi_plasma_scale"] = epi_scale
                curve["sub_plasma_scale"] = sub_scale
                curve["dataset"] = f'{config["material"]}_{int(config["angle_deg"])}deg'
                curves.append(curve)
                best_angle = curve.sort_values("rmse").iloc[0]
                angle_rows.append(
                    {
                        "epi_plasma_scale": epi_scale,
                        "sub_plasma_scale": sub_scale,
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
                    "epi_plasma_scale": epi_scale,
                    "sub_plasma_scale": sub_scale,
                    "joint_best_thickness_um": joint["thickness_um"],
                    "joint_mean_rmse": joint["mean"],
                    "joint_max_rmse": joint["max"],
                    "joint_std_rmse": joint["std"],
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(angle_rows)


def write_summary(joint, angle):
    valid = joint[joint["epi_plasma_scale"] != joint["sub_plasma_scale"]].copy()
    best_rows = valid.sort_values(["joint_mean_rmse", "joint_max_rmse"]).head(12)
    stable = (
        valid.groupby("joint_best_thickness_um")
        .size()
        .reset_index(name="count")
        .sort_values(["count", "joint_best_thickness_um"], ascending=[False, True])
    )
    lines = [
        "# Dong/TMM 参数敏感性摘要",
        "",
        "本输出用于检查 Dong2012 介电函数参数变化时，Airy/TMM 厚度低谷是否稳定，不是最终厚度结果。",
        "",
        "## 敏感性设计",
        "",
        "- 固定 Dong2012 声子参数。",
        "- 分别缩放外延层和衬底的 $\\nu_{p,\\perp}$。",
        f"- 缩放系数：{PLASMA_SCALES}。",
        f"- 厚度搜索区间：${THICKNESS_GRID_UM.min():.1f}\\text{{--}}{THICKNESS_GRID_UM.max():.1f}\\ \\mu m$。",
        f"- 波段：${REGION[0]:.0f}\\text{{--}}{REGION[1]:.0f}\\ cm^{{-1}}$。",
        "- 每个角度允许独立线性标定 $R_{\\mathrm{obs}}\\approx aR_{\\mathrm{model}}+b$。",
        "- 联合误差取 10 度和 15 度 RMSE 的均值，并用最大 RMSE 检查最差角度。",
        "",
        "## 联合误差最小的参数组合",
        "",
        sp.markdown_table(best_rows),
        "",
        "## 厚度低谷出现频次",
        "",
        sp.markdown_table(stable.head(20)),
        "",
        "## 解释",
        "",
        "- 如果许多参数组合都把低谷推到相近厚度，说明厚度主要由条纹相位决定，具有一定稳健性。",
        "- 如果低谷随参数缩放大幅漂移，说明当前全谱模型仍缺少材料约束，厚度不能直接定论。",
        "- `epi_plasma_scale = sub_plasma_scale` 时外延层和衬底 Drude 差异减弱，不适合作为主要可识别条件。",
        "- 下一步应把结果和 FOD、色散 FOD、人工 TMM 低谷放在同一张对比表中，形成论文中的模型路线比较。",
    ]
    (OUTPUT_DIR / "dong2012_tmm_sensitivity_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joint, angle = run_sensitivity()
    joint.to_csv(OUTPUT_DIR / "dong2012_tmm_sensitivity_joint.csv", index=False, encoding="utf-8-sig")
    angle.to_csv(OUTPUT_DIR / "dong2012_tmm_sensitivity_by_angle.csv", index=False, encoding="utf-8-sig")
    write_summary(joint, angle)
    print(OUTPUT_DIR / "dong2012_tmm_sensitivity_summary.md")


if __name__ == "__main__":
    main()
