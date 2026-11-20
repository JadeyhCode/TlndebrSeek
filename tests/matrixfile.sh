#!/bin/sh
# tests/matrixfile.sh — §6.961 族级迁移补洞：矩阵行最大 / 文件单词数减行数
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -f code/code_model.bin ] || sh code/build_code_model.sh > /dev/null 2>&1
W="$ROOT/_t/mf_case"; rm -rf "$W"; mkdir -p "$W/_t/work"
cp build_aip "$W/build_aip"; cp code/code_model.bin "$W/model.bin"
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }

echo "== ① 矩阵行最大：算出 3 6 =="
o=$(run '::act on\n::code synth 读入一个矩阵（标准输入），输出每一行中最大的数。')
exe=$(ls -t "$W"/_t/work/synth_矩阵行最大.c.out 2>/dev/null | head -1)
if [ -n "$exe" ]; then
    got=$(printf '2 3\n1 2 3\n4 5 6\n' | "$exe" 2>/dev/null | head -1)
    [ "$got" = "3 6" ] && ok "行最大输出 3 6" || bad "行最大不对" "got=$got"
else bad "没生成行最大候选" "$(printf '%s' "$o" | grep -a 合成 | tail -1)"; fi

echo "== ② 文件单词数减行数：3 词 2 行 = 1 =="
o=$(run '::act on\n::code synth 读入一个文件（命令行参数），输出单词个数减去行数。')
exe=$(ls -t "$W"/_t/work/synth_文件单词数减行数.c.out 2>/dev/null | head -1)
if [ -n "$exe" ]; then
    printf 'a bb\nccc\n' > "$W/t.txt"
    got=$("$exe" "$W/t.txt" 2>/dev/null | head -1)
    [ "$got" = "1" ] && ok "词数减行数 = 1" || bad "词数减行数不对" "got=$got"
else bad "没生成文件候选" "$(printf '%s' "$o" | grep -a 合成 | tail -1)"; fi

echo "== ③ “每一行”不再被矩阵乘法抢走 =="
printf '%s' "$o" >/dev/null
o2=$(run '::act on\n::code synth 读入一个矩阵（标准输入），输出每一行中最大的数。')
printf '%s' "$o2" | grep -qa '矩阵乘法' && bad "又被矩阵乘法抢走" "$(printf '%s' "$o2" | grep -a 合成 | tail -1)" || ok "没被矩阵乘法抢走"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL matrixfile（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS matrixfile（$pass 过 / 0 红）"
