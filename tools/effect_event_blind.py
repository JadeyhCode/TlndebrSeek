#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""effect_event_blind.py — §7.075 事件具体化（P1）首跑。

检查：event 生成 `[事件:…]` 节点；结果边是**普通动态关系边**指向 `[状态:…]`；
trace 可查；重复 event 幂等（结果边不重复、计数不涨）；约束不满足不产生事件；写入门闸门。
"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "effectevent")
CORPUS = "张三\t属于\t人\n人\t属于\t有生命\n米饭\t属于\t可食\n石头\t属于\t矿物\n"


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def trace_rows(out):
    return [l for l in out.splitlines() if re.match(r"^\s+--\[结果\]-->", l)]


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

    base = "::ingest c.tsv\n::sym write on\n::sym reason 盲测事件\n"
    checks = []

    out = run(base + "::effect event 吃 张三 米饭\n"
                     "::effect trace [事件:吃(张三,米饭)]\n::quit\n")
    checks.append(("事件已具体化", "事件已具体化" in out and "[事件:吃(张三,米饭)]" in out))
    checks.append(("结果边指向状态节点",
                   len(trace_rows(out)) == 1 and "[状态:数量(米饭,-1)]" in trace_rows(out)[0]))
    checks.append(("结果边是普通关系（--[结果]-->）", "--[结果]-->" in out))

    out = run(base + "::effect event 吃 张三 米饭\n"
                     "::effect event 吃 张三 米饭\n"
                     "::effect trace [事件:吃(张三,米饭)]\n::quit\n")
    checks.append(("重复事件幂等（仍 1 条结果边、计数 32）",
                   len(trace_rows(out)) == 1 and "计数 32" in trace_rows(out)[0]))

    out = run(base + "::effect apply 吃 张三 米饭\n"
                     "::effect trace [事件:吃(张三,米饭)]\n::quit\n")
    checks.append(("只 apply 不 event：没有事件/结果边",
                   "图里没有事件" in out and not trace_rows(out)))

    out = run(base + "::effect event 吃 张三 石头\n::quit\n")
    checks.append(("约束不满足：不产生事件", "奇怪" in out and "事件已具体化" not in out))

    out = run("::ingest c.tsv\n::effect event 吃 张三 米饭\n::quit\n")
    checks.append(("写入门没开：不产生事件", "只读模式" in out and "事件已具体化" not in out))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 事件具体化首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
