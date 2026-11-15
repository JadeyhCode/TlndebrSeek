#!/bin/sh
# tests/plan.sh — **需求分解**（§6.872）：一句话 → 需求树（必需/可选/排除）→ 可执行要点
#
# 判据：
#   1) “写一个跑酷游戏”必须拆出 平台跳跃/物理/重力/碰撞/左右移动，并**明确排除** 音效、计分；
#   2) 树的顺序必须先“平台跳跃”后“重力”“碰撞”（父先于子）；
#   3) 换一个根（猜数字游戏）也要能拆（证明不是把跑酷写死）；
#   4) 没登记的需求 ⇒ 明确说“没有匹配的需求根”，不许硬编。
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
mkdir -p _t/work
AIP=_t/work/plan_aip
sh "$ROOT/tests/prebuilt.sh" "$AIP" "$ROOT/main.c" -std=c11 -O2 >/dev/null 2>&1 || \
    gcc -std=c11 -O2 -o "$AIP" "$ROOT/main.c" -lm
[ -x "$AIP" ] || { echo "FAIL: 编不出 aip"; exit 1; }
[ -x ./build_aip ] || cp "$AIP" ./build_aip
[ -f code/code_model.bin ] || sh code/build_code_model.sh > _t/work/build.log 2>&1
[ -f code/code_model.bin ] || { echo "FAIL: 缺 code/code_model.bin"; exit 1; }
M=_t/work/plan_model.bin
cp code/code_model.bin "$M"
printf "::ingest code/knowledge/plan.triples\n::save %s\n::quit\n" "$M" \
    | "$AIP" --model "$M" > _t/work/plan_ingest.log 2>&1
fails=0
run() {
    printf "::code plan %s\n::quit\n" "$1" | "$AIP" --model "$M" > _t/work/plan.txt 2>&1
}

# 1) 跑酷：必需子需求 + 排除项
run 写一个跑酷游戏
for w in 需求分解 平台跳跃 平台 角色 物理 重力 碰撞 左右移动 上升 下落 排除 先写这些; do
    grep -qa "$w" _t/work/plan.txt || { echo "  [FAIL] 跑酷分解缺 $w"; fails=$((fails+1)); }
done
for w in 音效 计分; do
    grep -qa "$w" _t/work/plan.txt || { echo "  [FAIL] 排除项缺 $w"; fails=$((fails+1)); }
done

# 2) 顺序：父先于子
L1=$(grep -na '平台跳跃' _t/work/plan.txt | head -1 | cut -d: -f1)
L2=$(grep -na '重力' _t/work/plan.txt | head -1 | cut -d: -f1)
L3=$(grep -na '碰撞' _t/work/plan.txt | head -1 | cut -d: -f1)
if [ -n "$L1" ] && [ -n "$L2" ] && [ -n "$L3" ] && [ "$L1" -lt "$L2" ] && [ "$L2" -lt "$L3" ]; then :; else
    echo "  [FAIL] 顺序不对（平台跳跃 $L1 < 重力 $L2 < 碰撞 $L3）"; fails=$((fails+1));
fi

# 3) 另一个根：猜数字
run 写一个猜数字游戏
for w in 随机数 输入循环 比较反馈; do
    grep -qa "$w" _t/work/plan.txt || { echo "  [FAIL] 猜数字分解缺 $w"; fails=$((fails+1)); }
done

# 4) 未登记的需求：明确拒绝
run 写一个区块链浏览器
grep -qa '没有匹配的需求根' _t/work/plan.txt || { echo "  [FAIL] 未登记需求没有明确拒绝"; fails=$((fails+1)); }

if [ "$fails" -eq 0 ]; then echo "PASS plan（跑酷/猜数字两棵需求树 + 排除项 + 顺序 + 未登记拒绝）"; exit 0; fi
echo "FAIL plan（$fails 处）"; exit 1
