#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""learn_eval.py — §6.921 自学首跑读数：blind50 上“不会 → 问教师 → 学 → 用 gold 复考”。

口径：
  · baseline：直接 `::code synth`（本地能力）；
  · 不会的题走 `::code learn`（教师由环境变量 AIP_TOOL_URL/KEY/MODEL 提供，不落盘）；
  · 接受 = 编译过 + 有理由 + 有证据；
  · 语义复考：用题目 gold 生成随机输入，比较候选程序输出；
  · 误收 = 接受了但 gold 复考不过（比“不会”更危险）。

用法：
  AIP_TOOL_URL=https://api.deepseek.com/v1 AIP_TOOL_KEY=… AIP_TOOL_MODEL=deepseek-chat \
      python3 tools/learn_eval.py [--limit N] [--tries 4]
"""
import os
import random
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import code_search as S
import code_blind26 as B
import code_hidden as H

BIN = os.path.join(ROOT, "build_aip")
MODEL = os.path.join(ROOT, "code", "code_model.bin")
OUT = os.path.join(ROOT, "_t", "work")


def learn(desc):
    env = dict(os.environ)
    env["AIP_TOOL"] = "1"
    env.setdefault("AIP_TOOL_THINK", "1")
    p = subprocess.run([BIN, "--model", MODEL], input=("::code learn %s\n::quit\n" % desc).encode(),
                       capture_output=True, env=env, cwd=ROOT, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def gen(task, rng):
    if task["shape"] == "arr":
        v = [rng.randint(-9, 9) for _ in range(rng.randint(1, 7))]
        data = (" ".join(map(str, v)) + "\n").encode()
    elif task["shape"] == "matrix":
        rr = rng.randint(2, 4); cc = rng.randint(2, 4)
        v = [[rng.randint(-9, 9) for _ in range(cc)] for _ in range(rr)]
        data = (("%d %d\n" % (rr, cc)) + "\n".join(" ".join(map(str, r)) for r in v) + "\n").encode()
    elif task["shape"] == "two":
        a, b = rng.randint(-20, 20), rng.randint(-20, 20)
        v = (a, b); data = b""
    elif task["shape"] == "file":
        words = ["a", "bb", "ccc", "XY", "z", "pq"]
        lines = [" ".join(rng.choice(words) for _ in range(rng.randint(1, 4)))
                 for _ in range(rng.randint(1, 4))]
        v = "\n".join(lines) + "\n"
        fpath = os.path.join(OUT, "learn_eval_in.txt")
        os.makedirs(OUT, exist_ok=True)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(v)
        data = b""
    else:  # str
        v = "".join(rng.choice("abcXYZ") for _ in range(rng.randint(1, 6)))
        data = (v + "\n").encode()
    return v, data


def eval_candidate(task, path, rng, tries):
    ok_n = 0
    for _ in range(tries):
        v, data = gen(task, rng)
        want = task["gold"](v)
        if want is None:
            continue
        argv = None
        if task["shape"] == "file":
            argv = [os.path.join(OUT, "learn_eval_in.txt")]
        elif task["shape"] == "two":
            argv = [str(v[0]), str(v[1])]
        got = B.run_prog(path, data, argv=argv)
        if got is None:
            return False
        if H.clean_out(got).strip() != S.exp_str(want).strip():
            return False
        ok_n += 1
    return ok_n > 0


def main():
    limit = 8
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    rng = random.Random(20261219)
    tasks = S.BLIND50[:limit]
    base = acc = sem = false_acc = 0
    print("== blind50 自学首跑 ==")
    for t in tasks:
        got, _ = B.judge(t, rng)
        if got == "pass":
            base += 1
            print("  [BASE-PASS] %s" % t["name"])
            continue
        out = learn(t["desc"])
        m = re.search(r"候选：(\S+\.c)", out)
        if "[学习] 接受" not in out or not m:
            reason = ""
            for ln in out.splitlines():
                if "[学习]" in ln and ("拒绝" in ln or "不能瞎写" in ln or "没答上来" in ln):
                    reason = ln.strip()
            print("  [REJECT] %s  %s" % (t["name"], reason[:80]))
            continue
        acc += 1
        path = m.group(1)
        if eval_candidate(t, path, rng, 4):
            sem += 1
            print("  [LEARN-OK] %s" % t["name"])
        else:
            false_acc += 1
            print("  [FALSE-ACCEPT] %s（接受了但 gold 不过）" % t["name"])
    print("=> baseline %d/%d ｜ learn 接受 %d ｜ 语义通过 %d ｜ 误收 %d" %
          (base, len(tasks), acc, sem, false_acc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
