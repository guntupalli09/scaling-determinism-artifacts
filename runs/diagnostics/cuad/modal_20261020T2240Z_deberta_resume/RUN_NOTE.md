# DIAG-CUAD-2, DeBERTa-v2-xlarge: corrected full run (Kaggle v6 chunks 0–18 + Modal chunks 19–25)

**CORRECTED_DIAGNOSTIC: this is not the pre-registered Step A.** The pre-registered result stays STEP_A_FAIL
(28.2 / 0.0).

## How the run was assembled

All sessions used the same code, commit `87bd32b4`, verified file by file against its git blobs. Data was
sha256-verified. The scorer and the thresholds were unchanged. Library pins: transformers 4.57.6 / tokenizers 0.22.2.

1. **Kaggle version 6 (T4, 2026-10-20).** It produced the step results and chunks 0–18; see
   `../kaggle_v6_20261020T0109Z_deberta_partial/`. Kaggle cancelled the session when the weekly free GPU quota ran
   out.
2. **Colab.** Attempts to resume ended in disconnects, and then the free GPU limit was reached. Colab finished no
   chunks.
3. **Modal (T4, torch 2.11.0+cu130).** The state was seeded with Kaggle v6's diag_log and chunks 0–18 (the committed
   record, sha256-checked); see `comparators/diagnostics/modal_diag.py`.
   - **First session (22:40 UTC).** It finished chunks 19–21. It was then cancelled at 00:39 UTC, when the local
     `modal run --detach` client was stopped by this agent's 2 h background-command limit.
   - **Relaunch (01:45 UTC).** A spawned call on the deployed app, independent of the local client. It resumed with
     22 chunks done, finished chunks 22–25, merged all 26 and scored them at 03:34 UTC.
   - `environment.jsonl` records both sessions.

## Result (`step_a_result.json`, `diag_log.jsonl`)

| | AUPR | P@80R | P@90R |
|---|---|---|---|
| Published (CUAD paper) | 47.8 | 44.0 | 17.8 |
| Authors' released predictions, our scorer (Kaggle v6 / Colab) | 47.79 | 44.03 | 17.83 |
| **Corrected pipeline (this run)** | **47.79** | **44.02** | **17.83** |
| Pre-registered Step A | 28.2 | 0.0 | – |

**STEP_A_PASS** under the unchanged tolerance (±3.0 AUPR, ±5.0 P@80R); 4,182/4,182 questions.

## Checks

- **Independent re-score.** `nbest_partial.jsonl.gz` was re-scored locally with the unchanged scorer. The result is
  identical: 47.788 / 44.022 / 17.832.
- **Seed integrity.** Chunks 0–18 are identical to the Kaggle v6 record: 3,116/3,116 questions, text and
  probability. Chunks 19–25 contribute 1,066 newly computed questions.
- **Comparison with the pre-registered run (v6, full).**
  - Same top answer: 3,111/4,182 questions.
  - Null top answer: 2,198 here vs 3,051 in the pre-registered run.
  - The pre-registered pipeline's over-prediction of "no answer" accounts for its 28.2 / 0.0.
- **Mixed provenance.** Chunks come from two hosted environments, Kaggle and Modal, with the same code and pins. Our
  GPU/CPU and Kaggle/Colab comparisons agree to |Δp| ≤ 1.3e-5 on identical inputs.
