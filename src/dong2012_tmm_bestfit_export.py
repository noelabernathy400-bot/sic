from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from dong2012_tmm_uncertainty import (
    THICKNESS_GRID_UM,
    affine_fit_fast,
    load_coordinate_final_state,
    prepare_angle_data,
)


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"
FIGURE_DIR = PROJECT / "Experiments" / "figures"

DATASET_LABELS = {
    "SiC_10deg": "SiC 10度",
    "SiC_15deg": "SiC 15度",
}


def _scale(value, vmin, vmax, start, end):
    if np.isclose(vmin, vmax):
        return (start + end) / 2.0
    return start + (float(value) - vmin) / (vmax - vmin) * (end - start)


def _write_svg(path, elements, width, height):
    path.write_text(
        "\n".join(
            [
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                '<rect width="100%" height="100%" fill="white"/>',
                *elements,
                "</svg>",
            ]
        ),
        encoding="utf-8-sig",
    )


def _polyline(points, xmin, xmax, ymin, ymax, left, right, top, bottom, width, height):
    return " ".join(
        f"{_scale(x, xmin, xmax, left, width-right):.2f},{_scale(y, ymin, ymax, height-bottom, top):.2f}"
        for x, y in points
    )


def plot_fit(dataset_name, rows, path):
    width, height = 940, 520
    left, right, top, bottom = 70, 30, 58, 70
    x = rows["wavenumber_cm"].to_numpy(dtype=float)
    observed = rows["observed_reflectance"].to_numpy(dtype=float)
    fitted = rows["fitted_reflectance"].to_numpy(dtype=float)
    xmin, xmax = float(x.min()), float(x.max())
    ymin = float(min(observed.min(), fitted.min()))
    ymax = float(max(observed.max(), fitted.max()))
    pad = (ymax - ymin) * 0.08 or 0.01
    ymin -= pad
    ymax += pad

    obs_points = list(zip(x, observed))
    fit_points = list(zip(x, fitted))
    elems = [
        f'<text x="{width/2:.1f}" y="30" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">Dong/TMM 最佳拟合：{DATASET_LABELS.get(dataset_name, dataset_name)}</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
        f'<text x="{width/2:.1f}" y="{height-20}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">波数 (cm^-1)</text>',
        f'<text x="18" y="{height/2:.1f}" transform="rotate(-90 18,{height/2:.1f})" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">反射率</text>',
    ]
    for tick in [1500, 2000, 2500, 3000, 3500, 4000]:
        x_tick = _scale(tick, xmin, xmax, left, width - right)
        elems.append(f'<line x1="{x_tick:.1f}" y1="{top}" x2="{x_tick:.1f}" y2="{height-bottom}" stroke="#eeeeee"/>')
        elems.append(f'<text x="{x_tick:.1f}" y="{height-bottom+18}" text-anchor="middle" font-family="Arial" font-size="11">{tick}</text>')
    for frac in [0, 0.25, 0.5, 0.75, 1]:
        y_val = ymin + frac * (ymax - ymin)
        y_tick = _scale(y_val, ymin, ymax, height - bottom, top)
        elems.append(f'<line x1="{left}" y1="{y_tick:.1f}" x2="{width-right}" y2="{y_tick:.1f}" stroke="#f2f2f2"/>')
        elems.append(f'<text x="{left-8}" y="{y_tick+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{y_val:.2f}</text>')
    elems.append(
        f'<polyline fill="none" stroke="#1f77b4" stroke-width="1.4" points="{_polyline(obs_points, xmin, xmax, ymin, ymax, left, right, top, bottom, width, height)}"/>'
    )
    elems.append(
        f'<polyline fill="none" stroke="#d62728" stroke-width="1.6" points="{_polyline(fit_points, xmin, xmax, ymin, ymax, left, right, top, bottom, width, height)}"/>'
    )
    elems.append('<line x1="720" y1="70" x2="748" y2="70" stroke="#1f77b4" stroke-width="3"/>')
    elems.append('<text x="756" y="74" font-family="Arial, Microsoft YaHei" font-size="12">实验观测</text>')
    elems.append('<line x1="720" y1="92" x2="748" y2="92" stroke="#d62728" stroke-width="3"/>')
    elems.append('<text x="756" y="96" font-family="Arial, Microsoft YaHei" font-size="12">仿射校准 TMM</text>')
    _write_svg(path, elems, width, height)


def plot_residuals(curves, path):
    width, height = 940, 520
    left, right, top, bottom = 70, 30, 58, 70
    xmin = float(curves["wavenumber_cm"].min())
    xmax = float(curves["wavenumber_cm"].max())
    residual = curves["residual"].to_numpy(dtype=float)
    lim = max(abs(float(residual.min())), abs(float(residual.max()))) * 1.12
    ymin, ymax = -lim, lim
    colors = {"SiC_10deg": "#1f77b4", "SiC_15deg": "#2ca02c"}
    elems = [
        f'<text x="{width/2:.1f}" y="30" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">Dong/TMM 最佳拟合残差</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
        f'<text x="{width/2:.1f}" y="{height-20}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">波数 (cm^-1)</text>',
        f'<text x="18" y="{height/2:.1f}" transform="rotate(-90 18,{height/2:.1f})" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">残差</text>',
    ]
    zero_y = _scale(0.0, ymin, ymax, height - bottom, top)
    elems.append(f'<line x1="{left}" y1="{zero_y:.1f}" x2="{width-right}" y2="{zero_y:.1f}" stroke="#555" stroke-dasharray="4 4"/>')
    for name, group in curves.groupby("dataset"):
        points = list(zip(group["wavenumber_cm"], group["residual"]))
        elems.append(
            f'<polyline fill="none" stroke="{colors.get(name, "#333")}" stroke-width="1.2" points="{_polyline(points, xmin, xmax, ymin, ymax, left, right, top, bottom, width, height)}"/>'
        )
    elems.append('<line x1="720" y1="70" x2="748" y2="70" stroke="#1f77b4" stroke-width="3"/>')
    elems.append('<text x="756" y="74" font-family="Arial, Microsoft YaHei" font-size="12">SiC 10度</text>')
    elems.append('<line x1="720" y1="92" x2="748" y2="92" stroke="#2ca02c" stroke-width="3"/>')
    elems.append('<text x="756" y="96" font-family="Arial, Microsoft YaHei" font-size="12">SiC 15度</text>')
    _write_svg(path, elems, width, height)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)

    scale_state = load_coordinate_final_state()
    configs = [
        {"attachment": "附件1.xlsx", "material": "SiC", "angle_deg": 10.0, "n0": 2.60},
        {"attachment": "附件2.xlsx", "material": "SiC", "angle_deg": 15.0, "n0": 2.60},
    ]
    angle_data = [prepare_angle_data(config, scale_state) for config in configs]
    best_idx = int(np.argmin(np.abs(THICKNESS_GRID_UM - 7.455)))
    best_thickness = float(THICKNESS_GRID_UM[best_idx])

    curve_rows = []
    metric_rows = []
    for item in angle_data:
        model_raw = item["model_matrix"][best_idx]
        rmse, affine_scale, affine_offset, fitted, residual = affine_fit_fast(
            model_raw,
            item["observed"],
        )
        metric_rows.append(
            {
                "dataset": item["dataset"],
                "angle_deg": item["angle_deg"],
                "thickness_um": best_thickness,
                "rmse": rmse,
                "affine_scale": affine_scale,
                "affine_offset": affine_offset,
                "residual_mean": float(np.mean(residual)),
                "residual_std": float(np.std(residual, ddof=1)),
                "residual_max_abs": float(np.max(np.abs(residual))),
            }
        )
        for nu, observed, raw, fit, res in zip(
            item["wavenumber_cm"],
            item["observed"],
            model_raw,
            fitted,
            residual,
        ):
            curve_rows.append(
                {
                    "dataset": item["dataset"],
                    "angle_deg": item["angle_deg"],
                    "thickness_um": best_thickness,
                    "wavenumber_cm": nu,
                    "observed_reflectance": observed,
                    "model_raw_reflectance": raw,
                    "fitted_reflectance": fit,
                    "residual": res,
                }
            )

    curves = pd.DataFrame(curve_rows)
    metrics = pd.DataFrame(metric_rows)
    curves.to_csv(OUTPUT_DIR / "dong2012_tmm_bestfit_curves.csv", index=False, encoding="utf-8-sig")
    metrics.to_csv(OUTPUT_DIR / "dong2012_tmm_bestfit_metrics.csv", index=False, encoding="utf-8-sig")

    for dataset, group in curves.groupby("dataset"):
        plot_fit(dataset, group, FIGURE_DIR / f"paper_fig05_tmm_bestfit_{dataset}.svg")
    plot_residuals(curves, FIGURE_DIR / "paper_fig06_tmm_bestfit_residuals.svg")

    joint_rmse = float(metrics["rmse"].mean())
    summary = [
        "# Dong/TMM best-fit curve export summary",
        "",
        "This script exports the fitted spectral curves at the fixed-parameter representative thickness.",
        "",
        f"- thickness: ${best_thickness:.3f}\\ \\mu m$",
        f"- joint mean RMSE: `{joint_rmse:.8f}`",
        "- material-parameter state: final state from `dong2012_tmm_coordinate_search_chosen.csv`",
        "- fitting band: inherited from `dong2012_tmm_uncertainty.py`, $1500\\text{--}4000\\ \\mathrm{cm}^{-1}$",
        "",
        "## Metrics",
        "",
        "| dataset | RMSE | affine scale | affine offset | residual std | max abs residual |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in metric_rows:
        summary.append(
            "| {dataset} | {rmse:.8f} | {affine_scale:.6f} | {affine_offset:.6f} | {residual_std:.8f} | {residual_max_abs:.8f} |".format(
                **row
            )
        )
    summary.extend(
        [
            "",
            "## Interpretation",
            "",
            "The affine fit is a calibration layer between measured reflectance and model reflectance. Therefore these curves are evidence for phase and line-shape consistency, not proof that absolute reflectance amplitudes are fully explained.",
        ]
    )
    (OUTPUT_DIR / "dong2012_tmm_bestfit_summary.md").write_text(
        "\n".join(summary) + "\n",
        encoding="utf-8-sig",
    )


if __name__ == "__main__":
    main()
