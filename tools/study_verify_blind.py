#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""study_verify_blind.py — §7.070 verified self-solving (③) first run.

Self-judged “solved” is not proof. After a self-answer, the kernel now rechecks the graph:
direct edge → 直边, derived/cached edge → 传递（缓存边）, transitive path → 传递路径 N 跳, otherwise
未验证. Stats split verified/unverified; `study_verify=0` disables the recheck (ablation).
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "studyverify")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def read(p):
    return open(p, encoding="utf-8", errors="replace").read() if os.path.isfile(p) else ""


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    with open(os.path.join(W, "c.tsv"), "w", encoding="utf-8") as f:
        f.write("甲\t属于\t乙\n乙\t属于\t丙\n")
    with open(os.path.join(W, "c2.tsv"), "w", encoding="utf-8") as f:
        f.write("天\t属于\t地\n")
    base = "::ingest c.tsv\n"

    def clear_stats():
        # 统计是累计文件；每次测量前清掉，按“单次运行”读数判分
        p = os.path.join(W, "_t", "study", "stats.tsv")
        if os.path.isfile(p):
            os.remove(p)

    checks = []
    clear_stats()
    out = run(base + "::study pose 甲 属于 乙 吗\n::study next run\n::quit\n")
    checks.append(("直边：复核=直边 + 统计已验证 1", "[自学] 复核：直边" in out and "已验证 1 / 未验证 0" in out))

    clear_stats()
    out = run(base + "::study pose 甲 属于 丙 吗\n::study next run\n::quit\n")
    checks.append(("传递：复核=传递（缓存边）", "复核：传递（缓存边）" in out))

    clear_stats()
    out = run(base + "::study pose 丙 属于 甲 吗\n::study next run\n::quit\n")
    checks.append(("无依据：复核=未验证", "复核：未验证" in out))
    checks.append(("统计把未验证单列", "已验证 0 / 未验证 1" in out))

    prop = read(os.path.join(W, "_t", "study", "proposals.tsv"))
    checks.append(("待证带验证标注", "自解（已验证）" in prop and "自解（未验证）" in prop))

    # 消融用**新题面**：::study pose 对同一题 24h 去重，重复 pose 不会入队
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("study_verify=0\n")
    clear_stats()
    out = run("::ingest c2.tsv\n::study pose 天 属于 地 吗\n::study next run\n::quit\n")
    checks.append(("消融：关掉复核后明说“关”、全按未验证",
                   "复核：关（study_verify=0）" in out and "已验证 0 / 未验证 1" in out))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 可验证自解首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
