#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chain_blind.py — §7.046 多步约束求解 `::chain` 首跑（7 项）

覆盖：纯给定条件的多级链、条件+图知识的混合链、反向判定、条件不足拒答、
非传递关系的直边、图里的否定、以及每条成功结论都带自检行。
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "chain")


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
    out = run("::chain 甲兽 属于 乙兽 ; 乙兽 属于 丙兽 ; 丙兽 属于 丁兽 => 甲兽 属于 丁兽\n::quit\n")
    checks.append(("纯条件三级链 ⇒ 对且链完整",
                   "**对**" in out and "甲兽" in out and "丁兽" in out and "丙兽" in out))
    checks.append(("成功结论带自检", "[自检]" in out))

    out = run("::chain 猫 属于 哺乳动物 => 猫 属于 生物\n::quit\n")
    checks.append(("条件+图知识混合链 ⇒ 对", "**对**" in out and "生物" in out))

    out = run("::chain 甲兽 属于 乙兽 => 乙兽 属于 甲兽\n::quit\n")
    checks.append(("反向（条件里成立）⇒ 不对", "**不对**" in out))

    out = run("::chain 甲兽 属于 乙兽 => 甲兽 属于 丙兽\n::quit\n")
    checks.append(("条件不足 ⇒ 拒答", "条件不足" in out and "拒答" in out))

    out = run("::chain 甲兽 有 角 => 甲兽 有 角\n::quit\n")
    checks.append(("非传递关系直边（条件内）⇒ 对", "**对**" in out))

    out = run("::chain 猫 属于 动物 => 猫 会 飞\n::quit\n")
    checks.append(("图里的否定（猫不会飞）⇒ 不对", "**不对**" in out))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 多步求解首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
