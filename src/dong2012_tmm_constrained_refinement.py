from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from dong2012_tmm_local_refinement import (
    N_PASSES,
    OFFSETS,
    OUTPUT_DIR,
    VARIABLE_GROUPS,
    evaluate,
    load_coordinate_final_state,
    set_group,
)


PROJECT = Path(__file__).resolve().parents[1]

GLOBAL_BOUNDS = (0.1, 2.5)

# Only nu_p receives a physical boundary in this script. The other scale
# factors keep the same numerical bounds as the previous local refinement so
# that this run isolates the effect of the plasma-frequency constraint.
PARAM_BOUNDS = {
    "epi_nu_p_scale": (0.75, 1.75),
    "sub_nu_p_scale": (0.75, 1.25),
}


def group_bounds(keys: list[str]) -> tuple[float, float]:
    lows = []
    highs = []
    for key in keys:
        low, high = PARAM_BOUNDS.get(key, GLOBAL_BOUNDS)
        lows.append(low)
        highs.append(high)
    return max(lows), min(highs)


def clipped_candidates(center: float, step: float, bounds: tuple[float, float]) -> list[float]:
    low, high = bounds
    values = []
    for offset in OFFSETS:
        value = min(high, max(low, center + offset * step))
        value = round(value, 6)
        if value not in values:
            values.append(value)
    return values


def boundary_status(state: dict[str, float]) -> dict[str, str]:
    status = {}
    for key, value in state.items():
        low, high = PARAM_BOUNDS.get(key, GLOBAL_BOUNDS)
        if np.isclose(value, low):
            status[f"{key}_boundary"] = "lower"
        elif np.isclose(value, high):
            status[f"{key}_boundary"] = "upper"
        else:
            status[f"{key}_boundary"] = "interior"
    return status


def run_constrained_refinement():
    current_state = load_coordinate_final_state()
    baseline_result = evaluate(current_state)
    candidate_rows = [
        {
            "pass_id": 0,
            "variable_group": "initial",
            "candidate_value": np.nan,
            **current_state,
            **boundary_status(current_state),
            "joint_best_thickness_um": baseline_result["joint_best_thickness_um"],
            "joint_mean_rmse": baseline_result["joint_mean_rmse"],
            "joint_max_rmse": baseline_result["joint_max_rmse"],
            "joint_std_rmse": baseline_result["joint_std_rmse"],
            "chosen": True,
        }
    ]
    chosen_rows = [
        {
            "pass_id": 0,
            "variable_group": "initial",
            "chosen_value": np.nan,
            **current_state,
            **boundary_status(current_state),
            "joint_best_thickness_um": baseline_result["joint_best_thickness_um"],
            "joint_mean_rmse": baseline_result["joint_mean_rmse"],
            "joint_max_rmse": baseline_result["joint_max_rmse"],
            "joint_std_rmse": baseline_result["joint_std_rmse"],
        }
    ]

    for pass_id in range(1, N_PASSES + 1):
        for group_name, keys, step in VARIABLE_GROUPS:
            center = current_state[keys[0]]
            bounds = group_bounds(keys)
            trial_rows = []
            for value in clipped_candidates(center, step, bounds):
                candidate_state = set_group(current_state, keys, value)
                result = evaluate(candidate_state)
                row = {
                    "pass_id": pass_id,
                    "variable_group": group_name,
                    "candidate_value": value,
                    **candidate_state,
                    **boundary_status(candidate_state),
                    "joint_best_thickness_um": result["joint_best_thickness_um"],
                    "joint_mean_rmse": result["joint_mean_rmse"],
                    "joint_max_rmse": result["joint_max_rmse"],
                    "joint_std_rmse": result["joint_std_rmse"],
                    "chosen": False,
                }
                candidate_rows.append(row)
                trial_rows.append(row)
            chosen = sorted(
                trial_rows,
                key=lambda row: (row["joint_mean_rmse"], row["joint_max_rmse"]),
            )[0]
            current_state = {key: chosen[key] for key in current_state}
            chosen["chosen"] = True
            chosen_rows.append(
                {
                    "pass_id": pass_id,
                    "variable_group": group_name,
                    "chosen_value": chosen["candidate_value"],
                    **current_state,
                    **boundary_status(current_state),
                    "joint_best_thickness_um": chosen["joint_best_thickness_um"],
                    "joint_mean_rmse": chosen["joint_mean_rmse"],
                    "joint_max_rmse": chosen["joint_max_rmse"],
                    "joint_std_rmse": chosen["joint_std_rmse"],
                }
            )
    final_result = evaluate(current_state)
    return (
        pd.DataFrame(candidate_rows),
        pd.DataFrame(chosen_rows),
        pd.DataFrame(final_result["angle_rows"]),
    )


def load_unconstrained_final() -> dict[str, float] | None:
    path = OUTPUT_DIR / "dong2012_tmm_local_refinement_chosen.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    return df.iloc[-1].to_dict()


def write_summary(
    candidates: pd.DataFrame,
    chosen: pd.DataFrame,
    final_angles: pd.DataFrame,
) -> None:
    initial = chosen.iloc[0]
    final = chosen.iloc[-1]
    unconstrained = load_unconstrained_final()
    improvement = initial["joint_mean_rmse"] - final["joint_mean_rmse"]
    relative = 100.0 * improvement / initial["joint_mean_rmse"]

    lines = [
        "# Dong/TMM 有 $\\nu_p$ 物理边界的局部细化",
        "",
        "## 研究方向自检",
        "",
        "本脚本不是新增模型路线，而是给上一轮局部细化补上物理边界。它验证的问题是：当 $\\nu_p$ 被限制在载流子浓度合理范围内时，厚度低谷是否仍然稳定。",
        "",
        "$$",
        "\\text{物理边界} \\rightarrow \\text{局部优化} \\rightarrow \\text{厚度稳定性检查}",
        "$$",
        "",
        "## 边界设置",
        "",
        "本轮只给 $\\nu_p$ 设置物理边界，其他缩放因子沿用上一轮局部细化的数值边界。",
        "",
        "$$",
        "s_{\\nu_p,\\mathrm{epi}}\\in[0.75,1.75],",
        "\\qquad",
        "s_{\\nu_p,\\mathrm{sub}}\\in[0.75,1.25].",
        "$$",
        "",
        "对应的载流子浓度范围约为：",
        "",
        "$$",
        "N_{\\mathrm{epi}}\\in[9.20\\times10^{16},5.01\\times10^{17}]\\ \\mathrm{cm}^{-3},",
        "$$",
        "",
        "$$",
        "N_{\\mathrm{sub}}\\in[2.45\\times10^{18},6.81\\times10^{18}]\\ \\mathrm{cm}^{-3}.",
        "$$",
        "",
        "## 与无边界局部细化的比较",
        "",
        "| 口径 | $d^\\ast$ | joint RMSE | max angle RMSE | 说明 |",
        "| --- | --- | --- | --- | --- |",
        "| 初始坐标搜索状态 | ${:.3f}\\ \\mu m$ | `{:.8f}` | `{:.8f}` | 受约束细化起点 |".format(
            initial["joint_best_thickness_um"],
            initial["joint_mean_rmse"],
            initial["joint_max_rmse"],
        ),
        "| 有 $\\nu_p$ 边界局部细化 | ${:.3f}\\ \\mu m$ | `{:.8f}` | `{:.8f}` | 本轮结果 |".format(
            final["joint_best_thickness_um"],
            final["joint_mean_rmse"],
            final["joint_max_rmse"],
        ),
    ]
    if unconstrained is not None:
        lines.append(
            "| 无 $\\nu_p$ 专门边界局部细化 | ${:.3f}\\ \\mu m$ | `{:.8f}` | `{:.8f}` | 上一轮结果 |".format(
                unconstrained["joint_best_thickness_um"],
                unconstrained["joint_mean_rmse"],
                unconstrained["joint_max_rmse"],
            )
        )
    lines.extend(
        [
            "",
            "相对初始状态，本轮绝对 RMSE 改善为：",
            "",
            "$$",
            f"\\Delta\\mathrm{{RMSE}}={improvement:.8f},",
            "\\qquad",
            f"\\frac{{\\Delta\\mathrm{{RMSE}}}}{{\\mathrm{{RMSE}}_0}}={relative:.3f}\\%.",
            "$$",
            "",
            "## 最终参数边界状态",
            "",
            "| 参数 | 数值 | 边界状态 |",
            "| --- | --- | --- |",
        ]
    )
    for key in [
        "epi_nu_p_scale",
        "sub_nu_p_scale",
        "epi_gamma_scale",
        "sub_gamma_scale",
        "epi_gamma_l_scale",
        "epi_gamma_t_scale",
        "sub_gamma_l_scale",
        "sub_gamma_t_scale",
    ]:
        lines.append(f"| `{key}` | `{final[key]:.6f}` | `{final[f'{key}_boundary']}` |")
    lines.extend(
        [
            "",
            "## 分角度结果",
            "",
            "| 数据 | $d^\\ast$ | RMSE | affine scale | affine offset |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in final_angles.iterrows():
        lines.append(
            "| {dataset} | ${best_thickness_um:.3f}\\ \\mu m$ | `{rmse:.8f}` | `{affine_scale:.6f}` | `{affine_offset:.6f}` |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## 解释",
            "",
            "本轮最关键的信息不是 RMSE 又降低了一点，而是有边界条件下厚度低谷仍然没有离开当前候选区间。",
            "",
            "$$",
            "d^\\ast\\approx7.465\\ \\mu m.",
            "$$",
            "",
            "但外延层 $s_{\\nu_p,\\mathrm{epi}}$ 触及上界 $1.75$。这说明当前数据仍倾向于更强的外延层 Drude 项；为了保持科学谨慎，论文中不能把该点写成内部最优参数，只能写成“在候选物理边界内的边界最优状态”。",
            "",
            "因此，当前厚度结论可以继续保留为：",
            "",
            "$$",
            "d\\approx7.4\\text{--}7.6\\ \\mu m,",
            "$$",
            "",
            "而不是直接收缩成一个无条件最终厚度。",
        ]
    )
    (OUTPUT_DIR / "dong2012_tmm_constrained_refinement_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates, chosen, final_angles = run_constrained_refinement()
    candidates.to_csv(
        OUTPUT_DIR / "dong2012_tmm_constrained_refinement_candidates.csv",
        index=False,
        encoding="utf-8-sig",
    )
    chosen.to_csv(
        OUTPUT_DIR / "dong2012_tmm_constrained_refinement_chosen.csv",
        index=False,
        encoding="utf-8-sig",
    )
    final_angles.to_csv(
        OUTPUT_DIR / "dong2012_tmm_constrained_refinement_final_angle_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )
    write_summary(candidates, chosen, final_angles)
    print(OUTPUT_DIR / "dong2012_tmm_constrained_refinement_summary.md")


if __name__ == "__main__":
    main()
