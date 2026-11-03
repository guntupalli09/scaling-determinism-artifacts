# DIAG-CUAD-2, RoBERTa-base: corrected full run on Google Colab (2026-10-19)

**CORRECTED_DIAGNOSTIC: this is not the pre-registered Step A.** The pre-registered result stays STEP_A_FAIL
(37.70 / 26.80).

## Setup

- **Environment** (`environment.jsonl`): Colab, Tesla T4, CUDA, torch 2.11.0+cu130, transformers 4.57.6,
  Python 3.13.15.
- **Code:** commit `87bd32b4`, embedded in `comparators/diagnostics/colab_diag.ipynb` (repo commit `1a98eaa2`).
  The notebook checked all 29 files against the commit's git blob hashes before running.
- **Data:** `fetch_external.sh`, with every file sha256-verified.
- **Model:** `akdeniz27/roberta-base-cuad`. Its weights are identical to the official Zenodo 4599830 checkpoint
  (199/199 tensors, max |Δ| 0.0).
- **Scorer and thresholds:** unchanged `cuad_step_a.py` + official `evaluate.py`; tolerance ±3.0 AUPR, ±5.0 P@80R.

## Steps (`diag_log.jsonl`)

| Step | Result |
|---|---|
| Authors' released predictions, unchanged scorer | STEP_A_PASS 42.59 / 31.13 |
| Weights, community vs official | identical |
| Reference pipeline on the seed-20261018 sample | 123/123 top answers = authors'; max \|Δp\| 0.004 (cuda, 235 s) |
| **Corrected full run** (26 chunks; 16:41–19:01 UTC) | **STEP_A_PASS: AUPR 42.60 / P@80R 31.14** (Δ +0.003 / +0.04); 4,182/4,182 questions |

The corrected pipeline reproduces the published RoBERTa-base numbers, and the authors' own released predictions.
The pre-registered shortfall (37.70 / 26.80) is therefore fully explained by our pre-registered inference
pipeline, not by the model, the data or the scorer.

## Predictions

The merged predictions `nbest_partial.jsonl.gz` (2.9 MB) are on the run owner's Google Drive, under
`triage_phase3_diag/colab_roberta-base/diag_state/corrected_roberta-base/`. They are to be added here and
re-scored independently. Until then, the score above is the one computed in the Colab session by the verified,
unchanged scorer.
