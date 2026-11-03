# Day 1 validation

Run 2026-10-17T02:18:19.697485+00:00 at HEAD `de8970e8`.

| Check | Status |
|---|---|
| corpus.manifest_sha256_matches_recorded | PASS |
| corpus.row_count_618 | PASS |
| corpus.doc_ids_unique | PASS |
| corpus.all_text_hashes_match | PASS |
| corpus.slice_counts | PASS |
| corpus.cnli_cuad_texts_rederived_from_source | PASS |
| corpus.mcc_sample_reextract_hash_ok | PASS |
| corpus.mcc_sample_independent_extractor_len_within_8pct | PASS |
| corpus.mcc_no_bare_amendments | PASS |
| corpus.mcc_one_per_company_per_type | PASS |
| releases.all_hashes_reproduce_from_fresh_checkout | PASS |
| releases.iccs_state_has_25_rules | PASS |
| baseline.v7.2.0_precedes_mcc_introduction | PASS |
| runs.no_duplicate_or_missing_docs | PASS |
| runs.total_executions_26574 | PASS |
| runs.zero_variance_all_releases | PASS |
| reexec.sample_matches_stored_outputs | PASS |
| scoring.gold_test_json_vs_master_clauses_agree | PASS |
| scoring.independent_recount_matches_report | PASS |

## Version-drift table (rule definitions recomputed from fresh checkouts)

| Version label | Commit | Commit date | Rule count | Canonical ruleset SHA-256 |
|---|---|---|---|---|
| 1.0.3 (v1.0.3-iccs) | `ae097e74` | 2026-01-15T12:09:21 | 25 | `9bf6d61a2b10732899a41beb992019c945407d5edf2d12f0214e4bb5478df35d` |
| 1.0.3 (v1.0.3) | `1a270a56` | 2026-01-27T17:13:38 | 25 | `9bf6d61a2b10732899a41beb992019c945407d5edf2d12f0214e4bb5478df35d` |
| 2.0.0 (v2.0.0) | `468dee0f` | 2026-06-26T22:46:56 | 40 | `009c33f0ae929f12c801d76a8a9fc1451104ee6ea9562aab07c6f15c51b7196c` |
| 2.1.0 (v2.1.0) | `3600870f` | 2026-06-30T00:49:18 | 52 | `aa04ed32865d82135957e874ce2addc869dabee53a0d9306adff3ad925be40b4` |
| 3.0.0 (v3.0.0) | `decaa703` | 2026-07-13T22:21:00 | 80 | `72a676a9676b5bf17b07c6b35b5a390ad35698844e3acb776f7208c24a592afd` |
| 4.0.0 (v4.0.0) | `623d3c72` | 2026-07-16T01:36:03 | 80 | `72a676a9676b5bf17b07c6b35b5a390ad35698844e3acb776f7208c24a592afd` |
| 5.0.0 (v5.0.0) | `5aed1d53` | 2026-07-19T23:58:08 | 91 | `57db7f637c4b1d7320c7a2c081f3ec534f1765e4e5e0e1b0cd98c506499b460e` |
| 6.0.0 (v6.0.0) | `96cf3954` | 2026-07-22T04:52:34 | 117 | `b2bca1c6ee96be4a16064e0efc7a58272bd2639737814e6249a2578be8292d3e` |
| 7.0.0 (v7.0.0) | `7d4f3b19` | 2026-07-24T04:52:55 | 180 | `2d8d0e57b42326405be2e24d13de91a94081e849db36daaa7570810a1e9bf8ec` |
| 7.1.0 (v7.1.0) | `c251a6da` | 2026-07-31T07:41:59 | 185 | `e407a1e2c2e8c524e8ccefd3aca434959ee29f5552dfd204e4550731c301fd55` |
| 7.2.0 (v7.2.0) | `51d709e8` | 2026-07-31T07:59:35 | 189 | `129f7be56482f9af35ebf93782840d05eb0cd91c5b367a721c7dd0cc4a31a024` |
| 7.2.0 (v7.2.0+f5257056) | `f5257056` | 2026-08-08T03:13:42 | 189 | `c7781b73bcdac7c5777150edba0a54e4837e952789fceaf780be6bffdee4c06a` |
| 7.2.0 (v7.2.0+8b79a386) | `8b79a386` | 2026-08-08T06:30:07 | 189 | `cc91fb4f398aa1e184edf32d38e1a66e1ae0d72f110e5c85786767307fb429ac` |
| 7.2.0 (v7.2.0+6b9bfc8e) | `6b9bfc8e` | 2026-09-07T15:47:45 | 189 | `cc91fb4f398aa1e184edf32d38e1a66e1ae0d72f110e5c85786767307fb429ac` |
| 7.2.0 (v7.2.0+20294216) | `20294216` | 2026-09-10T01:28:34 | 189 | `cc91fb4f398aa1e184edf32d38e1a66e1ae0d72f110e5c85786767307fb429ac` |
