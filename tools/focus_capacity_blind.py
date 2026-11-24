#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""focus_capacity_blind.py — §7.030 焦点环 4→8 + 存档版本 v17 首跑

5 项：
  ① 旧档（v16 model.bin）还能读，图查询正常；
  ② 新档 `::save` 出来的是 v17（文件头版本号），且能重新加载并答对；
  ③ 跨轮注意力保住第 4 个以后的词（问“人”后再问“谁…”，`::att` 里仍有人）；
  ④ `att_list=1` 时列表按注意力把“人”排第一（不再依赖论文主题词）；
  ⑤ `att_list=0`（默认）顺序不变（猫第一）。
"""
import os
import re
import shutil
import struct
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "focuscap")


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


def run(inp, model="model.bin"):
    p = subprocess.run([BIN, "--model", model], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def version_of(path):
    with open(path, "rb") as f:
        head = f.read(8)
    if len(head) < 8:
        return None
    magic, ver = struct.unpack("<II", head)
    return ver if magic == 0x444D4941 else None


def main():
    checks = []
    fresh()
    out = run("猫 属于 动物 吗\n::quit\n")
    checks.append(("v16 旧档可读且答对", "对" in out and "猫" in out))

    run("::save new17.bin\n::quit\n")
    p = os.path.join(W, "new17.bin")
    checks.append(("新档版本号 = 17", version_of(p) == 17))
    out2 = run("猫 属于 动物 吗\n::quit\n", model="new17.bin")
    checks.append(("v17 新档能重载并答对", "对" in out2 and "猫" in out2))

    fresh()
    out3 = run("人 属于 动物 吗\n谁 属于 动物\n::att\n::quit\n")
    checks.append(("跨轮保住第 4 个以后的焦点词（人）", ("人" in out3.split("[注意力]")[-1])))

    fresh("att_list=1\n")
    out4 = run("人 属于 动物 吗\n谁 属于 动物\n::quit\n")
    m = re.search(r"属于 动物 的 有 ： ([^\n（]*)", out4)
    first4 = m.group(1).split("、")[0].strip() if m else "?"
    checks.append(("att_list=1：人排第一", first4 == "人"))

    fresh("att_list=0\n")
    out5 = run("人 属于 动物 吗\n谁 属于 动物\n::quit\n")
    m5 = re.search(r"属于 动物 的 有 ： ([^\n（]*)", out5)
    first5 = m5.group(1).split("、")[0].strip() if m5 else "?"
    checks.append(("att_list=0：默认顺序（猫第一）", first5 == "猫"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 焦点容量/存档版本首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
