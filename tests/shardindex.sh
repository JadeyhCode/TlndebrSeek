#!/bin/sh
# tests/shardindex.sh — §6.932 全局“名字→分片”路由：两分片也要一次命中，p95 有读数
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
W="$ROOT/_t/shardidx"; rm -rf "$W"; mkdir -p "$W/s"
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }

echo "== ① 编工具（写入器 / 索引器 / 压测器）=="
gcc -std=c11 -O2 -o "$W/triples2c7b" tools/triples2c7b.c > "$W/cc1.log" 2>&1 && ok "triples2c7b" || { bad "triples2c7b 编不过" "$(head -2 "$W/cc1.log")"; echo "FAIL shardindex"; exit 1; }
gcc -std=c11 -O2 -o "$W/c7b_index" tools/c7b_index.c > "$W/cc2.log" 2>&1 && ok "c7b_index" || { bad "c7b_index 编不过" "$(grep -m1 error "$W/cc2.log")"; echo "FAIL shardindex"; exit 1; }
gcc -std=c11 -O2 -o "$W/c7bq" tools/c7b_query_bench.c > "$W/cc3.log" 2>&1 && ok "c7b_query_bench" || { bad "bench 编不过" "$(grep -m1 error "$W/cc3.log")"; echo "FAIL shardindex"; exit 1; }

echo "== ② 造两个分片（N0–49999 / N50000–99999），各自的 000 文件再按号命名 =="
python3 - "$W" <<'PY'
import os, sys
w = sys.argv[1]
for part in range(2):
    base = part * 50000
    p = os.path.join(w, "in%d.triples" % part)
    with open(p, "w") as f:
        for i in range(50000):
            f.write("N%d\tP%d\tN%d\n" % (base + i, i % 20, base + (i * 7 + 3) % 50000))
PY
for part in 0 1; do
    mkdir -p "$W/t$part"
    "$W/triples2c7b" "$W/in$part.triples" "$W/t$part/s" --max-edges 5000000 > /dev/null 2>&1
    mv "$W/t$part/s.000.c7b2" "$W/s/s.00$part.c7b2"
    rmdir "$W/t$part"
done
n=$(ls "$W"/s/*.c7b2 | wc -l)
[ "$n" = "2" ] && ok "两个分片就位" || bad "分片数不对" "$n"

echo "== ③ 建索引 + 跨分片查询：必须一次命中，不靠扫所有分片 =="
"$W/c7b_index" "$W/s" "$W/idx.bin" > "$W/idx.log" 2>&1
[ -s "$W/idx.bin" ] && ok "索引写出来了" || bad "索引没写出来" "$(tail -2 "$W/idx.log")"
printf '%s' "$(cat "$W/idx.log")" | grep -q '节点 100000 个' && ok "索引覆盖 10 万节点" || bad "索引节点数不对" "$(cat "$W/idx.log")"
o=$("$W/c7bq" --index "$W/idx.bin" "$W/s" 100000 200 2>&1)
printf '%s' "$o" | grep -q '命中 200 / 未命中 0' && ok "200 次跨分片查询全命中" || bad "跨分片路由不对" "$(printf '%s' "$o" | tail -2)"
p95=$(printf '%s' "$o" | sed -n 's/.*p95 \([0-9.]*\) ms.*/\1/p')
[ -n "$p95" ] && ok "p95 = $p95 ms（2 分片/10 万节点）" || bad "没打出 p95" "$(printf '%s' "$o" | tail -2)"
[ -n "$p95" ] && python3 -c "import sys; sys.exit(0 if float('$p95') < 200 else 1)" && ok "p95 < 200 ms" || bad "p95 超 200ms" "$p95"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL shardindex（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS shardindex（$pass 过 / 0 红）"
