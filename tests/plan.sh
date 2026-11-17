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

# 4) `--data` 依据可追溯：边必须打印；默认不带
printf "::code plan --data 写一个跑酷游戏\n::quit\n" | "$AIP" --model "$M" > _t/work/plan_data.txt 2>&1
for w in '依据' '--[分解]' '--[排除]'; do
    grep -qaF -- "$w" _t/work/plan_data.txt || { echo "  [FAIL] --data 缺依据 $w"; fails=$((fails+1)); }
done
printf "::code plan 写一个跑酷游戏\n::quit\n" | "$AIP" --model "$M" > _t/work/plan_plain.txt 2>&1
if grep -qa '依据' _t/work/plan_plain.txt; then echo '  [FAIL] 默认不该打印依据'; fails=$((fails+1)); fi

# 6) §6.887 `--write`：需求 → 可编译骨架（要点缺一不可，且骨架要真能编）
rm -f _t/work/plan_write.c _t/work/plan_write.c.out
printf "::act on\n::code plan --write 写一个数组统计小工具\n::quit\n" | "$AIP" --model "$M" > _t/work/plan_write.txt 2>&1
grep -qa 'plan --write' _t/work/plan_write.txt || { echo "  [FAIL] --write 没输出摘要"; fails=$((fails+1)); }
grep -qa '2 个要点' _t/work/plan_write.txt || { echo "  [FAIL] --write 要点数不对"; fails=$((fails+1)); }
grep -qa '编过' _t/work/plan_write.txt || { echo "  [FAIL] --write 骨架没编过"; fails=$((fails+1)); }
if [ -s _t/work/plan_write.c ]; then
    for w in '输出它们的和' '输出最大值' 'impl_1' 'impl_2' '[已覆盖]'; do
        grep -qaF -- "$w" _t/work/plan_write.c || { echo "  [FAIL] 骨架缺 $w"; fails=$((fails+1)); }
    done
    gcc -std=c11 -Wall -Wextra -o _t/work/plan_write.verify _t/work/plan_write.c 2> _t/work/plan_write.gcc \
        || { echo "  [FAIL] 骨架独立 gcc 编不过：$(head -2 _t/work/plan_write.gcc | tr '\n' ' ')"; fails=$((fails+1)); }
    # §6.895 每条已覆盖的要点必须**真的生成成函数**（impl_<i>），而不是只留注释
    grep -qa 'static int impl_1' _t/work/plan_write.c || { echo "  [FAIL] 要点 1 没有内嵌成函数"; fails=$((fails+1)); }
    grep -qa 'static int impl_2' _t/work/plan_write.c || { echo "  [FAIL] 要点 2 没有内嵌成函数"; fails=$((fails+1)); }
    grep -qa '2 条已内嵌成函数' _t/work/plan_write.txt || { echo "  [FAIL] 摘要里没报内嵌函数数"; fails=$((fails+1)); }
    # §6.899 骨架必须**逐条自测**：内嵌函数返回码汇总，失败要能报 plan FAIL
    grep -qa 'if (impl_1() != 0) okp = 0;' _t/work/plan_write.c \
        || { echo "  [FAIL] 骨架没有逐条检查 impl 返回码"; fails=$((fails+1)); }
    if [ -x _t/work/plan_write.verify ]; then
        _t/work/plan_write.verify > _t/work/plan_write.run 2>&1
        rc=$?
        [ "$rc" -eq 0 ] || { echo "  [FAIL] 骨架产物退出码 $rc（应为 0）"; fails=$((fails+1)); }
        grep -qa 'plan ok' _t/work/plan_write.run || { echo "  [FAIL] 骨架产物没打 plan ok"; fails=$((fails+1)); }
    fi
else
    echo "  [FAIL] --write 没写出骨架文件"; fails=$((fails+1))
fi
# 6b) §6.902 逐条测试文件：存在、能编、跑出 test ok (2/2)
if [ -s _t/work/plan_write_test.c ]; then
    grep -qaF '#include "plan_write.c"' _t/work/plan_write_test.c \
        || { echo "  [FAIL] 测试文件没 include 骨架"; fails=$((fails+1)); }
    gcc -std=c11 -Wall -Wextra -o _t/work/plan_write_test _t/work/plan_write_test.c 2> _t/work/plan_write_test.gcc \
        || { echo "  [FAIL] 逐条测试文件编不过：$(head -2 _t/work/plan_write_test.gcc | tr '\n' ' ')"; fails=$((fails+1)); }
    if [ -x _t/work/plan_write_test ]; then
        _t/work/plan_write_test > _t/work/plan_write_test.run 2>&1
        rc=$?
        [ "$rc" -eq 0 ] || { echo "  [FAIL] 逐条测试退出码 $rc"; fails=$((fails+1)); }
        grep -qa 'test ok (2/2 points, embedded 2, todo 0)' _t/work/plan_write_test.run \
            || { echo "  [FAIL] 逐条测试没打 test ok (2/2 points, embedded 2, todo 0)"; fails=$((fails+1)); }
    fi
else
    echo "  [FAIL] 没生成逐条测试文件"; fails=$((fails+1))
fi

# 6c) §6.904 未覆盖要点的桩也要进测试：猜数字游戏（3 个要点全不会）→ test ok (3/3 points, embedded 0, todo 3)
printf "::act on\n::code plan --write 写一个猜数字游戏\n::quit\n" | "$AIP" --model "$M" > _t/work/plan_write_todo.txt 2>&1
if [ -s _t/work/plan_write_test.c ]; then
    gcc -std=c11 -Wall -Wextra -o _t/work/plan_write_todo _t/work/plan_write_test.c 2> _t/work/plan_write_todo.gcc \
        || { echo "  [FAIL] 桩测试文件编不过"; fails=$((fails+1)); }
    if [ -x _t/work/plan_write_todo ]; then
        _t/work/plan_write_todo > _t/work/plan_write_todo.run 2>&1
        rc=$?
        [ "$rc" -eq 0 ] || { echo "  [FAIL] 桩测试退出码 $rc"; fails=$((fails+1)); }
        grep -qaE 'test ok \([0-9]+/[0-9]+ points, embedded 0, todo [0-9]+\)' _t/work/plan_write_todo.run \
            || { echo "  [FAIL] 桩测试摘要不对（应 test ok (N/N points, embedded 0, todo N)）"; fails=$((fails+1)); }
        grep -qa 'TODO' _t/work/plan_write_todo.run \
            || { echo "  [FAIL] 桩测试没标 TODO"; fails=$((fails+1)); }
    fi
fi

# 6e) §6.908 可追溯报告：要点/覆盖/函数/测试/顺序（先重跑一次数组统计小工具，保证报告对得上）
printf "::act on\n::code plan --write 写一个数组统计小工具\n::quit\n" | "$AIP" --model "$M" > _t/work/plan_write_report_run.txt 2>&1
if [ -s _t/work/plan_write_report.md ]; then
    for w in '要点：2（已覆盖 2' '输出它们的和' '输出最大值' 'impl_1' 'test_impl_1' '调用顺序'; do
        grep -qaF -- "$w" _t/work/plan_write_report.md \
            || { echo "  [FAIL] 报告缺 $w"; fails=$((fails+1)); }
    done
else
    echo "  [FAIL] 没生成 plan_write_report.md"; fails=$((fails+1))
fi

# 6d) §6.906 依赖边决定调用顺序（顺序工具：先写A 依赖 后写B ⇒ impl_2 必须排在 impl_1 之前）
printf "::act on\n::code plan --write 写一个顺序工具\n::quit\n" | "$AIP" --model "$M" > _t/work/plan_write_dep.txt 2>&1
L1=$(grep -na 'if (impl_1()' _t/work/plan_write.c | head -1 | cut -d: -f1)
L2=$(grep -na 'if (impl_2()' _t/work/plan_write.c | head -1 | cut -d: -f1)
if [ -n "$L1" ] && [ -n "$L2" ] && [ "$L2" -lt "$L1" ]; then :; else
    echo "  [FAIL] 依赖顺序不对（impl_2 行 $L2 应在 impl_1 行 $L1 之前）"; fails=$((fails+1));
fi
grep -qaF 'impl_2 → impl_1' _t/work/plan_write_report.md \
    || { echo "  [FAIL] 报告里的调用顺序不对"; fails=$((fails+1)); }

# 6f) §6.912 严格模式：未覆盖要点记为失败（CI 用）；默认模式只标 TODO
printf "::act on\n::code plan --write --strict 写一个数组统计小工具\n::quit\n" | "$AIP" --model "$M" > _t/work/plan_strict_ok.txt 2>&1
if grep -qa '严格模式' _t/work/plan_strict_ok.txt; then :; else echo "  [FAIL] 严格模式没在摘要里标出"; fails=$((fails+1)); fi
gcc -std=c11 -Wall -Wextra -o _t/work/plan_strict_ok _t/work/plan_write_test.c 2>/dev/null
if [ -x _t/work/plan_strict_ok ]; then
    _t/work/plan_strict_ok > _t/work/plan_strict_ok.run 2>&1
    rc=$?
    [ "$rc" -eq 0 ] || { echo "  [FAIL] 全可合成树的严格测试应通过（rc=$rc）"; fails=$((fails+1)); }
    grep -qa 'todo 0, strict' _t/work/plan_strict_ok.run || { echo "  [FAIL] 严格模式摘要缺 strict"; fails=$((fails+1)); }
fi
printf "::act on\n::code plan --write --strict 写一个猜数字游戏\n::quit\n" | "$AIP" --model "$M" > _t/work/plan_strict_bad.txt 2>&1
gcc -std=c11 -Wall -Wextra -o _t/work/plan_strict_bad _t/work/plan_write_test.c 2>/dev/null
if [ -x _t/work/plan_strict_bad ]; then
    _t/work/plan_strict_bad > _t/work/plan_strict_bad.run 2>&1
    rc=$?
    [ "$rc" -ne 0 ] || { echo "  [FAIL] 有未覆盖要点的树在严格模式下应失败"; fails=$((fails+1)); }
    grep -qa 'FAIL (TODO)' _t/work/plan_strict_bad.run || { echo "  [FAIL] 严格模式没把 TODO 记为失败"; fails=$((fails+1)); }
fi

# 7) §6.901 带 argc/argv 的模板也必须内嵌（文件行数器）：impl_1(int argc, char **argv) + 调用给 (0, NULL)
printf "::act on\n::code plan --write 写一个文件行数器\n::quit\n" | "$AIP" --model "$M" > _t/work/plan_write_argv.txt 2>&1
grep -qaF 'static int impl_1(int argc, char **argv)' _t/work/plan_write.c \
    || { echo "  [FAIL] argc/argv 形态没有内嵌"; fails=$((fails+1)); }
grep -qaF 'impl_1(0, NULL)' _t/work/plan_write.c \
    || { echo "  [FAIL] argc/argv 形态调用没给 (0, NULL)"; fails=$((fails+1)); }
gcc -std=c11 -Wall -Wextra -o _t/work/plan_write_argv _t/work/plan_write.c 2> _t/work/plan_write_argv.gcc \
    || { echo "  [FAIL] argc 骨架编不过：$(head -2 _t/work/plan_write_argv.gcc | tr '\n' ' ')"; fails=$((fails+1)); }
if [ -x _t/work/plan_write_argv ]; then
    _t/work/plan_write_argv > _t/work/plan_write_argv.run 2>&1
    rc=$?
    [ "$rc" -eq 0 ] || { echo "  [FAIL] argc 骨架退出码 $rc"; fails=$((fails+1)); }
    grep -qa 'plan ok' _t/work/plan_write_argv.run || { echo "  [FAIL] argc 骨架没打 plan ok"; fails=$((fails+1)); }
fi

# 未登记的根：明确拒绝，不写文件
rm -f _t/work/plan_write.c
printf "::act on\n::code plan --write 写一个区块链浏览器\n::quit\n" | "$AIP" --model "$M" > _t/work/plan_write_bad.txt 2>&1
grep -qa '没有匹配的需求根' _t/work/plan_write_bad.txt || { echo "  [FAIL] --write 未登记需求没拒绝"; fails=$((fails+1)); }
[ -f _t/work/plan_write.c ] && { echo "  [FAIL] --write 拒绝时不该写文件"; fails=$((fails+1)); }

if [ "$fails" -eq 0 ]; then echo "PASS plan（两棵需求树 + 排除项 + 顺序 + 未登记拒绝 + --data 依据可追溯 + --write 可编译骨架）"; exit 0; fi
echo "FAIL plan（$fails 处）"; exit 1
