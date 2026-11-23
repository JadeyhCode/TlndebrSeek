#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attention_list_blind.py — §7.018 注意力影响**列表顺序**首跑（opt-in）

4 项：
  ① att_list=1 + 读论文（提到“狗”）→ `谁 属于 动物` 里狗排第一；
  ② att_list=0（默认）→ 原样（猫第一，逐字顺序不变）；
  ③ AIP_ATT=0（注意力关）→ 即使 att_list=1 也回到猫第一；
  ④ 删 policy.txt → 回默认（猫第一）。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "attlist")
PAPER = "根据参考文献，狗属于动物。\n"


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
    with open(os.path.join(W, "p.txt"), "w", encoding="utf-8") as f:
        f.write(PAPER)


def answer(env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    inp = "::paper roles p.txt\n谁 属于 动物\n::quit\n"
    p = subprocess.run([os.path.join(W, "build_aip"), "--model", "model.bin"],
                       input=inp.encode(), capture_output=True, cwd=W, timeout=120, env=e)
    out = (p.stdout + p.stderr).decode("utf-8", "replace")
    m = re.search(r"属于 动物 的 有 ： ([^\n（]*)", out)
    if not m:
        return "?"
    return m.group(1).split("、")[0].strip()


def main():
    checks = []
    fresh("att_list=1\n")
    checks.append(("att_list=1 + 论文提到狗 ⇒ 狗第一", answer() == "狗"))
    fresh("att_list=0\n")
    checks.append(("att_list=0 ⇒ 默认顺序（猫第一）", answer() == "猫"))
    fresh("att_list=1\n")
    checks.append(("AIP_ATT=0 ⇒ 关掉注意力，回猫第一", answer(env={"AIP_ATT": "0"}) == "猫"))
    fresh(None)
    checks.append(("无 policy.txt ⇒ 默认（猫第一）", answer() == "猫"))
    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 注意力列表顺序首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
