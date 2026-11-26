#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plan_study_blind.py — §7.066 plan refusal -> unsolved queue -> self-study loop (③/⑯/⑰).

Checks: a refused plan run records the question in `_t/unsolved.tsv` and says so; a successful run
records nothing; the recording is data-driven (`plan_note_unsolved=0` disables it).
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "planstudy")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def ledger():
    p = os.path.join(W, "_t", "unsolved.tsv")
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
    out = run("::ingest c.tsv\n::plan run 甲 属于 丙 吗\n::quit\n")
    checks.append(("放弃的流程明说已记入未解", "已记入未解" in out))
    checks.append(("未解账本里有这道题", "甲 属于 丙 吗" in ledger()))

    before = len(ledger().splitlines())
    out = run("::ingest c.tsv\n::plan run 甲 属于 乙 吗\n::quit\n")
    checks.append(("能答的流程不记未解",
                   "已记入未解" not in out and len(ledger().splitlines()) == before))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("plan_note_unsolved=0\n")
    before = len(ledger().splitlines())
    out = run("::ingest c.tsv\n::plan run 甲 属于 丙 吗\n::quit\n")
    checks.append(("消融：策略置 0 后不记",
                   "已记入未解" not in out and len(ledger().splitlines()) == before))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 流程→未解首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
