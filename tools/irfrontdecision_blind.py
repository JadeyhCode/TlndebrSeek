#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irfrontdecision_blind.py — §7.105 IR 前置默认值决策档案首跑。"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "irfront_decision.py")
OUT = os.path.join(ROOT, "_t", "ir_front_decision.txt")


def run(args):
    p = subprocess.run([sys.executable, TOOL] + args, capture_output=True, cwd=ROOT, timeout=600)
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    checks = []
    rc, out = run(["--selftest"])
    checks.append(("判定函数自检 5/5", rc == 0 and "判定函数自检：5/5" in out))
    checks.append(("全达标→1", "decide=1（期望 1）OK" in out))
    checks.append(("hidden 红/差异/UNKNOWN/延迟 各自→0",
                   out.count("decide=0（期望 0）OK") == 4))

    rc, out1 = run(["--ab-only"])
    rc2, out2 = run(["--ab-only"])
    strip = lambda s: [l for l in s.splitlines()
                       if not l.startswith("时间：") and not l.startswith("延迟：")]
    checks.append(("ab-only 可重复（除时间戳逐字一致）", rc == 0 and rc2 == 0 and strip(out1) == strip(out2)))
    checks.append(("ab-only 不升级默认（未跑 hidden/capbench）",
                   "建议默认值：0" in out1 and "hidden/capbench 未全绿" in out1))
    checks.append(("读数含 tries/changed/UNKNOWN/延迟",
                   all(k in out1 for k in ("tries=", "changed=", "unknown=", "ratio="))))

    rows = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else ""
    checks.append(("决策档案落盘且含回退开关",
                   "回退开关：policy ir_front=0" in rows and "建议默认值：" in rows))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 前置默认值决策档案首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
