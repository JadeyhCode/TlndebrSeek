#!/bin/sh
# tests/study.sh — §7.011 无人值守自学：出题/自答/自检/归因/求助/待证/统计（离线）
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -x build_aip ] || { echo "FAIL: 缺 build_aip"; exit 1; }
W="$ROOT/_t/studycase"; rm -rf "$W"; mkdir -p "$W"
cp build_aip model.bin patterns.txt frames.txt relations.txt policy.txt "$W/" 2>/dev/null
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }

echo "== ① 先攒 3 道答不出的题（进好奇心队列） =="
run '鸟 吃 石头 吗\n鸟 吃 木头 吗\n鸟 吃 玻璃 吗' > /dev/null
n=$(grep -c "pending" "$W/_t/curious.tsv" 2>/dev/null || true)
[ "$n" -ge 3 ] && ok "队列里 pending $n 条" || bad "队列没攒够" "条数=$n"

echo "== ② ::study 做题：自答→自检答不出→归因→求助③问用户→④::sym 建议 =="
o=$(run '::study')
printf '%s' "$o" | grep -qa '出题（来自好奇心队列）' && ok "取题" || bad "没取题" "$(printf '%s' "$o" | grep -a '自学' | head -3)"
printf '%s' "$o" | grep -qa '自检：答不出' && ok "自检答不出" || bad "自检不对" "$(printf '%s' "$o" | grep -a '自检' | head -2)"
printf '%s' "$o" | grep -qa '归因：缺' && ok "有归因" || bad "缺归因" "$(printf '%s' "$o" | grep -a '归因' | head -2)"
printf '%s' "$o" | grep -qa '问用户' && ok "求助③问用户" || bad "没写问用户" "$(printf '%s' "$o" | grep -a '求助' | head -3)"
printf '%s' "$o" | grep -qa '::sym edge add' && ok "给 ::sym 建议（不自动写）" || bad "没给 sym 建议" "$(printf '%s' "$o" | grep -a '自省工具' | head -2)"
[ -s "$W/_t/study/ask_user.tsv" ] && ok "问用户队列有文件" || bad "问用户队列空" ""
[ -s "$W/_t/study/sym_hints.tsv" ] && ok "sym 建议有文件" || bad "sym 建议文件空" ""

echo "== ③ 统计与 list =="
o=$(run '::study stats')
printf '%s' "$o" | grep -qa '出题 1' && ok "统计出题 1" || bad "统计不对" "$(printf '%s' "$o" | grep -a '自学统计' | head -2)"
printf '%s' "$o" | grep -qa '问用户 1' && ok "求助分布记了问用户" || bad "求助分布不对" "$(printf '%s' "$o" | grep -a '自学统计' | head -2)"
o=$(run '::study list')
printf '%s' "$o" | grep -qa 'pending' && printf '%s' "$o" | grep -qa '鸟 吃 木头 吗' && ok "list 看到剩下的题" || bad "list 不对" "$(printf '%s' "$o" | grep -a '自学' | head -3)"

echo "== ④ 消融：study_rounds=1 时 run 5 只做 1 题 =="
printf 'study_rounds=1\n' > "$W/policy.txt"
o=$(run '::study run 5')
printf '%s' "$o" | grep -qa '出题 2' && ok "预算 1 生效（累计 2）" || bad "预算没生效" "$(printf '%s' "$o" | grep -a '自学统计' | head -2)"

echo "== ⑤ 外部通道没开：不产外部待证（不擅自联网） =="
rm -f "$W/policy.txt"
run '::study run 5' > /dev/null
if [ -f "$W/_t/study/proposals.tsv" ] && grep -qa '外部' "$W/_t/study/proposals.tsv"; then
    bad "外部没开却产生了外部待证" "$(head -2 "$W/_t/study/proposals.tsv")"
else
    ok "外部没开时没有外部待证"
fi

echo "== ⑥ 队列空：不硬造题 =="
run '::study run 5' > /dev/null
o=$(run '::study')
printf '%s' "$o" | grep -qa '没有待学的题' && ok "空队列不硬造" || bad "空队列乱造" "$(printf '%s' "$o" | grep -a '自学' | head -3)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL study（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS study（$pass 过 / 0 红）"
