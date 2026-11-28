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
### TESTS
IN: 1 2 3 => OUT: 6
IN: 4 5 => OUT: 9
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
# 并行负载高时假端点偶发回包不完整（编译段丢失）⇒ 最多重试 4 次再判（12 路并行下截断可能连续出现），避免把“回包截断”记成“接受坏代码”
o=''
t=0
while [ "$t" -lt 4 ]; do
    o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::code learn 写一个坏程序")
    printf '%s' "$o" | grep -qa '编译没过' && break
    t=$((t + 1)); sleep 1
done
printf '%s' "$o" | grep -qa '编译没过' && ok "编译不过：拒绝" || bad "编译不过也接受" "$(printf '%s' "$o" | tail -3)"
stop_server

echo "== ⑥ 教师测试不过：拒绝（编译过不算证明）=="
start_server '### CODE
```c
#include <stdio.h>
int main(void){long x,s=0;while(scanf("%ld",&x)==1)s+=x;printf("%ld\n",s);return 0;}
```
### RATIONALE
边读边加。
### TESTS
IN: 1 2 => OUT: 999
IN: 3 4 => OUT: 7
### EVIDENCE
本地编译过。'
# 并行时假端点偶发回包不完整 ⇒ 最多重试 4 次再判（12 路并行下截断可能连续出现）（同 ⑤；别把“回包截断”记成“接受”）
o=''
r=0
while [ "$r" -lt 4 ]; do
    o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::code learn 写一个求和器三号")
    printf '%s' "$o" | grep -qa '教师测试没过' && break
    r=$((r + 1)); sleep 1
done
printf '%s' "$o" | grep -qa '教师测试没过' && ok "教师测试不过：拒绝" || bad "教师测试不过也接受" "$(printf '%s' "$o" | tail -3)"
stop_server

echo "== ⑦ 教师没给 TESTS：拒绝（没有可复现证据）=="
start_server '### CODE
```c
#include <stdio.h>
int main(void){puts("hi");return 0;}
```
### RATIONALE
打印 hi。
### EVIDENCE
编译过。'
o=''
r=0
while [ "$r" -lt 4 ]; do
    o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::code learn 写一个打印 hi 的程序二号")
    printf '%s' "$o" | grep -qa '没给够测试' && break
    r=$((r + 1)); sleep 1
done
printf '%s' "$o" | grep -qa '没给够测试' && ok "没 TESTS：拒绝" || bad "没 TESTS 也接受" "$(printf '%s' "$o" | tail -3)"
stop_server

echo "== ⑧ teacher-free：学过的题，关掉教师 + act on 后本地还能做 =="
o=$(run '::act on
::code synth 实现一个简易的待办清单管理器')
printf '%s' "$o" | grep -qa '本地记住的解' && ok "teacher-free：命中记住的解" || bad "教师关了就不会" "$(printf '%s' "$o" | tail -3)"
printf '%s' "$o" | grep -qa '测试全绿' && ok "teacher-free：产物测试全绿" || bad "teacher-free 产物不过" "$(printf '%s' "$o" | tail -3)"

echo "== ⑨ §6.934 accept 硬闸门：缺理由/编译不过都不许进待灌区 =="
mkdir -p "$W/_t/learn"
printf '没有理由的题\t_t/learn/none.c\t\t（没验证）\n编译不过的题\t_t/learn/bad.c\t理由：先这样\t证据：编译过\n' > "$W/_t/learn/accepted.tsv"
printf 'this is not C;\n' > "$W/_t/learn/bad.c"
o=$(run '::code accept all')
printf '%s' "$o" | grep -qa '缺理由' && ok "缺理由：拒绝" || bad "缺理由也接受" "$(printf '%s' "$o" | tail -2)"
printf '%s' "$o" | grep -qa '拒绝：候选编译不过' && ok "编译不过：拒绝" || bad "编译不过也接受" "$(printf '%s' "$o" | tail -2)"
[ -s "$W/_t/learn/graph.triples" ] && bad "拒绝却写了待灌区" "" || ok "两条都没落盘"

echo "== ⑩ 三样齐才通过，并写进待灌区（仍要 ::ingest 才进图）=="
printf '三样齐的题\t_t/learn/good.c\t理由：因为这样\t证据：教师测试 2/2\n' > "$W/_t/learn/accepted.tsv"
printf '#include <stdio.h>\nint main(void){puts("ok");return 0;}' > "$W/_t/learn/good.c"
o=$(run '::code accept 三样齐的题')
printf '%s' "$o" | grep -qa '通过' && ok "三样齐：通过" || bad "三样齐也没过" "$(printf '%s' "$o" | tail -3)"
[ -s "$W/_t/learn/graph.triples" ] && grep -qa '理由' "$W/_t/learn/graph.triples" && ok "待灌区写了理由" || bad "待灌区缺理由" ""
grep -qa '重新编译通过' "$W/_t/learn/graph.triples" 2>/dev/null && ok "证据带重新编译" || bad "证据没带编译" ""

echo "== ⑪ §6.935 accept 重跑 TESTS：存着的测试不对就不许落盘 =="
printf '测试不对的题\t_t/learn/good.c\t理由：占位\t证据：编译过\tx=>bye;\n' > "$W/_t/learn/accepted.tsv"
rm -f "$W/_t/learn/graph.triples"
o=$(run '::code accept 测试不对的题')
printf '%s' "$o" | grep -qa '测试重跑没过' && ok "测试重跑不过：拒绝" || bad "测试不对也接受" "$(printf '%s' "$o" | tail -2)"
[ -s "$W/_t/learn/graph.triples" ] && bad "拒绝了还写待灌区" "" || ok "拒绝后没有落盘"
printf '测试对的题\t_t/learn/good.c\t理由：占位\t证据：编译过\nx=>ok;\n' > "$W/_t/learn/accepted.tsv"
printf '#include <stdio.h>\nint main(void){puts("ok");return 0;}\n' > "$W/_t/learn/good.c"
o=$(run '::code accept 测试对的题')
printf '%s' "$o" | grep -qa '通过' && ok "测试重跑通过：接受" || bad "测试对也没过" "$(printf '%s' "$o" | tail -2)"

echo "== ⑫ §6.936 进图后可查：::ingest 学习记录 → ::whyfor 打出理由/证据 =="
o=$(run '::ingest _t/learn/graph.triples
::whyfor 学习:测试对的题')
printf '%s' "$o" | grep -qa '\[理由\]' && ok "进图后能查理由" || bad "查不到理由" "$(printf '%s' "$o" | tail -3)"
printf '%s' "$o" | grep -qa '\[证据\]' && ok "进图后能查证据" || bad "查不到证据" "$(printf '%s' "$o" | tail -3)"
printf '%s' "$o" | grep -qa '\[来源\].*学来的' && ok "进图后能查来源（学来的）" || bad "查不到来源" "$(printf '%s' "$o" | tail -3)"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL learn（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS learn（$pass 过 / 0 红）"
