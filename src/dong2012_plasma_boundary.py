from __future__ import annotations

import csv
import math
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"
WRITING_DIR = PROJECT / "Writing"

ELECTRON_CHARGE_C = 1.602176634e-19
VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12
LIGHT_SPEED_CM_PER_S = 2.99792458e10
ELECTRON_REST_MASS_KG = 9.1093837015e-31

# Dong2012 Table 2 and the project Dong/TMM scripts use the perpendicular
# dielectric path. The effective mass factor is the perpendicular 4H-SiC
# value used in the current Dong2012 conversion check.
EPS_INF_PERP = 6.56
MSTAR_PERP_FACTOR = 0.42

DONG_TABLE2 = {
    "epilayer": {
        "label": "外延层",
        "nu_p_perp_cm_inv": 72.98,
        "dong_infrared_n_cm3": 1.6e17,
        "dong_other_n_cm3": 8.8e16,
        "other_method": "Hg-probe C-V",
    },
    "substrate": {
        "label": "衬底",
        "nu_p_perp_cm_inv": 376.60,
        "dong_infrared_n_cm3": 4.4e18,
        "dong_other_n_cm3": 5.0e18,
        "other_method": "Hall measurement",
    },
}

SCENARIOS = [
    {
        "role": "epilayer",
        "scenario": "Dong2012 Table 2 baseline",
        "scale": 1.0,
        "reason": "Dong2012 表 2 的外延层红外拟合参数，作为当前代码基准。",
    },
    {
        "role": "epilayer",
        "scenario": "nu_p sensitivity RMSE-best",
        "scale": 1.5,
        "reason": "当前本题数据的 $\\nu_p$ 敏感性扫描中，联合 RMSE 最小的外延层缩放。",
    },
    {
        "role": "epilayer",
        "scenario": "local refinement final",
        "scale": 1.75,
        "reason": "无 scipy 局部细化坐标搜索的最终外延层 $\\nu_p$ 缩放。",
    },
    {
        "role": "epilayer",
        "scenario": "provisional constrained lower",
        "scale": 0.75,
        "reason": "候选受约束优化下界；覆盖 Dong2012 其他方法量级，同时避免过低导致信号弱耦合。",
    },
    {
        "role": "epilayer",
        "scenario": "provisional constrained upper",
        "scale": 1.75,
        "reason": "候选受约束优化上界；暂取到当前局部细化边界，不继续无依据放宽。",
    },
    {
        "role": "substrate",
        "scenario": "Dong2012 Table 2 baseline",
        "scale": 1.0,
        "reason": "Dong2012 表 2 的衬底红外拟合参数，作为当前代码基准。",
    },
    {
        "role": "substrate",
        "scenario": "nu_p sensitivity RMSE-best",
        "scale": 1.0,
        "reason": "当前本题数据的 $\\nu_p$ 敏感性扫描中，联合 RMSE 最小的衬底缩放。",
    },
    {
        "role": "substrate",
        "scenario": "local refinement final",
        "scale": 1.0,
        "reason": "无 scipy 局部细化坐标搜索的最终衬底 $\\nu_p$ 缩放。",
    },
    {
        "role": "substrate",
        "scenario": "provisional constrained lower",
        "scale": 0.75,
        "reason": "候选受约束优化下界；允许衬底载流子浓度低于 Dong2012 基准但仍保持重掺杂量级。",
    },
    {
        "role": "substrate",
        "scenario": "provisional constrained upper",
        "scale": 1.25,
        "reason": "候选受约束优化上界；覆盖 Hall 结果相对红外结果的偏高量级。",
    },
]


def concentration_from_nu_p(nu_p_cm_inv: float) -> float:
    """Convert plasma frequency in cm^-1 to carrier concentration in cm^-3."""
    angular_frequency = 2.0 * math.pi * LIGHT_SPEED_CM_PER_S * nu_p_cm_inv
    effective_mass = MSTAR_PERP_FACTOR * ELECTRON_REST_MASS_KG
    concentration_m3 = (
        angular_frequency**2
        * effective_mass
        * VACUUM_PERMITTIVITY_F_PER_M
        * EPS_INF_PERP
        / ELECTRON_CHARGE_C**2
    )
    return concentration_m3 / 1.0e6


def nu_p_from_concentration(concentration_cm3: float) -> float:
    """Convert carrier concentration in cm^-3 to plasma frequency in cm^-1."""
    concentration_m3 = concentration_cm3 * 1.0e6
    effective_mass = MSTAR_PERP_FACTOR * ELECTRON_REST_MASS_KG
    angular_frequency = math.sqrt(
        concentration_m3
        * ELECTRON_CHARGE_C**2
        / (effective_mass * VACUUM_PERMITTIVITY_F_PER_M * EPS_INF_PERP)
    )
    return angular_frequency / (2.0 * math.pi * LIGHT_SPEED_CM_PER_S)


def sci(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}e}"


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row[col]) for col in columns) + " |")
    return "\n".join(lines)


def build_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for role, info in DONG_TABLE2.items():
        baseline_n = concentration_from_nu_p(info["nu_p_perp_cm_inv"])
        other_n = info["dong_other_n_cm3"]
        other_scale = math.sqrt(other_n / baseline_n)
        rows.append(
            {
                "role": role,
                "layer": info["label"],
                "scenario": f"Dong2012 other method ({info['other_method']})",
                "nu_p_scale": f"{other_scale:.4f}",
                "nu_p_perp_cm_inv": f"{nu_p_from_concentration(other_n):.3f}",
                "carrier_concentration_cm3": sci(other_n),
                "relative_to_baseline_n": f"{other_n / baseline_n:.3f}",
                "reason": "Dong2012 表 2 的外部方法对照值；用于检查红外拟合参数量级。",
            }
        )

    for item in SCENARIOS:
        role = item["role"]
        info = DONG_TABLE2[role]
        baseline_n = concentration_from_nu_p(info["nu_p_perp_cm_inv"])
        scaled_n = baseline_n * item["scale"] ** 2
        scaled_nu_p = info["nu_p_perp_cm_inv"] * item["scale"]
        rows.append(
            {
                "role": role,
                "layer": info["label"],
                "scenario": item["scenario"],
                "nu_p_scale": f"{item['scale']:.4f}",
                "nu_p_perp_cm_inv": f"{scaled_nu_p:.3f}",
                "carrier_concentration_cm3": sci(scaled_n),
                "relative_to_baseline_n": f"{item['scale'] ** 2:.3f}",
                "reason": item["reason"],
            }
        )
    return rows


def write_csv(rows: list[dict[str, object]]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "dong2012_plasma_boundary_table.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_summary(rows: list[dict[str, object]]) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    WRITING_DIR.mkdir(parents=True, exist_ok=True)

    columns = [
        "layer",
        "scenario",
        "nu_p_scale",
        "nu_p_perp_cm_inv",
        "carrier_concentration_cm3",
        "relative_to_baseline_n",
    ]
    table = markdown_table(rows, columns)

    epilayer_base = concentration_from_nu_p(DONG_TABLE2["epilayer"]["nu_p_perp_cm_inv"])
    substrate_base = concentration_from_nu_p(DONG_TABLE2["substrate"]["nu_p_perp_cm_inv"])

    content = r"""# $\nu_p$ 物理边界与载流子浓度换算

## 研究方向自检

本轮工作只解决一个模型问题：当前 Dong/TMM 模型对 $\\nu_p$ 最敏感，而 $\\nu_p$ 又不能作为任意数值参数自由扩张。因此需要把 $\\nu_p$ 换算为载流子浓度 $N$，给下一轮受约束优化提供物理边界。

它服务于当前主线：

$$
\\text{{题目数据}}\\rightarrow \\text{{物理参数约束}}\\rightarrow \\text{{受约束 TMM 优化}}\\rightarrow \\text{{厚度可信度}}
$$

## 资料来源

- Dong et al. 2012，题名为 *Characterization of 4H-SiC substrates and epilayers by Fourier transform infrared reflectance spectroscopy*，DOI 为 $10.1088/1674\\text{{-}}1056/21/4/047802$。本项目已保存 Crossref 元数据和本地 PDF/抽取文本。
- 本轮只使用 Dong2012 中已经在本地精读笔记记录的 Eq. (2) 和 Table 2 数值，不新增未经核验的外部文献结论。
- PDF 抽取文本存在符号乱码风险；正式论文引用前仍应对照 PDF 页面截图复核公式排版。

## 模型关系

Dong2012 给出的关系可以整理为：

$$
\\nu_{p,\\perp}
=
\\frac{{1}}{{2\\pi c}}
\\sqrt{{
\\frac{{Nq^2}}
{{m_{\\perp}^{*}\\varepsilon_0\\varepsilon_{\\infty,\\perp}}}
}}
$$

反解得到：

$$
N
=
\\frac{{(2\\pi c\\nu_{p,\\perp})^2
m_{\\perp}^{*}\\varepsilon_0\\varepsilon_{\\infty,\\perp}}}
{{q^2}}
$$

因此如果把等离子体频率写成缩放形式

$$
\\nu_{p,\\perp}=s_{\\nu_p}\\nu_{p,0},
$$

则载流子浓度随缩放因子平方变化：

$$
N(s_{\\nu_p})=s_{\\nu_p}^{2}N_0.
$$

这一步非常重要，因为它说明 $s_{\\nu_p}=2$ 不是“参数翻倍”那么轻，而是把载流子浓度放大到 $4$ 倍。

## 换算基准

当前脚本使用：

$$
\\varepsilon_{\\infty,\\perp}=6.56,
\\qquad
m_{\\perp}^{*}=0.42m_0.
$$

由 Dong2012 表 2 中的 $\\nu_{p,\\perp}$ 换算得到：

$$
N_{{\\mathrm{{epi}},0}}\\approx __EPILAYER_BASE__\\ \\mathrm{{cm}}^{{-3}},
\\qquad
N_{{\\mathrm{{sub}},0}}\\approx __SUBSTRATE_BASE__\\ \\mathrm{{cm}}^{{-3}}.
$$

这与 Dong2012 Table 2 中外延层约 $1.6\\times10^{{17}}\\ \\mathrm{{cm}}^{{-3}}$、衬底约 $4.4\\times10^{{18}}\\ \\mathrm{{cm}}^{{-3}}$ 的红外拟合结果一致，说明本项目代码中的单位换算是自洽的。

## 当前参数场景换算表

__TABLE__

## 对当前模型的约束建议

下一轮受约束优化可以先采用候选边界：

$$
s_{\\nu_p,\\mathrm{{epi}}}\\in[0.75,1.75],
\\qquad
s_{\\nu_p,\\mathrm{{sub}}}\\in[0.75,1.25].
$$

对应的载流子浓度范围约为：

$$
N_{{\\mathrm{{epi}}}}\\in[9.20\\times10^{{16}},5.01\\times10^{{17}}]\\ \\mathrm{{cm}}^{{-3}},
$$

$$
N_{{\\mathrm{{sub}}}}\\in[2.45\\times10^{{18}},6.81\\times10^{{18}}]\\ \\mathrm{{cm}}^{{-3}}.
$$

这组边界的含义不是“本题样品真实浓度已经确定”，而是：

1. 它覆盖 Dong2012 红外结果和其他方法对照值的同量级范围；
2. 它包含当前本题数据的 $\\nu_p$ 敏感性 RMSE 最小点；
3. 它包含局部细化得到的外延层 $s_{\\nu_p}=1.75$；
4. 它不允许继续无依据地把 $\\nu_p$ 放大到非常高的载流子浓度，从而避免数值优化只追 RMSE。

## 不能下的结论

本轮不能写：

> 本题样品外延层载流子浓度就是 $5.01\\times10^{{17}}\\ \\mathrm{{cm}}^{{-3}}$。

更准确的写法是：

> 根据 Dong2012 的 $\\nu_p$-$N$ 关系，当前局部细化中的外延层 $s_{\\nu_p}=1.75$ 等价于把 Dong2012 外延层基准载流子浓度放大到约 $5.01\\times10^{{17}}\\ \\mathrm{{cm}}^{{-3}}$。由于本题未提供独立电学测量，该数值只能作为受约束优化中的候选参数状态，而不是样品真实掺杂结论。

## 下一步

最有价值的下一步是把上面的 $s_{\\nu_p}$ 边界接入 Dong/TMM 局部优化脚本，重新比较：

$$
\\text{{无物理边界局部细化}}
\\quad\\text{{vs.}}\\quad
\\text{{有 }\\nu_p\\text{{ 物理边界的局部细化}}
$$

评价指标不只看联合 RMSE，还要看：

$$
d^\\ast,\quad
\\mathrm{{RMSE}}_{{10^\\circ}},\quad
\\mathrm{{RMSE}}_{{15^\\circ}},\quad
\\text{{是否触及边界}},\quad
\\text{{残差是否集中在特定波段}}.
$$
"""
    content = (
        content.replace("__EPILAYER_BASE__", sci(epilayer_base))
        .replace("__SUBSTRATE_BASE__", sci(substrate_base))
        .replace("__TABLE__", table)
        .replace("{{", "{")
        .replace("}}", "}")
        .replace("\\\\", "\\")
    )

    output_path = OUTPUT_DIR / "dong2012_plasma_boundary_summary.md"
    writing_path = WRITING_DIR / "nu_p物理边界与优化约束-2026-05-04.md"
    output_path.write_text(content, encoding="utf-8")
    writing_path.write_text(content, encoding="utf-8")
    return output_path, writing_path


def main() -> None:
    rows = build_rows()
    csv_path = write_csv(rows)
    summary_path, writing_path = write_summary(rows)
    print(csv_path)
    print(summary_path)
    print(writing_path)


if __name__ == "__main__":
    main()
