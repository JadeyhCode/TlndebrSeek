#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pathsim2_blind.py — §7.091 终点类别归一 + 属性重叠（单位归一）首跑。"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "pathsim2")

CORPUS = (
    "犰狳\t属于\t独兽\n貔貅\t属于\t独兽\n"
    "犰狳\t有\t尾甲\n貔貅\t有\t尾乙\n"
    "尾甲\t属于\t身体\n尾乙\t属于\t身体\n"
    "甲属\t属性\t3米\n乙属\t属性\t300厘米\n"
    "甲属\t标甲\t丙地\n乙属\t标甲\t丙地\n"
    "丙属\t属性\t2秒\n丙属\t标乙\t丁地\n"
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

    out = run(base + "::pathsim 犰狳 貔貅\n::quit\n")
    checks.append(("终点类别归一：有→尾甲/尾乙（同类）⇒ 路径 1.00",
                   "路径 1.00" in out and "⇒ 0.70" in out))

    out = run(base + "::pathsig 犰狳\n::quit\n")
    checks.append(("路径签名显示终点类别", "[类:身体]" in out))

    out = run(base + "::pathsim 甲属 乙属\n::quit\n")
    checks.append(("属性单位归一：3米 vs 300厘米 ⇒ 属性 1.00",
                   "属性 1.00" in out and "⇒ 0.53" in out))

    out = run(base + "::pathsim 甲属 丙属\n::quit\n")
    checks.append(("不同量纲属性 ⇒ 属性 0.00（不硬配）", "属性 0.00" in out))

    out = run(base + "::pathsim 犰狳 貔貅\n::quit\n")
    checks.append(("无属性时属性分 0.00、权重显示 0.30",
                   "属性 0.00" in out and "w_attr=0.30" in out))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("sim_w_attr=0\nsim_w_path=0.5\nsim_w_nbr=0.2\n")
    out = run(base + "::pathsim 甲属 乙属\n::quit\n")
    checks.append(("消融：w_attr=0 ⇒ 属性权重消失",
                   "w_attr=0.00" in out and "⇒ 0.23" in out))
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(orig)

    o1 = run(base + "::pathsim 甲属 乙属\n::quit\n")
    o2 = run(base + "::pathsim 甲属 乙属\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 类别/属性相似首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
