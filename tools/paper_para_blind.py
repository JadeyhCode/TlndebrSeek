#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper_para_blind.py — §7.072 paragraph provenance for paper claims (D12) first run.

Claims now carry the paragraph they came from (`论文#N`). Checks: three-paragraph doc yields
#1/#2/#3 sources, conflicts show the two distinct sources, ::know symbol shows the paragraph,
and a single paragraph stays #1.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "paperpara")
DOC = "第一段：根据参考文献，猫 属于 动物。\n\n第二段：实验表明，猫 有 毛发。\n\n第三段：结论，猫 属于 猫科。\n"


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    with open(os.path.join(W, "d.txt"), "w", encoding="utf-8") as f:
        f.write(DOC)
    with open(os.path.join(W, "one.txt"), "w", encoding="utf-8") as f:
        f.write("根据参考文献，狗 属于 动物。\n")

    checks = []
    out = run("::paper read d.txt\n::claim\n::quit\n")
    checks.append(("三段各带段落出处", "论文#1" in out and "论文#2" in out and "论文#3" in out))
    checks.append(("待证 3 条", "共 3 条" in out))

    out = run("::paper read d.txt\n::know symbol 猫\n::quit\n")
    checks.append(("符号自省显示段落出处", "论文#3" in out and "猫 属于 猫科" in out))

    out = run("::paper read d.txt\n::paper conflicts\n::quit\n")
    checks.append(("冲突两侧来源不同段", "论文#1" in out and "论文#3" in out))

    out = run("::paper read one.txt\n::claim\n::quit\n")
    checks.append(("单段文件是 #1", "论文#1" in out))

    out = run("::paper read d.txt\n::claim\n::quit\n")
    checks.append(("出处格式统一为 论文#N", "来源：论文#" in out))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 论文段落出处首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
