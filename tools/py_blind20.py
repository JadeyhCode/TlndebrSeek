#!/usr/bin/env python3
"""§6.950 Python 首跑盲测集：20 题，只走 ::code learn --py（教师没开就应拒绝，不猜）。

读数：pass / refuse / wrong。首跑（教师未配置）预期 refuse=20——这是“不乱写”的基线；
配上教师后同一集合再跑，才算 Python 能力读数。
"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
MODEL = os.path.join(ROOT, "code", "code_model.bin")
W = os.path.join(ROOT, "_t", "pyblind")

TASKS = [
    ("把一行逗号分隔的文本切分后输出字段个数", "a,b,c\n", "3"),
    ("把一行数字用空格分开后输出最大值", "3 9 2\n", "9"),
    ("把一行数字用空格分开后输出它们的和", "1 2 3 4\n", "10"),
    ("把一行英文句子翻转单词顺序输出", "hello world\n", "world hello"),
    ("判断一个整数是不是偶数，输出 yes 或 no", "4\n", "yes"),
    ("输出 1 到 n 的平方和", "3\n", "14"),
    ("统计一行文本里字母 a 出现的次数", "banana\n", "3"),
    ("把一行数字升序排序后输出", "5 1 4\n", "1 4 5"),
    ("输出一个字符串的长度", "abcd\n", "4"),
    ("判断一个字符串是不是回文，输出 yes 或 no", "level\n", "yes"),
    ("把一行数字里的负数变成 0 后输出", "-1 2 -3\n", "0 2 0"),
    ("输出两个整数的最大公约数", "12 18\n", "6"),
    ("输出 n 的阶乘", "5\n", "120"),
    ("把一行单词按长度升序排序输出", "ccc a bb\n", "a bb ccc"),
    ("输出一行文本里单词的个数", "a bb ccc\n", "3"),
    ("输出一个整数的各位数字之和", "1234\n", "10"),
    ("把一行数字去重后按原顺序输出", "1 2 1 3\n", "1 2 3"),
    ("输出斐波那契数列第 n 项", "7\n", "13"),
    ("统计一行数字里大于 5 的个数", "1 9 6 2\n", "2"),
    ("把一行数字倒序输出", "1 2 3\n", "3 2 1"),
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
