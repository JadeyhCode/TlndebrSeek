#!/usr/bin/env python3
"""§6.955 Python 20 题对照集（V2）：20 题，只走 ::code learn --py（教师没开就应拒绝，不猜）。

读数：pass / refuse / wrong。首跑（教师未配置）预期 refuse=20——这是“不乱写”的基线；
配上教师后同一集合再跑，才算 Python 能力读数。
"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
MODEL = os.path.join(ROOT, "code", "code_model.bin")
W = os.path.join(ROOT, "_t", "pyblind")

TASKS = [
    ("输入一个整数，输出它的阶乘", "6\n", "720"),
    ("判断一行字符串是不是回文，是就输出 yes", "level\n", "yes"),
    ("求一个整数各位数字加起来是多少", "1234\n", "10"),
    ("把一串数字去重后按原顺序输出", "1 2 1 3\n", "1 2 3"),
    ("输出斐波那契数列第 n 项", "8\n", "21"),
    ("统计一行数字里大于 5 的个数", "1 9 6 2\n", "2"),
    ("输出一行文本里单词的个数", "a bb ccc\n", "3"),
    ("把一行数字倒序输出", "1 2 3\n", "3 2 1"),
    ("把负数都变成 0 后输出", "-1 2 -3\n", "0 2 0"),
    ("输入若干整数，输出它们的和", "2 3 5\n", "10"),
    ("输入若干整数，输出最大的一个", "4 8 1\n", "8"),
    ("输出一个字符串的长度", "hello\n", "5"),
    ("判断一个数是不是偶数，输出 yes 或 no", "7\n", "no"),
    ("把一行数字升序排序后输出", "9 2 7\n", "2 7 9"),
    ("求两个整数的最大公约数", "8 12\n", "4"),
    ("统计一行里字母 a 出现的次数", "aardvark\n", "3"),
    ("把英文句子的单词顺序反过来输出", "one two three\n", "three two one"),
    ("输入一行用逗号分隔的文本，输出字段个数", "a,b\n", "2"),
    ("输出 1 到 n 的整数和", "4\n", "10"),
    ("判断字符串正反是否一样，输出 yes 或 no", "abba\n", "yes"),
]

def run_learn(desc):
    cmd = [BIN, "--model", MODEL]
    inp = "::act on\n::code learn --py %s\n::quit\n" % desc
    return subprocess.run(cmd, input=inp, text=True, capture_output=True, cwd=W, timeout=120).stdout

def latest_candidate():
    d = os.path.join(W, "_t", "py")
    if not os.path.isdir(d):
        return None
    best = None
    for f in os.listdir(d):
        if f.startswith("cand_") and f.endswith(".py"):
            p = os.path.join(d, f)
            if best is None or os.path.getmtime(p) > os.path.getmtime(best):
                best = p
    return best

def main():
    if not os.path.isfile(BIN):
        print("缺 build_aip"); return 2
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    shutil.copy(MODEL, os.path.join(W, "model.bin"))
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    res = {"pass": 0, "refuse": 0, "wrong": 0}
    for desc, inp, exp in TASKS:
        out = run_learn(desc)
        if "接受" not in out:
            res["refuse"] += 1
            print("  [REFUSE] %s" % desc)
            continue
        cand = latest_candidate()
        if not cand:
            res["refuse"] += 1
            print("  [REFUSE] %s（接受了但没候选）" % desc)
            continue
        try:
            got = subprocess.run(["python3", cand], input=inp, text=True,
                                 capture_output=True, timeout=10).stdout.strip()
        except Exception:
            got = ""
        if got == exp.strip():
            res["pass"] += 1
            print("  [PASS] %s" % desc)
        else:
            res["wrong"] += 1
            print("  [WRONG] %s（期望 %r 实际 %r）" % (desc, exp.strip(), got))
    print("=> pass %d / refuse %d / wrong %d（共 %d）"
          % (res["pass"], res["refuse"], res["wrong"], len(TASKS)))
    return 0

if __name__ == "__main__":
    sys.exit(main())
