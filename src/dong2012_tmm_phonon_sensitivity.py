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

PHONON_SCALES = [0.5, 1.0, 1.5, 2.0]


def scaled_params(role, gamma_l_scale=1.0, gamma_t_scale=1.0):
    params = dict(DONG_TABLE2[role])
    params["gamma_L"] = params["gamma_L"] * gamma_l_scale
    params["gamma_T"] = params["gamma_T"] * gamma_t_scale
    return params


def angle_error_curve(config, epi_gamma_l_scale, epi_gamma_t_scale, sub_gamma_l_scale, sub_gamma_t_scale):
    nu, observed = read_sic_dataset(config)
    epi_params = scaled_params("epilayer", epi_gamma_l_scale, epi_gamma_t_scale)
    sub_params = scaled_params("substrate", sub_gamma_l_scale, sub_gamma_t_scale)
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


def parameter_grid():
    rows = []

    for epi_scale in PHONON_SCALES:
        for sub_scale in PHONON_SCALES:
            rows.append(
                {
                    "mode": "layer_shared_scale",
                    "epi_gamma_l_scale": epi_scale,
                    "epi_gamma_t_scale": epi_scale,
                    "sub_gamma_l_scale": sub_scale,
                    "sub_gamma_t_scale": sub_scale,
                    "design_note": "外延层与衬底分别缩放，且每层内 $\\Gamma_L$ 与 $\\Gamma_T$ 同比例缩放。",
                }
            )

    for gamma_l_scale in PHONON_SCALES:
        for gamma_t_scale in PHONON_SCALES:
            rows.append(
                {
                    "mode": "lt_shared_scale",
                    "epi_gamma_l_scale": gamma_l_scale,
                    "epi_gamma_t_scale": gamma_t_scale,
                    "sub_gamma_l_scale": gamma_l_scale,
                    "sub_gamma_t_scale": gamma_t_scale,
                    "design_note": "全局缩放 $\\Gamma_L$ 与 $\\Gamma_T$，检查 LO/TO 阻尼结构对厚度低谷的影响。",
                }
            )

    return pd.DataFrame(rows)


def summarize_joint(curves):
    merged = pd.concat(curves, ignore_index=True)
    return (
        merged.groupby("thickness_um")["rmse"]
        .agg(["mean", "max", "std"])
        .reset_index()
        .sort_values(["mean", "max"])
        .iloc[0]
    )


def run_sensitivity():
    joint_rows = []
    angle_rows = []
    configs = [item for item in sp.DATASETS if item["material"] == "SiC"]
    for _, design in parameter_grid().iterrows():
        curves = []
        for config in configs:
            curve = angle_error_curve(
                config,
                design["epi_gamma_l_scale"],
                design["epi_gamma_t_scale"],
                design["sub_gamma_l_scale"],
                design["sub_gamma_t_scale"],
            )
            curve["mode"] = design["mode"]
            curve["dataset"] = f'{config["material"]}_{int(config["angle_deg"])}deg'
            for key in [
                "epi_gamma_l_scale",
                "epi_gamma_t_scale",
                "sub_gamma_l_scale",
                "sub_gamma_t_scale",
            ]:
                curve[key] = design[key]
            curves.append(curve)
            best_angle = curve.sort_values("rmse").iloc[0]
            angle_rows.append(
                {
                    "mode": design["mode"],
                    "dataset": f'{config["material"]}_{int(config["angle_deg"])}deg',
                    "angle_deg": config["angle_deg"],
                    "epi_gamma_l_scale": design["epi_gamma_l_scale"],
                    "epi_gamma_t_scale": design["epi_gamma_t_scale"],
                    "sub_gamma_l_scale": design["sub_gamma_l_scale"],
                    "sub_gamma_t_scale": design["sub_gamma_t_scale"],
                    "best_thickness_um": best_angle["thickness_um"],
                    "best_rmse": best_angle["rmse"],
                }
            )
        joint = summarize_joint(curves)
        joint_rows.append(
            {
                "mode": design["mode"],
                "design_note": design["design_note"],
                "epi_gamma_l_scale": design["epi_gamma_l_scale"],
                "epi_gamma_t_scale": design["epi_gamma_t_scale"],
                "sub_gamma_l_scale": design["sub_gamma_l_scale"],
                "sub_gamma_t_scale": design["sub_gamma_t_scale"],
                "joint_best_thickness_um": joint["thickness_um"],
                "joint_mean_rmse": joint["mean"],
                "joint_max_rmse": joint["max"],
                "joint_std_rmse": joint["std"],
            }
        )
    return pd.DataFrame(joint_rows), pd.DataFrame(angle_rows)


def write_summary(joint, angle):
    best_rows = joint.sort_values(["joint_mean_rmse", "joint_max_rmse"]).head(16)
    stable = (
        joint.groupby(["mode", "joint_best_thickness_um"])
        .size()
        .reset_index(name="count")
        .sort_values(["mode", "count", "joint_best_thickness_um"], ascending=[True, False, True])
    )
    by_mode = (
        joint.groupby("mode")["joint_best_thickness_um"]
        .agg(["min", "max", "mean", "std"])
        .reset_index()
    )
    lines = [
        "# Dong/TMM $\\Gamma_L,\\Gamma_T$ 参数敏感性摘要",
        "",
        "本输出用于检查 Dong2012 介电函数中的声子阻尼参数改变时，Airy/TMM 厚度低谷是否稳定，不是最终厚度结果。",
        "",
        "## 敏感性设计",
        "",
        "- 固定 Dong2012 的 $\\nu_{p,\\perp}$ 与 Drude 阻尼 $\\gamma$。",
        "- 改变声子阻尼 $\\Gamma_L$ 与 $\\Gamma_T$。",
        f"- 缩放系数：{PHONON_SCALES}。",
        "- `layer_shared_scale`：外延层与衬底分别缩放，且每层内 $\\Gamma_L$ 与 $\\Gamma_T$ 同比例缩放。",
        "- `lt_shared_scale`：全局缩放 $\\Gamma_L$ 与 $\\Gamma_T$，检查 LO/TO 阻尼结构对厚度低谷的影响。",
        f"- 厚度搜索区间：${THICKNESS_GRID_UM.min():.1f}\\text{{--}}{THICKNESS_GRID_UM.max():.1f}\\ \\mu m$。",
        f"- 波段：${REGION[0]:.0f}\\text{{--}}{REGION[1]:.0f}\\ cm^{{-1}}$。",
        "- 每个角度允许独立线性标定 $R_{\\mathrm{obs}}\\approx aR_{\\mathrm{model}}+b$。",
        "- 联合误差取 $10^\\circ$ 和 $15^\\circ$ RMSE 的均值，并用最大 RMSE 检查最差角度。",
        "",
        "## 各设计模式下的低谷范围",
        "",
        sp.markdown_table(by_mode),
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
        "- $\\Gamma_L$ 与 $\\Gamma_T$ 控制晶格振动项的线宽，主要影响吸收带附近的谱线形状。",
        "- 如果声子阻尼缩放后厚度低谷仍集中，说明厚度识别主要来自条纹相位，而不是某个声子阻尼参数偶然造成。",
        "- 如果低谷明显漂移，说明当前 Dong/TMM 模型对 Reststrahlen 区或阻尼参数仍较敏感，论文中必须降低结论强度。",
        "- 该结果仍不能替代最终联合拟合，因为真实样品的 $\\Gamma_L,\\Gamma_T$ 未知，且波段选择尚未系统比较。",
    ]
    (OUTPUT_DIR / "dong2012_tmm_phonon_sensitivity_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joint, angle = run_sensitivity()
    joint.to_csv(OUTPUT_DIR / "dong2012_tmm_phonon_sensitivity_joint.csv", index=False, encoding="utf-8-sig")
    angle.to_csv(OUTPUT_DIR / "dong2012_tmm_phonon_sensitivity_by_angle.csv", index=False, encoding="utf-8-sig")
    write_summary(joint, angle)
    print(OUTPUT_DIR / "dong2012_tmm_phonon_sensitivity_summary.md")


if __name__ == "__main__":
    main()
