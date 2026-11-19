#!/bin/sh
# tests/multivar.sh — §6.943 多变量链：两个量（x 行数 / y 最长行）按依赖排序，不是关键词顺序
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
BIN=${BIN:-./build_aip}
M=code/code_model.bin
[ -x "$BIN" ] || { echo "FAIL: 缺 $BIN"; exit 1; }
[ -f "$M" ] || sh code/build_code_model.sh > /dev/null 2>&1
W="$ROOT/_t/multivar"; rm -rf "$W"; mkdir -p "$W"
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
synth() {
    printf '::act on\n::code synth %s\n::quit\n' "$1" | "$BIN" --model "$M" 2>&1
}
run_one() {  # $1=源码名 $2=输入文件 → 输出第一行
    gcc -std=c11 -O2 -o "$W/p.out" "$1" > "$W/cc.log" 2>&1 || return 1
    "$W/p.out" "$2" 2>/dev/null | head -1
}

echo "== ① 行数 × 最长行：依赖排序把“最长行”提前 =="
o=$(printf '::act on\n::code synth 读入一个文件路径（命令行参数），输出文件的行数乘以最长行的长度\n::quit\n' | AIP_CHAINDBG=1 "$BIN" --model "$M" 2>&1)
printf '%s' "$o" | grep -qa '依赖 .*乘上第二量.*把 运算:最长行长度 提前' && ok "依赖排序生效" || bad "没走依赖排序" "$(printf '%s' "$o" | grep -a '依赖' | head -2)"
src=$(ls -t _t/work/synth_文件行数_乘上第二量.c 2>/dev/null | head -1)
if [ -n "$src" ]; then
    printf 'abcde\nabcdefg\nab\n' > "$W/f1.txt"
    got=$(run_one "$src" "$W/f1.txt")
    [ "$got" = "21" ] && ok "3 行 × 最长 7 = 21" || bad "结果不对" "got=$got"
else bad "没生成源码" ""; fi

echo "== ② 单词数 − 行数：第二个量由“行数到 y”产出 =="
o=$(printf '::act on\n::code synth 读入一个文件路径（命令行参数），输出文件的单词数减去行数\n::quit\n' | AIP_CHAINDBG=1 "$BIN" --model "$M" 2>&1)
printf '%s' "$o" | grep -qa '依赖 .*减去第二量.*把 运算:文件行数到y 提前' && ok "依赖排序生效（减法）" || bad "减法没排序" "$(printf '%s' "$o" | grep -a '依赖' | head -2)"
src=$(ls -t _t/work/synth_文件单词数_减去第二量.c 2>/dev/null | head -1)
if [ -n "$src" ]; then
    printf 'a b\nc\nd e f\n' > "$W/f2.txt"
    got=$(run_one "$src" "$W/f2.txt")
    [ "$got" = "3" ] && ok "6 词 − 3 行 = 3" || bad "结果不对" "got=$got"
else bad "没生成源码（减法）" ""; fi

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL multivar（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS multivar（$pass 过 / 0 红）"
