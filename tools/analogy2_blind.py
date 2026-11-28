#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""analogy2_blind.py — §7.093 多跳路径同构类比（≤3 跳）首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "analogy2")

CORPUS = (
    "犰狳\t属于\t独兽\n独兽\t有\t鳞甲\n"
    "河马\t属于\t河马科\n河马科\t有\t皮脂\n"
    "猫\t属于\t动物\n狗\t属于\t动物\n"
    "动物\t包含\t猫\n独兽\t包含\t貔貅\n"
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
    with open(os.path.join(W, "c.tsv"), "w", encoding="utf-8") as f:
        f.write(CORPUS)
    base = "::ingest c.tsv\n"
    checks = []

    out = run(base + "::analogy 犰狳 鳞甲 河马\n::quit\n")
    checks.append(("两跳路径同构：犰狳:鳞甲::河马⇒皮脂",
                   "河马 : 皮脂" in out and "2 跳" in out))

    out = run(base + "::analogy 猫 动物 狗\n::quit\n")
    checks.append(("直边仍优先：猫:动物::狗⇒动物", "狗 : 动物" in out and "同关系 属于" in out))

    out = run(base + "::analogy 动物 猫 独兽\n::quit\n")
    checks.append(("逆关系直边：动物:猫::独兽⇒貔貅（反向）",
                   "独兽 : 貔貅" in out and "反向" in out))

    out = run(base + "::analogy 犰狳 鳞甲 石头\n::quit\n")
    checks.append(("C 没有同构路径 ⇒ 未知（不猜）", "未知" in out))

    out = run(base + "::analogy 石头 鳞甲 河马\n::quit\n")
    checks.append(("A→B 没有路径 ⇒ 未知（不猜）", "没有路径" in out and "未知" in out))

    o1 = run(base + "::analogy 犰狳 鳞甲 河马\n::quit\n")
    o2 = run(base + "::analogy 犰狳 鳞甲 河马\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 多跳路径类比首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
