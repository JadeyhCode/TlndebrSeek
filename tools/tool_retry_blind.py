#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tool_retry_blind.py — §7.024 外部工具失败重试首跑（本地假端点，503 一次）

3 项：
  ① 假端点第一次 503、第二次正常 ⇒ `::tool ask` 仍能拿到答复（重试生效）；
  ② tool.log 里有“重试后成功”的审计行；
  ③ `tool_retries=0` 时同样的 503 一次 ⇒ 直接失败，不重试。
"""
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "toolretry")


def start(fail_first):
    p = subprocess.Popen([sys.executable, os.path.join(ROOT, "tools", "fake_openai.py"),
                          "--port", "0", "--fail-first", str(fail_first),
                          "--reply", "重试成功答复"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, cwd=W)
    port = None
    for _ in range(100):
        line = p.stdout.readline()
        if line:
            port = "".join(ch for ch in line if ch.isdigit())
            if port:
                break
        time.sleep(0.05)
    return p, port


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=120)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def fresh(policy=None):
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    if policy is not None:
        with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
            f.write(policy)


def main():
    checks = []
    fresh()
    srv, port = start(1)
    try:
        out = run("::tool set http://127.0.0.1:%s/v1 k m\n::tool on\n::tool ask 你好\n::quit\n" % port)
        checks.append(("503 一次后重试拿到答复", "重试成功答复" in out))
        log = ""
        if os.path.isfile(os.path.join(W, "tool.log")):
            log = open(os.path.join(W, "tool.log"), encoding="utf-8", errors="replace").read()
        checks.append(("审计里有“重试后成功”", "重试后成功" in log))
    finally:
        srv.terminate()
    fresh("tool_retries=0\n")
    srv, port = start(1)
    try:
        out = run("::tool set http://127.0.0.1:%s/v1 k m\n::tool on\n::tool ask 你好\n::quit\n" % port)
        checks.append(("tool_retries=0 时不重试（失败）", "没答上来" in out and "重试成功答复" not in out))
    finally:
        srv.terminate()
    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 工具重试首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
