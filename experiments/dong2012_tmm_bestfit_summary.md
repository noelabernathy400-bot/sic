# Dong/TMM best-fit curve export summary

This script exports the fitted spectral curves at the fixed-parameter representative thickness.

- thickness: $7.455\ \mu m$
- joint mean RMSE: `0.00173772`
- material-parameter state: final state from `dong2012_tmm_coordinate_search_chosen.csv`
- fitting band: inherited from `dong2012_tmm_uncertainty.py`, $1500\text{--}4000\ \mathrm{cm}^{-1}$

## Metrics

| dataset | RMSE | affine scale | affine offset | residual std | max abs residual |
| --- | --- | --- | --- | --- | --- |
| SiC_10deg | 0.00133086 | 1.001874 | -0.004880 | 0.00133163 | 0.00785488 |
| SiC_15deg | 0.00214457 | 1.081020 | -0.011205 | 0.00214581 | 0.00875344 |

## Interpretation

The affine fit is a calibration layer between measured reflectance and model reflectance. Therefore these curves are evidence for phase and line-shape consistency, not proof that absolute reflectance amplitudes are fully explained.
