#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§6.963 新迁移集 T2（8 条，未参与调参）首跑：学 A 考 B 的组合。
只走本地 ::code synth，不联网。
"""
import os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import code_blind26 as B

T2 = [
    dict(name="最大减最小加一", shape="arr",
         desc="读入一行整数（标准输入），输出最大值减去最小值再加一。",
         gold=lambda a: max(a) - min(a) + 1),
    dict(name="排序后第二个", shape="arr",
         desc="读入一行整数（标准输入），从小到大排序后输出第二个数。",
         gold=lambda a: sorted(a)[1] if len(a) > 1 else sorted(a)[0]),
    dict(name="和除个数", shape="arr",
         desc="读入一行整数（标准输入），输出总和的平均值。",
         gold=lambda a: sum(a) // len(a)),
    dict(name="每行和减行最大", shape="matrix",
         desc="读入一个矩阵（标准输入），输出每一行的和减去该行最大值。",
         gold=lambda m: [sum(r) - max(r) for r in m]),
    dict(name="行数乘二", shape="file",
         desc="读入一个文件（命令行参数），输出行数的两倍。",
         gold=lambda t: len(t.splitlines()) * 2),
    dict(name="两数平方和", shape="two",
         desc="读入两个整数（命令行参数），输出它们的平方和。",
         gold=lambda p: p[0] * p[0] + p[1] * p[1]),
    dict(name="单词数乘二", shape="str",
         desc="读入一行文本（标准输入），输出单词个数的两倍。",
         gold=lambda s: len(s.split()) * 2),
    dict(name="去重后最小", shape="arr",
         desc="读入一行整数（标准输入），去掉重复的数之后输出最小值。",
         gold=lambda a: min(set(a))),
]

def main():
    rng = random.Random(20270101)
    cnt = dict(pass_=0, refuse=0, wrong=0)
    fam = {}
    for t in T2:
        got, _ = B.judge(t, rng)
        cnt["pass_" if got == "pass" else got] += 1
        sh = t.get("shape", "?")
        d = fam.setdefault(sh, dict(pass_=0, refuse=0, wrong=0, n=0))
        d["pass_" if got == "pass" else got] += 1
        d["n"] += 1
        print("  [%s] %-7s %s" % (got.upper(), sh, t["name"]))
    print("=> pass %d / refuse %d / wrong %d（共 %d）" %
          (cnt["pass_"], cnt["refuse"], cnt["wrong"], len(T2)))
    for sh in sorted(fam):
        d = fam[sh]
        print("   族 %-7s pass %d / refuse %d / wrong %d（共 %d）" %
              (sh, d["pass_"], d["refuse"], d["wrong"], d["n"]))
    return 0

if __name__ == "__main__":
    sys.exit(main())
