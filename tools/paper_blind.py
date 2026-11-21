#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§6.979 长文多段盲测（10 题首跑）：多段文档 → ::paper 抽断言 → 全部确认 → 跨段问答。
判分：期望串出现=pass；明确拒绝=refuse；其它=wrong。
"""
import os, re, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip"); MODEL = os.path.join(ROOT, "model.bin")
W = os.path.join(ROOT, "_t", "paperblind")

DOC = """貘 属于 奇蹄目。
貘 有 长鼻子。
貘 在 南美洲。

奇蹄目 属于 哺乳动物。
哺乳动物 有 肺。

树懒 属于 披毛目。
树懒 吃 叶子。
树懒 在 树上。

披毛目 属于 哺乳动物。

犰狳 属于 贫齿目。
犰狳 吃 蚂蚁。
牛 属于 偶蹄目。
牛 吃 草。
"""
ASKS = [
    ("貘 有 长鼻子 吗", "对"),
    ("貘 属于 奇蹄目 吗", "对"),
    ("貘 属于 哺乳动物 吗", "对"),
    ("貘 有 肺 吗", "对"),
    ("树懒 吃 什么", "叶子"),
    ("树懒 在 哪里", "树"),
    ("披毛目 属于 哺乳动物 吗", "对"),
    ("犰狳 吃 什么", "蚂蚁"),
    ("牛 吃 草 吗", "对"),
    ("犰狳 属于 哺乳动物 吗", "不"),
]

def run(inp, model):
    p = subprocess.run([BIN, "--model", model], input=inp, text=True, encoding="utf-8",
                       errors="replace", capture_output=True, cwd=W, timeout=180)
    return p.stdout

def main():
    shutil.rmtree(W, ignore_errors=True); os.makedirs(W)
    shutil.copy(MODEL, os.path.join(W, "m.bin")); shutil.copy(BIN, os.path.join(W, "build_aip"))
    for f in ("patterns.txt", "frames.txt", "relations.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src): shutil.copy(src, os.path.join(W, f))
    open(os.path.join(W, "doc.txt"), "w", encoding="utf-8").write(DOC)
    # ① 读文档 → 全确认
    first = run("::notepad off\n::char off\n::paper read doc.txt\n::save m.bin\n::quit\n", "m.bin")
    m = re.search(r"抽到\s*(\d+)\s*条", first)
    n = int(m.group(1)) if m else 0
    acc = "::notepad off\n::char off\n" + ("::claim accept 1\n" * n) + "::claim\n::save m.bin\n::quit\n"
    run(acc, "m.bin")
    print("文档断言：%d 条（已全部确认）" % n)
    # ② 逐题问（同一模型，独立进程）
    res = {"pass": 0, "refuse": 0, "wrong": 0}
    for q, want in ASKS:
        out = run("::notepad off\n::char off\n" + q + "\n::quit\n", "m.bin")
        rs = [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]
        got = rs[-1] if rs else ""
        ref = any(w in got for w in ("不 认识", "不 知道", "没 记 过", "不 太 懂", "不 确定", "不 太 确定"))
        if want in got and not ref: res["pass"] += 1; print("  [PASS] %-18s => %r" % (q, got.strip()[:50]))
        elif ref: res["refuse"] += 1; print("  [REFUSE] %-15s => %r" % (q, got.strip()[:50]))
        else: res["wrong"] += 1; print("  [WRONG] %-16s => %r（要 %r）" % (q, got.strip()[:50], want))
    print("=> pass %d / refuse %d / wrong %d（共 %d）" % (res["pass"], res["refuse"], res["wrong"], len(ASKS)))
    return 1 if res["wrong"] > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
