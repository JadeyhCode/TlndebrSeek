#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gap_exec_blind.py — §7.064 `::gap do`: plan -> execute local proof -> verify (⑯/⑰).

Checks: transitive proof found (2 hops), not-found path with next steps, missing word needs data,
ledger rows, the three observable stages, and ablation (`gap_do_local=0` disables execution).
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "gapexec")
CORPUS = "甲\t属于\t乙\n乙\t属于\t丙\n"


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
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
    with open(os.path.join(W, "c.tsv"), "w", encoding="utf-8") as f:
        f.write(CORPUS)
    base = "::ingest c.tsv\n"

    out = run(base + "::gap do 甲 属于 丙\n::quit\n")
    checks = []
    checks.append(("传递求证：2 跳路径 + 本地可求证",
                   "找到传递路径（2 跳）" in out and "本地可求证" in out))

    out = run(base + "::gap do 丙 属于 甲\n::quit\n")
    checks.append(("无路径：明说失败 + 给下一步",
                   "本地无路径" in out and "本地求证失败" in out and "::paper search" in out))

    out = run(base + "::gap do 丁 属于 甲\n::quit\n")
    checks.append(("缺词：明说不能自动补", "缺词" in out and "不能自动补" in out))

    out = run(base + "::gap do 甲 属于 丙\n::quit\n")
    checks.append(("三阶段可观测", "计划→执行→验证" in out and "计划：" in out and "执行：" in out and "验证：" in out))

    led = os.path.join(W, "_t", "gap_exec.tsv")
    ok_led = os.path.isfile(led) and "found" in open(led, encoding="utf-8").read()
    checks.append(("账本记录 found", ok_led))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("gap_do_local=0\n")
    out = run(base + "::gap do 甲 属于 丙\n::quit\n")
    checks.append(("消融：策略关闭后不执行本地搜索",
                   "本地搜索被策略关闭" in out and "找到传递路径" not in out))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 缺口执行首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
