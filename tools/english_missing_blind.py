#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""english_missing_blind.py — §7.042 英文“没映射”要明说 首跑

4 项：
  ① 没映射的词（wombat）→ 回复里点名它 + “no [syn] entry”，不再含糊；
  ② 宾语位置没映射（a wombat）也一样；
  ③ 已知词仍答 Yes（不误伤）；
  ④ 开放问句（who）仍走“只答是非问”的指引（不被“没映射”抢走）。
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "enmissing")


def fresh():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def last(out):
    a = [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]
    return a[-1] if a else ""


def main():
    checks = []
    fresh()
    out = run("can a wombat swim?\n::quit\n")
    a = last(out)
    checks.append(("主语没映射：点名 wombat + no [syn]", "wombat" in a and "no [syn]" in a))

    out2 = run("is a cat a wombat?\n::quit\n")
    a2 = last(out2)
    checks.append(("宾语没映射：也点名", "wombat" in a2 and "no [syn]" in a2))

    out3 = run("is a cat an animal?\n::quit\n")
    checks.append(("已知词仍答 Yes", "Yes. Cat is an animal." in last(out3)))

    out4 = run("who is an animal?\n::quit\n")
    a4 = last(out4)
    checks.append(("开放问句仍走只答是非问的指引",
                   "only answer yes/no" in a4 and "wombat" not in a4))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 英文没映射提示首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
