#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""study_priority_blind.py — §7.068 unsolved-priority in study picking (①/③) first run.

Two pending questions: a user-posed curiosity one and a plan-refused one (why=未解). With the policy
bonus the refused/unsolved question is picked; with `att_pick_unsolved=0` the earlier curiosity one wins.
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "studypriority")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def picked(out):
    m = re.search(r"\[自学\] 下一题（注意力得分 ([\d.]+)）：(.+)", out)
    return (float(m.group(1)), m.group(2).strip()) if m else (None, None)


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
    base = ("::ingest c.tsv\n::study pose 好奇的问题 是 什么\n"
            "::plan run 甲 属于 丙 吗\n")

    checks = []
    out_empty = run("::study next\n::quit\n")
    checks.append(("队列空时明说没有待学", "没有待学的题" in out_empty))

    out = run(base + "::study next\n::quit\n")
    sc, q = picked(out)
    checks.append(("未解题被优先选中", q is not None and "甲 属于 丙 吗" in q))
    checks.append(("注意力加成 0.60 生效", sc is not None and abs(sc - 0.60) < 0.01))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("att_pick_unsolved=0\n")
    out = run(base + "::study next\n::quit\n")
    sc2, q2 = picked(out)
    checks.append(("消融：关掉加成后选回先入队的题",
                   q2 is not None and "好奇的问题" in q2 and sc2 is not None and sc2 < 0.01))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    cur = os.path.join(W, "_t", "curious.tsv")
    distinct = set()
    if os.path.isfile(cur):
        for line in open(cur, encoding="utf-8"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) >= 2 and "pending" in line:
                distinct.add(parts[1])
    checks.append(("两题都保留在队列里（不丢题）", len(distinct) == 2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 未解优先首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
