#!/bin/sh
# tests/leadwords.sh — §6.969 引导语按词序列匹配：空格/逗号不再影响
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -x build_aip ] || { echo "FAIL: 缺 build_aip"; exit 1; }
W="$ROOT/_t/leadw"; rm -rf "$W"; mkdir -p "$W"
cp build_aip model.bin patterns.txt frames.txt relations.txt "$W/" 2>/dev/null
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }

echo "== ① 没空格的「我教你，」也学得下来 =="
o=$(run '我教你，獾 属于 哺乳动物\n獾 属于 什么')
printf '%s' "$o" | grep -qa '记下 了' && ok "无空格：记下" || bad "无空格没学" "$(printf '%s' "$o" | grep -a 'AI >' | head -2)"
printf '%s' "$o" | grep -qa '獾 -\[属于\]-> 哺乳动物' || printf '%s' "$o" | grep -qa '哺乳动物' && ok "无空格：问得出来" || bad "问不出来" "$(printf '%s' "$o" | grep -a 'AI >' | tail -2)"

echo "== ② 有空格/逗号的同一句 =="
o=$(run '我 教 你 ， 水獭 属于 鼬科\n水獭 属于 什么')
printf '%s' "$o" | grep -qa '记下 了' && ok "有空格：记下" || bad "有空格没学" "$(printf '%s' "$o" | grep -a 'AI >' | head -2)"

echo "== ③ 多字引导语「难道」「你以为」 =="
o=$(run '难 道 猫 属 于 动 物 吗')
printf '%s' "$o" | grep -qa '猫 -\[属于\]-> 动物' && ok "难道：剥掉后照答" || bad "难道坏了" "$(printf '%s' "$o" | grep -a 'AI >' | tail -1)"
o=$(run '你 以 为 猫 属 于 什 么')
printf '%s' "$o" | grep -qa '猫' && ok "你以为：当引导语" || bad "你以为坏了" "$(printf '%s' "$o" | grep -a 'AI >' | tail -1)"

echo "== ④ §6.970b 显式教属性句「X 很 Y」 =="
o=$(run '我教你，南极 很 冷\n南极 很 冷 吗\n南极 冷 吗')
printf '%s' "$o" | grep -qa '记下 了' && ok "属性句：记下" || bad "属性句没学" "$(printf '%s' "$o" | grep -a 'AI >' | head -2)"
n=$(printf '%s' "$o" | grep -ac '对 ， 南极 很 冷') || true
[ "${n:-0}" -ge 2 ] && ok "两种问法都答对（$n）" || bad "属性问法不全对" "$(printf '%s' "$o" | grep -a 'AI >' | tail -2)"

echo "== ⑤ 普通陈述「今天 很 热」不被属性教学抢走 =="
o=$(run '今天 很 热')
printf '%s' "$o" | grep -qa '记下 了 ： 今天' && bad "普通聊天被当成教学" "$(printf '%s' "$o" | grep -a 'AI >' | head -1)" || ok "普通陈述仍走聊天"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL leadwords（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS leadwords（$pass 过 / 0 红）"
