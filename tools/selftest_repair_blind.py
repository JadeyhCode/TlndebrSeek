#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selftest_repair_blind.py — §7.061 guarded self-repair (E18 step) first run.

Checks:
  ① normal model: repair finds nothing to fix, checks still 10/10;
  ② forced attention-budget corruption: check reports FAIL, repair scales weights, recheck has 0 red;
  ③ without repair, the corruption stays red (no silent fix);
  ④ ledger records `repair` rows;
  ⑤ normal selftest still 10/10.
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "selftestrepair")


def run(inp, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180, env=e)
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
    out = run("::selftest repair\n::quit\n")
    checks.append(("正常模型：无项可修 + 10/10",
                   "没有需要修的项目" in out and "结果：10 过 / 0 红" in out))

    out = run("::selftest repair\n::quit\n", {"AIP_SELFTEST_BREAK": "budget"})
    checks.append(("损坏态：先报 FAIL 再修复",
                   "[FAIL]" in out and "实际修了 1 项" in out and "按 0.003 缩放" in out))
    checks.append(("修复后复检 0 红", "复检" in out and "0 红" in out))

    out = run("::selftest\n::quit\n", {"AIP_SELFTEST_BREAK": "budget"})
    checks.append(("不修复时保持红（不静默修）",
                   "[FAIL] 注意力分配不超预算" in out and "[修复]" not in out))

    tsv = os.path.join(W, "_t", "selftest.tsv")
    ok_tsv = os.path.isfile(tsv) and "repair" in open(tsv, encoding="utf-8").read()
    checks.append(("ledger 记录 repair 行", ok_tsv))

    out = run("::selftest\n::quit\n")
    checks.append(("正常自检仍 10/10", "结果：10 过 / 0 红" in out))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 自检-修复首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
