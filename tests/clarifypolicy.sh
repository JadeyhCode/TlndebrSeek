#!/bin/sh
# tests/clarifypolicy.sh — §7.006 澄清窄形状由 policy.txt 决定（改阈值/尾词/删文件都可消融）
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -x build_aip ] || { echo "FAIL: 缺 build_aip"; exit 1; }
W="$ROOT/_t/clarifyp"; rm -rf "$W"; mkdir -p "$W"
cp build_aip model.bin patterns.txt frames.txt relations.txt "$W/" 2>/dev/null
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }

echo "== ① 默认：4 词问句会反问 =="
o=$(run '猫 对 动物 吗')
printf '%s' "$o" | grep -qa '什么 关系' && ok "默认反问" || bad "默认没反问" "$(printf '%s' "$o" | grep -a 'AI >' | head -2)"

echo "== ② clarify_max_tokens=3：4 词不再反问（回退到拒答） =="
printf 'clarify_max_tokens=3\n' > "$W/policy.txt"
o=$(run '猫 对 动物 吗')
printf '%s' "$o" | grep -qa '什么 关系' && bad "阈值 3 还在反问" "$(printf '%s' "$o" | grep -a 'AI >' | head -2)" || ok "阈值 3 时不再反问"
printf '%s' "$o" | grep -qa '不 太 懂\|不 知 道\|不 确定' && ok "回退到诚实拒答/不确定" || bad "既没反问也没拒答" "$(printf '%s' "$o" | grep -a 'AI >' | head -2)"

echo "== ③ clarify_tail_words=呢：吗 问题不反问，呢 问题反问 =="
printf 'clarify_tail_words=呢\n' > "$W/policy.txt"
o=$(run '猫 对 动物 吗')
printf '%s' "$o" | grep -qa '什么 关系' && bad "只留呢 还反问吗 句" "$(printf '%s' "$o" | grep -a 'AI >' | head -2)" || ok "吗 句不再反问"
o=$(run '猫 对 动物 呢')
printf '%s' "$o" | grep -qa '什么 关系' && ok "呢 句仍反问" || bad "呢 句没反问" "$(printf '%s' "$o" | grep -a 'AI >' | head -2)"

echo "== ④ 删 policy.txt：回默认（吗/呢 都反问） =="
rm -f "$W/policy.txt"
o=$(run '猫 对 动物 吗')
printf '%s' "$o" | grep -qa '什么 关系' && ok "删文件回默认" || bad "没回默认" "$(printf '%s' "$o" | grep -a 'AI >' | head -2)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL clarifypolicy（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS clarifypolicy（$pass 过 / 0 红）"
