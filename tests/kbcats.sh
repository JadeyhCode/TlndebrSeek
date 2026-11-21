#!/bin/sh
# tests/kbcats.sh — §6.974 基础分类/处所：传递、继承、处所、未知拒绝
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -x build_aip ] || { echo "FAIL: 缺 build_aip"; exit 1; }
W="$ROOT/_t/kbcats"; rm -rf "$W"; mkdir -p "$W"
cp build_aip model.bin patterns.txt frames.txt relations.txt "$W/" 2>/dev/null
mkdir -p "$W/code/knowledge"; cp code/knowledge/基础分类.triples "$W/code/knowledge/"
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
run() { ( cd "$W" && printf '::ingest code/knowledge/基础分类.triples\n%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }

echo "== ① 传递：狗 → 犬科 → 食肉目 → 哺乳动物 =="
o=$(run '狗 属于 哺乳动物 吗')
printf '%s' "$o" | grep -qa '传递' && ok "传递链答对" || bad "传递没走" "$(printf '%s' "$o" | grep -a 'AI >' | tail -1)"

echo "== ② 继承：鲸鱼 属于 哺乳动物 ⇒ 有 肺 =="
o=$(run '鲸鱼 有 肺 吗')
printf '%s' "$o" | grep -qa '有' && ok "属性继承答对" || bad "继承没走" "$(printf '%s' "$o" | grep -a 'AI >' | tail -1)"

echo "== ③ 处所：中国 在 亚洲 =="
o=$(run '中国 在 亚洲 吗')
printf '%s' "$o" | grep -qa '对 ， 中国' && ok "处所答对" || bad "处所没答" "$(printf '%s' "$o" | grep -a 'AI >' | tail -1)"

echo "== ④ 未知词：老实拒绝，不编 =="
o=$(run '犰狳 属于 什么')
printf '%s' "$o" | grep -qa '不 认识' && ok "未知词拒绝" || bad "未知词乱答" "$(printf '%s' "$o" | grep -a 'AI >' | tail -1)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL kbcats（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS kbcats（$pass 过 / 0 红）"
