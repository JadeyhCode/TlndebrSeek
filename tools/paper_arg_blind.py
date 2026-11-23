#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper_arg_blind.py — §7.014 论文论证结构首跑（主张/证据/限定/出处/陈述）

10 句（未参与调优），`::paper roles` 逐句判角色；首跑读数=准确率。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "paperarg")

CASES = [
    ("根据参考文献，地磁倒转周期约二十万年。", "出处"),
    ("实验表明，温度升高时反应会加快。", "证据"),
    ("作者认为这个模型适合小样本。", "主张"),
    ("统计显示，样本量越大误差越小。", "证据"),
    ("也许这组数据有噪声。", "限定"),
    ("该方法通常需要更多标注。", "限定"),
    ("我们主张先验证再扩展。", "主张"),
    ("数据来源不详，结论可能不稳。", "出处"),
    ("猫属于动物。", "陈述"),
    ("这批样本往往不稳定。", "限定"),
]


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    txt = os.path.join(W, "arg.txt")
    with open(txt, "w", encoding="utf-8") as f:
        for s, _ in CASES:
            f.write(s + "\n")
    p = subprocess.run([os.path.join(W, "build_aip"), "--model", "model.bin"],
                       input=("::paper roles arg.txt\n::quit\n").encode(),
                       capture_output=True, cwd=W, timeout=120)
    out = (p.stdout + p.stderr).decode("utf-8", "replace")
    roles = re.findall(r"\[(主张|证据|限定|出处|陈述)\] ", out)
    ok = 0
    for i, (s, want) in enumerate(CASES):
        got = roles[i] if i < len(roles) else "?"
        good = (got == want)
        ok += good
        print("  [%s] 期望 %-2s 实得 %-2s  %s" % ("OK" if good else "FAIL", want, got, s))
    n = len(CASES)
    print("=> 论证结构首跑：%d/%d（%.0f%%）" % (ok, n, 100.0 * ok / n))
    return 0 if ok * 10 >= n * 8 else 1


if __name__ == "__main__":
    sys.exit(main())
