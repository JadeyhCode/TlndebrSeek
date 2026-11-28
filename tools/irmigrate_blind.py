#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irmigrate_blind.py — §7.099 IR 证据分类 + 迁移账本首跑（只读）。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "irmigrate")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def ledger():
    p = os.path.join(W, "_t", "ir_migration.tsv")
    if not os.path.isfile(p):
        return []
    return open(p, encoding="utf-8").read().splitlines()


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

    out = run("::irparity 猫 属于 动物\n::quit\n")
    checks.append(("直接事实：证据=直接", "成立(直接)" in out))

    out = run("::irparity 猫 属于 生物\n::quit\n")
    checks.append(("传递推导：证据=推导", "成立(推导)" in out))

    out = run("::irparity 墙 怕 猫 吗\n::quit\n")
    checks.append(("无证据：证据=未知", "未知(未知)" in out))

    checks.append(("一致时默认不写迁移账本", len(ledger()) == 0))

    set_policy(orig + "\nir_migrate_all=1\n")
    out = run("::irparity 猫 属于 动物\n::quit\n")
    rows = ledger()
    checks.append(("ir_migrate_all=1 ⇒ 记一行 reason=none",
                   len(rows) == 1 and "\tnone\t" in rows[0] and "\tok\t" in rows[0]))
    set_policy(orig)

    lp = os.path.join(W, "_t", "ir_migration.tsv")
    if os.path.isfile(lp):
        os.remove(lp)
    set_policy("ir_adapter=0\n")
    out = run("::irparity 猫 属于 动物\n::quit\n")
    checks.append(("消融 ir_adapter=0 ⇒ 不做 IR、不记账", "不做 IR 中转" in out and len(ledger()) == 0))
    set_policy(orig)

    o1 = run("::irparity 猫 属于 动物\n::quit\n")
    o2 = run("::irparity 猫 属于 动物\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> IR 证据/迁移账本首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
