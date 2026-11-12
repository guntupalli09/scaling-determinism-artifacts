# Kaggle diagnostic sessions, 2026-10-18/19 (`triage-phase3-diagnostic`, code `2f402742`)

Diagnostic only (DIAG-CUAD-2). No pre-registered result is affected.

## What happened to version 3 (submitted 2026-10-18 21:14 UTC)

- **It did not hang. It waited ~18.5 h for a free T4, then ran normally.**
- **Kaggle counts that wait as "Running".**
  - The page's "Running for 67258 s" is measured from submission: 21:14 UTC + 67,258 s = 15:55 UTC on 10-19.
  - The session's own log clock starts at ≈15:41 UTC.
  - At first, the page showed only the 4 notebook-startup lines and 0 B output. That was the queue wait, not a hang.
- **It ran for 1,072 s and completed.** The first cell, which copies the code snapshot and reports the GPUs, took
  ~9 min of that.
- **Logs.**
  - Full log: `kernel_log_stream.jsonl`.
  - Step log: `diag_state/diag_log.jsonl`.

| Step | Result |
|---|---|
| roberta-base: authors' released predictions, unchanged scorer | **STEP_A_PASS, 42.59 / 31.13** (published 42.6 / 31.1) |
| roberta-base: community vs official weights | **identical**: 199/199 tensors, max \|Δ\| 0.0 |
| roberta-base: reference pipeline on the seed-20261018 sample, T4 GPU | **123/123** top answers = authors'; max \|Δp\| 0.004. Identical to the local CPU run (123/123, max \|Δp\| 1.1e-5); 250 s on GPU |
| roberta-base: corrected full run | **failed at its first chunk**: `AssertionError: unknown title in sample` |

### Root cause of the failure

- **The bug.** Two CUAD test titles end in a trailing space:
  - "PACIRA PHARMACEUTICALS, … MARKETING AGREEMENT "
  - "Monsanto Company - SECOND A_R … MARKETING AGREEMENT "

  The full run writes each chunk's titles to a file, one per line. The pipeline strips them when reading back, so
  those two titles no longer matched. That breaks chunks 0 and 19.
- **Why the sample passed.** The 3-contract sample has no such titles.
- **Fix.** Titles are now compared after stripping both sides. A check over all 26 chunks of 4 contracts finds 0
  mismatches, and the sample still matches 3/3. This changes no inputs or predictions: the contract records are
  passed on unchanged.

### Two wrong hypotheses, recorded and withdrawn

Before this log was available, I had reported version 3 as "stuck" and then guessed a fork-after-CUDA deadlock
in the sample step. I reordered the feature building and committed that as `8610f6fe`. The log disproves both:
- the session was queued, not hung;
- the sample step ran on GPU without problems.

The reorder has been reverted, so the code is exactly what was validated on the GPU. The timeouts were kept:
- 1 h on the sample step;
- bounded and retried downloads;
- a hard notebook timeout of budget + 30 min.

They cannot change results.

Planning consequence: free-T4 queue waits are currently very long (≈2.4 h for v4 of the pre-registered
notebook, ≈18.5 h here), so each run can take a day to start.
