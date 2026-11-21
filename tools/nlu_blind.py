#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""§6.970 NLU 盲测集（20 题，首跑读数）：指令学习/纠错/定义句/否定/追问/同义/多轮指代。
每题先教后问；判分只看**答复里有没有期望串**（不比对整句）。不联网。
"""
import os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
MODEL = os.path.join(ROOT, "model.bin")
W = os.path.join(ROOT, "_t", "nlublind")

# (名字, 前几句, [(问句, 期望串)])
TASKS = [
    ("无空格指令学习", ["我教你，貘 属于 奇蹄目"], [("貘 属于 什么", "奇蹄目")]),
    ("有空格指令学习", ["我 教 你 ， 树懒 属于 披毛目"], [("树懒 属于 什么", "披毛目")]),
    ("纠错改口", ["我教你，貘 属于 偶蹄目", "不对，貘 属于 奇蹄目"], [("貘 属于 什么", "奇蹄目")]),
    ("全称句", ["所有 的 雪豹 都 属于 猫科"], [("雪豹 属于 什么", "猫科")]),
    ("是 一种 定义", ["雪貂 是 一种 鼬科动物"], [("雪貂 属于 什么", "鼬科")]),
    ("否定事实", ["鲸鱼 不 是 鱼"], [("鲸鱼 是 鱼 吗", "不")]),
    ("反问标记", ["难道 猫 会 飞 吗"], [("猫 会 飞 吗", "不")]),
    ("追问 那X呢", ["猫 属于 动物", "狗 属于 动物"], [("那 狗 呢", "动物")]),
    ("同义词 猫咪", ["猫 喜欢 鱼"], [("猫咪 喜欢 什么", "鱼")]),
    ("同义词 小鲸鱼", ["鲸鱼 属于 哺乳动物"], [("小鲸鱼 属于 什么", "哺乳动物")]),
    ("多轮主题延续", ["猫 属于 动物"], [("它 属于 什么", "动物")]),
    ("谁 属于", ["猫 属于 动物", "狗 属于 动物"], [("谁 属于 动物", "猫")]),
    ("哪些 属于", ["猫 属于 动物", "狗 属于 动物"], [("哪些 属于 动物", "狗")]),
    ("既有知识问1", [], [("猫 属于 什么", "动物")]),
    ("既有知识问2", [], [("猫 喜欢 什么", "鱼")]),
    ("既有知识问3", [], [("鲸鱼 属于 什么", "哺乳")]),
    ("否定问句2", ["鲸鱼 不 是 鱼"], [("鲸鱼 属于 鱼 吗", "不")]),
    ("教属性句", ["我教你，南极 很 冷"], [("南极 冷 吗", "冷")]),
    ("教 会 句", ["我教你，企鹅 会 游泳"], [("企鹅 会 什么", "游泳")]),
    ("多句连教", ["我教你，貘 属于 奇蹄目", "我教你，貘 会 游泳"], [("貘 会 什么", "游泳")]),
]

def run(lines):
    inp = "::notepad off\n::char off\n::hypo cache off\n::rel analogy off\n"
    for l in lines:
        inp += l + "\n"
    inp += "::quit\n"
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp, text=True,
                       encoding="utf-8", errors="replace", capture_output=True, cwd=W, timeout=180)
    return p.stdout

def replies(out):
    r = []
    for line in out.splitlines():
        i = line.find("AI > ")
        if i >= 0:
            r.append(line[i + 5:])
    return r

def main():
    if not os.path.isfile(BIN) or not os.path.isfile(MODEL):
        print("缺 build_aip/model.bin"); return 2
    shutil.rmtree(W, ignore_errors=True); os.makedirs(W)
    shutil.copy(MODEL, os.path.join(W, "model.bin")); shutil.copy(BIN, os.path.join(W, "build_aip"))
    for f in ("patterns.txt", "frames.txt", "relations.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src): shutil.copy(src, os.path.join(W, f))
    res = {"pass": 0, "refuse": 0, "wrong": 0}
    for name, teach, asks in TASKS:
        lines = list(teach) + [q for q, _ in asks]
        out = run(lines)
        rs = replies(out)
        ok = True; refuse = False
        for k, (q, want) in enumerate(asks):
            idx = len(teach) + k
            got = rs[idx] if idx < len(rs) else ""
            if want not in got:
                ok = False
                if any(w in got for w in ("不 会", "不 知道", "没 记 过", "不 太 懂", "不 认识")):
                    refuse = True
                print("  [%s] %-10s %s => %r（要 %r）" %
                      ("MISS", name, q, got.strip()[:60], want))
        if ok:
            res["pass"] += 1; print("  [PASS] %s" % name)
        elif refuse:
            res["refuse"] += 1; print("  [REFUSE] %s" % name)
        else:
            res["wrong"] += 1; print("  [WRONG] %s" % name)
    print("=> pass %d / refuse %d / wrong %d（共 %d）" %
          (res["pass"], res["refuse"], res["wrong"], len(TASKS)))
    return 0

if __name__ == "__main__":
    sys.exit(main())
