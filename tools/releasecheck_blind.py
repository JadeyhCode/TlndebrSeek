#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""releasecheck_blind.py — §7.108 v0.09b 收尾清单审计首跑。"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "releasecheck.py")


def run(args):
    p = subprocess.run([sys.executable, TOOL] + args, capture_output=True, cwd=ROOT, timeout=300)
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    checks = []
    rc, out = run(["--selftest"])
    checks.append(("自检 3/3", rc == 0 and "收尾清单自检：3/3" in out))
    checks.append(("自检覆盖 done 无证据 / gap 无缺口", "selftest 2" in out and "selftest 3" in out))

    rc, out = run([])
    checks.append(("结构合法（0 错误）", rc == 0 and "FAIL" not in out))
    checks.append(("覆盖 P0–P4 + 路线 + 发布", "行数 31" in out))
    checks.append(("诚实报告 5 个 gap", out.count("GAP") == 5 and "未达 v0.09b 发布" in out))
    checks.append(("gap 含核只吃 IR 与基准/污染", "核只吃 IR" in out and "bAbI/GSM8K" in out))

    rc, out2 = run(["--strict"])
    checks.append(("--strict 有 gap ⇒ 发布闸门拒绝（rc=1）",
                   rc == 1 and "发布闸门拒绝" in out2))

    rc2, out3 = run([])
    checks.append(("读数确定（两次一致）", rc2 == 0 and out == out3))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 收尾清单审计首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
