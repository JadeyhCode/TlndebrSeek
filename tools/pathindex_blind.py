#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pathindex_blind.py — §7.112 倒排路径索引（build/stats/epoch 失效/回退）首跑。"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "pathindex")
CORPUS = ("犰狳\t属于\t独兽\n独兽\t有\t鳞甲\n河马\t属于\t河马科\n河马科\t有\t皮脂\n"
          "猫\t属于\t动物\n狗\t属于\t动物\n")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=240)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def set_policy(extra):
    txt = open(os.path.join(ROOT, "policy.txt"), encoding="utf-8").read()
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n" + extra + "\n")


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
    checks = []

    out = run("::ingest c.tsv\n::pathindex build\n::pathindex stats\n::quit\n")
    m = re.search(r"建好：(\d+) 条", out)
    checks.append(("build 产出条目", bool(m) and int(m.group(1)) > 0))
    checks.append(("stats 显示有效与开关", "有效" in out and "path_index=1" in out))

    out = run("::ingest c.tsv\n::pathindex build\n::analogy 犰狳 鳞甲 河马\n::quit\n")
    checks.append(("索引命中：犰狳:鳞甲::河马⇒皮脂", "河马 : 皮脂" in out and "索引路径" in out))

    out = run("::ingest c.tsv\n::pathindex build\n::ingest c.tsv\n::pathindex stats\n::quit\n")
    checks.append(("再写边后 epoch 失效", "未建/已失效" in out))

    out = run("::ingest c.tsv\n::pathindex build\n::ingest c.tsv\n::analogy 犰狳 鳞甲 河马\n::quit\n")
    checks.append(("失效后回退枚举仍答对", "河马 : 皮脂" in out and "索引路径" not in out))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(open(os.path.join(ROOT, "policy.txt"), encoding="utf-8").read()
                + "\npath_index=0\n")
    out = run("::ingest c.tsv\n::pathindex build\n::pathindex stats\n::analogy 犰狳 鳞甲 河马\n::quit\n")
    checks.append(("消融 path_index=0：stats 标 0，类比走枚举",
                   "path_index=0" in out and "河马 : 皮脂" in out and "索引路径" not in out))
    set_policy("")

    out = run("::ingest c.tsv\n::pathindex build\n::pathindex clear\n::pathindex stats\n::quit\n")
    checks.append(("clear 后条目 0", "条目 0" in out))

    o1 = run("::ingest c.tsv\n::pathindex build\n::analogy 犰狳 鳞甲 河马\n::quit\n")
    o2 = run("::ingest c.tsv\n::pathindex build\n::analogy 犰狳 鳞甲 河马\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 倒排路径索引首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
