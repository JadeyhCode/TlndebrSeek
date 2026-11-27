#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sisplit_blind.py — §7.077 P1「属于」拆分（subclass-of / instance-of / unknown）首跑。

只读分类：类 = 至少有 N 个不同主语指向它的 属于 入边（默认 N=2，可消融）。
"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "sisplit")
CORPUS = ("甲兽\t属于\t乙类\n丙兽\t属于\t乙类\n乙类\t属于\t丁界\n"
          "戊类\t属于\t丁界\n戊\t属于\t戊类\n己\t属于\t戊类\n甲兽\t属于\t庚类\n")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def counts(out):
    m = re.search(r"共 (\d+) 条：subclass-of (\d+) / instance-of (\d+) / unknown (\d+)", out)
    return tuple(int(x) for x in m.groups()) if m else None


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

    out = run(base + "::sisplit 甲兽\n::quit\n")
    checks.append(("甲兽：1 instance + 1 unknown", counts(out) == (2, 0, 1, 1)))
    checks.append(("unknown 给出原因", "unknown（宾语没有入边/类证据）" in out))

    out = run(base + "::sisplit 乙类\n::sisplit 戊类\n::quit\n")
    checks.append(("乙类/戊类：两边都是类 ⇒ subclass-of",
                   counts(out) == (1, 1, 0, 0) and "两边都是类" in out))

    out = run(base + "::sisplit 甲兽\n::quit\n")
    checks.append(("只读：明说不改图、不产生效果账本",
                   "只读，不改图" in out and
                   not os.path.exists(os.path.join(W, "_t", "effects.tsv"))))

    out = run(base + "::sisplit 无此词\n::quit\n")
    checks.append(("未知主语：明说图里没有", "图里没有" in out))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("sisplit_min_inbound=1\n")
    out = run(base + "::sisplit 甲兽\n::quit\n")
    checks.append(("消融：阈值 1 时庚类算类（unknown→instance）",
                   counts(out) == (2, 0, 2, 0)))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    out = run(base + "::sisplit\n::quit\n")
    checks.append(("全局模式行显示阈值", "入边数 ≥ 2 才算类" in out))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 属于拆分首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
