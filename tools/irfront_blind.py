#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irfront_blind.py — §7.100 IR 前置（受控开关，默认关）首跑。"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "irfront")
BATCH = ["猫 属于 动物 吗", "猫 是 动物 吗", "猫 不 属于 植物 吗",
         "桌子 会 飞 吗", "今天 天气 很 好"]


def run(inp, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180, env=e)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def answers(out):
    return [l for l in out.splitlines() if "AI >" in l]


def set_policy(text):
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(text)


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt",
              "policy.txt", "relations_beh.txt", "dims.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    orig = open(os.path.join(W, "policy.txt"), encoding="utf-8").read()
    checks = []

    set_policy(orig + "\nir_front=1\n")
    out = run("猫 是 动物 吗\n::quit\n", env={"AIP_IRFRONT_DBG": "1"})
    checks.append(("front 开：别名句被回写成规范关系",
                   "[irfront] 猫 是 动物 吗 => 猫 属于 动物 吗" in out))
    checks.append(("front 开：答案与直入一致", "对 ， 猫 -[属于]-> 动物" in out))

    set_policy(orig)
    out = run("猫 是 动物 吗\n::quit\n", env={"AIP_IRFRONT_DBG": "1"})
    checks.append(("front 关（默认）：不回写、答案不变",
                   "[irfront]" not in out and "对 ， 猫 -[属于]-> 动物" in out))

    batch_in = "".join(x + "\n" for x in BATCH) + "::quit\n"
    set_policy(orig)
    off = run(batch_in)
    set_policy(orig + "\nir_front=1\n")
    on = run(batch_in)
    checks.append(("整批答案逐字一致（front 0 vs 1）", answers(off) == answers(on) and answers(on)))

    out = run("今天 天气 很 好\n::quit\n", env={"AIP_IRFRONT_DBG": "1"})
    checks.append(("UNKNOWN 原样透传（无 irfront 行）", "[irfront]" not in out))

    out = run("::rel 猫\n::quit\n", env={"AIP_IRFRONT_DBG": "1"})
    checks.append(("命令不经过 IR 前置", "[irfront]" not in out and "猫 --[" in out))

    set_policy(orig + "\nir_front=1\nir_adapter=0\n")
    out = run("猫 是 动物 吗\n::quit\n", env={"AIP_IRFRONT_DBG": "1"})
    checks.append(("ir_adapter=0 时前置也关闭（无回写）", "[irfront]" not in out))
    set_policy(orig)

    set_policy(orig + "\nir_front=1\n")
    o1 = run("猫 是 动物 吗\n::quit\n")
    o2 = run("猫 是 动物 吗\n::quit\n")
    checks.append(("front 开读数确定（两次一致）", o1 == o2))
    set_policy(orig)

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> IR 前置首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
