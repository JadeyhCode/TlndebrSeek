#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""generalize_eval.py — §6.924 泛化/迁移首跑读数（不联网）

两组：
  A. **同义改写**（同一道题、换一种说法）：量“换个说法还认不认得”；
  B. **组合迁移**（用已会的算子拼一个没登记过的新组合）：量“学会一个能不能用在相邻题上”。

判分复用 blind 判官那套（synth → 随机输入 → 与 gold 比），结果只报首跑。
"""
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import code_search as S
import code_blind26 as B

PARA = [
    dict(name="总和的换说法", shape="arr", desc="把这一行的整数全部加起来，输出总和。",
         gold=lambda a: sum(a)),
    dict(name="最大的换说法", shape="arr", desc="找出这一行里最大的那个数并输出。",
         gold=lambda a: max(a)),
    dict(name="排序加一的换说法", shape="arr",
         desc="先把这些数从小到大排好，再给每个数加上一，输出结果。",
         gold=lambda a: [x + 1 for x in sorted(a)]),
    dict(name="去重极差的换说法", shape="arr",
         desc="去掉重复的数字以后，输出最大值和最小值的差。",
         gold=lambda a: max(set(a)) - min(set(a))),
    dict(name="矩阵行和的换说法", shape="matrix",
         desc="对矩阵的每一行分别求和，输出这些和。",
         gold=lambda m: [sum(r) for r in m]),
    dict(name="单词数的换说法", shape="str", desc="数一数这行字里有多少个词。",
         gold=lambda s: len(s.split())),
    dict(name="和与积的换说法", shape="two",
         desc="给定两个整数，分别输出相加和相乘的结果。",
         gold=lambda p: [p[0] + p[1], p[0] * p[1]]),
    dict(name="文件行数的换说法", shape="file", desc="这个文件一共有多少行？",
         gold=lambda t: len(t.splitlines())),
]

TRANSFER = [
    dict(name="最大的平方", shape="arr", desc="读入一行整数（标准输入），输出最大值的平方。",
         gold=lambda a: max(a) ** 2),
    dict(name="和减最大", shape="arr", desc="读入一行整数（标准输入），输出总和的相反数再加上最大值。",
         gold=lambda a: -sum(a) + max(a)),
    dict(name="排序后取中", shape="arr", desc="读入一行整数（标准输入），从小到大排序后输出中间那个数。",
         gold=lambda a: sorted(a)[len(a) // 2]),
    dict(name="去重后求和", shape="arr", desc="读入一行整数（标准输入），去掉重复的数之后输出它们的和。",
         gold=lambda a: sum(set(a))),
    dict(name="矩阵行最大", shape="matrix", desc="读入一个矩阵（标准输入），输出每一行中最大的数。",
         gold=lambda m: [max(r) for r in m]),
    dict(name="词数减行数", shape="file", desc="读入一个文件（命令行参数），输出单词个数减去行数。",
         gold=lambda t: len(t.split()) - len(t.splitlines())),
    dict(name="两数商与余", shape="two", desc="读入两个整数（命令行参数），输出它们的商和余数。",
         gold=lambda p: None if p[1] == 0 else [int(p[0] / p[1]), p[0] % p[1]]),
    dict(name="最大加最小", shape="arr", desc="读入一行整数（标准输入），输出最大值与最小值的和。",
         gold=lambda a: max(a) + min(a)),
]


def run_group(name, tasks, rng):
    cnt = dict(pass_=0, refuse=0, wrong=0)
    fam = {}
    print("== %s ==" % name)
    for t in tasks:
        got, _ = B.judge(t, rng)
        cnt["pass_" if got == "pass" else got] += 1
        sh = t.get("shape", "?")
        d = fam.setdefault(sh, dict(pass_=0, refuse=0, wrong=0, n=0))
        d["pass_" if got == "pass" else got] += 1
        d["n"] += 1
        print("  [%s] %-12s %s" % (got.upper(), sh, t["name"]))
    print("=> pass %d / refuse %d / wrong %d（共 %d）" %
          (cnt["pass_"], cnt["refuse"], cnt["wrong"], len(tasks)))
    for sh in sorted(fam):
        d = fam[sh]
        print("   族 %-7s pass %d / refuse %d / wrong %d（共 %d）" %
              (sh, d["pass_"], d["refuse"], d["wrong"], d["n"]))
    return cnt


def main():
    rng = random.Random(20261226)
    a = run_group("A 同义改写（同一道题换说法）", PARA, rng)
    b = run_group("B 组合迁移（没登记过的新组合）", TRANSFER, rng)
    print("=> 首跑汇总：改写 %d/%d ｜ 迁移 %d/%d" %
          (a["pass_"], len(PARA), b["pass_"], len(TRANSFER)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
