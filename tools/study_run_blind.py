#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""study_run_blind.py — §7.069 `::study next run`: pick → self-answer → reflect → help order (③).

Checks: full pipeline output, stats row/print, plain `next` does not self-answer, unanswerable
question goes through the help order (sym hint + ask user) and records the distribution, and
`study_ask_user=0` stops the user-help step (ablation).
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "studyrun")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def read(p):
    return open(p, encoding="utf-8", errors="replace").read() if os.path.isfile(p) else ""


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
    out = run("::ingest c.tsv\n::plan run 甲 属于 丙 吗\n::study next run\n::quit\n")
    checks.append(("一条命令走完 出题→自答→自检→归因",
                   "[自学] 出题" in out and "[自学] 自答" in out and
                   "[自学] 自检" in out and "归因" in out))
    stats = read(os.path.join(W, "_t", "study", "stats.tsv"))
    checks.append(("stats 账本记录该题", "甲 属于 丙 吗" in stats))
    checks.append(("打印自学统计", "[自学统计]" in out and "自解" in out))

    out = run("::study pose 甲 有 翅膀 吗\n::study next\n::quit\n")
    checks.append(("只选题不自答（next 无 run）", "[自学] 下一题" in out and "[自学] 自答" not in out))

    out = run("::study next run\n::quit\n")
    checks.append(("答不出时按求助顺序（sym 建议 + 问用户）",
                   "求助④自省工具建议" in out and "求助③问用户" in out))
    checks.append(("求助分布记账",
                   "问用户 1" in out and
                   "甲 有 翅膀 吗" in read(os.path.join(W, "_t", "study", "ask_user.tsv"))))

    before = len(read(os.path.join(W, "_t", "study", "ask_user.tsv")).splitlines())
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("study_ask_user=0\n")
    out = run("::study pose 甲 有 第三只手 吗\n::study next run\n::quit\n")
    after = len(read(os.path.join(W, "_t", "study", "ask_user.tsv")).splitlines())
    checks.append(("消融：study_ask_user=0 不再问用户",
                   after == before and "求助③问用户" not in out))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 选题即跑首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
