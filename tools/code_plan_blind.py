#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§6.900 plan 盲测：8 条**未参与调优**的需求描述，只量 `::code plan --write` 的首跑。

判据（全部要过）：
  ① 骨架写出来了、gcc 能编过、跑起来退出码 0 且打 `plan ok`；
  ② 摘要里的“要点数/已覆盖数/已内嵌数”一致（本轮要求全内嵌，否则记 READ 而不是 PASS）。
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESCS = [
    "写一个数组求和器",
    "写一个数组最值器",
    "写一个数组切片器",
    "写一个数组去重器",
    "写一个文件行数器",
    "写一个两数计算器",
    "写一个单词统计器",
    "写一个成绩统计器",
]


def run(aip, inp):
    return subprocess.run([aip, "--model", os.path.join(ROOT, "code", "code_model.bin")],
                          input=inp.encode(), capture_output=True, timeout=300, cwd=ROOT)


def main():
    aip = os.path.join(ROOT, "build_aip")
    src = os.path.join(ROOT, "_t", "work", "plan_write.c")
    exe = src[:-2]
    ok = 0
    for desc in DESCS:
        # 清掉上一轮的产物，避免把旧骨架当新结果
        for p in (src, exe):
            if os.path.exists(p):
                os.remove(p)
        out = run(aip, "::act on\n::code plan --write %s\n::quit\n" % desc)
        txt = (out.stdout + out.stderr).decode("utf-8", "replace")
        m = re.search(r"(\d+) 个要点，(\d+) 个已覆盖（(\d+) 条已内嵌成函数）", txt)
        if not m:
            print("  [FAIL] %s（没有摘要）" % desc)
            continue
        npts, ncov, nemb = map(int, m.groups())
        if not os.path.exists(src):
            print("  [FAIL] %s（没写骨架）" % desc)
            continue
        cc = subprocess.run(["gcc", "-std=c11", "-Wall", "-Wextra", "-o", exe, src],
                            capture_output=True)
        if cc.returncode != 0:
            print("  [FAIL] %s（骨架编不过）" % desc)
            continue
        rr = subprocess.run([exe], capture_output=True, timeout=10)
        got = (rr.stdout + rr.stderr).decode("utf-8", "replace")
        if rr.returncode != 0 or "plan ok" not in got:
            print("  [FAIL] %s（跑不出 plan ok：rc=%d）" % (desc, rr.returncode))
            continue
        if nemb < npts or ncov < npts:
            print("  [READ] %s（要点 %d / 已覆盖 %d / 已内嵌 %d）" % (desc, npts, ncov, nemb))
            continue
        ok += 1
        print("  [PASS] %s（%d 个要点全部内嵌）" % (desc, npts))
    print("=> plan 盲测首跑：%d / %d" % (ok, len(DESCS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
