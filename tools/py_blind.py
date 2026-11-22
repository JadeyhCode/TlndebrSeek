#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""py_blind.py — §6.997 Python 20 题最小闭环首跑（离线、teacher-free）

每题三步：
  ① `::code learn --py <描述>`（**不配教师**）→ 本地 py 模板命中才接受；
  ② 接受则用随机输入跑候选，与 gold 对比（**误收** = 接受但复考不过）；
  ③ 同一描述再问一次 → 应走 teacher-free 回放（记 `reuse`）。
判分：pass（接受且复考过）/ refuse（没接受，诚实）/ wrong（接受但答错）。
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
W = os.path.join(ROOT, "_t", "pyblind")

TASKS = [
    ("求和", "读入一行整数，输出它们的和。", "arr", lambda a: str(sum(a))),
    ("最大值", "读入一行整数，输出其中的最大值。", "arr", lambda a: str(max(a))),
    ("偶数", "读入一行整数，输出其中所有的偶数。", "arr",
     lambda a: " ".join(str(x) for x in a if x % 2 == 0)),
    ("大于计数", "读入一行整数，统计有多少个数大于十。", "arr", lambda a: str(sum(1 for x in a if x > 10))),
    ("升序排序", "读入一行整数，从小到大排序后输出。", "arr", lambda a: " ".join(map(str, sorted(a)))),
    ("平方和", "读入一行整数，输出每个数的平方和。", "arr", lambda a: str(sum(x * x for x in a))),
    ("负数清零", "读入一行整数，把负数都变成零后输出。", "arr",
     lambda a: " ".join(str(x if x >= 0 else 0) for x in a)),
    ("去重保序", "读入一行整数，去掉重复的数并保持原来的顺序输出。", "arr",
     lambda a: " ".join(map(str, list(dict.fromkeys(a))))),
    ("数位和", "读入一个整数，输出它的各位数字之和。", "num", lambda n: str(sum(int(c) for c in str(n)))),
    ("数字倒序", "读入一个整数，把它的数字倒过来输出。", "num", lambda n: str(int(str(n)[::-1])) if n else "0"),
    ("阶乘", "读入一个整数 n，输出 n 的阶乘。", "small", lambda n: str(__import__("math").factorial(n))),
    ("斐波那契", "读入一个整数 n，输出斐波那契数列的第 n 项。", "small", lambda n: str(fib(n))),
    ("最大公约数", "读入两个整数，输出它们的最大公约数。", "two",
     lambda p: str(__import__("math").gcd(abs(p[0]), abs(p[1])))),
    ("回文", "读入一行字符串，判断它是不是回文（是输出 yes，否则 no）。", "str",
     lambda s: "yes" if s == s[::-1] else "no"),
    ("字符串长度", "读入一行字符串，输出它的长度。", "str", lambda s: str(len(s))),
    ("单词个数", "读入一行英文，输出单词的个数。", "str", lambda s: str(len(s.split()))),
    ("翻转单词", "读入一行英文，把单词顺序倒过来输出。", "str", lambda s: " ".join(s.split()[::-1])),
    ("字母计数", "读入一行字符串，统计其中英文字母的个数。", "str",
     lambda s: str(sum(1 for c in s if c.isalpha()))),
    ("按长度排序", "读入一行英文，按单词长度从小到大排序后输出。", "str",
     lambda s: " ".join(sorted(s.split(), key=len))),
    # 本地没有模板：期望诚实拒绝（不许编）
    ("两数商与余", "读入两个整数，输出它们的商和余数。", "two",
     lambda p: None if p[1] == 0 else "%d %d" % (int(p[0] / p[1]), p[0] % p[1])),
]

def fib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

def run_learn(desc):
    inp = "::act on\n::code learn --py %s\n::quit\n" % desc
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=240,
                       env={k: v for k, v in os.environ.items()
                            if not k.startswith("AIP_TOOL")})
    return (p.stdout + p.stderr).decode("utf-8", "replace")

def candidate(out):
    m = re.search(r"候选：(\S+)", out)
    if not m:
        return None
    c = m.group(1)
    if not os.path.isabs(c):
        c = os.path.join(W, c)
    return c if os.path.isfile(c) else None

def judge(shape, path, rng):
    if shape == "arr":
        v = [rng.randint(-9, 9) for _ in range(rng.randint(1, 6))]
    elif shape == "num":
        v = rng.randint(1, 999)
    elif shape == "small":
        v = rng.randint(0, 8)
    elif shape == "two":
        v = (rng.randint(-20, 20), rng.randint(-20, 20) or 1)
    else:
        v = " ".join(rng.choice(["ab", "ba", "a", "xyz", "cat", "dog", "e"])
                     for _ in range(rng.randint(1, 3)))
    task = next(t for t in TASKS if t[1] == path[1])
    gold = task[3](v)
    if gold is None:
        return "skip"
    if shape == "arr":
        data = " ".join(map(str, v)) + "\n"
    elif shape in ("num", "small"):
        data = "%d\n" % v
    elif shape == "two":
        data = "%d %d\n" % v
    else:
        data = v + "\n"
    try:
        p = subprocess.run(["python3", path[0]], input=data.encode(),
                           capture_output=True, timeout=5)
    except subprocess.TimeoutExpired:
        return "wrong"
    got = p.stdout.decode("utf-8", "replace").strip()
    clean = lambda s: "".join(ch for ch in s if not ch.isspace())
    return "pass" if clean(got) == clean(gold) else "wrong"

def main():
    if not os.path.isfile(MODEL):   # 干净沙箱里代码模型可能没被复制：现场建一份
        subprocess.run(["sh", "code/build_code_model.sh"], cwd=ROOT,
                       capture_output=True, timeout=900)
    if not os.path.isfile(MODEL):
        print("FAIL: 建不出 code/code_model.bin")
        return 1
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(os.path.join(W, "_t", "py"), exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(MODEL, os.path.join(W, "model.bin"))
    rng = random.Random(20261227)
    cnt = dict(pass_=0, refuse=0, wrong=0)
    reuse_hit = 0
    for name, desc, shape, _gold in TASKS:
        out = run_learn(desc)
        path = candidate(out)
        if "回放通过（teacher-free）" in out:
            reuse_hit += 1
        if not path:
            cnt["refuse"] += 1
            why = "本地没模板" if "不能瞎写" in out or "没配" in out else out.strip().splitlines()[-1][:40]
            print("  [REFUSE] %-10s %s（%s）" % (shape, name, why))
            continue
        got = judge(shape, (path, desc), rng)
        if got == "pass":
            cnt["pass_"] += 1
            out2 = run_learn(desc)
            if "回放通过（teacher-free）" in out2:
                reuse_hit += 1
            print("  [PASS]   %-10s %s" % (shape, name))
        elif got == "skip":
            cnt["refuse"] += 1
            print("  [REFUSE] %-10s %s（gold 跳过）" % (shape, name))
        else:
            cnt["wrong"] += 1
            print("  [WRONG]  %-10s %s（接受但复考不过）" % (shape, name))
    print("=> pass %d / refuse %d / wrong %d（共 %d）｜teacher-free 回放命中 %d"
          % (cnt["pass_"], cnt["refuse"], cnt["wrong"], len(TASKS), reuse_hit))
    return 1 if cnt["wrong"] > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
