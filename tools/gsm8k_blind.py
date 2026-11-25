#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gsm8k_blind.py — §7.050 external-style benchmark adapter: 20 GSM8K-style word problems.

These are human-written grade-school math word problems in the GSM8K style (not the official
test split; a locally written 20-item set to avoid contamination). The kernel gets the raw
English problem and must answer with a number.

Score: pass = numeric answer matches; refuse = explicit refusal/uncertainty; wrong = other.
This is a benchmark reading, not a gate criterion (exit 0 unless it crashes).
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "gsm8k")

CASES = [
    ("A shop had 23 apples and sold 15. How many are left?", 8),
    ("Tom has 12 marbles, buys 9 more, then loses 4. How many now?", 17),
    ("A box holds 6 packs, each pack has 8 pencils. How many pencils?", 48),
    ("There are 5 rows of 7 chairs. How many chairs?", 35),
    ("A train travels 60 km per hour for 3 hours. How far?", 180),
    ("A pizza is cut into 8 slices and 3 are eaten. How many are left?", 5),
    ("Lisa saves 15 dollars a week for 4 weeks. How much does she save?", 60),
    ("A book has 120 pages; 45 have been read. How many are left?", 75),
    ("12 cookies are shared equally among 4 children. How many each?", 3),
    ("A farmer has 34 sheep and buys 18 more. How many now?", 52),
    ("A tank holds 50 liters and 17 leak out. How many liters are left?", 33),
    ("Each box has 9 eggs and there are 4 boxes. How many eggs?", 36),
    ("A class has 18 boys and 21 girls. How many students in total?", 39),
    ("A car travels 240 km in 4 hours. What is its speed in km per hour?", 60),
    ("A rope 100 cm long is cut into 4 equal pieces. How long is each piece?", 25),
    ("There are 6 boxes and each box weighs 14 kg. What is the total weight?", 84),
    ("A store sells 8 toys at 7 dollars each. How much money is that?", 56),
    ("Sam reads 12 pages a day for 5 days. How many pages does he read?", 60),
    ("A recipe needs 3 eggs per cake and 7 cakes are made. How many eggs?", 21),
    ("A farmer has 40 apples, sells 12, then picks 9 more. How many now?", 37),
]

REFUSE = ("don't know", "do not know", "sorry", "only answer", "no [syn]", "won't guess",
          "don't have", "不知道", "不 知道", "不 太 懂", "不确定")


def num_of(s):
    ms = re.findall(r"-?\d+", s.replace(",", ""))
    return int(ms[-1]) if ms else None


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))

    st = {"pass": 0, "refuse": 0, "wrong": 0}
    fails = []
    for text, gold in CASES:
        p = subprocess.run([BIN, "--model", "model.bin"], input=(text + "\n::quit\n").encode(),
                           capture_output=True, cwd=W, timeout=120)
        out = (p.stdout + p.stderr).decode("utf-8", "replace")
        ans = [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]
        reply = ans[-1] if ans else ""
        got = num_of(reply)
        if got == gold and ("answer is" in reply.lower() or reply.strip() == str(gold)):
            st["pass"] += 1
        elif any(k in reply.lower() for k in REFUSE) or not reply.strip():
            st["refuse"] += 1
            fails.append((text[:40], gold, reply[:50]))
        else:
            st["wrong"] += 1
            fails.append((text[:40], gold, reply[:50]))
    n = len(CASES)
    print("=> GSM8K-style 首跑：pass %d / refuse %d / wrong %d（共 %d，准确率 %.1f%%）"
          % (st["pass"], st["refuse"], st["wrong"], n, 100.0 * st["pass"] / n))
    for t, g, r in fails[:8]:
        print("   [%s] 期望 %s，答：%s" % (t, g, r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
