#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""effect_blind.py — §7.074 P1 效果执行器（assert/retract + tick + 来源）首跑。

检查：
  ① 写入门/理由闸门；② 正向效果落图（数量=-1，计数）；③ 重复应用幂等且计数；
  ④ 约束不满足（石头 非 可食）→ “奇怪”且不执行；⑤ retract 撤销；⑥ effect_enable=0 消融；
  ⑦ 无 schema / 无 post 的关系拒绝执行；⑧ 账本记录来源与时刻。
"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "effect")
CORPUS = "张三\t属于\t人\n人\t属于\t有生命\n米饭\t属于\t可食\n石头\t属于\t矿物\n"


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def state_rows(out):
    # 只数“状态行”（两空格缩进 + `数量 = -1（`），别把 apply 的回显算进去
    return [l for l in out.splitlines() if re.match(r"^\s+数量 = -1（", l)]


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt",
              "policy.txt", "laws.txt", "relations_beh.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    with open(os.path.join(W, "c.tsv"), "w", encoding="utf-8") as f:
        f.write(CORPUS)

    base = "::ingest c.tsv\n"
    checks = []

    out = run(base + "::effect apply 吃 张三 米饭\n::quit\n")
    checks.append(("写入门没开：拒绝", "只读模式" in out))

    out = run(base + "::sym write on\n::effect apply 吃 张三 米饭\n::quit\n")
    checks.append(("没理由：拒绝", "必须给理由" in out))

    out = run(base + "::sym write on\n::sym reason 盲测效果\n"
                     "::effect apply 吃 张三 米饭\n::effect state 米饭\n::quit\n")
    checks.append(("正向效果落图（数量=-1）", "已写入" in out and state_rows(out)))
    checks.append(("状态带计数与时刻", "计数 32" in out and "tick " in out))

    out = run(base + "::sym write on\n::sym reason 盲测效果\n"
                     "::effect apply 吃 张三 米饭\n::effect apply 吃 张三 米饭\n"
                     "::effect state 米饭\n::quit\n")
    checks.append(("重复应用：幂等且计数（64）",
                   "重复应用只计数" in out and "计数 64" in out and len(state_rows(out)) == 1))

    out = run(base + "::sym write on\n::sym reason 盲测效果\n"
                     "::effect apply 吃 张三 石头\n::effect state 石头\n::quit\n")
    checks.append(("约束不满足：奇怪且不执行",
                   "奇怪" in out and "不执行" in out and not state_rows(out)))

    out = run(base + "::sym write on\n::sym reason 盲测效果\n"
                     "::effect apply 吃 张三 米饭\n::effect retract 吃 张三 米饭\n"
                     "::effect state 米饭\n::quit\n")
    checks.append(("retract撤销后状态为空", "已撤" in out and not state_rows(out)))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("effect_enable=0\n")
    out = run(base + "::sym write on\n::sym reason 盲测效果\n"
                     "::effect apply 吃 张三 米饭\n::effect state 米饭\n::quit\n")
    checks.append(("消融 effect_enable=0：不执行",
                   "策略关闭" in out and not state_rows(out)))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    out = run(base + "::sym write on\n::sym reason 盲测效果\n"
                     "::effect apply 想念 张三 米饭\n::effect apply 属于 张三 人\n::quit\n")
    checks.append(("无 schema / 无 post 的关系拒绝执行",
                   "没有 schema" in out and "没有 post" in out))

    led = os.path.join(W, "_t", "effects.tsv")
    ok_led = os.path.isfile(led) and "assert:数量" in open(led, encoding="utf-8").read()
    checks.append(("账本记录来源/时刻/理由", ok_led))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 效果执行器首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
