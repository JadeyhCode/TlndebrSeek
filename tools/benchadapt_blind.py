#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""benchadapt_blind.py — §7.116 P4 GSM8K 官方子集适配首跑（含污染检查与消融）。"""
import hashlib, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "benchadapt.py")
DATA = os.path.join(ROOT, "tests", "data", "gsm8k_test20.jsonl")
README = os.path.join(ROOT, "tests", "data", "README.md")
W = os.path.join(ROOT, "_t", "benchadapt")


def run():
    p = subprocess.run([sys.executable, TOOL], capture_output=True, cwd=ROOT, timeout=900)
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


def main():
    checks = []
    rows = [json.loads(l) for l in open(DATA, encoding="utf-8") if l.strip()]
    checks.append(("官方子集 20 题", len(rows) == 20 and all("question" in r and "####" in r["answer"] for r in rows)))

    readme = open(README, encoding="utf-8").read()
    h = hashlib.sha256(open(DATA, "rb").read()).hexdigest()
    checks.append(("README 记录子集 sha256 且一致", h in readme))
    checks.append(("README 写清来源/许可/抽样规则",
                   "grade-school-math" in readme and "MIT" in readme and "每隔 65" in readme))

    rc, out = run()
    checks.append(("工具正常退出", rc == 0))
    m = re.search(r"pass (\d+) / refuse (\d+) / wrong (\d+)（共 (\d+)）", out)
    checks.append(("计数完整（三类和=20）", bool(m) and int(m.group(4)) == 20 and
                   int(m.group(1)) + int(m.group(2)) + int(m.group(3)) == 20))
    checks.append(("消融行存在且 pass 不增", "消融 adapter_en_math=0" in out and "应不增" in out))
    checks.append(("污染检查有读数（逐字+5-gram）", "问题逐字命中" in out and "5-gram 命中" in out))
    checks.append(("如实提示低分不调题", "不调题、不改判分" in out))

    tsv = os.path.join(ROOT, "_t", "benchadapt_gsm8k.tsv")
    lines = open(tsv, encoding="utf-8").read().splitlines() if os.path.isfile(tsv) else []
    checks.append(("TSV 20 行且判定合法",
                   len(lines) == 20 and all(l.split("\t")[2] in ("pass", "refuse", "wrong") for l in lines)))

    rc2, out2 = run()
    counts = lambda s: re.search(r"pass (\d+) / refuse (\d+) / wrong (\d+)（共 \d+）", s).groups()
    checks.append(("读数可重复（两次计数一致）", rc2 == 0 and bool(m) and counts(out) == counts(out2)))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> GSM8K 官方子集适配首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
