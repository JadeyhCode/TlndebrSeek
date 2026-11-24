#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""english_conflict_blind.py — §7.037 英文教学：冲突可见 + 来源留痕 首跑

3 项：
  ① 教的东西和旧知识打架（fish can fly vs 鱼不会飞）⇒ 回复里说出“I also had…”；
  ② 教完后再问 ⇒ Yes（新值生效）；
  ③ 第二个冲突事实也可见（旧值被说出来）。
  （注：这个出厂模型里常识否定很多，找不到“干净无冲突”的现成事实——如实记在边界里。）
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "enconflict")


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
    out = run("fish can fly\nyes\ncan a fish fly?\n::quit\n")
    checks.append(("冲突时先问（I also had + Say yes）",
                   "I also had" in out and "Say yes" in out and "cannot fly" in out))
    checks.append(("回答 yes 后新值生效（再问 Yes）", "Yes. Fish can fly." in out))
    fresh()
    out2 = run("fish can fly\nno\ncan a fish fly?\n::quit\n")
    checks.append(("回答 no 保留旧值（再问 No）",
                   "I'll keep" in out2 and "No. Fish cannot fly." in out2))
    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 英文冲突可见首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
