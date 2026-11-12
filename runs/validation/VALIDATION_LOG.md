# Validation log

## Run 1 — 2026-10-17 ~00:30 UTC — 18/19 PASS, 1 FAIL (output file later overwritten; reconstructed here from the session log)

FAIL releases.all_hashes_reproduce_from_fresh_checkout
  mismatches: v7.2.0+8b79a386, v7.2.0+6b9bfc8e, v7.2.0+20294216

Diagnosis: the canonical ruleset hash was not stable across processes for engine states that build
`Rule.contract_types` from a Python set (introduced 2026-08-08, `f5257056`): list order followed
PYTHONHASHSEED. Demonstrated by hashing the same tree three times (three different hashes) and
by diffing two seeds (only `contract_types` order differed, in 7 rules). The engine tests
membership only (`contract_type in rule.contract_types`), so canonicalisation must sort it.
All pre-corpus states, including the v7.2.0 baseline (`51d709e8`), were already stable.

Fix: release_worker.SET_SEMANTIC_FIELDS = ("contract_types",), sorted in the canonical form.
New manifest written to releases/manifest_v2.json; the Day 1 releases/manifest.json is kept unchanged as the record.
Effect on Day 1 claims: "7.2.0" covers **3** distinct rule-definition states (not 5) and 5 distinct
engine-code states. Two of the five Day 1 "rulesets" were hashing artefacts.

## Run 2 — 20261017T010147Z — 19/19 PASS
Fresh-checkout hashes computed under PYTHONHASHSEED=12345 reproduce manifest_v2.json for all 15 states.
Files: runs/validation/20261017T010147Z/day1_validation.{json,md}

## Additional methodological check added after Run 1
Day 1 repetitions all ran inside one interpreter (one hash seed). Cross-process determinism
(60 docs x 6 PYTHONHASHSEED values x 15 engine states = 5,400 executions) found 0 output variance:
runs/determinism_crossprocess/20261017T002540Z/.
