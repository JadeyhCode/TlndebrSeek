#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plan_queue_blind.py — §7.067 plan refusal enters the study queue (③/⑰) first run.

Checks: refused plan queues the full question with reason 未解; `::study next` picks it; a successful
plan does not queue; `plan_queue_study=0` disables it (ablation).
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "planqueue")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def curious():
    p = os.path.join(W, "_t", "curious.tsv")
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
    out = run("::ingest c.tsv\n::plan run 甲 属于 丙 吗\n::study next\n::quit\n")
    checks.append(("放弃时排入自学队列", "已排入自学队列" in out))
    checks.append(("队列里是整题、理由是未解",
                   "甲 属于 丙 吗" in curious() and "未解（流程放弃）" in curious()))
    checks.append(("::study next 取到同一题",
                   "[自学] 下一题" in out and "甲 属于 丙 吗" in out.split("[自学] 下一题", 1)[1]))

    before = len(curious().splitlines())
    out = run("::ingest c.tsv\n::plan run 甲 属于 乙 吗\n::quit\n")
    checks.append(("能答的流程不入队",
                   "已排入自学队列" not in out and len(curious().splitlines()) == before))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("plan_queue_study=0\n")
    before = len(curious().splitlines())
    out = run("::ingest c.tsv\n::plan run 甲 属于 丙 吗\n::quit\n")
    checks.append(("消融：置 0 后不入队",
                   "已排入自学队列" not in out and len(curious().splitlines()) == before))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 流程→自学队列首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
