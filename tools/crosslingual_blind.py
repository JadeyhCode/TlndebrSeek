#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""crosslingual_blind.py — §7.041 中英互译迁移首跑（学 A 考 B）

8 项：
  A. 同一事实两种语言问，极性一致（4 条）；
  B. 英文教 → 中文问得出（2 条）；
  C. 中文教 → 英文问得出（2 条）。
判定：极性对 pass；拒答 refuse；**极性相反**才算 wrong（wrong>0 才红）。
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "crosslingual")
BAD = ("不 知道", "不知道", "不 太 懂", "不太懂", "不 确定", "不确定",
       "don't know", "Sorry", "没 记 过", "没记过")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def answers(out):
    return [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]


def polarity(ans):
    a = ans.lower()
    if "不 对" in a or "不对" in a:      # 中文否定必须先判（否则 "不对" 含 "对"）
        return -1
    if "yes" in a:
        return 1
    if "no." in a or "no " in a:
        return -1
    if "对" in a:
        return 1
    return 0


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))

    checks = []
    pairs = [("is a cat an animal?", "猫 属于 动物 吗", 1),
             ("can a bird fly?", "鸟 会 飞 吗", 1),
             ("can a bird swim?", "鸟 会 游泳 吗", -1),
             ("can a dog swim?", "狗 会 游泳 吗", -1)]
    for en, zh, want in pairs:
        out = run(en + "\n" + zh + "\n::quit\n")
        as_ = answers(out)
        pe = polarity(as_[-2]) if len(as_) >= 2 else 0
        pz = polarity(as_[-1]) if as_ else 0
        checks.append(("%s / %s 极性一致(期望 %d)" % (en[:18], zh, want),
                       pe == want and pz == want))

    out = run("cat can sleep\n猫 会 睡觉 吗\ncan a cat sleep?\n::quit\n")
    as_ = answers(out)
    checks.append(("英文教 → 中文问（对）", len(as_) >= 2 and "对" in as_[1]))
    checks.append(("英文教 → 英文问（Yes）", len(as_) >= 3 and "Yes" in as_[2]))

    out = run("rabbit can sing\n兔 会 唱歌 吗\n::quit\n")
    as_ = answers(out)
    checks.append(("新映射 rabbit=兔：英文教 → 中文问（对）",
                   len(as_) >= 2 and "对" in as_[1]))

    out = run("我教你，狗 会 唱歌\ncan a dog sing?\n::quit\n")
    as_ = answers(out)
    checks.append(("中文教 → 英文问（Yes）", bool(as_) and "Yes" in as_[-1]))

    out = run("我教你，狗 会 睡觉\ncan a dog sleep?\n::quit\n")
    as_ = answers(out)
    checks.append(("中文教 → 英文问（二）", bool(as_) and "Yes" in as_[-1]))

    bad = 0
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
        if not good:
            bad += 1
    print("=> 中英互译迁移首跑：%d/%d" % (len(checks) - bad, len(checks)))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
