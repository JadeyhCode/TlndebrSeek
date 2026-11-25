#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bench.py — §7.049 kernel-native benchmark harness (F19/F20 baseline)

Runs a fixed set of existing blind tools and reports a **disclosed** scorecard:
category | pass | refuse | wrong | total | coverage(pass/total) | precision(pass/(pass+wrong)).

This is NOT MMLU/GSM8K: these are categories this kernel can actually measure.
Public scoring rule:
  - coverage  = pass / total            (how often it answers correctly)
  - precision = pass / (pass + wrong)   (when it commits, how often it is right; refuses excluded)
  - composite = mean(coverage over categories)
  - target    = majority (>= half) of categories with coverage >= 60%

Usage: python3 tools/bench.py [--quick] [--json]
--quick skips slow categories (studyeval).
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CATS = [
    ("dialogue", ["python3", "tools/dialogue_blind.py"],
     r"=> pass (\d+) / refuse (\d+) / wrong (\d+)"),
    ("longtext", ["python3", "tools/longtext_blind.py"],
     r"=> pass (\d+) / refuse (\d+) / wrong (\d+)"),
    ("nospace", ["python3", "tools/nospace_blind.py"],
     r"=> 无空格中文首跑：pass (\d+) / refuse (\d+) / wrong (\d+)"),
    ("symgen", ["python3", "tools/symgen_blind.py"],
     r"=> 符号组合泛化首跑：pass (\d+) / wrong (\d+)"),
    ("chain", ["python3", "tools/chain_blind.py"],
     r"=> 多步求解首跑：(\d+)/(\d+)"),
    ("crosslingual", ["python3", "tools/crosslingual_blind.py"],
     r"=> 中英互译迁移首跑：(\d+)/(\d+)"),
    ("english", ["python3", "tools/english_blind.py"],
     r"=> 英文首跑：pass (\d+) / refuse (\d+) / wrong (\d+)"),
    ("longdoc", ["python3", "tools/longdoc_blind.py"],
     r"=> 长文档首跑：pass (\d+) / refuse (\d+) / wrong (\d+)"),
    ("gap", ["python3", "tools/gap_blind.py"],
     r"=> 缺口检测首跑：(\d+)/(\d+)"),
    ("study", ["python3", "tools/study_eval.py"],
     r"=> 自学首跑：出题 (\d+)｜自解 (\d+)"),
]


def run_cat(name, cmd, pat):
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1200)
    out = p.stdout + p.stderr
    m = re.search(pat, out)
    if not m:
        return dict(name=name, error=True, detail=out.strip().splitlines()[-1][:80] if out.strip() else "no output")
    g = [int(x) for x in m.groups()]
    if name in ("dialogue", "longtext", "nospace", "english", "longdoc"):
        ps, rf, wr = g[0], g[1], g[2]
    elif name in ("symgen",):
        ps, wr = g[0], g[1]
        rf = 0
    elif name in ("chain", "crosslingual", "gap"):
        ps, tot = g[0], g[1]
        wr = tot - ps
        rf = 0
    else:  # study: g[0]=posed(total), g[1]=solved(pass); wrong not reported per-category
        tot, ps = g[0], g[1]
        wr = 0
        rf = tot - ps
    tot = ps + rf + wr
    cov = ps / tot if tot else 0.0
    prec = ps / (ps + wr) if (ps + wr) else 0.0
    return dict(name=name, pass_=ps, refuse=rf, wrong=wr, total=tot, coverage=cov, precision=prec)


def main():
    quick = "--quick" in sys.argv
    as_json = "--json" in sys.argv
    rows = []
    for name, argv, pat in CATS:
        if quick and name == "study":
            continue
        rows.append(run_cat(name, argv, pat))
    comps = [r["coverage"] for r in rows if not r.get("error")]
    maj = sum(1 for r in rows if not r.get("error") and r["coverage"] >= 0.6)
    n = len(rows)
    if as_json:
        print(json.dumps(dict(rows=rows, composite=(sum(comps) / len(comps) if comps else 0.0),
                              majority_ge60=(maj, n)), ensure_ascii=False, indent=2))
        return 0
    print("%-13s %5s %6s %5s %5s %8s %9s" % ("category", "pass", "refuse", "wrong", "total", "coverage", "precision"))
    for r in rows:
        if r.get("error"):
            print("%-13s ERROR  %s" % (r["name"], r["detail"]))
            continue
        print("%-13s %5d %6d %5d %5d %7.1f%% %8.1f%%" % (
            r["name"], r["pass_"], r["refuse"], r["wrong"], r["total"],
            100 * r["coverage"], 100 * r["precision"]))
    if comps:
        print("\ncomposite coverage = %.1f%% (mean over %d categories)" % (100 * sum(comps) / len(comps), len(comps)))
        print("majority >=60%% coverage: %d/%d categories => %s" % (maj, n, "PASS" if maj * 2 >= n else "FAIL"))
    errs = sum(1 for r in rows if r.get("error"))
    return 0 if errs == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
