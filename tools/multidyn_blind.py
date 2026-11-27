#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""multidyn_blind.py — §7.082 同一对多动态关系（AIP_MULTIDYN=1 开；默认关=旧行为）首跑。"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "multidyn")


def run(inp, model="model.bin", env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([BIN, "--model", model], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180, env=e)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def rel_edges(out):
    return [l for l in out.splitlines() if re.search(r"--\[谓[一二三]\]-->", l)]


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt",
              "policy.txt", "relations_beh.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    with open(os.path.join(W, "c.tsv"), "w", encoding="utf-8") as f:
        f.write("甲\t谓一\t乙\n甲\t谓二\t乙\n甲\t谓三\t乙\n")
    checks = []

    out = run("::ingest c.tsv\n甲 谓一 乙 吗\n甲 谓二 乙 吗\n甲 谓三 乙 吗\n::quit\n",
              env={"AIP_MULTIDYN": "1"})
    checks.append(("同对三条动态关系全部可问", out.count("AI > 对") == 3))

    out = run("::ingest c.tsv\n::rel 甲\n::quit\n", env={"AIP_MULTIDYN": "1"})
    checks.append(("::rel 列出三条动态边", len(rel_edges(out)) == 3))

    out = run("::ingest c.tsv\n::ingest c.tsv\n::rel 甲\n::quit\n", env={"AIP_MULTIDYN": "1"})
    checks.append(("重复灌入幂等（仍 3 条）", len(rel_edges(out)) == 3))

    run("::ingest c.tsv\n::save md.bin\n::quit\n", env={"AIP_MULTIDYN": "1"})
    out = run("甲 谓一 乙 吗\n甲 谓二 乙 吗\n甲 谓三 乙 吗\n::quit\n", model="md.bin",
              env={"AIP_MULTIDYN": "1"})
    checks.append(("v18 存读后三条都还在", out.count("AI > 对") == 3))

    out = run("::ingest c.tsv\n甲 谓一 乙 吗\n::gap 甲 谓一 乙\n::quit\n",
              env={"AIP_MULTIDYN": "1"})
    checks.append(("动态关系可被 ::gap 认出", "已能回答" in out))

    out = run("::ingest c.tsv\n甲 谓一 乙 吗\n甲 谓三 乙 吗\n::rel 甲\n::quit\n")
    checks.append(("默认（未设 AIP_MULTIDYN）仍是旧覆盖行为（只有最后一条）",
                   "AI > 对" in out and "谓三" in out and
                   out.count("AI > 对") == 1 and len(rel_edges(out)) == 1))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 同对多动态关系首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
