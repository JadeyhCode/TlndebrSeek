#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""relinduce_blind.py — §7.085 P3 行为归纳（trans/sym/excl 支持率 + 待证建议）首跑。"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "relinduce")
CORPUS = ("甲\t祖\t乙\n乙\t祖\t丙\n丙\t祖\t丁\n甲\t祖\t丙\n乙\t祖\t丁\n甲\t祖\t丁\n"
          "甲\t识\t乙\n乙\t识\t丙\n甲\t邻\t乙\n乙\t邻\t甲\n甲\t拥\t乙\n甲\t拥\t丙\n")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def line_for(out, name):
    for l in out.splitlines():
        if re.search(r"^\s+%s\s+边" % re.escape(name), l):
            return l
    return ""


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt",
              "policy.txt", "relations_beh.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    with open(os.path.join(W, "c.tsv"), "w", encoding="utf-8") as f:
        f.write(CORPUS)
    base = "::ingest c.tsv\n"
    checks = []

    out = run(base + "::induce 30\n::quit\n")
    z = line_for(out, "祖")
    checks.append(("传递关系：4/4 支持、建议 trans", "trans 4/4(1.00)" in z and "建议：trans" in z))
    s = line_for(out, "识")
    checks.append(("非传递：0/1 不支持 trans", "trans 0/1(0.00)" in s and "建议：trans" not in s))
    l = line_for(out, "邻")
    checks.append(("对称关系：2/2 支持、建议 sym", "sym 2/2(1.00)" in l and "建议：sym" in l))
    y = line_for(out, "拥")
    checks.append(("多值关系：有反例 ⇒ 不建议 excl", "单0/多2" in y and "建议：excl" not in y))

    out = run(base + "::induce claim 祖 trans\n::quit\n")
    checks.append(("没有写入门/理由：拒绝", "只读模式" in out or "必须给理由" in out))

    out = run(base + "::sym write on\n::sym reason 盲测归纳\n::induce claim 祖 trans\n::claim\n::quit\n")
    checks.append(("理由齐全：写成待证、来源「归纳」",
                   "已写成待证" in out and "来源：归纳" in out))

    led = os.path.join(W, "_t", "induce.tsv")
    before = len(open(led, encoding="utf-8").read().splitlines()) if os.path.isfile(led) else 0
    out = run(base + "::induce 30\n::claim\n::quit\n")
    after = len(open(led, encoding="utf-8").read().splitlines()) if os.path.isfile(led) else 0
    checks.append(("只建议不写图（待证 0、账本不增）",
                   ("没有待证" in out or "共 0 条" in out) and after == before))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("induce_min_support=10\n")
    out = run(base + "::induce 30\n::quit\n")
    checks.append(("消融：支持阈值 10 ⇒ 不再建议 trans",
                   not line_for(out, "祖") or "建议：trans" not in line_for(out, "祖")))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 行为归纳首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
