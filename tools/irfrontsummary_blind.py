#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irfrontsummary_blind.py — §7.102 IR 前置命中汇总/清零首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "irfrontsummary")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def set_policy(text):
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(text)


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

    set_policy(orig + "\nir_front=1\n")
    out = run("猫 是 动物 吗\n猫 是 动物 吗\n::irfront summary\n::quit\n")
    checks.append(("两次同句命中：2 条 / 去重 1 条",
                   "命中账本：2 条，去重原文 1 条" in out))
    checks.append(("汇总带最近样例", "最近：" in out and "猫 是 动物 吗" in out))

    out = run("::irfront summary\n::irfront summary\n::quit\n")
    checks.append(("summary 只读：重复看不会新增账本行",
                   "命中账本：2 条，去重原文 1 条" in out))

    out = run("::irfront reset\n::irfront summary\n::quit\n")
    checks.append(("reset 同时清账本", "还没有命中记录" in out))

    set_policy(orig)
    out = run("猫 是 动物 吗\n::irfront summary\n::quit\n")
    checks.append(("front=0：无命中记录", "还没有命中记录" in out))

    set_policy(orig + "\nir_front=1\n")
    o1 = run("::irfront reset\n猫 是 动物 吗\n::irfront summary\n::quit\n")
    o2 = run("::irfront reset\n猫 是 动物 吗\n::irfront summary\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 前置命中汇总首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
