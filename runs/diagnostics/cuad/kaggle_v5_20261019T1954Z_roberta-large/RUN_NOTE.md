# DIAG-CUAD-2, RoBERTa-large: corrected full run on Kaggle (version 5, 2026-10-19/20)

**CORRECTED_DIAGNOSTIC: this is not the pre-registered Step A.** The pre-registered result stays STEP_A_FAIL
(44.63 / 34.73).

## Setup

- **Kaggle run:** kernel `triage-phase3-diagnostic`, version 5, on a T4.
- **Code:** dataset snapshot of commit `87bd32b4`.
- **Data:** sha256-verified `fetch_external.sh`.
- **Model:** `akdeniz27/roberta-large-cuad`.
- **Scorer and thresholds:** unchanged `cuad_step_a.py` + official `evaluate.py`; tolerance ±3.0 AUPR, ±5.0 P@80R.

## Steps (`diag_state/diag_log.jsonl`)

| Step | Result |
|---|---|
| Authors' released predictions (Zenodo 4599830), unchanged scorer | STEP_A_PASS 48.25 / 38.13 |
| Weights, community vs official | identical, 391/391 tensors, max \|Δ\| 0.0 |
| Reference pipeline on the seed-20261018 sample | 123/123 top answers = authors'; max \|Δp\| 1.3e-5 (cuda, 597 s) |
| **Corrected full run** (26/26 chunks; 20:06–00:52 UTC) | **STEP_A_PASS: AUPR 48.25 / P@80R 38.13** (published 48.2 / 38.1); 4,182/4,182 questions |

## Checks done locally on the downloaded predictions

- **Independent re-score.** `nbest_partial.jsonl` was re-scored with the unchanged scorer. The result is
  identical: 48.2497 / 38.1281, STEP_A_PASS, 4,182 questions.
- **The score equals the authors'-predictions score to every digit.** On the sample, this pipeline reproduces the
  authors' predictions to |Δp| ≤ 1.3e-5, so the rankings, and therefore the scores, coincide.
- **This is not a copy of an earlier file.**
  - The predictions differ from our pre-registered RoBERTa-large predictions on 681/4,182 top answers. 3,501 are
    the same.
  - The null top answer appears 2,306 times here, against 2,245 in the pre-registered run.
  - The authors' file was scored in a separate directory, and its predictions were deleted after scoring.

`diag_state/corrected_roberta-large/nbest_partial.jsonl.gz` holds the predictions. The per-chunk files and the
model weights are not kept.
