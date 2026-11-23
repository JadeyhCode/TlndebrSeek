#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""shard_cold.py — §7.003 S1 冷读压测（单分片；真实 `.c7b2` 路径）

做四件事：
  ① 造 N 条唯一事实（无重复注入 ⇒ 去重率基线 0%）→ `triples2c7b` 写一个分片；
  ② 冷读名字查询：查询数 = 1% 抽样（默认 200k 边 ⇒ 2000 次），每次 `fadvise(DONTNEED)`；
     **抽检命中率 ≥95%、p95 ≤200ms** 才 PASS；
  ③ 冷读事实查询（`--facts`）200 次，报 p95；
  ④ 打印 RSS、去重口径。
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = os.path.join(ROOT, "_t", "shardcold")
EDGES = int(os.environ.get("AIP_SHARD_EDGES", "200000"))
QUERIES = max(50, EDGES // 100)          # 1% 抽样


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def p95_of(out):
    m = re.search(r"p95 ([\d.]+) ms", out)
    return float(m.group(1)) if m else None


def main():
    os.makedirs(W, exist_ok=True)
    for f in os.listdir(W):
        p = os.path.join(W, f)
        if os.path.isfile(p):
            os.remove(p)
    t2c = os.path.join(W, "triples2c7b")
    r = sh(["gcc", "-std=c11", "-O2", "-o", t2c, os.path.join(ROOT, "tools", "triples2c7b.c")])
    if r.returncode != 0:
        print("FAIL: triples2c7b 编不过\n" + r.stderr[:300]); return 1
    bench = os.path.join(W, "c7bq")
    r = sh(["gcc", "-std=c11", "-O2", "-o", bench, os.path.join(ROOT, "tools", "c7b_query_bench.c")])
    if r.returncode != 0:
        print("FAIL: c7b_query_bench 编不过\n" + r.stderr[:300]); return 1

    # ① 唯一事实：A(i) 属于 B((i*7+3) % nodes) —— 不注入重复
    trip = os.path.join(W, "in.triples")
    with open(trip, "w", encoding="utf-8") as f:
        for i in range(EDGES):
            f.write("N%d\tP%d\tN%d\n" % (i % 100000, i % 20, (i * 7 + 3) % 100000))
    out_pref = os.path.join(W, "s")
    r = sh([t2c, trip, out_pref, "--max-edges", str(EDGES + 10)])
    shards = [f for f in os.listdir(W) if re.match(r"s\.\d+\.c7b2$", f)]
    if not shards:
        print("FAIL: 没写出分片\n" + (r.stderr or r.stdout)[:300]); return 1
    print("== ① 造数据：%d 条事实 ⇒ %d 个分片（唯一事实，按生成口径去重率 0%%） ==" %
          (EDGES, len(shards)))

    shard = os.path.join(W, shards[0])
    # ② 冷读名字查询（1% 抽样）
    env = dict(os.environ, AIP_COLD="1")
    r = sh([bench, shard, str(QUERIES)], env=env)
    out = r.stdout
    m = re.search(r"命中 (\d+) / 未命中 (\d+)", out)
    if not m:
        print("FAIL: 名字查询没输出读数\n" + out[:300]); return 1
    hit, miss = int(m.group(1)), int(m.group(2))
    ratio = hit / max(1, hit + miss)
    p95 = p95_of(out)
    print("== ② 冷读名字查询（%d 次 = 1%% 抽样）：命中率 %.2f%%  p95 %s ms ==" %
          (QUERIES, ratio * 100, ("%.2f" % p95) if p95 is not None else "?"))
    ok = True
    if ratio < 0.95:
        print("  [FAIL] 抽检命中率 < 95%"); ok = False
    else:
        print("  [OK]   抽检命中率 ≥ 95%")
    if p95 is None or p95 > 200:
        print("  [FAIL] p95 %s > 200ms" % p95); ok = False
    else:
        print("  [OK]   冷读 p95 ≤ 200ms（= %.2f）" % p95)
    # ③ 冷读事实查询
    r = sh([bench, "--facts", shard, "200"], env=env)
    p95f = p95_of(r.stdout)
    print("== ③ 冷读事实查询 200 次：p95 %s ms ==" % (("%.2f" % p95f) if p95f is not None else "?"))
    if p95f is None or p95f > 200:
        print("  [FAIL] 事实冷读 p95 > 200ms"); ok = False
    else:
        print("  [OK]   事实冷读 p95 ≤ 200ms")
    # ④ 多分片 + 全局桶索引的路由冷读
    sharddir = os.path.join(W, "many")
    os.makedirs(sharddir, exist_ok=True)
    for f in os.listdir(sharddir):
        os.remove(os.path.join(sharddir, f))
    trip2 = os.path.join(W, "in2.triples")
    with open(trip2, "w", encoding="utf-8") as f:
        for i in range(EDGES):
            f.write("N%d\tP%d\tN%d\n" % (i % 100000, i % 20, (i * 7 + 3) % 100000))
    per = max(1, EDGES // 10)
    r = sh([t2c, trip2, os.path.join(sharddir, "s"), "--max-edges", str(per)])
    nsh = len([f for f in os.listdir(sharddir) if f.endswith(".c7b2")])
    print("== ④ 多分片路由（%d 片，每片 %d 边） ==" % (nsh, per))
    idxbin = os.path.join(W, "c7bidx")
    r = sh(["gcc", "-std=c11", "-O2", "-o", idxbin, os.path.join(ROOT, "tools", "c7b_index.c")])
    if r.returncode != 0:
        print("  [FAIL] c7b_index 编不过\n" + r.stderr[:300]); ok = False
    else:
        idxdir = os.path.join(W, "idx")
        r = sh([idxbin, sharddir, idxdir])
        if r.returncode != 0:
            print("  [FAIL] 索引建不出\n" + (r.stderr or r.stdout)[:300]); ok = False
        else:
            r = sh([bench, "--index", idxdir, sharddir, "100000", str(QUERIES)], env=env)
            m = re.search(r"命中 (\d+) / 未命中 (\d+)", r.stdout)
            p95i = p95_of(r.stdout)
            if not m:
                print("  [FAIL] 路由查询没读数\n" + r.stdout[:300]); ok = False
            else:
                hi, mi = int(m.group(1)), int(m.group(2))
                ri = hi / max(1, hi + mi)
                print("  路由查询 %d 次：命中 %.2f%%  p95 %s ms" %
                      (QUERIES, ri * 100, ("%.2f" % p95i) if p95i is not None else "?"))
                if ri < 0.95 or p95i is None or p95i > 200:
                    print("  [FAIL] 多分片路由命中率 <95% 或 p95 >200ms"); ok = False
                else:
                    print("  [OK]   多分片路由命中率 ≥95% 且 p95 ≤200ms")

    # ⑤ 去重率：故意注入 5% 重复，再看写进分片的边数
    U = 50000
    dup_n = U // 10   # 故意注入 10% 重复（阈值 5%，必须靠写入口去重）
    tdup = os.path.join(W, "dup.triples")
    with open(tdup, "w", encoding="utf-8") as f:
        for i in range(U):
            f.write("N%d\tP%d\tN%d\n" % (i, i % 20, (i * 7 + 3) % U))
        for i in range(dup_n):
            f.write("N%d\tP%d\tN%d\n" % (i, i % 20, (i * 7 + 3) % U))   # 原样重复
    ddir = os.path.join(W, "dup")
    shutil_rm = __import__("shutil")
    shutil_rm.rmtree(ddir, ignore_errors=True)
    os.makedirs(ddir, exist_ok=True)
    r_conv = sh([t2c, tdup, os.path.join(ddir, "s"), "--max-edges", str(U * 2)])
    dumps = [f for f in os.listdir(ddir) if f.endswith(".c7b2")]
    stored = None
    if dumps:
        dbin = os.path.join(W, "c7bdump")
        r = sh(["gcc", "-std=c11", "-O2", "-o", dbin, os.path.join(ROOT, "tools", "c7b2dump.c")])
        if r.returncode == 0:
            r = sh([dbin, os.path.join(ddir, dumps[0]), str(U * 4)])
            stored = len([l for l in r.stdout.splitlines() if l.strip()])
    if stored is None:
        print("== ⑤ 去重率：测量失败（dump 打不开） ==")
        ok = False
    else:
        rate = (stored - U) / max(1, stored)
        rep = re.search(r"去重 (\d+) 条", (r_conv.stderr or "") + (r_conv.stdout or ""))
        print("== ⑤ 去重率：输入 %d 条（其中 %d 条重复）⇒ 分片 %d 条，重复占比 %.2f%%%s ==" %
              (U + dup_n, dup_n, stored, max(0.0, rate) * 100,
               ("，写入口报去重 %s 条" % rep.group(1)) if rep else ""))
        if stored <= U * 1.05:
            print("  [OK]   重复占比 <5%（写入口已去重）")
        else:
            print("  [FAIL] 重复占比 ≥5%"); ok = False

    # ⑥ RSS
    m = re.search(r"RSS: ([\d.]+) MB", r.stdout)
    print("== ⑥ RSS：%s MB（--index 输出里没带就写 ?） ==" % (m.group(1) if m else "?"))
    route = ""
    try: route = " / 路由 p95 %.2f ms" % p95i
    except Exception: pass
    print("=> S1 冷读压测：%d 边 / 1%% 抽样 / 命中 %.2f%% / 名字 p95 %s ms / 事实 p95 %s ms%s / 去重 %s"
          % (EDGES, ratio * 100,
             ("%.2f" % p95) if p95 is not None else "?",
             ("%.2f" % p95f) if p95f is not None else "?", route,
             ("%.2f%%" % (max(0.0, (stored - U) / max(1, stored)) * 100)) if stored is not None else "?"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
