#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plan_blind.py — §7.048 流程策略 `::plan` 首跑（7 项）

检查：四类任务的步骤顺序、`run` 只执行安全本地一步（能答/拒）、不擅自联网、
以及 plans.tsv 记账（dry + run 两类）。
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "plan")


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
    out = run("::plan 猫 属于 动物 吗\n::quit\n")
    checks.append(("事实类：六步且顺序对",
                   "任务类型：fact" in out and "::gap" in out and "本地图检索" in out
                   and "::paper search" in out and "::ask" in out and "放弃" in out))

    out = run("::plan 写一个程序：读入一个整数，输出它的平方。\n::quit\n")
    checks.append(("代码类：合成 + 缺口 + 放弃", "任务类型：code" in out
                   and "::code synth" in out and "::gap" in out))

    out = run("::plan 3 米 + 20 厘米 等于 多少 厘米\n::quit\n")
    checks.append(("计算类：先精确计算", "任务类型：math" in out and "计算/单位/百分比" in out))

    out = run("::plan 这篇论文讲了什么\n::quit\n")
    checks.append(("论文类：先查论文", "任务类型：paper" in out and "1) ::paper search" in out))

    out = run("::plan run 猫 属于 动物 吗\n::quit\n")
    checks.append(("run：本地能答就停", "能答" in out and "→ 停" in out))

    out = run("::plan run 螺旋兽 属于 动物 吗\n::quit\n")
    checks.append(("run：答不出就按计划继续（不擅自联网）",
                   "答不出" in out and "按上面步骤继续" in out and "不擅自联网" in out))

    tsv = os.path.join(W, "_t", "plans.tsv")
    ok_tsv = False
    if os.path.isfile(tsv):
        s = open(tsv, encoding="utf-8", errors="replace").read()
        ok_tsv = ("dry" in s and "run" in s)
    checks.append(("plans.tsv 记账（dry + run）", ok_tsv))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 流程策略首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
