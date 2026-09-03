# SiC FTIR Thickness Inversion: Research Repository Guide

## Research question

This repository studies thickness inversion for silicon-carbide epitaxial
layers from Fourier-transform infrared (FTIR) reflectance spectra.  It compares
frequency-domain initialization, dispersion-aware estimation, and
transfer-matrix-method (TMM) full-spectrum fitting, including multi-angle
calibration and robustness checks.

## Start here

| Purpose | Entry point |
| --- | --- |
| Project summary and current result | `README.md` |
| Research context, decisions, and limits | `docs/Overview.md`, `docs/Decision Log.md`, `docs/Status.md` |
| Scripts and recorded experiment outputs | `src/`, `experiments/` |
| Final bilingual manuscript package | `deliverables/SiC_FTIR_Thickness_Paper_Integrated_2026-08-15/` |
| Earlier final paper package | `deliverables/final_research_paper_2026-07-07/` |

## Main result and its scope

The recorded workflow estimates an epitaxial-layer thickness near **6.9 μm**
and a Si substrate thickness near **402 μm** for the supplied experiment.  The
claim is scoped to the measured FTIR spectra, model family, calibration
choices, and robustness analyses held in this repository.  It is not a
universal thickness guarantee for arbitrary wafers or instruments.

## Reproducibility structure

- `src/` contains the inversion and forward-model code.
- `experiments/` retains compact outputs, sensitivity analyses, and figures.
- `deliverables/` contains manuscript source, rendered PDFs, and publication
  figures.
- `docs/` records methods, handoff context, and evidence decisions.

## Data policy

The measured FTIR source files are not redistributed where they are large,
instrument-specific, or originate from a supplied competition/research
attachment.  The repository retains the processing code, frozen experiment
outputs, figure-generation path, and manuscripts so that the analysis can be
audited.  See `DATA_AVAILABILITY.md`.
