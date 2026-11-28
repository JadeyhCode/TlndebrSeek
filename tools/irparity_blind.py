#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irparity_blind.py — §7.098 IR 双跑对照（原文 vs IR 回写，只读）首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "irparity")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt",
              "policy.txt", "relations_beh.txt", "dims.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    orig = open(os.path.join(W, "policy.txt"), encoding="utf-8").read()
    checks = []

    out = run("::irparity 猫 属于 动物\n::quit\n")
    checks.append(("陈述：原子一致 + 真值/证据一致",
                   "原子一致=是" in out and "原文=成立(直接)" in out
                   and "回写=成立(直接)" in out and "可安全走 IR" in out))

    out = run("::irparity 猫 属于 生物\n::quit\n")
    checks.append(("传递问句（属于→生物）：推导证据一致",
                   "原文=成立(推导)" in out and "回写=成立(推导)" in out))

    out = run("::irparity 猫 不 属于 植物\n::quit\n")
    checks.append(("否定：不成立且证据一致",
                   "原文=不成立(" in out and "回写=不成立(" in out))

    out = run("::irparity ::stats\n::quit\n")
    checks.append(("元命令：CMD 一致", "一致（非关系原子）" in out))

    out = run("::irparity 今天 天气 很 好\n::quit\n")
    checks.append(("UNKNOWN：两边一致（不崩）", "回写 → UNKNOWN" in out and "一致（非关系原子）" in out))

    out = run("::irparity 甲测 属于 乙测\n::rel 甲测\n::quit\n")
    checks.append(("只读：对照不写图", "甲测 --[属于]--> 乙测" not in out))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("ir_adapter=0\n")
    out = run("::irparity 猫 属于 动物\n::quit\n")
    checks.append(("消融 ir_adapter=0 ⇒ 不做 IR 中转", "不做 IR 中转" in out))
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(orig)

    o1 = run("::irparity 猫 属于 动物\n::quit\n")
    o2 = run("::irparity 猫 属于 动物\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> IR 双跑对照首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
