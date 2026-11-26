#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""knowsymbol_blind.py — §7.071 self-symbol inventory: meaning + edges + sources + claims (D13).

Checks: outgoing relations and degree, incoming edges, source-role distribution, pending claims with
source, unknown-symbol message, and claim count.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "knowsymbol")


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
    with open(os.path.join(W, "c.tsv"), "w", encoding="utf-8") as f:
        f.write("猫\t属于\t动物\n猫\t有\t毛发\n")
    with open(os.path.join(W, "d.txt"), "w", encoding="utf-8") as f:
        f.write("根据参考文献，猫 属于 猫科。\n")

    base = "::ingest c.tsv\n::paper read d.txt\n"
    checks = []
    out = run(base + "::know symbol 猫\n::quit\n")
    checks.append(("出边：猫 --[属于]--> 动物", "猫 --[属于]--> 动物" in out))
    checks.append(("行有度数", "度 " in out and "关系边" in out))

    out = run(base + "::know symbol 动物\n::quit\n")
    checks.append(("入边：猫 --[属于]--> 动物", "入边" in out and "猫 --[属于]--> 动物" in out))

    out = run(base + "::know symbol 动物\n::quit\n")
    checks.append(("来源档分布（基准/共现等）", "来源档：" in out and ("基准" in out or "共现" in out)))

    out = run(base + "::know symbol 猫\n::quit\n")
    checks.append(("待证带来源", "待证（还不算数）" in out and "猫 属于 猫科" in out and "论文" in out))
    checks.append(("待证条数=1", "待证条数：1" in out))

    out = run("::know symbol 不存在的符号\n::quit\n")
    checks.append(("未知符号明说没有", "图里没有" in out))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 符号自省首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
