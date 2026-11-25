#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gsm8k4_blind.py — §7.053 GSM8K-style blind set v4 (20 new problems, honest first run).

Measures the cut-into/eaten priority fix and semantic inversion (boys<->girls, free<->taken).
Locally written; not official GSM8K.
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "gsm8k4")

CASES = [
    ("A pizza is cut into 16 slices and 6 are eaten. How many are left?", 10),
    ("A class has 29 students and 12 are girls. How many boys?", 17),
    ("A box has 5 packs with 8 pens each. How many pens?", 40),
    ("A tank has 64 liters and 19 leak out. How many are left?", 45),
    ("A bus has 36 seats and 14 are free. How many are taken?", 22),
    ("A printer prints 21 pages per minute for 4 minutes. How many pages?", 84),
    ("A team scores 2 goals per game for 11 games. How many goals?", 22),
    ("A rope 72 cm long is cut into 6 equal parts. How long is each part?", 12),
    ("A farmer has 47 apples, sells 18, picks 6 more. How many now?", 35),
    ("A shop has 9 shelves with 13 books each. How many books?", 117),
    ("A car goes 280 km in 4 hours. What is its speed in km per hour?", 70),
    ("A recipe needs 6 eggs per cake and 5 cakes are made. How many eggs?", 30),
    ("There are 7 rows of 8 chairs. How many chairs?", 56),
    ("A worker earns 17 dollars per hour for 9 hours. How much?", 153),
    ("A pool has 95 liters and 28 evaporate. How many are left?", 67),
    ("Nia has 26 stickers, buys 9, gives 7 away. How many now?", 28),
    ("A train goes 120 km per hour for 3 hours. How far?", 360),
    ("A pizza is cut into 9 slices and 4 are eaten. How many are left?", 5),
    ("A class has 34 students and 15 are boys. How many girls?", 19),
    ("A box holds 4 trays with 11 cookies each. How many cookies?", 44),
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
    print("=> GSM8K-v4 首跑：pass %d / refuse %d / wrong %d（共 %d，准确率 %.1f%%）"
          % (st["pass"], st["refuse"], st["wrong"], n, 100.0 * st["pass"] / n))
    for t, g, r in fails[:8]:
        print("   [%s] 期望 %s，答：%s" % (t, g, r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
