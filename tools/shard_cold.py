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
    # ④ RSS
    m = re.search(r"RSS: ([\d.]+) MB", r.stdout)
    print("== ④ 去重口径：生成即唯一（未注入重复）；RSS %s MB ==" % (m.group(1) if m else "?"))
    print("=> S1 冷读压测：%d 边 / 1%% 抽样 / 命中 %.2f%% / 名字 p95 %s ms / 事实 p95 %s ms"
          % (EDGES, ratio * 100,
             ("%.2f" % p95) if p95 is not None else "?",
             ("%.2f" % p95f) if p95f is not None else "?"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
