#!/bin/sh
# tests/attention.sh — §7.010 元认知管理的注意力：可观测/可分配/策略可消融
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -x build_aip ] || { echo "FAIL: 缺 build_aip"; exit 1; }
W="$ROOT/_t/attention"; rm -rf "$W"; mkdir -p "$W"
cp build_aip model.bin patterns.txt frames.txt relations.txt "$W/" 2>/dev/null
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }

echo "== ① 默认：一句话后能看到注意力（预算/份额/来源） =="
o=$(run '猫 属于 动物 吗\n::att')
printf '%s' "$o" | grep -qa '预算 1.00' && ok "预算 1.00" || bad "预算不对" "$(printf '%s' "$o" | grep -a '注意力' | head -2)"
n=$(printf '%s' "$o" | grep -c '份额 ' || true)
[ "$n" -ge 1 ] && ok "有 $n 项注意力" || bad "没有注意力项" "$(printf '%s' "$o" | grep -a '注意力' | head -2)"
printf '%s' "$o" | grep -qa '来源 ' && ok "每项有来源" || bad "缺来源" "$(printf '%s' "$o" | grep -a '份额' | head -2)"

echo "== ② att_topk=1：只给 1 项 =="
printf 'att_topk=1\n' > "$W/policy.txt"
o=$(run '猫 属于 动物 吗\n::att')
n=$(printf '%s' "$o" | grep -c '份额 ' || true)
[ "$n" = "1" ] && ok "topk=1 生效" || bad "topk 没生效（$n 项）" "$(printf '%s' "$o" | grep -a '份额' | head -3)"

echo "== ③ att_budget=0.2：份额总和 ≤0.2 =="
printf 'att_budget=0.2\n' > "$W/policy.txt"
o=$(run '猫 属于 动物 吗\n::att')
printf '%s' "$o" | grep -qa '预算 0.20' && ok "预算 0.20" || bad "预算没变" "$(printf '%s' "$o" | grep -a '注意力' | head -2)"
sum=$(printf '%s' "$o" | sed -n 's/.*份额 \([0-9.]*\).*/\1/p' | awk '{s+=$1} END{printf "%.2f", s+0}')
python3 -c "import sys; sys.exit(0 if float('$sum') <= 0.2001 else 1)" && ok "份额总和 $sum ≤0.2" || bad "份额总和超了" "sum=$sum"

echo "== ④ AIP_ATT=0：注意力关掉 =="
rm -f "$W/policy.txt"
o=$( cd "$W" && printf '猫 属于 动物 吗\n::att\n::quit\n' | AIP_ATT=0 ./build_aip --model model.bin 2>&1 )
printf '%s' "$o" | grep -qa '注意力] 关' && ok "关掉后报关" || bad "关掉没报关" "$(printf '%s' "$o" | grep -a '注意力' | tail -2)"

echo "== ⑤ 删 policy.txt：回默认 =="
o=$(run '猫 属于 动物 吗\n::att')
printf '%s' "$o" | grep -qa '预算 1.00' && ok "删文件回默认" || bad "没回默认" "$(printf '%s' "$o" | grep -a '注意力' | head -2)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL attention（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS attention（$pass 过 / 0 红）"
