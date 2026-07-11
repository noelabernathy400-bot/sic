from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from dong2012_tmm_local_refinement import CONFIGS
from dong2012_tmm_uncertainty import THICKNESS_GRID_UM, prepare_angle_data


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"
FIGURE_DIR = PROJECT / "Experiments" / "figures"

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

SCENARIO_LABELS = {
    "all_equal": "全波段等权",
    "frequency_screened": "频域筛选",
    "frequency_downweighted": "频域降权",
    "continuous_frequency_weight": "连续频域权重",
}

DATASET_LABELS = {
    "SiC_10deg": "SiC 10度",
    "SiC_15deg": "SiC 15度",
    "joint": "双角度联合",
}


def load_constrained_state() -> dict[str, float]:
    path = OUTPUT_DIR / "dong2012_tmm_constrained_refinement_chosen.csv"
    if not path.exists():
        raise FileNotFoundError("Run dong2012_tmm_constrained_refinement.py first.")
    final = pd.read_csv(path).iloc[-1]
    return {key: float(final[key]) for key in STATE_KEYS}


def load_alignment() -> pd.DataFrame:
    path = OUTPUT_DIR / "residual_fft_alignment_summary.csv"
    if not path.exists():
        raise FileNotFoundError("Run residual_fft_alignment.py first.")
    return pd.read_csv(path)


def scenario_band_weights(alignment: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in alignment.itertuples(index=False):
        strong_frequency = (not bool(row.frequency_evidence_weak)) and bool(row.period_stable)
        rows.append(
            {
                "dataset": row.dataset,
                "band": row.band,
                "band_min_cm": float(row.band_min_cm),
                "band_max_cm": float(row.band_max_cm),
                "scenario": "all_equal",
                "band_weight": 1.0,
                "reason": "全波段等权基线",
            }
        )
        rows.append(
            {
                "dataset": row.dataset,
                "band": row.band,
                "band_min_cm": float(row.band_min_cm),
                "band_max_cm": float(row.band_max_cm),
                "scenario": "frequency_screened",
                "band_weight": 1.0 if strong_frequency else 0.0,
                "reason": "只保留周期稳定且频域峰较强的波段",
            }
        )
        rows.append(
            {
                "dataset": row.dataset,
                "band": row.band,
                "band_min_cm": float(row.band_min_cm),
                "band_max_cm": float(row.band_max_cm),
                "scenario": "frequency_downweighted",
                "band_weight": 1.0 if strong_frequency else 0.35,
                "reason": "频域证据较弱波段降权但不丢弃",
            }
        )
        strength = float(row.min_peak_to_median)
        scaled = min(1.25, max(0.35, strength / 4.5))
        if not bool(row.period_stable):
            scaled *= 0.7
        rows.append(
            {
                "dataset": row.dataset,
                "band": row.band,
                "band_min_cm": float(row.band_min_cm),
                "band_max_cm": float(row.band_max_cm),
                "scenario": "continuous_frequency_weight",
                "band_weight": float(scaled),
                "reason": "按频域峰强度和周期稳定性连续赋权",
            }
        )
    return pd.DataFrame(rows)


def weights_for_points(nu: np.ndarray, dataset: str, scenario: str, band_weights: pd.DataFrame) -> np.ndarray:
    selected = band_weights[(band_weights["dataset"] == dataset) & (band_weights["scenario"] == scenario)]
    weights = np.zeros_like(nu, dtype=float)
    for row in selected.itertuples(index=False):
        mask = (nu >= float(row.band_min_cm)) & (nu <= float(row.band_max_cm))
        weights[mask] = np.maximum(weights[mask], float(row.band_weight))
    # Keep points outside explicitly listed base bands out of the objective.
    return weights


def weighted_affine_fit(model: np.ndarray, observed: np.ndarray, weights: np.ndarray) -> tuple[float, float, float]:
    x = np.asarray(model, dtype=float)
    y = np.asarray(observed, dtype=float)
    w = np.asarray(weights, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y) & np.isfinite(w) & (w > 0)
    if np.count_nonzero(mask) < 3:
        return np.nan, np.nan, np.nan
    x = x[mask]
    y = y[mask]
    w = w[mask]
    w_sum = float(np.sum(w))
    x_mean = float(np.sum(w * x) / w_sum)
    y_mean = float(np.sum(w * y) / w_sum)
    denom = float(np.sum(w * (x - x_mean) ** 2))
    if denom <= 0:
        scale = 0.0
    else:
        scale = float(np.sum(w * (x - x_mean) * (y - y_mean)) / denom)
    offset = float(y_mean - scale * x_mean)
    residual = y - (scale * x + offset)
    rmse = float(np.sqrt(np.sum(w * residual**2) / w_sum))
    return rmse, scale, offset


def profile_for_scenario(angle_data: list[dict], scenario: str, band_weights: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows = []
    for idx, thickness_um in enumerate(THICKNESS_GRID_UM):
        angle_rmses = []
        angle_weights = []
        for item in angle_data:
            weights = weights_for_points(
                item["wavenumber_cm"],
                item["dataset"],
                scenario,
                band_weights,
            )
            rmse, scale, offset = weighted_affine_fit(
                item["model_matrix"][idx],
                item["observed"],
                weights,
            )
            effective_points = int(np.count_nonzero(weights > 0))
            rows.append(
                {
                    "scenario": scenario,
                    "dataset": item["dataset"],
                    "angle_deg": float(item["angle_deg"]),
                    "thickness_um": float(thickness_um),
                    "weighted_rmse": rmse,
                    "affine_scale": scale,
                    "affine_offset": offset,
                    "effective_points": effective_points,
                    "point_weight_sum": float(np.sum(weights)),
                }
            )
            if np.isfinite(rmse):
                angle_rmses.append(rmse)
                angle_weights.append(float(np.sum(weights)))
        if angle_rmses:
            rows.append(
                {
                    "scenario": scenario,
                    "dataset": "joint",
                    "angle_deg": np.nan,
                    "thickness_um": float(thickness_um),
                    "weighted_rmse": float(np.average(angle_rmses, weights=angle_weights)),
                    "affine_scale": np.nan,
                    "affine_offset": np.nan,
                    "effective_points": int(np.sum([row["effective_points"] for row in rows[-len(angle_rmses) :]])),
                    "point_weight_sum": float(np.sum(angle_weights)),
                }
            )
    profile = pd.DataFrame(rows)
    joint = profile[profile["dataset"] == "joint"].copy()
    best = joint.sort_values(["weighted_rmse", "thickness_um"]).iloc[0].to_dict()
    return profile, best


def build_profiles() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    state = load_constrained_state()
    alignment = load_alignment()
    band_weights = scenario_band_weights(alignment)
    angle_data = [prepare_angle_data(config, state) for config in CONFIGS]
    profiles = []
    summaries = []
    scenarios = [
        "all_equal",
        "frequency_screened",
        "frequency_downweighted",
        "continuous_frequency_weight",
    ]
    for scenario in scenarios:
        profile, best = profile_for_scenario(angle_data, scenario, band_weights)
        profiles.append(profile)
        summaries.append(
            {
                "scenario": scenario,
                "best_thickness_um": float(best["thickness_um"]),
                "joint_weighted_rmse": float(best["weighted_rmse"]),
                "effective_points": int(best["effective_points"]),
                "point_weight_sum": float(best["point_weight_sum"]),
            }
        )
    summary = pd.DataFrame(summaries)
    baseline = summary[summary["scenario"] == "all_equal"].iloc[0]
    summary["delta_from_all_equal_um"] = summary["best_thickness_um"] - float(baseline["best_thickness_um"])
    summary["rmse_ratio_vs_all_equal"] = summary["joint_weighted_rmse"] / float(baseline["joint_weighted_rmse"])
    return pd.concat(profiles, ignore_index=True), summary, band_weights


def _scale(value: float, vmin: float, vmax: float, start: float, end: float) -> float:
    if np.isclose(vmin, vmax):
        return (start + end) / 2.0
    return start + (float(value) - vmin) / (vmax - vmin) * (end - start)


def write_svg(profile: pd.DataFrame, path: Path) -> None:
    joint = profile[profile["dataset"] == "joint"].copy()
    width, height = 980, 560
    left, right, top, bottom = 78, 34, 58, 74
    xmin = float(joint["thickness_um"].min())
    xmax = float(joint["thickness_um"].max())
    ymin = float(joint["weighted_rmse"].min()) * 0.98
    ymax = float(joint["weighted_rmse"].max()) * 1.02
    colors = {
        "all_equal": "#4c78a8",
        "frequency_screened": "#f58518",
        "frequency_downweighted": "#54a24b",
        "continuous_frequency_weight": "#b279a2",
    }
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="{width/2:.1f}" y="30" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="20">波段权重下的 Dong/TMM 厚度剖面</text>',
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}" stroke="#333"/>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" stroke="#333"/>',
        f'<text x="{width/2:.1f}" y="{height-24}" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">厚度 (μm)</text>',
        f'<text x="22" y="{height/2:.1f}" transform="rotate(-90 22,{height/2:.1f})" text-anchor="middle" font-family="Arial, Microsoft YaHei" font-size="13">加权联合 RMSE</text>',
    ]
    for scenario, group in joint.groupby("scenario"):
        group = group.sort_values("thickness_um")
        points = " ".join(
            f'{_scale(row.thickness_um, xmin, xmax, left, width-right):.2f},{_scale(row.weighted_rmse, ymin, ymax, height-bottom, top):.2f}'
            for row in group.itertuples(index=False)
        )
        elements.append(f'<polyline fill="none" stroke="{colors[scenario]}" stroke-width="2" points="{points}"><title>{SCENARIO_LABELS.get(scenario, scenario)}</title></polyline>')
    legend_y = 50
    legend_x = left
    for scenario, color in colors.items():
        elements.append(f'<line x1="{legend_x}" y1="{legend_y}" x2="{legend_x+24}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        elements.append(f'<text x="{legend_x+30}" y="{legend_y+4}" font-family="Arial, Microsoft YaHei" font-size="12">{SCENARIO_LABELS.get(scenario, scenario)}</text>')
        legend_x += 215
    elements.append("</svg>")
    path.write_text("\n".join(elements) + "\n", encoding="utf-8-sig")


def markdown_table(df: pd.DataFrame) -> str:
    view = df.copy()
    if "scenario" in view.columns:
        view["scenario"] = view["scenario"].map(lambda value: SCENARIO_LABELS.get(str(value), str(value)))
    if "dataset" in view.columns:
        view["dataset"] = view["dataset"].map(lambda value: DATASET_LABELS.get(str(value), str(value)))
    rename_map = {
        "scenario": "权重口径",
        "best_thickness_um": "最佳厚度_um",
        "joint_weighted_rmse": "联合加权RMSE",
        "effective_points": "有效点数",
        "point_weight_sum": "点权重和",
        "delta_from_all_equal_um": "相对等权位移_um",
        "rmse_ratio_vs_all_equal": "相对等权RMSE比值",
        "dataset": "数据",
        "band": "波段",
        "band_weight": "波段权重",
        "reason": "原因",
    }
    view = view.rename(columns=rename_map)
    for col in view.columns:
        if pd.api.types.is_numeric_dtype(view[col]):
            view[col] = view[col].map(lambda value: f"{value:.6g}")
    header = "| " + " | ".join(view.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    body = ["| " + " | ".join(map(str, row)) + " |" for row in view.to_numpy()]
    return "\n".join([header, sep, *body])


def make_markdown(summary: pd.DataFrame, band_weights: pd.DataFrame) -> str:
    max_shift = float(summary["delta_from_all_equal_um"].abs().max())
    best_min = float(summary["best_thickness_um"].min())
    best_max = float(summary["best_thickness_um"].max())
    return f"""# 波段权重 TMM 厚度剖面诊断

## 问题

[[残差与频域证据对齐]]显示：部分高残差波段同时存在频域证据偏弱或周期波动偏大的问题。本轮要回答：

$$
\\text{{如果降低这些波段的影响，Dong/TMM 厚度低谷是否仍然稳定？}}
$$

本轮不重新优化材料参数，只固定当前受约束 Dong/TMM 参数，比较不同波段权重下的厚度剖面。因此它是稳健性检查，不是最终优化。

## 权重方案

- 全波段等权：所有基础波段等权；
- 频域筛选：只保留周期稳定且频域峰不弱的波段；
- 频域降权：频域证据偏弱或周期不稳的波段降权到 $0.35$；
- 连续频域权重：根据频域峰相对中位数和周期稳定性给连续权重。

## 结果

{markdown_table(summary)}

所有权重口径下的最佳厚度范围为：

$$
d^\\ast\\in[{best_min:.3f},{best_max:.3f}]\\ \\mu m.
$$

相对全波段等权口径，最大厚度位移为：

$$
\\max |\\Delta d|={max_shift:.3f}\\ \\mu m.
$$

## 当前解释

如果改变波段权重后 $d^\\ast$ 仍停留在 $7.4\\text{{--}}7.6\\ \\mu m$ 附近，说明当前厚度候选不是由某个单一异常波段决定的。若某个方案导致厚度明显跳出该区间，则说明候选厚度对波段选择敏感，必须回到波段筛选和物理模型。

本轮结果应用于论文时，只能写成“波段权重稳健性检查”，不能写成最终置信区间。

## 波段权重表

{markdown_table(band_weights[["dataset", "band", "scenario", "band_weight", "reason"]])}

## 下一步

下一步应检查“频域筛选”是否丢弃了太多数据点。如果它只依赖少数波段，即使厚度稳定，也不能作为最终主结果，只能作为稳健性旁证。最终论文更适合采用全波段主模型，并报告频域证据加权模型作为对比。
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    profile, summary, band_weights = build_profiles()
    profile.to_csv(OUTPUT_DIR / "band_weighted_tmm_profile.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(OUTPUT_DIR / "band_weighted_tmm_profile_summary.csv", index=False, encoding="utf-8-sig")
    band_weights.to_csv(OUTPUT_DIR / "band_weighted_tmm_band_weights.csv", index=False, encoding="utf-8-sig")
    write_svg(profile, FIGURE_DIR / "band_weighted_tmm_profile.svg")
    (OUTPUT_DIR / "band_weighted_tmm_profile_summary.md").write_text(
        make_markdown(summary, band_weights),
        encoding="utf-8-sig",
    )
    print("Wrote band-weighted TMM profile diagnostics.")


if __name__ == "__main__":
    main()
