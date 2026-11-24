#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""conflict_attn_blind.py — §7.031 冲突作为注意力来源 首跑

5 项：
  ① 学到和旧值打架的事会写 `_t/conflict.tsv`（主语/关系/新值/旧值）；
  ② `::conflict` 看得到；
  ③ 下一轮 `::att` 里主语来源标「冲突」；
  ④ 没有冲突时不写记录（`::conflict` 说还没有记录）；
  ⑤ 冲突主语在 `::study next` 里被优先（猫题压过先入队的狗题）。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "conflictattn")


def fresh():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    checks = []
    fresh()
    run("猫 属于 动物\n猫 属于 猫科\n::quit\n")
    tsv = os.path.join(W, "_t", "conflict.tsv")
    rows = open(tsv, encoding="utf-8").read().splitlines() if os.path.isfile(tsv) else []
    checks.append(("冲突写进 conflict.tsv（猫/动物/猫科）",
                   bool(rows) and "猫" in rows[0] and "动物" in rows[0] and "猫科" in rows[0]))

    out = run("猫 属于 动物\n猫 属于 猫科\n::conflict\n::quit\n")
    m = re.search(r"共显示 (\d+) 条", out)
    checks.append(("::conflict 看得到", bool(m) and int(m.group(1)) >= 1))

    out2 = run("猫 属于 动物\n猫 属于 猫科\n猫 有 什么\n::att\n::quit\n")
    checks.append(("下一轮注意力来源标「冲突」", "来源 冲突" in out2))

    fresh()
    out3 = run("猫 有 什么\n::conflict\n::quit\n")
    checks.append(("无冲突时不写记录", "还没有记录" in out3))

    fresh()
    out4 = run("猫 属于 动物\n猫 属于 猫科\n::study pose 狗 会 飞 吗\n::study pose 猫 会 飞 吗\n::study next\n::quit\n")
    last = out4.split("下一题")[-1] if "下一题" in out4 else ""
    checks.append(("自学取题优先冲突主语（猫）", "猫 会 飞 吗" in last))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 冲突注意力首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
