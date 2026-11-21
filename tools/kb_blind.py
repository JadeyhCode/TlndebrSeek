#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§6.974 分类/处所“学 A 考 B”盲测（12 题首跑）：用新教的基础分类做**没教过的组合**。
判分：期望串出现=pass；明确拒绝/不知道=refuse；其它=wrong。
"""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip"); MODEL = os.path.join(ROOT, "model.bin")
W = os.path.join(ROOT, "_t", "kblind")
TASKS = [
    ("狗 属于 哺乳动物 吗", "对"),
    ("鲸鱼 有 肺 吗", "对"),
    ("企鹅 有 翅膀 吗", "对"),
    ("蛇 有 鳞片 吗", "对"),
    ("蚂蚁 属于 动物 吗", "对"),
    ("青蛙 属于 两栖动物 吗", "对"),
    ("猫 属于 食肉目 吗", "对"),
    ("鸟 属于 哺乳动物 吗", "不 是"),
    ("鱼 属于 哺乳动物 吗", "不 是"),
    ("猫 有 六 条 腿 吗", "不 是"),
    ("中国 在 亚洲 吗", "对"),
    ("犰狳 属于 什么", "不 认识"),
]
def run(q):
    inp = "::notepad off\n::char off\n::ingest code/knowledge/基础分类.triples\n" + q + "\n::quit\n"
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp, text=True,
                       encoding="utf-8", errors="replace", capture_output=True, cwd=W, timeout=120)
    rs = [l[l.find("AI > ") + 5:] for l in p.stdout.splitlines() if "AI > " in l]
    return rs[-1] if rs else ""
def main():
    shutil.rmtree(W, ignore_errors=True); os.makedirs(W)
    shutil.copy(MODEL, os.path.join(W, "model.bin")); shutil.copy(BIN, os.path.join(W, "build_aip"))
    for f in ("patterns.txt", "frames.txt", "relations.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src): shutil.copy(src, os.path.join(W, f))
    kd = os.path.join(W, "code", "knowledge"); os.makedirs(kd, exist_ok=True)
    shutil.copy(os.path.join(ROOT, "code", "knowledge", "基础分类.triples"), kd)
    res = {"pass": 0, "refuse": 0, "wrong": 0}
    for q, want in TASKS:
        got = run(q)
        ref = any(w in got for w in ("不 认识", "不 知道", "没 记 过", "不 太 懂", "不 确定"))
        if want in got and not ref:
            res["pass"] += 1; print("  [PASS] %-20s => %r" % (q, got.strip()[:60]))
        elif ref:
            res["refuse"] += 1; print("  [REFUSE] %-18s => %r" % (q, got.strip()[:60]))
        else:
            res["wrong"] += 1; print("  [WRONG] %-19s => %r（要 %r）" % (q, got.strip()[:60], want))
    print("=> pass %d / refuse %d / wrong %d（共 %d）" % (res["pass"], res["refuse"], res["wrong"], len(TASKS)))
    return 0
if __name__ == "__main__":
    sys.exit(main())
