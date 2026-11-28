#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""plansearch_blind.py — §7.087 P3 有界证明搜索（步数/代价/深度预算）首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "plansearch")

BASE = ("::notepad off\n::char off\n"
        "::pred make 父 甲 乙\n::pred make 父 乙 丙\n"
        "::rule add 祖先($x,$y) :- 父($x,$y)\n"
        "::rule add 祖先($x,$z) :- 父($x,$y), 祖先($y,$z)\n")
CYCLE = ("::notepad off\n::char off\n::pred make 人 甲\n"
         "::rule add p($x) :- 人($x), 不q($x)\n"
         "::rule add q($x) :- 人($x), 不p($x)\n")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def set_policy(text):
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(text)


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
    orig = open(os.path.join(W, "policy.txt"), encoding="utf-8").read()
    checks = []

    out = run(BASE + "::search 祖先(甲,丙)\n::quit\n")
    checks.append(("两跳目标成立，给出步数/代价",
                   "成立" in out and "步数" in out and "代价" in out))

    out = run(BASE + "::search 祖先(甲,丁)\n::quit\n")
    checks.append(("不可达 ⇒ 推不出来（未知，不是假）",
                   "推不出来" in out and "未知，不是假" in out))

    set_policy("search_max_steps=1\n")
    out = run(BASE + "::search 祖先(甲,丙)\n::quit\n")
    checks.append(("消融：步数上限 1 ⇒ 超出步数/代价上限", "超出步数/代价上限" in out))
    set_policy(orig)

    set_policy("search_max_cost=2\n")
    out = run(BASE + "::search 祖先(甲,丙)\n::quit\n")
    checks.append(("消融：代价上限 2 ⇒ 超限不猜", "超出步数/代价上限" in out))
    set_policy(orig)

    set_policy("rule_max_depth=2\n")
    out = run(BASE + "::search 祖先(甲,丙)\n::quit\n")
    checks.append(("深度 2 ⇒ 超出深度上限（不猜）", "超出深度上限" in out))
    set_policy(orig)

    out = run(CYCLE + "::search p(甲)\n::quit\n")
    checks.append(("非分层规则 ⇒ 结构坏了（不是用法错）",
                   "结构坏了" in out and "用法" not in out))

    out = run(BASE + "::search 祖先(甲,丙)\n::quit\n")
    checks.append(("恢复预算后仍能成立（消融可逆）",
                   "⇒ **成立**" in out and "步数" in out))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 有界证明搜索首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
