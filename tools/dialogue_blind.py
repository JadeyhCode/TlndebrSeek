#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§6.981 多轮对话盲测（12 题首跑）：指代/追问/纠错/复述/来源。
每项 = 若干轮输入 + 最后一轮的期望串。判分：期望串=pass；明确拒绝=refuse；其它=wrong。
"""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip"); MODEL = os.path.join(ROOT, "model.bin")
W = os.path.join(ROOT, "_t", "dialblind")
CASES = [
    ("它-属于", ["我教你，貘 属于 奇蹄目", "它 属于 什么"], "奇蹄目"),
    ("它-吃", ["我教你，树懒 吃 叶子", "它 吃 什么"], "叶子"),
    ("那X呢-已知", ["猫 属于 动物", "那 狗 呢"], "对"),
    ("这个-指代", ["我教你，貘 属于 奇蹄目", "这个 属于 什么"], "奇蹄目"),
    ("纠错", ["我教你，貘 属于 偶蹄目", "不对，貘 属于 奇蹄目", "貘 属于 什么"], "奇蹄目"),
    ("追问谁", ["我教你，貘 属于 奇蹄目", "谁 属于 奇蹄目"], "貘"),
    ("复述上一句", ["我教你，貘 属于 奇蹄目", "刚才 说 的 是 什么"], "貘"),
    ("再说一遍", ["我教你，树懒 吃 叶子", "再说 一遍"], "树懒"),
    ("它-会", ["我教你，企鹅 会 游泳", "它 会 什么"], "游泳"),
    ("那-无知识", ["我教你，猫 吃 鱼", "那 狗 呢"], "不 知道"),
    ("它-有", ["我教你，象 有 长鼻子", "它 有 什么"], "长鼻子"),
    ("引述确认", ["我教你，貘 属于 奇蹄目", "你 说 貘 属于 什么"], "奇蹄目"),
]
def run(lines):
    inp = "::notepad off\n::char off\n" + "\n".join(lines) + "\n::quit\n"
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp, text=True, encoding="utf-8",
                       errors="replace", capture_output=True, cwd=W, timeout=180)
    return [l[l.find("AI > ") + 5:] for l in p.stdout.splitlines() if "AI > " in l]
def main():
    shutil.rmtree(W, ignore_errors=True); os.makedirs(W)
    shutil.copy(MODEL, os.path.join(W, "model.bin")); shutil.copy(BIN, os.path.join(W, "build_aip"))
    for f in ("patterns.txt", "frames.txt", "relations.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src): shutil.copy(src, os.path.join(W, f))
    res = {"pass": 0, "refuse": 0, "wrong": 0}
    for name, lines, want in CASES:
        rs = run(lines); got = rs[-1] if rs else ""
        ref = any(w in got for w in ("不 认识", "不 知道", "没 记 过", "不 太 懂", "不 确定", "不 太 确定"))
        if want in got and not ref: res["pass"] += 1; print("  [PASS] %-10s => %r" % (name, got.strip()[:55]))
        elif ref: res["refuse"] += 1; print("  [REFUSE] %-8s => %r" % (name, got.strip()[:55]))
        else: res["wrong"] += 1; print("  [WRONG] %-9s => %r（要 %r）" % (name, got.strip()[:55], want))
    print("=> pass %d / refuse %d / wrong %d（共 %d）" % (res["pass"], res["refuse"], res["wrong"], len(CASES)))
    return 1 if res["wrong"] > 0 else 0
if __name__ == "__main__":
    sys.exit(main())
