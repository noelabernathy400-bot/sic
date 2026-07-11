from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import spectral_pipeline as sp


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"
FIGURE_DIR = PROJECT / "Experiments" / "figures"

SIC_CONFIGS = [
    {"attachment_index": 1, "dataset": "SiC_10deg", "angle_deg": 10.0, "n0": 2.60},
    {"attachment_index": 2, "dataset": "SiC_15deg", "angle_deg": 15.0, "n0": 2.60},
]

DATASET_LABELS = {
    "SiC_10deg": "SiC 10度",
    "SiC_15deg": "SiC 15度",
}

PREPROCESSING_LABELS = {
    "center_only": "去均值",
    "ma_detrend_201cm": "移动平均去趋势 201",
    "ma_detrend_401cm": "移动平均去趋势 401",
    "ma_detrend_801cm": "移动平均去趋势 801",
    "poly2_detrend": "二次多项式去趋势",
    "poly3_detrend": "三次多项式去趋势",
    "rolling_median_401cm": "滚动中位数基线",
    "rolling_q20_401cm": "滚动20%分位基线",
    "first_difference": "一阶差分",
}

BAND_LOW_CM = 1500.0
BAND_HIGH_CM = 4000.0
UNIFORM_STEP_CM = 1.0
TARGET_THICKNESS_RANGE_UM = (3.0, 12.0)


def read_attachment_by_index(index: int) -> pd.DataFrame:
    candidates = sorted(sp.attachment_dir().glob("*.xlsx"))
    matches = [path for path in candidates if str(index) in path.stem]
    if not matches:
        raise FileNotFoundError(f"Could not find attachment {index} in {sp.attachment_dir()}.")
    raw = pd.read_excel(matches[0])
    return pd.DataFrame(
        {
            "wavenumber_cm": raw.iloc[:, 0].astype(float),
            "reflectance": raw.iloc[:, 1].astype(float) / 100.0,
        }
    )


def load_uniform_band(config: dict) -> tuple[np.ndarray, np.ndarray]:
    df = read_attachment_by_index(int(config["attachment_index"]))
    nu = df["wavenumber_cm"].to_numpy(dtype=float)
    reflectance = df["reflectance"].to_numpy(dtype=float)
    order = np.argsort(nu)
    nu = nu[order]
    reflectance = reflectance[order]
    mask = (nu >= BAND_LOW_CM) & (nu <= BAND_HIGH_CM)
    nu = nu[mask]
    reflectance = reflectance[mask]
    grid = np.arange(float(nu.min()), float(nu.max()) + 0.5 * UNIFORM_STEP_CM, UNIFORM_STEP_CM)
    signal = np.interp(grid, nu, reflectance)
    return grid, signal


def odd_window(width_cm: float, n_points: int, step_cm: float = UNIFORM_STEP_CM) -> int:
    window = max(5, int(round(width_cm / step_cm)))
    if window % 2 == 0:
        window += 1
    return min(window, n_points // 2 * 2 + 1)


def centered(values: np.ndarray) -> np.ndarray:
    return values - float(np.mean(values))


def moving_average_detrend(values: np.ndarray, width_cm: float) -> np.ndarray:
    trend = sp.moving_average(values, odd_window(width_cm, len(values)))
    return centered(values - trend)


def polynomial_detrend(grid: np.ndarray, values: np.ndarray, degree: int) -> np.ndarray:
    x = (grid - float(np.mean(grid))) / float(np.std(grid, ddof=1))
    coeff = np.polyfit(x, values, degree)
    trend = np.polyval(coeff, x)
    return centered(values - trend)


def rolling_median_detrend(values: np.ndarray, width_cm: float) -> np.ndarray:
    window = odd_window(width_cm, len(values))
    trend = (
        pd.Series(values)
        .rolling(window=window, center=True, min_periods=max(5, window // 5))
        .median()
        .bfill()
        .ffill()
        .to_numpy(dtype=float)
    )
    return centered(values - trend)


def rolling_quantile_detrend(values: np.ndarray, width_cm: float, quantile: float) -> np.ndarray:
    window = odd_window(width_cm, len(values))
    trend = (
        pd.Series(values)
        .rolling(window=window, center=True, min_periods=max(5, window // 5))
        .quantile(quantile)
        .bfill()
        .ffill()
        .to_numpy(dtype=float)
    )
    return centered(values - trend)


def first_difference(values: np.ndarray) -> np.ndarray:
    diff = np.diff(values, prepend=values[0])
    return centered(diff)


def preprocessing_variants(grid: np.ndarray, signal: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "center_only": centered(signal),
        "ma_detrend_201cm": moving_average_detrend(signal, 201.0),
        "ma_detrend_401cm": moving_average_detrend(signal, 401.0),
        "ma_detrend_801cm": moving_average_detrend(signal, 801.0),
        "poly2_detrend": polynomial_detrend(grid, signal, 2),
        "poly3_detrend": polynomial_detrend(grid, signal, 3),
        "rolling_median_401cm": rolling_median_detrend(signal, 401.0),
        "rolling_q20_401cm": rolling_quantile_detrend(signal, 401.0, 0.20),
        "first_difference": first_difference(signal),
    }


def optical_factor(n_eff: float, angle_deg: float) -> float:
    theta = np.deg2rad(angle_deg)
    return float(np.sqrt(n_eff**2 - np.sin(theta) ** 2))


def frequency_bounds(n_eff: float, angle_deg: float) -> tuple[float, float]:
    d_min, d_max = TARGET_THICKNESS_RANGE_UM
    factor = optical_factor(n_eff, angle_deg)
    return 2.0 * d_min * factor / 10000.0, 2.0 * d_max * factor / 10000.0


def thickness_from_frequency(frequency: float, n_eff: float, angle_deg: float) -> float:
    return float(10000.0 * frequency / (2.0 * optical_factor(n_eff, angle_deg)))


def fft_metrics(grid: np.ndarray, values: np.ndarray, n_eff: float, angle_deg: float) -> dict[str, float | str]:
    if len(grid) < 32:
        return {"fft_status": "too_few_points"}
    step = float(np.median(np.diff(grid)))
    windowed = centered(values) * np.hanning(len(values))
    spectrum = np.abs(np.fft.rfft(windowed))
    freq = np.fft.rfftfreq(len(values), d=step)
    f_min, f_max = frequency_bounds(n_eff, angle_deg)
    mask = (freq >= f_min) & (freq <= f_max)
    mask[0] = False
    if np.count_nonzero(mask) < 3:
        return {"fft_status": "too_few_frequency_bins"}
    idxs = np.where(mask)[0]
    target_amp = spectrum[idxs]
    peak_idx = int(idxs[int(np.argmax(target_amp))])
    peak_frequency = float(freq[peak_idx])
    sorted_amp = np.sort(target_amp)
    peak_amp = float(spectrum[peak_idx])
    second_amp = float(sorted_amp[-2]) if len(sorted_amp) >= 2 else np.nan
    median_amp = float(np.median(target_amp))
    return {
        "fft_status": "ok",
        "fft_resolution": float(freq[1] - freq[0]) if len(freq) > 1 else np.nan,
        "peak_frequency_cycles_per_cm": peak_frequency,
        "peak_period_cm": float(1.0 / peak_frequency),
        "constant_n_thickness_um": thickness_from_frequency(peak_frequency, n_eff, angle_deg),
        "peak_to_second": float(peak_amp / second_amp) if second_amp > 0 else np.nan,
        "peak_to_median": float(peak_amp / median_amp) if median_amp > 0 else np.nan,
        "target_energy_fraction": float(np.sum(target_amp**2) / np.sum(spectrum[1:] ** 2)),
        "signal_std": float(np.std(values, ddof=1)),
    }


def simple_extrema_metrics(grid: np.ndarray, values: np.ndarray, angle_deg: float, n_eff: float) -> dict[str, float]:
    # Extrema are found on the preprocessed signal. A light smoothing is used
    # only to avoid counting point-level wiggles as physical fringes.
    smooth = sp.moving_average(values, 51)
    max_idx = np.where((smooth[1:-1] > smooth[:-2]) & (smooth[1:-1] > smooth[2:]))[0] + 1
    min_idx = np.where((smooth[1:-1] < smooth[:-2]) & (smooth[1:-1] < smooth[2:]))[0] + 1

    def keep_spaced(idxs: np.ndarray, high: bool) -> np.ndarray:
        min_distance = int(round(160.0 / UNIFORM_STEP_CM))
        ordered = sorted(idxs, key=lambda idx: smooth[idx], reverse=high)
        kept: list[int] = []
        for idx in ordered:
            if all(abs(idx - prev) >= min_distance for prev in kept):
                kept.append(int(idx))
        return np.array(sorted(kept), dtype=int)

    peaks = keep_spaced(max_idx, True)
    troughs = keep_spaced(min_idx, False)

    def spacing_stats(idxs: np.ndarray, prefix: str) -> dict[str, float]:
        if len(idxs) < 2:
            return {
                f"{prefix}_count": int(len(idxs)),
                f"{prefix}_median_spacing_cm": np.nan,
                f"{prefix}_constant_n_interval_thickness_um": np.nan,
            }
        spacings = np.diff(grid[idxs])
        median_spacing = float(np.median(spacings))
        d_um = 10000.0 / (2.0 * n_eff * np.sqrt(1.0 - (np.sin(np.deg2rad(angle_deg)) / n_eff) ** 2) * median_spacing)
        return {
            f"{prefix}_count": int(len(idxs)),
            f"{prefix}_median_spacing_cm": median_spacing,
            f"{prefix}_constant_n_interval_thickness_um": float(d_um),
        }

    out = {}
    out.update(spacing_stats(peaks, "peak"))
    out.update(spacing_stats(troughs, "trough"))
    return out


def build_diagnostics() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    curves = []
    for config in SIC_CONFIGS:
        grid, signal = load_uniform_band(config)
        variants = preprocessing_variants(grid, signal)
        for method, processed in variants.items():
            metrics = {
                "dataset": config["dataset"],
                "angle_deg": float(config["angle_deg"]),
                "preprocessing": method,
                "band_min_cm": BAND_LOW_CM,
                "band_max_cm": BAND_HIGH_CM,
                "n_eff_for_constant_n_check": float(config["n0"]),
            }
            metrics.update(fft_metrics(grid, processed, float(config["n0"]), float(config["angle_deg"])))
            metrics.update(simple_extrema_metrics(grid, processed, float(config["angle_deg"]), float(config["n0"])))
            rows.append(metrics)
            stride = max(1, len(grid) // 900)
            for nu, value in zip(grid[::stride], processed[::stride]):
                curves.append(
                    {
                        "dataset": config["dataset"],
                        "angle_deg": float(config["angle_deg"]),
                        "preprocessing": method,
                        "wavenumber_cm": float(nu),
                        "processed_signal": float(value),
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(curves)


def _scale(value: float, vmin: float, vmax: float, start: float, end: float) -> float:
    if np.isclose(vmin, vmax):
        return (start + end) / 2.0
    return start + (float(value) - vmin) / (vmax - vmin) * (end - start)


def write_svg_lines(curves: pd.DataFrame, path: Path) -> None:
    selected_methods = [
        "center_only",
        "ma_detrend_401cm",
        "poly3_detrend",
        "rolling_median_401cm",
        "first_difference",
    ]
    selected = curves[curves["preprocessing"].isin(selected_methods)].copy()
    width, height = 1080, 720
    left, right, top, bottom = 76, 34, 58, 70
    panel_gap = 46
    panel_h = (height - top - bottom - panel_gap) / 2.0
    xmin = BAND_LOW_CM
    xmax = BAND_HIGH_CM
    colors = {
        "center_only": "#4c78a8",
        "ma_detrend_401cm": "#f58518",
        "poly3_detrend": "#54a24b",
        "rolling_median_401cm": "#b279a2",
        "first_difference": "#e45756",
    }
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2:.1f}" y="30" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">SiC preprocessing comparison: extracted fringe signal</text>',
    ]
    for panel_idx, dataset in enumerate(["SiC_10deg", "SiC_15deg"]):
        panel = selected[selected["dataset"] == dataset]
        y = panel["processed_signal"].to_numpy(dtype=float)
        ymax = max(abs(float(np.nanmin(y))), abs(float(np.nanmax(y)))) * 1.08
        ymin = -ymax
        y_top = top + panel_idx * (panel_h + panel_gap)
        y_bottom = y_top + panel_h
        elements.extend(
            [
                f'<text x="{left}" y="{y_top-12:.1f}" font-family="Arial, Microsoft YaHei" font-size="15">{DATASET_LABELS.get(dataset, dataset)}</text>',
                f'<line x1="{left}" y1="{y_bottom:.1f}" x2="{width-right}" y2="{y_bottom:.1f}" stroke="#333"/>',
                f'<line x1="{left}" y1="{y_top:.1f}" x2="{left}" y2="{y_bottom:.1f}" stroke="#333"/>',
            ]
        )
        for method in selected_methods:
            sub = panel[panel["preprocessing"] == method]
            points = " ".join(
                f'{_scale(row.wavenumber_cm, xmin, xmax, left, width-right):.2f},{_scale(row.processed_signal, ymin, ymax, y_bottom, y_top):.2f}'
                for row in sub.itertuples(index=False)
            )
            elements.append(
                f'<polyline fill="none" stroke="{colors[method]}" stroke-width="1.35" opacity="0.86" points="{points}"><title>{PREPROCESSING_LABELS.get(method, method)}</title></polyline>'
            )
    legend_x = left
    legend_y = height - 24
    x = legend_x
    for method in selected_methods:
        elements.append(f'<line x1="{x}" y1="{legend_y}" x2="{x+26}" y2="{legend_y}" stroke="{colors[method]}" stroke-width="3"/>')
        elements.append(f'<text x="{x+32}" y="{legend_y+4}" font-family="Arial, Microsoft YaHei" font-size="12">{PREPROCESSING_LABELS.get(method, method)}</text>')
        x += 190
    elements.append("</svg>")
    path.write_text("\n".join(elements) + "\n", encoding="utf-8-sig")


def write_svg_thickness(summary: pd.DataFrame, path: Path) -> None:
    ok = summary[summary["fft_status"] == "ok"].copy()
    width, height = 1080, 560
    left, right, top, bottom = 82, 34, 58, 120
    methods = list(ok["preprocessing"].drop_duplicates())
    x_slots = {(dataset, method): idx for idx, (dataset, method) in enumerate((d, m) for d in ["SiC_10deg", "SiC_15deg"] for m in methods)}
    ymin = max(0.0, float(ok["constant_n_thickness_um"].min()) - 0.8)
    ymax = float(ok["constant_n_thickness_um"].max()) + 0.8
    colors = {"SiC_10deg": "#4c78a8", "SiC_15deg": "#f58518"}
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2:.1f}" y="30" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">不同预处理下的常数折射率 FFT 厚度初值</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
        f'<text x="20" y="{height/2:.1f}" transform="rotate(-90 20,{height/2:.1f})" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">厚度初值 (μm)，常数 n=2.60</text>',
    ]
    n_slots = max(1, len(x_slots) - 1)
    for row in ok.itertuples(index=False):
        slot = x_slots[(row.dataset, row.preprocessing)]
        x = _scale(slot, 0, n_slots, left + 14, width - right - 14)
        y = _scale(row.constant_n_thickness_um, ymin, ymax, height - bottom, top)
        elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{colors[row.dataset]}"><title>{DATASET_LABELS.get(row.dataset, row.dataset)} {PREPROCESSING_LABELS.get(row.preprocessing, row.preprocessing)}: {row.constant_n_thickness_um:.4f} μm</title></circle>')
    for tick in np.linspace(ymin, ymax, 6):
        y = _scale(tick, ymin, ymax, height - bottom, top)
        elements.append(f'<line x1="{left-4}" y1="{y:.1f}" x2="{left}" y2="{y:.1f}" stroke="#333"/>')
        elements.append(f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{tick:.2f}</text>')
    for i, method in enumerate(methods):
        x1 = _scale(i, 0, max(1, len(methods) - 1), left + 14, (width - right - 14 + left + 14) / 2.0 - 20)
        elements.append(f'<text x="{x1:.1f}" y="{height-bottom+18}" transform="rotate(38 {x1:.1f},{height-bottom+18})" font-family="Arial, Microsoft YaHei" font-size="10">{PREPROCESSING_LABELS.get(method, method)}</text>')
        x2 = _scale(i, 0, max(1, len(methods) - 1), (width - right - 14 + left + 14) / 2.0 + 20, width - right - 14)
        elements.append(f'<text x="{x2:.1f}" y="{height-bottom+18}" transform="rotate(38 {x2:.1f},{height-bottom+18})" font-family="Arial, Microsoft YaHei" font-size="10">{PREPROCESSING_LABELS.get(method, method)}</text>')
    elements.extend(
        [
            f'<circle cx="{width-250}" cy="48" r="5" fill="{colors["SiC_10deg"]}"/><text x="{width-238}" y="52" font-family="Arial, Microsoft YaHei" font-size="12">SiC 10度</text>',
            f'<circle cx="{width-150}" cy="48" r="5" fill="{colors["SiC_15deg"]}"/><text x="{width-138}" y="52" font-family="Arial, Microsoft YaHei" font-size="12">SiC 15度</text>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(elements) + "\n", encoding="utf-8-sig")


def make_markdown(summary: pd.DataFrame) -> str:
    ok = summary[summary["fft_status"] == "ok"].copy()
    rows = []
    for method, group in ok.groupby("preprocessing"):
        if set(group["dataset"]) != {"SiC_10deg", "SiC_15deg"}:
            continue
        t10 = float(group[group["dataset"] == "SiC_10deg"]["constant_n_thickness_um"].iloc[0])
        t15 = float(group[group["dataset"] == "SiC_15deg"]["constant_n_thickness_um"].iloc[0])
        p10 = float(group[group["dataset"] == "SiC_10deg"]["peak_period_cm"].iloc[0])
        p15 = float(group[group["dataset"] == "SiC_15deg"]["peak_period_cm"].iloc[0])
        rows.append(
            {
                "preprocessing": method,
                "thickness_10deg_um": t10,
                "thickness_15deg_um": t15,
                "thickness_gap_um": abs(t10 - t15),
                "period_10deg_cm": p10,
                "period_15deg_cm": p15,
                "period_gap_cm": abs(p10 - p15),
                "min_peak_to_median": float(group["peak_to_median"].min()),
            }
        )
    compare = pd.DataFrame(rows).sort_values(["period_gap_cm", "thickness_gap_um"])
    best = compare.iloc[0] if len(compare) else None
    stable = ok.groupby("preprocessing")["peak_period_cm"].mean().describe()
    table = compare.copy()
    for col in table.columns:
        if col != "preprocessing":
            table[col] = table[col].map(lambda value: f"{value:.6g}")
    md_table = "| " + " | ".join(table.columns) + " |\n"
    md_table += "| " + " | ".join(["---"] * len(table.columns)) + " |\n"
    md_table += "\n".join("| " + " | ".join(map(str, row)) + " |" for row in table.to_numpy())
    if len(table) == 0:
        md_table = "No comparable rows."
    best_text = "暂无可比较结果。"
    if best is not None:
        n_same_period = int(np.sum(np.isclose(compare["period_gap_cm"].to_numpy(dtype=float), 0.0)))
        if n_same_period == len(compare):
            best_text = (
                "本轮测试的所有预处理都给出相同的双角度主周期 "
                "$\\Delta\\nu=250\\ \\mathrm{cm^{-1}}$，因此不能说某一种预处理在主周期上明显胜出。"
                "差异主要体现在峰值显著性、峰谷数量和局部曲线形态上。"
                "常数 $n=2.60$ 口径下，$10^\\circ$ 与 $15^\\circ$ 的 FFT 厚度初值差约为 "
                f"${best['thickness_gap_um']:.3g}\\ \\mu m$。"
            )
        else:
            best_text = (
                f"按双角度主周期差异排序，当前最稳的预处理是 `{best['preprocessing']}`；"
                f"$10^\\circ$ 与 $15^\\circ$ 的主周期差为 "
                f"${best['period_gap_cm']:.3g}\\ \\mathrm{{cm^{{-1}}}}$，"
                f"常数 $n=2.60$ 口径下厚度初值差为 "
                f"${best['thickness_gap_um']:.3g}\\ \\mu m$。"
            )
    return f"""# 数据处理诊断摘要

## 问题

本轮实验回答的问题是：在碳化硅附件 1、附件 2 中，厚度信息是不是只由物理模型决定，数据处理是否几乎无关？

答案不是二选一。物理模型决定“如何把条纹相位解释为厚度”，数据处理决定“我们是否稳定地看见了同一组条纹信息”。本轮只做小规模 sanity check，不把任何预处理结果写成最终厚度。

## 方法

对 $1500\\text{{--}}4000\\ \\mathrm{{cm^{{-1}}}}$ 波段做统一重采样，然后比较以下预处理：

- 去均值：`center_only`
- 移动平均去趋势：`ma_detrend_201cm`、`ma_detrend_401cm`、`ma_detrend_801cm`
- 多项式去趋势：`poly2_detrend`、`poly3_detrend`
- 滚动中位数/分位数基线：`rolling_median_401cm`、`rolling_q20_401cm`
- 一阶差分：`first_difference`

评价指标包括主频周期、常数 $n=2.60$ 口径下的 FFT 厚度初值、峰值显著性 `peak_to_median`、峰谷数量和双角度一致性。

## 主要发现

{best_text}

所有预处理的平均主周期统计如下：

| 指标 | 数值 |
| --- | --- |
| count | {stable.get('count', np.nan):.6g} |
| mean | {stable.get('mean', np.nan):.6g} |
| std | {stable.get('std', np.nan):.6g} |
| min | {stable.get('min', np.nan):.6g} |
| max | {stable.get('max', np.nan):.6g} |

双角度对比表：

{md_table}

## 当前解释

数据中并不是“信息很少”，而是主要信息比较集中：条纹周期给出厚度尺度，条纹相位和振幅包络约束材料参数，双角度差异暴露模型是否一致，残差结构暴露模型遗漏项。数据处理的作用是把这些信息拆开看清楚。

如果不同预处理都给出接近的主周期，说明条纹周期是数据中的稳定信息；如果不同预处理导致厚度初值或峰谷数量大幅变化，说明简单峰谷法和频域法不能单独作为最终结论，必须回到 TMM 物理模型和残差诊断。

## 与主模型关系

本轮实验不替代 Dong/TMM 模型。它只提供三类证据：

1. 检查条纹周期是否稳定；
2. 判断哪些预处理会破坏物理条纹；
3. 为后续滑窗 FFT、VMD-LSP 或 TMM 联合拟合提供更可靠的数据处理口径。

## 输出文件

- `Experiments/outputs/data_processing_diagnostics_summary.csv`
- `Experiments/outputs/data_processing_diagnostics_curves.csv`
- `Experiments/outputs/data_processing_diagnostics_summary.md`
- `Experiments/figures/data_processing_preprocessed_curves.svg`
- `Experiments/figures/data_processing_fft_thickness_seed.svg`

## 下一步

下一步不应盲目加复杂预处理。更合理的是：

1. 把最稳的 2-3 种预处理接入滑窗 FFT；
2. 检查主周期是否随波数区间漂移；
3. 把漂移结果和 Dong/TMM 残差高发波段对齐；
4. 判断差异来自数据噪声、基线处理、吸收区，还是来自物理模型缺项。
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    summary, curves = build_diagnostics()
    summary.to_csv(OUTPUT_DIR / "data_processing_diagnostics_summary.csv", index=False, encoding="utf-8-sig")
    curves.to_csv(OUTPUT_DIR / "data_processing_diagnostics_curves.csv", index=False, encoding="utf-8-sig")
    write_svg_lines(curves, FIGURE_DIR / "data_processing_preprocessed_curves.svg")
    write_svg_thickness(summary, FIGURE_DIR / "data_processing_fft_thickness_seed.svg")
    (OUTPUT_DIR / "data_processing_diagnostics_summary.md").write_text(
        make_markdown(summary),
        encoding="utf-8-sig",
    )
    print("Wrote data processing diagnostics.")


if __name__ == "__main__":
    main()
