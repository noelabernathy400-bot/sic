"""Rebuild the English-paper figures from recorded SiC experiment outputs.

The script changes presentation only: it reads existing outputs and never
re-estimates thickness or changes any reported result.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(r"D:\ai\sic")
DATA = ROOT / "experiments"
OUT = Path(__file__).resolve().parent
COLORS = {10.0: "#0072B2", 15.0: "#D55E00"}

plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 8,
    "axes.labelsize": 9,
    "axes.titlesize": 10,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "savefig.dpi": 350,
})


def finish(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=350, bbox_inches="tight")
    plt.close(fig)


def raw_spectra():
    df = pd.read_csv(DATA / "dong2012_tmm_bestfit_curves.csv")
    fig, ax = plt.subplots(figsize=(6.4, 2.65))
    for angle, sub in df.groupby("angle_deg"):
        ax.plot(sub.wavenumber_cm, sub.observed_reflectance, lw=0.8,
                color=COLORS[angle], label=f"{int(angle)}° incidence")
    ax.set(xlabel=r"Wavenumber (cm$^{-1}$)", ylabel="Reflectance")
    ax.legend(frameon=False, ncol=2, loc="upper right")
    finish(fig, "en_raw_dual_angle.png")


def fft_seed():
    df = pd.read_csv(DATA / "fft_frequency_seed_results.csv")
    df = df[(df.band == "1500-4000") & (df.status == "ok")]
    labels = {"constant_n": "Constant n = 2.60", "larruquert_n_eff": "Larruquert n_eff", "dong_constrained_n_eff": "Constrained Dong n_eff"}
    fig, ax = plt.subplots(figsize=(6.2, 2.8))
    x = np.arange(len(labels)); width = 0.34
    for j, angle in enumerate([10.0, 15.0]):
        vals = [df[(df.angle_deg == angle) & (df.n_model == k)].thickness_um.iloc[0] for k in labels]
        ax.bar(x + (j - .5) * width, vals, width, label=f"{int(angle)}°", color=COLORS[angle])
    ax.set(xticks=x, xticklabels=list(labels.values()), ylabel=r"FFT thickness seed ($\mu$m)")
    ax.tick_params(axis="x", rotation=13)
    ax.legend(frameon=False, title="Incidence")
    finish(fig, "en_fft_thickness_seed.png")


def sliding_fft():
    df = pd.read_csv(DATA / "sliding_fft_diagnostics_summary.csv")
    df = df[df.status == "ok"]
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.55), sharex=True)
    for angle, sub in df.groupby("angle_deg"):
        axes[0].plot(sub.window_center_cm, sub.peak_period_cm, "o-", ms=3, lw=.9, color=COLORS[angle], label=f"{int(angle)}°")
        axes[1].plot(sub.window_center_cm, sub.constant_n_thickness_um, "o-", ms=3, lw=.9, color=COLORS[angle], label=f"{int(angle)}°")
    axes[0].axhline(250, color="0.45", ls="--", lw=.8)
    axes[0].set(ylabel=r"Fringe period (cm$^{-1}$)", xlabel=r"Window centre (cm$^{-1}$)")
    axes[1].set(ylabel=r"Seed thickness ($\mu$m, n = 2.60)", xlabel=r"Window centre (cm$^{-1}$)")
    axes[0].legend(frameon=False, title="Incidence")
    for letter, ax in zip("AB", axes):
        ax.text(-.14, 1.04, letter, transform=ax.transAxes, fontweight="bold")
    finish(fig, "en_sliding_fft.png")


def best_fits():
    df = pd.read_csv(DATA / "residual_diagnostics_curves.csv")
    for angle, sub in df.groupby("angle_deg"):
        fig, ax = plt.subplots(figsize=(5.1, 2.55))
        ax.plot(sub.wavenumber_cm, sub.observed_reflectance, color="0.25", lw=.8, label="Observed")
        ax.plot(sub.wavenumber_cm, sub.fitted_reflectance, color=COLORS[angle], lw=1.0, label="Affine-calibrated TMM")
        ax.set(xlabel=r"Wavenumber (cm$^{-1}$)", ylabel="Reflectance", title=f"Constrained Dong/TMM fit ({int(angle)}°)")
        ax.legend(frameon=False)
        finish(fig, f"en_tmm_fit_{int(angle)}deg.png")


def weight_profile():
    df = pd.read_csv(DATA / "band_weighted_tmm_profile.csv")
    joint = df[df.dataset == "joint"]
    names = {"all_equal": "Equal weight", "frequency_screened": "Frequency screened", "frequency_downweighted": "Frequency downweighted", "continuous_frequency_weight": "Continuous frequency weight"}
    fig, ax = plt.subplots(figsize=(6.2, 2.75))
    for key, label in names.items():
        sub = joint[joint.scenario == key]
        ax.plot(sub.thickness_um, sub.weighted_rmse, lw=1.0, label=label)
    ax.set(xlabel=r"Thickness ($\mu$m)", ylabel="Joint weighted RMSE")
    ax.legend(frameon=False, ncol=2)
    finish(fig, "en_band_weighted_profile.png")


def plasma_heatmap():
    df = pd.read_csv(DATA / "dong2012_tmm_sensitivity_joint.csv")
    grid = df.pivot(index="epi_plasma_scale", columns="sub_plasma_scale", values="joint_mean_rmse")
    fig, ax = plt.subplots(figsize=(4.8, 3.35))
    im = ax.imshow(grid.values, origin="lower", aspect="auto", cmap="cividis")
    ax.set(xticks=np.arange(len(grid.columns)), xticklabels=[f"{x:g}" for x in grid.columns],
           yticks=np.arange(len(grid.index)), yticklabels=[f"{x:g}" for x in grid.index],
           xlabel=r"Substrate $\nu_p$ scale", ylabel=r"Epilayer $\nu_p$ scale")
    cbar = fig.colorbar(im, ax=ax, pad=.02); cbar.set_label("Joint mean RMSE")
    finish(fig, "en_nup_rmse_heatmap.png")


def residuals():
    df = pd.read_csv(DATA / "residual_diagnostics_curves.csv")
    fig, ax = plt.subplots(figsize=(6.3, 2.7))
    for angle, sub in df.groupby("angle_deg"):
        ax.plot(sub.wavenumber_cm, sub.residual, lw=.75, color=COLORS[angle], label=f"{int(angle)}°")
    ax.axhline(0, color="0.25", lw=.7)
    ax.set(xlabel=r"Wavenumber (cm$^{-1}$)", ylabel="Residual (observed - fitted)")
    ax.legend(frameon=False, title="Incidence")
    finish(fig, "en_residual_diagnostics.png")


def final_audit():
    df = pd.read_csv(DATA / "final_evidence_audit.csv")
    sub = df[(df.include_in_final_interval == "是") & df.lower_um.notna() & df.upper_um.notna()].copy()
    labels = ["Two-angle Dong/TMM", r"$\nu_p$ sensitivity", r"$\gamma$ sensitivity", "Phonon damping", "Band sensitivity", "Constrained refinement", "Block bootstrap", "Band-weight profile"]
    sub = sub.iloc[:len(labels)].copy(); sub["label"] = labels[:len(sub)]
    fig, ax = plt.subplots(figsize=(6.5, 3.45))
    ax.axvspan(7.4, 7.6, color="0.85", zorder=0, label="Reported interval")
    for i, row in sub.iloc[::-1].reset_index(drop=True).iterrows():
        ax.hlines(i, row.lower_um, row.upper_um, color="#0072B2", lw=4)
        ax.plot(row.estimate_um, i, "o", color="#D55E00", ms=4)
    ax.axvline(7.465, color="#D55E00", lw=1, ls="--", label="Representative value")
    ax.set(yticks=np.arange(len(sub)), yticklabels=list(sub.iloc[::-1].label), xlabel=r"Thickness ($\mu$m)", xlim=(7.34, 7.63))
    ax.legend(frameon=False, loc="lower right")
    finish(fig, "en_final_evidence_audit.png")


if __name__ == "__main__":
    raw_spectra(); fft_seed(); sliding_fft(); best_fits(); weight_profile()
    plasma_heatmap(); residuals(); final_audit()
