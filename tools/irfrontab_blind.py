#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irfrontab_blind.py — §7.104 进程内 IR A/B（临时脑）首跑。"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "irfrontab")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=240)
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
    with open(os.path.join(W, "ab.txt"), "w", encoding="utf-8") as f:
        f.write("猫 属于 动物 吗\n猫 是 动物 吗\n猫 不 属于 植物 吗\n"
                "今天 天气 很 好\n::rel 猫\n")
    with open(os.path.join(W, "ab50.txt"), "w", encoding="utf-8") as f:
        for i in range(50):
            f.write("猫 %s 动物 吗\n" % ("是" if i % 10 == 0 else "属于"))
    checks = []

    out = run("::irfront ab ab.txt\n::quit\n")
    checks.append(("4 句比较、1 条命令跳过、0 差异",
                   "比较 4 句（跳过命令 1）：差异 0 句" in out))
    led = os.path.join(W, "_t", "ir_front_ab.tsv")
    rows = open(led, encoding="utf-8").read().splitlines() if os.path.isfile(led) else []
    checks.append(("账本 4 行", len(rows) == 4))
    checks.append(("别名句：原文是、规范文本属于、两侧一致",
                   any("猫 是 动物 吗" in r and "猫 属于 动物 吗" in r and "一致" in r for r in rows)))
    checks.append(("UNKNOWN 透传（今天天气）",
                   any("今天 天气 很 好" in r and "一致" in r for r in rows)))

    out = run("::rel 猫\n::irfront ab ab.txt\n::rel 猫\n::quit\n")
    rels = [l for l in out.splitlines() if "猫 --[" in l]
    checks.append(("临时脑不污染主脑（前后 ::rel 猫 一致）",
                   len(rels) >= 2 and rels[:len(rels)//2] == rels[len(rels)//2:]))

    out = run("::irfront ab 不存在.txt\n::quit\n")
    checks.append(("缺文件给出用法错误", "打不开文件" in out))

    out = run("::irfront ab ab50.txt\n::quit\n")
    checks.append(("50 句批：比较 50、0 差异",
                   "比较 50 句" in out and "差异 0 句" in out))

    o1 = run("::irfront ab ab.txt\n::quit\n")
    o2 = run("::irfront ab ab.txt\n::quit\n")
    # 临时脑耗时是墙钟读数，会波动；只比较“比较/差异/账本”这些结构字段
    def stable(s):
        s = re.sub(r"耗时 [0-9.]+s / [0-9.]+s", "耗时 <clock>", s)
        return s
    checks.append(("读数确定（两次一致，忽略墙钟）", stable(o1) == stable(o2)))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 进程内 IR A/B 首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
