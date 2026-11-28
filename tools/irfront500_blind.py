#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irfront500_blind.py — §7.103 IR 前置 500 句规模对照（答案差异率 / UNKNOWN / 延迟）。"""
import json, os, re, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "irfront500")
N = 500

SUBJECTS = ["猫", "狗", "鱼", "鸟", "老鼠", "桌子", "石头", "人", "动物", "植物"]
RELATIONS = ["属于", "属于", "会", "吃", "怕"]
OBJECTS = ["动物", "植物", "生物", "鱼", "老鼠", "毛", "飞", "水", "食物", "桌子"]


def build_sentences():
    out = []
    for i in range(N):
        s = SUBJECTS[i % len(SUBJECTS)]
        r = RELATIONS[(i // len(SUBJECTS)) % len(RELATIONS)]
        o = OBJECTS[(i * 7) % len(OBJECTS)]
        if r == "属于" and i % 25 == 0:
            r = "是"          # 别名写法：IR 前置应回写成「属于」
        out.append("%s %s %s 吗" % (s, r, o))
    return out


def run(inp, env=None):
    t0 = time.monotonic()
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=600, env=e)
    dt = time.monotonic() - t0
    return (p.stdout + p.stderr).decode("utf-8", "replace"), dt


def set_policy(text):
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(text)


def norm(a):
    for p in ("估计，", "应该，", "大概 吧，", "大概，"):
        if a.startswith(p):
            a = a[len(p):]
    return a


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
    sents = build_sentences()
    lines = list(sents)
    base_batch = "".join(s + "\n" for s in lines)
    batch = base_batch + "::quit\n"

    set_policy(orig)
    off_out, off_dt = run(batch)
    off_ans = [l.split("AI > ", 1)[1] for l in off_out.splitlines() if "AI > " in l]

    set_policy(orig + "\nir_front=1\n")
    on_out, on_dt = run(base_batch + "::irfront show\n::quit\n")
    on_ans = [l.split("AI > ", 1)[1] for l in on_out.splitlines() if "AI > " in l]

    m = re.search(r"尝试 (\d+)，回写 (\d+)，UNKNOWN (\d+)，原样 (\d+)，命令跳过 (\d+)", on_out)
    checks = []
    changed = [(i, sents[i], a, b) for i, (a, b) in enumerate(zip(off_ans, on_ans))
               if norm(a) != norm(b)]
    checks.append(("500 句两模式都跑完（无崩溃/截断）",
                   len(off_ans) == N and len(on_ans) == N))
    checks.append(("答案变化率 = 0（去掉随机语气前缀后）", len(changed) == 0))
    if changed:
        for row in changed[:3]:
            print("    CHANGED", row)
    checks.append(("统计覆盖全部 500 句：rewrites+unknown+same == tries",
                   bool(m) and int(m.group(2)) + int(m.group(3)) + int(m.group(4)) == int(m.group(1))
                   and int(m.group(1)) == N))
    checks.append(("规模下有实际回写（rewrites>0）", bool(m) and int(m.group(2)) > 0))
    checks.append(("规模下有 UNKNOWN 透传（unknown>0）", bool(m) and int(m.group(3)) > 0))
    checks.append(("前置延迟可接受（≤ 3× 基线 + 5s）", on_dt <= off_dt * 3 + 5))
    checks.append(("延迟读数（仅记录）", True))

    # 差异账本（工具侧）：只写有差异的行
    diffp = os.path.join(W, "_t", "ir_front_diff.tsv")
    os.makedirs(os.path.dirname(diffp), exist_ok=True)
    with open(diffp, "w", encoding="utf-8") as f:
        for i, s, a, b in changed:
            f.write("%d\t%s\t%s\t%s\t%s\n" % (i, s, a, b, "否"))
    checks.append(("差异账本行数 = 变化数", len(open(diffp, encoding="utf-8").read().splitlines()) == len(changed)))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    if m:
        print("  读数：tries=%s rewrites=%s unknown=%s same=%s cmds=%s ｜ 基线 %.2fs / 前置 %.2fs"
              % (m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), off_dt, on_dt))
    print("=> 前置 500 句规模首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
