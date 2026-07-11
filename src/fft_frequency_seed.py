from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import spectral_pipeline as sp
from dong2012_dielectric_debug import dong_epsilon_perp, nk_from_epsilon
from dong2012_tmm_coordinate_search import apply_scales


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"
FIGURE_DIR = PROJECT / "Experiments" / "figures"

SIC_CONFIGS = [
    {"attachment_index": 1, "material": "SiC", "angle_deg": 10.0, "n0": 2.60},
    {"attachment_index": 2, "material": "SiC", "angle_deg": 15.0, "n0": 2.60},
]

BANDS = [
    ("1500-4000", 1500.0, 4000.0),
    ("1500-2500", 1500.0, 2500.0),
    ("2500-4000", 2500.0, 4000.0),
    ("1500-2000", 1500.0, 2000.0),
    ("2000-2500", 2000.0, 2500.0),
    ("2500-3000", 2500.0, 3000.0),
    ("3000-3500", 3000.0, 3500.0),
    ("3500-4000", 3500.0, 4000.0),
]

TARGET_THICKNESS_RANGE_UM = (3.0, 12.0)
UNIFORM_STEP_CM = 1.0
TREND_WINDOW_CM = 401.0


def read_attachment_by_index(index: int) -> pd.DataFrame:
    candidates = sorted(sp.attachment_dir().glob("*.xlsx"))
    matches = [path for path in candidates if str(index) in path.stem]
    if not matches:
        raise FileNotFoundError(f"Could not find attachment {index} in {sp.attachment_dir()}.")
    raw = pd.read_excel(matches[0])
    return pd.DataFrame(
        {
            "wavenumber_cm": raw.iloc[:, 0].astype(float),
            "reflectance_pct": raw.iloc[:, 1].astype(float),
        }
    )


def read_band(config: dict, low: float, high: float) -> tuple[np.ndarray, np.ndarray]:
    df = read_attachment_by_index(int(config["attachment_index"]))
    nu = df["wavenumber_cm"].to_numpy(dtype=float)
    reflectance = df["reflectance_pct"].to_numpy(dtype=float) / 100.0
    order = np.argsort(nu)
    nu = nu[order]
    reflectance = reflectance[order]
    mask = (nu >= low) & (nu <= high)
    return nu[mask], reflectance[mask]


def resample_uniform_wavenumber(
    nu: np.ndarray,
    reflectance: np.ndarray,
    step_cm: float = UNIFORM_STEP_CM,
) -> tuple[np.ndarray, np.ndarray]:
    if len(nu) < 5:
        return np.array([]), np.array([])
    grid = np.arange(float(nu.min()), float(nu.max()) + 0.5 * step_cm, step_cm)
    signal = np.interp(grid, nu, reflectance)
    return grid, signal


def detrend_signal(signal: np.ndarray, step_cm: float = UNIFORM_STEP_CM) -> np.ndarray:
    window = max(5, int(round(TREND_WINDOW_CM / step_cm)))
    if window % 2 == 0:
        window += 1
    window = min(window, len(signal) // 2 * 2 + 1)
    if window < 5:
        return signal - np.mean(signal)
    trend = sp.moving_average(signal, window)
    residual = signal - trend
    return residual - np.mean(residual)


def load_constrained_state() -> dict[str, float] | None:
    path = OUTPUT_DIR / "dong2012_tmm_constrained_refinement_chosen.csv"
    if not path.exists():
        return None
    row = pd.read_csv(path).iloc[-1]
    keys = [
        "epi_nu_p_scale",
        "sub_nu_p_scale",
        "epi_gamma_scale",
        "sub_gamma_scale",
        "epi_gamma_l_scale",
        "epi_gamma_t_scale",
        "sub_gamma_l_scale",
        "sub_gamma_t_scale",
    ]
    return {key: float(row[key]) for key in keys}


def effective_n_dong_for_band(low: float, high: float) -> tuple[float, float, float]:
    state = load_constrained_state()
    if state is None:
        return np.nan, np.nan, np.nan
    grid = np.linspace(low, high, 250)
    epi_params = apply_scales("epilayer", state)
    n_complex = nk_from_epsilon(dong_epsilon_perp(grid, epi_params))
    return (
        float(np.mean(np.real(n_complex))),
        float(np.mean(np.imag(n_complex))),
        float(np.max(np.imag(n_complex))),
    )


def effective_n_for_band(
    low: float,
    high: float,
    fallback_n: float,
) -> tuple[float, float, float]:
    try:
        nk = sp.load_larruquert_sic_nk()
        grid = np.linspace(low, high, 250)
        n, k = sp.interpolate_nk(nk, grid)
        return float(np.mean(n)), float(np.mean(k)), float(np.max(k))
    except Exception:
        return float(fallback_n), np.nan, np.nan


def frequency_bounds_for_thickness(
    n_eff: float,
    angle_deg: float,
    thickness_range_um: tuple[float, float] = TARGET_THICKNESS_RANGE_UM,
) -> tuple[float, float]:
    theta = np.deg2rad(angle_deg)
    optical_factor = np.sqrt(n_eff**2 - np.sin(theta) ** 2)
    d_min, d_max = thickness_range_um
    f_min = 2.0 * d_min * optical_factor / 10000.0
    f_max = 2.0 * d_max * optical_factor / 10000.0
    return float(f_min), float(f_max)


def thickness_from_frequency(
    frequency_cycles_per_cm: float,
    n_eff: float,
    angle_deg: float,
) -> float:
    theta = np.deg2rad(angle_deg)
    optical_factor = np.sqrt(n_eff**2 - np.sin(theta) ** 2)
    return float(10000.0 * frequency_cycles_per_cm / (2.0 * optical_factor))


def estimate_fft_seed(
    grid: np.ndarray,
    signal: np.ndarray,
    n_eff: float,
    angle_deg: float,
) -> dict:
    if not np.isfinite(n_eff) or n_eff <= 1.0:
        return {"status": "invalid_n_eff", "n_uniform_points": len(grid)}
    if len(grid) < 32:
        return {"status": "too_few_points", "n_uniform_points": len(grid)}
    step = float(np.median(np.diff(grid)))
    detrended = detrend_signal(signal, step)
    window = np.hanning(len(detrended))
    spectrum = np.abs(np.fft.rfft(detrended * window))
    freq = np.fft.rfftfreq(len(detrended), d=step)
    f_min, f_max = frequency_bounds_for_thickness(n_eff, angle_deg)
    mask = (freq >= f_min) & (freq <= f_max)
    mask[0] = False
    if np.count_nonzero(mask) < 3:
        return {
            "status": "frequency_grid_too_coarse",
            "n_uniform_points": len(grid),
            "fft_resolution": float(freq[1] - freq[0]) if len(freq) > 1 else np.nan,
            "target_frequency_min": f_min,
            "target_frequency_max": f_max,
        }
    idxs = np.where(mask)[0]
    local_spectrum = spectrum[idxs]
    peak_local = int(np.argmax(local_spectrum))
    peak_idx = int(idxs[peak_local])
    peak_frequency = float(freq[peak_idx])
    peak_amplitude = float(spectrum[peak_idx])
    sorted_amp = np.sort(local_spectrum)
    second_amplitude = float(sorted_amp[-2]) if len(sorted_amp) >= 2 else np.nan
    median_amplitude = float(np.median(local_spectrum))
    energy_fraction = float(np.sum(local_spectrum**2) / np.sum(spectrum[1:] ** 2))
    return {
        "status": "ok",
        "n_uniform_points": len(grid),
        "fft_resolution": float(freq[1] - freq[0]) if len(freq) > 1 else np.nan,
        "target_frequency_min": f_min,
        "target_frequency_max": f_max,
        "peak_frequency_cycles_per_cm": peak_frequency,
        "peak_period_cm": float(1.0 / peak_frequency),
        "thickness_um": thickness_from_frequency(peak_frequency, n_eff, angle_deg),
        "peak_amplitude": peak_amplitude,
        "second_amplitude": second_amplitude,
        "peak_to_second": float(peak_amplitude / second_amplitude) if second_amplitude else np.nan,
        "peak_to_median": float(peak_amplitude / median_amplitude) if median_amplitude else np.nan,
        "target_band_energy_fraction": energy_fraction,
        "detrended_std": float(np.std(detrended, ddof=1)),
    }


def run_analysis() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    spectrum_rows = []
    for config in SIC_CONFIGS:
        for band_name, low, high in BANDS:
            nu, reflectance = read_band(config, low, high)
            grid, signal = resample_uniform_wavenumber(nu, reflectance)
            for n_model in ["constant_n", "larruquert_n_eff", "dong_constrained_n_eff"]:
                if n_model == "constant_n":
                    n_eff = float(config["n0"])
                    k_mean = np.nan
                    k_max = np.nan
                elif n_model == "dong_constrained_n_eff":
                    n_eff, k_mean, k_max = effective_n_dong_for_band(low, high)
                else:
                    n_eff, k_mean, k_max = effective_n_for_band(low, high, float(config["n0"]))
                result = estimate_fft_seed(grid, signal, n_eff, config["angle_deg"])
                rows.append(
                    {
                        "dataset": f'{config["material"]}_{int(config["angle_deg"])}deg',
                        "angle_deg": float(config["angle_deg"]),
                        "band": band_name,
                        "band_min_cm": low,
                        "band_max_cm": high,
                        "band_width_cm": high - low,
                        "n_model": n_model,
                        "n_eff": n_eff,
                        "k_mean": k_mean,
                        "k_max": k_max,
                        **result,
                    }
                )
            if len(grid) >= 32:
                detrended = detrend_signal(signal, UNIFORM_STEP_CM)
                window = np.hanning(len(detrended))
                spectrum = np.abs(np.fft.rfft(detrended * window))
                freq = np.fft.rfftfreq(len(detrended), d=UNIFORM_STEP_CM)
                for f, amp in zip(freq[1:], spectrum[1:]):
                    if 0.0005 <= f <= 0.008:
                        spectrum_rows.append(
                            {
                                "dataset": f'{config["material"]}_{int(config["angle_deg"])}deg',
                                "angle_deg": float(config["angle_deg"]),
                                "band": band_name,
                                "frequency_cycles_per_cm": float(f),
                                "amplitude": float(amp),
                            }
                        )
    return pd.DataFrame(rows), pd.DataFrame(spectrum_rows)


def _scale(value, vmin, vmax, start, end):
    if np.isclose(vmin, vmax):
        return (start + end) / 2.0
    return start + (float(value) - vmin) / (vmax - vmin) * (end - start)


def _write_svg(path: Path, elements: list[str], width: int, height: int) -> None:
    path.write_text(
        "\n".join(
            [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                '<rect width="100%" height="100%" fill="white"/>',
                *elements,
                "</svg>",
            ]
        )
        + "\n",
        encoding="utf-8-sig",
    )


def plot_thickness_by_band(results: pd.DataFrame, path: Path) -> None:
    selected = results[(results["status"] == "ok") & (results["n_model"] == "larruquert_n_eff")].copy()
    selected = selected[selected["band"].isin(["1500-4000", "1500-2500", "2500-4000"])]
    width, height = 980, 540
    left, right, top, bottom = 90, 36, 58, 96
    ymin = float(selected["thickness_um"].min()) - 0.6
    ymax = float(selected["thickness_um"].max()) + 0.6
    colors = {"SiC_10deg": "#1f77b4", "SiC_15deg": "#2ca02c"}
    bands = ["1500-4000", "1500-2500", "2500-4000"]
    elements = [
        f'<text x="{width/2:.1f}" y="30" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">FFT frequency thickness seed</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
        f'<text x="20" y="{height/2:.1f}" transform="rotate(-90 20,{height/2:.1f})" text-anchor="middle" font-family="Arial" font-size="13">Thickness (um)</text>',
    ]
    for y_value in np.linspace(np.floor(ymin), np.ceil(ymax), 7):
        y = _scale(y_value, ymin, ymax, height - bottom, top)
        elements.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#f2f2f2"/>')
        elements.append(f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{y_value:.1f}</text>')
    target_low = _scale(7.4, ymin, ymax, height - bottom, top)
    target_high = _scale(7.6, ymin, ymax, height - bottom, top)
    elements.append(f'<rect x="{left}" y="{target_high:.1f}" width="{width-left-right}" height="{target_low-target_high:.1f}" fill="#f6d7a7" opacity="0.45"/>')
    x_positions = {band: left + 135 + idx * 240 for idx, band in enumerate(bands)}
    for band, x in x_positions.items():
        elements.append(f'<text x="{x:.1f}" y="{height-bottom+30}" text-anchor="middle" font-family="Arial" font-size="12">{band}</text>')
    for _, row in selected.iterrows():
        x = x_positions[row["band"]] + (-18 if row["dataset"] == "SiC_10deg" else 18)
        y = _scale(row["thickness_um"], ymin, ymax, height - bottom, top)
        color = colors.get(row["dataset"], "#333")
        elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{color}"/>')
        elements.append(f'<text x="{x:.1f}" y="{y-10:.1f}" text-anchor="middle" font-family="Arial" font-size="10">{row["thickness_um"]:.2f}</text>')
    elements.append('<rect x="720" y="70" width="18" height="12" fill="#1f77b4"/>')
    elements.append('<text x="746" y="81" font-family="Arial" font-size="12">SiC_10deg</text>')
    elements.append('<rect x="720" y="94" width="18" height="12" fill="#2ca02c"/>')
    elements.append('<text x="746" y="105" font-family="Arial" font-size="12">SiC_15deg</text>')
    elements.append('<rect x="720" y="118" width="18" height="12" fill="#f6d7a7" opacity="0.65"/>')
    elements.append('<text x="746" y="129" font-family="Arial" font-size="12">7.4-7.6 um</text>')
    _write_svg(path, elements, width, height)


def write_summary(results: pd.DataFrame) -> None:
    ok = results[results["status"] == "ok"].copy()
    main = ok[(ok["n_model"] == "larruquert_n_eff") & (ok["band"].isin(["1500-4000", "1500-2500", "2500-4000"]))]
    dong = ok[(ok["n_model"] == "dong_constrained_n_eff") & (ok["band"].isin(["1500-4000", "1500-2500", "2500-4000"]))]
    constant = ok[(ok["n_model"] == "constant_n") & (ok["band"].isin(["1500-4000", "1500-2500", "2500-4000"]))]
    lines = [
        "# FFT 频域厚度初值诊断",
        "",
        "## 研究问题",
        "",
        "本脚本检查反射谱条纹的主周期是否独立支持当前 Dong/TMM 候选区间：",
        "",
        "$$",
        "d\\approx7.4\\text{--}7.6\\ \\mu m.",
        "$$",
        "",
        "频域结果只作为初值和真实性检查，不作为最终厚度。原因是 FFT 假设条纹周期近似平稳，而实际 $n(\\nu)$、$k(\\nu)$、吸收区和背景都会改变谱线形态。",
        "",
        "## 换算公式",
        "",
        "若主频为 $f$，其单位是 cycles per $\\mathrm{cm}^{-1}$，则条纹周期为",
        "",
        "$$",
        "\\Delta\\nu=\\frac{1}{f}.",
        "$$",
        "",
        "在近似有效折射率 $n_{\\mathrm{eff}}$ 下，厚度初值为",
        "",
        "$$",
        "d_{\\mathrm{FFT}}",
        "\\approx",
        "\\frac{10000 f}{2\\sqrt{n_{\\mathrm{eff}}^2-\\sin^2\\theta}}.",
        "$$",
        "",
        "这里 $d_{\\mathrm{FFT}}$ 的单位是 $\\mu m$。",
        "",
        "## 主波段结果：Larruquert $n_{\\mathrm{eff}}$ 口径",
        "",
        "| 数据 | 波段 | $n_{\\mathrm{eff}}$ | 主周期 $\\Delta\\nu$ | $d_{\\mathrm{FFT}}$ | 峰/次峰 | 峰/中位数 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in main.sort_values(["dataset", "band"]).iterrows():
        lines.append(
            "| {dataset} | {band} | `{n_eff:.4f}` | `{peak_period_cm:.2f}` | ${thickness_um:.3f}\\ \\mu m$ | `{peak_to_second:.3f}` | `{peak_to_median:.3f}` |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## 对照：Dong 受约束模型 $n_{\\mathrm{eff}}$ 口径",
            "",
            "| 数据 | 波段 | $n_{\\mathrm{eff}}$ | $k_{\\mathrm{mean}}$ | 主周期 $\\Delta\\nu$ | $d_{\\mathrm{FFT}}$ | 峰/次峰 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in dong.sort_values(["dataset", "band"]).iterrows():
        lines.append(
            "| {dataset} | {band} | `{n_eff:.4f}` | `{k_mean:.5f}` | `{peak_period_cm:.2f}` | ${thickness_um:.3f}\\ \\mu m$ | `{peak_to_second:.3f}` |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## 对照：常数 $n=2.60$ 口径",
            "",
            "| 数据 | 波段 | 主周期 $\\Delta\\nu$ | $d_{\\mathrm{FFT}}$ | 峰/次峰 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in constant.sort_values(["dataset", "band"]).iterrows():
        lines.append(
            "| {dataset} | {band} | `{peak_period_cm:.2f}` | ${thickness_um:.3f}\\ \\mu m$ | `{peak_to_second:.3f}` |".format(
                **row
            )
        )
    if len(main):
        grouped = main.groupby("dataset")["thickness_um"].agg(["mean", "std", "min", "max"]).reset_index()
        lines.extend(
            [
                "",
                "## 三个主波段的稳定性摘要",
                "",
                "| 数据 | 平均厚度 | 标准差 | 最小值 | 最大值 |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for _, row in grouped.iterrows():
            lines.append(
                "| {dataset} | ${mean:.3f}\\ \\mu m$ | `{std:.3f}` | ${min:.3f}\\ \\mu m$ | ${max:.3f}\\ \\mu m$ |".format(
                    **row
                )
            )
    lines.extend(
        [
            "",
            "## 初步解释",
            "",
            "- 当前 FFT 主周期非常稳定，约为 $\\Delta\\nu\\approx250\\ \\mathrm{cm}^{-1}$，这说明谱线确实有清晰的周期结构。",
            "- 但频域厚度不直接支持单一厚度值：Larruquert $n_{\\mathrm{eff}}$ 口径约为 $6.5\\ \\mu m$，常数 $n=2.60$ 口径约为 $7.7\\ \\mu m$，Dong 受约束 $n_{\\mathrm{eff}}$ 口径约为 $8.0\\ \\mu m$。",
            "- 因此当前更准确的判断是：FFT 支持“条纹周期稳定”，但暴露了厚度换算对折射率模型高度敏感；它尚不能直接证明 $d\\approx7.4\\text{--}7.6\\ \\mu m$。",
            "- 如果窄波段结果跳动较大，不应立即否定厚度候选；窄窗口频率分辨率较低，且可包含不足两个稳定周期。",
            "- 峰/次峰越接近 $1$，说明频域主峰不够唯一，不能把该波段当成强证据。",
            "",
            "## 输出文件",
            "",
            "- `Experiments/outputs/fft_frequency_seed_results.csv`",
            "- `Experiments/outputs/fft_frequency_seed_spectrum.csv`",
            "- `Experiments/figures/fft_frequency_seed_thickness_by_band.svg`",
        ]
    )
    (OUTPUT_DIR / "fft_frequency_seed_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8-sig",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    results, spectrum = run_analysis()
    results.to_csv(OUTPUT_DIR / "fft_frequency_seed_results.csv", index=False, encoding="utf-8-sig")
    spectrum.to_csv(OUTPUT_DIR / "fft_frequency_seed_spectrum.csv", index=False, encoding="utf-8-sig")
    plot_thickness_by_band(results, FIGURE_DIR / "fft_frequency_seed_thickness_by_band.svg")
    write_summary(results)


if __name__ == "__main__":
    main()
