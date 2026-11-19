#!/bin/sh
# tests/double.sh — §6.959 双结果闸门：要两个结果的说法，单值链不许硬答；有任务的别误伤
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -f code/code_model.bin ] || sh code/build_code_model.sh > /dev/null 2>&1
W="$ROOT/_t/double_case"; rm -rf "$W"; mkdir -p "$W/_t/work"
cp build_aip "$W/build_aip"; cp code/code_model.bin "$W/model.bin"
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }

echo "== ① 列表输入要“和与积”：拒绝，不硬打一个数 =="
o=$(run '::act on\n::code synth 输入一行整数，输出它们的和与积')
printf '%s' "$o" | grep -qa '两个结果' && ok "和与积（一行）：拒绝" || bad "和与积（一行）没拒绝" "$(printf '%s' "$o" | grep -a 合成 | tail -1)"

echo "== ② 两个整数的“和与积”：有任务，必须照做（别误伤） =="
o=$(run '::act on\n::code synth 写一个程序：读入两个整数（命令行参数），输出它们的和与积。')
printf '%s' "$o" | grep -qa 'synth_和与积.c' && ok "和与积（命令行两整数）：照做" || bad "误伤任务" "$(printf '%s' "$o" | grep -a 合成 | tail -1)"

echo "== ③ 最大值与最小值：拒绝 =="
o=$(run '::act on\n::code synth 输入一行整数，输出最大值与最小值')
printf '%s' "$o" | grep -qa '两个结果' && ok "最大值与最小值：拒绝" || bad "没拒绝" "$(printf '%s' "$o" | grep -a 合成 | tail -1)"

echo "== ④ 商与余：拒绝 =="
o=$(run '::act on\n::code synth 输入两个整数，输出商与余数')
printf '%s' "$o" | grep -qa '两个结果' && ok "商与余：拒绝" || bad "没拒绝" "$(printf '%s' "$o" | grep -a 合成 | tail -1)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL double（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS double（$pass 过 / 0 红）"
