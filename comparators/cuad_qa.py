"""
Phase 3 neural comparator: CUAD extractive-QA models (RoBERTa / DeBERTa).

Reproduces the CUAD paper's inference protocol (Hendrycks et al., 2021): SQuAD-v2
style windows (max_seq_length 512, doc_stride 256), n-best of 20 with a null
answer, and SQuAD-style n-best probabilities (softmax over candidate scores),
which is the input format the official CUAD evaluate.py scores.

Runs in its own virtualenv (torch + transformers); it imports nothing from the repo.

  Step 1, validation on the CUAD test split (writes nbest_predictions_.json for evaluate.py):
    python cuad_qa.py validate --model akdeniz27/roberta-base-cuad --out runs/comparators/cuad_roberta-base
  Step 2/3, our corpus (one JSON line per contract x category, for exact pairing):
    python cuad_qa.py corpus --model ... --manifest corpus/manifest.csv --texts corpus/texts --out ...
"""
import argparse
import csv
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForQuestionAnswering, AutoTokenizer

MAX_SEQ = 512
DOC_STRIDE = 256
N_BEST = 20
MAX_ANSWER_TOKENS = 512


DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def load(model_name):
    tok = AutoTokenizer.from_pretrained(model_name, use_fast=True)
    model = AutoModelForQuestionAnswering.from_pretrained(model_name).eval().to(DEVICE)
    torch.set_num_threads(max(1, os.cpu_count() or 1))
    return tok, model


@torch.inference_mode()
def nbest_for(tok, model, question, context, batch_size=16):
    q_len = len(tok(question, add_special_tokens=False)["input_ids"])
    ctx_room = MAX_SEQ - q_len - 4
    enc = tok(question, context, truncation="only_second", max_length=MAX_SEQ,
              stride=max(0, ctx_room - DOC_STRIDE), return_overflowing_tokens=True,
              return_offsets_mapping=True, padding="max_length", return_tensors="pt")
    offsets = enc.pop("offset_mapping")
    enc.pop("overflow_to_sample_mapping", None)
    seq_ids = [enc.sequence_ids(i) for i in range(enc["input_ids"].shape[0])]
    starts, ends = [], []
    for i in range(0, enc["input_ids"].shape[0], batch_size):
        out = model(**{k: v[i:i + batch_size].to(DEVICE) for k, v in enc.items()})
        starts.append(out.start_logits.float().cpu().numpy())
        ends.append(out.end_logits.float().cpu().numpy())
    starts, ends = np.concatenate(starts), np.concatenate(ends)

    candidates, null_score = {}, math.inf
    for f in range(starts.shape[0]):
        s, e, ids, offs = starts[f], ends[f], seq_ids[f], offsets[f].tolist()
        null_score = min(null_score, float(s[0] + e[0]))
        ctx = [j for j, sid in enumerate(ids) if sid == 1]
        if not ctx:
            continue
        lo, hi = ctx[0], ctx[-1]
        top_s = [j for j in np.argsort(s)[::-1][:N_BEST] if lo <= j <= hi]
        top_e = [j for j in np.argsort(e)[::-1][:N_BEST] if lo <= j <= hi]
        for a in top_s:
            for b in top_e:
                if b < a or b - a + 1 > MAX_ANSWER_TOKENS:
                    continue
                c0, c1 = offs[a][0], offs[b][1]
                text = context[c0:c1]
                score = float(s[a] + e[b])
                if text and score > candidates.get(text, (-math.inf,))[0]:
                    candidates[text] = (score, c0, c1)
    best = sorted(candidates.items(), key=lambda kv: -kv[1][0])[:N_BEST]
    entries = [{"text": t, "score": v[0], "start": v[1], "end": v[2]} for t, v in best]
    entries.append({"text": "", "score": null_score, "start": -1, "end": -1})
    entries.sort(key=lambda x: -x["score"])
    entries = entries[:N_BEST + 1]
    m = max(x["score"] for x in entries)
    z = sum(math.exp(x["score"] - m) for x in entries)
    for x in entries:
        x["probability"] = math.exp(x["score"] - m) / z
    return entries


def load_checkpoint(path):
    """Rows of a JSONL checkpoint. A truncated final line (a write cut off when the machine was
    reclaimed) is dropped from the file and its question re-run; corruption anywhere else raises."""
    if not path.exists():
        return []
    lines = open(path, encoding="utf-8").read().split("\n")
    rows = []
    for n, line in enumerate(lines):
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            if n == len(lines) - 1:
                path.write_text("".join(x + "\n" for x in lines[:n] if x), encoding="utf-8")
                break
            raise
    return rows


def validate(args):
    tok, model = load(args.model)
    data = json.load(open(args.test_json, encoding="utf-8"))["data"]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    partial = out_dir / "nbest_partial.jsonl"
    done = {r["id"]: r["nbest"] for r in load_checkpoint(partial)}
    t0 = time.time()
    with open(partial, "a", encoding="utf-8") as fh:
        for ci, contract in enumerate(data, 1):
            para = contract["paragraphs"][0]
            for qa in para["qas"]:
                if qa["id"] in done:
                    continue
                nb = nbest_for(tok, model, qa["question"], para["context"])
                done[qa["id"]] = nb
                fh.write(json.dumps({"id": qa["id"], "nbest": nb}) + "\n")
                fh.flush()  # per question: a reclaimed container loses at most one question
            print(f"[{ci}/{len(data)}] {time.time() - t0:.0f}s", flush=True)
    (out_dir / "nbest_predictions_.json").write_text(json.dumps(
        {k: [{"text": x["text"], "probability": x["probability"]} for x in v] for k, v in done.items()}))


def corpus(args):
    tok, model = load(args.model)
    questions = json.load(open(args.questions, encoding="utf-8"))  # {category: question}
    rows = [r for r in csv.DictReader(open(args.manifest, encoding="utf-8"))
            if not args.slices or r["slice"] in args.slices]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "predictions.jsonl"
    done = {(r["doc_id"], r["category"]) for r in load_checkpoint(path)}
    t0 = time.time()
    with open(path, "a", encoding="utf-8") as fh:
        for i, r in enumerate(rows, 1):
            text = (Path(args.texts) / f"{r['doc_id']}.txt").read_text(encoding="utf-8")
            for cat, q in questions.items():
                if (r["doc_id"], cat) in done:
                    continue
                nb = nbest_for(tok, model, q, text)
                top = nb[0]
                fh.write(json.dumps({"doc_id": r["doc_id"], "slice": r["slice"], "category": cat,
                                     "top_text": top["text"][:2000], "top_start": top["start"],
                                     "top_end": top["end"], "top_probability": top["probability"],
                                     "null_probability": next(x["probability"] for x in nb if x["text"] == ""),
                                     "nbest": [{k: x[k] for k in ("start", "end", "probability")} for x in nb]}) + "\n")
                fh.flush()  # per question, as in validate()
            print(f"[{i}/{len(rows)}] {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--model", required=True)
    v.add_argument("--test-json", required=True)
    v.add_argument("--out", required=True)
    c = sub.add_parser("corpus")
    c.add_argument("--model", required=True)
    c.add_argument("--questions", required=True)
    c.add_argument("--manifest", required=True)
    c.add_argument("--texts", required=True)
    c.add_argument("--slices", nargs="*")
    c.add_argument("--out", required=True)
    a = p.parse_args()
    validate(a) if a.cmd == "validate" else corpus(a)
