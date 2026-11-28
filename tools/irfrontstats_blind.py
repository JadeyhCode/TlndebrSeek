#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irfrontstats_blind.py — §7.101 IR 前置统计/命中账本首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "irfrontstats")
BATCH = "猫 属于 动物 吗\n猫 是 动物 吗\n今天 天气 很 好\n"


def run(inp, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180, env=e)
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
    out = run(BATCH + "::irfront show\n::quit\n")
    checks.append(("front=1：尝试3/回写1/UNKNOWN1/原样1/命令1",
                   "尝试 3，回写 1，UNKNOWN 1，原样 1，命令跳过 1" in out))

    led = os.path.join(W, "_t", "ir_front_stats.tsv")
    rows = open(led, encoding="utf-8").read().splitlines() if os.path.isfile(led) else []
    checks.append(("命中账本只记回写（1 行，含原文与规范文本）",
                   len(rows) == 1 and "猫 是 动物 吗" in rows[0] and "猫 属于 动物 吗" in rows[0]))

    set_policy(orig)
    out = run(BATCH + "::irfront show\n::quit\n")
    checks.append(("front=0（默认）：不做统计/回写", "尝试 0，回写 0" in out))

    set_policy(orig + "\nir_front=1\n")
    out = run("::irfront reset\n::irfront show\n::quit\n")
    checks.append(("reset 清空计数", "尝试 0，回写 0，UNKNOWN 0" in out))

    out = run("::rel 猫\n::irfront show\n::quit\n")
    checks.append(("命令计入“命令跳过”但不计尝试",
                   "尝试 0，回写 0" in out and "命令跳过 2" in out))

    set_policy(orig + "\nir_front=1\nir_adapter=0\n")
    out = run("猫 是 动物 吗\n::irfront show\n::quit\n")
    checks.append(("ir_adapter=0 ⇒ 不统计（尝试 0）", "尝试 0，回写 0" in out))
    set_policy(orig)

    set_policy(orig + "\nir_front=1\n")
    o1 = run(BATCH + "::irfront show\n::quit\n")
    o2 = run(BATCH + "::irfront show\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))
    set_policy(orig)

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> IR 前置统计首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
