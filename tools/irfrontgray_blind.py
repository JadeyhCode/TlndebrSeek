#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irfrontgray_blind.py — §7.106 IR 前置灰度模式（仅核心关系）首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "irfrontgray")


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
    with open(os.path.join(W, "d.tsv"), "w", encoding="utf-8") as f:
        f.write("甲测\t谓测\t乙测\n")
    checks = []

    set_policy(orig + "\nir_front=2\n")
    out = run("::ingest d.tsv\n猫 是 动物 吗\n甲测 谓测 乙测 吗\n::irfront show\n::quit\n")
    checks.append(("灰度：核心别名回写 1 次", "回写 1" in out))
    checks.append(("灰度：动态谓语透传 1 次", "灰度透传 1" in out and "灰度命中 1" in out))
    checks.append(("show 标明模式 2", "ir_front=2" in out and "灰度：仅核心关系" in out))

    set_policy(orig + "\nir_front=1\n")
    out = run("::ingest d.tsv\n猫 是 动物 吗\n甲测 谓测 乙测 吗\n::irfront show\n::quit\n")
    checks.append(("全开模式不记灰度计数", "灰度命中 0，灰度透传 0" in out))

    set_policy(orig)
    out = run("猫 是 动物 吗\n::irfront show\n::quit\n")
    checks.append(("关闭模式不统计", "尝试 0，回写 0" in out))

    set_policy(orig + "\nir_front=2\n")
    out = run("::irfront reset\n::irfront show\n::quit\n")
    checks.append(("reset 清灰度计数", "灰度命中 0，灰度透传 0" in out and "尝试 0" in out))

    # 灰度与关闭的答案一致（核心+动态两句）
    set_policy(orig)
    off = run("::ingest d.tsv\n猫 是 动物 吗\n甲测 谓测 乙测 吗\n::quit\n")
    set_policy(orig + "\nir_front=2\n")
    gray = run("::ingest d.tsv\n猫 是 动物 吗\n甲测 谓测 乙测 吗\n::quit\n")
    aoff = [l for l in off.splitlines() if "AI >" in l]
    agray = [l for l in gray.splitlines() if "AI >" in l]
    checks.append(("灰度与关闭答案一致", aoff == agray and len(aoff) == 2))

    o1 = run("::ingest d.tsv\n猫 是 动物 吗\n::irfront show\n::quit\n")
    o2 = run("::ingest d.tsv\n猫 是 动物 吗\n::irfront show\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> IR 前置灰度首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
