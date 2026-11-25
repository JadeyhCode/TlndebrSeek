#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""timeline_blind.py — §7.058 paper timeline extraction (D12) first run.

Checks: marker count, document order preserved, non-temporal doc → 0, missing file error,
and one ablation proving markers come from policy data (`time_marker`).
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "timeline")

DOC = """起初，佐格住在北境。
之后，佐格搬到了南城。
米拉一直在南城。
佐格先吃了矿石。
然后佐格去找米拉。
最后他们一起回来了。
"""
PLAIN = """佐格属于兽类。
米拉属于人类。
兽类属于生物。
"""


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    with open(os.path.join(W, "doc.txt"), "w", encoding="utf-8") as f:
        f.write(DOC)
    with open(os.path.join(W, "plain.txt"), "w", encoding="utf-8") as f:
        f.write(PLAIN)

    checks = []
    out = run("::paper timeline doc.txt\n::quit\n")
    m = re.search(r"共 (\d+) 个时间标记句", out)
    checks.append(("标记句共 5 个", bool(m) and m.group(1) == "5"))
    order = [out.find("[起初]"), out.find("[之后]"), out.find("[先]"),
             out.find("[然后]"), out.find("[最后]")]
    checks.append(("按文档顺序（起初<之后<先<然后<最后）",
                   all(x >= 0 for x in order) and order == sorted(order)))

    out = run("::paper timeline plain.txt\n::quit\n")
    m = re.search(r"共 (\d+) 个时间标记句", out)
    checks.append(("无时间标记 → 0", bool(m) and m.group(1) == "0"))

    out = run("::paper timeline missing.txt\n::quit\n")
    checks.append(("文件不存在 → 明说读不开", "读不开" in out))

    # ablation: replace marker list with a word not in the doc → 0
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("time_marker=zzz\n")
    out = run("::paper timeline doc.txt\n::quit\n")
    m = re.search(r"共 (\d+) 个时间标记句", out)
    checks.append(("消融：改词表后不再命中（数据驱动）", bool(m) and m.group(1) == "0"))
    # restore
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 论文时间线首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
