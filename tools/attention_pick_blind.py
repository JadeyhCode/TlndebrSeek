#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attention_pick_blind.py — §7.016 注意力影响行为（取题顺序）首跑

三问：
  ① 读了论文（鲸鱼）之后，pending 里的鲸鱼问题应**先于**更早入队的猫问题被选中；
  ② AIP_ATT=0 时注意力关 ⇒ 退化成“最早入队优先”（猫问题）；
  ③ `::study next` 打出得分（开：>0；关：0.00）。
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "attpick")
PAPER = "根据参考文献，鲸鱼属于哺乳动物。\n作者认为鲸鱼会飞。\n"


def run(inp, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([os.path.join(W, "build_aip"), "--model", "model.bin"],
                       input=inp.encode(), capture_output=True, cwd=W, timeout=120, env=e)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def fresh():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    with open(os.path.join(W, "p.txt"), "w", encoding="utf-8") as f:
        f.write(PAPER)


def main():
    ok = 0
    checks = []
    fresh()
    out = run("::study pose 猫 会 飞 吗\n::paper roles p.txt\n::paper queue\n::study next\n::quit\n")
    checks.append(("开注意力：优先论文里的鲸鱼问题", ("鲸鱼" in out and out.rfind("下一题") > out.rfind("猫 会 飞 吗"))))
    m = re.search(r"下一题（注意力得分 ([\d.]+)）", out)
    checks.append(("开注意力：得分 > 0", bool(m) and float(m.group(1)) > 0))
    fresh()
    out2 = run("::study pose 猫 会 飞 吗\n::paper roles p.txt\n::paper queue\n::study next\n::quit\n",
               env={"AIP_ATT": "0"})
    checks.append(("关注意力：退回最早入队（猫）", ("下一题" in out2 and out2.rfind("猫 会 飞 吗") > 0 and "鲸鱼会飞" not in out2.split("下一题")[-1])))
    m2 = re.search(r"下一题（注意力得分 ([\d.]+)）", out2)
    checks.append(("关注意力：得分 0.00", bool(m2) and float(m2.group(1)) == 0.0))
    # ③ 权重可消融：把两个论文加成置 0，顺序退化成最早入队（猫）
    fresh()
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("att_pick_paper_focus=0\natt_pick_paper_src=0\n")
    out3 = run("::study pose 猫 会 飞 吗\n::paper roles p.txt\n::paper queue\n::study next\n::quit\n")
    m3 = re.search(r"下一题（注意力得分 ([\d.]+)）", out3)
    checks.append(("权重置 0：论文加成消失（得分比默认低 ≥0.7）",
                   bool(m3) and bool(m) and float(m.group(1)) - float(m3.group(1)) >= 0.7))
    # ④ 删 policy.txt 回默认
    fresh()
    os.remove(os.path.join(W, "policy.txt"))
    out4 = run("::study pose 猫 会 飞 吗\n::paper roles p.txt\n::paper queue\n::study next\n::quit\n")
    last4 = out4.split("下一题")[-1] if "下一题" in out4 else ""
    checks.append(("删 policy.txt 回默认（鲸鱼优先）", ("鲸鱼" in last4)))
    for name, good in checks:
        ok += good
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 注意力取题首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
