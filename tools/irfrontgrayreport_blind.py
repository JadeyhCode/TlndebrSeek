#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irfrontgrayreport_blind.py — §7.107 灰度汇总/灰度决策档案首跑。"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
TOOL = os.path.join(ROOT, "tools", "irfront_decision.py")
W = os.path.join(ROOT, "_t", "irfrontgrayreport")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def set_policy(text):
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(text)


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt",
              "policy.txt", "relations_beh.txt", "dims.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    orig = open(os.path.join(W, "policy.txt"), encoding="utf-8").read()
    checks = []

    set_policy(orig + "\nir_front=2\n")
    out = run("猫 是 动物 吗\n猫 属于 动物 吗\n::irfront gray-report\n::quit\n")
    checks.append(("灰度 report：尝试2/命中2/回写1",
                   "尝试 2，灰度命中 2，灰度透传 0，回写 1" in out))
    checks.append(("灰度 report：命中率 100%", "命中率 100.0%" in out))

    set_policy(orig)
    out = run("猫 是 动物 吗\n::irfront gray-report\n::quit\n")
    checks.append(("非灰度模式明确提示", "当前不是灰度模式" in out))

    rc = subprocess.run([sys.executable, TOOL, "--gray-selftest"], cwd=ROOT,
                        capture_output=True)
    ro = rc.stdout.decode("utf-8", "replace")
    checks.append(("灰度判定自检 4/4", rc.returncode == 0 and "灰度判定自检：4/4" in ro))

    rc = subprocess.run([sys.executable, TOOL, "--selftest"], cwd=ROOT,
                        capture_output=True)
    ro2 = rc.stdout.decode("utf-8", "replace")
    checks.append(("原决策自检仍 5/5", rc.returncode == 0 and "判定函数自检：5/5" in ro2))

    r1 = subprocess.run([sys.executable, TOOL, "--gray-only"], cwd=ROOT,
                        capture_output=True, timeout=600)
    o1 = (r1.stdout + r1.stderr).decode("utf-8", "replace")
    r2 = subprocess.run([sys.executable, TOOL, "--gray-only"], cwd=ROOT,
                        capture_output=True, timeout=600)
    o2 = (r2.stdout + r2.stderr).decode("utf-8", "replace")
    checks.append(("gray-only：tries=50/命中=50/changed=0",
                   "tries=50 命中=50 透传=0 changed=0" in o1))
    checks.append(("gray-only 建议默认值 2", "建议默认值：2" in o1 and "回退开关" in o1))

    def stable(s):
        return [l for l in s.splitlines()
                if not l.startswith("时间：") and not l.startswith("延迟：")]
    checks.append(("gray-only 可重复（除时间/延迟）", r1.returncode == 0 and
                   r2.returncode == 0 and stable(o1) == stable(o2)))

    fp = os.path.join(ROOT, "_t", "ir_front_decision_gray.txt")
    rows = open(fp, encoding="utf-8").read() if os.path.isfile(fp) else ""
    checks.append(("灰度决策档案落盘", "建议默认值：2" in rows and "回退开关" in rows))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 灰度汇总/决策首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
