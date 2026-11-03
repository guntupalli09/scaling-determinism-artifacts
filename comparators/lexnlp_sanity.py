"""
LexNLP extractor sanity validation (runs in the LexNLP venv). An extractor may be scored
only if it passes every positive AND negative synthetic example here.

    python lexnlp_sanity.py --out ../runs/comparators/lexnlp_sanity/<stamp>
"""
import argparse
import json
import locale
import platform
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

from lexnlp.extract.en import amounts, dates, durations, money  # noqa: E402

CASES = {
    "dates": [("This Agreement is dated as of March 1, 2020.", True), ("The parties agree as follows.", False),
              ("Effective Date: 2019-07-15", True)],
    "durations": [("This term shall continue for 3 years.", True), ("Notice must be given ninety (90) days in advance.", True),
                  ("The Supplier shall deliver the goods.", False)],
    "money": [("The fee is $100.00 per month.", True), ("Liability shall not exceed USD 1,000,000.", True),
              ("Each party shall bear its own costs.", False)],
    "amounts": [("a total of 25 units", True), ("three hundred shares", True), ("no numbers here", False)],
}
FN = {"dates": lambda s: list(dates.get_dates(s)), "durations": lambda s: list(durations.get_durations(s)),
      "money": lambda s: list(money.get_money(s)), "amounts": lambda s: list(amounts.get_amounts(s))}


def main(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    report = {"python": sys.version, "platform": platform.platform(), "locale_en_US_available": None, "extractors": {}}
    try:
        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
        locale.setlocale(locale.LC_ALL, "")
        report["locale_en_US_available"] = True
    except locale.Error as e:
        report["locale_en_US_available"] = f"no: {e}"
    for name, cases in CASES.items():
        rows = []
        for text, expect in cases:
            try:
                got = FN[name](text)
                err = None
            except Exception as e:
                got, err = [], f"{type(e).__name__}: {e}"
            rows.append({"text": text, "expect_entity": expect, "got": [str(g) for g in got], "error": err,
                         "pass": (len(got) > 0) == expect and err is None})
        report["extractors"][name] = {"status": "PASS" if all(r["pass"] for r in rows) else "FAIL", "cases": rows}
    (out / "sanity.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v["status"] for k, v in report["extractors"].items()}), report["locale_en_US_available"])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    main(p.parse_args().out)
