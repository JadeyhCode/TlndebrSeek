#!/usr/bin/env python3
"""§6.954 Python 迁移集 T2：同一批能力换说法（学 A 考 B），只走本地模板/回放。

读数：pass / refuse / wrong。首跑（教师未配置）预期 refuse=20——这是“不乱写”的基线；
配上教师后同一集合再跑，才算 Python 能力读数。
"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
MODEL = os.path.join(ROOT, "code", "code_model.bin")
W = os.path.join(ROOT, "_t", "pyblind")

TASKS = [
    ("把空格分开的各个整数累加，输出结果", "1 2 3 4\n", "10"),
    ("输出这串数字里哪一个是最大的", "3 9 2\n", "9"),
    ("把一行数字加总后打印", "4 5\n", "9"),
    ("倒着排列句子中的单词", "hello world\n", "world hello"),
    ("这个数除以 2 余数为 0 就输出 yes，否则输出 no", "4\n", "yes"),
    ("把输入的数字按升序排好打印", "5 1 4\n", "1 4 5"),
    ("这段文本一共有多少个字符", "abcd\n", "4"),
    ("求两个数的最大公因数", "12 18\n", "6"),
    ("统计文本中字母 a 的数量", "banana\n", "3"),
    ("输入一串整数，输出最大的数", "1 7 3\n", "7"),
    ("把单词收拾一下，从后往前输出", "aa bb\n", "bb aa"),
    ("两个整数相除的余数", "7 3\n", "1"),
    ("把一句话按空格切开，打印切成了几块", "a b c\n", "3"),
    ("统计一行里有几个单词", "a bb ccc\n", "3"),
    ("把数字串里小于 0 的数换成 0 再输出", "-1 2\n", "0 2"),
    ("求 1 到 n 的所有整数和", "3\n", "6"),
    ("求一个整数各个数字的和", "1234\n", "10"),
    ("判断一个字符串正着反着是否一样", "level\n", "yes"),
    ("按字典序给单词排序", "c a b\n", "a b c"),
    ("输出 n 的阶乘", "5\n", "120"),
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
