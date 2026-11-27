#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""relwide_blind.py — §7.080 P2a 动态关系容量/查询/迁移（只读+策略）首跑。

96→245（uint8 id 上限）、REL_TABLE_MAX=255（独占槽覆盖全部 uint8 id）、
v18 存档迁移、软上限消融；4096 需 RelId 扩宽，列为 P2b（未做）。
"""
import os, re, shutil, struct, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "relwide")


def run(inp, model="model.bin", env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([BIN, "--model", model], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180, env=e)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def model_version(path):
    with open(path, "rb") as f:
        head = f.read(8)
    if len(head) < 8:
        return None
    return struct.unpack("<II", head)[1]


def pred_name(i):
    return "谓" + chr(0x4e00 + i)          # 全 CJK，避免数字被切词


def corpus(path, n):
    with open(path, "w", encoding="utf-8") as f:
        for i in range(1, n + 1):
            f.write("甲%d\t%s\t乙%d\n" % (i, pred_name(i), i))


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
    corpus(os.path.join(W, "c300.tsv"), 300)
    corpus(os.path.join(W, "c20.tsv"), 20)
    checks = []

    out = run("::reldyn 3\n::quit\n")
    checks.append(("基线：245 上限 + 255 表 + 无缺口",
                   "动态关系 1 / 245" in out and "REL_TABLE_MAX=255" in out
                   and "id>24 的 0 个" in out))

    out = run("::ingest c300.tsv\n::reldyn 3\n::quit\n")
    m = re.search(r"动态关系 (\d+) / 245", out)
    checks.append(("灌 300 个谓语后停在 245", bool(m) and int(m.group(1)) == 245))
    checks.append(("满额告警（P2b 4096）", "已满" in out and "P2b" in out and "4096" in out))
    checks.append(("id>24 缺口消失（255 覆盖）", "id>24 的 0 个" in out))

    out = run("::ingest c300.tsv\n::rel 甲244\n::quit\n")
    checks.append(("高 id 动态边可查（::rel 甲244，模型自带 1 个 dyn 占 1 格）",
                   pred_name(244) in out and "乙244" in out))

    run("::ingest c300.tsv\n::save rw18b.bin\n::quit\n")
    out2 = run("::reldyn 3\n::rel 甲244\n::quit\n", model="rw18b.bin")
    checks.append(("v18 存读后 245 个动态关系与高 id 边都在",
                   "动态关系 245 / 245" in out2 and pred_name(244) in out2))
    checks.append(("旧档输入可读、新档版本 18",
                   model_version(os.path.join(W, "model.bin")) <= 17 and
                   model_version(os.path.join(W, "rw18b.bin")) == 18))

    with open(os.path.join(W, "policy.txt"), "w", encoding="utf-8") as f:
        f.write("dynrel_soft_limit=8\n")
    out3 = run("::ingest c20.tsv\n::reldyn 3\n::quit\n")
    m3 = re.search(r"动态关系 (\d+) / 245", out3)
    checks.append(("消融：软上限 8 ⇒ 只登记 8 个",
                   bool(m3) and int(m3.group(1)) == 8 and "当前上限 8" in out3))
    shutil.copy(os.path.join(ROOT, "policy.txt"), os.path.join(W, "policy.txt"))

    out4 = run("::ingest c300.tsv\n::reldyn 3\n::quit\n")
    checks.append(("读数确定（两次一致）",
                   re.search(r"动态关系 (\d+) / 245", out4).group(1) == "245"))

    ok = sum(1 for _, g in checks if g)
    for name, good in checks:
        print("  [%s] %s" % ("OK" if good else "FAIL", name))
    print("=> 动态关系容量首跑：%d/%d" % (ok, len(checks)))
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
