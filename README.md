# Research artefacts: The Cost of Scaling Determinism

Research artefacts for S. Guntupalli and M.-P. Laakkonen, *The Cost of Scaling Determinism: Coverage, Regression Risk
and Attack Surface in a Versioned Symbolic Control Plane for LLM-Assisted Contract Analysis* (manuscript prepared for submission to the Journal
of Computational Science).

The contract-analysis engine studied in the paper is proprietary and is **not** included. Its executable releases are
identified by commit, ruleset hash and engine-code hash (`releases/manifest_v2.json`). Everything needed to check the
paper's numbers from the engine's recorded outputs is here.

## Quick check (standard library only)

    python verify.py

The script:
1. checks every file against `SHA256SUMS`;
2. recomputes Tables 5 and 6 (Step C, engine vs. comparators, including the stratified split) from the per-unit files;
3. recomputes Table 3 (injection attribution) from the per-case file.

It prints each value next to the value reported in the manuscript and exits non-zero on any mismatch.

`TRACEABILITY.md` lists every file that a number, table or figure in the manuscript comes from, each checked byte for
byte against the study record when this package was built.

## What is here

| Path | Contents | Paper |
|---|---|---|
| `corpus/manifest.csv`, `manifest/` | The 618 frozen documents: source, slice, SHA-256 of each text (manifest SHA-256 `3bcd0d90…a8c755b`) | §4 |
| `releases/manifest_v2.json` | The 15 engine states: commit, rule count, canonical ruleset and engine-code hashes | Table 1, §5.4 |
| `comparators/label_mapping.json` | The frozen category-to-rule mapping (SHA-256 `ed28bb8d…`) | Appendix A |
| `runs/v*/results.jsonl` | Per-document engine output for each release: finding sets, rule IDs, output and finding fingerprints for every repeated run, timing medians | §5.1, §5.2, §5.8 |
| `runs/determinism_crossprocess/`, `runs/validation/` | Cross-process runs (6 hash seeds × 60 documents × 15 states) and fresh-checkout validation | §5.1 |
| `runs/analysis/`, `runs/phase6/` | Per-unit fixed-denominator files, per-release statistics, runtime scaling fits, figures | §5.2, §5.8, Table 2 |
| `runs/phase4_counterfactual/` | Single-rule counterfactuals and bisection for the v5.0 regression | §5.3 |
| `runs/phase5/`, `runs/phase5_control/`, `runs/repro_injection/` | Injection cases, benign controls and per-case attribution | §5.5, Table 3 |
| `runs/phase2/`, `runs/phase5_proposal/`, `adaptivity/` | Adaptation pipeline test and the 38 proposal-path security cases | §5.6 |
| `runs/phase3_kaggle/`, `runs/diagnostics/` | Pre-registered Step A runs (failed), diagnosis and corrected Step A runs | §5.9, Table 4 |
| `runs/step_b/` | Step B predictions (merged), Step C per-unit files and reports, stratified analysis, run notes and logs | §5.9, Tables 5–6 |
| `comparators/` | Comparator code: CUAD inference and scoring, ContractNLI training/scoring, Step B harness, LexNLP | §5.9 |
| `*.py` at the top level | Study scripts (statistics, evaluation, freezing, injection, adaptation) | all |
| `COMPUTATIONAL_RESULTS.md`, `FINAL_RESULTS_MANIFEST.md` | Results summary and a manifest tracing every reported number to its raw file | all |

Scripts that execute the engine (for example `validate_day1.py` and `phase5_security.py`) are included so the procedure
is documented. They need the proprietary engine to run. Their recorded outputs are in `runs/`.

## Deeper verification

- **Documents.** Download the public sources and recompute every text's SHA-256 against `corpus/manifest.csv`:
  - MCC exhibits from EDGAR, via the Material Contracts Corpus;
  - CUAD and ContractNLI, with `comparators/gpu/fetch_external.sh`, which checks each file against
    `comparators/gpu/EXTERNAL.sha256`.

  `build_corpus.py` and `triagebench/html_extract.py` rebuild the MCC texts from the filings.
- **Step A.** `comparators/cuad_step_a.py` scores CUAD predictions with the official CUAD `evaluate.py`, from n-best
  files such as `runs/step_b/cuad_roberta-base/roberta-base/cuad_test/nbest_partial.jsonl.gz` (decompress first). It
  should reproduce AUPR 42.603 / P@80R 31.140. The `RUN_NOTE.md` files give the equivalent paths for the other models.
- **Step B / Step C from scratch.** `comparators/step_b/` runs the validated CUAD procedure on any GPU from the public
  checkpoints (`akdeniz27/*-cuad` on Hugging Face). `evaluate_paired.py` pairs it with the engine outputs in
  `runs/v7.2.0`.
- **Statistics.** `phase6_stats.py` recomputes Table 2 and the release-to-release tests from `runs/analysis`.

## Notes and limitations

- The category-to-rule mapping is author-defined. It was frozen before any result was computed and has not been
  validated by an independent legal expert.
- Step B is incomplete for DeBERTa-v2-xlarge: when this archive was built, its run on the 516 documents without expert
  labels had completed 43 of 294 chunks. Those documents enter no reported metric. DeBERTa's Step C uses its validated
  test-set predictions, is final, and is included. A completed run would be added as a new version of this archive.
- Engine findings in `runs/` contain short matched spans of the documents. MCC texts are licensed CC BY-NC-SA 4.0;
  CUAD and ContractNLI are CC BY 4.0.

## Licence

This is a **mixed-license archive**, not a blanket CC BY 4.0 release. Original data and documentation authored for this study: CC BY 4.0. Original Python and shell code: MIT. Short excerpts derived from the Material Contracts Corpus (MCC) in recorded outputs retain the source CC BY-NC-SA 4.0 restrictions, including noncommercial use and share-alike where applicable. Third-party files, model outputs and dataset-derived text are not relicensed by this repository. See `LICENSE` and `RELEASE_DISCLOSURE_AUDIT.md`; inspect each file's provenance before reuse.

## Contact

Santhosh Guntupalli (corresponding author), santhosh.guntupalli09@gmail.com
