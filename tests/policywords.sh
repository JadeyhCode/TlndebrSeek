#!/bin/sh
# tests/policywords.sh — §7.009 问句/续列词表来自 policy.txt（换词/删文件都可消融）
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -x build_aip ] || { echo "FAIL: 缺 build_aip"; exit 1; }
W="$ROOT/_t/policyw"; rm -rf "$W"; mkdir -p "$W"
cp build_aip model.bin patterns.txt frames.txt relations.txt "$W/" 2>/dev/null
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }

echo "== ① 默认：吗 问句入好奇心队列 =="
o=$(run '鸟 吃 石头 吗\n::curious')
printf '%s' "$o" | grep -qa '鸟 吃 石头 吗' && ok "默认入队" || bad "默认没入队" "$(printf '%s' "$o" | grep -a '好奇' -A2 | head -3)"

echo "== ② curious_question_tail=呢：吗 问句不再算问句（不入队） =="
rm -rf "$W/_t"
printf 'curious_question_tail=呢\n' > "$W/policy.txt"
o=$(run '鸟 吃 石头 吗\n::curious')
printf '%s' "$o" | grep -qa '鸟 吃 石头 吗' && bad "尾词表改了还入队" "$(printf '%s' "$o" | grep -a '鸟 吃' | head -2)" || ok "吗 句不再入队"
o=$(run '鸟 吃 石头 呢\n::curious')
printf '%s' "$o" | grep -qa '鸟 吃 石头 呢' && ok "呢 句仍入队" || bad "呢 句没入队" "$(printf '%s' "$o" | grep -a '好奇' -A2 | head -3)"

echo "== ③ 续列词表可换：先垫 8 个成员保证列表有后续 =="
mk_w2() {
    rm -rf "$W2"; mkdir -p "$W2"
    cp build_aip model.bin patterns.txt frames.txt relations.txt "$W2/" 2>/dev/null
    printf '测试甲\t属于\t动物\n测试乙\t属于\t动物\n测试丙\t属于\t动物\n测试丁\t属于\t动物\n测试戊\t属于\t动物\n测试己\t属于\t动物\n' > "$W2/t.triples"
}
W2="$ROOT/_t/policyw2"
mk_w2
o=$( cd "$W2" && printf '::ingest t.triples\n谁 属于 动物\n还有 哪些\n::quit\n' | ./build_aip --model model.bin 2>&1 )
printf '%s' "$o" | grep -qa '还 有 ：' && ok "默认续列能接列表" || bad "默认续列没接上" "$(printf '%s' "$o" | grep -a 'AI >' | tail -2)"
mk_w2
printf 'more_marker_words=继续\nmore_tail_words=吧\n' > "$W2/policy.txt"
o=$( cd "$W2" && printf '::ingest t.triples\n谁 属于 动物\n还有 哪些\n::quit\n' | ./build_aip --model model.bin 2>&1 )
printf '%s' "$o" | grep -qa '还 有 ：' && bad "换了词表还认旧词" "$(printf '%s' "$o" | grep -a 'AI >' | tail -2)" || ok "旧词让位"
mk_w2
o=$( cd "$W2" && printf '::ingest t.triples\n谁 属于 动物\n还有 哪些\n::quit\n' | ./build_aip --model model.bin 2>&1 )
printf '%s' "$o" | grep -qa '还 有 ：' && ok "删文件回默认" || bad "没回默认" "$(printf '%s' "$o" | grep -a 'AI >' | tail -2)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL policywords（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS policywords（$pass 过 / 0 红）"
