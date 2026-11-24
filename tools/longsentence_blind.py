#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""longsentence_blind.py — §7.035 长文长句作为注意力来源 首跑

4 项：
  ① 长段落（≥60 字节）里的内容词在 `::att` 里标「长句」；
  ② 短句不标；
  ③ 把 `long_sentence_chars` 调大（等于关闭）后长段落不再标（消融）；
  ④ 被标「长句」的词是内容词，不是虚词。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "longsent")
LONG = ("在这个很长的段落里面我想说的是关于动物的分类以及它们的习性"
        "还有它们生活的环境等等这些内容")


def fresh(policy=None):
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    if policy is not None:
        with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
            f.write(policy)


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def att_lines(out):
    return [l for l in out.splitlines() if "份额" in l]


def main():
    checks = []
    fresh()
    out = run(LONG + "\n::att\n::quit\n")
    lines = att_lines(out)
    checks.append(("长段落出现「来源 长句」", any("来源 长句" in l for l in lines)))
    checks.append(("被标长句的是内容词（动物）",
                   any("动物" in l and "来源 长句" in l for l in lines)))

    fresh()
    out2 = run("猫 属于 动物 吗\n::att\n::quit\n")
    checks.append(("短句不标长句", not any("来源 长句" in l for l in att_lines(out2))))

    fresh("long_sentence_chars=10000\n")
    out3 = run(LONG + "\n::att\n::quit\n")
    checks.append(("阈值调大后不再标（消融）", not any("来源 长句" in l for l in att_lines(out3))))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 长句注意力首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
