"""
CUAD Step B (amendment B9, approved 2026-11-02; review_package/DECISION_STEP_B_APPROVAL.md): the corrected, validated
CUAD inference procedure applied to the frozen evaluation corpus (corpus/manifest.csv, 618 documents) for all 41
CUAD questions.

The procedure is the one validated in Step A (comparators/diagnostics/cuad_reference_pipeline.py), unchanged:
legacy SQuAD-v2 features, slow tokenizer, max_seq_length 512, doc_stride 256, max_query_length 64, token_type_ids
dropped for roberta-family models, the authors' compute_predictions_logits (external/cuad_utils.py) with n_best 20,
max_answer_length 512, null_score_diff_threshold 0.0. Each frozen document becomes one SQuAD-v2 example per CUAD
question; the question text is CUAD's own (comparators/cuad_questions.json, verbatim from the CUAD test split).
Example ids are "<doc_id>__<category>".

Work is split into deterministic chunks (plan.json): small documents are grouped up to --chunk-chars characters,
and a larger document is split into blocks of questions, so one chunk takes minutes, not hours. Each finished chunk
writes chunk_NNNN/nbest.json.gz and is never recomputed (resumable). A chunk is only started when the remaining
--budget-hours cover it, estimated from the measured rate, so a time-limited session ends cleanly.

    python cuad_step_b.py run   --model akdeniz27/roberta-base-cuad --state DIR [--skip-slices cuad_test]
                                [--shard-of 2 --shards 0]
    python cuad_step_b.py merge --state DIR      # -> predictions.jsonl.gz, cuad_test/nbest_partial.jsonl
"""
import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import os
import time
from pathlib import Path

F = Path(__file__).resolve().parents[2]
FROZEN_MANIFEST_SHA = "3bcd0d90806f244197d7afe6ca1752dbcae4dad6430d06c7b81fd4130a8c755b"
ROBERTA_FAMILY = ("xlm", "roberta", "distilbert", "camembert", "bart", "longformer")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def corpus():
    man = F / "corpus/manifest.csv"
    assert sha256(man) == FROZEN_MANIFEST_SHA, "corpus manifest is not the frozen one"
    rows = list(csv.DictReader(open(man, encoding="utf-8")))
    questions = json.load(open(F / "comparators/cuad_questions.json", encoding="utf-8"))
    return rows, questions


def make_plan(chunk_chars, skip_slices):
    rows, questions = corpus()
    cats = list(questions)
    chunks, group, size = [], [], 0
    for r in rows:
        if r["slice"] in skip_slices:
            continue
        n = int(r["chars"])
        if n > chunk_chars:                       # large document: blocks of questions
            blocks = math.ceil(n / chunk_chars)
            per = math.ceil(len(cats) / blocks)
            for i in range(0, len(cats), per):
                chunks.append({"units": [[r["doc_id"], cats[i:i + per]]], "chars": n * len(cats[i:i + per]) / len(cats)})
            continue
        if group and size + n > chunk_chars:
            chunks.append({"units": group, "chars": size})
            group, size = [], 0
        group.append([r["doc_id"], cats])
        size += n
    if group:
        chunks.append({"units": group, "chars": size})
    return {"manifest_sha256": FROZEN_MANIFEST_SHA, "chunk_chars": chunk_chars, "skip_slices": sorted(skip_slices),
            "questions": len(cats), "units_expected": sum(len(c) for ch in chunks for _, c in ch["units"]),
            "chunks": chunks}


def squad_dict(chunk, rows_by_id, questions):
    data = []
    for doc_id, cats in chunk["units"]:
        text = (F / "corpus/texts" / f"{doc_id}.txt").read_text(encoding="utf-8")
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == rows_by_id[doc_id]["text_sha256"], doc_id
        data.append({"title": doc_id, "paragraphs": [{"context": text, "qas": [
            {"id": f"{doc_id}__{c}", "question": questions[c], "answers": [], "is_impossible": False} for c in cats]}]})
    return {"version": "v1", "data": data}


def load_reference_utils():
    spec = importlib.util.spec_from_file_location("cuad_utils", F / "external" / "cuad_utils.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def infer_chunk(sub, cdir, tok, model, device, batch_size, threads):
    """cuad_reference_pipeline.main, with the example set given directly instead of selected by title."""
    import torch
    from torch.utils.data import DataLoader
    from transformers.data.processors.squad import SquadResult, SquadV2Processor, squad_convert_examples_to_features
    sub_path = cdir / "chunk_input.json"
    sub_path.write_text(json.dumps(sub))
    examples = SquadV2Processor().get_dev_examples(str(cdir), filename=sub_path.name)
    features, dataset = squad_convert_examples_to_features(
        examples=examples, tokenizer=tok, max_seq_length=512, doc_stride=256, max_query_length=64,
        is_training=False, return_dataset="pt", threads=threads)
    results = []
    for batch in DataLoader(dataset, batch_size=batch_size):
        batch = tuple(t.to(device) for t in batch)
        inputs = {"input_ids": batch[0], "attention_mask": batch[1], "token_type_ids": batch[2]}
        if model.config.model_type in ROBERTA_FAMILY:
            del inputs["token_type_ids"]
        with torch.inference_mode():
            o = model(**inputs)
        for i, fi in enumerate(batch[3]):
            f = features[fi.item()]
            results.append(SquadResult(int(f.unique_id), o.start_logits[i].float().cpu().tolist(),
                                       o.end_logits[i].float().cpu().tolist()))
    load_reference_utils().compute_predictions_logits(
        sub, examples, features, results, 20, 512, False, str(cdir / "predictions_.json"),
        str(cdir / "nbest_predictions_.json"), str(cdir / "null_odds_.json"), False, True, 0.0, tok)
    nb = json.load(open(cdir / "nbest_predictions_.json"))
    with gzip.open(cdir / "nbest.json.gz.tmp", "wt") as fh:
        json.dump(nb, fh)
    os.replace(cdir / "nbest.json.gz.tmp", cdir / "nbest.json.gz")   # the chunk counts as done only now
    for p in ("chunk_input.json", "predictions_.json", "nbest_predictions_.json", "null_odds_.json"):
        (cdir / p).unlink(missing_ok=True)
    return len(examples), len(features)


def run(a):
    state = Path(a.state)
    state.mkdir(parents=True, exist_ok=True)
    plan_path = state / "plan.json"
    plan = make_plan(a.chunk_chars, set(a.skip_slices))
    if plan_path.exists():                       # resuming: the plan must be the same frozen plan
        assert json.load(open(plan_path)) == plan, "plan.json differs from this configuration"
    else:                                         # atomic: parallel shards may start together
        tmp = state / f"plan.json.{os.getpid()}"
        tmp.write_text(json.dumps(plan, indent=1) + "\n")
        os.replace(tmp, plan_path)
    rows, questions = corpus()
    by_id = {r["doc_id"]: r for r in rows}
    # shard k of n takes chunks i with i % n == k: several GPUs or machines never overlap
    mine = [i for i in range(len(plan["chunks"])) if i % a.shard_of in a.shards]
    todo = [i for i in mine if not (state / f"chunk_{i:04d}" / "nbest.json.gz").exists()]
    log = open(state / f"run_log_shards{'-'.join(map(str, a.shards))}of{a.shard_of}.jsonl", "a")
    print(f"shards {a.shards} of {a.shard_of}: {len(mine) - len(todo)}/{len(mine)} chunks done; {len(todo)} to do",
          flush=True)
    if not todo:
        return
    import torch
    import transformers
    from transformers import AutoModelForQuestionAnswering, AutoTokenizer
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(a.model, use_fast=False)
    model = AutoModelForQuestionAnswering.from_pretrained(a.model).eval().to(device)
    deadline = time.time() + a.budget_hours * 3600
    rate = a.initial_sec_per_kchar           # seconds per 1,000 characters x questions/41, updated as we go
    for i in todo:
        ch = plan["chunks"][i]
        est = rate * ch["chars"] / 1000 * 1.5
        if time.time() + est > deadline:
            log.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "stop": "budget",
                                  "next_chunk": i, "estimated_s": round(est)}) + "\n")
            print(f"budget: stopping before chunk {i} (estimated {est:.0f}s)", flush=True)
            break
        cdir = state / f"chunk_{i:04d}"
        cdir.mkdir(exist_ok=True)
        t0 = time.time()
        nq, nf = infer_chunk(squad_dict(ch, by_id, questions), cdir, tok, model, device, a.batch_size, a.threads)
        dt = time.time() - t0
        rate = dt / (ch["chars"] / 1000)
        rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "chunk": i, "questions": nq, "features": nf,
               "units_expected": sum(len(c) for _, c in ch["units"]),
               "seconds": round(dt, 1), "model": a.model, "device": device, "torch": torch.__version__,
               "transformers": transformers.__version__}
        log.write(json.dumps(rec) + "\n")
        log.flush()
        print(json.dumps(rec), flush=True)


def merge(a):
    state = Path(a.state)
    plan = json.load(open(state / "plan.json"))
    rows, _ = corpus()
    by_id = {r["doc_id"]: r for r in rows}
    merged = {}
    for i in range(len(plan["chunks"])):
        p = state / f"chunk_{i:04d}" / "nbest.json.gz"
        assert p.exists(), f"chunk {i} not done"
        merged.update(json.load(gzip.open(p, "rt")))
    assert len(merged) == plan["units_expected"], (len(merged), plan["units_expected"])
    with gzip.open(state / "predictions.jsonl.gz", "wt") as fh:
        for uid, nb in merged.items():
            doc_id, cat = uid.split("__", 1)
            fh.write(json.dumps({"doc_id": doc_id, "slice": by_id[doc_id]["slice"], "category": cat,
                                 "nbest": [{"text": x["text"], "probability": x["probability"]} for x in nb]}) + "\n")
    # CUAD-test slice in the Step A format (id = CUAD title__category), for the unchanged scorer and Step C
    cuad = [(uid, nb) for uid, nb in merged.items() if by_id[uid.split("__", 1)[0]]["slice"] == "cuad_test"]
    if cuad:
        (state / "cuad_test").mkdir(exist_ok=True)
        with open(state / "cuad_test" / "nbest_partial.jsonl", "w") as fh:
            for uid, nb in cuad:
                doc_id, cat = uid.split("__", 1)
                fh.write(json.dumps({"id": f"{by_id[doc_id]['source_ref']}__{cat}", "nbest": [
                    {"text": x["text"], "probability": x["probability"]} for x in nb]}) + "\n")
    print(f"merged {len(merged)} units ({len(cuad)} cuad_test) -> {state / 'predictions.jsonl.gz'}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--model", required=True)
    r.add_argument("--state", required=True)
    r.add_argument("--skip-slices", nargs="*", default=[])
    r.add_argument("--chunk-chars", type=int, default=150000)
    r.add_argument("--budget-hours", type=float, default=11.0)
    r.add_argument("--initial-sec-per-kchar", type=float, default=10.0, help="first estimate; measured afterwards")
    r.add_argument("--shard-of", type=int, default=1)
    r.add_argument("--shards", type=int, nargs="+", default=[0])
    r.add_argument("--batch-size", type=int, default=16)
    r.add_argument("--threads", type=int, default=os.cpu_count() or 1)
    m = sub.add_parser("merge")
    m.add_argument("--state", required=True)
    a = p.parse_args()
    run(a) if a.cmd == "run" else merge(a)
