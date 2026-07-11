from pathlib import Path

import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT / "Sources"


def find_attachment_dir():
    for child in SOURCE_DIR.iterdir():
        if child.is_dir():
            return child
    raise FileNotFoundError("No attachment directory found under Sources.")


def moving_average(y, window=101):
    if window % 2 == 0:
        window += 1
    if len(y) < window:
        window = max(3, len(y) // 2 * 2 + 1)
    kernel = np.ones(window) / window
    return np.convolve(y, kernel, mode="same")


def separated_extrema(x, y, min_spacing_cm=250, window=101):
    smooth = moving_average(y, window)
    max_candidates = np.where((smooth[1:-1] > smooth[:-2]) & (smooth[1:-1] > smooth[2:]))[0] + 1
    min_candidates = np.where((smooth[1:-1] < smooth[:-2]) & (smooth[1:-1] < smooth[2:]))[0] + 1
    step = np.median(np.diff(x))
    min_distance = max(1, int(min_spacing_cm / step))

    def keep_by_distance(candidates, high=True):
        ordered = sorted(candidates, key=lambda idx: smooth[idx], reverse=high)
        kept = []
        for idx in ordered:
            if all(abs(idx - prev) >= min_distance for prev in kept):
                kept.append(idx)
        return np.array(sorted(kept))

    return keep_by_distance(max_candidates, True), keep_by_distance(min_candidates, False)


def rough_thickness_um(extrema_cm, refractive_index, angle_deg):
    if len(extrema_cm) < 2:
        return np.array([])
    theta = np.deg2rad(angle_deg)
    cos_inside = np.sqrt(1 - (np.sin(theta) / refractive_index) ** 2)
    spacing = np.diff(extrema_cm)
    return 10000 / (2 * refractive_index * cos_inside * spacing)


def main():
    attachment_dir = find_attachment_dir()
    files = sorted(attachment_dir.glob("*.xlsx"))
    configs = [
        ("SiC", 10, 2.6),
        ("SiC", 15, 2.6),
        ("Si", 10, 3.42),
        ("Si", 15, 3.42),
    ]

    for file, (material, angle, n0) in zip(files, configs):
        df = pd.read_excel(file)
        x = df.iloc[:, 0].to_numpy(float)
        y = df.iloc[:, 1].to_numpy(float)
        mask = (x > 1000) & (x < 4000)
        xs = x[mask]
        ys = y[mask]
        peaks, troughs = separated_extrema(xs, ys)
        peak_x = xs[peaks]
        trough_x = xs[troughs]
        d = np.concatenate([
            rough_thickness_um(peak_x, n0, angle),
            rough_thickness_um(trough_x, n0, angle),
        ])

        print(f"\n{file.name} | material={material} | angle={angle} deg | n0={n0}")
        print(f"rows={len(df)}, wavenumber=({x.min():.3f}, {x.max():.3f}) cm^-1")
        print(f"reflectance=({y.min():.3f}, {y.max():.3f}) %, mean={y.mean():.3f}%")
        print(f"peaks={len(peak_x)}, first_peaks={np.round(peak_x[:8], 2).tolist()}")
        print(f"troughs={len(trough_x)}, first_troughs={np.round(trough_x[:8], 2).tolist()}")
        if len(d):
            print(f"rough_thickness_mean={d.mean():.3f} um, std={d.std():.3f} um, intervals={len(d)}")


if __name__ == "__main__":
    main()
