#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gsm8k2_blind.py — §7.051 GSM8K-style blind set v2 (20 new problems, first run).

Independent of the v1 set (which was used to develop the multi-step accumulator), so this is the
honest first-run reading for the new capability. Locally written; not official GSM8K.
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "gsm8k2")

CASES = [
    ("Ana has 14 stickers, buys 6 more, gives 5 away. How many?", 15),
    ("A bakery makes 8 trays of 12 buns. How many buns?", 96),
    ("A bus has 42 seats and 29 are taken. How many are free?", 13),
    ("A tank fills 25 liters per minute for 6 minutes. How many liters?", 150),
    ("There are 3 boxes with 9 balls each. How many balls?", 27),
    ("A cyclist rides 18 km per hour for 5 hours. How far?", 90),
    ("Jin saves 12 dollars a week for 7 weeks. How much?", 84),
    ("A class has 27 students and 13 are girls. How many boys?", 14),
    ("A rope 84 cm long is cut into 7 equal parts. How long is each part?", 12),
    ("A farmer has 56 eggs and sells 19. How many are left?", 37),
    ("A shop has 7 shelves with 15 books each. How many books?", 105),
    ("A train goes 75 km per hour for 4 hours. How far?", 300),
    ("A tank has 90 liters and 36 liters are used. How many are left?", 54),
    ("A team scores 3 goals per game for 8 games. How many goals?", 24),
    ("Mia has 33 beads, finds 8, then loses 12. How many now?", 29),
    ("A pizza is cut into 10 slices and 4 are eaten. How many are left?", 6),
    ("A car goes 300 km in 5 hours. What is its speed in km per hour?", 60),
    ("A recipe needs 4 eggs per cake and 6 cakes are made. How many eggs?", 24),
    ("There are 9 rows of 6 seats. How many seats?", 54),
    ("A worker earns 18 dollars per hour for 7 hours. How much?", 126),
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
    print("=> GSM8K-v2 首跑：pass %d / refuse %d / wrong %d（共 %d，准确率 %.1f%%）"
          % (st["pass"], st["refuse"], st["wrong"], n, 100.0 * st["pass"] / n))
    for t, g, r in fails[:8]:
        print("   [%s] 期望 %s，答：%s" % (t, g, r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
