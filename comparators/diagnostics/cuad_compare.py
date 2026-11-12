"""
CUAD diagnostic comparison (DIAG-CUAD-1): our pre-registered n-best vs the reference pipeline's
n-best on the same sampled questions. Sample-level AUPR uses the official evaluate.py functions
restricted to the sampled questions. Sample numbers are diagnostics, not Step A results.

    python cuad_compare.py --ours <nbest_partial.jsonl[.gz]> --ref <dir with nbest_predictions_.json> [--ref ...]
"""
import argparse
import gzip
import importlib.util
import json
import os
from pathlib import Path

F = Path(__file__).resolve().parents[2]


def official():
    cwd = os.getcwd()
    os.chdir(F / "external")
    spec = importlib.util.spec_from_file_location("ev", F / "external" / "cuad_evaluate.py")
    ev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ev)
    os.chdir(cwd)
    return ev


def ws(t):
    return " ".join(t.split())


def ws_normalize(nb):
    """Reference-style answer text (whitespace tokens joined by one space), deduplicated by final text
    keeping the highest-scoring entry, probabilities renormalised (= softmax over the kept scores)."""
    seen = {}
    for x in nb:
        t = ws(x["text"])
        if t not in seen:
            seen[t] = x["probability"]
    z = sum(seen.values())
    return [{"text": t, "probability": p / z} for t, p in seen.items()]


def load_ours(path):
    op = gzip.open if str(path).endswith(".gz") else open
    return {r["id"]: [{"text": x["text"], "probability": x["probability"]} for x in r["nbest"]]
            for r in (json.loads(l) for l in op(path, "rt"))}


def main(a):
    ev = official()
    refs = {Path(r).name: json.load(open(Path(r) / "nbest_predictions_.json")) for r in a.ref}
    ids = sorted(next(iter(refs.values())))
    ours_all = load_ours(a.ours)
    ours = {i: ours_all[i] for i in ids}
    test = json.load(open(F / "external/cuad_split/test.json"))
    gt = {k: v for k, v in ev.get_answers(test).items() if k in set(ids)}

    def score(nb):
        p, r, c = ev.get_precisions_recalls(nb, gt)
        return {"aupr": round(100 * ev.get_aupr(p, r), 2), "p_at_80r": round(100 * ev.get_prec_at_recall(p, r, c, 0.8)[0], 2)}

    def top(nb):
        return ws(nb[0]["text"])

    systems = {"ours_preregistered": ours, "ours_ws_normalized": {i: ws_normalize(v) for i, v in ours.items()}}
    systems.update({f"reference[{k}]": {i: [{"text": x["text"], "probability": x["probability"]} for x in v[i]]
                                        for i in ids} for k, v in refs.items()})
    out = {"questions": len(ids), "gold_positive_questions": sum(bool(gt[i]) for i in ids), "systems": {}}
    base = systems[f"reference[{next(iter(refs))}]"]
    for name, nb in systems.items():
        out["systems"][name] = {**score(nb), "top_is_null": sum(top(nb[i]) == "" for i in ids),
                                "top_agrees_with_first_reference": sum(top(nb[i]) == top(base[i]) for i in ids)}
    print(json.dumps(out, indent=2))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ours", required=True)
    p.add_argument("--ref", action="append", required=True)
    p.add_argument("--out")
    main(p.parse_args())
