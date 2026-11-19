#!/bin/sh
# tests/harvest.sh — §6.957 扩图 S3：事实去重率 + 抽检有效率（续行要拼成逻辑记录）
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
W="$ROOT/_t/harvest_case"; rm -rf "$W"; mkdir -p "$W"
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }

printf '片段:a\t代码\tfoo()\\\n{ bar(); }\n片段:b\t声明\tx\n片段:b\t声明\tx\n坏行只有两列\n片段:c\t声明\ty\n' > "$W/f.triples"
o=$(python3 tools/harvest_eval.py "$W/f.triples" 2>&1)
printf '%s' "$o" | grep -qa '总条数         5' && ok "续行拼成 5 条逻辑记录" || bad "条数不对" "$(printf '%s' "$o" | head -2)"
printf '%s' "$o" | grep -qa '精确重复率     20.00%' && ok "重复率 20%（1/5）" || bad "重复率不对" "$(printf '%s' "$o" | grep 重复)"
printf '%s' "$o" | grep -qa '不合格 0' && ok "抽检有不合格计数" || bad "抽检字段缺" "$(printf '%s' "$o" | tail -1)"
printf '%s' "$o" | grep -qa '字段数分布' && ok "字段数分布有读数" || bad "缺字段分布" "$(printf '%s' "$o" | tail -2)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL harvest（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS harvest（$pass 过 / 0 红）"
