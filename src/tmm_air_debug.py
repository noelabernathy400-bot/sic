from pathlib import Path

import numpy as np
import pandas as pd

import spectral_pipeline as sp


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"

REGION = (1500.0, 4000.0)
THICKNESS_GRID_UM = np.linspace(3.0, 8.0, 251)
CONTRAST_DELTAS = [0.0, 0.05, 0.15, 0.30]


def complex_cos_inside(angle_deg, n_layer, n_incident=1.0):
    theta0 = np.deg2rad(angle_deg)
    n_layer = np.asarray(n_layer, dtype=complex)
    return np.sqrt(1.0 - (n_incident * np.sin(theta0) / n_layer) ** 2)


def fresnel_r(n_i, cos_i, n_j, cos_j, polarization):
    if polarization == "s":
        numerator = n_i * cos_i - n_j * cos_j
        denominator = n_i * cos_i + n_j * cos_j
    elif polarization == "p":
        numerator = n_j * cos_i - n_i * cos_j
        denominator = n_j * cos_i + n_i * cos_j
    else:
        raise ValueError(f"Unknown polarization: {polarization}")
    return numerator / denominator


def airy_reflectance(
    wavenumber_cm,
    thickness_um,
    n_layer,
    n_substrate,
    angle_deg,
    polarization,
):
    nu = np.asarray(wavenumber_cm, dtype=float)
    n0 = 1.0 + 0.0j
    n1 = np.asarray(n_layer, dtype=complex)
    n2 = np.asarray(n_substrate, dtype=complex)
    cos0 = np.cos(np.deg2rad(angle_deg)) + 0.0j
    cos1 = complex_cos_inside(angle_deg, n1, n0)
    cos2 = complex_cos_inside(angle_deg, n2, n0)
    r01 = fresnel_r(n0, cos0, n1, cos1, polarization)
    r12 = fresnel_r(n1, cos1, n2, cos2, polarization)
    delta = 2.0 * np.pi * n1 * cos1 * thickness_um * nu / 10000.0
    phase = np.exp(2.0j * delta)
    r_total = (r01 + r12 * phase) / (1.0 + r01 * r12 * phase)
    return np.abs(r_total) ** 2


def unpolarized_reflectance(wavenumber_cm, thickness_um, n_layer, n_substrate, angle_deg):
    rs = airy_reflectance(wavenumber_cm, thickness_um, n_layer, n_substrate, angle_deg, "s")
    rp = airy_reflectance(wavenumber_cm, thickness_um, n_layer, n_substrate, angle_deg, "p")
    return 0.5 * (rs + rp)


def affine_fit_error(model_reflectance, observed_reflectance):
    x = np.asarray(model_reflectance, dtype=float)
    y = np.asarray(observed_reflectance, dtype=float)
    design = np.column_stack([x, np.ones_like(x)])
    coeff, *_ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coeff
    residual = y - fitted
    rmse = float(np.sqrt(np.mean(residual**2)))
    return rmse, float(coeff[0]), float(coeff[1])


def read_sic_dataset(config):
    df = sp.read_dataset(config)
    x = df["wavenumber_cm"].to_numpy(dtype=float)
    y = df["reflectance_pct"].to_numpy(dtype=float) / 100.0
    mask = (x >= REGION[0]) & (x <= REGION[1])
    x = x[mask]
    y = y[mask]
    if len(x) > 1200:
        stride = int(np.ceil(len(x) / 1200))
        x = x[::stride]
        y = y[::stride]
    return x, y


def run_debug_grid():
    nk_table = sp.load_larruquert_sic_nk()
    rows = []
    sanity_rows = []
    for config in [item for item in sp.DATASETS if item["material"] == "SiC"]:
        dataset = f'{config["material"]}_{int(config["angle_deg"])}deg'
        nu, observed = read_sic_dataset(config)
        n_real, k_ext = sp.interpolate_nk(nk_table, nu)
        n_layer = n_real + 1j * k_ext
        for contrast_delta in CONTRAST_DELTAS:
            n_substrate = (n_real + contrast_delta) + 1j * k_ext
            first_curve = unpolarized_reflectance(
                nu,
                THICKNESS_GRID_UM[0],
                n_layer,
                n_substrate,
                config["angle_deg"],
            )
            last_curve = unpolarized_reflectance(
                nu,
                THICKNESS_GRID_UM[-1],
                n_layer,
                n_substrate,
                config["angle_deg"],
            )
            thickness_sensitivity = float(np.sqrt(np.mean((first_curve - last_curve) ** 2)))
            sanity_rows.append(
                {
                    "dataset": dataset,
                    "angle_deg": config["angle_deg"],
                    "contrast_delta_n": contrast_delta,
                    "thickness_sensitivity_rmse": thickness_sensitivity,
                }
            )
            for thickness_um in THICKNESS_GRID_UM:
                predicted = unpolarized_reflectance(
                    nu,
                    thickness_um,
                    n_layer,
                    n_substrate,
                    config["angle_deg"],
                )
                rmse, scale, offset = affine_fit_error(predicted, observed)
                rows.append(
                    {
                        "dataset": dataset,
                        "angle_deg": config["angle_deg"],
                        "contrast_delta_n": contrast_delta,
                        "thickness_um": thickness_um,
                        "affine_rmse": rmse,
                        "affine_scale": scale,
                        "affine_offset": offset,
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(sanity_rows)


def write_summary(grid, sanity):
    best = (
        grid.sort_values("affine_rmse")
        .groupby(["dataset", "contrast_delta_n"], as_index=False)
        .first()
        .sort_values(["dataset", "contrast_delta_n"])
    )
    lines = [
        "# Airy/TMM 最小调试摘要",
        "",
        "本输出只用于调试 Airy 单层反射模型，不是最终厚度结果。",
        "",
        "## 模型口径",
        "",
        "- 结构：空气 / SiC 外延层 / SiC 衬底。",
        f"- 调试波段：{REGION[0]:.0f}-{REGION[1]:.0f} cm^-1。",
        "- 外延层复折射率使用 Larruquert SiC n,k 插值。",
        "- 衬底折射率用 `n_substrate = n_layer + contrast_delta_n` 做人工光学差异测试。",
        "- 拟合误差使用 `R_obs ≈ a R_model + b` 的线性标定后 RMSE。",
        "- `contrast_delta_n = 0` 是同质界面 sanity check，不应产生可靠厚度识别。",
        "",
        "## 厚度敏感性 sanity check",
        "",
        sp.markdown_table(sanity),
        "",
        "## 各人工折射率差下的网格搜索最小误差",
        "",
        sp.markdown_table(
            best[
                [
                    "dataset",
                    "angle_deg",
                    "contrast_delta_n",
                    "thickness_um",
                    "affine_rmse",
                    "affine_scale",
                    "affine_offset",
                ]
            ]
        ),
        "",
        "## 调试解释",
        "",
        "- 当 `contrast_delta_n = 0` 时，外延层和衬底没有光学界面，模型对厚度的敏感性应接近 0；这用于检查代码物理边界。",
        "- 当人为引入 `contrast_delta_n` 时，模型会出现厚度敏感性，但这个差值不是题目给定的真实材料参数。",
        "- 因此本表中的最佳厚度只能说明网格搜索流程能工作，不能作为论文结果。",
        "- 下一步必须从 Dong2012 或标准/材料模型中提取更合理的外延层与衬底介电函数差异。",
    ]
    (OUTPUT_DIR / "tmm_air_debug_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    grid, sanity = run_debug_grid()
    grid.to_csv(OUTPUT_DIR / "tmm_air_debug_grid.csv", index=False, encoding="utf-8-sig")
    sanity.to_csv(OUTPUT_DIR / "tmm_air_debug_sanity.csv", index=False, encoding="utf-8-sig")
    write_summary(grid, sanity)
    print(OUTPUT_DIR / "tmm_air_debug_summary.md")


if __name__ == "__main__":
    main()
