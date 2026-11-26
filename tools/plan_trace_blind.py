#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plan_trace_blind.py — §7.065 observable plan→execute→verify trace (⑰).

Checks: known fact stops at local step with 能答; unknown runs all steps, external/write steps are
refused, result 拒; math task selects calc steps; ledger row; step list is policy data (ablation).
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "plantrace")


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
        f.write("甲\t属于\t乙\n")

    checks = []
    out = run("::ingest c.tsv\n::plan run 甲 属于 乙 吗\n::quit\n")
    checks.append(("已知：gap 已能回答 + local 能答 → 停",
                   "gap → 已能回答" in out and "local → 能答" in out and
                   "结果：能答" in out and "paper →" not in out))

    out = run("::ingest c.tsv\n::plan run 甲 属于 丙 吗\n::quit\n")
    checks.append(("未知：跑完全部步骤并拒",
                   "结果：拒" in out and "共走 6 步" in out))
    checks.append(("外部/写入步骤被拒绝（不擅自联网/写图）",
                   "ask → 拒绝" in out and "sym → 拒绝" in out))

    out = run("::ingest c.tsv\n::plan run 12 加 3 是多少\n::quit\n")
    checks.append(("数学类型走 calc 步骤（不自动执行）",
                   "任务类型：math" in out and "calc → 未自动执行" in out))

    led = os.path.join(W, "_t", "plans.tsv")
    ok_led = os.path.isfile(led) and "run" in open(led, encoding="utf-8").read()
    checks.append(("账本记录 run", ok_led))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("plan_steps_fact=local,refuse\n")
    out = run("::ingest c.tsv\n::plan run 甲 属于 丙 吗\n::quit\n")
    checks.append(("消融：步骤表由数据决定（只 2 步）",
                   "gap →" not in out and "共走 2 步" in out))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 流程 trace 首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
