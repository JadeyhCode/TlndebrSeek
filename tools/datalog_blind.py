#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""datalog_blind.py — §7.086 P3 分层否定 Datalog（NAF + 分层检查 + 深度）首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "datalog")


def run(inp, model="model.bin"):
    p = subprocess.run([BIN, "--model", model], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


BASE = ("::notepad off\n::char off\n"
        "::pred make 父 甲 乙\n::pred make 父 乙 丙\n"
        "::rule add 祖先($x,$y) :- 父($x,$y)\n"
        "::rule add 祖先($x,$z) :- 父($x,$y), 祖先($y,$z)\n")
NEG = ("::notepad off\n::char off\n"
       "::pred make 人 丁\n::pred make 人 甲\n::pred make 父 甲 乙\n"
       "::rule add 孤儿($x) :- 人($x), 不父($x,乙)\n")
CYCLE = ("::notepad off\n::char off\n::pred make 人 甲\n"
         "::rule add p($x) :- 人($x), 不q($x)\n"
         "::rule add q($x) :- 人($x), 不p($x)\n")


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt",
              "policy.txt", "relations_beh.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    checks = []

    out = run(BASE + "::prove 祖先 甲 丙\n::quit\n")
    checks.append(("递归证明：祖先(甲,丙) 成立", "祖先(甲,丙) ⇒ **成立**" in out))

    out = run(NEG + "::prove 孤儿 丁\n::quit\n")
    checks.append(("否定前提：孤儿(丁) 成立（父(丁,乙) 推不出来）",
                   "孤儿(丁) ⇒ **成立**" in out and "否定前提成立" in out))

    out = run(NEG + "::prove 孤儿 甲\n::quit\n")
    checks.append(("否定前提有正例：孤儿(甲) 推不出来（未知，不是假）",
                   "孤儿(甲) ⇒ **推不出来**" in out and "未知，不是假" in out))

    out = run(CYCLE + "::rule check\n::prove p 甲\n::quit\n")
    checks.append(("非分层否定：体检报告 + 证明报结构坏",
                   "非分层否定" in out and "结构坏了" in out and "用法" not in out))

    out = run(BASE + "::prove 祖先 甲 丁\n::quit\n")
    checks.append(("证不出来 ⇒ 未知不是假", "推不出来" in out and "未知，不是假" in out))

    base = open(os.path.join(W, "policy.txt"), encoding="utf-8").read()
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("rule_max_depth=2\n")
    out = run(BASE + "::prove 祖先 甲 丙\n::quit\n")
    checks.append(("消融：深度 2 ⇒ 两跳证明变未知", "推不出来" in out and "成立" not in out))
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(base)

    out = run(BASE + "::prove 祖先 甲 丙\n::quit\n")
    checks.append(("恢复深度后又能证出", "⇒ **成立**" in out))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 分层否定 Datalog 首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
