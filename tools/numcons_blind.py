#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""numcons_blind.py — §7.110 规则数值约束（>/</=，不引函数符号）首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "numcons")
BASE = ("::notepad off\n::char off\n"
        "::pred make 人 甲\n::pred make 岁 甲 20\n"
        "::pred make 人 乙\n::pred make 岁 乙 17\n"
        "::pred make 人 丙\n::pred make 岁 丙 18\n")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


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

    out = run(BASE + "::rule add 成人($x) :- 人($x), 岁($x,$y), >($y,18)\n"
              "::prove 成人 甲\n::prove 成人 乙\n::prove 成人 丙\n::quit\n")
    checks.append(("> 成立（20 > 18）", "成人(甲) ⇒ **成立**" in out and "数值约束成立" in out))
    checks.append(("> 不成立（17 > 18）", "成人(乙) ⇒ **推不出来**" in out and "数值约束不成立" in out))
    checks.append(("边界 18 > 18 不成立", "成人(丙) ⇒ **推不出来**" in out))

    out = run(BASE + "::rule add 未成年($x) :- 人($x), 岁($x,$y), <($y,18)\n"
              "::prove 未成年 乙\n::prove 未成年 甲\n::quit\n")
    checks.append(("< 成立（17 < 18）", "未成年(乙) ⇒ **成立**" in out))
    checks.append(("< 不成立（20 < 18）", "未成年(甲) ⇒ **推不出来**" in out))

    out = run(BASE + "::rule add 十八($x) :- 人($x), 岁($x,$y), =($y,18)\n"
              "::prove 十八 丙\n::prove 十八 甲\n::quit\n")
    checks.append(("= 精确匹配（18 = 18）", "十八(丙) ⇒ **成立**" in out))
    checks.append(("= 不匹配（20 = 18）", "十八(甲) ⇒ **推不出来**" in out))

    # 头变量 $y 已绑定、约束里的 $x 未绑定 ⇒ 必须报“未绑定”，不能拿甲去比数字
    out = run(BASE + "::rule add 大($y) :- >($x,$y)\n::prove 大 甲\n::quit\n")
    checks.append(("未绑定变量 ⇒ 不算成立", "未绑定变量" in out and "**推不出来**" in out))

    out = run(BASE + "::pred make 人 丁\n::pred make 岁 丁 成年\n"
              "::rule add 成人($x) :- 人($x), 岁($x,$y), >($y,18)\n"
              "::prove 成人 丁\n::quit\n")
    checks.append(("非数字操作数 ⇒ 不算成立", "不是数字" in out and "**推不出来**" in out))

    o1 = run(BASE + "::rule add 成人($x) :- 人($x), 岁($x,$y), >($y,18)\n::prove 成人 甲\n::quit\n")
    o2 = run(BASE + "::rule add 成人($x) :- 人($x), 岁($x,$y), >($y,18)\n::prove 成人 甲\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 规则数值约束首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
