#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""learn_blind.py — §7.001 自学闭环读数（离线假教师，teacher-free 复用）

每题四步：
  ① baseline：`::code synth`（本地，不配教师）→ 与 gold 比（**误收** = 自测绿但语义错）；
  ② `::code learn --force`（本地自测过也请教师复核，教师用假端点）→ 记是否接受；
  ③ 接受后用随机输入与 gold 比（**误收**计数）；
  ④ 关掉教师再 `::code synth` → 应命中“本地记住的解”（teacher-free 通过率）。
判分：baseline pass/wrong/refuse；learn accepted/正确/误收；teacher-free 命中且正确。
"""
import os
import random
import re
import shutil
import socket
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
MODEL = os.path.join(ROOT, "code", "code_model.bin")
W = os.path.join(ROOT, "_t", "learnblind")

TASKS = [
    dict(name="平均值向下取整", desc="读入一行整数，输出它们的平均值（向下取整）。",
         gold=lambda a: str(sum(a) // len(a)),
         code='#include <stdio.h>\nint main(void){long x,s=0,n=0;while(scanf("%ld",&x)==1){s+=x;n++;}if(n)printf("%ld\\n",s/n);return 0;}',
         tests=["IN: 1 2 3 => OUT: 2", "IN: 4 6 => OUT: 5"]),
    dict(name="第二大（去重）", desc="读入一行整数，输出第二大的数。",
         gold=lambda a: str(sorted(set(a))[-2] if len(set(a)) > 1 else max(a)),
         code='#include <stdio.h>\nint main(void){long v[256];int n=0;while(n<256&&scanf("%ld",&v[n])==1)n++;if(!n)return 0;long mx=v[0],se=-1;int have=0;for(int i=1;i<n;i++){if(v[i]>mx){se=mx;mx=v[i];have=1;}else if(v[i]<mx&&(!have||v[i]>se)){se=v[i];have=1;}}printf("%ld\\n",have?se:mx);return 0;}',
         tests=["IN: 1 2 3 => OUT: 2", "IN: 5 5 => OUT: 5"]),
    dict(name="相邻差最小", desc="读入一行整数，输出相邻两个数的差的最小值。",
         gold=lambda a: str(min(abs(a[i+1]-a[i]) for i in range(len(a)-1)) if len(a) > 1 else 0),
         code='#include <stdio.h>\nint main(void){long v[256];int n=0;while(n<256&&scanf("%ld",&v[n])==1)n++;if(n<2){printf("0\\n");return 0;}long best=-1;for(int i=1;i<n;i++){long d=v[i]-v[i-1];if(d<0)d=-d;if(best<0||d<best)best=d;}printf("%ld\\n",best);return 0;}',
         tests=["IN: 1 5 9 => OUT: 4", "IN: 3 4 10 => OUT: 1"]),
]

def reply(task):
    return ("### CODE\n```c\n%s\n```\n### RATIONALE\n按题意逐项计算，边界单独处理。\n"
            "### TESTS\n%s\n### EVIDENCE\n本地 gcc 编译通过。\n"
            % (task["code"], "\n".join(task["tests"])))

def start_teacher(text):
    p = subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "fake_openai.py"),
                          "--port", "0", "--reply", text],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         text=True, cwd=W)
    port = None
    for _ in range(100):
        line = p.stdout.readline()
        if line:
            port = "".join(ch for ch in line if ch.isdigit())
            if port:
                break
        time.sleep(0.05)
    return p, port

def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=240)
    return (p.stdout + p.stderr).decode("utf-8", "replace")

def newest_c():
    cs = []
    for sub in ("work", "learn"):
        wd = os.path.join(W, "_t", sub)
        if os.path.isdir(wd):
            cs += [os.path.join(wd, f) for f in os.listdir(wd) if f.endswith(".c")]
    return max(cs, key=os.path.getmtime) if cs else None

def clean(s):
    return "".join(ch for ch in s if not ch.isspace())

def check(path, task, rng):
    ins = [[rng.randint(1, 99) for _ in range(rng.randint(2, 6))] for _ in range(4)]
    for a in ins:
        exe = path[:-2]
        r = subprocess.run(["gcc", "-std=c11", "-O1", "-w", "-o", exe, path, "-lm"],
                           capture_output=True)
        if r.returncode != 0:
            return "refuse"
        try:
            got = subprocess.run([exe], input=(" ".join(map(str, a)) + "\n").encode(),
                                 capture_output=True, timeout=5).stdout.decode("utf-8", "replace")
        except subprocess.TimeoutExpired:
            return "wrong"
        if clean(got) != clean(task["gold"](a)):
            return "wrong"
    return "pass"

def main():
    if not os.path.isfile(MODEL):
        subprocess.run(["sh", "code/build_code_model.sh"], cwd=ROOT, capture_output=True, timeout=900)
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(os.path.join(W, "_t", "work"), exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(MODEL, os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt"):
        if os.path.isfile(os.path.join(ROOT, f)):
            shutil.copy(os.path.join(ROOT, f), os.path.join(W, f))
    rng = random.Random(20261228)
    base = dict(pass_=0, wrong=0, refuse=0)
    acc = dict(n=0, ok=0, false=0)
    tf = dict(hit=0, ok=0)
    print("== ① baseline（本地合成，不配教师） ==")
    for t in TASKS:
        out = run("::act on\n::code synth %s\n::quit\n" % t["desc"])
        p = newest_c()
        if "本地已经会了" in out or "编过" in out:
            pass
        if not p:
            base["refuse"] += 1
            print("  [REFUSE] %s" % t["name"])
            continue
        got = check(p, t, rng)
        base["pass_" if got == "pass" else got] += 1
        print("  [%s] %s" % (got.upper(), t["name"]))
    print("== ② --force 问假教师 → 接受/复考 ==")
    for t in TASKS:
        srv, port = start_teacher(reply(t))
        try:
            out = run("::act on\n::tool set http://127.0.0.1:%s/v1 k m\n::tool on\n"
                      "::code learn --force %s\n::quit\n" % (port, t["desc"]))
            accepted = ("[接受]" in out) or ("接受：" in out)
            print("  [%s] %s（%s）" % ("ACCEPT" if accepted else "REFUSE", t["name"],
                                       "编译过+理由+证据" if accepted else "教师没给出可验证答案"))
        finally:
            srv.terminate()
        if not accepted:
            continue
        acc["n"] += 1
        p = newest_c()
        got = check(p, t, rng) if p else "refuse"
        if got == "pass":
            acc["ok"] += 1
        else:
            acc["false"] += 1
            print("       **误收**：接受了但复考不过")
    print("== ③ teacher-free 复用（关教师再 synth） ==")
    for t in TASKS:
        out = run("::act on\n::code synth %s\n::quit\n" % t["desc"])
        hit = "本地记住的解" in out or "teacher-free" in out
        if not hit:
            print("  [MISS] %s" % t["name"])
            continue
        tf["hit"] += 1
        p = newest_c()
        if p and check(p, t, rng) == "pass":
            tf["ok"] += 1
            print("  [HIT] %s（复用且复考过）" % t["name"])
        else:
            print("  [HIT] %s（复用但复考不过）" % t["name"])
    print("=> baseline 对 %d / 错 %d / 拒 %d ｜ 接受 %d（正确 %d / **误收 %d**）｜ teacher-free 命中 %d（正确 %d）"
          % (base["pass_"], base["wrong"], base["refuse"], acc["n"], acc["ok"], acc["false"],
             tf["hit"], tf["ok"]))
    return 1 if acc["false"] > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
