from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

import spectral_pipeline as sp


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"


WINDOWS = [61, 101, 151]
MIN_SPACINGS = [200.0, 240.0, 280.0]
REGIONS = [(1000.0, 4000.0), (1200.0, 4000.0), (1500.0, 3500.0), (1700.0, 3000.0)]


def summarize_values(values):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return {"mean": np.nan, "std": np.nan, "min": np.nan, "max": np.nan, "count": 0}
    return {
        "mean": float(values.mean()),
        "std": float(values.std()),
        "min": float(values.min()),
        "max": float(values.max()),
        "count": int(len(values)),
    }


def run_one(config, window, min_spacing, region):
    df = sp.read_dataset(config)
    x_all = df["wavenumber_cm"].to_numpy()
    y_all = df["reflectance_pct"].to_numpy()
    mask = (x_all >= region[0]) & (x_all <= region[1])
    x = x_all[mask]
    y = y_all[mask]
    if len(x) < 10:
        return []

    peaks, troughs, _ = sp.separated_extrema(x, y, window=window, min_spacing_cm=min_spacing)
    rows = []
    for kind, indices in [("peak", peaks), ("trough", troughs)]:
        extrema_cm = x[indices]
        interval_d = sp.interval_thickness_um(extrema_cm, config["n0"], config["angle_deg"])
        interval_summary = summarize_values(interval_d)
        fod = sp.fit_fod(extrema_cm, config["n0"], config["angle_deg"])
        rows.append(
            {
                "dataset": f'{config["material"]}_{int(config["angle_deg"])}deg',
                "material": config["material"],
                "angle_deg": config["angle_deg"],
                "kind": kind,
                "window": window,
                "min_spacing_cm": min_spacing,
                "region_min_cm": region[0],
                "region_max_cm": region[1],
                "n_extrema": len(extrema_cm),
                "interval_mean_um": interval_summary["mean"],
                "interval_std_um": interval_summary["std"],
                "interval_count": interval_summary["count"],
                "fod_d_um": fod["d_um"] if fod else np.nan,
                "fod_r2": fod["r2"] if fod else np.nan,
                "fod_rss": fod["rss"] if fod else np.nan,
            }
        )
    return rows


def markdown_table(df):
    if len(df) == 0:
        return "No rows."
    rows = df.copy()
    for col in rows.columns:
        if pd.api.types.is_numeric_dtype(rows[col]):
            rows[col] = rows[col].map(lambda v: "" if pd.isna(v) else f"{v:.6g}")
        else:
            rows[col] = rows[col].astype(str)
    header = "| " + " | ".join(rows.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(rows.columns)) + " |"
    body = ["| " + " | ".join(map(str, row)) + " |" for row in rows.to_numpy()]
    return "\n".join([header, sep, *body])


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for config, window, min_spacing, region in product(sp.DATASETS, WINDOWS, MIN_SPACINGS, REGIONS):
        rows.extend(run_one(config, window, min_spacing, region))

    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT_DIR / "fod_sensitivity_results.csv", index=False, encoding="utf-8-sig")

    stable = (
        result.dropna(subset=["fod_d_um"])
        .groupby(["material", "angle_deg", "kind"])["fod_d_um"]
        .agg(["mean", "std", "min", "max", "count"])
        .reset_index()
    )
    by_dataset = (
        result.dropna(subset=["fod_d_um"])
        .groupby(["dataset"])["fod_d_um"]
        .agg(["mean", "std", "min", "max", "count"])
        .reset_index()
    )

    lines = [
        "# FOD 参数敏感性摘要",
        "",
        "这是常数折射率 FOD 模型的参数敏感性检查，不是最终厚度结果。",
        "",
        "## 参数网格",
        "",
        f"- 平滑窗口：{WINDOWS}",
        f"- 最小极值间距：{MIN_SPACINGS} cm^-1",
        f"- 波段范围：{REGIONS} cm^-1",
        "",
        "## 按数据集汇总",
        "",
        markdown_table(by_dataset),
        "",
        "## 按材料、角度和极值类型汇总",
        "",
        markdown_table(stable),
        "",
        "## 解释",
        "",
        "- 如果厚度范围很宽，说明模型强依赖峰谷提取或波段选择。",
        "- Si 需要优先复核，因为当前基线和 FOD 结果都与旧论文 5.13 um 差异明显。",
        "- 下一步应引入色散折射率 n(nu)，尤其是 SiC。",
    ]
    (OUTPUT_DIR / "fod_sensitivity_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(OUTPUT_DIR / "fod_sensitivity_summary.md")


if __name__ == "__main__":
    main()
