#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analogy_blind.py — §7.092 类型化路径类比 + R5 替换首跑。"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "analogy")

CORPUS = (
    "猫\t属于\t动物\n狗\t属于\t动物\n"
    "动物\t包含\t猫\n独兽\t包含\t貔貅\n"
    "甲熊\t属于\t熊类\n乙熊\t属于\t熊类\n乙熊\t会\t冬眠\n"
    "石头\t怕\t墙\n"
)


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
    with open(os.path.join(W, "c.tsv"), "w", encoding="utf-8") as f:
        f.write(CORPUS)
    base = "::ingest c.tsv\n"
    checks = []

    out = run(base + "::analogy 猫 动物 狗\n::quit\n")
    checks.append(("同关系类比 猫:动物::狗⇒动物", "狗 : 动物" in out and "属于" in out))

    out = run(base + "::analogy 动物 猫 独兽\n::quit\n")
    checks.append(("逆关系规范化：包含→反向 属于 ⇒ 貔貅",
                   "独兽 : 貔貅" in out and "反向" in out))

    out = run(base + "::analogy 猫 动物 石头\n::quit\n")
    checks.append(("C 无同关系边 ⇒ 未知（不猜）", "未知" in out))

    out = run(base + "::analogy 石头 动物 狗\n::quit\n")
    checks.append(("A→B 无边 ⇒ 未知（不猜）", "没有关系边" in out and "未知" in out))

    out = run(base + "甲熊 会 冬眠 吗\n::quit\n")
    checks.append(("R5 用路径相似做类比（甲熊 ≈ 乙熊）",
                   "AI >" in out and ("推测" in out or "像" in out) and "类比" in out))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("sim_mode=emb\n")
    out = run(base + "::analogy 猫 动物 狗\n::quit\n")
    checks.append(("sim_mode=emb 不影响路径类比（无稠密依赖）",
                   "狗 : 动物" in out))
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(orig)

    o1 = run(base + "::analogy 猫 动物 狗\n::quit\n")
    o2 = run(base + "::analogy 猫 动物 狗\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 路径类比/R5 首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
