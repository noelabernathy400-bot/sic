from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from dong2012_tmm_local_refinement import CONFIGS
from dong2012_tmm_uncertainty import (
    THICKNESS_GRID_UM,
    affine_fit_fast,
    prepare_angle_data,
)


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"
FIGURE_DIR = PROJECT / "Experiments" / "figures"

DATASET_LABELS = {
    "SiC_10deg": "SiC 10度",
    "SiC_15deg": "SiC 15度",
}

STATE_KEYS = [
    "epi_nu_p_scale",
    "sub_nu_p_scale",
    "epi_gamma_scale",
    "sub_gamma_scale",
    "epi_gamma_l_scale",
    "epi_gamma_t_scale",
    "sub_gamma_l_scale",
    "sub_gamma_t_scale",
]

BANDS = [
    ("1500-2000", 1500.0, 2000.0),
    ("2000-2500", 2000.0, 2500.0),
    ("2500-3000", 2500.0, 3000.0),
    ("3000-3500", 3000.0, 3500.0),
    ("3500-4000", 3500.0, 4000.0),
    ("1500-2500", 1500.0, 2500.0),
    ("2500-4000", 2500.0, 4000.0),
    ("1500-4000", 1500.0, 4000.0),
]


def load_constrained_final_state() -> tuple[dict[str, float], float, float]:
    path = OUTPUT_DIR / "dong2012_tmm_constrained_refinement_chosen.csv"
    if not path.exists():
        raise FileNotFoundError(
            "Run dong2012_tmm_constrained_refinement.py before residual diagnostics."
        )
    chosen = pd.read_csv(path)
    final = chosen.iloc[-1]
    state = {key: float(final[key]) for key in STATE_KEYS}
    thickness = float(final["joint_best_thickness_um"])
    joint_rmse = float(final["joint_mean_rmse"])
    return state, thickness, joint_rmse


def nearest_thickness_index(thickness_um: float) -> int:
    return int(np.argmin(np.abs(THICKNESS_GRID_UM - thickness_um)))


def lag1_autocorrelation(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    if len(values) < 3:
        return np.nan
    centered = values - values.mean()
    denom = float(np.dot(centered, centered))
    if denom <= 0:
        return np.nan
    return float(np.dot(centered[:-1], centered[1:]) / denom)


def sign_run_stats(values: np.ndarray) -> tuple[int, int, float]:
    signs = np.sign(np.asarray(values, dtype=float))
    signs = signs[signs != 0]
    if len(signs) == 0:
        return 0, 0, np.nan
    runs = 1
    current = 1
    max_run = 1
    for prev, curr in zip(signs[:-1], signs[1:]):
        if curr == prev:
            current += 1
        else:
            runs += 1
            max_run = max(max_run, current)
            current = 1
    max_run = max(max_run, current)
    positive_fraction = float(np.mean(signs > 0))
    return runs, max_run, positive_fraction


def metrics_for_values(values: np.ndarray) -> dict[str, float]:
    values = np.asarray(values, dtype=float)
    runs, max_run, positive_fraction = sign_run_stats(values)
    return {
        "n_points": int(len(values)),
        "mean_residual": float(np.mean(values)),
        "rmse": float(np.sqrt(np.mean(values**2))),
        "mae": float(np.mean(np.abs(values))),
        "std_residual": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        "max_abs_residual": float(np.max(np.abs(values))),
        "p95_abs_residual": float(np.quantile(np.abs(values), 0.95)),
        "lag1_autocorr": lag1_autocorrelation(values),
        "sign_runs": int(runs),
        "max_sign_run": int(max_run),
        "positive_fraction": positive_fraction,
    }


def build_residual_curves(
    state: dict[str, float],
    thickness_um: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    idx = nearest_thickness_index(thickness_um)
    actual_thickness = float(THICKNESS_GRID_UM[idx])
    angle_data = [prepare_angle_data(config, state) for config in CONFIGS]
    curve_rows = []
    angle_rows = []
    for item in angle_data:
        model_raw = item["model_matrix"][idx]
        rmse, scale, offset, fitted, residual = affine_fit_fast(
            model_raw,
            item["observed"],
        )
        angle_metric = {
            "dataset": item["dataset"],
            "angle_deg": float(item["angle_deg"]),
            "thickness_um": actual_thickness,
            "affine_scale": float(scale),
            "affine_offset": float(offset),
            **metrics_for_values(residual),
        }
        angle_metric["rmse_from_fit"] = float(rmse)
        angle_rows.append(angle_metric)
        for nu, obs, raw, fit, res in zip(
            item["wavenumber_cm"],
            item["observed"],
            model_raw,
            fitted,
            residual,
        ):
            curve_rows.append(
                {
                    "dataset": item["dataset"],
                    "angle_deg": float(item["angle_deg"]),
                    "thickness_um": actual_thickness,
                    "wavenumber_cm": float(nu),
                    "observed_reflectance": float(obs),
                    "model_raw_reflectance": float(raw),
                    "fitted_reflectance": float(fit),
                    "residual": float(res),
                }
            )
    return pd.DataFrame(curve_rows), pd.DataFrame(angle_rows)


def build_band_metrics(curves: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for dataset, group in curves.groupby("dataset"):
        for band_name, low, high in BANDS:
            mask = (group["wavenumber_cm"] >= low) & (group["wavenumber_cm"] <= high)
            selected = group.loc[mask, "residual"].to_numpy(dtype=float)
            if len(selected) == 0:
                continue
            rows.append(
                {
                    "dataset": dataset,
                    "angle_deg": float(group["angle_deg"].iloc[0]),
                    "band": band_name,
                    "band_min_cm": low,
                    "band_max_cm": high,
                    **metrics_for_values(selected),
                }
            )
    return pd.DataFrame(rows)


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


def _polyline(points, xmin, xmax, ymin, ymax, left, right, top, bottom, width, height):
    return " ".join(
        f"{_scale(x, xmin, xmax, left, width-right):.2f},{_scale(y, ymin, ymax, height-bottom, top):.2f}"
        for x, y in points
    )


def plot_residual_curves(curves: pd.DataFrame, path: Path) -> None:
    width, height = 980, 540
    left, right, top, bottom = 76, 32, 58, 72
    xmin = float(curves["wavenumber_cm"].min())
    xmax = float(curves["wavenumber_cm"].max())
    residual = curves["residual"].to_numpy(dtype=float)
    lim = max(abs(float(residual.min())), abs(float(residual.max()))) * 1.12
    ymin, ymax = -lim, lim
    colors = {"SiC_10deg": "#1f77b4", "SiC_15deg": "#2ca02c"}
    elements = [
        f'<text x="{width/2:.1f}" y="30" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">受约束 Dong/TMM 残差诊断</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
        f'<text x="{width/2:.1f}" y="{height-20}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">波数 (cm^-1)</text>',
        f'<text x="18" y="{height/2:.1f}" transform="rotate(-90 18,{height/2:.1f})" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">残差</text>',
    ]
    zero_y = _scale(0.0, ymin, ymax, height - bottom, top)
    elements.append(f'<line x1="{left}" y1="{zero_y:.1f}" x2="{width-right}" y2="{zero_y:.1f}" stroke="#555" stroke-dasharray="4 4"/>')
    for tick in [1500, 2000, 2500, 3000, 3500, 4000]:
        x_tick = _scale(tick, xmin, xmax, left, width - right)
        elements.append(f'<line x1="{x_tick:.1f}" y1="{top}" x2="{x_tick:.1f}" y2="{height-bottom}" stroke="#eeeeee"/>')
        elements.append(f'<text x="{x_tick:.1f}" y="{height-bottom+18}" text-anchor="middle" font-family="Arial" font-size="11">{tick}</text>')
    for name, group in curves.groupby("dataset"):
        points = list(zip(group["wavenumber_cm"], group["residual"]))
        elements.append(
            f'<polyline fill="none" stroke="{colors.get(name, "#333")}" stroke-width="1.2" points="{_polyline(points, xmin, xmax, ymin, ymax, left, right, top, bottom, width, height)}"/>'
        )
    elements.append('<line x1="730" y1="70" x2="758" y2="70" stroke="#1f77b4" stroke-width="3"/>')
    elements.append('<text x="766" y="74" font-family="Arial, Microsoft YaHei" font-size="12">SiC 10度</text>')
    elements.append('<line x1="730" y1="94" x2="758" y2="94" stroke="#2ca02c" stroke-width="3"/>')
    elements.append('<text x="766" y="98" font-family="Arial, Microsoft YaHei" font-size="12">SiC 15度</text>')
    _write_svg(path, elements, width, height)


def plot_band_rmse(band_metrics: pd.DataFrame, path: Path) -> None:
    selected = band_metrics[band_metrics["band"].isin([band[0] for band in BANDS[:5]])].copy()
    datasets = list(selected["dataset"].drop_duplicates())
    bands = [band[0] for band in BANDS[:5]]
    width, height = 980, 540
    left, right, top, bottom = 86, 34, 58, 92
    ymax = float(selected["rmse"].max()) * 1.18
    bar_w = 28
    group_gap = 70
    band_gap = 130
    colors = {"SiC_10deg": "#1f77b4", "SiC_15deg": "#2ca02c"}
    elements = [
        f'<text x="{width/2:.1f}" y="30" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">分波段残差 RMSE</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
        f'<text x="20" y="{height/2:.1f}" transform="rotate(-90 20,{height/2:.1f})" text-anchor="middle" font-family="Arial" font-size="13">RMSE</text>',
    ]
    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        value = ymax * frac
        y = _scale(value, 0.0, ymax, height - bottom, top)
        elements.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#f2f2f2"/>')
        elements.append(f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{value:.4f}</text>')
    x0 = left + 55
    for band_idx, band in enumerate(bands):
        center = x0 + band_idx * (2 * bar_w + group_gap + band_gap)
        elements.append(f'<text x="{center+bar_w:.1f}" y="{height-bottom+28}" text-anchor="middle" font-family="Arial" font-size="11">{band}</text>')
        for dataset_idx, dataset in enumerate(datasets):
            row = selected[(selected["band"] == band) & (selected["dataset"] == dataset)].iloc[0]
            value = float(row["rmse"])
            x = center + dataset_idx * (bar_w + 8)
            y = _scale(value, 0.0, ymax, height - bottom, top)
            h = height - bottom - y
            elements.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}" fill="{colors.get(dataset, "#555")}"/>')
    elements.append('<rect x="730" y="70" width="18" height="12" fill="#1f77b4"/>')
    elements.append('<text x="756" y="81" font-family="Arial" font-size="12">SiC_10deg</text>')
    elements.append('<rect x="730" y="94" width="18" height="12" fill="#2ca02c"/>')
    elements.append('<text x="756" y="105" font-family="Arial" font-size="12">SiC_15deg</text>')
    _write_svg(path, elements, width, height)


def write_summary(
    state: dict[str, float],
    thickness_um: float,
    expected_joint_rmse: float,
    angle_metrics: pd.DataFrame,
    band_metrics: pd.DataFrame,
) -> None:
    full_band = band_metrics[band_metrics["band"] == "1500-4000"].copy()
    worst_rows = (
        band_metrics[~band_metrics["band"].eq("1500-4000")]
        .sort_values("rmse", ascending=False)
        .head(6)
    )
    lines = [
        "# Dong/TMM 受约束最终状态残差诊断",
        "",
        "## 研究问题",
        "",
        "本诊断不是重新寻找更小 RMSE，而是检查当前受约束最终状态下残差是否具有结构性模式。数学上看的是：",
        "",
        "$$",
        "r_i(\\nu)=R_{\\mathrm{obs},i}(\\nu)-R_{\\mathrm{model},i}(\\nu),",
        "\\qquad",
        "i\\in\\{10^\\circ,15^\\circ\\}.",
        "$$",
        "",
        "如果残差在某些波段连续偏正或偏负，说明当前 TMM/材料参数/背景校正仍有未解释结构。",
        "",
        "## 使用的状态",
        "",
        f"- 厚度：${thickness_um:.3f}\\ \\mu m$",
        f"- 受约束优化记录的 joint RMSE：`{expected_joint_rmse:.8f}`",
        "- 参数状态来自 `dong2012_tmm_constrained_refinement_chosen.csv` 的最后一行。",
        "",
        "| 参数 | 数值 |",
        "| --- | --- |",
    ]
    for key, value in state.items():
        lines.append(f"| `{key}` | `{value:.6f}` |")
    lines.extend(
        [
            "",
            "## 分角度整体指标",
            "",
            "| 数据 | RMSE | MAE | 最大绝对残差 | 95% 绝对残差分位 | 一阶自相关 | 最大同号连续段 | 正残差占比 |",
            "| --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in angle_metrics.iterrows():
        lines.append(
            "| {dataset} | `{rmse:.8f}` | `{mae:.8f}` | `{max_abs_residual:.8f}` | `{p95_abs_residual:.8f}` | `{lag1_autocorr:.4f}` | `{max_sign_run}` | `{positive_fraction:.3f}` |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## 全波段对照",
            "",
            "| 数据 | 全波段 RMSE | 全波段均值残差 | 一阶自相关 | 最大同号连续段 |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in full_band.iterrows():
        lines.append(
            "| {dataset} | `{rmse:.8f}` | `{mean_residual:.8e}` | `{lag1_autocorr:.4f}` | `{max_sign_run}` |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## 残差最强的波段",
            "",
            "| 数据 | 波段 | RMSE | MAE | 均值残差 | 一阶自相关 | 最大同号连续段 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in worst_rows.iterrows():
        lines.append(
            "| {dataset} | {band} | `{rmse:.8f}` | `{mae:.8f}` | `{mean_residual:.8e}` | `{lag1_autocorr:.4f}` | `{max_sign_run}` |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## 初步解释",
            "",
            "本输出只说明残差结构，不直接证明某个物理机制。阅读时应遵守以下口径：",
            "",
            "- 若某个波段 RMSE 明显偏大，优先检查该波段是否受吸收、基线、采样或材料模型不匹配影响。",
            "- 若一阶自相关较高或最大同号连续段很长，说明残差不是完全随机噪声，当前模型仍有系统误差。",
            "- 若 $15^\\circ$ 的残差持续强于 $10^\\circ$，后续论文必须诚实写出角度一致性尚未完全闭合。",
            "",
            "## 输出文件",
            "",
            "- `Experiments/outputs/residual_diagnostics_curves.csv`",
            "- `Experiments/outputs/residual_diagnostics_angle_metrics.csv`",
            "- `Experiments/outputs/residual_diagnostics_band_metrics.csv`",
            "- `Experiments/figures/residual_diagnostics_angle_residuals.svg`",
            "- `Experiments/figures/residual_diagnostics_band_rmse.svg`",
        ]
    )
    (OUTPUT_DIR / "residual_diagnostics_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8-sig",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    state, thickness_um, joint_rmse = load_constrained_final_state()
    curves, angle_metrics = build_residual_curves(state, thickness_um)
    band_metrics = build_band_metrics(curves)
    curves.to_csv(OUTPUT_DIR / "residual_diagnostics_curves.csv", index=False, encoding="utf-8-sig")
    angle_metrics.to_csv(OUTPUT_DIR / "residual_diagnostics_angle_metrics.csv", index=False, encoding="utf-8-sig")
    band_metrics.to_csv(OUTPUT_DIR / "residual_diagnostics_band_metrics.csv", index=False, encoding="utf-8-sig")
    plot_residual_curves(curves, FIGURE_DIR / "residual_diagnostics_angle_residuals.svg")
    plot_band_rmse(band_metrics, FIGURE_DIR / "residual_diagnostics_band_rmse.svg")
    write_summary(state, thickness_um, joint_rmse, angle_metrics, band_metrics)


if __name__ == "__main__":
    main()
