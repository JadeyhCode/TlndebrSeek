#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§6.971 长文/多句理解盲测（10 题首跑）：多句事实、代词、传递、列举、否定一致性、纠错。
每题把若干句（有的是一条长段落按句号拆开）逐句喂进去，再问；判分看期望串。不联网。
"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
MODEL = os.path.join(ROOT, "model.bin")
W = os.path.join(ROOT, "_t", "longblind")

TASKS = [
    ("传递推理", ["我教你，貘 属于 奇蹄目", "我教你，奇蹄目 属于 哺乳动物"],
     [("貘 属于 什么", "奇蹄目"), ("貘 属于 哺乳动物 吗", "对")]),
    ("代词指代", ["我教你，树懒 住 在 树上", "我教你，树懒 吃 叶子"],
     [("树懒 吃 什么", "叶子")]),
    ("列举", ["我教你，猫 属于 动物", "我教你，狗 属于 动物", "我教你，马 属于 动物"],
     [("哪些 属于 动物", "狗"), ("谁 属于 动物", "马")]),
    ("否定一致性", ["我教你，企鹅 不 会 飞"], [("企鹅 会 飞 吗", "不")]),
    ("纠错", ["我教你，貘 属于 偶蹄目", "不对，貘 属于 奇蹄目"], [("貘 属于 什么", "奇蹄目")]),
    ("多跳", ["我教你，雪豹 属于 猫科", "我教你，猫科 属于 食肉目"],
     [("雪豹 属于 食肉目 吗", "对")]),
    ("长段落一句喂", ["我教你，貘 属于 奇蹄目。貘 会 游泳。貘 住 在 河边"],
     [("貘 会 什么", "游泳")]),
    ("属性追问", ["我教你，珠峰 很 高"], [("珠峰 高 吗", "高")]),
    ("数量/存在", ["我教你，猫 属于 动物"], [("动物 有 什么", "猫")]),
    ("反义对照", ["我教你，企鹅 不 会 飞", "我教你，鹰 会 飞"],
     [("鹰 会 飞 吗", "对"), ("企鹅 会 飞 吗", "不")]),
]

def run(lines):
    inp = "::notepad off\n::char off\n::hypo cache off\n::rel analogy off\n"
    inp += "\n".join(lines) + "\n::quit\n"
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp, text=True,
                       encoding="utf-8", errors="replace", capture_output=True, cwd=W, timeout=240)
    return p.stdout

def replies(out):
    return [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]

def main():
    if not os.path.isfile(BIN) or not os.path.isfile(MODEL):
        print("缺 build_aip/model.bin"); return 2
    shutil.rmtree(W, ignore_errors=True); os.makedirs(W)
    shutil.copy(MODEL, os.path.join(W, "model.bin")); shutil.copy(BIN, os.path.join(W, "build_aip"))
    for f in ("patterns.txt", "frames.txt", "relations.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src): shutil.copy(src, os.path.join(W, f))
    res = {"pass": 0, "refuse": 0, "wrong": 0}
    for name, facts, asks in TASKS:
        out = run(list(facts) + [q for q, _ in asks])
        rs = replies(out)
        ok = True; refuse = False
        for k, (q, want) in enumerate(asks):
            idx = len(facts) + k
            got = rs[idx] if idx < len(rs) else ""
            if want not in got:
                ok = False
                if any(w in got for w in ("不 会", "不 知道", "没 记 过", "不 太 懂", "不 认识")):
                    refuse = True
                print("  [MISS] %-12s %s => %r（要 %r）" % (name, q, got.strip()[:60], want))
        if ok: res["pass"] += 1; print("  [PASS] %s" % name)
        elif refuse: res["refuse"] += 1; print("  [REFUSE] %s" % name)
        else: res["wrong"] += 1; print("  [WRONG] %s" % name)
    print("=> pass %d / refuse %d / wrong %d（共 %d）" %
          (res["pass"], res["refuse"], res["wrong"], len(TASKS)))
    return 0

if __name__ == "__main__":
    sys.exit(main())
