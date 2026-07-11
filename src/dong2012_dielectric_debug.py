from pathlib import Path

import numpy as np
import pandas as pd

import spectral_pipeline as sp
from tmm_air_debug import affine_fit_error, unpolarized_reflectance


PROJECT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT / "Experiments" / "outputs"

REGION = (1500.0, 4000.0)
THICKNESS_GRID_UM = np.linspace(3.0, 8.0, 251)

DONG_FIXED = {
    "nu_L_perp": 970.1,
    "nu_T_perp": 797.3,
    "eps_inf_perp": 6.56,
}

DONG_TABLE2 = {
    "epilayer": {
        "nu_p_perp": 72.98,
        "gamma": 59.72,
        "gamma_L": 3.67,
        "gamma_T": 1.42,
    },
    "substrate": {
        "nu_p_perp": 376.60,
        "gamma": 447.46,
        "gamma_L": 25.27,
        "gamma_T": 5.79,
    },
}


def dong_epsilon_perp(wavenumber_cm, params):
    """Dong2012-style perpendicular dielectric function.

    This is a model-transfer debug implementation based on the extracted
    formula. It uses the perpendicular component only and must be checked
    against the PDF formula before being used as a final fitting model.
    """
    nu = np.asarray(wavenumber_cm, dtype=float)
    eps_inf = DONG_FIXED["eps_inf_perp"]
    nu_L = DONG_FIXED["nu_L_perp"]
    nu_T = DONG_FIXED["nu_T_perp"]
    gamma_L = params["gamma_L"]
    gamma_T = params["gamma_T"]
    nu_p = params["nu_p_perp"]
    gamma = params["gamma"]
    lattice = (nu_L**2 - nu**2 - 1j * gamma_L * nu) / (
        nu_T**2 - nu**2 - 1j * gamma_T * nu
    )
    drude = (nu_p**2) / (nu * (nu + 1j * gamma))
    return eps_inf * (lattice - drude)


def nk_from_epsilon(epsilon):
    n_complex = np.sqrt(epsilon.astype(complex))
    n_real = np.real(n_complex)
    k_ext = np.imag(n_complex)
    negative = k_ext < 0
    if np.any(negative):
        n_complex[negative] *= -1
    return n_complex


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


def write_nk_sample():
    grid = np.arange(REGION[0], REGION[1] + 0.1, 250.0)
    rows = []
    for role, params in DONG_TABLE2.items():
        epsilon = dong_epsilon_perp(grid, params)
        n_complex = nk_from_epsilon(epsilon)
        for nu, eps, nc in zip(grid, epsilon, n_complex):
            rows.append(
                {
                    "role": role,
                    "wavenumber_cm": nu,
                    "epsilon_real": float(np.real(eps)),
                    "epsilon_imag": float(np.imag(eps)),
                    "n": float(np.real(nc)),
                    "k": float(np.imag(nc)),
                }
            )
    return pd.DataFrame(rows)


def run_thickness_debug():
    rows = []
    for config in [item for item in sp.DATASETS if item["material"] == "SiC"]:
        dataset = f'{config["material"]}_{int(config["angle_deg"])}deg'
        nu, observed = read_sic_dataset(config)
        n_epi = nk_from_epsilon(dong_epsilon_perp(nu, DONG_TABLE2["epilayer"]))
        n_sub = nk_from_epsilon(dong_epsilon_perp(nu, DONG_TABLE2["substrate"]))
        for thickness_um in THICKNESS_GRID_UM:
            predicted = unpolarized_reflectance(
                nu,
                thickness_um,
                n_epi,
                n_sub,
                config["angle_deg"],
            )
            rmse, scale, offset = affine_fit_error(predicted, observed)
            rows.append(
                {
                    "dataset": dataset,
                    "angle_deg": config["angle_deg"],
                    "thickness_um": thickness_um,
                    "affine_rmse": rmse,
                    "affine_scale": scale,
                    "affine_offset": offset,
                }
            )
    return pd.DataFrame(rows)


def write_summary(nk_sample, grid):
    best = (
        grid.sort_values("affine_rmse")
        .groupby(["dataset"], as_index=False)
        .first()
        .sort_values(["dataset"])
    )
    lines = [
        "# Dong2012 介电函数调试摘要",
        "",
        "本输出用于把 Dong2012 的介电函数思想转化为可运行代码，不是最终厚度结果。",
        "",
        "## 调试口径",
        "",
        f"- 波段：${REGION[0]:.0f}\\text{{--}}{REGION[1]:.0f}\\ cm^{{-1}}$。",
        "- 只使用垂直于 c 轴的介电函数分量。",
        "- 固定声子参数来自 Dong2012 正文。",
        "- 外延层和衬底的 $\\nu_{p,\\perp}$、$\\gamma$、$\\Gamma_L$、$\\Gamma_T$ 暂用 Dong2012 表 2 参数。",
        "- 这些参数属于 Dong2012 样品，不是本题附件样品。",
        "",
        "## n,k 抽样",
        "",
        sp.markdown_table(nk_sample),
        "",
        "## 使用 Dong2012 表 2 参数进行本题附件网格调试",
        "",
        sp.markdown_table(best),
        "",
        "## 解释",
        "",
        "- 这个脚本把人工 $\\Delta n$ 替换为文献介电函数产生的外延层/衬底差异。",
        "- 由于参数来自 Dong2012 的 $14.4\\ \\mu m$ 样品，不能把本表最佳厚度当作本题结果。",
        "- 如果最佳厚度区间与 FOD/TMM 人工调试相近，只能说明模型相位链条具有一致性；最终仍需对本题数据拟合材料参数或做敏感性分析。",
        "- 下一步应把 $\\nu_{p,\\perp}$、$\\gamma$ 或等效参数作为待拟合/敏感性参数，而不是固定为 Dong2012 表 2。",
    ]
    (OUTPUT_DIR / "dong2012_dielectric_debug_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    nk_sample = write_nk_sample()
    grid = run_thickness_debug()
    nk_sample.to_csv(OUTPUT_DIR / "dong2012_dielectric_nk_sample.csv", index=False, encoding="utf-8-sig")
    grid.to_csv(OUTPUT_DIR / "dong2012_dielectric_thickness_grid.csv", index=False, encoding="utf-8-sig")
    write_summary(nk_sample, grid)
    print(OUTPUT_DIR / "dong2012_dielectric_debug_summary.md")


if __name__ == "__main__":
    main()
