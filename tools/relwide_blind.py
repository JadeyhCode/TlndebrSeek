#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""relwide_blind.py — §7.078 P2 前置：动态关系压力读数（只读）首跑。

量化现状：96 上限登记失败、id>24 的独占槽缺口、v17 动态关系分布；不扩 id、不改格式。
"""
import os, re, shutil, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "relwide")


def run(inp, model="model.bin"):
    p = subprocess.run([BIN, "--model", model], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def model_version(path):
    with open(path, "rb") as f:
        head = f.read(8)
    if len(head) < 8:
        return None
    _magic, ver = struct.unpack("<II", head)
    return ver


def top_lines(out):
    return [l for l in out.splitlines() if re.match(r"^  #\d+ ", l)]


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
    # 每对主宾都不同：同一对 (甲,乙) 只能挂**一个** dyn（单字节），会被后者覆盖——
    # 这本身是 P2 要修的限制，这里用不同对先量“登记/边”两个维度。
    with open(os.path.join(W, "c100.tsv"), "w", encoding="utf-8") as f:
        for i in range(1, 101):
            f.write("甲%d\t谓%d\t乙%d\n" % (i, i, i))

    checks = []
    base = "::ingest c100.tsv\n"

    out = run("::reldyn 5\n::quit\n")
    checks.append(("基线：96 上限与 id>24 缺口都报",
                   "动态关系 1 / 96" in out and "id>24 的 0 个" in out))

    out = run(base + "::reldyn 3\n::quit\n")
    m = re.search(r"动态关系 (\d+) / 96", out)
    checks.append(("灌满 100 个谓语后登记停在 96", bool(m) and int(m.group(1)) == 96))
    checks.append(("满额告警", "已满" in out and "P2 要扩到 4096" in out))
    m2 = re.search(r"id>24 的 (\d+) 个", out)
    checks.append(("id>24 缺口被量化（96 中有 81）", bool(m2) and int(m2.group(1)) == 81))
    checks.append(("只列 top 3", len(top_lines(out)) == 3 and "边 " in out))

    out2 = run(base + "::reldyn 3\n::quit\n")
    checks.append(("读数确定（两次一致）",
                   re.search(r"动态关系 (\d+) / 96", out2).group(1) == m.group(1) and
                   re.search(r"id>24 的 (\d+)", out2).group(1) == m2.group(1)))

    # v18：v17 输入可读、新档版本号 18、读回动态关系数不变
    run(base + "::save rw18.bin\n::quit\n")
    out3 = run("::reldyn 3\n::quit\n", model="rw18.bin")
    m3 = re.search(r"动态关系 (\d+) / 96", out3)
    oldv = model_version(os.path.join(W, "model.bin"))
    checks.append(("旧档输入可读（出厂 model.bin 是 v%d）" % (oldv or -1), oldv is not None and oldv <= 17))
    checks.append(("新存档版本号 = 18", model_version(os.path.join(W, "rw18.bin")) == 18))
    checks.append(("v18 存读后动态关系数不变", bool(m3) and m3.group(1) == "96"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 动态关系压力首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
