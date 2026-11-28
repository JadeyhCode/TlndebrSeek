#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sismigrate_blind.py — §7.109 「属于」拆分迁移（dry-run/apply/幂等/旧边双读）首跑。"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "sismigrate")
CORPUS = ("猫\t属于\t动物\n狗\t属于\t动物\n虎\t属于\t猫科\n"
          "猫\t属于\t猫科\n猫科\t属于\t动物\n")


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
    checks = []

    out = run("::ingest c.tsv\n::sismigrate\n::pred\n::quit\n")
    m = re.search(r"subclass-of (\d+) / instance-of (\d+) / unknown (\d+)", out)
    checks.append(("dry-run 给出计划（三类计数）", bool(m) and "dry-run" in out
                   and int(m.group(1)) >= 1 and int(m.group(2)) >= 1))
    checks.append(("dry-run 不写谓词事实",
                   "子类  （" not in out and "实例  （" not in out))

    out = run("::ingest c.tsv\n::sismigrate --apply\n::pred\n::quit\n")
    checks.append(("--apply 写入谓词事实",
                   "已执行" in out and "新写谓词事实" in out and "子类  （" in out and "实例  （" in out))
    checks.append(("旧「属于」边保留（双读）", "猫 --[属于]--> 动物" in run(
        "::ingest c.tsv\n::sismigrate --apply\n::rel 猫\n::quit\n")))

    out = run("::ingest c.tsv\n::sismigrate --apply\n::sismigrate --apply\n::quit\n")
    checks.append(("重复 apply 幂等（第二次新写 0）",
                   "新写谓词事实 0 条" in out and "已存在" in out))

    out = run("::ingest c.tsv\n::pred 子类\n::quit\n")
    # 未 apply 时不应该有子类谓词；命令不存在/空都应满足“没有事实”
    checks.append(("未 apply 时没有子类事实", "（没有" in out or "子类(猫科,动物)" not in out))

    o1 = run("::ingest c.tsv\n::sismigrate\n::quit\n")
    o2 = run("::ingest c.tsv\n::sismigrate\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 属于迁移首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
