#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pronoun_blind.py — §7.040 多轮指代首跑（最近主语环，问句主语不回指）

5 项：
  ① 陈述后紧跟“他/它” → 指回陈述主语；
  ② 陈述 → 问句（另一主语）→ “他…” → 仍指陈述主语（这轮修的点）；
  ③ 两个陈述 → “它” → 最近那个陈述主语；
  ④ 陈述 → “它 属于 什么”（该事实没有）→ 允许拒，但不许答成别的主语；
  ⑤ 没有任何陈述就“他…” → 允许拒，不许崩。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "pronoun")

REFUSE = ("不 知道", "不知道", "不 太 懂", "不太懂", "没 记 过", "没记过",
          "不 认识", "不认识", "不 确定", "不确定", "图里 没")


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


def last_ans(out):
    a = [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]
    return a[-1] if a else ""


def main():
    checks = []
    fresh()
    out = run("我教你，小明 喜欢 游泳\n他 喜欢 什么\n::quit\n")
    checks.append(("紧跟指代 → 小明/游泳", "游泳" in last_ans(out)))

    fresh()
    out2 = run("我教你，小明 喜欢 游泳\n猫 属于 动物 吗\n他 喜欢 什么\n::quit\n")
    checks.append(("隔一个问句仍指陈述主语 → 游泳", "游泳" in last_ans(out2)))

    fresh()
    out3 = run("我教你，貘 属于 奇蹄目\n我教你，树懒 有 爪子\n它 有 什么\n::quit\n")
    checks.append(("两个陈述 → 它指最近陈述 → 爪子", "爪子" in last_ans(out3)))

    fresh()
    out4 = run("我教你，袋鼠 有 袋子\n它 属于 什么\n::quit\n")
    a4 = last_ans(out4)
    checks.append(("没有的事允许拒，但不答错主语",
                   ("属于" in a4 and ("袋鼠" in a4 or any(k in a4 for k in REFUSE))) or any(k in a4 for k in REFUSE)))

    fresh()
    out5 = run("他 喜欢 什么\n::quit\n")
    checks.append(("没有先行词不崩（拒或问清楚）", bool(last_ans(out5))))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 多轮指代首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
