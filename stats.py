"""Dependency-free statistics for the follow-up study (exact McNemar, Wilson and bootstrap CIs)."""
import math
import random


def wilson(k: int, n: int, z: float = 1.959964) -> dict:
    if n == 0:
        return {"p": None, "lo": None, "hi": None, "k": k, "n": n}
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return {"p": p, "lo": max(0.0, c - h), "hi": min(1.0, c + h), "k": k, "n": n}


def mcnemar_exact(a_correct: list, b_correct: list) -> dict:
    """Exact two-sided McNemar test on paired correctness vectors."""
    assert len(a_correct) == len(b_correct)
    b = sum(1 for x, y in zip(a_correct, b_correct) if x and not y)  # only A correct
    c = sum(1 for x, y in zip(a_correct, b_correct) if y and not x)  # only B correct
    n = b + c
    if n == 0:
        p = 1.0
    else:
        tail = sum(math.comb(n, i) for i in range(0, min(b, c) + 1)) / 2 ** n
        p = min(1.0, 2 * tail)
    return {"only_a_correct": b, "only_b_correct": c, "discordant": n, "p_value": p, "n_pairs": len(a_correct)}


def prf(tp: int, fp: int, fn: int) -> dict:
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    f1 = 2 * prec * rec / (prec + rec) if prec and rec else (0.0 if prec is not None and rec is not None else None)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec, "f1": f1,
            "precision_ci": wilson(tp, tp + fp), "recall_ci": wilson(tp, tp + fn)}


def bootstrap_f1_ci(units: list, iters: int = 2000, seed: int = 20261016) -> dict:
    """units: list of (gold: bool, pred: bool), resampled by document groups upstream if needed."""
    rng = random.Random(seed)
    vals = []
    for _ in range(iters):
        s = [units[rng.randrange(len(units))] for _ in units]
        tp = sum(g and p for g, p in s)
        fp = sum((not g) and p for g, p in s)
        fn = sum(g and not p for g, p in s)
        f = prf(tp, fp, fn)["f1"]
        if f is not None:
            vals.append(f)
    vals.sort()
    if not vals:
        return {"lo": None, "hi": None}
    return {"lo": vals[int(0.025 * len(vals))], "hi": vals[int(0.975 * len(vals)) - 1]}
