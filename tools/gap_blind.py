#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gap_blind.py — §7.047 缺口检测 + 可执行下一步 首跑（6 项）

覆盖：缺词（含未映射整词）、缺事实（词都认识但没边）、缺结构（没有关系词）、
已能回答、计划里真的给了可执行命令、以及 `_t/gaps.tsv` 记账。
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "gap")


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

    checks = []
    out = run("::gap 螺旋兽 属于 动物 吗\n::quit\n")
    checks.append(("缺词：点名整词", "类型：缺词" in out and "螺旋兽" in out))
    checks.append(("缺词计划：paper search + study pose + sym add",
                   "::paper search 螺旋兽" in out and "::study pose" in out and "::sym add 螺旋兽" in out))

    out = run("::gap 鱼 怕 鸟 吗\n::quit\n")
    checks.append(("缺事实：给出 edge add 与 ask",
                   "类型：缺事实" in out and "::sym edge add 鱼 怕 鸟" in out and "::ask" in out))

    out = run("::gap 螺旋兽螺旋化石头\n::quit\n")
    checks.append(("缺结构：指向 relations.txt", "类型：缺结构" in out and "relations.txt" in out))

    out = run("::gap 猫 属于 动物 吗\n::quit\n")
    checks.append(("已能回答：不再给缺口计划", "类型：已能回答" in out))

    tsv = os.path.join(W, "_t", "gaps.tsv")
    ok_tsv = False
    if os.path.isfile(tsv):
        s = open(tsv, encoding="utf-8", errors="replace").read()
        ok_tsv = ("缺词" in s and "缺事实" in s)
    checks.append(("gaps.tsv 记账（缺词/缺事实都在）", ok_tsv))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 缺口检测首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
