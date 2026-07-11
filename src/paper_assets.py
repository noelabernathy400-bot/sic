from __future__ import annotations

import csv
import html
import math
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"
FIGURE_DIR = PROJECT / "Experiments" / "figures"
WRITING_DIR = PROJECT / "Writing"

DATASET_LABELS = {
    "joint": "双角度联合",
    "SiC_10deg": "SiC 10度",
    "SiC_15deg": "SiC 15度",
}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def to_float(value: str | None) -> float:
    if value is None or value == "":
        return math.nan
    try:
        return float(value)
    except ValueError:
        return math.nan


def parse_range(value: str) -> tuple[float, float] | None:
    if not value or "-" not in value:
        return None
    left, right = value.split("-", 1)
    try:
        return float(left), float(right)
    except ValueError:
        return None


def parse_summary_value(value: str) -> float:
    if not value:
        return math.nan
    cleaned = value.split("±", 1)[0].strip()
    try:
        return float(cleaned)
    except ValueError:
        return math.nan


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def zh_object_label(value: str) -> str:
    replacements = {
        "SiC_10deg": "SiC 10度",
        "SiC_15deg": "SiC 15度",
        "SiC 10deg": "SiC 10度",
        "SiC 15deg": "SiC 15度",
        "SiC 10deg+15deg joint": "SiC 10度+15度联合",
        "Si 10deg": "Si 10度",
        "Si 15deg": "Si 15度",
        "layer_shared_scale": "层间共同缩放",
        "lt_shared_scale": "纵横声子共同缩放",
        "bootstrap median": "自助法中位数",
        "um": "μm",
    }
    out = str(value)
    for old, new in replacements.items():
        out = out.replace(old, new)
    return out


def scale(value: float, vmin: float, vmax: float, start: float, end: float) -> float:
    if math.isclose(vmin, vmax):
        return (start + end) / 2
    return start + (value - vmin) / (vmax - vmin) * (end - start)


def write_svg(path: Path, elements: list[str], width: int, height: int) -> None:
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


def figure_model_route_comparison() -> Path:
    rows = read_rows(OUTPUT_DIR / "model_route_comparison.csv")
    plot_rows = []
    for row in rows:
        trust = row.get("trust_level", "")
        if trust == "调试用":
            continue
        value = parse_summary_value(row.get("thickness_um_summary", ""))
        interval = parse_range(row.get("thickness_um_range", ""))
        if math.isnan(value):
            continue
        if interval is None:
            interval = (value, value)
        label = zh_object_label(f"{row['model_route']} | {row['object']}")
        plot_rows.append((label, value, interval[0], interval[1], trust))

    width, height = 1180, 620
    left, right, top, bottom = 360, 60, 58, 70
    xmin = min(item[2] for item in plot_rows) - 0.08
    xmax = max(item[3] for item in plot_rows) + 0.08
    y_step = (height - top - bottom) / max(1, len(plot_rows) - 1)
    colors = {
        "中低": "#8c8c8c",
        "中": "#4c78a8",
        "中高候选": "#2ca02c",
        "当前最强候选": "#d62728",
        "稳健性补充": "#9467bd",
        "中间审查": "#ff7f0e",
    }
    elems = [
        '<text x="590" y="30" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">模型路线厚度候选对比</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<text x="{(left+width-right)/2:.1f}" y="{height-22}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">厚度 d (μm)</text>',
    ]
    for tick in [5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0]:
        if xmin <= tick <= xmax:
            x = scale(tick, xmin, xmax, left, width - right)
            elems.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height-bottom}" stroke="#e6e6e6"/>')
            elems.append(f'<text x="{x:.1f}" y="{height-bottom+18}" text-anchor="middle" font-family="Arial" font-size="11">{tick:.1f}</text>')
    for idx, (label, value, lo, hi, trust) in enumerate(plot_rows):
        y = top + idx * y_step
        x0 = scale(lo, xmin, xmax, left, width - right)
        x1 = scale(hi, xmin, xmax, left, width - right)
        xv = scale(value, xmin, xmax, left, width - right)
        color = colors.get(trust, "#333")
        elems.append(f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" font-family="Arial, Microsoft YaHei" font-size="12">{esc(label)}</text>')
        elems.append(f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" stroke="{color}" stroke-width="5" stroke-linecap="round"/>')
        elems.append(f'<circle cx="{xv:.1f}" cy="{y:.1f}" r="5" fill="{color}"><title>{esc(label)}: {value:.3f} μm</title></circle>')

    path = FIGURE_DIR / "paper_fig01_model_route_comparison.svg"
    write_svg(path, elems, width, height)
    return path


def figure_profile_objective() -> Path:
    rows = read_rows(OUTPUT_DIR / "dong2012_tmm_uncertainty_profile.csv")
    series: dict[str, list[tuple[float, float]]] = {}
    for row in rows:
        name = row["dataset"]
        series.setdefault(name, []).append((to_float(row["thickness_um"]), to_float(row["rmse"])))
    series = {
        name: sorted(points)
        for name, points in series.items()
        if name in {"joint", "SiC_10deg", "SiC_15deg"}
    }

    all_x = [x for points in series.values() for x, _ in points]
    all_y = [y for points in series.values() for _, y in points]
    width, height = 900, 520
    left, right, top, bottom = 72, 28, 52, 66
    xmin, xmax = min(all_x), max(all_x)
    ymin, ymax = min(all_y) * 0.96, max(all_y) * 1.04
    colors = {"joint": "#d62728", "SiC_10deg": "#1f77b4", "SiC_15deg": "#2ca02c"}
    elems = [
        '<text x="450" y="28" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">固定参数下 RMSE-厚度剖面</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
        f'<text x="450" y="{height-20}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">厚度 d (μm)</text>',
        f'<text x="18" y="{height/2:.1f}" transform="rotate(-90 18,{height/2:.1f})" text-anchor="middle" font-family="Arial" font-size="13">RMSE</text>',
    ]
    for tick in [7.2, 7.3, 7.4, 7.5, 7.6, 7.7]:
        x = scale(tick, xmin, xmax, left, width - right)
        elems.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height-bottom}" stroke="#eeeeee"/>')
        elems.append(f'<text x="{x:.1f}" y="{height-bottom+18}" text-anchor="middle" font-family="Arial" font-size="11">{tick:.1f}</text>')
    for frac in [0, 0.25, 0.5, 0.75, 1]:
        yv = ymin + frac * (ymax - ymin)
        y = scale(yv, ymin, ymax, height - bottom, top)
        elems.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#f2f2f2"/>')
        elems.append(f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{yv:.4f}</text>')
    legend_x = width - 210
    for idx, (name, points) in enumerate(series.items()):
        path_points = " ".join(
            f"{scale(x, xmin, xmax, left, width-right):.2f},{scale(y, ymin, ymax, height-bottom, top):.2f}"
            for x, y in points
        )
        color = colors.get(name, "#333")
        elems.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{path_points}"/>')
        elems.append(f'<line x1="{legend_x}" y1="{top+idx*22}" x2="{legend_x+24}" y2="{top+idx*22}" stroke="{color}" stroke-width="3"/>')
        elems.append(f'<text x="{legend_x+32}" y="{top+idx*22+4}" font-family="Arial, Microsoft YaHei" font-size="12">{esc(DATASET_LABELS.get(name, name))}</text>')
    path = FIGURE_DIR / "paper_fig02_tmm_profile.svg"
    write_svg(path, elems, width, height)
    return path


def figure_bootstrap_histogram() -> Path:
    rows = read_rows(OUTPUT_DIR / "dong2012_tmm_uncertainty_bootstrap.csv")
    values = [to_float(row["best_thickness_um"]) for row in rows]
    values = [value for value in values if not math.isnan(value)]
    bin_width = 0.005
    lo = math.floor(min(values) / bin_width) * bin_width
    hi = math.ceil(max(values) / bin_width) * bin_width
    bins = []
    x = lo
    while x <= hi + 1e-12:
        bins.append(x)
        x += bin_width
    counts = [0 for _ in range(len(bins) - 1)]
    for value in values:
        idx = min(len(counts) - 1, max(0, int((value - lo) / bin_width)))
        counts[idx] += 1

    width, height = 860, 480
    left, right, top, bottom = 68, 28, 52, 64
    ymax = max(counts)
    elems = [
        '<text x="430" y="28" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">残差块 Bootstrap 厚度分布</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
        f'<text x="430" y="{height-18}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">最佳厚度 d (μm)</text>',
        f'<text x="18" y="{height/2:.1f}" transform="rotate(-90 18,{height/2:.1f})" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">次数</text>',
    ]
    for idx, count in enumerate(counts):
        x0 = scale(bins[idx], lo, hi, left, width - right)
        x1 = scale(bins[idx + 1], lo, hi, left, width - right)
        y = scale(count, 0, ymax, height - bottom, top)
        elems.append(f'<rect x="{x0+1:.1f}" y="{y:.1f}" width="{max(1, x1-x0-2):.1f}" height="{height-bottom-y:.1f}" fill="#4c78a8"/>')
    for tick in sorted(set(round(value, 3) for value in [lo, 7.445, 7.455, 7.465, hi])):
        if lo <= tick <= hi:
            x = scale(tick, lo, hi, left, width - right)
            elems.append(f'<text x="{x:.1f}" y="{height-bottom+18}" text-anchor="middle" font-family="Arial" font-size="11">{tick:.3f}</text>')
    path = FIGURE_DIR / "paper_fig03_bootstrap_histogram.svg"
    write_svg(path, elems, width, height)
    return path


def figure_band_sensitivity() -> Path:
    rows = read_rows(OUTPUT_DIR / "dong2012_tmm_band_sensitivity_joint.csv")
    labels = [row["band_name"] for row in rows]
    thickness = [to_float(row["joint_best_thickness_um"]) for row in rows]
    rmse = [to_float(row["joint_mean_rmse"]) for row in rows]
    width, height = 980, 520
    left, right, top, bottom = 98, 36, 56, 120
    xmin = -0.6
    xmax = len(labels) - 0.4
    tmin, tmax = min(thickness) - 0.04, max(thickness) + 0.04
    rmax = max(rmse) * 1.15
    elems = [
        '<text x="490" y="30" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">拟合波段敏感性</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
        f'<text x="24" y="{height/2:.1f}" transform="rotate(-90 24,{height/2:.1f})" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">厚度 d (μm)</text>',
    ]
    bar_width = (width - left - right) / len(labels) * 0.55
    for idx, (label, thick, error) in enumerate(zip(labels, thickness, rmse)):
        x = scale(idx, xmin, xmax, left, width - right)
        bar_h = error / rmax * (height - top - bottom)
        elems.append(f'<rect x="{x-bar_width/2:.1f}" y="{height-bottom-bar_h:.1f}" width="{bar_width:.1f}" height="{bar_h:.1f}" fill="#cfe1f2"><title>RMSE {error:.5f}</title></rect>')
        y = scale(thick, tmin, tmax, height - bottom, top)
        elems.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#d62728"><title>{esc(label)}: {thick:.3f} um</title></circle>')
        elems.append(f'<text x="{x:.1f}" y="{height-bottom+16}" transform="rotate(35 {x:.1f},{height-bottom+16})" text-anchor="start" font-family="Arial" font-size="11">{esc(label)}</text>')
    for tick in [7.35, 7.40, 7.45, 7.50]:
        if tmin <= tick <= tmax:
            y = scale(tick, tmin, tmax, height - bottom, top)
            elems.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" stroke="#eeeeee"/>')
            elems.append(f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end" font-family="Arial" font-size="11">{tick:.2f}</text>')
    elems.append('<text x="720" y="68" font-family="Arial, Microsoft YaHei" font-size="12" fill="#d62728">红点：最佳厚度 d</text>')
    elems.append('<text x="720" y="88" font-family="Arial, Microsoft YaHei" font-size="12" fill="#4c78a8">蓝柱：相对 RMSE 尺度</text>')
    path = FIGURE_DIR / "paper_fig04_band_sensitivity.svg"
    write_svg(path, elems, width, height)
    return path


def _color_for_value(value: float, vmin: float, vmax: float) -> str:
    if math.isclose(vmin, vmax):
        t = 0.5
    else:
        t = max(0.0, min(1.0, (value - vmin) / (vmax - vmin)))
    r = int(49 + t * (198 - 49))
    g = int(130 + t * (55 - 130))
    b = int(189 + t * (32 - 189))
    return f"#{r:02x}{g:02x}{b:02x}"


def _figure_heatmap(
    rows: list[dict[str, str]],
    x_key: str,
    y_key: str,
    value_key: str,
    title: str,
    x_label: str,
    y_label: str,
    path: Path,
) -> Path:
    values = []
    xs = sorted({to_float(row[x_key]) for row in rows})
    ys = sorted({to_float(row[y_key]) for row in rows}, reverse=True)
    grid = {}
    for row in rows:
        x = to_float(row[x_key])
        y = to_float(row[y_key])
        value = to_float(row[value_key])
        if not math.isnan(value):
            grid[(x, y)] = value
            values.append(value)
    vmin, vmax = min(values), max(values)
    width, height = 760, 600
    left, right, top, bottom = 128, 104, 70, 92
    cell_w = (width - left - right) / len(xs)
    cell_h = (height - top - bottom) / len(ys)
    elems = [
        f'<text x="{width/2:.1f}" y="32" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">{esc(title)}</text>',
        f'<text x="{(left+width-right)/2:.1f}" y="{height-28}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">{esc(x_label)}</text>',
        f'<text x="26" y="{(top+height-bottom)/2:.1f}" transform="rotate(-90 26,{(top+height-bottom)/2:.1f})" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">{esc(y_label)}</text>',
    ]
    for i, x in enumerate(xs):
        x_pos = left + i * cell_w
        elems.append(f'<text x="{x_pos+cell_w/2:.1f}" y="{height-bottom+20}" text-anchor="middle" font-family="Arial" font-size="12">{x:g}</text>')
    for j, y in enumerate(ys):
        y_pos = top + j * cell_h
        elems.append(f'<text x="{left-12}" y="{y_pos+cell_h/2+4:.1f}" text-anchor="end" font-family="Arial" font-size="12">{y:g}</text>')
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            value = grid.get((x, y), math.nan)
            x_pos = left + i * cell_w
            y_pos = top + j * cell_h
            color = "#f6f6f6" if math.isnan(value) else _color_for_value(value, vmin, vmax)
            elems.append(f'<rect x="{x_pos:.1f}" y="{y_pos:.1f}" width="{cell_w:.1f}" height="{cell_h:.1f}" fill="{color}" stroke="white"/>')
            if not math.isnan(value):
                elems.append(f'<text x="{x_pos+cell_w/2:.1f}" y="{y_pos+cell_h/2+4:.1f}" text-anchor="middle" font-family="Arial" font-size="12" fill="white">{value:.2f}</text>')
    legend_x = width - 70
    legend_y = top
    legend_h = height - top - bottom
    for idx in range(40):
        t0 = idx / 40
        val = vmin + t0 * (vmax - vmin)
        color = _color_for_value(val, vmin, vmax)
        y0 = legend_y + (1 - (idx + 1) / 40) * legend_h
        elems.append(f'<rect x="{legend_x}" y="{y0:.1f}" width="18" height="{legend_h/40+1:.1f}" fill="{color}"/>')
    elems.append(f'<text x="{legend_x+26}" y="{legend_y+4}" font-family="Arial" font-size="11">{vmax:.2f}</text>')
    elems.append(f'<text x="{legend_x+26}" y="{legend_y+legend_h:.1f}" font-family="Arial" font-size="11">{vmin:.2f}</text>')
    elems.append(f'<text x="{legend_x-10}" y="{legend_y+legend_h+26:.1f}" font-family="Arial, Microsoft YaHei" font-size="11">最佳 d (μm)</text>')
    write_svg(path, elems, width, height)
    return path


def _figure_rmse_heatmap(
    rows: list[dict[str, str]],
    x_key: str,
    y_key: str,
    value_key: str,
    title: str,
    x_label: str,
    y_label: str,
    path: Path,
) -> Path:
    values = []
    xs = sorted({to_float(row[x_key]) for row in rows})
    ys = sorted({to_float(row[y_key]) for row in rows}, reverse=True)
    grid = {}
    for row in rows:
        x = to_float(row[x_key])
        y = to_float(row[y_key])
        value = to_float(row[value_key])
        if not math.isnan(value):
            grid[(x, y)] = value
            values.append(value)
    vmin, vmax = min(values), max(values)
    width, height = 760, 600
    left, right, top, bottom = 128, 112, 70, 92
    cell_w = (width - left - right) / len(xs)
    cell_h = (height - top - bottom) / len(ys)
    elems = [
        f'<text x="{width/2:.1f}" y="32" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">{esc(title)}</text>',
        f'<text x="{(left+width-right)/2:.1f}" y="{height-28}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">{esc(x_label)}</text>',
        f'<text x="26" y="{(top+height-bottom)/2:.1f}" transform="rotate(-90 26,{(top+height-bottom)/2:.1f})" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">{esc(y_label)}</text>',
    ]
    for i, x in enumerate(xs):
        x_pos = left + i * cell_w
        elems.append(f'<text x="{x_pos+cell_w/2:.1f}" y="{height-bottom+20}" text-anchor="middle" font-family="Arial" font-size="12">{x:g}</text>')
    for j, y in enumerate(ys):
        y_pos = top + j * cell_h
        elems.append(f'<text x="{left-12}" y="{y_pos+cell_h/2+4:.1f}" text-anchor="end" font-family="Arial" font-size="12">{y:g}</text>')
    for i, x in enumerate(xs):
        for j, y in enumerate(ys):
            value = grid.get((x, y), math.nan)
            x_pos = left + i * cell_w
            y_pos = top + j * cell_h
            color = "#f6f6f6" if math.isnan(value) else _color_for_value(value, vmin, vmax)
            elems.append(f'<rect x="{x_pos:.1f}" y="{y_pos:.1f}" width="{cell_w:.1f}" height="{cell_h:.1f}" fill="{color}" stroke="white"/>')
            if not math.isnan(value):
                elems.append(f'<text x="{x_pos+cell_w/2:.1f}" y="{y_pos+cell_h/2+4:.1f}" text-anchor="middle" font-family="Arial" font-size="11" fill="white">{value:.4f}</text>')
    legend_x = width - 76
    legend_y = top
    legend_h = height - top - bottom
    for idx in range(40):
        t0 = idx / 40
        val = vmin + t0 * (vmax - vmin)
        color = _color_for_value(val, vmin, vmax)
        y0 = legend_y + (1 - (idx + 1) / 40) * legend_h
        elems.append(f'<rect x="{legend_x}" y="{y0:.1f}" width="18" height="{legend_h/40+1:.1f}" fill="{color}"/>')
    elems.append(f'<text x="{legend_x+26}" y="{legend_y+4}" font-family="Arial" font-size="11">{vmax:.4f}</text>')
    elems.append(f'<text x="{legend_x+26}" y="{legend_y+legend_h:.1f}" font-family="Arial" font-size="11">{vmin:.4f}</text>')
    elems.append(f'<text x="{legend_x-14}" y="{legend_y+legend_h+26:.1f}" font-family="Arial, Microsoft YaHei" font-size="11">联合 RMSE</text>')
    write_svg(path, elems, width, height)
    return path


def figure_parameter_heatmaps() -> list[Path]:
    nu_rows = read_rows(OUTPUT_DIR / "dong2012_tmm_sensitivity_joint.csv")
    gamma_rows = read_rows(OUTPUT_DIR / "dong2012_tmm_gamma_sensitivity_joint.csv")
    phonon_rows = [
        row
        for row in read_rows(OUTPUT_DIR / "dong2012_tmm_phonon_sensitivity_joint.csv")
        if row.get("mode") == "layer_shared_scale"
    ]
    return [
        _figure_heatmap(
            nu_rows,
            "sub_plasma_scale",
            "epi_plasma_scale",
            "joint_best_thickness_um",
            "nu_p 敏感性：联合最佳厚度",
            "衬底 nu_p 缩放",
            "外延层 nu_p 缩放",
            FIGURE_DIR / "paper_fig07_heatmap_nu_p_sensitivity.svg",
        ),
        _figure_heatmap(
            gamma_rows,
            "sub_gamma_scale",
            "epi_gamma_scale",
            "joint_best_thickness_um",
            "gamma 敏感性：联合最佳厚度",
            "衬底 gamma 缩放",
            "外延层 gamma 缩放",
            FIGURE_DIR / "paper_fig08_heatmap_gamma_sensitivity.svg",
        ),
        _figure_heatmap(
            phonon_rows,
            "sub_gamma_l_scale",
            "epi_gamma_l_scale",
            "joint_best_thickness_um",
            "声子阻尼敏感性：联合最佳厚度",
            "衬底 Gamma 缩放",
            "外延层 Gamma 缩放",
            FIGURE_DIR / "paper_fig09_heatmap_phonon_sensitivity.svg",
        ),
        _figure_rmse_heatmap(
            nu_rows,
            "sub_plasma_scale",
            "epi_plasma_scale",
            "joint_mean_rmse",
            "nu_p 敏感性：联合 RMSE",
            "衬底 nu_p 缩放",
            "外延层 nu_p 缩放",
            FIGURE_DIR / "paper_fig10_rmse_heatmap_nu_p_sensitivity.svg",
        ),
        _figure_rmse_heatmap(
            gamma_rows,
            "sub_gamma_scale",
            "epi_gamma_scale",
            "joint_mean_rmse",
            "gamma 敏感性：联合 RMSE",
            "衬底 gamma 缩放",
            "外延层 gamma 缩放",
            FIGURE_DIR / "paper_fig11_rmse_heatmap_gamma_sensitivity.svg",
        ),
        _figure_rmse_heatmap(
            phonon_rows,
            "sub_gamma_l_scale",
            "epi_gamma_l_scale",
            "joint_mean_rmse",
            "声子阻尼敏感性：联合 RMSE",
            "衬底 Gamma 缩放",
            "外延层 Gamma 缩放",
            FIGURE_DIR / "paper_fig12_rmse_heatmap_phonon_sensitivity.svg",
        ),
    ]


def parameter_table_markdown() -> Path:
    route_rows = read_rows(OUTPUT_DIR / "model_route_comparison.csv")
    support_rows = read_rows(OUTPUT_DIR / "dong2012_tmm_uncertainty_support.csv")
    bootstrap_rows = read_rows(OUTPUT_DIR / "dong2012_tmm_uncertainty_bootstrap_summary.csv")
    chosen_rows = read_rows(OUTPUT_DIR / "dong2012_tmm_coordinate_search_chosen.csv")
    final_state = chosen_rows[-1] if chosen_rows else {}

    lines = [
        "---",
        "type: paper-table",
        "project: 碳化硅外延层厚度确定研究",
        "created: 2026-05-04",
        "---",
        "",
        "# 论文参数表与结果表 - 2026-05-04",
        "",
        "本文件由 `Code/paper_assets.py` 根据已有实验输出生成。它只整理已经可追溯的结果，不新增模型结论。",
        "",
        "## 表 1：模型路线结果对比",
        "",
        "| 模型路线 | 对象 | 厚度摘要 $\\mu m$ | 厚度范围 $\\mu m$ | 可信度 | 主要风险 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in route_rows:
        lines.append(
            "| {model_route} | {object} | {summary} | {range_} | {trust} | {risk} |".format(
                model_route=row["model_route"],
                object=row["object"],
                summary=row["thickness_um_summary"],
                range_=row["thickness_um_range"],
                trust=row["trust_level"],
                risk=row["main_risk"],
            )
        )

    lines.extend(
        [
            "",
            "## 表 2：分阶段坐标搜索最终参数缩放",
            "",
            "这些缩放值来自粗网格分阶段搜索，只表示当前探索路径的最终状态，不是全局最优证明。",
            "",
            "| 参数 | 缩放值 | 解释 |",
            "| --- | --- | --- |",
        ]
    )
    param_notes = {
        "epi_nu_p_scale": "外延层等离子体频率 $\\nu_p$ 缩放",
        "sub_nu_p_scale": "衬底等离子体频率 $\\nu_p$ 缩放",
        "epi_gamma_scale": "外延层 Drude 阻尼 $\\gamma$ 缩放",
        "sub_gamma_scale": "衬底 Drude 阻尼 $\\gamma$ 缩放",
        "epi_gamma_l_scale": "外延层 $\\Gamma_L$ 缩放",
        "epi_gamma_t_scale": "外延层 $\\Gamma_T$ 缩放",
        "sub_gamma_l_scale": "衬底 $\\Gamma_L$ 缩放",
        "sub_gamma_t_scale": "衬底 $\\Gamma_T$ 缩放",
    }
    for key, note in param_notes.items():
        lines.append(f"| `{key}` | {final_state.get(key, '待生成')} | {note} |")

    lines.extend(
        [
            "",
            "## 表 3：固定参数 RMSE 支持区间",
            "",
            "| RMSE 相对增加 | 支持区间下界 $\\mu m$ | 支持区间上界 $\\mu m$ | 宽度 $\\mu m$ |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in support_rows:
        rel = to_float(row["relative_rmse_increase"])
        lines.append(
            f"| {rel:.0%} | {row['support_min_um']} | {row['support_max_um']} | {row['support_width_um']} |"
        )

    lines.extend(
        [
            "",
            "## 表 4：固定参数残差块 Bootstrap 摘要",
            "",
            "| 重采样次数 | 均值 $\\mu m$ | 标准差 $\\mu m$ | $2.5\\%$ 分位 | 中位数 | $97.5\\%$ 分位 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    if bootstrap_rows:
        row = bootstrap_rows[0]
        lines.append(
            f"| {row['n_replicates']} | {row['mean_um']} | {row['std_um']} | {row['q025_um']} | {row['median_um']} | {row['q975_um']} |"
        )

    lines.extend(
        [
            "",
            "## 写作提醒",
            "",
            "- 表 2 到表 4 都依赖当前 Dong/TMM 固定参数路径，不能写成完整物理置信区间。",
            "- 若后续做连续联合优化，本文件应重新生成，并在论文中替换相应表格。",
        ]
    )

    path = WRITING_DIR / "论文参数表与结果表-2026-05-04.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return path


def figure_plan_markdown(figure_paths: list[Path], table_path: Path) -> Path:
    lines = [
        "---",
        "type: paper-figure-plan",
        "project: 碳化硅外延层厚度确定研究",
        "created: 2026-05-04",
        "---",
        "",
        "# 论文图表与参数表计划 - 2026-05-04",
        "",
        "本文件是 `Writing/论文初稿-2026-05-04.md` 的配套图表计划。当前优先把已有证据变成可检查图表，再决定哪些模型需要继续补实验。",
        "",
        "## 已生成图表",
        "",
        "| 编号 | 文件 | 放入论文的位置 | 作用 |",
        "| --- | --- | --- | --- |",
    ]
    entries = [
        ("图 1", figure_paths[0], "第 10 节 当前综合结果", "横向比较所有非调试模型的厚度候选区间，防止只盯住单个数值。"),
        ("图 2", figure_paths[1], "第 9.6 节 固定参数不确定性", "展示 $\\mathrm{RMSE}(d)$ 在 $7.455\\ \\mu m$ 附近的低谷形状。"),
        ("图 3", figure_paths[2], "第 9.6 节 固定参数不确定性", "展示残差块 bootstrap 下厚度低谷的局部分布。"),
        ("图 4", figure_paths[3], "第 9.4 节 波段敏感性", "说明波段改变会影响 RMSE，但厚度低谷仍主要留在 $7.4\\ \\mu m$ 附近。"),
    ]
    bestfit_entries = [
        (
            "图 5",
            FIGURE_DIR / "paper_fig05_tmm_bestfit_SiC_10deg.svg",
            "第 8.3 节 Dong 表 2 参数调试结果或第 9.6 节",
            "展示 $10^\\circ$ 数据在 $d=7.455\\ \\mu m$ 固定参数代表值下的实验谱线与仿射标定 TMM 拟合谱线。",
        ),
        (
            "图 6",
            FIGURE_DIR / "paper_fig05_tmm_bestfit_SiC_15deg.svg",
            "第 8.3 节 Dong 表 2 参数调试结果或第 9.6 节",
            "展示 $15^\\circ$ 数据在 $d=7.455\\ \\mu m$ 固定参数代表值下的实验谱线与仿射标定 TMM 拟合谱线。",
        ),
        (
            "图 7",
            FIGURE_DIR / "paper_fig06_tmm_bestfit_residuals.svg",
            "第 9.6 节 固定参数不确定性",
            "展示两个角度的拟合残差，帮助判断模型误差是否集中在某些波段。",
        ),
    ]
    heatmap_entries = [
        ("图 8", FIGURE_DIR / "paper_fig07_heatmap_nu_p_sensitivity.svg", "第 9.1 节 $\\nu_p$ 敏感性", "展示外延层/衬底 $\\nu_p$ 缩放组合下的联合最优厚度。"),
        ("图 9", FIGURE_DIR / "paper_fig08_heatmap_gamma_sensitivity.svg", "第 9.2 节 $\\gamma$ 敏感性", "展示外延层/衬底 $\\gamma$ 缩放组合下的联合最优厚度。"),
        ("图 10", FIGURE_DIR / "paper_fig09_heatmap_phonon_sensitivity.svg", "第 9.3 节 $\\Gamma_L,\\Gamma_T$ 敏感性", "展示声子阻尼缩放组合下的联合最优厚度。"),
        ("图 11", FIGURE_DIR / "paper_fig10_rmse_heatmap_nu_p_sensitivity.svg", "第 9.1 节 $\\nu_p$ 敏感性", "展示外延层/衬底 $\\nu_p$ 缩放组合下的联合 RMSE，区分厚度稳定和拟合质量。"),
        ("图 12", FIGURE_DIR / "paper_fig11_rmse_heatmap_gamma_sensitivity.svg", "第 9.2 节 $\\gamma$ 敏感性", "展示外延层/衬底 $\\gamma$ 缩放组合下的联合 RMSE。"),
        ("图 13", FIGURE_DIR / "paper_fig12_rmse_heatmap_phonon_sensitivity.svg", "第 9.3 节 $\\Gamma_L,\\Gamma_T$ 敏感性", "展示声子阻尼缩放组合下的联合 RMSE。"),
    ]
    entries.extend(item for item in bestfit_entries if item[1].exists())
    entries.extend(item for item in heatmap_entries if item[1].exists())
    for number, path, location, role in entries:
        lines.append(f"| {number} | `{path.relative_to(PROJECT)}` | {location} | {role} |")

    lines.extend(
        [
            "",
            "## 已生成表格",
            "",
            f"- `{table_path.relative_to(PROJECT)}`：整理模型路线结果、坐标搜索最终参数、固定参数支持区间和 bootstrap 摘要。",
            "",
            "## 仍需补的关键图",
            "",
            "| 编号 | 图表 | 为什么还缺 | 下一步动作 |",
            "| --- | --- | --- | --- |",
            "| 图 A | SiC 附件 1/2 原始谱线合并图 | 现有图是单附件 SVG，论文需要双角度同图对比 | 后续从原始附件读取并生成合并图 |",
            "| 图 B | TMM 实验谱线 vs 拟合谱线 | 已有固定参数代表值版本，但还不是连续联合优化后的最终版本 | 连续优化完成后重新导出拟合谱线与残差 |",
            "| 图 C | 参数敏感性热力图 | 厚度低谷热力图和 RMSE 热力图均已有，但还不是连续联合优化后的参数空间图 | 连续/受约束局部优化后重新生成最终版 |",
            "| 图 D | 文献参数来源图 | 需要解释 Dong2012 参数如何进入本题模型 | 写成流程图或 Mermaid 图 |",
            "",
            "## 当前判断",
            "",
            "这些图表已经足够支撑一版论文讨论，但还不足以支撑最终定稿。最重要的缺口是图 B 和图 C：前者展示模型是否真的拟合了谱线，后者展示厚度低谷是否在参数空间内稳定。",
        ]
    )
    path = WRITING_DIR / "论文图表与参数表计划-2026-05-04.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return path


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    WRITING_DIR.mkdir(parents=True, exist_ok=True)
    figure_paths = [
        figure_model_route_comparison(),
        figure_profile_objective(),
        figure_bootstrap_histogram(),
        figure_band_sensitivity(),
        *figure_parameter_heatmaps(),
    ]
    table_path = parameter_table_markdown()
    plan_path = figure_plan_markdown(figure_paths, table_path)
    summary_path = OUTPUT_DIR / "paper_assets_summary.md"
    lines = [
        "# Paper assets summary",
        "",
        "Generated from existing experiment outputs. No new thickness model was fitted in this script.",
        "",
        "## Figures",
        "",
    ]
    for path in figure_paths:
        lines.append(f"- `{path.relative_to(PROJECT)}`")
    lines.extend(
        [
            "",
            "## Tables and plan",
            "",
            f"- `{table_path.relative_to(PROJECT)}`",
            f"- `{plan_path.relative_to(PROJECT)}`",
        ]
    )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


if __name__ == "__main__":
    main()
