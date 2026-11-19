#!/bin/sh
# tests/py.sh — §6.950 Python 最小自学闭环：教师给 CODE/TESTS，python3 验过才落盘
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
BIN=${BIN:-./build_aip}
[ -x "$BIN" ] || { echo "FAIL: 缺 $BIN"; exit 1; }
[ -f code/code_model.bin ] || sh code/build_code_model.sh > /dev/null 2>&1
W="$ROOT/_t/py_case"; rm -rf "$W"; mkdir -p "$W"
cp "$BIN" "$W/build_aip"; cp code/code_model.bin "$W/model.bin"
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
start_server() {
    python3 "$ROOT/tools/fake_openai.py" --port 0 --reply "$1" --dump "$W/body.json" \
        > "$W/server.log" 2>&1 &
    SRV=$!
    PORT=""
    i=0
    while [ "$i" -lt 50 ]; do
        PORT=$(head -1 "$W/server.log" 2>/dev/null | tr -cd '0-9')
        [ -n "$PORT" ] && break
        i=$((i + 1)); sleep 0.1
    done
    [ -n "$PORT" ] || { echo "FAIL: 假端点没起来"; exit 1; }
}
stop_server() { kill "$SRV" 2>/dev/null; }
trap 'stop_server' EXIT
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }
task='把一段 CSV 行按逗号切分后输出字段个数（Python）'

echo "== ① 教师没开：不在本地瞎写 Python =="
o=$(run "::act on\n::code learn --py $task")
printf '%s' "$o" | grep -qa '不能瞎写' && ok "教师没开：拒绝" || bad "教师没开还写" "$(printf '%s' "$o" | tail -2)"

echo "== ② 教师给 Python + 2 条测试：接受并落盘 =="
start_server '### CODE
```python
import sys
line = sys.stdin.read().strip()
print(0 if not line else len(line.split(",")))
```
### RATIONALE
按逗号切分后取长度；空行单独处理。
### TESTS
IN: a,b,c => OUT: 3
IN: x => OUT: 1
### EVIDENCE
本地 python3 语法检查通过。'
o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::code learn --py $task")
printf '%s' "$o" | grep -qa '接受' && ok "教师代码：接受" || bad "教师代码没接受" "$(printf '%s' "$o" | tail -3)"
ls "$W"/_t/py/cand_*.py >/dev/null 2>&1 && ok "候选 .py 落盘" || bad "没有候选 .py" "$(ls "$W"/_t/py 2>/dev/null | head -3)"
grep -qa "$task" "$W/_t/py/registry.tsv" 2>/dev/null && ok "registry 记下任务" || bad "registry 没记" ""
cand=$(ls "$W"/_t/py/cand_*.py 2>/dev/null | head -1)
if [ -n "$cand" ]; then
    got=$(printf 'a,b,c,d\n' | python3 "$cand" 2>/dev/null)
    [ "$got" = "4" ] && ok "候选实跑对（4）" || bad "候选实跑不对" "got=$got"
else bad "没候选可跑" ""; fi
stop_server

echo "== ②b teacher-free 回放：同一描述不再叫教师，重跑存的测试 =="
o=$(run "::code learn --py $task")
printf '%s' "$o" | grep -qa '回放通过' && ok "回放通过：不叫教师" || bad "没有回放" "$(printf '%s' "$o" | tail -3)"
printf '%s' "$o" | grep -qa '问教师' && bad "回放还去问教师" "" || ok "确实没问教师"

echo "== ③ 教师给的 Python 语法错：拒绝，不落盘 =="
start_server '### CODE
```python
def broken(:
    pass
```
### RATIONALE
占位。
### TESTS
IN: 1 => OUT: 1
IN: 2 => OUT: 2
### EVIDENCE
没验证。'
o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::code learn --py 解析日志行并输出告警数量（Python）")
printf '%s' "$o" | grep -qa '语法\|编译没过' && ok "语法错：拒绝" || bad "语法错也接受" "$(printf '%s' "$o" | tail -3)"
stop_server

echo "== ④ §6.952 本地模板：没教师也能做（自带测试验过） =="
o=$(run "::act on\n::code learn --py 把一行数字用空格分开后输出它们的和")
printf '%s' "$o" | grep -qa '本地模板接受' && ok "求和：本地模板接受" || bad "本地模板没接受" "$(printf '%s' "$o" | tail -3)"
printf '%s' "$o" | grep -qa '\[学习\] 问教师' && bad "本地模板还问教师" "" || ok "本地模板没问教师"
c2=$(ls -t "$W"/_t/py/cand_*.py 2>/dev/null | head -1)
if [ -n "$c2" ]; then
    got=$(printf '1 2 3 4\n' | python3 "$c2" 2>/dev/null)
    [ "$got" = "10" ] && ok "模板实跑对（10）" || bad "模板实跑不对" "got=$got"
else bad "没有模板候选" ""; fi

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL py（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS py（$pass 过 / 0 红）"
