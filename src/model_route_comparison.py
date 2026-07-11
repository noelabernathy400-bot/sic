from pathlib import Path

import numpy as np
import pandas as pd

import spectral_pipeline as sp


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"


def fmt_range(values):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return ""
    return f"{values.min():.3f}-{values.max():.3f}"


def fmt_mean_std(values):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return ""
    if len(values) == 1:
        return f"{values[0]:.3f}"
    return f"{values.mean():.3f} ± {values.std(ddof=1):.3f}"


def load_constant_fod():
    fod = pd.read_csv(OUTPUT_DIR / "fod_fit_results.csv")
    sic = fod[fod["material"] == "SiC"]
    rows = []
    for angle, group in sic.groupby("angle_deg"):
        rows.append(
            {
                "model_route": "常数折射率 FOD",
                "object": f"SiC {angle:.0f}deg",
                "thickness_um_summary": fmt_mean_std(group["d_um"]),
                "thickness_um_range": fmt_range(group["d_um"]),
                "main_evidence": "峰/谷同类极值链 FOD 拟合，$n=2.60$",
                "trust_level": "中低",
                "main_risk": "常数折射率假设过强；10度和15度不一致；只使用极值位置",
            }
        )
    return rows


def load_dispersion_fod():
    disp = pd.read_csv(OUTPUT_DIR / "dispersion_fod_results.csv")
    rows = []
    for angle, group in disp.groupby("angle_deg"):
        rows.append(
            {
                "model_route": "Larruquert 色散 FOD",
                "object": f"SiC {angle:.0f}deg",
                "thickness_um_summary": fmt_mean_std(group["dispersion_fod_um"]),
                "thickness_um_range": fmt_range(group["dispersion_fod_um"]),
                "main_evidence": "将 FOD 相位因子升级为 $n(\\nu)\\cos\\theta_1\\nu$",
                "trust_level": "中",
                "main_risk": "Larruquert 薄膜 $n,k$ 不一定适配本题 4H-SiC 外延层；$k(\\nu)$ 未进入完整反射模型",
            }
        )
    return rows


def load_tmm_artificial():
    grid = pd.read_csv(OUTPUT_DIR / "tmm_air_debug_grid.csv")
    rows = []
    for (dataset, contrast), group in grid.groupby(["dataset", "contrast_delta_n"]):
        if abs(float(contrast) - 0.05) > 1e-9:
            continue
        best = group.sort_values("affine_rmse").iloc[0]
        rows.append(
            {
                "model_route": "Airy/TMM 人工折射率差",
                "object": dataset,
                "thickness_um_summary": f"{best['thickness_um']:.3f}",
                "thickness_um_range": f"{best['thickness_um']:.3f}",
                "main_evidence": "用人工 $\\Delta n=0.05$ 检查全谱相位拟合流程",
                "trust_level": "调试用",
                "main_risk": "$\\Delta n$ 是人工设定；只能证明代码链条可运行",
            }
        )
    return rows


def load_dong_table2():
    grid = pd.read_csv(OUTPUT_DIR / "dong2012_dielectric_thickness_grid.csv")
    rows = []
    for dataset, group in grid.groupby("dataset"):
        best = group.sort_values("affine_rmse").iloc[0]
        rows.append(
            {
                "model_route": "Dong2012 表2介电函数 TMM",
                "object": dataset,
                "thickness_um_summary": f"{best['thickness_um']:.3f}",
                "thickness_um_range": f"{best['thickness_um']:.3f}",
                "main_evidence": "用 Dong2012 表2外延层/衬底参数生成复折射率并全谱搜索",
                "trust_level": "中高候选",
                "main_risk": "参数来自 Dong2012 样品，不是本题样品",
            }
        )
    return rows


def load_dong_sensitivity():
    sens = pd.read_csv(OUTPUT_DIR / "dong2012_tmm_sensitivity_joint.csv")
    top = sens.sort_values(["joint_mean_rmse", "joint_max_rmse"]).head(12)
    return [
        {
            "model_route": "Dong/TMM $\\nu_p$ 敏感性",
            "object": "SiC 10deg+15deg joint",
            "thickness_um_summary": fmt_mean_std(top["joint_best_thickness_um"]),
            "thickness_um_range": fmt_range(top["joint_best_thickness_um"]),
            "main_evidence": "缩放外延层/衬底等离子体频率后，多角度联合低谷仍集中",
            "trust_level": "当前最强候选",
            "main_risk": "只单独缩放 $\\nu_p$，尚未与 $\\gamma$、声子阻尼和波段联合优化",
        }
    ]


def load_dong_gamma_sensitivity():
    path = OUTPUT_DIR / "dong2012_tmm_gamma_sensitivity_joint.csv"
    if not path.exists():
        return []
    sens = pd.read_csv(path)
    top = sens.sort_values(["joint_mean_rmse", "joint_max_rmse"]).head(12)
    return [
        {
            "model_route": "Dong/TMM $\\gamma$ 敏感性",
            "object": "SiC 10deg+15deg joint",
            "thickness_um_summary": fmt_mean_std(top["joint_best_thickness_um"]),
            "thickness_um_range": fmt_range(top["joint_best_thickness_um"]),
            "main_evidence": "缩放外延层/衬底 Drude 阻尼 $\\gamma$ 后，多角度联合低谷仍集中",
            "trust_level": "稳健性补充",
            "main_risk": "只单独改变 $\\gamma$，尚未和 $\\nu_p$、声子阻尼、波段联合优化",
        }
    ]


def load_dong_phonon_sensitivity():
    path = OUTPUT_DIR / "dong2012_tmm_phonon_sensitivity_joint.csv"
    if not path.exists():
        return []
    sens = pd.read_csv(path)
    rows = []
    for mode, group in sens.groupby("mode"):
        top = group.sort_values(["joint_mean_rmse", "joint_max_rmse"]).head(12)
        rows.append(
            {
                "model_route": f"Dong/TMM $\\Gamma_L,\\Gamma_T$ 敏感性：{mode}",
                "object": "SiC 10deg+15deg joint",
                "thickness_um_summary": fmt_mean_std(top["joint_best_thickness_um"]),
                "thickness_um_range": fmt_range(top["joint_best_thickness_um"]),
                "main_evidence": "缩放声子阻尼后，多角度联合低谷的漂移范围",
                "trust_level": "稳健性补充",
                "main_risk": "仍未和 $\\nu_p$、$\\gamma$、波段做联合优化",
            }
        )
    return rows


def load_dong_band_sensitivity():
    path = OUTPUT_DIR / "dong2012_tmm_band_sensitivity_joint.csv"
    if not path.exists():
        return []
    sens = pd.read_csv(path)
    rows = []
    groups = [
        ("Dong/TMM 波段敏感性：全部波段", sens),
        ("Dong/TMM 波段敏感性：不含 Reststrahlen", sens[~sens["includes_reststrahlen"].astype(bool)]),
    ]
    for name, group in groups:
        rows.append(
            {
                "model_route": name,
                "object": "SiC 10deg+15deg joint",
                "thickness_um_summary": fmt_mean_std(group["joint_best_thickness_um"]),
                "thickness_um_range": fmt_range(group["joint_best_thickness_um"]),
                "main_evidence": "改变参与拟合的波数区间后，多角度联合低谷的漂移范围",
                "trust_level": "稳健性补充",
                "main_risk": "仍未和材料参数做联合优化；包含 Reststrahlen 区时误差明显增大",
            }
        )
    return rows


def load_dong_coordinate_search():
    path = OUTPUT_DIR / "dong2012_tmm_coordinate_search_chosen.csv"
    if not path.exists():
        return []
    chosen = pd.read_csv(path)
    final = chosen.iloc[-1]
    return [
        {
            "model_route": "Dong/TMM 分阶段坐标搜索",
            "object": "SiC 10deg+15deg joint",
            "thickness_um_summary": f"{final['joint_best_thickness_um']:.3f}",
            "thickness_um_range": f"{final['joint_best_thickness_um']:.3f}",
            "main_evidence": "按 baseline → $\\nu_p$ → $\\gamma$ → $\\Gamma_L,\\Gamma_T$ 分阶段搜索后的联合低谷",
            "trust_level": "探索性优化",
            "main_risk": "顺序坐标搜索依赖阶段顺序和粗网格，不能视为全局最优",
        }
    ]


def load_dong_local_refinement():
    path = OUTPUT_DIR / "dong2012_tmm_local_refinement_chosen.csv"
    if not path.exists():
        return []
    chosen = pd.read_csv(path)
    initial = chosen.iloc[0]
    final = chosen.iloc[-1]
    improvement_pct = 100.0 * (
        initial["joint_mean_rmse"] - final["joint_mean_rmse"]
    ) / initial["joint_mean_rmse"]
    return [
        {
            "model_route": "Dong/TMM 局部细化坐标搜索",
            "object": "SiC 10deg+15deg joint",
            "thickness_um_summary": f"{final['joint_best_thickness_um']:.3f}",
            "thickness_um_range": f"{initial['joint_best_thickness_um']:.3f}-{final['joint_best_thickness_um']:.3f}",
            "main_evidence": (
                "在粗网格最终状态附近用 $0.125$ 步长做两轮局部坐标细化，"
                f"joint RMSE 相对改善约 {improvement_pct:.3f}%"
            ),
            "trust_level": "局部优化补充",
            "main_risk": "部分参数被推到局部搜索边界；仍不是连续全局优化，也不能替代材料参数物理约束",
        }
    ]


def load_dong_constrained_refinement():
    path = OUTPUT_DIR / "dong2012_tmm_constrained_refinement_chosen.csv"
    if not path.exists():
        return []
    chosen = pd.read_csv(path)
    initial = chosen.iloc[0]
    final = chosen.iloc[-1]
    improvement_pct = 100.0 * (
        initial["joint_mean_rmse"] - final["joint_mean_rmse"]
    ) / initial["joint_mean_rmse"]
    boundary_note = "epi nu_p upper" if final.get("epi_nu_p_scale_boundary") == "upper" else "interior"
    return [
        {
            "model_route": "Dong/TMM 有 $\\nu_p$ 物理边界局部细化",
            "object": "SiC 10deg+15deg joint",
            "thickness_um_summary": f"{final['joint_best_thickness_um']:.3f}",
            "thickness_um_range": f"{initial['joint_best_thickness_um']:.3f}-{final['joint_best_thickness_um']:.3f}",
            "main_evidence": (
                "将 $s_{\\nu_p,\\mathrm{epi}}\\in[0.75,1.75]$、"
                "$s_{\\nu_p,\\mathrm{sub}}\\in[0.75,1.25]$ 接入局部细化，"
                f"joint RMSE 相对改善约 {improvement_pct:.3f}%，边界状态为 {boundary_note}"
            ),
            "trust_level": "物理约束优化补充",
            "main_risk": "外延层 $s_{\\nu_p}$ 触及上界，说明它是候选边界内的边界最优状态，不能写成内部最优材料参数",
        }
    ]


def load_dong_uncertainty():
    path = OUTPUT_DIR / "dong2012_tmm_uncertainty_bootstrap_summary.csv"
    if not path.exists():
        return []
    summary = pd.read_csv(path).iloc[0]
    support_path = OUTPUT_DIR / "dong2012_tmm_uncertainty_support.csv"
    support = pd.read_csv(support_path)
    five_pct = support[support["relative_rmse_increase"] == 0.05].iloc[0]
    return [
        {
            "model_route": "Dong/TMM 固定参数不确定性",
            "object": "SiC 10deg+15deg joint",
            "thickness_um_summary": f"{summary['median_um']:.3f} bootstrap median",
            "thickness_um_range": f"{summary['q025_um']:.3f}-{summary['q975_um']:.3f}",
            "main_evidence": (
                "固定坐标搜索参数后，profile support 和 moving block bootstrap "
                f"均集中；5% RMSE 支持区间为 {five_pct['support_min_um']:.3f}-{five_pct['support_max_um']:.3f}"
            ),
            "trust_level": "局部不确定性",
            "main_risk": "只反映固定材料参数和残差重采样假设下的数据扰动，不是最终物理置信区间",
        }
    ]


def load_si_review():
    si = pd.read_csv(OUTPUT_DIR / "si_thickness_review.csv")
    rows = []
    for angle, group in si.groupby("angle_deg"):
        rows.append(
            {
                "model_route": "Si 常数 FOD 反向复核",
                "object": f"Si {angle:.0f}deg",
                "thickness_um_summary": fmt_mean_std(group["current_fod_um"]),
                "thickness_um_range": fmt_range(group["current_fod_um"]),
                "main_evidence": "附件3/4在 $n=3.42$ 口径下峰/谷 FOD 稳定指向 $3.4\\text{--}3.6\\ \\mu m$",
                "trust_level": "中间审查",
                "main_risk": "尚未引入 Si 色散光学常数和全谱模型，不能最终否定旧值 $5.13\\ \\mu m$",
            }
        )
    return rows


def build_comparison():
    rows = []
    rows.extend(load_constant_fod())
    rows.extend(load_dispersion_fod())
    rows.extend(load_tmm_artificial())
    rows.extend(load_dong_table2())
    rows.extend(load_dong_sensitivity())
    rows.extend(load_dong_gamma_sensitivity())
    rows.extend(load_dong_phonon_sensitivity())
    rows.extend(load_dong_band_sensitivity())
    rows.extend(load_dong_coordinate_search())
    rows.extend(load_dong_local_refinement())
    rows.extend(load_dong_constrained_refinement())
    rows.extend(load_dong_uncertainty())
    rows.extend(load_si_review())
    return pd.DataFrame(rows)


def write_summary(comparison):
    lines = [
        "# 模型路线结果对比与可信度",
        "",
        "本表用于比较当前所有阶段模型的厚度候选区间和可信度。它不是最终结论，而是研究路线图。",
        "",
        "## 对比表",
        "",
        sp.markdown_table(comparison),
        "",
        "## 当前主判断",
        "",
        "1. 常数折射率 FOD 和 Larruquert 色散 FOD 都证明了一个事实：折射率模型会显著改变厚度结果。",
        "2. Airy/TMM 人工折射率差模型只用于验证代码物理边界，不能给最终厚度。",
        "3. Dong2012 介电函数把外延层/衬底差异从人工参数推进到物理参数，是当前最有研究价值的路线。",
        "4. Dong/TMM 的 $\\nu_p$ 敏感性显示，多组参数的联合厚度低谷集中在约 $7.4\\text{--}7.6\\ \\mu m$；$\\gamma$ 敏感性进一步收束到约 $7.44\\text{--}7.46\\ \\mu m$。",
        "5. 波段敏感性显示，不含 Reststrahlen 区的高波数波段低谷集中在约 $7.42\\text{--}7.44\\ \\mu m$；包含低波数强吸收区时误差明显增大，但低谷仍未离开 $7.4\\ \\mu m$ 附近。",
        "6. 分阶段坐标搜索把联合低谷保持在 $7.46\\ \\mu m$ 附近，但误差改善很小，说明粗网格参数调整没有推翻当前候选区间，也不能证明已经达到全局最优。",
        "7. 固定坐标搜索参数后，厚度 profile 和残差块 bootstrap 都集中在 $7.45\\ \\mu m$ 附近，说明在该模型口径下数据扰动不容易推翻低谷。",
        "8. 因为仍缺少连续优化和材料参数置信区间，上述区间应作为当前最强候选区间，而不是最终答案。",
        "9. Si 附件的 $3.4\\text{--}3.6\\ \\mu m$ 复核结果说明旧论文 $5.13\\ \\mu m$ 需要进一步解释，但仍需 Si 色散/TMM 才能最终裁决。",
        "",
        "## 论文表达建议",
        "",
        "论文中不要把模型写成一次跳跃。更强的写法是展示可信度递进：",
        "",
        "$$",
        "\\text{峰距法}",
        "\\rightarrow",
        "\\text{FOD}",
        "\\rightarrow",
        "\\text{色散 FOD}",
        "\\rightarrow",
        "\\text{Airy/TMM}",
        "\\rightarrow",
        "\\text{Dong 介电函数敏感性}",
        "$$",
        "",
        "每一步都回答前一步的缺陷，最终把推荐路线建立在全谱、多角度和参数敏感性之上。",
    ]
    (OUTPUT_DIR / "model_route_comparison_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    comparison = build_comparison()
    comparison.to_csv(OUTPUT_DIR / "model_route_comparison.csv", index=False, encoding="utf-8-sig")
    write_summary(comparison)
    print(OUTPUT_DIR / "model_route_comparison_summary.md")


if __name__ == "__main__":
    main()
