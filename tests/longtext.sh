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

echo "== ④ 语法归一：量词短语 / 「的 一种」问法 =="
o=$(run '三只 猫 属于 动物 吗')
printf '%s' "$o" | grep -qa '猫 -\[属于\]-> 动物' && ok "量词短语剥掉后照答" || bad "量词没归一等" "$(printf '%s' "$o" | grep -a 'AI >' | head -1)"
o=$(run '猫 是 动物 的 一种 吗')
printf '%s' "$o" | grep -qa '猫 -\[属于\]-> 动物' && ok "定义问法归一到属于" || bad "定义问法没归一" "$(printf '%s' "$o" | grep -a 'AI >' | head -1)"

echo "== ⑤ 类比门槛：事实问句不许用 60% 相似度下结论 =="
o=$(run '猫 有 六 条 腿 吗')
printf '%s' "$o" | grep -qaE '大概|同类里|像）' && bad "6 条腿仍靠类比答" "$(printf '%s' "$o" | grep -a 'AI >' | head -1)" || ok "不再靠类比硬答"

echo "== ⑥ 无空格中文：亲属/量词/定义/指令 =="
o=$(run '小明是我的表弟')
printf '%s' "$o" | grep -qa '表弟' && ok "无空格亲属句学得进" || bad "无空格亲属句没学" "$(printf '%s' "$o" | grep -a 'AI >' | head -1)"
o=$(run '三只猫属于动物吗')
printf '%s' "$o" | grep -qa '猫 -\[属于\]-> 动物' && ok "无空格量词句答得出" || bad "无空格量词句没答" "$(printf '%s' "$o" | grep -a 'AI >' | head -1)"
o=$(run '猫是动物的一种吗')
printf '%s' "$o" | grep -qa '猫 -\[属于\]-> 动物' && ok "无空格定义问法答得出" || bad "无空格定义问法没答" "$(printf '%s' "$o" | grep -a 'AI >' | head -1)"
o=$(run '我教你貘属于奇蹄目\n貘属于什么')
printf '%s' "$o" | grep -qa '奇蹄目' && ok "无空格教学+查询" || bad "无空格教学没学" "$(printf '%s' "$o" | grep -a 'AI >' | tail -1)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL longtext（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS longtext（$pass 过 / 0 红）"
