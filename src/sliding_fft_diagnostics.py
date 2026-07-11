from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from data_processing_diagnostics import (
    SIC_CONFIGS,
    DATASET_LABELS,
    PREPROCESSING_LABELS,
    centered,
    frequency_bounds,
    load_uniform_band,
    moving_average_detrend,
    rolling_median_detrend,
    thickness_from_frequency,
)


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"
FIGURE_DIR = PROJECT / "Experiments" / "figures"

WINDOW_WIDTH_CM = 1200.0
WINDOW_STEP_CM = 250.0
N_EFF = 2.60
ZERO_PADDING_FACTOR = 8


def preprocessing_variants(signal: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "center_only": centered(signal),
        "ma_detrend_401cm": moving_average_detrend(signal, 401.0),
        "rolling_median_401cm": rolling_median_detrend(signal, 401.0),
    }


def window_fft(
    grid: np.ndarray,
    values: np.ndarray,
    angle_deg: float,
) -> dict[str, float | str]:
    if len(grid) < 64:
        return {"status": "too_few_points"}
    step = float(np.median(np.diff(grid)))
    n_fft = int(2 ** np.ceil(np.log2(len(values) * ZERO_PADDING_FACTOR)))
    windowed = centered(values) * np.hanning(len(values))
    spectrum = np.abs(np.fft.rfft(windowed, n=n_fft))
    freq = np.fft.rfftfreq(n_fft, d=step)
    f_min, f_max = frequency_bounds(N_EFF, angle_deg)
    mask = (freq >= f_min) & (freq <= f_max)
    mask[0] = False
    if np.count_nonzero(mask) < 3:
        return {"status": "too_few_frequency_bins"}
    idxs = np.where(mask)[0]
    target_amp = spectrum[idxs]
    peak_idx = int(idxs[int(np.argmax(target_amp))])
    peak_frequency = float(freq[peak_idx])
    peak_period = float(1.0 / peak_frequency)
    sorted_amp = np.sort(target_amp)
    second_amp = float(sorted_amp[-2]) if len(sorted_amp) >= 2 else np.nan
    median_amp = float(np.median(target_amp))
    peak_amp = float(spectrum[peak_idx])
    return {
        "status": "ok",
        "n_points": int(len(grid)),
        "fft_bin_spacing": float(freq[1] - freq[0]),
        "peak_frequency_cycles_per_cm": peak_frequency,
        "peak_period_cm": peak_period,
        "constant_n_thickness_um": thickness_from_frequency(peak_frequency, N_EFF, angle_deg),
        "peak_to_second": float(peak_amp / second_amp) if second_amp > 0 else np.nan,
        "peak_to_median": float(peak_amp / median_amp) if median_amp > 0 else np.nan,
    }


def build_sliding_fft() -> pd.DataFrame:
    rows = []
    for config in SIC_CONFIGS:
        grid, signal = load_uniform_band(config)
        variants = preprocessing_variants(signal)
        starts = np.arange(float(grid.min()), float(grid.max()) - WINDOW_WIDTH_CM + 0.5, WINDOW_STEP_CM)
        for method, processed in variants.items():
            for start in starts:
                end = start + WINDOW_WIDTH_CM
                mask = (grid >= start) & (grid <= end)
                sub_grid = grid[mask]
                sub_values = processed[mask]
                result = window_fft(sub_grid, sub_values, float(config["angle_deg"]))
                rows.append(
                    {
                        "dataset": config["dataset"],
                        "angle_deg": float(config["angle_deg"]),
                        "preprocessing": method,
                        "window_min_cm": float(start),
                        "window_max_cm": float(end),
                        "window_center_cm": float((start + end) / 2.0),
                        "window_width_cm": WINDOW_WIDTH_CM,
                        "n_eff": N_EFF,
                        **result,
                    }
                )
    return pd.DataFrame(rows)


def _scale(value: float, vmin: float, vmax: float, start: float, end: float) -> float:
    if np.isclose(vmin, vmax):
        return (start + end) / 2.0
    return start + (float(value) - vmin) / (vmax - vmin) * (end - start)


def write_svg(summary: pd.DataFrame, path: Path) -> None:
    ok = summary[summary["status"] == "ok"].copy()
    width, height = 1040, 620
    left, right, top, bottom = 78, 34, 58, 72
    panel_gap = 40
    panel_h = (height - top - bottom - panel_gap) / 2.0
    xmin = float(ok["window_center_cm"].min())
    xmax = float(ok["window_center_cm"].max())
    ymin = float(ok["constant_n_thickness_um"].min()) - 0.4
    ymax = float(ok["constant_n_thickness_um"].max()) + 0.4
    colors = {
        "center_only": "#4c78a8",
        "ma_detrend_401cm": "#f58518",
        "rolling_median_401cm": "#54a24b",
    }
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2:.1f}" y="30" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">不同波数窗口下的滑窗 FFT 厚度初值</text>',
    ]
    for panel_idx, dataset in enumerate(["SiC_10deg", "SiC_15deg"]):
        y_top = top + panel_idx * (panel_h + panel_gap)
        y_bottom = y_top + panel_h
        panel = ok[ok["dataset"] == dataset]
        elements.extend(
            [
                f'<text x="{left}" y="{y_top-12:.1f}" font-family="Arial, Microsoft YaHei" font-size="15">{DATASET_LABELS.get(dataset, dataset)}</text>',
                f'<line x1="{left}" y1="{y_bottom:.1f}" x2="{width-right}" y2="{y_bottom:.1f}" stroke="#333"/>',
                f'<line x1="{left}" y1="{y_top:.1f}" x2="{left}" y2="{y_bottom:.1f}" stroke="#333"/>',
            ]
        )
        for method, group in panel.groupby("preprocessing"):
            group = group.sort_values("window_center_cm")
            points = " ".join(
                f'{_scale(row.window_center_cm, xmin, xmax, left, width-right):.2f},{_scale(row.constant_n_thickness_um, ymin, ymax, y_bottom, y_top):.2f}'
                for row in group.itertuples(index=False)
            )
            method_label = PREPROCESSING_LABELS.get(method, method)
            elements.append(f'<polyline fill="none" stroke="{colors[method]}" stroke-width="2" points="{points}"><title>{method_label}</title></polyline>')
            for row in group.itertuples(index=False):
                x = _scale(row.window_center_cm, xmin, xmax, left, width - right)
                y = _scale(row.constant_n_thickness_um, ymin, ymax, y_bottom, y_top)
                elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.3" fill="{colors[method]}"><title>{method_label}: {row.window_center_cm:.0f} cm^-1, {row.constant_n_thickness_um:.4f} μm</title></circle>')
        for tick in np.linspace(ymin, ymax, 5):
            y = _scale(tick, ymin, ymax, y_bottom, y_top)
            elements.append(f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{tick:.2f}</text>')
    for tick in np.linspace(xmin, xmax, 6):
        x = _scale(tick, xmin, xmax, left, width - right)
        elements.append(f'<text x="{x:.1f}" y="{height-24}" text-anchor="middle" font-family="Arial" font-size="11">{tick:.0f}</text>')
    elements.append(f'<text x="{width/2:.1f}" y="{height-7}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">窗口中心波数 (cm^-1)</text>')
    legend_x = left
    legend_y = 50
    for method, color in colors.items():
        elements.append(f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x+26}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        elements.append(f'<text x="{legend_x+32}" y="{legend_y+4}" font-family="Arial, Microsoft YaHei" font-size="12">{PREPROCESSING_LABELS.get(method, method)}</text>')
        legend_x += 190
    elements.append("</svg>")
    path.write_text("\n".join(elements) + "\n", encoding="utf-8-sig")


def make_markdown(summary: pd.DataFrame) -> str:
    ok = summary[summary["status"] == "ok"].copy()
    rows = []
    for (dataset, method), group in ok.groupby(["dataset", "preprocessing"]):
        rows.append(
            {
                "dataset": dataset,
                "preprocessing": method,
                "n_windows": int(len(group)),
                "period_min_cm": float(group["peak_period_cm"].min()),
                "period_max_cm": float(group["peak_period_cm"].max()),
                "period_std_cm": float(group["peak_period_cm"].std(ddof=1)) if len(group) > 1 else 0.0,
                "thickness_min_um": float(group["constant_n_thickness_um"].min()),
                "thickness_max_um": float(group["constant_n_thickness_um"].max()),
                "thickness_std_um": float(group["constant_n_thickness_um"].std(ddof=1)) if len(group) > 1 else 0.0,
                "min_peak_to_median": float(group["peak_to_median"].min()),
            }
        )
    table = pd.DataFrame(rows).sort_values(["dataset", "preprocessing"])
    printable = table.copy()
    for col in printable.columns:
        if col not in {"dataset", "preprocessing"}:
            printable[col] = printable[col].map(lambda value: f"{value:.6g}")
    md_table = "| " + " | ".join(printable.columns) + " |\n"
    md_table += "| " + " | ".join(["---"] * len(printable.columns)) + " |\n"
    md_table += "\n".join("| " + " | ".join(map(str, row)) + " |" for row in printable.to_numpy())
    overall_period_min = float(ok["peak_period_cm"].min())
    overall_period_max = float(ok["peak_period_cm"].max())
    overall_thick_min = float(ok["constant_n_thickness_um"].min())
    overall_thick_max = float(ok["constant_n_thickness_um"].max())
    return f"""# 滑窗 FFT 诊断摘要

## 问题

上一轮全波段 FFT 显示主周期约为 $250\\ \\mathrm{{cm^{{-1}}}}$。本轮继续问一个更细的问题：这个主周期是否在不同波数窗口里都稳定？如果某些窗口明显漂移，它们可能对应吸收区、基线异常、噪声增强或物理模型遗漏。

## 方法

使用窗口宽度：

$$
W={WINDOW_WIDTH_CM:.0f}\\ \\mathrm{{cm^{{-1}}}},
$$

步长：

$$
S={WINDOW_STEP_CM:.0f}\\ \\mathrm{{cm^{{-1}}}}.
$$

对每个窗口分别做 FFT，并用常数 $n=2.60$ 只作统一尺度换算：

$$
d_{{\\mathrm{{FFT}}}}
=
\\frac{{10000 f}}{{2\\sqrt{{n^2-\\sin^2\\theta}}}}.
$$

注意：这里的 $d_{{\\mathrm{{FFT}}}}$ 是频域厚度初值，不是最终厚度。

## 当前结果

所有窗口与预处理下，主周期范围为：

$$
\\Delta\\nu\\in[{overall_period_min:.3f},{overall_period_max:.3f}]\\ \\mathrm{{cm^{{-1}}}}.
$$

对应常数 $n=2.60$ 口径下的厚度初值范围为：

$$
d_{{\\mathrm{{FFT}}}}\\in[{overall_thick_min:.3f},{overall_thick_max:.3f}]\\ \\mu m.
$$

分组统计如下：

{md_table}

## 解释

若主周期在滑窗中仍然稳定，说明数据中的条纹周期不是某个全局预处理偶然制造出来的，而是在多个局部波段都存在。这提高了“数据本身确实含有稳定厚度尺度”的可信度。

但这仍然不等于证明 Dong/TMM 的 $d\\approx7.4\\text{{--}}7.6\\ \\mu m$ 已经完全正确。原因是频域换算仍依赖 $n_{{\\mathrm{{eff}}}}$，而当前常数 $n=2.60$ 只是统一比较口径。最终厚度必须回到 [[TMM转移矩阵法]]、[[Lorentz-Drude介电函数模型]]、双角度联合拟合和 [[残差诊断]]。

## 下一步

下一步应该把滑窗 FFT 的窗口结果和 TMM 分波段残差对齐：如果某些残差高发波段仍有稳定主周期，那么问题更可能来自材料模型或背景校准；如果这些波段主周期也不稳定，那么问题可能来自数据预处理、吸收区或局部噪声。
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    summary = build_sliding_fft()
    summary.to_csv(OUTPUT_DIR / "sliding_fft_diagnostics_summary.csv", index=False, encoding="utf-8-sig")
    write_svg(summary, FIGURE_DIR / "sliding_fft_thickness_by_window.svg")
    (OUTPUT_DIR / "sliding_fft_diagnostics_summary.md").write_text(
        make_markdown(summary),
        encoding="utf-8-sig",
    )
    print("Wrote sliding FFT diagnostics.")


if __name__ == "__main__":
    main()
