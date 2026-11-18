#!/bin/sh
# tests/shardquery.sh — §6.931 分片查询延迟：真路径（名字→节点→事实）能跑，p95 有读数
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
W="$ROOT/_t/shardq"; rm -rf "$W"; mkdir -p "$W"
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }

echo "== ① 编工具 + 造 10 万边小语料 + 转分片 =="
gcc -std=c11 -O2 -o "$W/triples2c7b" tools/triples2c7b.c > "$W/cc1.log" 2>&1 \
    && ok "triples2c7b 编译通过" || { bad "triples2c7b 编不过" "$(head -2 "$W/cc1.log")"; echo "FAIL shardquery"; exit 1; }
gcc -std=c11 -O2 -o "$W/c7bq" tools/c7b_query_bench.c > "$W/cc2.log" 2>&1 \
    && ok "c7b_query_bench 编译通过" || { bad "bench 编不过" "$(grep -m1 error "$W/cc2.log")"; echo "FAIL shardquery"; exit 1; }
python3 - "$W/in.triples" <<'PY'
import random, sys
rng = random.Random(11)
with open(sys.argv[1], "w") as f:
    for i in range(100000):
        a = i % 50000
        b = (i * 7 + 3) % 50000
        f.write("N%d\tP%d\tN%d\n" % (a, i % 20, b))
PY
[ -s "$W/in.triples" ] && ok "造了 10 万边" || bad "语料没造出来" ""
"$W/triples2c7b" "$W/in.triples" "$W/s" --max-edges 200000 > "$W/conv.log" 2>&1
ls "$W"/s.*.c7b2 >/dev/null 2>&1 && ok "分片写出来了" || bad "没分片" "$(tail -2 "$W/conv.log")"

echo "== ② 查询压测：命中率 100%，打印 p50/p95 =="
o=$("$W/c7bq" "$W"/s.000.c7b2 50 2>&1)
printf '%s' "$o" | grep -q "命中 50 / 未命中 0" && ok "50 次查询全命中" || bad "命中率不对" "$(printf '%s' "$o" | tail -2)"
p95=$(printf '%s' "$o" | sed -n 's/.*p95 \([0-9.]*\) ms.*/\1/p')
[ -n "$p95" ] && ok "p95 = $p95 ms（10 万边/5 万节点）" || bad "没打出 p95" "$(printf '%s' "$o" | tail -2)"
[ -n "$p95" ] && python3 -c "import sys; sys.exit(0 if float('$p95') < 200 else 1)" \
    && ok "小分片 p95 < 200 ms" || bad "小分片 p95 超 200ms" "$p95"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL shardquery（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS shardquery（$pass 过 / 0 红）"
