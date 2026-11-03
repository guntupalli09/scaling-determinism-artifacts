"""Manuscript figures 1 and 2: the Day 3 figures (plot_figures_day3.py) re-drawn from the same data, without the
draft-stage in-figure titles (captions are in the manuscript). Writes manuscript_final/figures/."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

F = Path(__file__).resolve().parents[1]
A = F / "runs" / "analysis"
OUT = F / "manuscript_final" / "figures"
OUT.mkdir(parents=True, exist_ok=True)
P6 = sorted((F / "runs" / "phase6").glob("*/performance.json"))[-1]
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})
CK = ["v1.0.3-iccs", "v2.0.0", "v2.1.0", "v3.0.0", "v4.0.0", "v5.0.0", "v6.0.0", "v7.0.0", "v7.1.0", "v7.2.0"]
rules = {r["label"]: r["rule_count"] for r in json.load(open(F / "releases/manifest_v2.json"))}
perf = json.load(open(P6))
row = {(r["system"], r["dataset"], r["subset"]): r for r in perf}
xt = [f"{c.replace('-iccs', ' (ICCS)')}\n{rules[c]} rules" for c in CK]
x = list(range(len(CK)))

# Fig 1: CUAD fixed-denominator recall & precision with Wilson 95% CIs
fig, ax = plt.subplots(figsize=(9, 4.4))
for key, color, marker, name in (("recall", BLUE, "o", "Recall (coverage)"), ("precision", ORANGE, "s", "Precision")):
    ys = [row[(c, "cuad", "fixed_denominator")][key] for c in CK]
    lo = [y - row[(c, "cuad", "fixed_denominator")][key + "_ci"][0] for c, y in zip(CK, ys)]
    hi = [row[(c, "cuad", "fixed_denominator")][key + "_ci"][1] - y for c, y in zip(CK, ys)]
    ax.errorbar(x, ys, yerr=[lo, hi], color=color, lw=2, marker=marker, ms=7, capsize=3, elinewidth=1,
                markeredgecolor=SURFACE, markeredgewidth=1.5, label=name)
    ax.text(x[-1] + 0.2, ys[-1], f"{name.split(' ')[0]} {ys[-1]:.2f}", va="center", color=INK)
ax.set_xticks(x, xt, fontsize=7.5)
ax.set_ylim(0, 1)
ax.set_xlim(-0.4, len(x) + 0.9)
ax.yaxis.grid(True, color=GRID)
ax.set_ylabel("CUAD test split (2,142 fixed units)")
ax.legend(frameon=False, loc="upper left")
fig.tight_layout()
fig.savefig(OUT / "Figure_1.png", dpi=300)

# Fig 3: ContractNLI per-hypothesis recall by release (masked regression)
units = {c: list(csv.DictReader(open(A / c / "units_contractnli.csv"))) for c in CK}
hyps = [("nda-3", "nda-3 verbal info (broad scope)", BLUE, "o"), ("nda-18", "nda-18 no solicitation", ORANGE, "s"),
        ("nda-16", "nda-16 return/destroy", AQUA, "^"), ("nda-19", "nda-19 survival", YELLOW, "D"),
        ("nda-12", "nda-12 no indep. development", MAGENTA, "v")]
fig, ax = plt.subplots(figsize=(9, 5.0))
for h, name, color, marker in hyps:
    ys = []
    for c in CK:
        u = [r for r in units[c] if r["category"] == h]
        g = sum(r["gold"] == "True" for r in u)
        ys.append(sum(r["gold"] == "True" and r["engine"] == "True" for r in u) / g if g else 0)
    ax.plot(x, ys, color=color, lw=2, marker=marker, ms=7, markeredgecolor=SURFACE, markeredgewidth=1.5, label=name)
    dy = {"nda-19": 0.035, "nda-12": -0.005}.get(h, 0)
    ax.text(x[-1] + 0.2, ys[-1] + dy, name.split(" ")[0], va="center", color=INK, fontsize=8.5)
ax.axvline(5, color=MUTED, lw=1, ls=":")
ax.text(6.1, 0.44, "v5.0 (dotted): L_BROADDEF_01 bounded\n→ nda-3 −19 TP, not recovered", fontsize=8, color=INK, va="top")
ax.axvline(3, color=MUTED, lw=1, ls=":")
ax.text(0.0, 0.50, "v3.0 (dotted): commit\n13532073 (chunking)\n→ nda-3 −9 TP", fontsize=8, color=INK, va="top")
ax.set_xticks(x, xt, fontsize=7.5)
ax.set_ylim(0, 1.0)
ax.set_xlim(-0.4, len(x) + 0.6)
ax.yaxis.grid(True, color=GRID)
ax.set_ylabel("Recall on ContractNLI test (123 NDAs)")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.17), fontsize=8, ncol=5)
fig.tight_layout()
fig.savefig(OUT / "Figure_2.png", dpi=300)

# Figure 3: runtime scaling, (a) rule count across releases, (b) document length at v7.2.0 (from plot_figures.py)
sc = json.load(open(A / "scaling.json"))
pts = sc["rule_count_scaling"]["points"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9, 3.8))
a1.plot([p["rule_count"] for p in pts], [p["median_seconds_per_doc"] for p in pts], color=BLUE, lw=2, marker="o", ms=8,
        markeredgecolor=SURFACE, markeredgewidth=2)
a1.set_xscale("log"); a1.set_yscale("log")
a1.set_xlabel("Rules in release"); a1.set_ylabel("Median seconds / document")
a1.set_title("(a)", loc="left", fontsize=10)
a1.grid(True, color=GRID, which="major")
res = [json.loads(l) for l in open(F / "runs" / "v7.2.0" / "results.jsonl")]
chars = {r["doc_id"]: int(r["chars"]) for r in csv.DictReader(open(F / "corpus" / "manifest.csv"))}
a2.scatter([chars[r["doc_id"]] for r in res], [r["seconds_median"] for r in res], s=10, color=BLUE, alpha=0.5, linewidths=0)
a2.set_xscale("log"); a2.set_yscale("log")
a2.set_xlabel("Document length (characters)"); a2.set_ylabel("Seconds / document (v7.2.0)")
a2.set_title("(b)", loc="left", fontsize=10)
a2.grid(True, color=GRID, which="major")
fig.tight_layout()
fig.savefig(OUT / "Figure_3.png", dpi=300)
print(OUT)
