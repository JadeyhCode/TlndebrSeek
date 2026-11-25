#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper_conflict_blind.py — §7.055 paper-claim conflict detection (D12 extension).

Checks `::paper conflicts`:
  ① conflicting claims between paragraphs (same A/R, different B) reported with sources;
  ② consistent document → 0 pairs (no false conflict);
  ③ unrelated claims → 0;
  ④ claim vs existing graph fact reported as 与图冲突;
  ⑤ sources are shown (论文);
  ⑥ after rejecting one side, only the graph conflict remains.
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "paperconflict")

DOC_CONFLICT = ("根据参考文献，猫 属于 动物。\n"
                "实验表明，猫 属于 猫科。\n"
                "根据参考文献，狗 属于 动物。\n")
DOC_OK = ("根据参考文献，猫 属于 动物。\n"
          "实验表明，狗 属于 动物。\n"
          "根据参考文献，鸟 会 飞。\n")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def counts(out):
    m = re.search(r"待证间 (\d+) 对 / 与图 (\d+) 条", out)
    return (int(m.group(1)), int(m.group(2))) if m else (None, None)


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    with open(os.path.join(W, "conflict.txt"), "w", encoding="utf-8") as f:
        f.write(DOC_CONFLICT)
    with open(os.path.join(W, "ok.txt"), "w", encoding="utf-8") as f:
        f.write(DOC_OK)

    checks = []
    out = run("::paper read conflict.txt\n::paper conflicts\n::quit\n")
    c = counts(out)
    checks.append(("冲突文档：1 对", c == (1, 1)))
    checks.append(("冲突行带来源「论文」", "来源 论文" in out))

    out = run("::paper read ok.txt\n::paper conflicts\n::quit\n")
    c = counts(out)
    checks.append(("一致文档：0 对", c is not None and c[0] == 0))

    out = run("::paper read conflict.txt\n::claim reject 1\n::paper conflicts\n::quit\n")
    c = counts(out)
    checks.append(("reject 一侧后：待证间 0 对", c is not None and c[0] == 0))

    out = run("::paper conflicts\n::quit\n")
    checks.append(("没有待证：0 对 0 条", counts(out) == (0, 0)))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 论文冲突检测首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
