#!/bin/sh
# tests/reseg.sh — §6.968 切词修正：解析失败时自动合并/拆开，成功才采用
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -x build_aip ] || { echo "FAIL: 缺 build_aip"; exit 1; }
W="$ROOT/_t/reseg"; rm -rf "$W"; mkdir -p "$W"
cp build_aip model.bin "$W/"
printf '猫吃\t测试\t1\n' > "$W/x.triples"
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }

echo "== ① 合并且：没空格的“麒麟属于神兽” → 学成 麒麟 属于 神兽 =="
o=$(run '麒麟属于神兽\n::rel 麒麟')
printf '%s' "$o" | grep -qa '记下 了' && ok "合并且后学下来了" || bad "没学下来" "$(printf '%s' "$o" | grep -a 'AI >' | head -2)"
printf '%s' "$o" | grep -qa '属于' && ok "::rel 麒麟 里有 属于" || bad "关系没进图" "$(printf '%s' "$o" | grep -a '麒麟 --' | head -2)"

echo "== ② 拆开且：图里错误粘着“猫吃” → 拆成 猫/吃/鱼 =="
o=$(run '::ingest x.triples\n猫吃鱼\n::rel 猫\n::seg')
printf '%s' "$o" | grep -qa '猫 --\[吃\]--> 鱼' && ok "拆开后学成 猫 吃 鱼" || bad "拆开没学成" "$(printf '%s' "$o" | grep -a '猫' | head -3)"
printf '%s' "$o" | grep -qa '切词修正' && ok "::seg 有合并/拆开计数" || bad "计数行缺" "$(printf '%s' "$o" | grep -a '切词修正')"

echo "== ③ 正常句子不受影响 =="
o=$(run '猫 属于 动物')
printf '%s' "$o" | grep -qaE '记下 了|我 知道' && ok "正常句子照常学" || bad "正常句子受影响" "$(printf '%s' "$o" | grep -a 'AI >' | head -2)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL reseg（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS reseg（$pass 过 / 0 红）"
