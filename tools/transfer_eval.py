#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""transfer_eval.py — §7.007 学 A 考 B（迁移）读数

A（教）: `code/knowledge/xor.triples` 只登记**归约算子** `异或和`；
B（考）: 若干**没教过的组合**（先加一/平方后再异或、异或和再加一/乘二）。
流程：
  ① baseline：原始 code_model.bin 跑 B（应拒/错）；
  ② 学 A：`::ingest` xor.triples → `::save` 新模型；
  ③ 迁移：用学过的模型再跑 B，判分（gold 随机输入）。
读数：baseline 对/拒/错 → 迁移后 对/拒/错；**直接题 vs 组合题**分开报。
"""
import os
import random
import re
import shutil
import subprocess
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import code_hidden as H

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
MODEL = os.path.join(ROOT, "code", "code_model.bin")
A_FILE = os.path.join(ROOT, "code", "knowledge", "xor.triples")
W = os.path.join(ROOT, "_t", "transfer")


def xor_all(a):
    r = 0
    for x in a:
        r ^= x
    return r


TASKS = [
    dict(name="直接：异或和", direct=True,
         desc="读入一行整数，输出所有数的异或和。", gold=lambda a: str(xor_all(a))),
    dict(name="组合：加一后异或", direct=False,
         desc="读入一行整数，输出每个数加一之后的异或和。",
         gold=lambda a: str(xor_all([x + 1 for x in a]))),
    dict(name="组合：平方后异或", direct=False,
         desc="读入一行整数，输出每个数平方之后的异或和。",
         gold=lambda a: str(xor_all([x * x for x in a]))),
    dict(name="组合：异或和再加一", direct=False,
         desc="读入一行整数，输出异或和再加一。", gold=lambda a: str(xor_all(a) + 1)),
    dict(name="组合：异或和再乘二", direct=False,
         desc="读入一行整数，输出异或和再乘二。", gold=lambda a: str(xor_all(a) * 2)),
]

def run(inp, model):
    p = subprocess.run([BIN, "--model", model], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=240)
    return (p.stdout + p.stderr).decode("utf-8", "replace")

def newest_c():
    wd = os.path.join(W, "_t", "work")
    cs = [os.path.join(wd, f) for f in os.listdir(wd) if f.endswith(".c")] if os.path.isdir(wd) else []
    return max(cs, key=os.path.getmtime) if cs else None

def clean(s):
    return "".join(ch for ch in H.clean_out(s) if not ch.isspace())

def check(path, task, rng):
    ins = [[rng.randint(0, 31) for _ in range(rng.randint(2, 6))] for _ in range(4)]
    exe = path[:-2]
    r = subprocess.run(["gcc", "-std=c11", "-O1", "-w", "-o", exe, path, "-lm"], capture_output=True)
    if r.returncode != 0:
        return "refuse"
    for a in ins:
        try:
            got = subprocess.run([exe], input=(" ".join(map(str, a)) + "\n").encode(),
                                 capture_output=True, timeout=5).stdout.decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            return "wrong"
        if clean(got) != clean(task["gold"](a)):
            return "wrong"
    return "pass"

def run_set(model, rng):
    res = []
    for t in TASKS:
        for f in (os.path.join(W, "_t", "work"),):
            if os.path.isdir(f):
                for x in os.listdir(f):
                    os.remove(os.path.join(f, x))
        out = run("::act on\n::code synth %s\n::quit\n" % t["desc"], model)
        p = newest_c()
        got = check(p, t, rng) if p else "refuse"
        res.append((t, got))
    return res

def summarize(tag, res):
    c = dict(pass_=0, refuse=0, wrong=0)
    for t, g in res:
        c["pass_" if g == "pass" else g] += 1
    print("%s: 对 %d / 拒 %d / 错 %d" % (tag, c["pass_"], c["refuse"], c["wrong"]))
    return c

def main():
    if not os.path.isfile(MODEL):   # 干净沙箱里代码模型没被复制：现场建
        subprocess.run(["sh", "code/build_code_model.sh"], cwd=ROOT, capture_output=True, timeout=900)
    if not os.path.isfile(MODEL) or not os.path.isfile(A_FILE):
        print("FAIL: 缺 code_model.bin 或 xor.triples")
        return 1
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(os.path.join(W, "_t", "work"), exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(MODEL, os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        if os.path.isfile(os.path.join(ROOT, f)):
            shutil.copy(os.path.join(ROOT, f), os.path.join(W, f))
    rng = random.Random(20261229)

    print("== ① baseline（未学 A） ==")
    base = run_set("model.bin", rng)
    for t, g in base:
        print("  [%s] %s" % (g.upper(), t["name"]))
    b = summarize("  baseline", base)

    print("== ② 学 A：ingest 异或和（只给归约，不给组合） ==")
    learn_model = os.path.join(W, "model_learned.bin")
    out = run("::ingest %s\n::save model_learned.bin\n::quit\n" % A_FILE, "model.bin")
    if not os.path.isfile(learn_model):
        print("FAIL: 学 A 没存出模型\n" + out[-400:])
        return 1

    print("== ③ 考 B（直接用学过的模型） ==")
    after = run_set("model_learned.bin", rng)
    for t, g in after:
        print("  [%s] %s" % (g.upper(), t["name"]))
    a = summarize("  迁移后", after)
    gain = sum(1 for (t, g0), (_, g1) in zip(base, after) if g0 != "pass" and g1 == "pass")
    direct_b = [g for t, g in base if t["direct"]]
    direct_a = [g for t, g in after if t["direct"]]
    comb_b = [g for t, g in base if not t["direct"]]
    comb_a = [g for t, g in after if not t["direct"]]
    print("=> 学 A 考 B：baseline %d/%d 对（组合 %d/%d）｜迁移后 %d/%d 对（组合 %d/%d）｜新会 %d 题"
          % (b["pass_"], len(TASKS), sum(1 for g in comb_b if g == "pass"), len(comb_b),
             a["pass_"], len(TASKS), sum(1 for g in comb_a if g == "pass"), len(comb_a), gain))
    # 判据：组合题至少过半通过，且没有“错”（错=学歪）
    if a["wrong"] > 0:
        print("  [FAIL] 迁移后出现答错"); return 1
    if sum(1 for g in comb_a if g == "pass") * 2 < len(comb_a):
        print("  [FAIL] 组合迁移通过不到一半"); return 1
    print("  [OK]   学了归约后，没教过的组合也能拼（且 0 错）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
