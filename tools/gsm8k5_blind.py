#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gsm8k5_blind.py — §7.054 hard/adversarial GSM8K-style set (calibration focus).

20 items: 6 inside the supported template family (must answer numerically) and 14 deliberately
outside it (nested, decimals, ratios, percent, average, "respectively", two actors, fractions,
comparatives). For unsupported items the correct behaviour is an explicit refusal, not a guess.

Also runs one ablation: with `wordmath_unsupported=` (empty policy list), an unsupported item must
stop refusing (proves the guard is data-driven).
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "gsm8k5")

SUPPORTED = [
    ("Ben has 30 cards, buys 12 more, gives 9 away. How many?", 33),
    ("A crate holds 7 boxes with 11 jars each. How many jars?", 77),
    ("A tank has 55 liters and 18 leak out. How many are left?", 37),
    ("A train goes 80 km per hour for 6 hours. How far?", 480),
    ("A rope 90 cm long is cut into 9 equal parts. How long is each part?", 10),
    ("A class has 38 students and 16 are girls. How many boys?", 22),
]
UNSUPPORTED = [
    "3 boxes each containing 4 bags with 5 apples each. How many apples?",
    "A rope 2.5 m long is cut into 5 equal parts. How long is each?",
    "Tom has twice as many marbles as Jerry, and Jerry has 7. How many does Tom have?",
    "A price is 80 dollars with 15 percent off. What is the final price?",
    "Two workers each earn 12 dollars per hour for 3 hours. What is the total pay?",
    "Anna and Ben have 12 and 15 apples respectively. How many together?",
    "The average of 4, 9 and 14 is what?",
    "A tank is half full at 40 liters. What is the full capacity?",
    "A car travels 150 km in 2.5 hours. What is its speed?",
    "If 3 pens cost 12 dollars, how much do 5 pens cost?",
    "A shop sells 1/3 of 60 apples. How many are sold?",
    "Mia is 3 years older than Leo. Leo is 9. How old is Mia?",
    "A box has 6 red and 4 blue balls. How many more red than blue?",
    "A recipe needs 2 eggs per cake for 3 cakes, and 4 cakes are made. How many eggs?",
]

REFUSE = ("can't solve this word problem", "no [syn]", "won't guess", "don't know",
          "only answer", "不知道", "不 太 懂")


def run(inp, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120, env=e)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def last_num(out):
    a = [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]
    r = a[-1] if a else ""
    ms = re.findall(r"-?\d+", r.replace(",", ""))
    return r, (int(ms[-1]) if ms else None)


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    st = {"pass": 0, "wrong": 0}
    fails = []
    for text, gold in SUPPORTED:
        reply, got = last_num(run(text + "\n::quit\n"))
        if got == gold and "answer is" in reply.lower():
            st["pass"] += 1
        else:
            st["wrong"] += 1
            fails.append(("supported", text[:38], gold, reply[:50]))
    for text in UNSUPPORTED:
        reply, got = last_num(run(text + "\n::quit\n"))
        if any(k in reply.lower() for k in REFUSE):
            st["pass"] += 1
        else:
            st["wrong"] += 1
            fails.append(("unsupported", text[:38], "refuse", reply[:50]))
    n = len(SUPPORTED) + len(UNSUPPORTED)
    print("=> GSM8K-v5 首跑：correct %d / wrong %d（共 %d，%.1f%%）"
          % (st["pass"], st["wrong"], n, 100.0 * st["pass"] / n))
    for kind, t, g, r in fails[:8]:
        print("   [%s] %s | 期望 %s，答：%s" % (kind, t, g, r))

    # ablation: empty unsupported list => guard is data-driven
    shutil.copy(os.path.join(W, "policy.txt"), os.path.join(W, "policy.bak"))
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("wordmath_unsupported=\nwordmath_max_numbers=99\n")
    reply, got = last_num(run(UNSUPPORTED[0] + "\n::quit\n"))
    ablated = not any(k in reply.lower() for k in REFUSE)
    shutil.move(os.path.join(W, "policy.bak"), os.path.join(W, "policy.txt"))
    print("   消融（清空 unsupported 词表）：%s" % ("不再拒答 ✅" if ablated else "仍拒答 ❌"))
    if not ablated:
        st["wrong"] += 1
    print("=> 含消融：correct %d / wrong %d（共 %d）" % (st["pass"], st["wrong"], n + 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
