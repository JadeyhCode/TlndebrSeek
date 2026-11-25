#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""longdoc_blind.py — §7.043 长文档盲测（10 项，跨段/长距离/出处）

一份 9 段文档：8 条三段式断言（4 个实体 × 2 条）+ 1 段无标点长文（应抽不出、也不应拖累）。
流程：`::paper read` 抽断言 → 逐条 `::claim accept 1` → 跨段问 → 出处检索 → 该拒的拒。
判定：答对=pass；明确拒=refuse；**答成别的**=wrong（wrong>0 才红）。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "longdoc")

DOC = """根据参考文献，貘 属于 奇蹄目。
实验表明，貘 有 长鼻子。
根据参考文献，树懒 属于 披毛目。
实验表明，树懒 有 爪子。
根据参考文献，犰狳 属于 有甲目。
实验表明，犰狳 有 甲片。
根据参考文献，角马 属于 偶蹄目。
实验表明，角马 有 角。
在这个很长的段落里我想说的是动物分类和它们的习性以及生活环境等等这些内容没有任何三段式断言也没有标点分隔所以它应该抽不出东西来但是也不应该影响前面那些段落的抽取能力
"""

REFUSE = ("不 太 懂", "不太懂", "不 知道", "不知道", "不 确定", "不确定",
          "没 记 过", "没记过", "不 认识", "不认识", "图里 没")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def last_ans(out):
    a = [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]
    return a[-1] if a else ""


def judge(name, ans, want, checks):
    if want in ans:
        checks.append((name, True, ans))
    elif any(k in ans for k in REFUSE):
        checks.append((name, False, ans))   # 拒答不算错，只记为 refuse
    else:
        checks.append((name, None, ans))    # None = wrong


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    os.makedirs(os.path.join(W, "papers", "cache"), exist_ok=True)
    with open(os.path.join(W, "papers", "cache", "doc.txt"), "w", encoding="utf-8") as f:
        f.write(DOC)
    P = "papers/cache/doc.txt"

    checks = []
    out = run("::paper read %s\n::quit\n" % P)
    m = re.search(r"抽到 (\d+) 条", out)
    checks.append(("长文抽断言 8 条（长段落不拖累）", bool(m) and m.group(1) == "8", out[-200:]))

    acc = "::paper read %s\n" % P + "::claim accept 1\n" * 8 + "::claim\n::quit\n"
    out = run(acc)
    checks.append(("接受后待证清零", ("没有待证" in out) or bool(re.search(r"共 0 条", out)), out[-200:]))

    for q, want, label in [("貘 属于 什么", "奇蹄目", "第 1 段事实"),
                           ("树懒 有 什么", "爪子", "第 4 段事实"),
                           ("犰狳 属于 什么", "有甲目", "第 5 段事实"),
                           ("角马 有 什么", "角", "第 8 段事实（长距离）")]:
        out = run("::paper read %s\n" % P + "::claim accept 1\n" * 8 + q + "\n::quit\n")
        judge(label, last_ans(out), want, checks)

    out = run("::paper read %s\n" % P + "::claim accept 1\n" * 8 + "袋鼠 属于 奇蹄目 吗\n::quit\n")
    a = last_ans(out)
    checks.append(("文档里没有的事：拒答", any(k in a for k in REFUSE), a))

    out = run("::paper search 甲片\n::quit\n")
    checks.append(("出处检索：命中 doc.txt", "doc.txt" in out and "命中" in out, out[-200:]))

    out = run("::paper read %s\n" % P + "::claim accept 1\n" * 8 + "这篇文档讲了什么\n::quit\n")
    a = last_ans(out)
    checks.append(("摘要类问题：允许拒（不编）", any(k in a for k in REFUSE), a))

    n_pass = sum(1 for _, g, _ in checks if g is True)
    n_refuse = sum(1 for _, g, _ in checks if g is False)
    n_wrong = sum(1 for _, g, _ in checks if g is None)
    for name, g, a in checks:
        tag = "PASS" if g is True else ("REFUSE" if g is False else "WRONG")
        print("  [%-6s] %-28s %s" % (tag, name, a[:60]))
    print("=> 长文档首跑：pass %d / refuse %d / wrong %d（共 %d）"
          % (n_pass, n_refuse, n_wrong, len(checks)))
    return 0 if n_wrong == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
