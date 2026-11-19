#!/usr/bin/env python3
"""§6.956 Python 20 题盲测集（V3，未参与调参）：20 题，只走 ::code learn --py（教师没开就应拒绝，不猜）。

读数：pass / refuse / wrong。首跑（教师未配置）预期 refuse=20——这是“不乱写”的基线；
配上教师后同一集合再跑，才算 Python 能力读数。
"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
MODEL = os.path.join(ROOT, "code", "code_model.bin")
W = os.path.join(ROOT, "_t", "pyblind")

TASKS = [
    ("输入一个整数，判断它是不是素数，输出 yes 或 no", "7\n", "yes"),
    ("把一个整数的数字顺序倒过来输出", "1230\n", "321"),
    ("输出一行数字的平均值（保留 2 位小数）", "1 2 3\n", "2.00"),
    ("输出一行数字里第二大的数", "5 9 3\n", "5"),
    ("输出 a 到 b 之间所有整数的和", "2 4\n", "9"),
    ("判断年份是不是闰年，输出 yes 或 no", "2024\n", "yes"),
    ("统计一行英文里元音字母的个数", "hello\n", "2"),
    ("把一行单词的首字母大写后输出", "hello world\n", "Hello World"),
    ("输出最大值的下标（从 0 开始）", "3 9 2\n", "1"),
    ("输出 1!+2!+...+n! 的和", "3\n", "9"),
    ("输出一行文本里出现次数最多的字符", "aabbb\n", "b"),
    ("把两行已排序的数字合并后输出", "1 3\n2 4\n", "1 2 3 4"),
    ("把十进制整数转成二进制输出", "5\n", "101"),
    ("摄氏温度转华氏温度，输出整数", "0\n", "32"),
    ("输入 2x3 矩阵，输出每行元素的和", "1 2 3\n4 5 6\n", "6 15"),
    ("把一句话按单词倒序输出", "a bb ccc\n", "ccc bb a"),
    ("输入一个整数，输出它的阶乘", "4\n", "24"),
    ("判断一个整数是不是回文数，输出 yes 或 no", "12321\n", "yes"),
    ("把一行数字去重后升序输出", "3 1 3 2\n", "1 2 3"),
    ("统计一行里有几个偶数", "1 2 4\n", "2"),
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
