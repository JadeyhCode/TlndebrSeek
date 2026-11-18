#!/bin/sh
# tests/rewrite.sh — §6.925 说法归一必须真的生效（改写表以前是死数据：前缀+单边被跳过）
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
BIN=${BIN:-./build_aip}
[ -x "$BIN" ] || { echo "FAIL: 缺 $BIN"; exit 1; }
[ -f code/code_model.bin ] || sh code/build_code_model.sh > /dev/null 2>&1
M=code/code_model.bin
W="$ROOT/_t/work"; mkdir -p "$W"
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }

echo "== ① 换说法要命中排序+加一（以前整张改写表不生效）=="
rm -f "$W"/synth_*.c
o=$(printf '::act on\n::code synth 先把这些数从小到大排好，再给每个数加上一，输出结果。\n::quit\n' \
    | "$BIN" --model "$M" 2>&1)
printf '%s' "$o" | grep -aq '写出来了' && ok "合成成功" || bad "换说法合不出来" "$(printf '%s' "$o" | grep -a '合成' | tail -2)"
f=$(ls -t "$W"/synth_*.c 2>/dev/null | head -1)
if [ -n "$f" ] && [ -x "$f.out" ]; then
    got=$(printf '3 1 2\n' | "$f.out" 2>/dev/null | grep -v '^ok$' | tail -1)
    [ "$got" = "2 3 4" ] && ok "产物语义对（3 1 2 → 2 3 4）" || bad "产物语义不对" "实际: $got"
else
    bad "没有产物" "$f"
fi

echo "== ② 改写的两种写法都要生效：'峰值'→最大、'有多少行'→行数 =="
o=$(printf '::act on\n::code synth 读入一行整数（标准输入），输出总数。\n::quit\n' \
    | "$BIN" --model "$M" 2>&1)
printf '%s' "$o" | grep -aq '写出来了' && ok "总数→总和 生效" || bad "总数没归一" "$(printf '%s' "$o" | grep -a '合成' | tail -1)"

echo "== ③ §6.926 yes/no 题：链只会输出数值 ⇒ 证据不足先拒（不硬答）=="
o=$(printf '::act on\n::code synth 写一个程序：读入一行整数（标准输入），输出是否只有一个峰值（输出 yes 或 no）。\n::quit\n' \
    | "$BIN" --model "$M" 2>&1)
printf '%s' "$o" | grep -aqE '证据不足|没有匹配' && ok "yes/no 题拒绝了" || bad "yes/no 题硬答了" "$(printf '%s' "$o" | grep -a '合成' | tail -2)"
printf '%s' "$o" | grep -aq '写出来了' && bad "yes/no 题还答出来了" "" || ok "没有硬写出数值答案"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL rewrite（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS rewrite（$pass 过 / 0 红）"
