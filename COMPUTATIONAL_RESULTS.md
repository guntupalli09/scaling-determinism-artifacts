# Computational results — follow-up study (Days 1–3)

*Bounding the Cost of Determinism: Coverage, Adaptivity, and Real-World Generalization in
Symbolic–LLM Hybrid Pipelines* (working title). State as of 2026-10-17. Branch
`claude/adoring-heisenberg-gd2tv1`.

**Status labels used throughout**

| Label | Meaning |
|---|---|
| **COMPLETE** | computed, independently re-checked where stated |
| **EXPERT-LABELLED** | scored against existing third-party expert labels (CUAD, ContractNLI) |
| **PRELIMINARY_MAPPING_PENDING_REVIEW** | depends on the draft CUAD/ContractNLI ↔ rule mapping (`comparators/label_mapping.json`); not final |
| **PENDING_HUMAN_ANNOTATION** | needs the planned two-annotator labels |
| **BLOCKED_GPU / BLOCKED_API / ENV** | could not be run in this environment |

---

## 1. Executive summary

- **Determinism (COMPLETE).**
  - 26,574 within-process executions across 12 engine states: 0 documents with any output or
    finding-set variance.
  - 5,400 cross-process executions (15 states × 60 docs × 6 `PYTHONHASHSEED` values): 0 variance.
  - Determinism held at every one of the 10 measured historical releases (25 → 189 rules).
- **Coverage vs. release (EXPERT-LABELLED, PRELIMINARY_MAPPING_PENDING_REVIEW).**
  - CUAD test split, 2,142 fixed (contract, category) units: recall rises from 0.213 (ICCS v1.0.3,
    25 rules) to 0.354 (v7.2.0, 189 rules). Precision moves from 0.712 to 0.663.
  - Paired recall test: 81 gold-positive units gained, 4 lost; exact McNemar p ≈ 1e-19.
- **Version drift (COMPLETE).**
  - The label "7.2.0" covers **3 distinct rule-definition states and 5 distinct engine-code
    states**, the later ones created after the MCC corpus entered the repo.
  - A real regression (ContractNLI nda-3 recall 38/73 → 19/73 at v5.0) was **masked** in the
    aggregate by an unrelated gain on a different hypothesis at v6.0.
  - Single-rule counterfactuals attribute 13–16 of the 19 lost true positives to one pattern
    change; the rest is unattributed within the same commit.
  - An earlier drop is localised by bisection to a chunking-only commit.
- **Bounded adaptivity (COMPLETE as a mechanism; LLM step BLOCKED_API).**
  - The full offline failure → proposal → gate → two-reviewer approval → frozen, hashed release
    pipeline works end to end.
  - A pipeline-test release (fixtures, test reviewer identities) fixed its 2 targeted failures,
    caused 0 regressions on 412 previously passing assertions, and removed no base finding
    anywhere in the corpus.
- **Security (COMPLETE, failures recorded).**
  - Proposal path, 38 cases: 35 PASS, **2 FAIL**, 1 BLOCKED_API. The FAILs are:
    - a well-formed but harmful rule passes the automatic gate (only human review stops it);
    - overlay verification is an integrity check, not authentication.
  - Inference path, reconstructed E6 suite over all 618 docs, with a benign-insertion control:
    - **14.0% of v7.2.0 cases** (693/4,944) change the authoritative findings differently from a
      benign insertion, against **1.0%** for the ICCS ruleset.
    - Mechanism: lexical, not instruction-following. Document-scoped absence-check
      (REQUIRED_SECTION) rules can be suppressed or triggered by inserted vocabulary, such as
      "pre-approved" or "SYSTEM:".
  - Explanation layer (baseline), two FAILs:
    - verbatim contract excerpts, including injected text, reach the LLM prompt;
    - fabricated explanation items are logged but not removed.
- **Comparators.**
  - LexNLP repaired (root cause: missing `en_US` locale) and sanity-validated. It has no published
    reference metrics, so its scores are **UNVALIDATED**.
  - CUAD RoBERTa-base Step A is **INCOMPLETE** (96/4,182 questions on shared CPU), so the comparator is not valid yet.
  - ContractNLI Span NLI BERT has no released weights: **BLOCKED_GPU**.
  - RoBERTa-large and DeBERTa-xlarge: **BLOCKED_GPU** (runbook prepared).

## 2. Phase-by-phase status

| Phase | Status | Notes |
|---|---|---|
| 1 Corpus + baseline | COMPLETE (MCC P/R PENDING_HUMAN_ANNOTATION) | 618-row frozen corpus; v7.2.0 baseline; Q3-2026 holdout **not executable** (§3) |
| 2 Bounded adaptivity | Mechanism COMPLETE; LLM generation BLOCKED_API | fixtures and TEST reviewer identities only; no adaptation-quality claim |
| 3 Comparators | Partial | LexNLP UNVALIDATED; CUAD RoBERTa-base Step A INCOMPLETE (not valid); Span NLI BERT and large CUAD models BLOCKED_GPU |
| 4 Coverage vs determinism | COMPLETE (mapping-dependent parts PRELIMINARY) | 10 checkpoints, fixed and release-scope denominators, transitions, counterfactual attribution |
| 5 Security | COMPLETE with recorded FAILs | inference path (reconstructed suite + benign control): 14.0% attributable F changes at v7.2.0; proposal path: 2 FAIL / 35 PASS / 1 BLOCKED_API |
| 6 Statistics | Preliminary package COMPLETE | traceable to raw paired units |

## 3. Frozen corpus

`corpus/manifest.csv`, SHA-256 `3bcd0d90806f244197d7afe6ca1752dbcae4dad6430d06c7b81fd4130a8c755b`.
Per-document text hashes were re-verified on Day 2 from the original sources.

| Slice | Docs | Source | Labels |
|---|---|---|---|
| mcc_employment / services / purchase / lease | 100 / 100 / 100 / 32 | Stanford MCC, 2026 Q1–Q2 8-K exhibits (filtered, one per company per type) | none (PENDING_HUMAN_ANNOTATION) |
| nda | 123 | ContractNLI test split | expert NLI labels (17 hypotheses) |
| licensing | 61 | CUAD license/IP agreements (6 test-split, 55 train-split) | expert CUAD labels |
| cuad_test | 102 | CUAD official test split | expert CUAD labels (41 categories) |

Independence and the claims each slice supports are set out in `CORPUS_INDEPENDENCE.md`:
- **The 2026 Q3 holdout cannot run.** MCC hasn't published Q3; its index was last generated
  2026-08-06. No substitute was made.
- **The baseline predates MCC.** v7.2.0 (`51d709e8`, 2026-07-31 07:59 UTC) precedes the MCC
  commit (`035d3e21`, 2026-08-02 03:24 UTC) by about 43 hours.
- **"Never seen" / OOD language is not supported.**
- **Licensing:** MCC is CC BY-NC-SA 4.0 (non-commercial).

## 4. Ruleset / version / hash table

The canonical ruleset SHA-256 is computed over sorted rule definitions, with set-semantic fields
sorted. Recomputed from fresh `git` checkouts under `PYTHONHASHSEED=12345`, it matches
`releases/manifest_v2.json` for all 15 states.

| Label | version.json | Commit | Date | Role | Rules | Ruleset SHA-256 | rules_engine.py SHA-256 |
|---|---|---|---|---|---|---|---|
| v1.0.3-iccs | 1.0.3 | `ae097e74` | 2026-01-15 | checkpoint (ICCS experiments) | 25 | `9bf6d61a2b107328…` | `6f43cf061ed8…` |
| v1.0.3 | 1.0.3 | `1a270a56` | 2026-01-27 | checkpoint | 25 | `9bf6d61a2b107328…` | `df3e9fc606fe…` |
| v2.0.0 | 2.0.0 | `468dee0f` | 2026-06-26 | checkpoint | 40 | `009c33f0ae929f12…` | `63a344f3b2f2…` |
| v2.1.0 | 2.1.0 | `3600870f` | 2026-06-30 | checkpoint | 52 | `aa04ed32865d8213…` | `cd9cc1b16cc1…` |
| v3.0.0 | 3.0.0 | `decaa703` | 2026-07-13 | checkpoint | 80 | `72a676a9676b5bf1…` | `3eb7b0f26236…` |
| v4.0.0 | 4.0.0 | `623d3c72` | 2026-07-16 | checkpoint | 80 | `72a676a9676b5bf1…` | `df5ed40905ff…` |
| v5.0.0 | 5.0.0 | `5aed1d53` | 2026-07-19 | checkpoint | 91 | `57db7f637c4b1d73…` | `e3484358c262…` |
| v6.0.0 | 6.0.0 | `96cf3954` | 2026-07-22 | checkpoint | 117 | `b2bca1c6ee96be4a…` | `e6352111c368…` |
| v7.0.0 | 7.0.0 | `7d4f3b19` | 2026-07-24 | checkpoint | 180 | `2d8d0e57b4232640…` | `b3f7843691a2…` |
| v7.1.0 | 7.1.0 | `c251a6da` | 2026-07-31 | checkpoint | 185 | `e407a1e2c2e8c524…` | `8cc21c7f2251…` |
| **v7.2.0** | 7.2.0 | **`51d709e8`** | 2026-07-31 | **frozen baseline** | 189 | **`129f7be56482f9af…`** | `5248b0ea4349…` |
| v7.2.0+f5257056 | 7.2.0 | `f5257056` | 2026-08-08 | post-corpus | 189 | `c7781b73bcdac7c5…` | `07b723335dad…` |
| v7.2.0+8b79a386 | 7.2.0 | `8b79a386` | 2026-08-08 | post-corpus | 189 | `cc91fb4f398aa1e1…` | `14cf6d71a89c…` |
| v7.2.0+6b9bfc8e | 7.2.0 | `6b9bfc8e` | 2026-09-07 | post-corpus | 189 | `cc91fb4f398aa1e1…` | `8a5fbfc223b0…` |
| v7.2.0+20294216 | 7.2.0 | `20294216` | 2026-09-10 | post-corpus | 189 | `cc91fb4f398aa1e1…` | `39102cd80ee1…` |
| 7.3.0-pipelinetest.1 | — | overlay on `51d709e8` | 2026-10-17 | Phase 2 pipeline test | 191 | `2687851c8434379b…` | (base) |

**Empirical version-drift finding.**
- The semantic version **7.2.0** identifies 3 distinct rule-definition states and 5 distinct
  engine-code states over 41 days.
- v3.0.0 and v4.0.0 share identical rule definitions but differ in engine code.
- Engine-code changes alone moved measured recall: commit `13532073` (chunking), §8.
- A version string, or even a rule-definition hash on its own, therefore does not identify the
  executable behaviour. A release needs **both** the ruleset hash and the engine-code hash plus the
  commit.

Correction log: the Day 1 report said "five different rulesets". Two of the five apparent
differences were an artefact of my own hashing: `contract_types` list order followed
`PYTHONHASHSEED`. The first validation run caught it, and it is fixed in `manifest_v2.json`.
Details: `runs/validation/VALIDATION_LOG.md`.

## 5. Phase 1 — baseline (v7.2.0 @ `51d709e8`)

**Determinism (COMPLETE):**
- 618 docs × 10 runs = 6,180 executions, 0 documents with output or finding variance. The exact
  one-sided 95% upper bound on the per-document variance rate is 0.48%.
- Cross-process: 60 docs × 6 hash seeds, 0 variance.
- Day 1 results were independently re-executed on a 30-document sample for 3 releases: byte-identical.

**Expert-labelled performance (PRELIMINARY_MAPPING_PENDING_REVIEW).** Wilson 95% CIs for P/R;
document-cluster bootstrap 95% CI for F1. Source: `runs/phase6/20261017T010324Z/performance.json`.

| Set | Units | Precision | Recall | F1 |
|---|---|---|---|---|
| CUAD test, 21 mapped categories (fixed) | 2,142 | 0.663 [0.607, 0.715] | 0.354 [0.315, 0.395] | 0.462 [0.421, 0.501] |
| CUAD test, "direct" mappings only | 1,020 | 0.860 [0.790, 0.910] | 0.451 [0.390, 0.514] | 0.592 [0.534, 0.648] |
| ContractNLI test, 5 mapped hypotheses | 615 | 0.623 [0.528, 0.709] | 0.304 [0.247, 0.368] | 0.409 [0.346, 0.471] |

**Gold-label integrity:** the CUAD gold labels re-derived from a second source
(`master_clauses.csv`) agree on all 4,284 units checked.

**MCC slices:** firing statistics only (descriptive, `runs/v7.2.0/summary.json`); precision and
recall are **PENDING_HUMAN_ANNOTATION**.

## 6. Phase 2 — bounded adaptivity

Experiment `P2-ADAPT-PIPELINE-1`. **Authoritative run:** `runs/phase2/20261017T021857Z/`, executed
from committed code `de8970e8`. It is identical in every outcome field to the earlier working-tree
run `runs/phase2/20261017T004130Z/`; only the pipeline commit and the derived release hash differ.

**Mechanism properties, each verified by execution:**
- offline only;
- additive only (a new `<FAMILY>_A<n>` id; shadowing an existing id is refused);
- inactive until approved;
- technical + legal-domain reviewer for substantive-interpretation rules;
- append-only, hash-chained approval ledger;
- release = semver + pipeline Git commit + overlay SHA-256 + combined-ruleset SHA-256 + approval
  entry hashes;
- the worker verifies the overlay hash before inference.

**Run results:**

| Item | Result |
|---|---|
| Failure cases from frozen v7.2.0 on the ICCS labelled set (85 docs, 527 assertions) | 115 (70 FN, 45 FP). FP cases are out of scope for an additive-only mechanism |
| LLM proposal generation | **BLOCKED_API** for all 115 cases (no API key; no substitute model used) |
| Candidates | 2 hand-authored **fixtures** (for `emp_01` H_INDEM_01 / H_ATTFEE_01), both pass the automatic gate |
| Build before review | refused ("no review record") |
| Review | **TEST identities**, not real reviewers |
| Release | `7.3.0-pipelinetest.1`, overlay `e6d58c31…`, combined ruleset `2687851c…` (191 rules), release `b11f8f00…` (pipeline commit `de8970e8`) |
| Before/after on targeted failures | 2/2 fixed |
| Regression on previously passing ICCS assertions | 0 of 412 regressed; 8 newly passing (all on development data; fixtures were written after reading `emp_01`) |
| Corpus additivity (618 docs, 3 runs) | 0 docs lost any base finding; 4 findings added; 0 variance |
| Ledger integrity | verified |

**What this does NOT show:** anything about LLM-driven adaptation quality, susceptibility to
manipulation, or generalisation. Those require the API-dependent experiment.

## 7. Phase 3 — comparators

| Comparator | Step A (reproduce published metrics) | Status |
|---|---|---|
| CUAD RoBERTa-base (`akdeniz27/roberta-base-cuad`, community upload) | running on CPU; target AUPR 42.6 / P@80R 31.1 | **INCOMPLETE — not valid.** 96 of 4,182 test questions done when this report was written (the third test contract is 175k characters; shared CPU). No partial score is reported, because AUPR on a partial split is not comparable to Table 2. Resumable: `comparators/cuad_qa.py validate …` continues from `nbest_partial.jsonl`; restarted once after a container restart. Needs about 1 day of dedicated CPU or under 1 hour on a GPU |
| CUAD RoBERTa-large / DeBERTa-v2-xlarge | not run | **BLOCKED_GPU** (CPU ≈ 3 / 8–10 days); commands in `comparators/GPU_RUNBOOK.md` |
| ContractNLI Span NLI BERT | not run | **BLOCKED_GPU**: no official weights (repo `058c56f` has no tags, weight files or download link; no stanfordnlp/author HF models; only third-party uploads). Targets: BERT-base mAP .885, P@R80 .663, Acc .838, F1(C) .287, F1(E) .765 |
| LexNLP 2.3.0 | **not possible**: LexNLP publishes no benchmark split or reference metrics | sanity-validated (dates, durations, money, amounts all PASS). **UNVALIDATED** |

**LexNLP repair.**
- Root cause of the Day 1 failure: LexNLP calls `locale.setlocale('en_US')`, the container lacked
  that locale, and LexNLP silently dropped every digit-based amount.
- Fixed by generating the locale (`comparators/setup_lexnlp_env.sh`). The Day 1 output is kept
  under `runs/comparators/lexnlp_INVALID_extractors_broken/` with a diagnosis and is never scored.

**Engine vs LexNLP** (UNVALIDATED + PRELIMINARY_MAPPING). The two systems overlap on only 4 CUAD
categories (408 units: Cap On Liability, Insurance, Notice Period, Renewal Term).

| System | Precision | Recall | F1 |
|---|---|---|---|
| LexNLP | 0.558 | 0.492 | 0.523 |
| v7.2.0 | 0.562 | 0.381 | 0.455 |

Exact McNemar on correctness: 55 vs 57 discordant, p = 0.92 (no detectable difference).

## 8. Phase 4 — coverage vs determinism

**Ten measured checkpoints** on the same 618 documents. Every number is measured; nothing is
extrapolated. All performance rows are PRELIMINARY_MAPPING_PENDING_REVIEW. "Recall" is the
fixed-denominator recall (coverage).

| Release | Rules | Executions | Output variance | CUAD recall | CUAD precision | NLI recall |
|---|---|---|---|---|---|---|
| v1.0.3 (ICCS) | 25 | 1,854 | 0 | 0.213 | 0.712 | 0.253 |
| v2.0.0 | 40 | 1,854 | 0 | 0.240 | 0.708 | 0.263 |
| v2.1.0 | 52 | 1,854 | 0 | 0.240 | 0.708 | 0.263 |
| v3.0.0 | 80 | 1,854 | 0 | 0.246 | 0.683 | 0.290 |
| v4.0.0 | 80 | 1,854 | 0 | 0.246 | 0.683 | 0.290 |
| v5.0.0 | 91 | 1,854 | 0 | 0.310 | 0.655 | 0.198 |
| v6.0.0 | 117 | 1,854 | 0 | 0.332 | 0.655 | 0.304 |
| v7.0.0 | 180 | 1,854 | 0 | 0.354 | 0.663 | 0.304 |
| v7.1.0 | 185 | 1,854 | 0 | 0.354 | 0.663 | 0.304 |
| v7.2.0 | 189 | 6,180 | 0 | 0.354 | 0.663 | 0.304 |

- **Fixed denominator vs release scope.** Precision is identical under both, because out-of-scope
  units can only be predicted negative. Release-scope recall is reported in
  `runs/phase6/…/performance.json` (`subset=release_scope`).
- **Paired recall changes** (exact McNemar on gold-positive units, Holm-adjusted across
  consecutive releases):

| Dataset | Releases | TP gained | TP lost | Holm p |
|---|---|---|---|---|
| CUAD | v1.0.3 → v2.0.0 | 15 | 0 | 4.9e-4 |
| CUAD | v4.0.0 → v5.0.0 | 40 | 5 | 7.1e-7 |
| CUAD | v5.0.0 → v6.0.0 | 12 | 0 | 3.4e-3 |
| CUAD | v6.0.0 → v7.0.0 | 12 | 0 | 3.4e-3 |
| ContractNLI | v4.0.0 → v5.0.0 | 0 | **20** | 1.5e-5 |
| ContractNLI | v5.0.0 → v6.0.0 | 23 | 0 | 2.2e-6 |

**Regression / recovery analysis (COMPLETE for attribution; PRELIMINARY for the mapping).**

- **The "recovery" is masking, not recovery.** The ContractNLI aggregate drop at v5.0 and the
  return at v6.0 involve different hypotheses:
  - v5.0: nda-3 (verbally conveyed information) loses 19 TP and never recovers. It stays at
    19/73 through v7.2.0.
  - v6.0: nda-18 (no solicitation) gains 23 TP from a newly added non-solicit rule.
- **v5.0 cause.** Single-rule counterfactuals (`runs/phase4_counterfactual/20261017T004653Z`) point
  to the bounding of `L_BROADDEF_01` (`.*?` → `.{0,150}?`), which is responsible for the
  **majority but not all** of the loss:
  - reverting only that rule in v5.0 restores 13 of 19 TP;
  - applying only that change to v4.0 removes 16 of 19.
  The remainder comes from other changes in the same single commit `5aed1d53` and is not further
  attributed.
- **v2.1 → v3.0 cause.** nda-3 drops 47 → 38 with **identical rule definitions**. A commit
  bisection (`runs/phase4_counterfactual/bisect_v2.1_v3.0_*.json`) localises it to `13532073`,
  "Fix evidence offset drift by chunking on verbatim text slices".
- **Per-category transitions:** `runs/phase6/20261017T010324Z/transitions.csv`.

Figures: `runs/analysis/figures/day3/fig1_cuad_coverage_ci.png`,
`runs/analysis/figures/day3/fig3_contractnli_per_hypothesis.png`.

## 9. Scaling (COMPLETE; shapes only — shared-CPU timings)

| Relationship | Fit (log-log) | Data |
|---|---|---|
| Rule-count scaling: median s/doc vs rules | t ∝ rules^**1.02**, R² 0.983 | 10 releases |
| Document-length scaling: s/doc vs characters | exponent **0.96–1.03** per release, R² 0.957–0.988 | 618 docs per release |

- The two relationships are kept separate.
- The v7.0 → v7.2 runtime rise at near-constant rule count comes from engine code added around
  the rules, not from rule count.
- Source: `runs/analysis/scaling.json`. Figure: `runs/analysis/figures/day3/fig2_runtime_scaling.png`.

## 10. Phase 5 — security

### 10a. Proposal path (`P5-SEC-PROPOSAL-1`, 38 cases; all cases with expected and actual outcome in `runs/phase5_proposal/*/cases_full.json`)

| Group | PASS | FAIL | BLOCKED_API |
|---|---|---|---|
| PA1 malicious failure case | 2 | 0 | 1 (end-to-end LLM susceptibility) |
| PA2 attacker-desired candidates (gate) | 17 | 0 | 0 |
| PA2 well-formed but harmful | 3 | **1** | 0 |
| PA3 activation-boundary bypass | 13 | **1** | 0 |

- **FAIL PA2.18:** a severity-inflation variant (`L_GOVLAW_01_A1`, CRITICAL on every
  governing-law clause) passes the automatic gate. It still cannot activate without the
  two-reviewer approval (PASS), so for intent-level attacks **human review is the only control**.
- **FAIL PA3.14:** the inference worker checks overlay content against the hash supplied with it,
  not against the approved-release registry. A caller with code-execution rights could supply a
  self-consistent unapproved overlay. This is an integrity check, not authentication.
- **PASS:** shadowing, unknown family, ReDoS, empty-match, universal and over-broad patterns, code
  fields, disallowed fields (`contract_types`, `rule_class`), invalid severity, bad regex, giant
  pattern, silent no-op, wrong types, unreviewed / partial / rejected / tampered / forged-ledger /
  foreign-ledger / overwrite attempts, forged / unsigned / shadowing overlays.

### 10b. Inference path (`P5-SEC-INFERENCE-1`, `runs/phase5/20261017T013302Z`, plus benign control `P5-SEC-CONTROL-1`, `runs/phase5_control/20261017T021750Z`)

**Reconstruction.** The original E6/E9 harness is not in the repository, so these suites are rebuilt
from the published specification. The P1–P4 wording is ours. Each payload is inserted at the
document end and directly after the first authoritative finding ("in_clause") in **every** corpus
document.

| Suite | Release | Cases | FAIL vs original document | Benign insertion also changed F | **Injection-attributable** (≠ benign) |
|---|---|---|---|---|---|
| S1 instruction (P1–P4) | v7.2.0 | 4,944 | 748 | 132 | **693 = 14.0 % [13.1, 15.0]** |
| S1 instruction (P1–P4) | v1.0.3-iccs | 4,944 | 235 | 264 | **49 = 1.0 % [0.75, 1.31]** |
| S2 obfuscated (OB1–OB3 × P1/P4) | v7.2.0 | 720 | 6 | — | 0 |
| S2 obfuscated (OB1–OB3 × P1/P4) | v1.0.3-iccs | 720 | 32 | — | 14 |
| S3 explanation layer (stub LLM) | v7.2.0 / v1.0.3-iccs | 7 / 7 | **2 / 2** | n/a | n/a |
| S4 read-only, no change during inference | both | 2 / 2 | 0 | n/a | n/a |

**Interpretation, based on rule inspection and the control.**

- **No instruction is "followed".** The engine has no instruction channel, and the TPS
  regex-as-data argument holds in that sense.
- **The authoritative findings F can still be manipulated lexically by inserted text.**
  Containment as TPS defines it (F unchanged relative to benign insertion) fails in 14.0% of v7.2.0
  cases. 420 of 693 attributable cases (8.5% of all cases) **remove** a finding.
- **The dominant mechanism is REQUIRED_SECTION (absence-check) rules, whose topic and protective
  patterns are evaluated over the whole document rather than the relevant clause:**
  - `M_EXPENSE_APPROVAL_01` is suppressed 388 times because its protective pattern
    `\bpre[-\s]?approved\b` matches P3's "pre-approved by legal counsel" anywhere in the document.
  - `M_SLA_01` is added 238 times because its topic pattern `\bsystem\b` matches P2's "SYSTEM:"
    prefix.
- **REQUIRED_SECTION rules were introduced in v4.0.** That explains why the ICCS ruleset is far
  better contained. Paired on identical (document, payload, position) cells, ICCS is contained in
  682 cells where v7.2.0 is not, versus 38 the other way (exact McNemar p ≈ 1e-153).
- **The published 16/16 result is not contradicted for its own setup**, but it does **not**
  generalise to absence-check rules or to the full corpus.

**S3 (explanation layer, frozen v7.2.0 `evaluator.py`, scripted malicious client, no network):**

| Case | Result |
|---|---|
| Risk override, malformed JSON, missing keys, write-back, raw-text block | PASS |
| **S3.4 FAIL** | a fabricated top issue not mapped to any finding is returned. `_verify_output_maps_to_findings` only logs |
| **S3.7 FAIL** | injected text inside a matched clause appears verbatim in the LLM prompt, because up to 2 `matched_excerpt` strings per rule are sent. The LLM *does* receive raw contract excerpts; the earlier "never receives raw input text" framing is too strong. `prompt_security.py` sanitisation was only added on 2026-08-07, after the baseline |

**S4:** ruleset hash is identical before and after inference on 60 documents, and Rule objects are
frozen dataclasses (assignment raises).

## 11. Phase 6 — statistics

`runs/phase6/20261017T010324Z/`. All rows carry their source file and status label.

- **Performance:** Wilson CIs (P/R), document-cluster bootstrap CIs (F1; 2,000 resamples, seed
  20261017), for every release × {fixed, release-scope, direct-only} × {CUAD, ContractNLI}.
- **Paired tests:** exact McNemar, used only on identical unit sets. Two families:
  - correctness on all units;
  - detection on gold-positive units (recall).
  Holm correction is applied within each consecutive-release family. The release-pair raw
  observations are the `units_*.csv` files.
- **Comparator tests:** engine vs LexNLP on 408 common units, with the raw paired file
  `paired_units_engine_vs_lexnlp.csv`.
- **Determinism:** descriptive only, with exact 0-event upper bounds. No hypothesis test is
  applied, because a test of "engine vs sampler" would only restate the architecture.
- **Correctness-based McNemar, ICCS → v7.2.0:** p = 0.046 on CUAD, while the recall-specific test
  gives p ≈ 1e-19. Extra true positives are partly offset by extra false positives. Both are
  reported.

## 12. Unexpected findings and regressions

1. **Version drift.** One semver label covers 3 rule states and 5 engine states (§4).
2. **Masked regression.** The nda-3 loss at v5.0 is hidden in the aggregate by the nda-18 gain at
   v6.0 (§8). Aggregate recall can look "recovered" when it isn't.
3. **Engine-code-only regression.** Chunking commit `13532073` reduced recall with identical rule
   definitions, so rule hashes alone are insufficient provenance.
4. **Hash-seed dependence in canonicalisation.** A methodology bug in my own hashing, caught by the
   fresh-checkout validation and fixed. The engine outputs themselves are seed-independent (0
   cross-process variance).
5. **Within-process determinism protocol gap.** The Day 1 repetitions shared one interpreter.
   Closed by the cross-process experiment (0 variance).
6. **LLM boundary weaker than described (baseline).** Verbatim contract excerpts reach the LLM
   prompt, so injected text inside a matched clause is transmitted, and fabricated explanation
   items are only logged (§10b).
7. **LexNLP silent failure.** A missing system locale made LexNLP return empty results without
   raising an error.
8. **The original E6/E9 security harness is not in the repository.** The inference suite is a
   reconstruction from the published specification.
9. **Lexical manipulability of absence-check rules.** Injection containment, in the TPS sense of
   "F unchanged relative to benign insertion", fails in 14.0% of v7.2.0 cases, against 1.0% for
   ICCS. The cause is document-scoped topic and protective patterns in REQUIRED_SECTION rules
   (added in v4.0): inserted vocabulary can suppress a "missing protection" finding.
   Coverage-oriented rule growth weakened this security property, which is a direct
   coverage-versus-robustness trade-off.

## 13. Methodological limitations

- **Mapping dependence.** Every CUAD and ContractNLI precision/recall value depends on a draft
  category ↔ rule mapping written by the engine's author. It is a presence proxy: rules detect
  risk patterns, not clause presence. Review by Prof. Laakkonen and the legal reviewer is required.
- **Holdout.** No Q3-2026 holdout (§3). The MCC slices are clean only for the releases up to and
  including v7.2.0.
- **MCC precision/recall.** Not available until human annotation is complete.
- **Phase 2.** Mechanism only. The candidates are fixtures and the reviewers are test identities;
  no LLM experiment was run.
- **Phase 5 inference suite.** It is a reconstruction (the wording of P1–P4 is ours). The
  explanation-layer tests use a scripted stub client, not a real model.
- **Comparators.** Most are blocked (GPU). LexNLP is unvalidated, and its trigger heuristics are
  our adaptation.
- **Timings.** Taken on a shared 4-CPU container. Use the shapes, not the absolute values.
- **Provenance.** Several Day 2 runs executed from uncommitted working-tree code on top of
  `ec32d703`. Authoritative re-runs from committed code `de8970e8` are listed in §16; the earlier
  runs are retained.
- **Licence.** The MCC licence is non-commercial.

## 14. Results pending human annotation
- Precision and recall on the 332 MCC documents (employment, services, purchase, lease).
- Inter-annotator agreement (Cohen's κ).
- Review of the category ↔ rule mapping (converts PRELIMINARY rows to final).
- The real technical and legal-domain review of any Phase 2 proposal.

## 15. Blockers

| Item | Blocker |
|---|---|
| Span NLI BERT (ContractNLI) | BLOCKED_GPU (no released weights; must train) |
| CUAD RoBERTa-large, DeBERTa-v2-xlarge; any CUAD model on our corpus | BLOCKED_GPU |
| CUAD RoBERTa-base Step A | CPU, in progress (≈1 day of dedicated CPU) |
| LLM rule-proposal generation; LLM susceptibility (PA1.2); pure-LLM baseline rerun | BLOCKED_API |
| Q3-2026 MCC holdout | data not published; web-only export |
| LexNLP Step A | no published reference metrics exist |

## 16. Raw outputs (all under `experiments/followup/`)

| Experiment ID | Path | Contents | Code state |
|---|---|---|---|
| Corpus v1 | `corpus/manifest.csv`, `corpus/MANIFEST.sha256`, `corpus/summary.json` | frozen 618-row manifest (texts regenerable: `build_corpus.py`) | committed |
| Releases | `releases/manifest.json` (Day 1 record), `releases/manifest_v2.json` (canonical) | 15 engine states: commit, hashes, rule ids | committed |
| P1/P4 runs | `runs/<release>/results.jsonl`, `runs/<release>/summary.json` (12 states) | per-document finding sets, output and finding fingerprints, per-run timing medians | Day 1 (`e039ff00`) |
| Paired units | `runs/analysis/<release>/units_cuad.csv`, `units_contractnli.csv`, `paired_report.json` | raw paired (contract, category) observations | re-scored Day 1 with fixed-denominator code |
| Phase 4 curve / scaling | `runs/analysis/phase4_curve.csv`, `.md`, `runs/analysis/scaling.json` | aggregates | committed |
| VAL-DAY1 | `runs/validation/20261017T010147Z/`, `runs/validation/20261017T021819Z/` (from `de8970e8`), `runs/validation/VALIDATION_LOG.md` | 19/19 checks; Run 1 FAIL documented | as stated |
| DET-XPROC-1 | `runs/determinism_crossprocess/20261017T002540Z/` | raw per-seed fingerprints, summary | working tree before `de8970e8`; script unchanged in commit |
| P2-ADAPT-PIPELINE-1 | `runs/phase2/20261017T004130Z/` (working tree), `runs/phase2/20261017T021857Z/` (from `de8970e8`) | failure cases, BLOCKED_API log, ledger, frozen release, before/after assertions | as stated |
| P4-CF-1 / P4-BISECT-1 | `runs/phase4_counterfactual/20261017T004653Z/`, `…/20261017T021716Z/` (from `de8970e8`), `bisect_v2.1_v3.0_20261017T004907Z.json` | counterfactual and bisection results | as stated |
| P5-SEC-PROPOSAL-1 | `runs/phase5_proposal/20261017T004223Z/`, `…/20261017T010203Z/`, `…/20261017T021711Z/` (from `de8970e8`) | 38 cases each, expected/actual/evidence | as stated |
| P5-SEC-INFERENCE-1 | `runs/phase5/20261017T013302Z/` (`cases.csv`, `cases_full.jsonl`, `meta.json`); aborted first attempt documented in `runs/phase5/20261017T010157Z_ABORTED_restart/` | 11,346 cases (S1–S4, 2 releases) | working tree (parallel batching added after `de8970e8`; committed with this report) |
| P5-SEC-CONTROL-1 | `runs/phase5_control/20261017T021750Z/` (`attribution.csv`, `control_cases.csv`, `meta.json`, `stats.json`, `s2_attribution.json`) | benign-insertion control and attribution | committed with this report |
| P6-STATS-1 | `runs/phase6/20261017T010231Z/` (superseded), `runs/phase6/20261017T010324Z/` (current) | performance with CIs, paired tests, transitions, determinism, comparator tests | `de8970e8` |
| LexNLP | `runs/comparators/lexnlp_sanity/20261017T004410Z/sanity.json`, `runs/comparators/lexnlp/20261017T004410Z/`, quarantined `runs/comparators/lexnlp_INVALID_extractors_broken/` | sanity diagnostics, predictions, Day 1 invalid output and diagnosis | as stated |
| CUAD RoBERTa-base Step A | `runs/comparators/cuad_roberta-base/nbest_partial.jsonl` (gitignored while running; resumable) | n-best per question, partial | INCOMPLETE |
| Figures | `runs/analysis/figures/day3/fig1_cuad_coverage_ci.png`, `fig2_runtime_scaling.png`, `fig3_contractnli_per_hypothesis.png` (Day 1 versions in `runs/analysis/figures/`) | preliminary figures | committed |

Regenerable and not committed (size): `corpus/texts/`, `.releases/`, `external/`, and the injected
documents under `runs/phase5*/*/inputs/`.

## 17. Figures and tables for Prof. Laakkonen
- `runs/analysis/figures/day3/fig1_cuad_coverage_ci.png`: coverage vs release with 95% CIs (PRELIMINARY).
- `runs/analysis/figures/day3/fig3_contractnli_per_hypothesis.png`: masked regression.
- `runs/analysis/figures/day3/fig2_runtime_scaling.png`: separate rule-count and document-length scaling.
- Tables: §4 (versions and hashes), §5 (baseline), §8 (coverage trajectory and paired recall tests),
  §10 (security), `runs/analysis/phase4_curve.csv`, `runs/phase6/20261017T010324Z/*.json`.
