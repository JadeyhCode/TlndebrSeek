#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§6.972 语法错/新词鲁棒性盲测（10 题首跑）：漏词、错序、无空格、新词、错别字。
判分：期望串出现=pass；明确拒绝（不认识/不知道/没记过）=refuse；其它=wrong。
"""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip"); MODEL = os.path.join(ROOT, "model.bin")
W = os.path.join(ROOT, "_t", "robustblind")
TASKS = [
    ("漏关系词", ["貘奇蹄目吗"], "奇蹄目", "refuse"),
    ("漏宾语", ["猫 属于 什么"], "动物", "pass"),
    ("无空格问句", ["猫属于什么"], "动物", "pass"),
    ("错序", ["什么 属于 猫"], "动物", "refuse"),
    ("新词问", ["犰狳 属于 什么"], "不认识", "pass"),
    ("新词教后问", ["我教你，犰狳 属于 贫齿目", "犰狳 属于 什么"], "贫齿目", "pass"),
    ("错别字", ["猫 属鱼 动物 吗"], "不", "refuse"),
    ("省略主语", ["猫 属于 动物", "它 属于 什么"], "动物", "pass"),
    ("否定漏字", ["鲸鱼 不是 鱼"], "不", "pass"),
    ("语序倒装", ["属于 动物 的 有 猫 吗"], "有", "refuse"),
]
def run(lines):
    inp = "::notepad off\n::char off\n" + "\n".join(lines) + "\n::quit\n"
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp, text=True,
                       encoding="utf-8", errors="replace", capture_output=True, cwd=W, timeout=120)
    return [l[l.find("AI > ") + 5:] for l in p.stdout.splitlines() if "AI > " in l]
def main():
    shutil.rmtree(W, ignore_errors=True); os.makedirs(W)
    shutil.copy(MODEL, os.path.join(W, "model.bin")); shutil.copy(BIN, os.path.join(W, "build_aip"))
    for f in ("patterns.txt", "frames.txt", "relations.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src): shutil.copy(src, os.path.join(W, f))
    res = {"pass": 0, "refuse": 0, "wrong": 0}
    for name, lines, want, kind in TASKS:
        rs = run(lines)
        got = rs[-1] if rs else ""
        ok = want in got
        if ok: res["pass"] += 1; print("  [PASS] %-10s => %r" % (name, got.strip()[:60]))
        else:
            ref = any(w in got for w in ("不 认识", "不 知道", "没 记 过", "不 太 懂", "不 确定"))
            if ref: res["refuse"] += 1; print("  [REFUSE] %-10s => %r（要 %r）" % (name, got.strip()[:60], want))
            else: res["wrong"] += 1; print("  [WRONG] %-10s => %r（要 %r）" % (name, got.strip()[:60], want))
    print("=> pass %d / refuse %d / wrong %d（共 %d）" % (res["pass"], res["refuse"], res["wrong"], len(TASKS)))
    return 0
if __name__ == "__main__":
    sys.exit(main())
