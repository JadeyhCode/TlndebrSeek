#!/bin/sh
# tests/learn.sh — §6.920 自学闭环 v1：本地先做，不会才问教师；无理由/无证据/编译不过都不落盘
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
BIN=${BIN:-./build_aip}
[ -x "$BIN" ] || { echo "FAIL: 缺 $BIN"; exit 1; }
[ -f code/code_model.bin ] || sh code/build_code_model.sh > /dev/null 2>&1
[ -f code/code_model.bin ] || { echo "FAIL: 缺 code/code_model.bin"; exit 1; }

W="$ROOT/_t/learn_case"; rm -rf "$W"; mkdir -p "$W"
cp "$BIN" "$W/build_aip"; cp code/code_model.bin "$W/model.bin"

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
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }

echo "== ① 本地已经会了：不问教师、不落盘 =="
o=$(run '::act on\n::code learn 读入一行整数（标准输入），输出它们的和')
printf '%s' "$o" | grep -qa '本地已经会了' && ok "本地会：不叫教师" || bad "本地会还去问教师" "$(printf '%s' "$o" | tail -2)"

echo "== ①b 写入门没开：本地会也不乱问教师 =="
o=$(run '::code learn 读入一行整数（标准输入），输出它们的和')
printf '%s' "$o" | grep -qa '写入门关着' && ok "写入门关着：提示先 ::act on" || bad "写入门关着还去问教师" "$(printf '%s' "$o" | tail -2)"

echo "== ② 不会且教师没开：不瞎写、不落盘 =="
o=$(run '::code learn 写一个会唱歌的咖啡机控制系统')
printf '%s' "$o" | grep -qa '不能瞎写' && ok "教师没开：拒绝" || bad "教师没开还写" "$(printf '%s' "$o" | tail -2)"

echo "== ③ 教师给了代码+理由+证据：接受并落盘到候选 triples =="
start_server '### CODE
```c
#include <stdio.h>
int main(void){long x,s=0;while(scanf("%ld",&x)==1)s+=x;printf("%ld\n",s);return 0;}
```
### RATIONALE
边读边加，不需要数组，省内存。
### EVIDENCE
本地 gcc 编译通过。'
o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::code learn 实现一个简易的待办清单管理器")
printf '%s' "$o" | grep -qa '接受：编译过了' && ok "有理由有证据：接受" || bad "该接受没接受" "$(printf '%s' "$o" | tail -3)"
[ -s "$W/_t/learn/accepted.triples" ] && grep -qa '理由' "$W/_t/learn/accepted.triples" && ok "候选 triples 里有理由" || bad "候选 triples 缺理由" "$(cat "$W/_t/learn/accepted.triples" 2>/dev/null | head -2)"
grep -qa '证据' "$W/_t/learn/accepted.triples" 2>/dev/null && ok "候选 triples 里有证据" || bad "候选 triples 缺证据" ""
ls "$W"/_t/learn/cand_*.c.out >/dev/null 2>&1 && ok "候选真的编译过了（.out 存在）" || bad "候选没编译" ""
stop_server

echo "== ④ 有代码没理由：拒绝落盘 =="
start_server '### CODE
```c
#include <stdio.h>
int main(void){puts("hi");return 0;}
```
### EVIDENCE
没验证。'
o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::code learn 写一个只会打印 hi 的程序")
printf '%s' "$o" | grep -qa '\*\*没有理由\*\*' && ok "没理由：拒绝" || bad "没理由也接受" "$(printf '%s' "$o" | tail -3)"
stop_server

echo "== ⑤ 有理由但编译不过：拒绝 =="
start_server '### CODE
```c
#include <stdio.h>
int main(void){ this is not C; return 0; }
```
### RATIONALE
随便写的。
### EVIDENCE
没验证。'
o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::code learn 写一个坏程序")
printf '%s' "$o" | grep -qa '编译没过' && ok "编译不过：拒绝" || bad "编译不过也接受" "$(printf '%s' "$o" | tail -3)"
stop_server

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL learn（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS learn（$pass 过 / 0 红）"
