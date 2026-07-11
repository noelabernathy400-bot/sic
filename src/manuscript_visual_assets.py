from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import spectral_pipeline as sp


PROJECT = Path(__file__).resolve().parents[1]
FIGURE_DIR = PROJECT / "Experiments" / "figures"
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"
WRITING_DIR = PROJECT / "Writing"

DATASET_LABELS = {
    "SiC_10deg": "SiC 10度",
    "SiC_15deg": "SiC 15度",
}


def _scale(value: float, vmin: float, vmax: float, start: float, end: float) -> float:
    if np.isclose(vmin, vmax):
        return (start + end) / 2.0
    return start + (float(value) - vmin) / (vmax - vmin) * (end - start)


def _polyline(points: list[tuple[float, float]], xmin, xmax, ymin, ymax, left, right, top, bottom, width, height) -> str:
    return " ".join(
        f"{_scale(x, xmin, xmax, left, width-right):.2f},{_scale(y, ymin, ymax, height-bottom, top):.2f}"
        for x, y in points
    )


def read_sic_raw() -> dict[str, pd.DataFrame]:
    configs = [
        {"attachment": "附件1.xlsx", "dataset": "SiC_10deg"},
        {"attachment": "附件2.xlsx", "dataset": "SiC_15deg"},
    ]
    out = {}
    for config in configs:
        path = sp.attachment_dir() / config["attachment"]
        raw = pd.read_excel(path)
        df = pd.DataFrame(
            {
                "wavenumber_cm": raw.iloc[:, 0].astype(float),
                "reflectance_pct": raw.iloc[:, 1].astype(float),
            }
        ).sort_values("wavenumber_cm")
        out[config["dataset"]] = df
    return out


def write_dual_angle_raw(path: Path) -> None:
    data = read_sic_raw()
    width, height = 1020, 520
    left, right, top, bottom = 78, 34, 58, 72
    xmin = min(float(df["wavenumber_cm"].min()) for df in data.values())
    xmax = max(float(df["wavenumber_cm"].max()) for df in data.values())
    ymin = min(float(df["reflectance_pct"].min()) for df in data.values())
    ymax = max(float(df["reflectance_pct"].max()) for df in data.values())
    ymin -= (ymax - ymin) * 0.06
    ymax += (ymax - ymin) * 0.06
    colors = {"SiC_10deg": "#4c78a8", "SiC_15deg": "#f58518"}
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2:.1f}" y="30" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">SiC 双角度红外反射谱</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
        f'<text x="{width/2:.1f}" y="{height-24}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">波数 (cm^-1)</text>',
        f'<text x="20" y="{height/2:.1f}" transform="rotate(-90 20,{height/2:.1f})" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">反射率 (%)</text>',
    ]
    for dataset, df in data.items():
        stride = max(1, len(df) // 1400)
        points = list(
            zip(
                df["wavenumber_cm"].to_numpy(dtype=float)[::stride],
                df["reflectance_pct"].to_numpy(dtype=float)[::stride],
            )
        )
        elements.append(
            f'<polyline fill="none" stroke="{colors[dataset]}" stroke-width="1.6" opacity="0.92" points="{_polyline(points, xmin, xmax, ymin, ymax, left, right, top, bottom, width, height)}"><title>{DATASET_LABELS.get(dataset, dataset)}</title></polyline>'
        )
    for tick in np.linspace(xmin, xmax, 6):
        x = _scale(tick, xmin, xmax, left, width - right)
        elements.append(f'<text x="{x:.1f}" y="{height-bottom+18}" text-anchor="middle" font-family="Arial" font-size="11">{tick:.0f}</text>')
    for tick in np.linspace(ymin, ymax, 6):
        y = _scale(tick, ymin, ymax, height - bottom, top)
        elements.append(f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{tick:.1f}</text>')
    legend_x = width - 220
    legend_y = 48
    for dataset, color in colors.items():
        elements.append(f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x+26}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        elements.append(f'<text x="{legend_x+34}" y="{legend_y+4}" font-family="Arial, Microsoft YaHei" font-size="12">{DATASET_LABELS.get(dataset, dataset)}</text>')
        legend_y += 20
    elements.append("</svg>")
    path.write_text("\n".join(elements) + "\n", encoding="utf-8-sig")


def write_evidence_flow(path: Path) -> None:
    width, height = 1180, 360
    boxes = [
        ("原始谱线", "双角度数据"),
        ("预处理", "稳定条纹周期"),
        ("FFT/FOD", "厚度尺度初值"),
        ("Dong/TMM", "物理正演模型"),
        ("诊断", "残差与敏感性"),
        ("稳健性", "波段权重"),
        ("候选结论", "7.4-7.6 μm"),
    ]
    colors = ["#e8f1fb", "#eef6e9", "#fff4df", "#f3ecfb", "#fdeceb", "#eaf7f6", "#eef0ff"]
    box_w, box_h = 138, 82
    y = 132
    gap = (width - 2 * 44 - len(boxes) * box_w) / (len(boxes) - 1)
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2:.1f}" y="38" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="22">SiC 外延层厚度反演证据链</text>',
        f'<text x="{width/2:.1f}" y="68" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13" fill="#555">先验证数据事实，再进入物理解释；每一步都有可复现诊断输出。</text>',
    ]
    for i, ((title, subtitle), fill) in enumerate(zip(boxes, colors)):
        x = 44 + i * (box_w + gap)
        elements.append(f'<rect x="{x:.1f}" y="{y}" width="{box_w}" height="{box_h}" rx="8" fill="{fill}" stroke="#445" stroke-width="1.2"/>')
        elements.append(f'<text x="{x+box_w/2:.1f}" y="{y+32}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="15" font-weight="600">{title}</text>')
        elements.append(f'<text x="{x+box_w/2:.1f}" y="{y+56}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="12" fill="#444">{subtitle}</text>')
        if i < len(boxes) - 1:
            x1 = x + box_w
            x2 = x + box_w + gap
            cy = y + box_h / 2
            elements.append(f'<line x1="{x1+6:.1f}" y1="{cy:.1f}" x2="{x2-10:.1f}" y2="{cy:.1f}" stroke="#555" stroke-width="1.5" marker-end="url(#arrow)"/>')
    elements.insert(
        2,
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="#555"/></marker></defs>',
    )
    elements.append(
        f'<text x="{width/2:.1f}" y="285" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="14">当前结论：候选区间，不是最终认证厚度</text>'
    )
    elements.append(
        f'<text x="{width/2:.1f}" y="312" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="16" font-weight="600">d ≈ 7.4-7.6 μm</text>'
    )
    elements.append("</svg>")
    path.write_text("\n".join(elements) + "\n", encoding="utf-8-sig")


def write_catalog(path: Path) -> None:
    rows = [
        ("图 1", "paper_fig00_evidence_flow.svg", "研究证据链总览", "摘要后或引言末尾"),
        ("图 2", "paper_fig00_sic_dual_angle_raw.svg", "SiC 双角度原始反射谱", "数据说明"),
        ("图 3", "data_processing_fft_thickness_seed.svg", "不同预处理下 FFT 厚度初值", "数据处理"),
        ("图 4", "sliding_fft_thickness_by_window.svg", "滑窗 FFT 主周期稳定性", "数据处理"),
        ("图 5", "paper_fig01_model_route_comparison.svg", "模型路线厚度对比", "综合结果"),
        ("图 6", "paper_fig05_tmm_bestfit_SiC_10deg.svg", "$10^\\circ$ TMM 拟合谱线", "TMM 结果"),
        ("图 7", "paper_fig05_tmm_bestfit_SiC_15deg.svg", "$15^\\circ$ TMM 拟合谱线", "TMM 结果"),
        ("图 8", "residual_diagnostics_angle_residuals.svg", "双角度残差曲线", "残差诊断"),
        ("图 9", "residual_fft_alignment.svg", "残差与频域证据对齐", "残差解释"),
        ("图 10", "band_weighted_tmm_profile.svg", "波段权重 TMM 厚度剖面", "稳健性分析"),
        ("图 11", "paper_fig10_rmse_heatmap_nu_p_sensitivity.svg", "$\\nu_p$ RMSE 热力图", "参数敏感性"),
        ("图 12", "paper_fig02_tmm_profile.svg", "TMM 厚度 RMSE 剖面", "最终候选区间"),
    ]
    lines = [
        "---",
        "type: figure-catalog",
        "project: 碳化硅外延层厚度确定研究",
        "created: 2026-05-04",
        "---",
        "",
        "# 论文图表嵌入清单 - 2026-05-04",
        "",
        "这份清单用于配套 `Writing/论文图文版-2026-05-04.md`。每张图都必须回答一个模型问题，而不是装饰。",
        "",
        "| 编号 | 文件 | 回答的问题 | 建议位置 |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.extend(
        [
            "",
            "## 图表使用原则",
            "",
            "- 每张图必须在正文中解释“它证明了什么”和“它不能证明什么”。",
            "- FFT 图只能证明条纹周期稳定，不能直接证明最终厚度。",
            "- TMM 拟合图必须和残差图一起看，不能只展示拟合曲线。",
            "- 波段权重图是稳健性旁证，不是最终置信区间。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    WRITING_DIR.mkdir(parents=True, exist_ok=True)
    write_dual_angle_raw(FIGURE_DIR / "paper_fig00_sic_dual_angle_raw.svg")
    write_evidence_flow(FIGURE_DIR / "paper_fig00_evidence_flow.svg")
    write_catalog(WRITING_DIR / "论文图表嵌入清单-2026-05-04.md")
    print("Wrote manuscript visual assets.")


if __name__ == "__main__":
    main()
