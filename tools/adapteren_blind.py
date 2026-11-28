#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adapteren_blind.py — §7.114 英语适配器钩子（adapter_en 回退）首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "adapteren")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def answers(out):
    return [l.split("AI > ", 1)[1] for l in out.splitlines() if "AI > " in l]


def set_policy(extra):
    txt = open(os.path.join(ROOT, "policy.txt"), encoding="utf-8").read()
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(txt + "\n" + extra + "\n")


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

    out = run("Is a cat an animal?\n::quit\n")
    checks.append(("默认：英语是非问 ⇒ Yes", "Yes." in out and "animal" in out))
    out = run("Is a cat a plant?\n::quit\n")
    checks.append(("默认：否命题 ⇒ No", "No." in out and "plant" in out))
    out = run("Does a zebra eat meat?\n::quit\n")
    checks.append(("未知词提示仍是英文", "mapping" in out and "guess" in out))

    set_policy("adapter_en=0")
    out = run("Is a cat an animal?\nIs a cat a plant?\n猫 属于 动物 吗\n::quit\n")
    a = answers(out)
    checks.append(("消融：英语句不再给 Yes/No", len(a) == 3 and "Yes." not in out and "No." not in out))
    checks.append(("消融：中文句仍答对", len(a) == 3 and "属于" in a[2]))

    set_policy("adapter_en=1")
    out = run("Is a cat an animal?\n::quit\n")
    checks.append(("显式开 1：Yes 恢复", "Yes." in out))

    set_policy("")
    o1 = run("Is a cat an animal?\n::quit\n")
    o2 = run("Is a cat an animal?\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 英语适配器钩子首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
