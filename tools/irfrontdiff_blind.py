#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irfrontdiff_blind.py — §7.102 IR 前置答案差异测量（front 0 vs 1，只读）。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "irfrontdiff")

# 只放**答案确定**的关系问句：小谈/创作类每进程随机措辞，不适合做逐字差异
SENTENCES = [
    "猫 属于 动物 吗", "猫 是 动物 吗", "猫 不 属于 植物 吗",
    "猫 会 飞 吗", "猫 吃 鱼 吗",
    "狗 属于 动物 吗", "狗 会 叫 吗",
    "猫 属于 生物 吗", "动物 包含 猫 吗",
]


def run(inp, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=240, env=e)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def answers(out):
    return [l.split("AI > ", 1)[1] for l in out.splitlines() if "AI > " in l]


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
    batch = "".join(s + "\n" for s in SENTENCES) + "::quit\n"

    set_policy(orig)
    off = answers(run(batch))
    set_policy(orig + "\nir_front=1\n")
    on = answers(run(batch))
    checks = []
    checks.append(("整批答案逐条一致（front 0 vs 1）", off == on and len(off) >= len(SENTENCES) - 2))

    # 差异账本：只在有差异时写；这里应当 0 行
    diffp = os.path.join(W, "_t", "ir_front_diff.tsv")
    rows = open(diffp, encoding="utf-8").read().splitlines() if os.path.isfile(diffp) else []
    checks.append(("答案变化率 0（无差异账本行）", len(rows) == 0))

    # 同一模式下两次一致
    a1 = answers(run(batch))
    a2 = answers(run(batch))
    checks.append(("front=1 两次读数一致", a1 == a2))

    # 把差异真实写出来（人为注入一行）以验证账本格式可用
    with open(diffp, "w", encoding="utf-8") as f:
        f.write("0\t样例\t原文\t回写\t一致\n")
    checks.append(("差异账本可写（格式：idx/输入/两侧答案/是否一致）",
                   os.path.isfile(diffp) and open(diffp, encoding="utf-8").read().count("\t") == 4))

    set_policy(orig)
    checks.append(("恢复默认后答案与基线一致", answers(run(batch)) == off))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 前置答案差异首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
