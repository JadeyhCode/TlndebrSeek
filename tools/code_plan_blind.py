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
DESCS2 = [
    "写一个数组累计器",
    "写一个数组极值器二号",
    "写一个数组切片器二号",
    "写一个数组变换器",
    "写一个文件单词器",
    "写一个工程计算器",
    "写一个单词计数器",
    "写一个数组工具集",
]

DESCS5 = [
    "写一个排序工具",
    "写一个去重工具三号",
    "写一个文件工具三号",
    "写一个两数工具三号",
    "写一个矩阵工具二号",
    "写一个字符串工具",
    "写一个顺序工具二号",
    "写一个桩工具",
]

DESCS4 = [
    "写一个数组去重工具二号",
    "写一个文件行数工具二号",
    "写一个两数工具二号",
    "写一个单词工具二号",
    "写一个矩阵工具",
    "写一个切片工具",
    "写一个混合工具",
    "写一个游戏工具",
]

DESCS3 = [
    "写一个数组统计工具",
    "写一个文件统计器",
    "写一个矩阵统计器",
    "写一个单词工具箱",
    "写一个猜数字游戏",
    "写一个数列求和解器",
    "写一个负零统计器",
    "写一个两数工具",
]

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
    descs = (DESCS5 if "--batch5" in sys.argv else
            DESCS4 if "--batch4" in sys.argv else
            DESCS3 if "--batch3" in sys.argv else
            DESCS2 if "--batch2" in sys.argv else DESCS)
    aip = os.path.join(ROOT, "build_aip")
    src = os.path.join(ROOT, "_t", "work", "plan_write.c")
    exe = src[:-2]
    ok = 0
    for desc in descs:
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
        # §6.902 逐条测试文件：编过 + 跑出 "test ok"
        tsrc = os.path.join(ROOT, "_t", "work", "plan_write_test.c")
        tex = tsrc[:-2]
        if not os.path.exists(tsrc):
            print("  [FAIL] %s（没有逐条测试文件）" % desc)
            continue
        tcc = subprocess.run(["gcc", "-std=c11", "-Wall", "-Wextra", "-o", tex, tsrc], capture_output=True)
        if tcc.returncode != 0:
            print("  [FAIL] %s（测试文件编不过）" % desc)
            continue
        tr = subprocess.run([tex], capture_output=True, timeout=10)
        tout = (tr.stdout + tr.stderr).decode("utf-8", "replace")
        if tr.returncode != 0 or "test ok" not in tout:
            print("  [FAIL] %s（逐条测试不过：rc=%d）" % (desc, tr.returncode))
            continue
        ok += 1
        print("  [PASS] %s（%d 个要点全部内嵌 + 逐条测试通过）" % (desc, npts))
    print("=> plan 盲测首跑：%d / %d" % (ok, len(descs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
