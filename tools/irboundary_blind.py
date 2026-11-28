#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irboundary_blind.py — §7.097 P4 IR 边界（text→IR→规范文本，只读）首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "irboundary")


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

    out = run("::ir 猫 属于 动物\n::quit\n")
    checks.append(("陈述 → REL 原子并回写", "kind=REL" in out and "a=猫 rel=属于 b=动物" in out
                   and "[IR→文本] 猫 属于 动物" in out))

    out = run("::ir 猫 属于 动物 吗\n::quit\n")
    checks.append(("问句 → QUERY（q=1）", "kind=QUERY" in out and "q=1" in out
                   and "[IR→文本] 猫 属于 动物 吗" in out))

    out = run("::ir 猫 不 属于 植物\n::quit\n")
    checks.append(("否定 → neg=1 并回写", "neg=1" in out and "猫 不 属于 植物" in out))

    out = run("::ir ::stats\n::quit\n")
    checks.append(("元命令 → CMD", "kind=CMD" in out and "cmd=::stats" in out))

    out = run("::ir 今天 天气 很 好\n::quit\n")
    checks.append(("接不住的文本 → UNKNOWN（不崩）", "kind=UNKNOWN" in out and "note=" in out))

    out = run("::ir 甲测 属于 乙测\n::rel 甲测\n::quit\n")
    checks.append(("只读：IR 不写图（甲测 没有属于边）", "甲测 --[属于]--> 乙测" not in out))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("ir_adapter=0\n")
    out = run("::ir 猫 属于 动物\n::quit\n")
    checks.append(("消融 ir_adapter=0 ⇒ 明确回退旧行为", "适配器关" in out))
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(orig)

    o1 = run("::ir 猫 属于 动物 吗\n::quit\n")
    o2 = run("::ir 猫 属于 动物 吗\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> IR 边界首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
