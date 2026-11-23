#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""paper_focus_blind.py — §7.015 论文→注意力→自学 首跑（离线）

6 项检查：
  ① 角色分类：主张/证据/出处各 1 句判对；
  ② 论文主题词进注意力，来源标「论文」；
  ③ `::paper queue` 只把**无证据的主张**推进队列（1 条）；
  ④ 队列行带出处（文件名）；
  ⑤ `::study list` 看得到这条；
  ⑥ `::study run 1` 会把它当成一道题处理（stats 出题 +1）。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "paperfocus")

TEXT = ("根据参考文献，鲸鱼属于哺乳动物。\n"
        "实验表明，鲸鱼会游泳。\n"
        "作者认为鲸鱼会飞。\n")


def run(inp):
    p = subprocess.run([os.path.join(W, "build_aip"), "--model", "model.bin"],
                       input=inp.encode(), capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    with open(os.path.join(W, "p.txt"), "w", encoding="utf-8") as f:
        f.write(TEXT)
    out = run("::paper roles p.txt\n::att\n::quit\n")
    ok = 0
    checks = []
    # ① 角色
    roles = re.findall(r"\[(主张|证据|限定|出处|陈述)\] ", out)
    roles_ok = roles[:3] == ["出处", "证据", "主张"]
    checks.append(("角色分类（出处/证据/主张）", roles_ok))
    # ② 注意力来源「论文」
    checks.append(("注意力来源标论文", ("来源 论文" in out)))
    out2 = run("::paper queue\n::study list\n::quit\n")
    # ③ 只推 1 条
    m = re.search(r"推进自学队列 (\d+) 条", out2)
    checks.append(("只推无证据的主张 1 条", bool(m) and m.group(1) == "1"))
    # ④ 出处
    tsv = os.path.join(W, "_t", "curious.tsv")
    rows = [l for l in open(tsv, encoding="utf-8", errors="replace")] if os.path.isfile(tsv) else []
    checks.append(("队列行带出处（p.txt）", any("出处：p.txt" in l for l in rows)))
    # ⑤ list 看得到
    checks.append(("study list 看得到", ("鲸鱼会飞" in out2)))
    # ⑥ study 会处理
    out3 = run("::study run 1\n::quit\n")
    checks.append(("study 把它当一道题处理", ("出题 1" in out3 or "出题（来自好奇心队列）" in out3)))
    for name, good in checks:
        ok += good
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 论文→注意力→自学 首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
