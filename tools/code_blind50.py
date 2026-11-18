#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blind50 判官：8 道**未参与调优**的泛化基准（算法组合/转置/自由文本/文件），只量首跑。"""
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import code_search as S
import code_blind26 as B


def main():
    rng = random.Random(20261212)
    cnt = dict(pass_=0, refuse=0, wrong=0)
    for t in S.BLIND50:
        got, _out = B.judge(t, rng)
        cnt["pass_" if got == "pass" else got] += 1
        print("  [%s] %s" % (got.upper(), t["name"]))
    print("=> pass %d / refuse %d / wrong %d" % (cnt["pass_"], cnt["refuse"], cnt["wrong"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
