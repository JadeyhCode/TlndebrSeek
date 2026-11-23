#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""study_eval.py — §7.012 自学闭环首跑读数：自出题（用户 pose）→ 本地自解 → 复考

10 道数组/两数题（不给例子、不调优）：每道 `::study pose <题>` + `::study run 1`。
判分：
  · 自解 = 本地合成被接受（有 verifier）；
  · **误收** = 接受了但用随机输入复考不过（比“答不出”更危险）；
  · 答不出 = 拒收/没合成出来。
读数：自解率、误收率、拒收数。
"""
import os
import random
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
MODEL = os.path.join(ROOT, "code", "code_model.bin")
W = os.path.join(ROOT, "_t", "studyeval")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import code_hidden as H


def xor(a):
    r = 0
    for x in a:
        r ^= x
    return r


TASKS = [
    ("平均向下", "写一个程序：读入一行整数（标准输入），输出它们的平均值（向下取整）。",
     lambda a: str(sum(a) // len(a))),
    ("第二大", "写一个程序：读入一行整数（标准输入），输出第二大的数。",
     lambda a: str(sorted(set(a))[-2] if len(set(a)) > 1 else max(a))),
    ("相邻差最小", "写一个程序：读入一行整数（标准输入），输出相邻两个数的差的最小值。",
     lambda a: str(min(abs(a[i + 1] - a[i]) for i in range(len(a) - 1)) if len(a) > 1 else 0)),
    ("数组gcd", "写一个程序：读入一行整数（标准输入），输出它们的最大公约数。",
     lambda a: str(__import__("math").gcd(*a))),
    ("去重后极差", "写一个程序：读入一行整数（标准输入），去掉重复的数，再输出最大值与最小值的差。",
     lambda a: str(max(set(a)) - min(set(a)))),
    ("平方和", "写一个程序：读入一行整数（标准输入），输出每个数的平方和。",
     lambda a: str(sum(x * x for x in a))),
    ("偶数筛", "写一个程序：读入一行整数（标准输入），输出其中所有偶数。",
     lambda a: " ".join(str(x) for x in a if x % 2 == 0)),
    ("奇数和", "写一个程序：读入一行整数（标准输入），输出其中所有奇数的和。",
     lambda a: str(sum(x for x in a if x % 2))),
    ("异或和", "写一个程序：读入一行整数（标准输入），输出所有数的异或和。",
     lambda a: str(xor(a))),
    ("中位（上）", "写一个程序：读入一行整数（标准输入），输出排序后中间的那个数。",
     lambda a: str(sorted(a)[len(a) // 2])),
]


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=240)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def newest_c():
    wd = os.path.join(W, "_t", "work")
    cs = [os.path.join(wd, f) for f in os.listdir(wd) if f.endswith(".c")] if os.path.isdir(wd) else []
    return max(cs, key=os.path.getmtime) if cs else None


def clean(s):
    return "".join(ch for ch in H.clean_out(s) if not ch.isspace())


def judge(path, gold, rng):
    exe = path[:-2]
    r = subprocess.run(["gcc", "-std=c11", "-O1", "-w", "-o", exe, path, "-lm"], capture_output=True)
    if r.returncode != 0:
        return "wrong"
    for _ in range(4):
        a = [rng.randint(0, 31) for _ in range(rng.randint(2, 6))]
        try:
            got = subprocess.run([exe], input=(" ".join(map(str, a)) + "\n").encode(),
                                 capture_output=True, timeout=5).stdout.decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            return "wrong"
        if clean(got) != clean(gold(a)):
            return "wrong"
    return "pass"


def main():
    if not os.path.isfile(MODEL):
        subprocess.run(["sh", "code/build_code_model.sh"], cwd=ROOT, capture_output=True, timeout=900)
    if not os.path.isfile(MODEL):
        print("FAIL: 缺 code_model.bin"); return 1
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(os.path.join(W, "_t", "work"), exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(MODEL, os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        if os.path.isfile(os.path.join(ROOT, f)):
            shutil.copy(os.path.join(ROOT, f), os.path.join(W, f))
    rng = random.Random(20261230)
    res = dict(solved=0, wrong=0, refuse=0, abstain=0)
    for name, desc, gold in TASKS:
        out = run("::study pose %s\n::study run 1\n::quit\n" % desc)
        accepted = ("求助①本地合成：成功" in out) or ("自解" in out and "待证" in out and "自检：答出了" in out)
        if not accepted:
            res["abstain"] += 1
            reason = ("演示骨架拒收" if "不读输入" in out else
                      "本地不成" if "本地合成：不成" in out else "没接受")
            print("  [REFUSE] %-8s（%s）" % (name, reason))
            continue
        p = newest_c()
        if not p:
            res["abstain"] += 1
            print("  [REFUSE] %-8s（接受了但找不到产物）" % name)
            continue
        got = judge(p, gold, rng)
        if got == "pass":
            res["solved"] += 1
            print("  [PASS]   %-8s（自解且复考过）" % name)
        else:
            res["wrong"] += 1
            print("  [WRONG]  %-8s（接受但复考不过 = **误收**）" % name)
    total = len(TASKS)
    solved_rate = 100.0 * res["solved"] / total
    wrong_rate = 100.0 * res["wrong"] / total
    print("=> 自学首跑：出题 %d｜自解 %d（%.1f%%）｜**误收 %d（%.1f%%）**｜拒收 %d"
          % (total, res["solved"], solved_rate, res["wrong"], wrong_rate, res["abstain"]))
    if res["wrong"] > 0:
        return 1
    if res["solved"] == 0:
        print("  [FAIL] 一道都没自解（概率不是 0，但至少要有一道）")
        return 1
    print("  [OK]   误收率 0（宁可拒也不收错的）；自解率 %.1f%%" % solved_rate)
    return 0


if __name__ == "__main__":
    sys.exit(main())
