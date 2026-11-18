#!/bin/sh
# tests/whyfor.sh — §6.919 理由层：知道“为什么”，没有理由就直说没有
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
BIN=${BIN:-./build_aip}
[ -x "$BIN" ] || { echo "FAIL: 缺 $BIN"; exit 1; }
# 用出厂 model.bin + 现场灌理由层：不依赖生成物 code_model.bin（沙箱里它不一定在）
mkdir -p _t/work
M=${1:-_t/work/whyfor_model.bin}
if [ "$M" = "_t/work/whyfor_model.bin" ]; then
    cp model.bin "$M" 2>/dev/null || { echo "FAIL: 缺 model.bin"; exit 1; }
fi
run() { printf '::ingest code/knowledge/rationale.triples\n%b\n::quit\n' "$1" | "$BIN" --model "$M" 2>&1; }
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }

echo "== ① 有理由：需求:数组工具集 必须打出 理由/证据/做法 =="
o=$(run '::whyfor 需求:数组工具集')
printf '%s' "$o" | grep -qa '\[理由\]' && ok "打出理由" || bad "没打出理由" "$(printf '%s' "$o" | tail -3)"
printf '%s' "$o" | grep -qa '\[证据\]' && ok "打出证据" || bad "没打出证据" "$(printf '%s' "$o" | tail -3)"
printf '%s' "$o" | grep -qa '\[做法\]' && ok "打出做法" || bad "没打出做法" "$(printf '%s' "$o" | tail -3)"

echo "== ② 目标层：自学闭环要有 意图/理由/证据 =="
o=$(run '::whyfor 目标:自学闭环')
printf '%s' "$o" | grep -qa '\[意图\]' && ok "打出意图" || bad "没打出意图" "$(printf '%s' "$o" | tail -3)"
printf '%s' "$o" | grep -qa '\[证据\]' && ok "打出证据（可待建）" || bad "没打出证据" "$(printf '%s' "$o" | tail -3)"

echo "== ③ 没有理由就直说：需求:猜数字游戏 不在理由层 =="
o=$(run '::whyfor 需求:猜数字游戏')
printf '%s' "$o" | grep -qaE '没有登记 理由/证据/原因|图里没有' && ok "没有理由时直说" || bad "没直说没有理由" "$(printf '%s' "$o" | tail -2)"

echo "== ④ 失败也要有原因：失败:中位数-最大值链 =="
o=$(run '::whyfor 失败:中位数-最大值链')
printf '%s' "$o" | grep -qa '\[原因\]' && ok "打出失败原因" || bad "没打原因" "$(printf '%s' "$o" | tail -2)"

echo "== ⑤ 不存在的对象 / 空参数 =="
o=$(run '::whyfor 需求:根本不存在的东西')
printf '%s' "$o" | grep -qa '图里没有「' && ok "不存在的对象不编理由" || bad "给不存在对象编了理由" "$(printf '%s' "$o" | tail -2)"
o=$(run '::whyfor')
printf '%s' "$o" | grep -qa '\[用法\]' && ok "空参数给用法" || bad "空参数没给用法" "$(printf '%s' "$o" | tail -2)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL whyfor（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS whyfor（$pass 过 / 0 红）"
