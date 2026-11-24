#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""unsolved_blind.py — §7.029 未解问题作为注意力来源 首跑

4 项：
  ① 没答上来的问题会写 `_t/unsolved.tsv`，`::unsolved` 看得到；
  ② 下一轮 `::att` 里出现「来源 未解」的主题；
  ③ `::study next` 会优先“未解主题”那道题（哪怕别的题先入队）；
  ④ 正常答对的问题**不**新增未解记录。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "unsolved")


def fresh():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))


def run(inp, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120, env=e)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    checks = []
    fresh()
    out = run("犰狳 属于 动物 吗\n::unsolved\n::quit\n")
    checks.append(("未解问题写进列表", "犰狳" in out and "共显示 1 条" in out))
    out2 = run("犰狳 属于 动物 吗\n猫 属于 动物 吗\n::att\n::quit\n")
    checks.append(("下一轮注意力来源标「未解」", "来源 未解" in out2))
    fresh()
    out3 = run("犰狳 属于 动物 吗\n::study pose 猫 会 飞 吗\n::study pose 犰狳 属于 动物 吗\n::study next\n::quit\n")
    last = out3.split("下一题")[-1] if "下一题" in out3 else ""
    checks.append(("自学取题优先未解主题", "犰" in last or "犰狳" in last))
    fresh()
    out4 = run("猫 属于 动物 吗\n::unsolved\n::quit\n")
    checks.append(("答对的问题不记未解", "还没有记录" in out4))
    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 未解注意力首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
