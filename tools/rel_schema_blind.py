#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""rel_schema_blind.py — §7.073 P0 关系 schema 数据层（首跑）。

检查：9 核心 schema 与 AI_RELS 逐条一致；别名；逆关系；动态纯标签；7 类非法行被拒且带行号；
AIP_NOSCHEMA=1 回退一致；缓存命中；缺数据文件回退；schema/NOSCHEMA 推理答案逐字相同（消融）。
"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "relschema")
DATA = ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt", "policy.txt", "laws.txt")

def run(inp, cwd=None, env=None):
    e = dict(os.environ)
    if env: e.update(env)
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=cwd or W, timeout=180, env=e)
    return (p.stdout + p.stderr).decode("utf-8", "replace")

def setup(d, schema=True):
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    shutil.copy(BIN, os.path.join(d, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(d, "model.bin"))
    for f in DATA:
        src = os.path.join(ROOT, f)
        if os.path.isfile(src): shutil.copy(src, os.path.join(d, f))
    if schema:
        shutil.copy(os.path.join(ROOT, "relations_beh.txt"), os.path.join(d, "relations_beh.txt"))

def main():
    setup(W)
    checks = []
    out = run("::relbeh\n::quit\n")
    checks.append(("载入 9 核心 + 2 别名，0 非法",
                   "有效 12 条，非法 0 行" in out and "推理读 schema" in out))

    expect = {
        "属于": ("trans,excl", "包含", "single"),
        "包含": ("-", "属于", "multi"),
        "有": ("inherit", "-", "multi"),
        "会": ("inherit,prereq", "-", "multi"),
        "怕": ("sym", "-", "multi"),
        "喜欢": ("-", "-", "multi"),
        "吃": ("-", "-", "multi"),
        "在": ("excl", "-", "single"),
        "需要": ("-", "-", "multi"),
    }
    bad = []
    for n, (fl, inv, card) in expect.items():
        d = run("::relbeh %s\n::quit\n" % n)
        if ("flags=" + fl) not in d or ("inv=" + inv) not in d or ("card=" + card) not in d:
            bad.append(n)
    checks.append(("9 核心逐条与 AI_RELS 一致", not bad))

    out = run("::relbeh 是\n::relbeh 爱\n::quit\n")
    checks.append(("别名：是→属于、爱→喜欢",
                   "是 是别名 → 属于" in out and "爱 是别名 → 喜欢" in out))

    out = run("::relbeh 想念\n::quit\n")
    checks.append(("无 schema 的动态关系是纯标签", "无 schema" in out and "纯标签" in out))

    # 非法行
    BAD = os.path.join(ROOT, "_t", "relschema_bad")
    setup(BAD)
    with open(os.path.join(BAD, "relations_beh.txt"), "w", encoding="utf-8") as f:
        f.write("属于 | trans,excl | inv=包含 | card=single\n")
        f.write("坏1 | causal,sym\n坏2 | functional,multi\n坏3 | trans,anti-trans\n")
        f.write("坏4 | inv=包含\n坏5 | dim=3\n坏6 | wishful\n坏7 | alias=不存在\n")
    out = run("::relbeh\n::quit\n", cwd=BAD)
    nums = [n for n in (2,3,4,5,6,7,8) if ("relations_beh.txt:%d 非法" % n) in out]
    checks.append(("7 类非法行被拒且带行号", len(nums) == 7 and "有效 1 条，非法 7 行" in out))

    # NOSCHEMA 回退
    out = run("::relbeh 属于\n::quit\n", env={"AIP_NOSCHEMA": "1"})
    checks.append(("AIP_NOSCHEMA=1 回退 AI_RELS",
                   "回退 AI_RELS" in out and "trans=1" in out and "excl=1" in out))

    # 缓存
    out = run("::relbeh 属于\n::relbeh\n::quit\n")
    m = re.search(r"hit=(\d+) miss=(\d+)", out)
    checks.append(("schema 缓存有命中", bool(m) and int(m.group(1)) > 0))

    # 缺文件回退
    MISS = os.path.join(ROOT, "_t", "relschema_miss")
    setup(MISS, schema=False)
    out = run("::relbeh 属于\n::quit\n", cwd=MISS)
    checks.append(("缺 relations_beh.txt 时回退且能启动",
                   "回退 AI_RELS" in out and "trans=1" in out))

    # 消融：schema vs NOSCHEMA 推理答案逐字相同
    base = "::ingest c.tsv\n"
    q = ("甲 属于 丙 吗\n丙 属于 甲 吗\n猫 属于 鸟 吗\n::quit\n")
    for d in (W, BAD, MISS):
        src = os.path.join(ROOT, "c.tsv")
        if os.path.isfile(src): shutil.copy(src, os.path.join(d, "c.tsv"))
    with open(os.path.join(W, "c.tsv"), "w", encoding="utf-8") as f:
        f.write("甲\t属于\t乙\n乙\t属于\t丙\n猫\t属于\t哺乳动物\n")
    on = [l for l in run(base + q).splitlines() if "AI >" in l]
    off = [l for l in run(base + q, env={"AIP_NOSCHEMA": "1"}).splitlines() if "AI >" in l]
    checks.append(("消融：schema 与回退推理答案逐字一致", on == off and len(on) == 3))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 关系 schema 首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1

if __name__ == "__main__":
    sys.exit(main())
