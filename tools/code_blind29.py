#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blind29 判官：8 道全新族外题（没参与过 26–28 的调优），量 C 管线首跑。"""
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import code_search as S
import code_blind26 as B


def main():
    rng = random.Random(20261120)
    cnt = dict(pass_=0, refuse=0, wrong=0)
    for t in S.BLIND29:
        got, out = B.judge(t, rng)
        cnt["pass_" if got == "pass" else got] += 1
        print("  [%s] %s" % (got.upper(), t["name"]))
    print("=> pass %d / refuse %d / wrong %d" % (cnt["pass_"], cnt["refuse"], cnt["wrong"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
