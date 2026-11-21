#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§6.983 错字/错关系词盲测（10 题首跑）：关系词写错、拆开、少字；期望仍能答对。
判分：期望串出现=pass；明确拒绝=refuse；其它=wrong。
"""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip"); MODEL = os.path.join(ROOT, "model.bin")
W = os.path.join(ROOT, "_t", "typoblind")
CASES = [
    ("猫 属鱼 动物 吗", "对"),
    ("猫 属干 动物 吗", "对"),
    ("猫 属与 动物 吗", "对"),
    ("猫 属 于 动物 吗", "对"),
    ("猫 属鱼 什么", "动物"),
    ("猫 属干 什么", "动物"),
    ("鸟 有 翅膀 吗", "对"),
    ("猫 吃 鱼 吗", "对"),
    ("猫 属于 动物 吗", "对"),
    ("猫 对 动物 吗", "对"),
]
def run(q):
    inp = "::notepad off\n::char off\n" + q + "\n::quit\n"
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp, text=True, encoding="utf-8",
                       errors="replace", capture_output=True, cwd=W, timeout=120)
    rs = [l[l.find("AI > ") + 5:] for l in p.stdout.splitlines() if "AI > " in l]
    return rs[-1] if rs else ""
def main():
    shutil.rmtree(W, ignore_errors=True); os.makedirs(W)
    shutil.copy(MODEL, os.path.join(W, "model.bin")); shutil.copy(BIN, os.path.join(W, "build_aip"))
    for f in ("patterns.txt", "frames.txt", "relations.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src): shutil.copy(src, os.path.join(W, f))
    res = {"pass": 0, "refuse": 0, "wrong": 0}
    for q, want in CASES:
        got = run(q)
        ref = any(w in got for w in ("不 认识", "不 知道", "没 记 过", "不 太 懂", "不 确定", "不 太 确定"))
        if want in got and not ref: res["pass"] += 1; print("  [PASS] %-16s => %r" % (q, got.strip()[:50]))
        elif ref: res["refuse"] += 1; print("  [REFUSE] %-13s => %r" % (q, got.strip()[:50]))
        else: res["wrong"] += 1; print("  [WRONG] %-14s => %r（要 %r）" % (q, got.strip()[:50], want))
    print("=> pass %d / refuse %d / wrong %d（共 %d）" % (res["pass"], res["refuse"], res["wrong"], len(CASES)))
    return 1 if res["wrong"] > 0 else 0
if __name__ == "__main__":
    sys.exit(main())
