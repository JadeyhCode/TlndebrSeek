#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""study_str_eval.py — §7.021 自学（字符串族）首跑：自出题→本地自解→字符串属性校验

5 题：长度 / 单词个数 / 翻转单词 / 回文（是）/ 回文（否）。
判分：自解=本地合成被接受；已验证=接受了字符串族属性校验；误收=接受但复考不过。
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
W = os.path.join(ROOT, "_t", "studystr")

TASKS = [
    ("字符串长度", "写一个程序：读入一行字符串（标准输入），输出它的长度。",
     lambda s: str(len(s))),
    ("单词个数", "写一个程序：读入一行英文（标准输入），输出单词的个数。",
     lambda s: str(len(s.split()))),
    ("翻转单词", "写一个程序：读入一行英文（标准输入），把单词顺序倒过来输出。",
     lambda s: " ".join(s.split()[::-1])),
    ("回文-是", "写一个程序：读入一行字符串（标准输入），判断它是不是回文（是输出 yes，否则 no）。",
     lambda s: "yes" if s == s[::-1] else "no"),
    ("回文-否", "写一个程序：读入一行字符串（标准输入），判断它是不是回文（是输出 yes，否则 no）。",
     lambda s: "yes" if s == s[::-1] else "no"),
]
INPUTS = ["ab cd ef", "abcba", "abc", "xy z", "q"]


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=240)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def newest_c():
    wd = os.path.join(W, "_t", "work")
    cs = [os.path.join(wd, f) for f in os.listdir(wd) if f.endswith(".c")] if os.path.isdir(wd) else []
    return max(cs, key=os.path.getmtime) if cs else None


def clean(s):
    z = "".join(ch for ch in s if not ch.isspace())
    if z.endswith("ok"):
        z = z[:-2]
    elif z.endswith("FAIL"):
        z = z[:-4]
    return z


def judge(path, gold, idx):
    exe = path[:-2]
    r = subprocess.run(["gcc", "-std=c11", "-O1", "-w", "-o", exe, path, "-lm"], capture_output=True)
    if r.returncode != 0:
        return "wrong"
    s = INPUTS[idx % len(INPUTS)]
    want = clean(gold(s))
    try:
        got = subprocess.run([exe], input=(s + "\n").encode(), capture_output=True,
                             timeout=5).stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return "wrong"
    return "pass" if clean(got) == want else "wrong"


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
    res = dict(solved=0, wrong=0, abstain=0, v=0, u=0, vw=0, uw=0)
    for i, (name, desc, gold) in enumerate(TASKS):
        out = run("::study pose %s\n::study run 1\n::quit\n" % desc)
        acc = next((l for l in out.splitlines() if "求助①本地合成：成功" in l), "")
        accepted = bool(acc) or ("自检：答出了" in out and "待证" in out)
        verified = ("性质「" in acc and "通过" in acc)
        if not accepted:
            res["abstain"] += 1
            print("  [REFUSE] %-8s" % name)
            continue
        p = newest_c()
        got = judge(p, gold, i) if p else "wrong"
        if got == "pass":
            res["solved"] += 1
            res["v" if verified else "u"] += 1
            print("  [PASS]   %-8s（%s）" % (name, "已验证" if verified else "未验证"))
        else:
            res["wrong"] += 1
            res["vw" if verified else "uw"] += 1
            print("  [WRONG]  %-8s（误收；%s）" % (name, "已验证" if verified else "未验证"))
    n = len(TASKS)
    print("=> 字符串族自学：出题 %d｜自解 %d（已验证 %d / 未验证 %d）｜误收 %d（已验证 %d / 未验证 %d）｜拒 %d"
          % (n, res["solved"], res["v"], res["u"], res["wrong"], res["vw"], res["uw"], res["abstain"]))
    if res["vw"] > 0:
        print("  [FAIL] 已验证误收"); return 1
    if res["solved"] == 0:
        print("  [FAIL] 一道都没自解"); return 1
    print("  [OK]   已验证误收 0（字符串族）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
