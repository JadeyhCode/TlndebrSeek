#!/bin/sh
# tests/familysplit.sh — §6.960 泛化/迁移按“族”切分（arr/matrix/str/file/two）
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -x build_aip ] || { echo "FAIL: 缺 build_aip"; exit 1; }
[ -f code/code_model.bin ] || sh code/build_code_model.sh > /dev/null 2>&1
W="$ROOT/_t/fam_case"; rm -rf "$W"; mkdir -p "$W"
cp build_aip "$W/build_aip"; cp code/code_model.bin "$W/model.bin"
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
o=$(cd "$W" && timeout 600 python3 "$ROOT/tools/generalize_eval.py" 2>&1)
printf '%s' "$o" | grep -qa '族 arr' && ok "有 arr 族读数" || bad "没有族读数" "$(printf '%s' "$o" | tail -2)"
n=$(printf '%s' "$o" | grep -ac '^   族 ') || true
[ "$n" -ge 5 ] && ok "A/B 两组共 $n 个族行" || bad "族行太少" "$n"
printf '%s' "$o" | grep -qa '首跑汇总' && ok "有首跑汇总" || bad "缺汇总" "$(printf '%s' "$o" | tail -1)"
echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL familysplit（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS familysplit（$pass 过 / 0 红）"
