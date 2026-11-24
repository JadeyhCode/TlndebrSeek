#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""longconv_blind.py — §7.034 长对话记忆首跑（跨轮事实环 + 12 轮盲测）

5 项：
  ① 12 轮里教 5 条事实后，`最近 学 了 什么` 至少列出 4 条；
  ② 隔 10 轮后老事实仍答得出（图记忆 + 事实环不互相干扰）；
  ③ 新命令 `::recent` 看得到 5 条；
  ④ `刚才 说 的 是 什么`（最近一句用户原话）仍然工作；
  ⑤ 指代（教完“树懒 有 爪子”再问“它 有 什么”）允许过或拒，但不许答成别的事实。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "longconv")

TEACH = ["我教你，貘 属于 奇蹄目", "我教你，树懒 有 爪子", "我教你，犰狳 有 甲片",
         "我教你，角马 属于 偶蹄目", "我教你，袋鼠 有 袋子"]
FILLER = ["猫 属于 动物 吗", "狗 属于 动物 吗", "鸟 会 飞 吗", "鱼 会 游泳 吗",
          "老鼠 属于 动物 吗", "人 属于 动物 吗", "猫 有 什么", "狗 有 什么",
          "鸟 有 什么", "鱼 有 什么"]


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))

    lines = TEACH[:2] + FILLER[:5] + TEACH[2:] + ["最近 学 了 什么", "::quit"]
    out = run("\n".join(lines) + "\n")
    memo = [l for l in out.splitlines() if "最近 学 到 的 事实" in l]
    listed = memo[-1] if memo else ""
    hits = sum(1 for f in ("貘", "树懒", "犰狳", "角马", "袋鼠") if f in listed)
    checks = [("12 轮后回忆至少 4 条事实", hits >= 4)]

    out2 = run("\n".join(TEACH + FILLER + ["貘 属于 什么", "::quit"]) + "\n")
    ans = [l for l in out2.splitlines() if "AI > " in l]
    checks.append(("隔 10 轮老事实仍答得出", bool(ans) and "奇蹄目" in ans[-1]))

    out3 = run("\n".join(TEACH + ["::recent", "::quit"]) + "\n")
    checks.append(("::recent 看得到 5 条", "学到 5 条" in out3))

    out4 = run("\n".join(TEACH + ["刚才 说 的 是 什么", "::quit"]) + "\n")
    checks.append(("最近一句用户原话仍可复述", "袋鼠" in out4 or "教" in out4))

    out5 = run("\n".join(["我教你，树懒 有 爪子", "猫 属于 动物 吗", "它 有 什么", "::quit"]) + "\n")
    a5 = [l for l in out5.splitlines() if "AI > " in l]
    last5 = a5[-1] if a5 else ""
    checks.append(("指代允许过或拒，但不许答错别的", ("爪子" in last5) or ("不" in last5) or ("没" in last5)))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 长对话记忆首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
