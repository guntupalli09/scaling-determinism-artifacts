# DIAG-CUAD-2, DeBERTa-v2-xlarge: Kaggle version 6 (partial, 2026-10-20)

**CORRECTED_DIAGNOSTIC and incomplete: no score is computed from this run.** A partial prediction set is never
scored.

## Setup

- **Code:** commit `87bd32b4` (Kaggle code dataset).
- **Hardware:** Kaggle, T4.
- **Session:** started ≈01:09 UTC. It was cancelled by Kaggle (status CANCEL_ACKNOWLEDGED) after the account's
  weekly free-GPU quota ran out. The quota resets 2026-10-24 00:00 UTC.

## Steps (`diag_state/diag_log.jsonl`)

| Step | Result |
|---|---|
| Authors' released predictions (Zenodo 4599830), unchanged scorer | STEP_A_PASS 47.79 / 44.03 / P@90R 17.83 (published 47.8 / 44.0 / 17.8) |
| Weights, community vs official | identical, 396/396 tensors, max \|Δ\| 0.0 |
| Reference pipeline on the seed-20261018 sample | 123/123 top answers = authors'; max \|Δp\| 0.0035 |
| Corrected full run | **19/26 chunks finished** (3,116 of 4,182 questions); chunk 19 was cut off mid-run |

## Notes

- Download time: fetching the authors' 3.1 GB DeBERTa release from Zenodo took ≈1.5 h of the session.
- Saved predictions: `chunks_000-018_nbest.jsonl.gz` holds the 19 finished chunks.
- Kaggle resume dataset: `santhoshguntupalli/triage-phase3-diag-state`. It is a separate dataset; the
  pre-registered state dataset is untouched.
- Cross-check plan: the chunks that the Colab run also completes will be compared question by question with these.
