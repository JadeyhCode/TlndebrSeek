#!/bin/sh
# tests/longtext.sh — §6.973 长文/多句理解：属性两种问法、X 有什么 双义项、列举
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -x build_aip ] || { echo "FAIL: 缺 build_aip"; exit 1; }
W="$ROOT/_t/longtext"; rm -rf "$W"; mkdir -p "$W"
cp build_aip model.bin patterns.txt frames.txt relations.txt "$W/" 2>/dev/null
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }

echo "== ① 教属性后两种问法都答 =="
o=$(run '我教你，南极 很 冷\n南极 很 冷 吗\n南极 冷 吗')
n=$(printf '%s' "$o" | grep -ac '对 ， 南极 很 冷') || true
[ "${n:-0}" -ge 2 ] && ok "两种问法都对（$n）" || bad "属性问法不全对" "$(printf '%s' "$o" | grep -a 'AI >' | tail -2)"

echo "== ② 「动物 有 什么」两种义项都答（成员 / 属性） =="
o=$(run '动物 有 什么')
printf '%s' "$o" | grep -qa '成员' && printf '%s' "$o" | grep -qa '属性' && ok "双义项都答" || bad "只答了一种" "$(printf '%s' "$o" | grep -a 'AI >' | head -1)"

echo "== ③ 列举仍带“等（只列前几个）” =="
o=$(run '谁 属于 动物')
printf '%s' "$o" | grep -qa '猫' && ok "列举有猫" || bad "没有成员" "$(printf '%s' "$o" | grep -a 'AI >' | head -1)"
printf '%s' "$o" | grep -qa '只列前几个' && ok "截断有提示" || bad "没有截断提示" "$(printf '%s' "$o" | grep -a 'AI >' | head -1)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL longtext（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS longtext（$pass 过 / 0 红）"
