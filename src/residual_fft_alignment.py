from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"
FIGURE_DIR = PROJECT / "Experiments" / "figures"

DATASET_LABELS = {
    "SiC_10deg": "SiC 10度",
    "SiC_15deg": "SiC 15度",
}

RESIDUAL_PATH = OUTPUT_DIR / "residual_diagnostics_band_metrics.csv"
SLIDING_FFT_PATH = OUTPUT_DIR / "sliding_fft_diagnostics_summary.csv"

BASE_BAND_WIDTH_CM = 500.0
PERIOD_STABLE_THRESHOLD_CM = 8.0
PEAK_TO_MEDIAN_WEAK_THRESHOLD = 3.5


def overlap_length(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    mask = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not np.any(mask):
        return np.nan
    return float(np.average(values[mask], weights=weights[mask]))


def weighted_std(values: np.ndarray, weights: np.ndarray) -> float:
    mask = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if np.count_nonzero(mask) < 2:
        return 0.0
    mean = np.average(values[mask], weights=weights[mask])
    var = np.average((values[mask] - mean) ** 2, weights=weights[mask])
    return float(np.sqrt(var))


def classify(row: pd.Series, high_rmse_threshold: float) -> str:
    high_residual = row["rmse"] >= high_rmse_threshold
    period_stable = row["period_range_cm"] <= PERIOD_STABLE_THRESHOLD_CM
    weak_peak = row["min_peak_to_median"] < PEAK_TO_MEDIAN_WEAK_THRESHOLD
    if high_residual and period_stable and not weak_peak:
        return "残差高但周期稳定：优先怀疑物理模型/材料参数/背景校准"
    if high_residual and (not period_stable or weak_peak):
        return "残差高且频域证据偏弱：优先检查局部数据质量、吸收区或预处理"
    if (not high_residual) and period_stable:
        return "残差低且周期稳定：当前模型解释相对可信"
    return "残差不高但周期不稳：不宜过度依赖该波段的频域初值"


def build_alignment() -> pd.DataFrame:
    residual = pd.read_csv(RESIDUAL_PATH)
    sliding = pd.read_csv(SLIDING_FFT_PATH)
    residual = residual[np.isclose(residual["band_max_cm"] - residual["band_min_cm"], BASE_BAND_WIDTH_CM)].copy()
    sliding = sliding[sliding["status"] == "ok"].copy()
    rows = []
    for res_row in residual.itertuples(index=False):
        candidates = sliding[sliding["dataset"] == res_row.dataset].copy()
        overlap_rows = []
        for fft_row in candidates.itertuples(index=False):
            overlap = overlap_length(
                float(res_row.band_min_cm),
                float(res_row.band_max_cm),
                float(fft_row.window_min_cm),
                float(fft_row.window_max_cm),
            )
            if overlap <= 0:
                continue
            overlap_rows.append(
                {
                    "overlap_cm": overlap,
                    "preprocessing": fft_row.preprocessing,
                    "window_center_cm": float(fft_row.window_center_cm),
                    "peak_period_cm": float(fft_row.peak_period_cm),
                    "constant_n_thickness_um": float(fft_row.constant_n_thickness_um),
                    "peak_to_median": float(fft_row.peak_to_median),
                }
            )
        overlap_df = pd.DataFrame(overlap_rows)
        if overlap_df.empty:
            rows.append({**res_row._asdict(), "alignment_status": "no_overlapping_fft_window"})
            continue
        period_values = overlap_df["peak_period_cm"].to_numpy(dtype=float)
        thickness_values = overlap_df["constant_n_thickness_um"].to_numpy(dtype=float)
        weights = overlap_df["overlap_cm"].to_numpy(dtype=float)
        rows.append(
            {
                "dataset": res_row.dataset,
                "angle_deg": float(res_row.angle_deg),
                "band": res_row.band,
                "band_min_cm": float(res_row.band_min_cm),
                "band_max_cm": float(res_row.band_max_cm),
                "rmse": float(res_row.rmse),
                "mae": float(res_row.mae),
                "lag1_autocorr": float(res_row.lag1_autocorr),
                "max_sign_run": int(res_row.max_sign_run),
                "positive_fraction": float(res_row.positive_fraction),
                "overlapping_fft_windows": int(len(overlap_df)),
                "period_weighted_mean_cm": weighted_mean(period_values, weights),
                "period_weighted_std_cm": weighted_std(period_values, weights),
                "period_min_cm": float(np.min(period_values)),
                "period_max_cm": float(np.max(period_values)),
                "period_range_cm": float(np.max(period_values) - np.min(period_values)),
                "thickness_weighted_mean_um": weighted_mean(thickness_values, weights),
                "thickness_min_um": float(np.min(thickness_values)),
                "thickness_max_um": float(np.max(thickness_values)),
                "thickness_range_um": float(np.max(thickness_values) - np.min(thickness_values)),
                "min_peak_to_median": float(overlap_df["peak_to_median"].min()),
                "median_peak_to_median": float(overlap_df["peak_to_median"].median()),
            }
        )
    aligned = pd.DataFrame(rows)
    thresholds = (
        aligned.groupby("dataset")["rmse"]
        .quantile(0.75)
        .rename("dataset_high_rmse_threshold")
        .reset_index()
    )
    aligned = aligned.merge(thresholds, on="dataset", how="left")
    aligned["diagnosis"] = aligned.apply(
        lambda row: classify(row, float(row["dataset_high_rmse_threshold"])),
        axis=1,
    )
    aligned["period_stable"] = aligned["period_range_cm"] <= PERIOD_STABLE_THRESHOLD_CM
    aligned["frequency_evidence_weak"] = aligned["min_peak_to_median"] < PEAK_TO_MEDIAN_WEAK_THRESHOLD
    return aligned


def _scale(value: float, vmin: float, vmax: float, start: float, end: float) -> float:
    if np.isclose(vmin, vmax):
        return (start + end) / 2.0
    return start + (float(value) - vmin) / (vmax - vmin) * (end - start)


def write_svg(aligned: pd.DataFrame, path: Path) -> None:
    width, height = 980, 540
    left, right, top, bottom = 86, 36, 58, 78
    x = aligned["period_range_cm"].to_numpy(dtype=float)
    y = aligned["rmse"].to_numpy(dtype=float)
    xmin, xmax = 0.0, max(1.0, float(np.nanmax(x)) * 1.12)
    ymin, ymax = 0.0, float(np.nanmax(y)) * 1.18
    colors = {"SiC_10deg": "#4c78a8", "SiC_15deg": "#f58518"}
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2:.1f}" y="30" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">残差 RMSE 与滑窗 FFT 周期稳定性</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
        f'<text x="{width/2:.1f}" y="{height-24}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">重叠 FFT 窗口中的周期波动范围 (cm^-1)</text>',
        f'<text x="22" y="{height/2:.1f}" transform="rotate(-90 22,{height/2:.1f})" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">TMM 残差 RMSE</text>',
    ]
    threshold_x = _scale(PERIOD_STABLE_THRESHOLD_CM, xmin, xmax, left, width - right)
    elements.append(f'<line x1="{threshold_x:.1f}" y1="{top}" x2="{threshold_x:.1f}" y2="{height-bottom}" stroke="#999" stroke-dasharray="5 5"/>')
    elements.append(f'<text x="{threshold_x+6:.1f}" y="{top+16}" font-family="Arial, Microsoft YaHei" font-size="11">周期波动 = {PERIOD_STABLE_THRESHOLD_CM:g}</text>')
    for row in aligned.itertuples(index=False):
        cx = _scale(float(row.period_range_cm), xmin, xmax, left, width - right)
        cy = _scale(float(row.rmse), ymin, ymax, height - bottom, top)
        radius = 4.8 if row.period_stable else 6.5
        stroke = "#111" if row.frequency_evidence_weak else "none"
        elements.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius}" fill="{colors[row.dataset]}" stroke="{stroke}" stroke-width="1.5">'
            f'<title>{DATASET_LABELS.get(row.dataset, row.dataset)} {row.band}: RMSE={row.rmse:.6g}, 周期波动={row.period_range_cm:.3g}, {row.diagnosis}</title></circle>'
        )
    for tick in np.linspace(xmin, xmax, 6):
        tx = _scale(tick, xmin, xmax, left, width - right)
        elements.append(f'<text x="{tx:.1f}" y="{height-bottom+18}" text-anchor="middle" font-family="Arial" font-size="11">{tick:.1f}</text>')
    for tick in np.linspace(ymin, ymax, 6):
        ty = _scale(tick, ymin, ymax, height - bottom, top)
        elements.append(f'<text x="{left-8}" y="{ty+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{tick:.4f}</text>')
    elements.extend(
        [
            f'<circle cx="{width-245}" cy="48" r="5" fill="{colors["SiC_10deg"]}"/><text x="{width-233}" y="52" font-family="Arial, Microsoft YaHei" font-size="12">SiC 10度</text>',
            f'<circle cx="{width-145}" cy="48" r="5" fill="{colors["SiC_15deg"]}"/><text x="{width-133}" y="52" font-family="Arial, Microsoft YaHei" font-size="12">SiC 15度</text>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(elements) + "\n", encoding="utf-8-sig")


def markdown_table(df: pd.DataFrame, columns: list[str]) -> str:
    view = df[columns].copy()
    for col in view.columns:
        if pd.api.types.is_numeric_dtype(view[col]):
            view[col] = view[col].map(lambda value: f"{value:.6g}")
    header = "| " + " | ".join(view.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    body = ["| " + " | ".join(map(str, row)) + " |" for row in view.to_numpy()]
    return "\n".join([header, sep, *body])


def make_markdown(aligned: pd.DataFrame) -> str:
    sorted_view = aligned.sort_values(["rmse"], ascending=False)
    high = sorted_view[sorted_view["rmse"] >= sorted_view["dataset_high_rmse_threshold"]]
    high_stable = high[high["period_stable"] & ~high["frequency_evidence_weak"]]
    high_weak = high[~(high["period_stable"] & ~high["frequency_evidence_weak"])]
    columns = [
        "dataset",
        "band",
        "rmse",
        "period_range_cm",
        "period_weighted_mean_cm",
        "min_peak_to_median",
        "diagnosis",
    ]
    direction = (
        "高残差波段中，若周期范围仍小且频域峰不弱，下一步应优先检查材料模型、背景校准、偏振或各向异性。"
    )
    if len(high_weak) > len(high_stable):
        direction = (
            "较多高残差波段同时出现频域证据偏弱，下一步应优先检查局部数据质量、吸收区和预处理口径。"
        )
    return f"""# 残差与滑窗 FFT 对齐诊断

## 问题

前面两条证据链分别说明：

1. [[残差诊断]]发现 TMM 在某些波段解释不好；
2. [[预处理稳健性诊断]]和 [[滑窗FFT与波段筛选]]发现条纹主周期整体稳定。

本轮要把二者对齐，回答：

$$
\\text{{残差高，是因为数据条纹本身不稳定，还是物理模型解释不够好？}}
$$

## 方法

对每个 $500\\ \\mathrm{{cm^{{-1}}}}$ 残差波段，寻找与其重叠的滑窗 FFT 窗口。用重叠长度作为权重，计算该波段附近的主周期均值和波动范围。

周期稳定阈值暂定为：

$$
\\mathrm{{range}}(\\Delta\\nu)\\le {PERIOD_STABLE_THRESHOLD_CM:.1f}\\ \\mathrm{{cm^{{-1}}}}.
$$

频域峰偏弱阈值暂定为：

$$
\\min(\\mathrm{{peak\\_to\\_median}})<{PEAK_TO_MEDIAN_WEAK_THRESHOLD:.1f}.
$$

这两个阈值只是诊断口径，不是物理常数。

## 结果表

{markdown_table(sorted_view, columns)}

## 当前判断

高残差且周期稳定的波段数：

$$
{len(high_stable)}
$$

高残差且频域证据偏弱或周期不稳的波段数：

$$
{len(high_weak)}
$$

当前方向判断：

> {direction}

## 对模型的意义

如果某个波段残差高，但滑窗 FFT 周期仍稳定，说明该波段不是“没有厚度信息”，而是当前 [[TMM转移矩阵法]] 或 [[Lorentz-Drude介电函数模型]] 没有充分解释振幅、相位、背景或材料参数。

如果某个波段残差高且频域峰也弱，则说明这个波段作为厚度信息来源的可信度较低，后续可以降低权重、单独建模或排除。

## 下一步

下一步最值得推进的是：对高残差但周期稳定的波段，检查物理模型缺项；对频域证据偏弱的波段，检查数据预处理和波段权重。这样才能避免无意义地继续堆模型。
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    aligned = build_alignment()
    aligned.to_csv(OUTPUT_DIR / "residual_fft_alignment_summary.csv", index=False, encoding="utf-8-sig")
    write_svg(aligned, FIGURE_DIR / "residual_fft_alignment.svg")
    (OUTPUT_DIR / "residual_fft_alignment_summary.md").write_text(
        make_markdown(aligned),
        encoding="utf-8-sig",
    )
    print("Wrote residual-FFT alignment diagnostics.")


if __name__ == "__main__":
    main()
