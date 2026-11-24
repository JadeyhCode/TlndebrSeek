#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""nospace_blind.py — §7.036 无空格中文长句首跑（10 题）

中文本来不靠空格分词；这组专门用**完全无空格**的连续句教/问，量真实能力。
判定：命中期望算 pass；明确拒答/不知道算 refuse；只有**自相矛盾地答错**算 wrong。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "nospace")

# (名字, 前置输入, 问题, 期望包含串, 是否允许多轮)
CASES = [
    ("无空格教-问", ["猫属于动物"], "猫属于动物吗", "对"),
    ("无空格-关系问", ["我教你，树懒有爪子"], "树懒有什么", "爪子"),
    ("无空格-新词", ["犰狳属于动物"], "犰狳属于动物吗", "对"),
    ("无空格-长句", ["我教你，貘属于奇蹄目并且喜欢水边"], "貘属于什么", "奇蹄目"),
    ("无空格-否定", ["猫不属于猫科"], "猫属于猫科吗", "不"),
    ("无空格-代词", ["我教你，袋鼠有袋子", "它有什么"], "袋鼠有什么", "袋子"),
    ("无空格-量词", ["牛有四条腿"], "牛有几条腿", "腿"),
    ("无空格-纠错", ["猫属于动物", "不对猫属于猫科"], "猫属于什么", "猫科"),
    ("无空格-追问", ["鸟会飞吗"], "那鱼呢", "鱼"),
    ("无空格-否定事实", ["我教你，企鹅不会飞"], "企鹅会飞吗", "不"),
]

REFUSE = ("不 知道", "不知道", "不 太 懂", "不太懂", "没 记 过", "没记过",
          "不 认识", "不认识", "不 确定", "不确定", "没 有 这 条", "没有这条")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def answer_of(out):
    a = [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]
    return a[-1] if a else ""


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
    for name, setup, q, want in CASES:
        out = run("\n".join(setup + [q, "::quit"]) + "\n")
        ans = answer_of(out)
        if want in ans:
            st["pass"] += 1
            print("  [PASS]   %-12s → %s" % (name, ans[:60]))
        elif any(k in ans for k in REFUSE):
            st["refuse"] += 1
            print("  [REFUSE] %-12s （期望含「%s」：%s）" % (name, want, ans[:60]))
        else:
            st["wrong"] += 1
            print("  [WRONG]  %-12s （期望含「%s」，答成：%s）" % (name, want, ans[:60]))
    n = len(CASES)
    print("=> 无空格中文首跑：pass %d / refuse %d / wrong %d（共 %d）"
          % (st["pass"], st["refuse"], st["wrong"], n))
    return 0 if st["wrong"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
