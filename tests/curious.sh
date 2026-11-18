#!/bin/sh
# tests/curious.sh — §6.927 好奇心队列：不会先入队、去重、按需再问（离线假端点）
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
BIN=${BIN:-./build_aip}
[ -x "$BIN" ] || { echo "FAIL: 缺 $BIN"; exit 1; }
[ -f code/code_model.bin ] || sh code/build_code_model.sh > /dev/null 2>&1
W="$ROOT/_t/curious_case"; rm -rf "$W"; mkdir -p "$W/_t/work"
cp "$BIN" "$W/build_aip"; cp code/code_model.bin "$W/model.bin"
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
trap 'kill ${SRV:-0} ${SRV2:-0} 2>/dev/null' EXIT

echo "== ① 合成失败自动入队，列表能看到，同一问题不重复入队 =="
run '::code synth 写一个会唱歌的咖啡机控制系统' > /dev/null
run '::code synth 写一个会唱歌的咖啡机控制系统' > /dev/null
n=$(grep -c "咖啡机" "$W/_t/curious.tsv" 2>/dev/null || true)
[ "$n" = "1" ] && ok "入队且 24h 去重（1 条）" || bad "入队/去重不对" "条数=$n"
o=$(run '::curious')
printf '%s' "$o" | grep -qa '咖啡机' && ok "列表能看到" || bad "列表没有" "$(printf '%s' "$o" | tail -2)"
printf '%s' "$o" | grep -qa '为什么问：没有匹配' && ok "每条带“为什么问”（失败原因）" || bad "没记失败原因" "$(printf '%s' "$o" | grep -a 咖啡机 | head -1)"

echo "== ② 没开外部工具时 ask 明确拒绝 =="
o=$(run '::curious ask 1')
printf '%s' "$o" | grep -qa '外部工具没开' && ok "没开工具：拒绝" || bad "没开工具也问" "$(printf '%s' "$o" | tail -2)"

echo "== ③ 开了外部工具：ask 走升级链路（先搜索再问） =="
python3 "$ROOT/tools/fake_openai.py" --port 0 --reply "假端点：先看错误行，再缩到最小例。" \
    > "$W/srv.log" 2>&1 &
SRV=$!
PORT=""; i=0
while [ "$i" -lt 50 ]; do PORT=$(head -1 "$W/srv.log" 2>/dev/null | tr -cd '0-9'); [ -n "$PORT" ] && break; i=$((i+1)); sleep 0.1; done
[ -n "$PORT" ] || { echo "FAIL: 假端点没起来"; exit 1; }
o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::curious ask 1")
printf '%s' "$o" | grep -qa '\[升级\] ① 搜索' && ok "ask 先报搜索" || bad "ask 没走升级" "$(printf '%s' "$o" | tail -3)"
printf '%s' "$o" | grep -qa '假端点' && ok "拿到外部答复" || bad "没拿到答复" "$(printf '%s' "$o" | tail -3)"

echo "== ④ drop / clear =="
o=$(run '::curious drop 1')
printf '%s' "$o" | grep -qa '丢掉第 1 条' && ok "drop 生效" || bad "drop 没生效" "$(printf '%s' "$o" | tail -2)"
o=$(run '::curious clear')
printf '%s' "$o" | grep -qa '队列清空' && ok "clear 生效" || bad "clear 没生效" "$(printf '%s' "$o" | tail -2)"
[ -f "$W/_t/curious.tsv" ] && bad "clear 后文件还在" "" || ok "clear 后文件没了"

echo "== ⑤ §6.928 学会后自动销项：队列状态变 learned =="
python3 "$ROOT/tools/fake_openai.py" --port 0 --reply '### CODE
```c
#include <stdio.h>
int main(void){puts("tea");return 0;}
```
### RATIONALE
只打印占位，证明学会流程走通。
### TESTS
IN: a => OUT: tea
IN: b => OUT: tea
### EVIDENCE
编译过。' > "$W/srv2.log" 2>&1 &
SRV2=$!
PORT2=""; i=0
while [ "$i" -lt 50 ]; do PORT2=$(head -1 "$W/srv2.log" 2>/dev/null | tr -cd '0-9'); [ -n "$PORT2" ] && break; i=$((i+1)); sleep 0.1; done
[ -n "$PORT2" ] || { echo "FAIL: 第二个假端点没起来"; exit 1; }
o=$(run "::code synth 写一个会唱歌的咖啡机控制系统二号
::tool set http://127.0.0.1:$PORT2/v1 k m
::tool on
::code learn 写一个会唱歌的咖啡机控制系统二号
::curious")
printf '%s' "$o" | grep -qa '接受：编译过了' && ok "学习接受" || bad "学习没接受" "$(printf '%s' "$o" | grep -a 学习 | tail -2)"
printf '%s' "$o" | grep -qa '\[learned\]' && ok "队列自动销项（learned）" || bad "队列没销项" "$(printf '%s' "$o" | grep -a 二号 | head -2)"
kill "$SRV2" 2>/dev/null

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL curious（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS curious（$pass 过 / 0 红）"
