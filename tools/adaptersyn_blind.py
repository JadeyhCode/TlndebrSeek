#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""adaptersyn_blind.py — §7.113 [syn]/[affix] 移到适配器侧、ablation 首跑。"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "adaptersyn")


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
    batch = "::notepad off\n::char off\n猫 属于 动物 吗\n猫咪 属于 动物 吗\n猫们 属于 动物 吗\n::quit\n"

    out = run(batch)
    a = answers(out)
    checks.append(("默认：猫咪/猫们 与 猫 同答",
                   len(a) == 3 and a[0] == a[1] == a[2] and "属于" in a[0]))
    checks.append(("替换没有叠加成猫猫", "猫猫" not in out))

    set_policy("adapter_syn=0")
    out = run(batch)
    a = answers(out)
    checks.append(("消融：猫 仍答对", len(a) == 3 and "属于" in a[0]))
    checks.append(("消融：猫咪 不再归一", len(a) == 3 and a[1] != a[0]))
    checks.append(("消融：猫们 不再归一", len(a) == 3 and a[2] != a[0]))

    set_policy("adapter_syn=1")
    out = run(batch)
    a = answers(out)
    checks.append(("显式开 1：三句仍同答", len(a) == 3 and a[0] == a[1] == a[2]))

    out = run("::paraphrase sync\n::quit\n")
    checks.append(("说法归一进图仍可用（表已移出核但数据仍在）",
                   "条" in out and ("同义" in out or "写入" in out or "说法" in out)))

    set_policy("")
    o1 = run(batch)
    o2 = run(batch)
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 适配器同义词迁移首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
