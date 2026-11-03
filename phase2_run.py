"""
Phase 2 run (experiment P2-ADAPT-PIPELINE-1): exercises the full bounded-adaptivity pipeline
on the frozen v7.2.0 baseline.

What is a RESULT here vs. a PIPELINE TEST:
  * Failure collection, BLOCKED_API status, gate decisions, ledger integrity, release hashes,
    before/after and regression measurements are real executions.
  * The candidate rules come from hand-authored FIXTURES and the reviewer identities are TEST
    identities. The resulting release (7.3.0-pipelinetest.1) demonstrates the mechanism; it is
    NOT evidence about LLM-driven adaptation quality, which is BLOCKED_API.

    python -m experiments.followup.phase2_run   ->  runs/phase2/<timestamp>/
"""
import csv
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from experiments.followup.adaptivity.pipeline import (BlockedAPI, FixtureProposalGenerator, LLMProposalGenerator,
                                                      Pipeline, collect_failures, sha256, validate_candidate)
from experiments.followup.releases import by_label, run_worker

F = Path(__file__).parent
BASE = "v7.2.0"
TEST_TECH = "TEST-TECHNICAL-REVIEWER (pipeline test, not a real review)"
TEST_LEGAL = "TEST-LEGAL-REVIEWER (pipeline test, not a real review)"


def iccs_labelled():
    docs = []
    for sub in ("ndas", "msas", "employment", "licensing"):
        for t in sorted((F.parent / "data" / sub).glob("*.truth.json")):
            did = t.name.replace(".truth.json", "")
            docs.append({"doc_id": did, "path": str(t.with_name(did + ".txt").resolve()), "truth": json.load(open(t))})
    return docs


def run(release_label, docs, overlay=None, runs=1):
    job = {"mode": "analyze", "runs": runs, "docs": [{"doc_id": d["doc_id"], "path": d["path"]} for d in docs]}
    if overlay:
        job["overlay"] = overlay
    out = []
    for i in range(0, len(job["docs"]), 150):
        out += run_worker(by_label(release_label), {**job, "docs": job["docs"][i:i + 150]})
    return {r["doc_id"]: r for r in out}


def credited(fired: set, overlay_ids: set) -> set:
    """An additive variant H_X_01_A1 credits its family H_X_01."""
    return fired | {rid.rsplit("_A", 1)[0] for rid in fired & overlay_ids}


def assertions(docs, results, overlay_ids=frozenset()):
    out = {}
    for d in docs:
        fired = credited(set(results[d["doc_id"]]["rule_ids_fired"]), set(overlay_ids))
        for r in d["truth"]["expected_rule_ids_present"]:
            out[(d["doc_id"], "present", r)] = r in fired
        for r in d["truth"].get("expected_rule_ids_absent", []):
            out[(d["doc_id"], "absent", r)] = r not in fired
    return out


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = F / "runs" / "phase2" / stamp
    out.mkdir(parents=True, exist_ok=False)
    rel = {r["label"]: r for r in json.load(open(F / "releases/manifest_v2.json"))}
    base_ids = set(rel[BASE]["rule_ids"])
    docs = iccs_labelled()
    texts = {d["doc_id"]: Path(d["path"]).read_text(encoding="utf-8") for d in docs}

    # 1. failures of the frozen baseline on the ICCS labelled set
    base_res = run(BASE, docs)
    cases = collect_failures(BASE, docs, base_res)
    (out / "failure_cases.json").write_text(json.dumps(cases, indent=2) + "\n")

    # 2. generation: real LLM (BLOCKED_API) and fixtures (pipeline test)
    llm = LLMProposalGenerator()
    gen_status = []
    for c in cases:
        try:
            llm.generate(c, texts[c["doc_id"]])
            gen_status.append({"case": c["case_sha256"], "status": "GENERATED"})
        except BlockedAPI as e:
            gen_status.append({"case": c["case_sha256"], "doc_id": c["doc_id"], "family": c["family"], "kind": c["kind"],
                               "status": "BLOCKED_API", "reason": str(e)})
    (out / "llm_generation_status.json").write_text(json.dumps(gen_status, indent=2) + "\n")

    pipe = Pipeline(out / "pipeline")
    fixtures = FixtureProposalGenerator(F / "adaptivity/fixtures/proposals_fixture.json")
    proposals = []
    for c in cases:
        if c["kind"] != "FN":
            continue  # additive-only mechanism cannot address false positives (documented limitation)
        negatives = [texts[d["doc_id"]] for d in docs if c["family"] not in d["truth"]["expected_rule_ids_present"]]
        for cand in fixtures.generate(c, texts[c["doc_id"]]):
            v = validate_candidate(cand, base_ids, texts[c["doc_id"]], negatives)
            proposals.append(pipe.propose(cand, c, v, generator="fixture"))
    fp_cases = [c for c in cases if c["kind"] == "FP"]

    # 3. activation boundary before review: building must be refused
    pre_review_refusal = None
    try:
        pipe.build_release(BASE, rel[BASE]["ruleset_sha256"], "7.3.0-pipelinetest.0", [p for p in proposals if p["status"] == "PROPOSED"])
    except PermissionError as e:
        pre_review_refusal = str(e)

    # 4. review (TEST identities) and freeze
    accepted = [p for p in proposals if p["status"] == "PROPOSED"]
    for p in accepted:
        pipe.review(p, technical_reviewer=TEST_TECH, legal_reviewer=TEST_LEGAL, decision="APPROVE",
                    notes="pipeline functional test; fixture candidate")
    release = pipe.build_release(BASE, rel[BASE]["ruleset_sha256"], "7.3.0-pipelinetest.1", accepted)
    overlay = {"rules": release["overlay_rules"], "sha256": release["overlay_sha256"]}
    overlay_ids = {r["rule_id"] for r in release["overlay_rules"]}
    combined = run_worker(by_label(BASE), {"mode": "rules", "overlay": overlay})

    # 5. before/after on failure cases + regression on previously passing ICCS assertions
    new_res = run(BASE, docs, overlay=overlay, runs=3)
    before, after = assertions(docs, base_res), assertions(docs, new_res, overlay_ids)
    target = [(c["doc_id"], "present", c["family"]) for c in cases if c["kind"] == "FN"
              and any(p["case"]["case_sha256"] == c["case_sha256"] and p["status"] == "PROPOSED" for p in proposals)]
    fixed = [k for k in target if not before[k] and after[k]]
    regressions = [k for k in before if before[k] and not after[k]]
    newly_passing = [k for k in before if not before[k] and after[k]]

    # 6. corpus-wide additivity + determinism of the new release on the frozen 618-document corpus
    corpus = [{"doc_id": r["doc_id"], "path": str((F / "corpus/texts" / f"{r['doc_id']}.txt").resolve())}
              for r in csv.DictReader(open(F / "corpus/manifest.csv", encoding="utf-8"))]
    base_corpus = {json.loads(l)["doc_id"]: json.loads(l) for l in open(F / "runs" / BASE / "results.jsonl")}
    new_corpus = run(BASE, corpus, overlay=overlay, runs=3)
    lost, added = [], Counter()
    for d, r in new_corpus.items():
        b = {tuple(x) for x in base_corpus[d]["findings"]}
        a = {tuple(x) for x in r["findings"]}
        if b - a:
            lost.append(d)
        for x in a - b:
            added[x[0]] += 1
    gold_regression = None
    try:  # mapping-dependent check: does the overlay change any CUAD/CNLI gold-unit prediction?
        mapping = json.load(open(F / "comparators/label_mapping.json"))
        mapped = {r for sec in ("cuad", "contractnli") for k, v in mapping[sec].items() if not k.startswith("_") for r in v["rules"]}
        gold_regression = {"overlay_ids_in_mapping": sorted(overlay_ids & mapped),
                           "note": "overlay rule ids are not in the CUAD/ContractNLI mapping, so gold-unit predictions are unchanged by construction"
                           if not overlay_ids & mapped else "re-run evaluate_paired with overlay"}
    except Exception as e:
        gold_regression = {"error": str(e)}

    ok, why = pipe.ledger.verify()
    result = {
        "experiment_id": "P2-ADAPT-PIPELINE-1", "timestamp": stamp, "git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=F).stdout.strip(),
        "base_release": {"label": BASE, "commit": rel[BASE]["commit"], "ruleset_sha256": rel[BASE]["ruleset_sha256"]},
        "corpus_manifest_sha256": (F / "corpus/MANIFEST.sha256").read_text().split()[0],
        "failure_cases": {"total": len(cases), "FN": sum(c["kind"] == "FN" for c in cases), "FP": len(fp_cases),
                          "FP_out_of_scope_for_additive_mechanism": len(fp_cases)},
        "llm_generation": {"status": "BLOCKED_API", "cases_blocked": sum(s["status"] == "BLOCKED_API" for s in gen_status)},
        "fixture_proposals": [{"rule_id": p["candidate"].get("rule_id"), "status": p["status"], "violations": p["violations"],
                               "proposal_sha256": p["proposal_sha256"]} for p in proposals],
        "pre_review_build_refused": pre_review_refusal,
        "release": {k: release[k] for k in ("version", "base_release", "base_ruleset_sha256", "overlay_sha256",
                                            "release_sha256", "pipeline_git_commit", "approval_entry_sha256")},
        "combined_ruleset": {"rule_count": combined["rule_count"], "ruleset_sha256": combined["ruleset_sha256"]},
        "before_after_failure_cases": {"targeted": len(target), "fixed": [list(k) for k in fixed]},
        "regression_iccs_assertions": {"assertions": len(before), "passing_before": sum(before.values()),
                                       "passing_after": sum(after.values()), "regressions": [list(k) for k in regressions],
                                       "newly_passing": [list(k) for k in newly_passing]},
        "corpus_additivity": {"docs": len(new_corpus), "docs_with_any_base_finding_lost": lost,
                              "added_findings_by_rule": dict(added),
                              "docs_with_variance_3runs": sum(r["distinct_output_hashes"] > 1 for r in new_corpus.values())},
        "gold_unit_regression": gold_regression,
        "ledger_verify": {"ok": ok, "detail": why},
        "labels": {"candidates": "TEST FIXTURES (hand-authored)", "reviewers": "TEST identities",
                   "release": "pipeline test release; not a research result about LLM adaptation"},
    }
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    (out / "iccs_assertions_before_after.json").write_text(json.dumps(
        [{"doc_id": k[0], "kind": k[1], "rule": k[2], "before": before[k], "after": after[k]} for k in sorted(before)], indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ("failure_cases", "llm_generation", "fixture_proposals", "pre_review_build_refused",
                                             "before_after_failure_cases", "corpus_additivity", "ledger_verify")}, indent=1)[:4000])
    print("regressions:", len(regressions), "newly passing:", len(newly_passing))
    print(out)


if __name__ == "__main__":
    main()
