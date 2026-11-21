#!/bin/sh
# tests/symtool.sh — §6.988 自省/自修改工具 ::sym（读、写、删、改、重命名、门禁）
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -x build_aip ] || { echo "FAIL: 缺 build_aip"; exit 1; }
W="$ROOT/_t/symtool"; rm -rf "$W"; mkdir -p "$W"
cp build_aip model.bin patterns.txt frames.txt relations.txt "$W/" 2>/dev/null
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }

echo "== ① 只读符号 =="
o=$(run '::sym active 5')
printf '%s' "$o" | grep -qa '池子共' && ok "active 能列符号" || bad "active 没输出" "$(printf '%s' "$o" | grep -a '符号' | head -2)"
o=$(run '::sym links 猫')
printf '%s' "$o" | grep -qa '出边' && printf '%s' "$o" | grep -qa '属于' && ok "links 猫 有出边/属于" || bad "links 猫 不对" "$(printf '%s' "$o" | grep -a '符号' | head -3)"

echo "== ② 默认只读：写被拒 =="
o=$(run '::sym edge add 测试甲 属于 测试乙')
printf '%s' "$o" | grep -qa '只读模式' && ok "默认只读拒写" || bad "默认没拦住" "$(printf '%s' "$o" | grep -a '符号' | head -2)"

echo "== ③ 开门后加边 / 查边 =="
o=$(run '::sym write on\n::sym edge add 测试甲 属于 测试乙\n::sym links 测试甲')
printf '%s' "$o" | grep -qa '已写入' && ok "加边成功" || bad "加边失败" "$(printf '%s' "$o" | grep -a '符号' | head -3)"
printf '%s' "$o" | grep -qa '属于 -> 测试乙' && ok "links 看得到新边" || bad "links 看不到" "$(printf '%s' "$o" | grep -a '->' | head -3)"

echo "== ④ 改边 属于→有 =="
o=$(run '::sym write on\n::sym edge add 测试甲 属于 测试乙\n::sym edge mod 测试甲 属于 测试乙 有\n::sym links 测试甲')
printf '%s' "$o" | grep -qa '有 -> 测试乙' && ok "改边成功" || bad "改边失败" "$(printf '%s' "$o" | grep -a '->' | head -3)"

echo "== ⑤ 删边 =="
o=$(run '::sym write on\n::sym edge add 测试甲 吃 测试乙\n::sym edge del 测试甲 吃 测试乙\n::sym links 测试甲')
printf '%s' "$o" | grep -qa '出边 0' && ok "删边后度 0" || bad "删边没生效" "$(printf '%s' "$o" | grep -a '出边' | head -2)"

echo "== ⑥ 新建 / 删除符号 =="
o=$(run '::sym write on\n::sym add 符号甲\n::sym del 符号甲\n::sym links 符号甲')
printf '%s' "$o" | grep -qa '已确保存在' && ok "新建符号" || bad "没新建" "$(printf '%s' "$o" | grep -a '符号' | head -2)"
printf '%s' "$o" | grep -qa '垃圾' && ok "删除标垃圾" || bad "删除没标" "$(printf '%s' "$o" | grep -a '符号甲' | head -2)"

echo "== ⑦ 重命名搬边 =="
o=$(run '::sym write on\n::sym edge add 甲兽 属于 神兽\n::sym rename 甲兽 乙兽\n::sym links 乙兽')
printf '%s' "$o" | grep -qa '搬 1 条边' && ok "搬边计数 1" || bad "搬边不对" "$(printf '%s' "$o" | grep -a '符号' | head -3)"
printf '%s' "$o" | grep -qa '属于 -> 神兽' && ok "新符号继承了边" || bad "新符号没边" "$(printf '%s' "$o" | grep -a '->' | head -3)"

echo "== ⑧ 入边查询 =="
o=$(run '::sym write on\n::sym edge add 丙兽 属于 丁兽\n::sym links 丁兽')
printf '%s' "$o" | grep -qa '丙兽.*属于' && ok "入边能看到丙兽" || bad "入边没看到" "$(printf '%s' "$o" | grep -a '入边' -A2 | head -4)"

echo "== ⑨ 关门后写回退 =="
o=$(run '::sym write on\n::sym write off\n::sym edge add 戊兽 属于 己兽')
printf '%s' "$o" | grep -qa '只读模式' && ok "关门后又拒写" || bad "关门没拦住" "$(printf '%s' "$o" | grep -a '符号' | head -3)"

echo "== ⑩ 撤销：加边/删边/改边/删符号 =="
o=$(run '::sym write on\n::sym edge add 甲 属于 乙\n::sym undo\n::sym links 甲')
printf '%s' "$o" | grep -qa '加边已回滚' && ok "撤销加边" || bad "撤销加边没生效" "$(printf '%s' "$o" | grep -a '撤销' | head -2)"
printf '%s' "$o" | grep -qa '出边 0' && ok "撤销后出边 0" || bad "撤销后还有边" "$(printf '%s' "$o" | grep -a '出边' | head -2)"
o=$(run '::sym write on\n::sym edge add 甲 属于 乙\n::sym edge del 甲 属于 乙\n::sym undo\n::sym links 甲')
printf '%s' "$o" | grep -qa '删边已加回' && ok "撤销删边" || bad "撤销删边没生效" "$(printf '%s' "$o" | grep -a '撤销' | head -2)"
o=$(run '::sym write on\n::sym edge add 甲 属于 乙\n::sym edge mod 甲 属于 乙 有\n::sym undo\n::sym links 甲')
printf '%s' "$o" | grep -qa '改边已还原' && ok "撤销改边" || bad "撤销改边没生效" "$(printf '%s' "$o" | grep -a '撤销' | head -2)"
printf '%s' "$o" | grep -qa '属于 -> 乙' && ok "改边撤销后回到 属于" || bad "关系没还原" "$(printf '%s' "$o" | grep -a -- '->' | head -2)"
o=$(run '::sym write on\n::sym add 符号丙\n::sym del 符号丙\n::sym undo\n::sym links 符号丙')
printf '%s' "$o" | grep -qa '符号删除已回滚' && ok "撤销删符号" || bad "撤销删符号没生效" "$(printf '%s' "$o" | grep -a '撤销' | head -2)"

echo "== ⑪ active 有「最近触碰」 =="
o=$(run '::sym active 3')
printf '%s' "$o" | grep -qa '最近触碰' && ok "active 列最近触碰" || bad "active 没有最近触碰" "$(printf '%s' "$o" | grep -a '活跃' | head -2)"

echo "== ⑫ JSON 输出（links/active） =="
o=$(run '::sym links 猫 json')
line=$(printf '%s' "$o" | grep -a '"name"' | head -1 | sed 's/^你 > //')
printf '%s' "$line" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["name"]=="猫" and d["degree"]>0 and len(d["out"])>0; print("ok")' >/dev/null 2>&1 \
    && ok "links json 可解析且 out 非空" || bad "links json 不合法" "$(printf '%s' "$line" | cut -c1-80)"
o=$(run '::sym active 2 json')
line=$(printf '%s' "$o" | grep -a '"pool"' | head -1 | sed 's/^你 > //')
printf '%s' "$line" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["pool"]>0 and "recent" in d; print("ok")' >/dev/null 2>&1 \
    && ok "active json 可解析且 pool>0" || bad "active json 不合法" "$(printf '%s' "$line" | cut -c1-80)"

echo "== ⑬ 理由登记 + 写操作日志 =="
o=$(run '::sym write on\n::sym reason 因为甲兽是测试分类\n::sym edge add 甲兽 属于 乙兽\n::sym log')
printf '%s' "$o" | grep -qa '下一条写操作的理由' && ok "reason 记录理由" || bad "reason 没记" "$(printf '%s' "$o" | grep -a '理由' | head -2)"
printf '%s' "$o" | grep -qa 'edge.add.*甲兽.*属于.*乙兽.*因为甲兽是测试分类' && ok "日志含操作+理由" || bad "日志缺理由" "$(printf '%s' "$o" | grep -a 'edge.add' | head -2)"
o=$(run '::sym write on\n::sym edge add 丙兽 属于 丁兽\n::sym log')
printf '%s' "$o" | grep -qa '未给理由' && ok "没给理由也登记" || bad "没登记未给理由" "$(printf '%s' "$o" | grep -a 'edge.add' | head -2)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL symtool（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS symtool（$pass 过 / 0 红）"
