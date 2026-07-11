from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from dong2012_tmm_uncertainty import (
    load_coordinate_final_state,
    prepare_angle_data,
    profile_objective,
)


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"

CONFIGS = [
    {"attachment": "附件1.xlsx", "material": "SiC", "angle_deg": 10.0, "n0": 2.60},
    {"attachment": "附件2.xlsx", "material": "SiC", "angle_deg": 15.0, "n0": 2.60},
]

VARIABLE_GROUPS = [
    ("epi_nu_p_scale", ["epi_nu_p_scale"], 0.125),
    ("sub_nu_p_scale", ["sub_nu_p_scale"], 0.125),
    ("epi_gamma_scale", ["epi_gamma_scale"], 0.125),
    ("sub_gamma_scale", ["sub_gamma_scale"], 0.125),
    ("epi_phonon_scale", ["epi_gamma_l_scale", "epi_gamma_t_scale"], 0.125),
    ("sub_phonon_scale", ["sub_gamma_l_scale", "sub_gamma_t_scale"], 0.125),
]

OFFSETS = [-2, -1, 0, 1, 2]
N_PASSES = 2
LOWER_BOUND = 0.1
UPPER_BOUND = 2.5


def clipped_candidates(center: float, step: float) -> list[float]:
    values = []
    for offset in OFFSETS:
        value = min(UPPER_BOUND, max(LOWER_BOUND, center + offset * step))
        value = round(value, 6)
        if value not in values:
            values.append(value)
    return values


def set_group(state: dict[str, float], keys: list[str], value: float) -> dict[str, float]:
    candidate = dict(state)
    for key in keys:
        candidate[key] = value
    return candidate


def evaluate(scale_state: dict[str, float]) -> dict[str, float]:
    angle_data = [prepare_angle_data(config, scale_state) for config in CONFIGS]
    _, best_thickness, best_rmse = profile_objective(angle_data)
    angle_rows = []
    for item in angle_data:
        best = None
        for idx, thickness in enumerate(np.round(np.arange(7.20, 7.701, 0.005), 6)):
            from dong2012_tmm_uncertainty import affine_fit_fast

            rmse, scale, offset, _, _ = affine_fit_fast(
                item["model_matrix"][idx],
                item["observed"],
            )
            row = {
                "dataset": item["dataset"],
                "best_thickness_um": float(thickness),
                "rmse": float(rmse),
                "affine_scale": float(scale),
                "affine_offset": float(offset),
            }
            if best is None or (row["rmse"], row["best_thickness_um"]) < (
                best["rmse"],
                best["best_thickness_um"],
            ):
                best = row
        angle_rows.append(best)
    return {
        "joint_best_thickness_um": best_thickness,
        "joint_mean_rmse": best_rmse,
        "joint_max_rmse": max(row["rmse"] for row in angle_rows),
        "joint_std_rmse": float(np.std([row["rmse"] for row in angle_rows], ddof=1)),
        "angle_rows": angle_rows,
    }


def run_local_refinement():
    current_state = load_coordinate_final_state()
    baseline_result = evaluate(current_state)
    candidate_rows = [
        {
            "pass_id": 0,
            "variable_group": "initial",
            "candidate_value": np.nan,
            **current_state,
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
            "joint_best_thickness_um": baseline_result["joint_best_thickness_um"],
            "joint_mean_rmse": baseline_result["joint_mean_rmse"],
            "joint_max_rmse": baseline_result["joint_max_rmse"],
            "joint_std_rmse": baseline_result["joint_std_rmse"],
        }
    ]

    for pass_id in range(1, N_PASSES + 1):
        for group_name, keys, step in VARIABLE_GROUPS:
            center = current_state[keys[0]]
            trial_rows = []
            for value in clipped_candidates(center, step):
                candidate_state = set_group(current_state, keys, value)
                result = evaluate(candidate_state)
                row = {
                    "pass_id": pass_id,
                    "variable_group": group_name,
                    "candidate_value": value,
                    **candidate_state,
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
                    "joint_best_thickness_um": chosen["joint_best_thickness_um"],
                    "joint_mean_rmse": chosen["joint_mean_rmse"],
                    "joint_max_rmse": chosen["joint_max_rmse"],
                    "joint_std_rmse": chosen["joint_std_rmse"],
                }
            )
    return pd.DataFrame(candidate_rows), pd.DataFrame(chosen_rows)


def write_summary(candidates: pd.DataFrame, chosen: pd.DataFrame) -> None:
    initial = chosen.iloc[0]
    final = chosen.iloc[-1]
    improvement = initial["joint_mean_rmse"] - final["joint_mean_rmse"]
    relative = 100.0 * improvement / initial["joint_mean_rmse"]
    lines = [
        "# Dong/TMM 局部细化坐标搜索摘要",
        "",
        "本脚本用于在无 `scipy` 环境下，对分阶段粗网格坐标搜索的最终状态做局部细化。它不是连续全局优化，而是围绕当前参数做小步长坐标检查。",
        "",
        "## 搜索设计",
        "",
        "- 初始状态来自 `dong2012_tmm_coordinate_search_chosen.csv` 的最终行。",
        "- 每次只调整一个参数组，候选值为中心值附近的 $-2,-1,0,1,2$ 个局部步长。",
        "- 局部步长为 $0.125$，搜索边界为 $[0.1,2.5]$。",
        "- 重复两轮坐标遍历。",
        "- 每个候选状态下重新扫描厚度 $d$，目标函数仍为双角度联合平均 RMSE。",
        "",
        "## 结果",
        "",
        f"- 初始联合 RMSE：`{initial['joint_mean_rmse']:.8f}`，厚度低谷：${initial['joint_best_thickness_um']:.3f}\\ \\mu m$。",
        f"- 细化后联合 RMSE：`{final['joint_mean_rmse']:.8f}`，厚度低谷：${final['joint_best_thickness_um']:.3f}\\ \\mu m$。",
        f"- 绝对改善：`{improvement:.8f}`。",
        f"- 相对改善：`{relative:.3f}%`。",
        "",
        "## 细化路径",
        "",
        "| pass | 参数组 | 选中值 | 厚度低谷 $\\mu m$ | joint RMSE | max RMSE |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in chosen.iterrows():
        lines.append(
            "| {pass_id} | {variable_group} | {chosen_value} | {joint_best_thickness_um:.3f} | {joint_mean_rmse:.8f} | {joint_max_rmse:.8f} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## 解释边界",
            "",
            "如果局部细化只带来很小 RMSE 改善，说明当前粗网格状态已经处于一个较平坦的局部区域；这支持候选厚度区间的局部稳定性，但仍不能证明全局最优。",
            "",
            "如果厚度低谷仍留在 $7.4\\text{--}7.6\\ \\mu m$，说明局部参数微调没有推翻当前候选区间。",
        ]
    )
    (OUTPUT_DIR / "dong2012_tmm_local_refinement_summary.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8-sig",
    )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates, chosen = run_local_refinement()
    candidates.to_csv(
        OUTPUT_DIR / "dong2012_tmm_local_refinement_candidates.csv",
        index=False,
        encoding="utf-8-sig",
    )
    chosen.to_csv(
        OUTPUT_DIR / "dong2012_tmm_local_refinement_chosen.csv",
        index=False,
        encoding="utf-8-sig",
    )
    write_summary(candidates, chosen)


if __name__ == "__main__":
    main()
