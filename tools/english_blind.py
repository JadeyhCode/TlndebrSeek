#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""english_blind.py — §7.032 英文 NLU 最小闭环首跑（10 题）

考的是“现在英文能到哪”：是否类问答 pass、明确不支持时 refuse 都算对，
只有**自信答错**（预期 no 却 yes 等）算 wrong。wrong>0 才红。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "english")

# (名字, 前置教学语句, 问题, 预期)
CASES = [
    ("教事实-是否", ["cat is an animal"], "is cat an animal?", "yes"),
    ("能力-是否", ["bird can fly"], "can a bird fly?", "yes"),
    ("否定", ["cat is not a fish"], "is a cat a fish?", "no"),
    ("冠词", ["a cat is an animal"], "is a cat an animal?", "yes"),
    ("开放问句-谁", ["cat is an animal"], "who is an animal?", "refuse"),
    ("开放问句-什么", ["cat is an animal"], "what is a cat?", "refuse"),
    ("代词多轮", ["cat is an animal"], "is it an animal?", "refuse"),
    ("未知事实", ["cat is an animal"], "is a dog a reptile?", "refuse"),
    ("倒装否定", ["cat is an animal"], "is an animal a cat?", "refuse"),
    ("教学-能力", ["cat can fly", "yes"], "can a cat fly?", "yes"),
    ("长句疑问", ["cat is an animal"], "is the cat that I saw an animal?", "refuse"),
]

REFUSE = ("don't know", "do not know", "sorry", "only answer", "not in my graph",
          "不知道", "不 知道", "没记过")


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def classify(ans):
    a = ans.lower()
    if any(k in a for k in REFUSE):
        return "refuse"
    if re.search(r"(^|\b)yes\b", a):
        return "yes"
    if re.search(r"(^|\b)no\b", a):
        return "no"
    return "refuse"


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    stats = {"pass": 0, "refuse": 0, "wrong": 0}
    for name, setup, q, want in CASES:
        inp = "\n".join(setup + [q, "::quit"]) + "\n"
        p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                           capture_output=True, cwd=W, timeout=120)
        out = (p.stdout + p.stderr).decode("utf-8", "replace")
        answers = [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]
        ans = clean(answers[-1]) if answers else ""
        got = classify(ans)
        if got == want:
            stats["pass"] += 1
            print("  [PASS]   %-12s → %s" % (name, got))
        elif got == "refuse":
            stats["refuse"] += 1
            print("  [REFUSE] %-12s （该答 %s，实际拒答：%s）" % (name, want, ans[:50]))
        else:
            stats["wrong"] += 1
            print("  [WRONG]  %-12s （该 %s，答成 %s：%s）" % (name, want, got, ans[:50]))
    n = len(CASES)
    print("=> 英文首跑：pass %d / refuse %d / wrong %d（共 %d）"
          % (stats["pass"], stats["refuse"], stats["wrong"], n))
    return 0 if stats["wrong"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
