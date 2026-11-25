#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gsm8k3_blind.py — §7.052 GSM8K-style blind set v3 (20 new problems, honest first run).

v1/v2 were used while developing the accumulator/clause parser, so this fresh set measures the
clause-based version for the first time. Locally written; not official GSM8K.
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "gsm8k3")

CASES = [
    ("Ben has 21 cards, buys 7 more, gives 4 away. How many?", 24),
    ("A crate holds 6 boxes with 12 jars each. How many jars?", 72),
    ("A pool has 80 liters and 25 evaporate. How many are left?", 55),
    ("A printer prints 15 pages per minute for 8 minutes. How many pages?", 120),
    ("There are 4 rows of 9 trees. How many trees?", 36),
    ("A runner goes 12 km per hour for 3 hours. How far?", 36),
    ("Nia saves 9 dollars a week for 6 weeks. How much?", 54),
    ("A class has 31 students and 17 are boys. How many girls?", 14),
    ("A ribbon 96 cm long is cut into 8 equal parts. How long is each part?", 12),
    ("A farmer has 63 eggs and sells 28. How many are left?", 35),
    ("A store has 6 shelves with 14 boxes each. How many boxes?", 84),
    ("A train goes 90 km per hour for 5 hours. How far?", 450),
    ("A tank has 75 liters and 34 are used. How many are left?", 41),
    ("A team scores 4 goals per game for 9 games. How many goals?", 36),
    ("Leo has 45 stamps, finds 9, then loses 16. How many now?", 38),
    ("A pizza is cut into 12 slices and 5 are eaten. How many are left?", 7),
    ("A car goes 350 km in 7 hours. What is its speed in km per hour?", 50),
    ("A recipe needs 5 eggs per cake and 4 cakes are made. How many eggs?", 20),
    ("There are 8 rows of 7 seats. How many seats?", 56),
    ("A worker earns 22 dollars per hour for 6 hours. How much?", 132),
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
        if got == gold and "answer is" in reply.lower():
            st["pass"] += 1
        elif any(k in reply.lower() for k in REFUSE) or not reply.strip():
            st["refuse"] += 1
            fails.append((text[:40], gold, reply[:50]))
        else:
            st["wrong"] += 1
            fails.append((text[:40], gold, reply[:50]))
    n = len(CASES)
    print("=> GSM8K-v3 首跑：pass %d / refuse %d / wrong %d（共 %d，准确率 %.1f%%）"
          % (st["pass"], st["refuse"], st["wrong"], n, 100.0 * st["pass"] / n))
    for t, g, r in fails[:8]:
        print("   [%s] 期望 %s，答：%s" % (t, g, r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
