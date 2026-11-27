#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dynquery_blind.py — §7.081 动态关系识别层（核心+动态）首跑。

修：动态关系名进词池（多字不再被切碎）+ ::gap 按字符串扫 core+dyn。
检查：多字动态谓语可问、::gap 认作“已能回答”、::know relations 列出、
高 id（245 内）可问、软上限未登记时不被识别（消融）。
"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "dynquery")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def pn(i):
    return "谓" + chr(0x4e00 + i)


def corpus(path, n):
    with open(path, "w", encoding="utf-8") as f:
        for i in range(1, n + 1):
            f.write("甲%d\t%s\t乙%d\n" % (i, pn(i), i))


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt",
              "policy.txt", "relations_beh.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    corpus(os.path.join(W, "c300.tsv"), 300)
    corpus(os.path.join(W, "c20.tsv"), 20)
    checks = []

    out = run("::ingest c300.tsv\n甲1 %s 乙1 吗\n::gap 甲1 %s 乙1\n::know relations\n::quit\n" % (pn(1), pn(1)))
    checks.append(("多字动态谓语可问（不再切碎）", "对" in out and "甲1" in out))
    checks.append(("::gap 认作已能回答", "已能回答" in out))
    checks.append(("::know relations 列出动态关系", pn(1) in out and "id=" in out))

    out = run("::ingest c300.tsv\n甲244 %s 乙244 吗\n::gap 甲244 %s 乙244\n::quit\n" % (pn(244), pn(244)))
    checks.append(("高 id（245 内）动态关系可问可查缺口",
                   "对" in out and "已能回答" in out))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("dynrel_soft_limit=8\n")
    out = run("::ingest c20.tsv\n甲10 %s 乙10 吗\n::gap 甲10 %s 乙10\n::quit\n" % (pn(10), pn(10)))
    checks.append(("消融：软上限 8 ⇒ 第 10 个谓语未登记、不被识别",
                   "缺结构" in out and "已能回答" not in out))
    checks.append(("消融后仍不崩（有答复路径）", "AI >" in out))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    out = run("::ingest c300.tsv\n甲2 %s 乙2 吗\n::quit\n" % pn(2))
    checks.append(("恢复后同一句又能答对", "对" in out))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 动态关系识别首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
