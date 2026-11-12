# Pre-release sensitive-data and redistribution audit (2026-11-05)

**Status: NOT CLEARED FOR RELEASE.** This is a documented preliminary audit, not a certification that every file is safe to redistribute.

## Scope and observations

- GitHub tree at commit `94f3f2a`: 385 blobs, approximately 120 MB, 521 tree entries. The recursive tree response was not truncated.
- No obvious private-key, database, PDF/DOCX contract, or `.env` filenames were identified in the tree listing. This **does not** establish that contents contain no secrets or personal data.
- Higher-risk content includes `runs/phase5/**/cases_full.jsonl`, `runs/v*/results.jsonl`, `runs/step_b/**/*.jsonl.gz`, `runs/phase3_kaggle/**/logs/*.log`, notebooks with outputs, and other raw prediction or document-span files. These may contain contract excerpts, source text, prompts, tokens, paths, or participant identifiers.
- The repository explicitly acknowledges short MCC contract excerpts in outputs. MCC CC BY-NC-SA terms may constrain redistribution and downstream commercial use. Other datasets and SEC-derived text need provenance-specific assessment. A public filing is not automatically free of privacy or redistribution concerns.
- GitHub's file-content interface did not return the bodies of several large files, so those files were **not** content-scanned in this review.

## Required local review before publishing GitHub release or Zenodo archive

1. Download a fresh, exact commit snapshot and verify `SHA256SUMS` with `python verify.py`; note that a release archive may include the newly added audit files and changed metadata.
2. Run a full-file secret scanner (for example Gitleaks) against the working tree and, separately, commit history. Review all findings, including false positives.
3. Inspect every JSONL, CSV, log, compressed prediction file and notebook (including notebook cell outputs) for personal information, API keys, internal paths, proprietary text, and third-party contract excerpts. Sample checks are insufficient for a claim of full clearance.
4. Create a provenance and licensing inventory for each data-bearing file and embedded excerpt, including source URL, upstream license, attribution, and whether verbatim redistribution is permitted. Remove, redact, or replace anything not cleared, and update manifests/checksums.
5. Have a human review the resulting archive and explicitly approve the final release. Preserve a written audit record.

## Release decision

**BLOCKED** pending full content-level and provenance review. Do not describe this document as evidence of completed clearance. The record-level Zenodo CC BY 4.0 metadata must not be construed as relicensing third-party material.
