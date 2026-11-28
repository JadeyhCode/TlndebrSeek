#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pathscale_blind.py — §7.096 路径剪枝/规模 p95 首跑。"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "pathscale")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=240)
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
    with open(os.path.join(W, "c.tsv"), "w", encoding="utf-8") as f:
        f.write("犰狳\t属于\t独兽\n独兽\t有\t鳞甲\n")
        for i in range(1, 41):
            f.write("心测\t有\t叶%d\n" % i)
    with open(os.path.join(W, "c5000.tsv"), "w", encoding="utf-8") as f:
        for i in range(1, 5001):
            f.write("甲%d\t谓%c\t乙%d\n" % (i, chr(0x4e00 + (i % 20000)), i))
    checks = []

    out = run("::ingest c5000.tsv\n::pathbench 甲3999 甲3998 100\n::quit\n")
    m = re.search(r"冷 p95 (\d+) µs / 热 p95 (\d+) µs", out)
    checks.append(("4096 关系规模：冷 p95 < 5000 µs", bool(m) and int(m.group(1)) < 5000))
    checks.append(("热缓存不慢于冷缓存", bool(m) and int(m.group(2)) <= int(m.group(1))))

    out = run("::ingest c.tsv\n::pathsig 心测\n::quit\n")
    checks.append(("默认 top-32 截断 40 条边", cnt(out) == 32))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("path_topk=4\n")
    out = run("::ingest c.tsv\n::pathsig 心测\n::quit\n")
    checks.append(("消融 path_topk=4 ⇒ 4 条", cnt(out) == 4))
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(orig)

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("path_max_len=1\n")
    out = run("::ingest c.tsv\n::pathsig 犰狳\n::quit\n")
    checks.append(("消融 path_max_len=1 ⇒ 只剩 1 跳", cnt(out) == 1))
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(orig)

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("path_deg_cap=1\n")
    out = run("::ingest c.tsv\n::pathsig 心测\n::quit\n")
    checks.append(("消融 path_deg_cap=1 ⇒ 只展开 1 条边", cnt(out) == 1))
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(orig)

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("path_cache=0\n")
    out = run("::ingest c5000.tsv\n::pathbench 甲3999 甲3998 50\n::quit\n")
    checks.append(("消融 path_cache=0 ⇒ 明确标注缓存关", "缓存 关" in out))
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(orig)

    o1 = run("::ingest c.tsv\n::pathsim 犰狳 独兽\n::quit\n")
    o2 = run("::ingest c.tsv\n::pathsim 犰狳 独兽\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 路径剪枝/规模首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
