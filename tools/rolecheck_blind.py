#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rolecheck_blind.py — §7.076 P1 角色/约束检查（属于链 + pred.h 谓词原子）首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "rolecheck")
CORPUS = "张三\t属于\t人\n人\t属于\t有生命\n米饭\t属于\t可食\n石头\t属于\t矿物\n"


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt",
              "policy.txt", "relations_beh.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    with open(os.path.join(W, "c.tsv"), "w", encoding="utf-8") as f:
        f.write(CORPUS)
    base = "::ingest c.tsv\n"
    checks = []

    out = run(base + "::rolecheck 吃 张三 米饭\n::quit\n")
    checks.append(("角色绑定显示", "施事=张三" in out and "受事=米饭" in out))
    checks.append(("约束通过（属于链）", "通过 2 / 奇怪 0" in out and "属于链" in out))

    out = run(base + "::rolecheck 吃 张三 石头\n::quit\n")
    checks.append(("约束不满足 → 奇怪", "奇怪 1" in out and "石头 不是/推不出 可食" in out))

    out = run(base + "::pred make 可食 石头\n::rolecheck 吃 张三 石头\n::quit\n")
    checks.append(("谓词原子可满足约束", "通过（谓词原子 可食(石头)）" in out and "通过 2 / 奇怪 0" in out))

    out = run(base + "::rolecheck 属于 猫 动物\n::quit\n")
    checks.append(("类词不知道 → 明说不知道",
                   "不知道「实例或子类」是什么" in out and "不知道 1" in out))

    out = run(base + "::rolecheck 想念 张三 米饭\n::quit\n")
    checks.append(("无 schema → 纯标签", "没有 schema" in out and "纯标签" in out))

    out = run(base + "::rolecheck 喜欢 猫 狗\n::quit\n")
    checks.append(("没有约束的关系", "没有约束" in out and "通过 0 / 奇怪 0" in out))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("role_constraint=0\n")
    out = run(base + "::rolecheck 吃 张三 石头\n::quit\n")
    checks.append(("消融 role_constraint=0：检查关闭",
                   "检查关闭（role_constraint=0）" in out and "奇怪" not in out))
    out = run(base + "::sym write on\n::sym reason 盲测\n::effect apply 吃 张三 石头\n::quit\n")
    checks.append(("消融后效果执行也不再拦约束", "已写入" in out and "奇怪" not in out))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 角色/约束首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
