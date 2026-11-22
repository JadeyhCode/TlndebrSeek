#!/bin/sh
# tests/toolcall.sh — §6.993 模型可调用自省/自修改工具（「工具 …」→ ::sym，过网关/写入门/限额）
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -x build_aip ] || { echo "FAIL: 缺 build_aip"; exit 1; }
W="$ROOT/_t/toolcall"; rm -rf "$W"; mkdir -p "$W"
cp build_aip model.bin patterns.txt frames.txt relations.txt "$W/" 2>/dev/null
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }

echo "== ① 只读工具：active / links =="
o=$(run '工具 active')
printf '%s' "$o" | grep -qa '焦点环' && ok "工具 active 有输出" || bad "工具 active 没输出" "$(printf '%s' "$o" | grep -a 'AI >' | head -2)"
o=$(run '工具 links 猫')
printf '%s' "$o" | grep -qa '属于' && ok "工具 links 猫 看得到属于" || bad "工具 links 猫 不对" "$(printf '%s' "$o" | grep -a '符号' | head -2)"
o=$(run '工具 看看猫的连接')
printf '%s' "$o" | grep -qa '猫  id=' && ok "无空格自然句能路由到 links" || bad "自然句没路由" "$(printf '%s' "$o" | grep -a '符号' | head -2)"

echo "== ② 模型不能自己开写入门 =="
o=$(run '工具 write on')
printf '%s' "$o" | grep -qa '写入门没开' && ok "工具 write on 被拒" || bad "模型自己开了写入门" "$(printf '%s' "$o" | grep -a '工具' | head -2)"
o=$(run '工具 edge add 甲 属于 乙')
printf '%s' "$o" | grep -qa '写入门没开' && ok "写操作被拒" || bad "写操作没拦住" "$(printf '%s' "$o" | grep -a '工具' | head -2)"

echo "== ③ 人开门后：理由 + 写 + 查 + 日志 =="
o=$(run '::sym write on\n工具 reason 因为甲是测试\n工具 edge add 甲 属于 乙\n工具 links 甲\n工具 log')
printf '%s' "$o" | grep -qa '已写入' && ok "工具能写边" || bad "工具写边失败" "$(printf '%s' "$o" | grep -a '符号' | head -3)"
printf '%s' "$o" | grep -qa '属于 -> 乙' && ok "写后 links 能看到" || bad "写后看不到边" "$(printf '%s' "$o" | grep -a -- '->' | head -2)"
printf '%s' "$o" | grep -qa 'edge.add.*因为甲是测试' && ok "日志带上了理由" || bad "日志没理由" "$(printf '%s' "$o" | grep -a 'edge.add' | head -2)"

echo "== ④ 网关账本 =="
o=$(run '::sym write on\n工具 reason 测试\n工具 edge add 甲兽 属于 乙兽\n工具 gate')
printf '%s' "$o" | grep -qa '工具网关' && ok "gate 有账本" || bad "gate 没输出" "$(printf '%s' "$o" | grep -a 'AI >' | head -2)"
printf '%s' "$o" | grep -qa 'allow_write' && ok "记账含 allow_write" || bad "账本没记写入" "$(printf '%s' "$o" | grep -a 'self' | head -2)"

echo "== ⑤ 写次数限额 =="
o=$(AIP_TOOLWRITE_LIMIT=1 run '::sym write on\n工具 reason r1\n工具 edge add 甲 属于 乙\n工具 reason r2\n工具 edge add 丙 属于 丁')
printf '%s' "$o" | grep -qa '到限额' && ok "超额被拒" || bad "限额没生效" "$(printf '%s' "$o" | grep -a '工具' | head -3)"

echo "== ⑥ 只读 dry 也要写入门 =="
o=$(run '工具 dry edge add 甲 属于 乙')
printf '%s' "$o" | grep -qa '写入门没开' && ok "dry 被写入门挡住" || bad "dry 绕过写入门" "$(printf '%s' "$o" | grep -a '工具' | head -2)"

echo "== ⑦ 无理由不落盘 + 理由进修改账 =="
o=$(run '::sym write on\n工具 edge add 无由甲 属于 无由乙')
printf '%s' "$o" | grep -qa '要先给理由' && ok "无理由写入被拒" || bad "无理由也写了" "$(printf '%s' "$o" | grep -a '工具' | head -2)"
o=$(run '::sym write on\n工具 reason 因为甲是测试分类\n工具 edge add 甲 属于 乙\n::mods')
printf '%s' "$o" | grep -qa '理由:因为甲是测试分类' && ok "理由进修改账" || bad "修改账没有理由" "$(printf '%s' "$o" | grep -a '加关系' | head -2)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL toolcall（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS toolcall（$pass 过 / 0 红）"
