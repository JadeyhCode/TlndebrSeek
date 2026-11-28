#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pathsim_blind.py — §7.090 类型化路径相似（禁稠密向量）首跑。"""
import os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "pathsim")

CORPUS = ("犰狳\t标甲\t螭吻\n貔貅\t标甲\t螭吻\n犰狳\t标乙\t狻猊\n"
          "螭吻\t包含\t犰狳\n")
DEGREE = "中心\t标丙\t叶%d\n"


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


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
    with open(os.path.join(W, "c.tsv"), "w", encoding="utf-8") as f:
        f.write(CORPUS)
        for i in range(1, 41):
            f.write(DEGREE % i)
    base = "::ingest c.tsv\n"
    checks = []

    out = run(base + "::pathsim 犰狳 貔貅\n::quit\n")
    m = re.search(r"⇒ ([0-9.]+)（", out)
    checks.append(("共享路径 ⇒ 相似度 > 0.1", bool(m) and float(m.group(1)) > 0.1))
    checks.append(("给出 top-3 证据（标甲→螭吻）", "证据:" in out and "标甲" in out))

    out = run(base + "::pathsim 的 犰狳\n::quit\n")
    checks.append(("无路径 ⇒ 未知（不是 0）", "未知" in out and "不是 0" in out))

    out = run(base + "::pathsig 中心\n::quit\n")
    mc = re.search(r"类型化路径 (\d+) 条", out)
    checks.append(("度截断后最多 32 条", bool(mc) and int(mc.group(1)) == 32))

    out = run(base + "::pathsig 螭吻\n::quit\n")
    checks.append(("逆关系方向被规范化（出现反向标记）", "<-包含->" in out or "<-属于->" in out))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("sim_w_path=0\nsim_w_nbr=0.3\n")
    out = run(base + "::pathsim 犰狳 貔貅\n::quit\n")
    checks.append(("消融：w_path=0 ⇒ 分数只由邻居构成", "w_path=0.00" in out and "⇒ 0.15" in out))
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(orig)

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("sim_mode=emb\n")
    out = run(base + "::pathsim 犰狳 貔貅\n::quit\n")
    checks.append(("sim_mode=emb 被拒（禁止稠密向量进核）", "未启用" in out and "稠密向量" in out))
    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write(orig)

    o1 = run(base + "::pathsim 犰狳 貔貅\n::quit\n")
    o2 = run(base + "::pathsim 犰狳 貔貅\n::quit\n")
    checks.append(("读数确定（两次一致）", o1 == o2))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 类型化路径相似首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
