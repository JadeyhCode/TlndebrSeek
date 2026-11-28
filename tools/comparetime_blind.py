#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""comparetime_blind.py — §7.088 P1 比较/时间线（::cmp + dims/schema）首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "comparetime")


def run(inp, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180, env=e)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


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
    checks = []

    def one(inp, needle):
        out = run(inp + "::quit\n")
        return needle in out

    checks.append(("3 小于 5 ⇒ 对", one("::cmp 3 小于 5\n", "3 小于 5 ⇒ 对")))
    checks.append(("5 大于 3 ⇒ 对", one("::cmp 5 大于 3\n", "5 大于 3 ⇒ 对")))
    checks.append(("3 等于 3.0 ⇒ 对", one("::cmp 3 等于 3.0\n", "3 等于 3.0 ⇒ 对")))
    checks.append(("5 小于 3 ⇒ 不对", one("::cmp 5 小于 3\n", "5 小于 3 ⇒ 不对")))
    checks.append(("单位归一：1小时 先于 90分钟",
                   one("::cmp 1小时 先于 90分钟\n", "1小时 先于 90分钟 ⇒ 对")))
    checks.append(("跨单位：2天 后于 47小时",
                   one("::cmp 2天 后于 47小时\n", "2天 后于 47小时 ⇒ 对")))
    checks.append(("时间关系拒长度：1米 先于 2 ⇒ 不可比",
                   one("::cmp 1米 先于 2\n", "不可比")))
    checks.append(("量纲不同 ⇒ 不可比（不说假）",
                   one("::cmp 1米 小于 2秒\n", "量纲不同")))

    out = run("::relbeh 大于\n::relbeh 先于\n::quit\n")
    checks.append(("schema：大于 dim=数值 inv=小于；先于 dim=时间 inv=后于",
                   "大于 id=0" in out and "dim=数值" in out and "inv=小于" in out and
                   "dim=时间" in out and "inv=后于" in out))

    out = run("::relbeh 大于\n::cmp 3 小于 5\n::quit\n", env={"AIP_NOSCHEMA": "1"})
    checks.append(("消融 NOSCHEMA：schema 回退，但 ::cmp 仍工作",
                   "回退 AI_RELS" in out and "3 小于 5 ⇒ 对" in out))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 比较/时间线首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
