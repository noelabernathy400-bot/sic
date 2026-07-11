from pathlib import Path

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT / "Sources"
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"
FIGURE_DIR = PROJECT / "Experiments" / "figures"
LARRUQUERT_YML = SOURCE_DIR / "Literature" / "SiC_Larruquert_refractiveindex.yml"

DATASETS = [
    {"attachment": "附件1.xlsx", "material": "SiC", "angle_deg": 10.0, "n0": 2.60},
    {"attachment": "附件2.xlsx", "material": "SiC", "angle_deg": 15.0, "n0": 2.60},
    {"attachment": "附件3.xlsx", "material": "Si", "angle_deg": 10.0, "n0": 3.42},
    {"attachment": "附件4.xlsx", "material": "Si", "angle_deg": 15.0, "n0": 3.42},
]


def attachment_dir():
    direct = SOURCE_DIR / "附件"
    if direct.exists():
        return direct
    dirs = [p for p in SOURCE_DIR.iterdir() if p.is_dir() and p.name != "Literature"]
    if not dirs:
        raise FileNotFoundError("No attachment directory under Sources.")
    return dirs[0]


def read_dataset(config):
    path = attachment_dir() / config["attachment"]
    df = pd.read_excel(path)
    return pd.DataFrame(
        {
            "wavenumber_cm": df.iloc[:, 0].astype(float),
            "reflectance_pct": df.iloc[:, 1].astype(float),
        }
    )


def moving_average(y, window):
    window = int(window)
    if window % 2 == 0:
        window += 1
    window = max(3, min(window, len(y) // 2 * 2 + 1))
    return np.convolve(y, np.ones(window) / window, mode="same")


def separated_extrema(x, y, window=101, min_spacing_cm=240.0):
    smooth = moving_average(y, window)
    max_candidates = np.where((smooth[1:-1] > smooth[:-2]) & (smooth[1:-1] > smooth[2:]))[0] + 1
    min_candidates = np.where((smooth[1:-1] < smooth[:-2]) & (smooth[1:-1] < smooth[2:]))[0] + 1
    step = float(np.median(np.diff(x)))
    min_distance = max(1, int(min_spacing_cm / step))

    def keep(candidates, high):
        ordered = sorted(candidates, key=lambda idx: smooth[idx], reverse=high)
        kept = []
        for idx in ordered:
            if all(abs(idx - prev) >= min_distance for prev in kept):
                kept.append(idx)
        return np.array(sorted(kept), dtype=int)

    return keep(max_candidates, True), keep(min_candidates, False), smooth


def cos_inside(angle_deg, n):
    theta = np.deg2rad(angle_deg)
    return np.sqrt(1.0 - (np.sin(theta) / n) ** 2)


def interval_thickness_um(extrema_cm, n, angle_deg):
    if len(extrema_cm) < 2:
        return np.array([])
    spacing = np.diff(extrema_cm)
    return 10000.0 / (2.0 * n * cos_inside(angle_deg, n) * spacing)


def fit_fod(extrema_cm, n, angle_deg):
    """Li2010-style fringe-order-difference fit with constant n baseline.

    p(nu) = 2*d*n*cos(theta1)*nu/10000 + 1/2.
    This function is called separately for peaks and troughs. Adjacent
    extrema of the same kind differ by one full order. Mixed peak-trough
    sequences would differ by half order, but they are not used here.
    """
    if len(extrema_cm) < 3:
        return None
    nu = np.asarray(extrema_cm, dtype=float)
    nu_ref = nu[-1]
    k = np.arange(len(nu) - 1, -1, -1, dtype=float)
    delta_p = k
    x = n * (nu_ref - nu)
    denom = float(np.dot(x, x))
    if denom <= 0:
        return None
    slope = float(np.dot(x, delta_p) / denom)
    pred = slope * x
    residual = delta_p - pred
    d_um = slope * 10000.0 / (2.0 * cos_inside(angle_deg, n))
    ss_res = float(np.sum(residual**2))
    ss_tot = float(np.sum((delta_p - delta_p.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot else np.nan
    return {
        "reference_wavenumber_cm": nu_ref,
        "n_points": len(nu),
        "d_um": d_um,
        "rss": ss_res,
        "r2": r2,
    }


def load_larruquert_sic_nk(path=LARRUQUERT_YML):
    """Read tabulated Larruquert SiC optical constants from local YAML data.

    The local CSV copy contains separate n and k blocks. The YAML source keeps
    wavelength, n, and k on one row, so it is safer for model input.
    """
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) != 3:
            continue
        try:
            wavelength_um, n_real, k_ext = map(float, parts)
        except ValueError:
            continue
        rows.append(
            {
                "wavelength_um": wavelength_um,
                "wavenumber_cm": 10000.0 / wavelength_um,
                "n": n_real,
                "k": k_ext,
            }
        )
    if not rows:
        raise ValueError(f"No tabulated nk data found in {path}.")
    table = pd.DataFrame(rows).sort_values("wavenumber_cm").reset_index(drop=True)
    return table


def interpolate_nk(nk_table, wavenumber_cm):
    """Linearly interpolate n(nu) and k(nu) at requested wavenumbers."""
    nu = np.asarray(wavenumber_cm, dtype=float)
    grid = nk_table["wavenumber_cm"].to_numpy(dtype=float)
    n_grid = nk_table["n"].to_numpy(dtype=float)
    k_grid = nk_table["k"].to_numpy(dtype=float)
    if nu.min() < grid.min() or nu.max() > grid.max():
        raise ValueError(
            "Requested wavenumber is outside Larruquert table range: "
            f"{nu.min():.3f}-{nu.max():.3f} cm^-1 vs "
            f"{grid.min():.3f}-{grid.max():.3f} cm^-1."
        )
    return np.interp(nu, grid, n_grid), np.interp(nu, grid, k_grid)


def optical_phase_factor(wavenumber_cm, n, angle_deg):
    """Return n(nu) cos(theta_1(nu)) nu for FOD phase differences."""
    nu = np.asarray(wavenumber_cm, dtype=float)
    n = np.asarray(n, dtype=float)
    return n * cos_inside(angle_deg, n) * nu


def fit_fod_dispersion(extrema_cm, n_values, k_values, angle_deg):
    """FOD fit using wavelength-dependent n for the SiC phase factor.

    For same-kind extrema, adjacent points still differ by one order. The
    regression variable becomes g(ref)-g(nu), where g(nu)=n(nu)cos(theta)nu.
    k is reported for diagnostics but not used in the phase-only FOD fit.
    """
    if len(extrema_cm) < 3:
        return None
    nu = np.asarray(extrema_cm, dtype=float)
    n_values = np.asarray(n_values, dtype=float)
    k_values = np.asarray(k_values, dtype=float)
    g = optical_phase_factor(nu, n_values, angle_deg)
    x = g[-1] - g
    delta_p = np.arange(len(nu) - 1, -1, -1, dtype=float)
    denom = float(np.dot(x, x))
    if denom <= 0:
        return None
    slope = float(np.dot(x, delta_p) / denom)
    pred = slope * x
    residual = delta_p - pred
    d_um = slope * 10000.0 / 2.0
    ss_res = float(np.sum(residual**2))
    ss_tot = float(np.sum((delta_p - delta_p.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot else np.nan
    return {
        "reference_wavenumber_cm": nu[-1],
        "n_points": len(nu),
        "d_um": d_um,
        "rss": ss_res,
        "r2": r2,
        "n_min": float(n_values.min()),
        "n_max": float(n_values.max()),
        "k_min": float(k_values.min()),
        "k_max": float(k_values.max()),
    }


def svg_line_plot(path, x, y, title, extrema=None, width=900, height=420):
    margin = 56
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    xmin, xmax = float(x.min()), float(x.max())
    ymin, ymax = float(y.min()), float(y.max())
    pad_y = (ymax - ymin) * 0.08 or 1.0
    ymin -= pad_y
    ymax += pad_y

    def sx(value):
        return margin + (float(value) - xmin) / (xmax - xmin) * (width - 2 * margin)

    def sy(value):
        return height - margin - (float(value) - ymin) / (ymax - ymin) * (height - 2 * margin)

    stride = max(1, len(x) // 1200)
    points = " ".join(f"{sx(xi):.2f},{sy(yi):.2f}" for xi, yi in zip(x[::stride], y[::stride]))
    elems = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2:.1f}" y="28" text-anchor="middle" font-family="Arial" font-size="18">{title}</text>',
        f'<line x1="{margin}" y1="{height-margin}" x2="{width-margin}" y2="{height-margin}" stroke="#333"/>',
        f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{height-margin}" stroke="#333"/>',
        f'<text x="{width/2:.1f}" y="{height-14}" text-anchor="middle" font-family="Arial" font-size="13">Wavenumber (cm^-1)</text>',
        f'<text x="18" y="{height/2:.1f}" transform="rotate(-90 18,{height/2:.1f})" text-anchor="middle" font-family="Arial" font-size="13">Reflectance (%)</text>',
        f'<polyline fill="none" stroke="#1f77b4" stroke-width="1.5" points="{points}"/>',
    ]
    for frac in np.linspace(0, 1, 5):
        xv = xmin + frac * (xmax - xmin)
        yv = ymin + frac * (ymax - ymin)
        elems.append(f'<text x="{sx(xv):.1f}" y="{height-margin+18}" text-anchor="middle" font-family="Arial" font-size="11">{xv:.0f}</text>')
        elems.append(f'<text x="{margin-8}" y="{sy(yv)+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{yv:.0f}</text>')
    if extrema is not None:
        for kind, data, color in extrema:
            for xi, yi in data:
                elems.append(f'<circle cx="{sx(xi):.2f}" cy="{sy(yi):.2f}" r="3" fill="{color}"><title>{kind}: {xi:.2f}, {yi:.2f}</title></circle>')
    elems.append("</svg>")
    path.write_text("\n".join(elems), encoding="utf-8")


def markdown_table(df):
    if df is None or len(df) == 0:
        return "No rows."
    rows = df.copy()
    for col in rows.columns:
        if pd.api.types.is_numeric_dtype(rows[col]):
            rows[col] = rows[col].map(lambda value: f"{value:.6g}")
        else:
            rows[col] = rows[col].astype(str)
    header = "| " + " | ".join(rows.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(rows.columns)) + " |"
    body = ["| " + " | ".join(map(str, row)) + " |" for row in rows.to_numpy()]
    return "\n".join([header, sep, *body])


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    extrema_rows = []
    interval_rows = []
    fod_rows = []

    for config in DATASETS:
        df = read_dataset(config)
        label = f'{config["material"]}_{int(config["angle_deg"])}deg'
        x_all = df["wavenumber_cm"].to_numpy()
        y_all = df["reflectance_pct"].to_numpy()
        mask = (x_all >= 1000.0) & (x_all <= 4000.0)
        x = x_all[mask]
        y = y_all[mask]
        peaks, troughs, smooth = separated_extrema(x, y)

        summary_rows.append(
            {
                "dataset": label,
                "material": config["material"],
                "angle_deg": config["angle_deg"],
                "rows": len(df),
                "wavenumber_min_cm": x_all.min(),
                "wavenumber_max_cm": x_all.max(),
                "reflectance_min_pct": y_all.min(),
                "reflectance_max_pct": y_all.max(),
                "reflectance_mean_pct": y_all.mean(),
                "peaks_high_region": len(peaks),
                "troughs_high_region": len(troughs),
            }
        )

        extrema_payload = []
        for kind, indices in [("peak", peaks), ("trough", troughs)]:
            nu = x[indices]
            refl = y[indices]
            extrema_payload.append((kind, list(zip(nu, refl)), "#d62728" if kind == "peak" else "#2ca02c"))
            for order, (nu_i, refl_i) in enumerate(zip(nu, refl)):
                extrema_rows.append(
                    {
                        "dataset": label,
                        "material": config["material"],
                        "angle_deg": config["angle_deg"],
                        "kind": kind,
                        "order": order,
                        "wavenumber_cm": nu_i,
                        "reflectance_pct": refl_i,
                    }
                )
            dvals = interval_thickness_um(nu, config["n0"], config["angle_deg"])
            for order, d_um in enumerate(dvals):
                interval_rows.append(
                    {
                        "dataset": label,
                        "material": config["material"],
                        "angle_deg": config["angle_deg"],
                        "kind": f"{kind}-{kind}",
                        "from_wavenumber_cm": nu[order],
                        "to_wavenumber_cm": nu[order + 1],
                        "spacing_cm": nu[order + 1] - nu[order],
                        "n0": config["n0"],
                        "thickness_um": d_um,
                    }
                )
            fod = fit_fod(nu, config["n0"], config["angle_deg"])
            if fod:
                fod_rows.append(
                    {
                        "dataset": label,
                        "material": config["material"],
                        "angle_deg": config["angle_deg"],
                        "kind": kind,
                        "n0": config["n0"],
                        **fod,
                    }
                )

        svg_line_plot(
            FIGURE_DIR / f"{label}_raw.svg",
            x_all,
            y_all,
            f"{label} raw reflectance spectrum",
        )
        svg_line_plot(
            FIGURE_DIR / f"{label}_extrema.svg",
            x,
            smooth,
            f"{label} high-region extrema after smoothing",
            extrema=extrema_payload,
        )

    summary = pd.DataFrame(summary_rows)
    extrema = pd.DataFrame(extrema_rows)
    intervals = pd.DataFrame(interval_rows)
    fod = pd.DataFrame(fod_rows)

    summary.to_csv(OUTPUT_DIR / "spectral_summary.csv", index=False, encoding="utf-8-sig")
    extrema.to_csv(OUTPUT_DIR / "extrema_points.csv", index=False, encoding="utf-8-sig")
    intervals.to_csv(OUTPUT_DIR / "baseline_thickness_intervals.csv", index=False, encoding="utf-8-sig")
    fod.to_csv(OUTPUT_DIR / "fod_fit_results.csv", index=False, encoding="utf-8-sig")

    grouped = intervals.groupby(["material", "angle_deg"])["thickness_um"].agg(["mean", "std", "count"]).reset_index()
    lines = [
        "# 谱线基础流程摘要",
        "",
        "这是探索性基线结果，不是最终模型结论。",
        "",
        "## 相邻同类极值厚度粗估",
        "",
        markdown_table(grouped),
        "",
        "## 常数折射率 FOD 拟合结果",
        "",
        markdown_table(fod),
        "",
        "## 说明",
        "",
        "- 当前基线使用常数折射率：SiC n=2.60，Si n=3.42。",
        "- FOD 拟合以最高波数极值为参考，峰和谷分开拟合；同类相邻极值按一级次差处理。",
        "- 后续需要用色散折射率替代常数 n，并检查峰谷提取参数敏感性。",
    ]
    (OUTPUT_DIR / "spectral_pipeline_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT_DIR / "spectral_pipeline_summary.md")


if __name__ == "__main__":
    main()
