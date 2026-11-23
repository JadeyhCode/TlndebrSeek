#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper_qa_blind.py — §7.022 论文问答首跑（能答/该拒/出处对不对）

一条流程 6 个检查：
  ① `::paper read` 从 3 个三段式句子抽出 3 条待证；
  ② 待证列表的来源都是「论文」；
  ③ **未接受**前问其中一条 → 不能答“对”（待证不算知识）；
  ④ `::claim accept 1` 后同一问题 → “对”；
  ⑤ 另一条**没接受**的问 → 答“只听说过/来源论文/待证”，不冒充事实；
  ⑥ 待证剩 2 条。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "paperqa")
TEXT = ("根据参考文献，企鹅 属于 鸟类。\n"
        "实验表明，企鹅 会 游泳。\n"
        "作者认为，企鹅 会 飞。\n")


def run(inp):
    p = subprocess.run([os.path.join(W, "build_aip"), "--model", "model.bin"],
                       input=inp.encode(), capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def last_answer(out):
    rs = [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]
    return rs[-1] if rs else ""


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    with open(os.path.join(W, "p.txt"), "w", encoding="utf-8") as f:
        f.write(TEXT)

    out = run("::paper read p.txt\n::claim\n::quit\n")
    checks = []
    checks.append(("抽出 3 条待证", bool(re.search(r"抽到 3 条", out))))
    checks.append(("待证来源都标「论文」", out.count("来源：论文") >= 3))

    out2 = run("::paper read p.txt\n企鹅 属于 鸟类 吗\n::quit\n")
    a1 = last_answer(out2)
    checks.append(("未接受前不能答“对”", ("对" not in a1.split("，")[0] and "对 ，" not in a1)))

    out3 = run("::paper read p.txt\n::claim accept 1\n企鹅 属于 鸟类 吗\n::quit\n")
    a2 = last_answer(out3)
    checks.append(("接受第 1 条后答“对”", a2.startswith("对")))

    out4 = run("::paper read p.txt\n::claim accept 1\n企鹅 会 游泳 吗\n::quit\n")
    a3 = last_answer(out4)
    checks.append(("未接受的说“只听说过/来源论文/待证”",
                   ("听 说" in a3 or "听说" in a3) and "论文" in a3))

    out5 = run("::paper read p.txt\n::claim accept 1\n::claim\n::quit\n")
    checks.append(("接受后剩 2 条待证", bool(re.search(r"共 2 条", out5))))

    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    ok = sum(1 for _, g in checks if g)
    print("=> 论文问答首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
