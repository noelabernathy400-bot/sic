from pathlib import Path

import numpy as np
import pandas as pd

import spectral_pipeline as sp


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"

REGION = (1000.0, 4000.0)
TARGET_SI_OLD_UM = 5.13


def extract_extrema_for_config(config, region=REGION, window=101, min_spacing_cm=240.0):
    df = sp.read_dataset(config)
    x_all = df["wavenumber_cm"].to_numpy()
    y_all = df["reflectance_pct"].to_numpy()
    mask = (x_all >= region[0]) & (x_all <= region[1])
    x = x_all[mask]
    y = y_all[mask]
    peaks, troughs, smooth = sp.separated_extrema(
        x,
        y,
        window=window,
        min_spacing_cm=min_spacing_cm,
    )
    return x, y, smooth, {"peak": x[peaks], "trough": x[troughs]}


def run_sic_dispersion():
    nk_table = sp.load_larruquert_sic_nk()
    rows = []
    sample_grid = np.arange(REGION[0], REGION[1] + 0.1, 250.0)
    sample_n, sample_k = sp.interpolate_nk(nk_table, sample_grid)
    nk_sample = pd.DataFrame(
        {
            "wavenumber_cm": sample_grid,
            "wavelength_um": 10000.0 / sample_grid,
            "n": sample_n,
            "k": sample_k,
        }
    )

    for config in [item for item in sp.DATASETS if item["material"] == "SiC"]:
        _, _, _, extrema = extract_extrema_for_config(config)
        dataset = f'{config["material"]}_{int(config["angle_deg"])}deg'
        for kind, extrema_cm in extrema.items():
            constant = sp.fit_fod(extrema_cm, config["n0"], config["angle_deg"])
            n_values, k_values = sp.interpolate_nk(nk_table, extrema_cm)
            dispersion = sp.fit_fod_dispersion(extrema_cm, n_values, k_values, config["angle_deg"])
            if not dispersion:
                continue
            rows.append(
                {
                    "dataset": dataset,
                    "material": config["material"],
                    "angle_deg": config["angle_deg"],
                    "kind": kind,
                    "n_points": len(extrema_cm),
                    "constant_n0": config["n0"],
                    "constant_fod_um": constant["d_um"] if constant else np.nan,
                    "dispersion_fod_um": dispersion["d_um"],
                    "delta_um": dispersion["d_um"] - (constant["d_um"] if constant else np.nan),
                    "delta_pct": (
                        (dispersion["d_um"] / constant["d_um"] - 1.0) * 100.0
                        if constant
                        else np.nan
                    ),
                    "r2": dispersion["r2"],
                    "rss": dispersion["rss"],
                    "n_min": dispersion["n_min"],
                    "n_max": dispersion["n_max"],
                    "k_min": dispersion["k_min"],
                    "k_max": dispersion["k_max"],
                    "reference_wavenumber_cm": dispersion["reference_wavenumber_cm"],
                }
            )
    return pd.DataFrame(rows), nk_sample


def solve_required_constant_n(extrema_cm, angle_deg, target_um):
    lower = max(np.sin(np.deg2rad(angle_deg)) + 1e-6, 1.001)
    upper = 6.0

    def value(n):
        fit = sp.fit_fod(extrema_cm, n, angle_deg)
        return np.nan if fit is None else fit["d_um"] - target_um

    f_low = value(lower)
    f_high = value(upper)
    if np.isnan(f_low) or np.isnan(f_high) or f_low * f_high > 0:
        return np.nan
    lo, hi = lower, upper
    for _ in range(80):
        mid = (lo + hi) / 2.0
        f_mid = value(mid)
        if f_low * f_mid <= 0:
            hi = mid
            f_high = f_mid
        else:
            lo = mid
            f_low = f_mid
    return (lo + hi) / 2.0


def run_si_review():
    rows = []
    for config in [item for item in sp.DATASETS if item["material"] == "Si"]:
        _, _, _, extrema = extract_extrema_for_config(config)
        dataset = f'{config["material"]}_{int(config["angle_deg"])}deg'
        for kind, extrema_cm in extrema.items():
            fit = sp.fit_fod(extrema_cm, config["n0"], config["angle_deg"])
            if not fit:
                continue
            required_n = solve_required_constant_n(extrema_cm, config["angle_deg"], TARGET_SI_OLD_UM)
            rows.append(
                {
                    "dataset": dataset,
                    "material": config["material"],
                    "angle_deg": config["angle_deg"],
                    "kind": kind,
                    "n_points": len(extrema_cm),
                    "current_n0": config["n0"],
                    "current_fod_um": fit["d_um"],
                    "target_old_um": TARGET_SI_OLD_UM,
                    "target_minus_current_um": TARGET_SI_OLD_UM - fit["d_um"],
                    "required_constant_n_for_target": required_n,
                    "r2": fit["r2"],
                    "rss": fit["rss"],
                }
            )
    return pd.DataFrame(rows)


def write_summary(sic_rows, si_rows, nk_sample):
    sic_grouped = (
        sic_rows.groupby(["angle_deg"])["dispersion_fod_um"]
        .agg(["mean", "std", "min", "max", "count"])
        .reset_index()
    )
    si_grouped = (
        si_rows.groupby(["angle_deg"])["current_fod_um"]
        .agg(["mean", "std", "min", "max", "count"])
        .reset_index()
    )
    lines = [
        "# 色散 FOD 与 Si 厚度复核",
        "",
        "本轮只把 SiC FOD 的相位因子从常数 n 升级为 Larruquert n(nu), k(nu) 插值。它仍然是基于峰谷极值的模型，还不是最终 TMM 全谱拟合。",
        "",
        "## 使用的 Larruquert SiC 光学常数",
        "",
        "- 本地来源：`Sources/Literature/SiC_Larruquert_refractiveindex.yml`。",
        f"- FOD 使用波段：{REGION[0]:.0f}-{REGION[1]:.0f} cm^-1。",
        "- 插值方式：先用 nu=10000/lambda_um 将波长转换为波数，再按波数线性插值。",
        "- 相位拟合使用实部 n(nu)；k(nu) 作为吸收诊断量输出。",
        "- 适用性提醒：该表对应室温沉积 SiC 薄膜，与 4H-SiC 外延样品的匹配仍是材料假设风险。",
        "",
        "### n,k 抽样表",
        "",
        sp.markdown_table(nk_sample),
        "",
        "## SiC 色散 FOD 结果",
        "",
        sp.markdown_table(sic_rows),
        "",
        "### SiC 按角度汇总",
        "",
        sp.markdown_table(sic_grouped),
        "",
        "## Si 厚度复核",
        "",
        "Si 复核保持当前常数折射率 FOD 基线。旧论文的 5.13 um 只作为诊断目标，不作为证据。",
        "",
        sp.markdown_table(si_rows),
        "",
        "### Si 按角度汇总",
        "",
        sp.markdown_table(si_grouped),
        "",
        "## 解释",
        "",
        "- 在 1000-4000 cm^-1 的大部分区域，Larruquert 给出的 SiC 实部折射率高于 n=2.60 基线，因此 FOD 厚度相对常数折射率结果下降。",
        "- 本波段低波数侧 k(nu) 增大，说明吸收可能影响极值可靠性；不能直接把全波段当作最终证据。",
        "- Si 数据在 n=3.42 下仍集中在 3.4-3.6 um。若用同一极值链条达到 5.13 um，需要远低于 Si 基线的等效常数折射率，所以旧值暂不被当前 FOD 复核支持。",
        "- 下一步：避开高吸收或边缘波段，在同一波段上比较常数折射率 FOD、色散 FOD 和 TMM/Airy 全谱拟合。",
    ]
    (OUTPUT_DIR / "dispersion_fod_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sic_rows, nk_sample = run_sic_dispersion()
    si_rows = run_si_review()
    nk_sample.to_csv(OUTPUT_DIR / "sic_larruquert_nk_sample.csv", index=False, encoding="utf-8-sig")
    sic_rows.to_csv(OUTPUT_DIR / "dispersion_fod_results.csv", index=False, encoding="utf-8-sig")
    si_rows.to_csv(OUTPUT_DIR / "si_thickness_review.csv", index=False, encoding="utf-8-sig")
    write_summary(sic_rows, si_rows, nk_sample)
    print(OUTPUT_DIR / "dispersion_fod_summary.md")


if __name__ == "__main__":
    main()
