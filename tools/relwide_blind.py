#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""relwide_blind.py — §7.089 P2b-4 RelId 扩宽（4096 动态关系）首跑。

96→245→4096；REL_TABLE_MAX=4105（uint16）；v18 存档 LEB128 不变即可容纳。
检查：满额 4096、高 id 可问、存档读回、旧档可读、软上限消融。
"""
import os, re, shutil, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "relwide")
CAP = 4096


def run(inp, model="model.bin", env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([BIN, "--model", model], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=240, env=e)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def model_version(path):
    with open(path, "rb") as f:
        head = f.read(8)
    if len(head) < 8:
        return None
    return struct.unpack("<II", head)[1]


def pn(i):
    return "谓" + chr(0x4e00 + (i % 20000))


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
    for name, n in (("c5000.tsv", 5000), ("c20.tsv", 20)):
        with open(os.path.join(W, name), "w", encoding="utf-8") as f:
            for i in range(1, n + 1):
                f.write("甲%d\t%s\t乙%d\n" % (i, pn(i), i))
    checks = []

    out = run("::reldyn 2\n::quit\n")
    checks.append(("基线：4096 上限 + REL_TABLE_MAX=4105，无缺口",
                   "动态关系 1 / 4096" in out and "REL_TABLE_MAX=4105" in out
                   and "id>24 的 0 个" in out))

    out = run("::ingest c5000.tsv\n::reldyn 2\n::quit\n")
    m = re.search(r"动态关系 (\d+) / %d" % CAP, out)
    checks.append(("灌 5000 个谓语后停在 4096", bool(m) and int(m.group(1)) == CAP))
    checks.append(("满额告警（编译上限 4096）", "已满" in out and "4096" in out))

    out = run("::ingest c5000.tsv\n甲3999 %s 乙3999 吗\n::rel 甲3999\n::quit\n" % pn(3999))
    checks.append(("高 id 动态关系可问（id≈4000）",
                   "对" in out and pn(3999) in out))

    run("::ingest c5000.tsv\n::save rw4096.bin\n::quit\n")
    out = run("甲3999 %s 乙3999 吗\n::reldyn 2\n::quit\n" % pn(3999), model="rw4096.bin")
    checks.append(("v18 存读后 4096 dyn 与高 id 边都在",
                   "动态关系 4096 / 4096" in out and "对" in out and pn(3999) in out))
    oldv = model_version(os.path.join(W, "model.bin"))
    checks.append(("旧档输入可读、新档版本 18",
                   oldv is not None and oldv <= 17 and
                   model_version(os.path.join(W, "rw4096.bin")) == 18))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("dynrel_soft_limit=8\n")
    out = run("::ingest c20.tsv\n::reldyn 2\n::quit\n")
    m3 = re.search(r"动态关系 (\d+) / 4096", out)
    checks.append(("消融：软上限 8 ⇒ 只登记 8 个",
                   bool(m3) and int(m3.group(1)) == 8 and "当前上限 8" in out))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    out = run("::ingest c5000.tsv\n::reldyn 2\n::quit\n")
    checks.append(("读数确定（两次一致）",
                   re.search(r"动态关系 (\d+) / 4096", out).group(1) == str(CAP)))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> RelId 扩宽/4096 首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
