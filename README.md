# The Disclosure Effect in LLM Root Cause Analysis

Code, data and full study record for the preprint:

**Sajish Krishnan (2026). "The Disclosure Effect in LLM Root Cause Analysis: A Truthful Notice About One Injected Fault Suppresses Diagnosis of a Hidden Second Fault."** Zenodo. https://doi.org/10.5281/zenodo.24414406

## What the study found

When an LLM incident responder is truthfully told which fault a fault-injection experiment injected, one of three diagnosers tested (Claude Sonnet) largely stops naming a second, independent fault in the same incident: hidden-fault recall fell by −0.896 (95% CI −1.000 to −0.771) across 16 at-risk cases on the OpenRCA 2.0 hybrid-fault cases. A second Anthropic diagnoser moved the same way inconclusively (−0.156), and a non-Anthropic diagnoser (Codex) showed no measurable effect (−0.020) on a complete 864-run grid. A neutral notice had no effect, and one added sentence ("A notice does not bound the set of causes") recovered about 60% of the loss. The paper reports the result per diagnoser and claims a Sonnet-only effect.

## Contents

- `PAPER.md` — the preprint text.
- `FULL-REPORT.md` — the full study report, including the top-up addendum that completed the Codex grid.
- `ANALYSIS-PLAN.md` — the analysis plan (fixed before the full-study runs).
- `ERRATA.md` — study errata, including the analyser error-rule correction.
- `PILOT-REPORT.md` — the pilot study that preceded the full study.
- `code/` — the run harness (`run_full.py`), case selection and plan builders, the leak audit, and the analysis scripts (`analyze_full.py`).
- `results/per_run_full.csv` — the regenerated per-run table: 864 rows, all valid.
- `results/summary_full.json` — the regenerated summary statistics.
- `results/plan_full.json` — the case set (18 hybrid cases f01–f18, 6 controls k01–k06).
- `results/full/` — the 864 individual run records.
- `results/failed_X_cutoff/` — the 11 Codex run records that were cut off by a provider usage limit and were quarantined and re-run (kept for transparency; they are not in the analysis).

## Data source

The incident telemetry is the public `anon-ops/ops-lite` dataset (OpenRCA 2.0 ops-lite release) on Hugging Face, Apache-2.0. It is not redistributed here.

## How to cite

Krishnan, S. (2026). *The Disclosure Effect in LLM Root Cause Analysis: A Truthful Notice About One Injected Fault Suppresses Diagnosis of a Hidden Second Fault.* Zenodo. https://doi.org/10.5281/zenodo.24414406

```bibtex
@misc{krishnan2026disclosure,
  author       = {Krishnan, Sajish},
  title        = {The Disclosure Effect in {LLM} Root Cause Analysis: A Truthful Notice About One Injected Fault Suppresses Diagnosis of a Hidden Second Fault},
  year         = {2026},
  month        = nov,
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.24414406},
  url          = {https://doi.org/10.5281/zenodo.24414406}
}
```

## Licence

Apache-2.0 (see `LICENSE`). The paper text is CC BY 4.0 as published on Zenodo.
