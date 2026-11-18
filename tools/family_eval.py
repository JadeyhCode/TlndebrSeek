#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""family_eval.py — §6.929 族切分读数：按题型族统计 pass/refuse/wrong（固定种子，不联网）

族：算法(数组) / 矩阵 / 字符串 / 文件 / 两数。只做诊断，不做门禁。
"""
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import code_search as S
import code_blind26 as B
import generalize_eval as G


def family(t):
    d = t["desc"] + t["name"]
    if t["shape"] == "matrix":
        return "矩阵"
    if t["shape"] == "file":
        return "文件"
    if t["shape"] == "two":
        return "两数"
    if t["shape"] == "str":
        return "字符串"
    if "去重" in d or "排序" in d or "中位" in d or "递增" in d or "素" in d or "相邻" in d:
        return "算法(数组)"
    return "数组(基础)"


def main():
    rng = random.Random(20270102)
    tasks = list(S.BLIND50) + list(G.PARA) + list(G.TRANSFER)
    agg = {}
    print("== 族切分（blind50 + 同义改写 + 组合迁移，共 %d 题）==" % len(tasks))
    for t in tasks:
        fam = family(t)
        got, _ = B.judge(t, rng)
        key = "pass_" if got == "pass" else got
        a = agg.setdefault(fam, dict(pass_=0, refuse=0, wrong=0, n=0))
        a[key] += 1
        a["n"] += 1
    print("  %-10s %5s %7s %6s %6s" % ("族", "题数", "pass", "refuse", "wrong"))
    tot = dict(pass_=0, refuse=0, wrong=0, n=0)
    for fam in sorted(agg):
        a = agg[fam]
        print("  %-10s %5d %7d %7d %6d" % (fam, a["n"], a["pass_"], a["refuse"], a["wrong"]))
        for k in tot:
            tot[k] += a[k]
    print("  %-10s %5d %7d %7d %6d" % ("合计", tot["n"], tot["pass_"], tot["refuse"], tot["wrong"]))
    print("=> 首跑：pass %d / refuse %d / wrong %d（共 %d）" %
          (tot["pass_"], tot["refuse"], tot["wrong"], tot["n"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
