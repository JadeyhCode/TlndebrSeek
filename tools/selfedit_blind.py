#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""selfedit_blind.py — §7.062 guarded data-file self-edit (E18 step) first run.

Checks: gate/reason required; allowed file only; format/length checks; append/replace policy key
with backup + ledger; new process sees the effect; rollback restores it; rollback without backup
says so.
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "selfedit")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def topk():
    out = run("::att\n::quit\n")
    m = re.search(r"top-k (\d+)", out)
    return int(m.group(1)) if m else None


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
    out = run("::self edit policy.txt att_topk=2\n::quit\n")
    checks.append(("没开门/没理由 → 拒绝", "只读模式" in out or "必须给理由" in out))

    out = run("::sym write on\n::self edit policy.txt att_topk=2\n::quit\n")
    checks.append(("没理由 → 拒绝", "必须给理由" in out))

    out = run("::sym write on\n::sym reason 盲测自改\n::self edit build_aip foo=1\n::quit\n")
    checks.append(("非允许文件 → 拒绝", "只允许" in out))

    out = run("::sym write on\n::sym reason 盲测自改\n::self edit policy.txt x=1\n::quit\n")
    checks.append(("格式检查放过 key=value", "已写入" in out))

    # 真正的效果：替换 att_topk 并为新进程所见
    run("::sym write on\n::sym reason 盲测自改\n::self edit policy.txt att_topk=2\n::quit\n")
    checks.append(("新进程 top-k = 2", topk() == 2))
    led = os.path.join(W, "_t", "self", "ledger.tsv")
    checks.append(("账本记录（含理由）", os.path.isfile(led) and "盲测自改" in open(led, encoding="utf-8").read()))
    bk = os.path.join(W, "_t", "self", "backup")
    checks.append(("备份文件存在", os.path.isdir(bk) and len(os.listdir(bk)) >= 1))

    out = run("::self rollback\n::quit\n")
    checks.append(("回滚成功", "已回滚" in out and topk() == 5))

    out = run("::self rollback\n::quit\n")
    checks.append(("无备份回滚 → 明说", "没有可回滚" in out))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 数据文件自改首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
