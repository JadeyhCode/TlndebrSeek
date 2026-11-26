#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper_order_blind.py — §7.063 explicit ordering extraction + cycle detection (D12).

Checks: consistent chain (3 pairs/0 conflicts), direct reverse (1 conflict), 3-cycle (3 pairs),
no markers (0), missing file, and one ablation proving the marker words come from policy data.
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "paperorder")

CHAIN = "早饭 在 午饭 之前。\n午饭 在 晚饭 之前。\n"
REVERSE = "早饭 在 午饭 之前。\n午饭 在 早饭 之前。\n"
CYCLE = "早饭 在 午饭 之前。\n午饭 在 晚饭 之前。\n晚饭 在 早饭 之前。\n"
PLAIN = "猫 属于 动物。\n狗 属于 动物。\n"


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def counts(out):
    m = re.search(r"共 (\d+) 条显式先后；冲突 (\d+) 对", out)
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
    for name, text in (("chain.txt", CHAIN), ("rev.txt", REVERSE),
                       ("cycle.txt", CYCLE), ("plain.txt", PLAIN)):
        with open(os.path.join(W, name), "w", encoding="utf-8") as f:
            f.write(text)

    checks = []
    checks.append(("链：2 条先后 0 冲突", counts(run("::paper order chain.txt\n::quit\n")) == (2, 0)))
    checks.append(("直接反向：1 冲突", counts(run("::paper order rev.txt\n::quit\n")) == (2, 1)))
    checks.append(("三元环：3 条 / 3 对互相先后", counts(run("::paper order cycle.txt\n::quit\n")) == (3, 3)))
    checks.append(("无标记：0/0", counts(run("::paper order plain.txt\n::quit\n")) == (0, 0)))
    checks.append(("文件不存在 → 明说", "读不开" in run("::paper order nope.txt\n::quit\n")))

    # ablation: marker words are data
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("order_before=zzz\norder_after=qqq\n")
    checks.append(("消融：改词表后不再命中（数据驱动）",
                   counts(run("::paper order chain.txt\n::quit\n")) == (0, 0)))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 论文先后关检测首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
