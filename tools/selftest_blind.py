#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_blind.py — §7.060 in-kernel self-test (E18 groundwork) first run.

Runs `::selftest` and checks: 10/10 pass, all checks named, save/load roundtrip included,
ledger written, no FAIL lines.
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "selftest")


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    p = subprocess.run([BIN, "--model", "model.bin"], input=b"::selftest\n::quit\n",
                       capture_output=True, cwd=W, timeout=180)
    out = (p.stdout + p.stderr).decode("utf-8", "replace")
    checks = []
    checks.append(("10 项全过、0 红", "结果：10 过 / 0 红" in out and "FAIL]" not in out))
    checks.append(("10 个 [OK] 行", out.count("[OK]") == 10))
    checks.append(("含存读往返检查", "存读往返" in out))
    checks.append(("退出码 0", p.returncode == 0))
    tsv = os.path.join(W, "_t", "selftest.tsv")
    ok_tsv = False
    if os.path.isfile(tsv):
        row = open(tsv, encoding="utf-8").read().strip().splitlines()[-1].split("\t")
        ok_tsv = len(row) == 3 and row[1] == "10" and row[2] == "0"
    checks.append(("selftest.tsv 记账 10/0", ok_tsv))
    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 自检首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
