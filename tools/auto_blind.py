#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auto_blind.py — §7.025 `::auto` 无人值守循环首跑（离线）

4 项：
  ① 队列 3 题、默认 `auto_rounds=3` ⇒ 一次跑 3 题；
  ② `auto_rounds=1` ⇒ 只跑 1 题（预算可消融）；
  ③ 空队列 ⇒ 跑 0 题，不报错；
  ④ 三道硬题全部记“答不出/自解 0”（拒答检测回归：防止把“想想/答不上”误记成自解）。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "autoloop")
QS = ["鸟 吃 石头 吗", "鸟 吃 木头 吗", "鸟 吃 玻璃 吗"]


def fresh(policy=None):
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    if policy is not None:
        with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
            f.write(policy)


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=240)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    checks = []
    fresh()
    out = run("\n".join(QS) + "\n::auto\n::quit\n")
    m = re.search(r"本次跑了 (\d+) 题", out)
    checks.append(("默认上限 3 ⇒ 跑 3 题", bool(m) and m.group(1) == "3"))
    checks.append(("拒答不误记为自解（自解 0 / 答不出 3）",
                   bool(re.search(r"自解 0（", out)) and "答不出 3" in out))
    led = os.path.join(W, "_t", "auto", "ledger.tsv")
    rows = open(led, encoding="utf-8").read().splitlines() if os.path.isfile(led) else []
    checks.append(("记账写到 ledger.tsv", len(rows) >= 1 and rows[0].split("\t")[1] == "3"))

    fresh("auto_rounds=1\n")
    out2 = run("\n".join(QS) + "\n::auto\n::quit\n")
    m2 = re.search(r"本次跑了 (\d+) 题", out2)
    checks.append(("auto_rounds=1 ⇒ 只跑 1 题", bool(m2) and m2.group(1) == "1"))

    # ⑤ 拒答词表下沉 policy：默认判“答不出”；词表砍到只剩“不太懂”后同一句变“答出了”
    fresh()
    out4 = run("鸟 吃 石头 吗\n::study run 1\n::quit\n")
    checks.append(("默认拒答词表：答不出", "自检：答不出" in out4))
    fresh("refuse_words=不太懂\n")
    out5 = run("鸟 吃 石头 吗\n::study run 1\n::quit\n")
    checks.append(("词表砍短：同一句被误判成答出了（说明检测由数据决定）",
                   "自检：答出了" in out5))

    fresh()
    out3 = run("::auto\n::quit\n")
    m3 = re.search(r"本次跑了 (\d+) 题", out3)
    checks.append(("空队列 ⇒ 跑 0 题", bool(m3) and m3.group(1) == "0"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 无人值守循环首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
