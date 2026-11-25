#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""symgen_blind.py — §7.045 符号组合泛化（D13 泛化半）首跑

教一个小族（3 条事实）后问 8 项：
  ① 直接事实；② 传递（允许拒）；③ 反向（不许说“对”）；④ 没教过的属性（拒）；
  ⑤ 没教过的关系（拒）；⑥ 没教过的实体+关系（拒）；⑦ 空实体问属性（拒）；⑧ 重复确认。
判定：答对=pass；明确拒/不确定=refuse；**把没教的肯定成“对”**=wrong（wrong>0 才红）。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "symgen")
TEACH = ["我教你，貘 属于 奇蹄目", "我教你，奇蹄目 属于 哺乳纲", "我教你，貘 有 长鼻子"]
REFUSE = ("不 太 懂", "不太懂", "不 知道", "不知道", "不 确定", "不确定",
          "没 记 过", "没记过", "不 认识", "不认识", "图里 没", "应该", "大概")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def last(out):
    a = [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]
    return a[-1] if a else ""


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))

    checks = []
    setup = "\n".join(TEACH) + "\n"

    out = run(setup + "貘 属于 什么\n::quit\n")
    checks.append(("直接事实", "奇蹄目" in last(out), last(out)))

    out = run(setup + "貘 属于 哺乳纲 吗\n::quit\n")
    a = last(out)
    checks.append(("传递（答出或拒都行）", "哺乳纲" in a or any(k in a for k in REFUSE), a))

    out = run(setup + "奇蹄目 属于 貘 吗\n::quit\n")
    a = last(out)
    said_yes = ("对" in a) and ("不 对" not in a) and ("不对" not in a)
    checks.append(("反向不许肯定", (not said_yes), a))

    for q, name in [("貘 有 爪子 吗", "没教过的属性"),
                    ("貘 吃 什么", "没教过的关系"),
                    ("树懒 属于 奇蹄目 吗", "没教过的实体"),
                    ("奇蹄目 有 什么", "空实体问属性")]:
        out = run(setup + q + "\n::quit\n")
        a = last(out)
        said_yes = ("对" in a) and ("不 对" not in a) and ("不对" not in a)
        checks.append((name + "：不许肯定", not said_yes, a))

    out = run(setup + "貘 属于 奇蹄目 吗\n::quit\n")
    checks.append(("重复确认仍是“对”", "对" in last(out), last(out)))

    n_pass = sum(1 for _, g, _ in checks if g)
    n_wrong = len(checks) - n_pass
    for name, g, a in checks:
        print("  [%s] %-22s %s" % ("PASS" if g else "WRONG", name, a[:60]))
    print("=> 符号组合泛化首跑：pass %d / wrong %d（共 %d）" % (n_pass, n_wrong, len(checks)))
    return 0 if n_wrong == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
