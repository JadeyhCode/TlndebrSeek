#!/bin/sh
# tests/shapewords.sh — §6.939 形状词下沉第一步：图里有数据、代码会去查（后备表仍在）
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
BIN=${BIN:-./build_aip}
[ -x "$BIN" ] || { echo "FAIL: 缺 $BIN"; exit 1; }
[ -f code/code_model.bin ] || sh code/build_code_model.sh > /dev/null 2>&1
M=code/code_model.bin
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }

echo "== ① 数据文件在位，且已灌进代码模型 =="
[ -s code/knowledge/shapewords.triples ] && ok "shapewords.triples 存在" || bad "数据文件缺" ""
o=$(printf '::rel 形状词:第六个数\n::quit\n' | "$BIN" --model "$M" 2>&1)
printf '%s' "$o" | grep -qa '要标量' && ok "模型里有 第六个数→要标量" || bad "模型里没有" "$(printf '%s' "$o" | tail -2)"

echo "== ② 合成时会去图里查（AIP_SHAPEDBG 证据）=="
o=$(printf '::act on\n::code synth 读入一行整数（标准输入），从大到小排序后输出第六个数\n::quit\n' \
    | AIP_SHAPEDBG=1 "$BIN" --model "$M" 2>&1)
printf '%s' "$o" | grep -qa '图命中 形状词:第六个数（要标量）' && ok "命中图里的标量词" || bad "没查图" "$(printf '%s' "$o" | grep -a shapedbg | head -2)"
printf '%s' "$o" | grep -qa '图命中 形状词:排序后输出（要数组）' && ok "命中图里的数组词" || bad "数组词没命中" "$(printf '%s' "$o" | grep -a shapedbg | head -2)"

echo "== ③ 图里没有的词不装命中（后备表仍负责已知词）=="
o=$(printf '::act on\n::code synth 读入一行整数（标准输入），从大到小排序后输出第七个数\n::quit\n' \
    | AIP_SHAPEDBG=1 "$BIN" --model "$M" 2>&1)
printf '%s' "$o" | grep -qa '图命中 形状词:第七个数' && bad "不存在的词也命中了" "" || ok "不存在的词不命中"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL shapewords（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS shapewords（$pass 过 / 0 红）"
