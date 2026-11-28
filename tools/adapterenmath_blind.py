#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adapterenmath_blind.py — §7.115 英语应用题走 adapter 钩子（adapter_en_math 回退）首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "adapterenmath")
SUP = "Ben has 30 cards, buys 12 more, gives 9 away. How many?"
SUP2 = "A crate holds 7 boxes with 11 jars each. How many jars?"
UNSUP = "3 boxes each containing 4 bags with 5 apples each. How many apples?"


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def set_policy(extra):
    txt = open(os.path.join(ROOT, "policy.txt"), encoding="utf-8").read()
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n" + extra + "\n")


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
    checks = []

    out = run(SUP + "\n::quit\n")
    checks.append(("默认：支持模板算出 33", "The answer is 33." in out))
    out = run(SUP2 + "\n::quit\n")
    checks.append(("默认：第二个支持模板算出 77", "The answer is 77." in out))
    out = run(UNSUP + "\n::quit\n")
    checks.append(("默认：超出模板明确拒绝", "can't solve this word problem" in out))

    set_policy("adapter_en_math=0")
    out = run(SUP + "\n" + UNSUP + "\n猫 属于 动物 吗\n::quit\n")
    checks.append(("消融：不再算应用题（无 33/无拒绝语）",
                   "The answer is 33." not in out and "can't solve this word problem" not in out))
    checks.append(("消融：中文句仍答对", "属于" in out and "猫 -[属于]-> 动物" in out))

    set_policy("adapter_en_math=1")
    out = run(SUP + "\n::quit\n")
    checks.append(("显式开 1：33 恢复", "The answer is 33." in out))

    set_policy("")
    o1 = run(SUP + "\n::quit\n")
    o2 = run(SUP + "\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 英语应用题适配器首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
