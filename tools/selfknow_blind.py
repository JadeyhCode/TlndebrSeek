#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selfknow_blind.py — §7.044 自我符号认识（D13）首跑

5 项：
  ① `::know self` 报规模/规则计数；
  ② `::know relations` 列出核心关系及边数（属于>0）；
  ③ `::know symbol 猫` 有度、有至少一条关系边；
  ④ 不存在的符号 ⇒ 明说没有；
  ⑤ 代码脑上 `::know rules` 能列出校验规则（>0）。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "selfknow")


def run(inp, model="model.bin"):
    p = subprocess.run([BIN, "--model", model], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
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
    cm = os.path.join(ROOT, "code", "code_model.bin")
    if not os.path.isfile(cm):
        subprocess.run(["sh", "code/build_code_model.sh"], cwd=ROOT, capture_output=True, timeout=900)
    if os.path.isfile(cm):
        shutil.copy(cm, os.path.join(W, "cm.bin"))

    checks = []
    out = run("::know self\n::quit\n")
    checks.append(("self 报规模/规则计数", "[自我] 符号" in out and "校验规则" in out and "改写规则" in out))

    out = run("::know relations\n::quit\n")
    m = re.search(r"属于\s+正 (\d+)", out)
    checks.append(("relations 列出属于且正边>0", bool(m) and int(m.group(1)) > 0))

    out = run("::know symbol 猫\n::quit\n")
    m = re.search(r"符号「猫」：度 (\d+)（关系边 (\d+)）", out)
    checks.append(("symbol 猫 有度有边", bool(m) and int(m.group(1)) > 0 and int(m.group(2)) > 0))

    out = run("::know symbol 不存在的符号XYZ\n::quit\n")
    checks.append(("未知符号明说没有", "图里没有" in out))

    out = run("::know rules\n::quit\n", model="cm.bin")
    m = re.search(r"共 校验 (\d+) 条", out)
    checks.append(("代码脑 rules 有校验规则", bool(m) and int(m.group(1)) > 0))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 自我符号认识首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
