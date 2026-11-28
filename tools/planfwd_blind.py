#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""planfwd_blind.py — §7.111 P3 有界前向状态空间规划器首跑。"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "planfwd")
BASE = ("::notepad off\n::char off\n"
        "::pred make 父 甲 乙\n::pred make 父 乙 丙\n"
        "::rule add 祖先($x,$y) :- 父($x,$y)\n"
        "::rule add 祖先($x,$z) :- 父($x,$y), 祖先($y,$z)\n")
NUM = ("::notepad off\n::char off\n"
       "::pred make 人 甲\n::pred make 岁 甲 20\n"
       "::rule add 成人($x) :- 人($x), 岁($x,$y), >($y,18)\n")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def set_policy(extra):
    txt = open(os.path.join(ROOT, "policy.txt"), encoding="utf-8").read()
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n" + extra + "\n")


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt",
              "policy.txt", "relations_beh.txt", "dims.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    checks = []

    out = run(BASE + "::planfwd 祖先(甲,丙)\n::quit\n")
    checks.append(("两跳可达", "**可达**" in out and "祖先(甲,丙)" in out))
    checks.append(("路径含两条前提与两步规则",
                   "父(甲,乙)+祖先(乙,丙)" in out and "R1" in out and "R2" in out))
    checks.append(("路径深度 2", "深度 2" in out))

    out = run(BASE + "::planfwd 祖先(甲,丁)\n::quit\n")
    checks.append(("不可达 ⇒ 未知不是假", "不可达（未知，不是假）" in out))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(open(os.path.join(ROOT, "policy.txt"), encoding="utf-8").read()
                + "\nplanfwd_max_depth=1\n")
    out = run(BASE + "::planfwd 祖先(甲,丙)\n::quit\n")
    checks.append(("深度 1 消融 ⇒ 预算/深度截断", "超出深度/代价/步数预算" in out))
    set_policy("")

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(open(os.path.join(ROOT, "policy.txt"), encoding="utf-8").read()
                + "\nplanfwd_max_cost=2\n")
    out = run(BASE + "::planfwd 祖先(甲,丙)\n::quit\n")
    checks.append(("代价 2 消融 ⇒ 预算截断", "超出深度/代价/步数预算" in out))
    set_policy("")

    out = run(NUM + "::planfwd 成人(甲)\n::quit\n")
    checks.append(("数值约束规则可前向展开", "**可达**" in out and "成人(甲)" in out))

    out = run(BASE + "::rule add 孤儿($x) :- 人($x), 不父($x,乙)\n"
              "::pred make 人 丁\n::planfwd 孤儿(丁)\n::quit\n")
    checks.append(("否定前提规则不展开（前向 NAF 非单调）", "不可达" in out or "未知" in out))

    out = run(BASE + "::pred\n::planfwd 祖先(甲,丙)\n::pred\n::quit\n")
    pl = [l for l in out.splitlines() if "条实例" in l or "共 " in l and "名字" in l]
    half = len(pl) // 2
    checks.append(("只读：规划前后谓词实例表不变",
                   half >= 1 and pl[:half] == pl[half:]))

    o1 = run(BASE + "::planfwd 祖先(甲,丙)\n::quit\n")
    o2 = run(BASE + "::planfwd 祖先(甲,丙)\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 前向规划器首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
