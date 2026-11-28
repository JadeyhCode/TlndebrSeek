#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pathcache_blind.py — §7.095 路径缓存/epoch 失效首跑。"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "pathcache")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def cnt(out):
    m = re.search(r"类型化路径 (\d+) 条", out)
    return int(m.group(1)) if m else -1


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
    with open(os.path.join(W, "c1.tsv"), "w", encoding="utf-8") as f:
        f.write("甲测\t标一\t乙测\n")
    with open(os.path.join(W, "c2.tsv"), "w", encoding="utf-8") as f:
        f.write("甲测\t标二\t丙测\n")
    with open(os.path.join(W, "many.tsv"), "w", encoding="utf-8") as f:
        for i in range(1, 71):
            f.write("点%d\t标丙\t目%d\n" % (i, i))
    checks = []

    out = run("::ingest c1.tsv\n::pathsig 甲测\n::pathsig 甲测\n::quit\n")
    checks.append(("同一词两次路径一致（缓存命中）", out.count("类型化路径 1 条") == 2))

    out = run("::ingest c1.tsv\n::pathsig 甲测\n::ingest c2.tsv\n::pathsig 甲测\n::quit\n")
    allc = [int(x) for x in re.findall(r"类型化路径 (\d+) 条", out)]
    checks.append(("写新边后 epoch 失效：1→2 条", allc == [1, 2]))

    out1 = run("::ingest c1.tsv\n::pathsig 甲测\n::quit\n")
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("path_cache=0\n")
    out0 = run("::ingest c1.tsv\n::pathsig 甲测\n::quit\n")
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(orig)
    checks.append(("消融 path_cache=0 与默认结果一致", cnt(out0) == cnt(out1) == 1))

    out = run("::ingest many.tsv\n::pathsig 点1\n::pathsig 点40\n::pathsig 点70\n::pathsig 点1\n::quit\n")
    checks.append(("容量淘汰后重建仍正确（70 词）", out.count("类型化路径 1 条") == 4))

    out = run("::ingest many.tsv\n::pathsig 点1\n::pathsig 点1\n::quit\n")
    checks.append(("淘汰后重复读数一致", out.count("类型化路径 1 条") == 2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 路径缓存首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
