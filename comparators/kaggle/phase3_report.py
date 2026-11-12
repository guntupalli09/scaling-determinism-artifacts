"""
Phase 3 validation report, generated only from the files under the state directory.

Reporting rules (same as the rest of the study):
  * a metric is printed only for a stage that reached a terminal state; in-progress work shows
    counts only (questions or units done / expected), never a partial score;
  * Step A results are printed for PASS and FAIL alike; a failed reproduction is a result;
  * comparator-vs-engine numbers appear only after Step A PASS and are marked
    PRELIMINARY_MAPPING_PENDING_REVIEW (the category<->rule mapping is still under review);
  * Phase 3 is COMPLETE only when every comparator below has a terminal Step A and, where it
    passed, finished Steps B/C. Anything else is INCOMPLETE.

    python phase3_report.py --state /kaggle/working/phase3_state
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

CUAD = ["roberta-base", "roberta-large", "deberta-v2-xlarge"]
TERMINAL_A = ("STEP_A_PASS", "STEP_A_FAIL")
MAPPING = "PRELIMINARY_MAPPING_PENDING_REVIEW"


def load(path):
    return json.loads(path.read_text()) if path.exists() else None


def lines(path):
    if not path.exists():
        return 0
    with open(path, encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def fmt(x):
    return "n/a" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))


def main(state):
    st = load(state / "stages.json") or {}
    get = lambda k: st.get(k, {}).get("status", "NOT_STARTED")
    envs = load(state / "environment.json") or []
    rows, status, md = [], {}, []
    complete = True

    md.append("# Phase 3 validation report\n")
    md.append(f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} from `{state}`. "
              "Protocol: Step A (reproduce published metrics, pre-registered tolerances) → Step B (frozen corpus) "
              "→ Step C (paired comparison), B/C only after Step A PASS. No tuning.\n")
    if envs:
        md.append("## Sessions\n\n| Started (UTC) | GPUs | Repo commit | Dirty |\n|---|---|---|---|")
        for e in envs:
            md.append(f"| {e['at']} | {'; '.join(e['gpus']) or 'none'} | `{e['repo_commit'][:10]}` | {e['repo_dirty']} |")
        md.append("")
    md.append(f"Data: {get('data')}" + (f" (manifest sha256 `{st['data'].get('manifest_sha256', '')[:16]}…`)"
                                         if get('data') == "OK" else "") + "\n")

    # ---- CUAD
    md.append("## CUAD (Hendrycks et al. 2021, Table 2), test split, 4,182 questions\n")
    md.append("| Model | Step A | AUPR (published) | P@80R (published) | Step B frozen corpus | Step C paired |\n|---|---|---|---|---|---|")
    for key in CUAD:
        a, b, c = get(f"cuad_{key}_step_a"), get(f"cuad_{key}_step_b"), get(f"cuad_{key}_step_c")
        res = load(state / f"cuad_{key}_gpu" / "step_a_result.json")
        if a in TERMINAL_A and res:
            aupr = f"{res['reproduced']['aupr']:.1f} ({res['published']['aupr']})"
            p80 = f"{res['reproduced']['p_at_80r']:.1f} ({res['published']['p_at_80r']})"
        else:
            done = lines(state / f"cuad_{key}_gpu" / "nbest_partial.jsonl")
            a = f"{a} ({done}/4182 questions)" if a not in TERMINAL_A else a
            aupr = p80 = "not scored"
        if not a.startswith("STEP_A_PASS"):
            b_txt = c_txt = "gated (Step A not passed)" if a.startswith("STEP_A_FAIL") else "waits on Step A"
        else:
            units = lines(state / f"cuad_{key}_gpu_corpus" / "predictions.jsonl")
            b_txt = b if b == "COMPLETE" else f"{b} ({units}/25338 units)"
            c_txt = c
        md.append(f"| {key} | {a} | {aupr} | {p80} | {b_txt} | {c_txt} |")
        ok = a.startswith("STEP_A_FAIL") or (a.startswith("STEP_A_PASS") and b == "COMPLETE" and c == "COMPLETE")
        complete &= ok
        status[f"cuad_{key}"] = {"step_a": get(f"cuad_{key}_step_a"), "step_b": b, "step_c": c, "complete": ok}
    md.append("")
    for key in CUAD:
        rep = load(state / f"paired_cuad_{key}" / "paired_report.json")
        if get(f"cuad_{key}_step_a") == "STEP_A_PASS" and get(f"cuad_{key}_step_c") == "COMPLETE" and rep:
            cm = rep["cuad"].get("cuad_model", {})
            if isinstance(cm, dict):
                m, e, t = cm["on_common_units"], cm["engine_on_same_units"], cm["mcnemar_engine_vs_cuad_model"]
                md.append(f"**{key} vs engine v7.2.0** ({MAPPING}; {m['units']} paired units): "
                          f"model P/R/F1 {fmt(m['precision'])}/{fmt(m['recall'])}/{fmt(m['f1'])}, "
                          f"engine {fmt(e['precision'])}/{fmt(e['recall'])}/{fmt(e['f1'])}, exact McNemar p = {fmt(t.get('p_value'))}. "
                          f"Units: `paired_cuad_{key}/units_cuad.csv`.\n")

    # ---- ContractNLI
    md.append("## ContractNLI Span NLI BERT-base (Koreeda & Manning 2021, Table 3), test split\n")
    tr, te, a, pr = get("cnli_train"), get("cnli_test"), get("cnli_step_a"), get("cnli_pairing")
    res = load(state / "contractnli_bert-base" / "step_a_result.json")
    md.append(f"- Environment: {get('cnli_env')} {st.get('cnli_env', {}).get('torch', '')}; training (conf_base.yml, seed 42, "
              f"one GPU): **{tr}**; test.py: **{te}**")
    if a in TERMINAL_A and res:
        r, t = res["reproduced"], res["targets"]
        md.append(f"- Step A: **{a}**. mAP {fmt(r['map'])} (target {t['map']}), accuracy {fmt(r['accuracy'])} "
                  f"({t['accuracy']}), F1(E) {fmt(r['f1_entailment'])} ({t['f1_entailment']}); key paths "
                  f"`{res['key_paths_used']}`")
    else:
        md.append(f"- Step A: **{a}**" + (" (metric keys missing; see step_a_result.json)" if a.startswith("INCONCLUSIVE") else ""))
    pres = load(state / "contractnli_bert-base" / "paired_result.json")
    if a == "STEP_A_PASS" and pr == "COMPLETE" and pres:
        m = pres["mcnemar_correctness"]
        md.append(f"- Pairing vs engine v7.2.0 ({MAPPING}; {pres['units']} units): Span NLI BERT F1 "
                  f"{fmt(pres['span_nli_bert']['f1'])}, engine F1 {fmt(pres['engine']['f1'])}, exact McNemar p = "
                  f"{fmt(m.get('p_value') if isinstance(m, dict) else None)}")
    else:
        md.append(f"- Pairing: {pr if a in TERMINAL_A else 'waits on Step A'}")
    cnli_ok = a == "STEP_A_FAIL" or (a == "STEP_A_PASS" and pr == "COMPLETE")
    complete &= cnli_ok
    status["contractnli_bert-base"] = {"train": tr, "test": te, "step_a": a, "pairing": pr, "complete": cnli_ok}
    md.append("")

    errors = {k: v for k, v in st.items() if v.get("status", "").startswith(("ERROR", "BLOCKED"))}
    if errors:
        md.append("## Errors / blockers\n")
        for k, v in errors.items():
            md.append(f"- `{k}`: {v['status']} {json.dumps({x: y for x, y in v.items() if x not in ('status',)})[:400]}")
        md.append("")

    md.append("## Known deviations from the original setups (declared, not tuned)\n")
    md.append("- CUAD: community checkpoints `akdeniz27/*-cuad`; our re-implementation of HF SQuAD-v2 post-processing "
              "(max_seq 512, stride 256, n-best 20, fp32); tolerance pre-registered in `cuad_step_a.py` (commit `09e7990f`).")
    md.append("- ContractNLI: one published configuration (conf_base.yml, seed 42) instead of the paper's 100-config sweep "
              "averaged over the best 3; torch 1.8.1+cu111 (the authors' README build for newer GPUs) instead of 1.7.1; "
              "other pins as in the authors' requirements.txt, plus packaging==20.9 and protobuf==3.20.3 (unpinned "
              "transitive dependencies whose current versions break transformers 4.5.1 / tensorboard 2.4.1).")
    md.append("- Hardware: Kaggle free GPU (see Sessions). Results from a different GPU may differ in the last digits.\n")
    overall = "COMPLETE" if complete else "INCOMPLETE"
    passed = sum(v.get("step_a") == "STEP_A_PASS" for v in status.values())
    md.insert(1, f"**Phase 3 status: {overall}.** Step A passed for {passed} of {len(status)} comparators"
              + (" (a protocol-complete Phase 3 may still contain failed reproductions; those are results, "
                 "and the failed comparators are not compared with the engine)." if complete else ".") + ("" if complete else
              " At least one comparator has not reached a terminal Step A or has unfinished Steps B/C; "
              "nothing below that is marked in progress is a result.") + "\n")
    (state / "PHASE3_VALIDATION_REPORT.md").write_text("\n".join(md) + "\n")
    (state / "phase3_status.json").write_text(json.dumps({"overall": overall, "step_a_passed": passed, "comparators": status}, indent=2) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--state", required=True)
    main(Path(p.parse_args().state))
