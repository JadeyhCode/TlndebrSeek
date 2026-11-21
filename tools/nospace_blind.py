#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§6.977 无空格中文盲测（16 题首跑）：中文不加空格时的指令/问句/纠错/待证/亲属。
判分：期望串出现=pass；明确拒绝=refuse；其它=wrong。
"""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip"); MODEL = os.path.join(ROOT, "model.bin")
W = os.path.join(ROOT, "_t", "nospace")
TASKS = [
    ("猫属于什么", "动物"),
    ("鲸鱼属于动物吗", "对"),
    ("三只猫属于动物吗", "对"),
    ("猫是动物的一种吗", "对"),
    ("猫喜欢吃鱼吗", "对"),
    ("猫有尾巴吗", "对"),
    ("猫会飞吗", "不"),
    ("猫不是鸟吗", "不"),
    ("中国在亚洲吗", "对"),
    ("犰狳属于什么", "不 认识"),
    ("听说猫会飞", "待 证"),
    ("请记住树懒吃叶子", "记下"),
    ("我教你貘属于奇蹄目", "记下"),
    ("小明是我的表弟", "表弟"),
    ("猫吃鱼吗", "对"),
    ("什么属于动物", "猫"),
]
TWO = [("我教你貘属于奇蹄目", "貘属于什么", "奇蹄目"),
       ("请记住树懒吃叶子", "树懒吃什么", "叶子")]
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
    for text, want in TASKS:
        rs = run([text]); got = rs[-1] if rs else ""
        ref = any(w in got for w in ("不 认识", "不 知道", "没 记 过", "不 太 懂", "不 确定", "不 太 确定"))
        if want in got and not ref: res["pass"] += 1; print("  [PASS] %-14s => %r" % (text, got.strip()[:50]))
        elif ref: res["refuse"] += 1; print("  [REFUSE] %-11s => %r" % (text, got.strip()[:50]))
        else: res["wrong"] += 1; print("  [WRONG] %-12s => %r（要 %r）" % (text, got.strip()[:50], want))
    for t1, t2, want in TWO:
        rs = run([t1, t2]); got = rs[-1] if rs else ""
        ref = any(w in got for w in ("不 认识", "不 知道", "没 记 过", "不 太 懂", "不 确定"))
        if want in got and not ref: res["pass"] += 1; print("  [PASS] %-14s + %-10s => %r" % (t1, t2, got.strip()[:40]))
        elif ref: res["refuse"] += 1; print("  [REFUSE] %-11s + %-10s => %r" % (t1, t2, got.strip()[:40]))
        else: res["wrong"] += 1; print("  [WRONG] %-12s + %-10s => %r（要 %r）" % (t1, t2, got.strip()[:40], want))
    print("=> pass %d / refuse %d / wrong %d（共 %d）" % (res["pass"], res["refuse"], res["wrong"], len(TASKS) + len(TWO)))
    return 0
if __name__ == "__main__":
    sys.exit(main())
