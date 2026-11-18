#!/bin/sh
# tests/shard.sh — §6.930 扩图 S1 地基：`.c7b2` 分片真的能写、体积假设要有实测
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
W="$ROOT/_t/shard"; rm -rf "$W"; mkdir -p "$W"
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }

echo "== ① 编出分片写入器 =="
gcc -std=c11 -O2 -o "$W/triples2c7b" tools/triples2c7b.c > "$W/cc.log" 2>&1 \
    && ok "triples2c7b 编译通过" || { bad "编译失败" "$(head -3 "$W/cc.log")"; echo "FAIL shard"; exit 1; }

echo "== ② 小样本转分片：条数守恒、分片文件存在 =="
if [ -s code/knowledge/capi.triples ]; then
    head -2000 code/knowledge/capi.triples > "$W/in.triples"
else
    i=0; while [ $i -lt 2000 ]; do printf '节点%d\t有\t属性%d\n' "$i" "$((i % 37))" >> "$W/in.triples"; i=$((i+1)); done
fi
n_in=$(wc -l < "$W/in.triples")
o=$("$W/triples2c7b" "$W/in.triples" "$W/s" --max-edges 800 2>&1)
n_shard=$(ls "$W"/s.*.c7b2 2>/dev/null | wc -l)
[ "$n_shard" -ge 2 ] && ok "分片数 $n_shard（800 边/片）" || bad "分片数不对" "$o"
printf '%s' "$o" | grep -qa "文本事实 $n_in 条" && ok "条数守恒（$n_in 条）" || bad "条数不守恒" "$(printf '%s' "$o" | tail -2)"

echo "== ③ 体积实测：打印 bytes/edge（只报告，不当硬门槛）=="
bytes=$(du -sb "$W"/s.*.c7b2 2>/dev/null | awk '{s+=$1} END {print s+0}')
bpe=$(python3 -c "print(round($bytes/$n_in,1))" 2>/dev/null || echo "?")
echo "  [NOTE] 本样本：$bytes 字节 / $n_in 条 = **$bpe 字节/边**"
[ -n "$bpe" ] && [ "$bpe" != "?" ] && ok "体积可测（$bpe B/边）" || bad "体积测不出来" "$bytes"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL shard（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS shard（$pass 过 / 0 红）"
