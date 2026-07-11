from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"
FIGURE_DIR = PROJECT / "Experiments" / "figures"


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_float(value: str | None) -> float:
    if value is None or value == "":
        return math.nan
    cleaned = value.replace("bootstrap median", "").strip()
    cleaned = cleaned.split("±", 1)[0].strip()
    try:
        return float(cleaned)
    except ValueError:
        return math.nan


def parse_range(value: str | None, fallback: float) -> tuple[float, float]:
    if value and "-" in value:
        left, right = value.split("-", 1)
        try:
            return float(left), float(right)
        except ValueError:
            pass
    return fallback, fallback


def select_route(rows: Iterable[dict[str, str]], route_contains: str, object_contains: str = "joint") -> dict[str, str]:
    for row in rows:
        if route_contains in row.get("model_route", "") and object_contains in row.get("object", ""):
            return row
    raise KeyError(f"Missing route {route_contains!r} / {object_contains!r}")


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path(r"C:\Windows\Fonts\msyhbd.ttc") if bold else Path(r"C:\Windows\Fonts\msyh.ttc"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
        Path(r"C:\Windows\Fonts\simsun.ttc"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def build_evidence_rows() -> list[dict[str, object]]:
    route_rows = read_rows(OUTPUT_DIR / "model_route_comparison.csv")
    constrained = read_rows(OUTPUT_DIR / "dong2012_tmm_constrained_refinement_chosen.csv")[-1]
    bootstrap = read_rows(OUTPUT_DIR / "dong2012_tmm_uncertainty_bootstrap_summary.csv")[0]
    band_weight = read_rows(OUTPUT_DIR / "band_weighted_tmm_profile_summary.csv")
    residual = read_rows(OUTPUT_DIR / "residual_diagnostics_angle_metrics.csv")

    def route_evidence(
        eid: str,
        route_key: str,
        role: str,
        confidence: str,
        include: str,
        object_key: str = "joint",
    ) -> dict[str, object]:
        row = select_route(route_rows, route_key, object_key)
        estimate = parse_float(row.get("thickness_um_summary"))
        lower, upper = parse_range(row.get("thickness_um_range"), estimate)
        return {
            "evidence_id": eid,
            "category": "模型路线",
            "method": row["model_route"],
            "estimate_um": f"{estimate:.3f}",
            "lower_um": f"{lower:.3f}",
            "upper_um": f"{upper:.3f}",
            "evidence_role": role,
            "confidence_level": confidence,
            "include_in_final_interval": include,
            "source_files": "model_route_comparison.csv",
            "key_limitation": row["main_risk"],
        }

    constrained_estimate = float(constrained["joint_best_thickness_um"])
    constrained_rmse = float(constrained["joint_mean_rmse"])
    bootstrap_low = float(bootstrap["q025_um"])
    bootstrap_high = float(bootstrap["q975_um"])
    bootstrap_median = float(bootstrap["median_um"])
    band_values = [float(row["best_thickness_um"]) for row in band_weight]
    band_low = min(band_values)
    band_high = max(band_values)
    residual_text = "; ".join(
        f"{row['dataset']}: RMSE={float(row['rmse']):.6f}, lag1={float(row['lag1_autocorr']):.4f}"
        for row in residual
    )
    dong10 = select_route(route_rows, "Dong2012 表2介电函数 TMM", "SiC_10deg")
    dong15 = select_route(route_rows, "Dong2012 表2介电函数 TMM", "SiC_15deg")
    dong_values = [parse_float(dong10["thickness_um_summary"]), parse_float(dong15["thickness_um_summary"])]

    return [
        route_evidence("E01", "常数折射率 FOD", "基线模型，用于暴露简化折射率口径的不足", "中低", "否", "SiC 10deg"),
        {
            "evidence_id": "E02",
            "category": "模型路线",
            "method": "Dong2012 表2介电函数 TMM 双角度分算",
            "estimate_um": f"{sum(dong_values) / len(dong_values):.3f}",
            "lower_um": f"{min(dong_values):.3f}",
            "upper_um": f"{max(dong_values):.3f}",
            "evidence_role": "物理正演模型起点，显示双角度低谷已接近 7.4--7.5 微米",
            "confidence_level": "中高",
            "include_in_final_interval": "是",
            "source_files": "model_route_comparison.csv",
            "key_limitation": "参数来自 Dong2012 样品，不是本题样品；这里只作为物理模型起点。",
        },
        route_evidence("E03", "Dong/TMM $\\nu_p$ 敏感性", "检查载流子相关介电参数改变时厚度低谷是否稳定", "高", "是"),
        route_evidence("E04", "Dong/TMM $\\gamma$ 敏感性", "检查 Drude 阻尼改变时厚度低谷是否稳定", "中高", "是"),
        route_evidence(
            "E05",
            "Dong/TMM $\\Gamma_L,\\Gamma_T$ 敏感性：lt_shared_scale",
            "检查声子阻尼改变时厚度低谷是否稳定",
            "中高",
            "是",
        ),
        route_evidence(
            "E06",
            "Dong/TMM 波段敏感性：不含 Reststrahlen",
            "检查剔除强吸收区后厚度低谷是否仍存在",
            "中高",
            "是",
        ),
        {
            "evidence_id": "E07",
            "category": "物理约束优化",
            "method": "受 nu_p 物理边界约束的 Dong/TMM 局部细化",
            "estimate_um": f"{constrained_estimate:.3f}",
            "lower_um": "7.455",
            "upper_um": "7.465",
            "evidence_role": f"最终代表点；联合 RMSE={constrained_rmse:.8f}",
            "confidence_level": "高",
            "include_in_final_interval": "是",
            "source_files": "dong2012_tmm_constrained_refinement_chosen.csv; dong2012_tmm_constrained_refinement_final_angle_metrics.csv",
            "key_limitation": "外延层 nu_p 缩放触及上界，材料参数不能写成内部最优。",
        },
        {
            "evidence_id": "E08",
            "category": "局部不确定性",
            "method": "固定参数残差块 bootstrap",
            "estimate_um": f"{bootstrap_median:.3f}",
            "lower_um": f"{bootstrap_low:.3f}",
            "upper_um": f"{bootstrap_high:.3f}",
            "evidence_role": "评估固定材料参数和残差重采样假设下的数据扰动",
            "confidence_level": "中高",
            "include_in_final_interval": "是",
            "source_files": "dong2012_tmm_uncertainty_bootstrap_summary.csv",
            "key_limitation": "不是完整材料参数不确定性传播。",
        },
        {
            "evidence_id": "E09",
            "category": "波段权重稳健性",
            "method": "固定参数波段权重 TMM 厚度剖面",
            "estimate_um": f"{band_values[0]:.3f}",
            "lower_um": f"{band_low:.3f}",
            "upper_um": f"{band_high:.3f}",
            "evidence_role": "检查厚度是否由个别异常波段主导",
            "confidence_level": "中高",
            "include_in_final_interval": "是",
            "source_files": "band_weighted_tmm_profile_summary.csv",
            "key_limitation": "只改变波段权重，未重新联合优化材料参数。",
        },
        {
            "evidence_id": "E10",
            "category": "残差审计",
            "method": "双角度残差诊断",
            "estimate_um": f"{constrained_estimate:.3f}",
            "lower_um": "",
            "upper_um": "",
            "evidence_role": "指出最终模型仍有结构性残差，限制过强结论",
            "confidence_level": "风险提示",
            "include_in_final_interval": "否",
            "source_files": "residual_diagnostics_angle_metrics.csv",
            "key_limitation": residual_text,
        },
    ]


def draw_final_figure(rows: list[dict[str, object]], path: Path) -> None:
    plot_rows = [
        row
        for row in rows
        if row["include_in_final_interval"] == "是" and row["lower_um"] != "" and row["upper_um"] != ""
    ]
    width, height = 1800, 1080
    left, right, top, bottom = 570, 110, 155, 120
    xmin, xmax = 7.35, 7.62
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = font(38, bold=True)
    text_font = font(24)
    small_font = font(20)
    axis_font = font(22)

    def sx(value: float) -> float:
        return left + (value - xmin) / (xmax - xmin) * (width - left - right)

    y_step = (height - top - bottom) / max(1, len(plot_rows) - 1)

    draw.text((width / 2, 38), "最终厚度证据一致性审计", fill="#111111", font=title_font, anchor="ma")
    draw.text(
        (width / 2, 92),
        "灰色带为最终推荐区间 7.4--7.6 微米；红线为受约束 Dong/TMM 代表值 7.465 微米",
        fill="#555555",
        font=small_font,
        anchor="ma",
    )
    draw.rectangle((sx(7.4), top - 18, sx(7.6), height - bottom + 16), fill="#f1f1f1")
    draw.line((sx(7.465), top - 25, sx(7.465), height - bottom + 25), fill="#d62728", width=4)

    for tick in [7.35, 7.40, 7.45, 7.50, 7.55, 7.60]:
        x = sx(tick)
        draw.line((x, height - bottom, x, height - bottom + 10), fill="#333333", width=2)
        draw.text((x, height - bottom + 18), f"{tick:.2f}", fill="#333333", font=axis_font, anchor="ma")
        draw.line((x, top - 5, x, height - bottom), fill="#e5e5e5", width=1)
    draw.line((left, height - bottom, width - right, height - bottom), fill="#333333", width=2)
    draw.text((left + (width - left - right) / 2, height - 42), "厚度 d / 微米", fill="#222222", font=axis_font, anchor="ma")

    colors = {"高": "#1f77b4", "中高": "#2ca02c", "中": "#9467bd", "中低": "#8c8c8c"}
    for i, row in enumerate(plot_rows):
        y = top + i * y_step
        lower = float(row["lower_um"])
        upper = float(row["upper_um"])
        estimate = float(row["estimate_um"])
        color = colors.get(str(row["confidence_level"]), "#4c78a8")
        label_text = str(row["method"])
        label_text = label_text.replace("$\\nu_p$", "nu_p")
        label_text = label_text.replace("$\\gamma$", "gamma")
        label_text = label_text.replace("$\\Gamma_L,\\Gamma_T$", "Gamma_L/Gamma_T")
        label_text = label_text.replace("：lt_shared_scale", "")
        draw.text((30, y + 2), label_text, fill="#222222", font=text_font, anchor="la")
        draw.line((sx(lower), y, sx(upper), y), fill=color, width=8)
        draw.ellipse((sx(estimate) - 8, y - 8, sx(estimate) + 8, y + 8), fill=color, outline="white", width=2)
        label = f"{estimate:.3f}" if math.isclose(lower, upper) else f"{lower:.3f}-{upper:.3f}"
        draw.text((sx(upper) + 12, y + 2), label, fill=color, font=small_font, anchor="la")

    draw.text((sx(7.465) + 8, top - 36), "代表值 7.465", fill="#d62728", font=small_font, anchor="la")
    draw.text((sx(7.4) + 6, top - 36), "推荐区间", fill="#666666", font=small_font, anchor="la")
    image.save(path)


def write_summary(rows: list[dict[str, object]]) -> None:
    final_rows = [
        row
        for row in rows
        if row["include_in_final_interval"] == "是" and row["lower_um"] != "" and row["upper_um"] != ""
    ]
    lower = min(float(row["lower_um"]) for row in final_rows)
    upper = max(float(row["upper_um"]) for row in final_rows)
    constrained = next(row for row in rows if row["evidence_id"] == "E07")
    content = f"""# 最终证据一致性审计

## 目的

本脚本只读取已经生成并有文件记录的实验输出，用统一表格检查最终厚度结论是否由多条证据共同支持。它不重新调参，不扩大搜索，也不把频域初值或数据处理结果伪装成最终厚度。

## 主要结论

- 纳入最终区间判断的强证据覆盖约为 ${lower:.3f}\\text{{--}}{upper:.3f}\\ \\mu\\mathrm{{m}}$。
- 为避免过度精确化，论文采用更稳健的表述：$d\\approx7.4\\text{{--}}7.6\\ \\mu\\mathrm{{m}}$。
- 最终代表点来自受 $\\nu_p$ 物理边界约束的 Dong/TMM 局部细化：$d^\\ast={float(constrained['estimate_um']):.3f}\\ \\mu\\mathrm{{m}}$。
- 残差诊断显示 $15^\\circ$ 的残差强于 $10^\\circ$，且两角度残差自相关较高，因此不应把代表点写成已完全确定的真实厚度。

## 输出文件

- `final_evidence_audit.csv`：最终证据审计表。
- `final_evidence_audit_summary.md`：本摘要。
- `../figures/final_evidence_audit.png`：最终证据一致性图，可放入论文。

## 论文写作口径

建议写法是：当前数据和模型共同支持 $7.4\\text{{--}}7.6\\ \\mu\\mathrm{{m}}$ 作为最可信厚度区间；$7.465\\ \\mu\\mathrm{{m}}$ 是受物理边界约束的 Dong/TMM 模型代表值，而不是无条件真值。
"""
    (OUTPUT_DIR / "final_evidence_audit_summary.md").write_text(content, encoding="utf-8-sig")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    rows = build_evidence_rows()
    fieldnames = [
        "evidence_id",
        "category",
        "method",
        "estimate_um",
        "lower_um",
        "upper_um",
        "evidence_role",
        "confidence_level",
        "include_in_final_interval",
        "source_files",
        "key_limitation",
    ]
    write_rows(OUTPUT_DIR / "final_evidence_audit.csv", rows, fieldnames)
    draw_final_figure(rows, FIGURE_DIR / "final_evidence_audit.png")
    write_summary(rows)
    print("Wrote final evidence audit outputs.")


if __name__ == "__main__":
    main()
