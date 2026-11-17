#!/bin/sh
# tests/tool.sh — **外部工具**（本地大模型）：问得到、标出处、不进图、失败不装懂
#
# 为什么要有这一套：`::tool` 会往网络发请求，最容易出三类错 ——
#   ① 默默把工具的话当成自己的知识（污染）；
#   ② 请求体发错（curl 的 `--data-binary` 要 `@文件`，漏了会把**路径**当 JSON 发出去，
#      服务端只回 "parse error at line 1, column 1"，本地看不出问题）；
#   ③ 失败时编一句话糊过去。
# 这三条都是可判定的，所以钉死：用 `tools/fake_openai.py` 起一个假端点，不联网。
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
BIN=${BIN:-./build_aip}
MODEL=${1:-model.bin}
[ -x "$BIN" ] || { echo "FAIL: 缺可执行文件 $BIN"; exit 1; }
[ -f "$MODEL" ] || { echo "FAIL: 缺模型 $MODEL"; exit 1; }

W="$ROOT/_t/tool"; rm -rf "$W"; mkdir -p "$W"
cp "$BIN" "$W/build_aip"; cp "$MODEL" "$W/model.bin"
# 端口让**内核分配**（--port 0）：写死端口在并行跑时会撞上别的进程（实测撞到一个
# 要 API Key 的本地服务，答复 401，4 项判据全红）。
python3 "$ROOT/tools/fake_openai.py" --port 0 --reply "假端点的答复：北京" \
    --dump "$W/body.json" > "$W/server.log" 2>&1 &
SRV=$!
trap 'kill '"$SRV"' 2>/dev/null' EXIT
PORT=""
i=0
while [ "$i" -lt 50 ]; do
    # 取第一行里的数字（`sed 's/[^0-9]//gp'` 在"整行都是数字"时不会触发替换 ⇒ 拿不到，踩过）
    PORT=$(head -1 "$W/server.log" 2>/dev/null | tr -cd '0-9')
    [ -n "$PORT" ] && break
    i=$((i + 1)); sleep 0.1
done
[ -n "$PORT" ] || { echo "FAIL: 假端点没起来"; exit 1; }

run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }

echo "== ① 默认关：没开就问，必须拒绝 =="
o=$(run '::tool ask 你好')
printf '%s' "$o" | grep -q '工具没打开' && ok "默认关：拒绝（工具没打开）" || bad "默认关没拒" "$(printf '%s' "$o" | grep -a '外部工具' | head -2)"

echo "== ② 配上 + 打开：问得到，且**标出处** =="
o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::tool ask 你好")
printf '%s' "$o" | grep -q '假端点的答复' && ok "答复回来了" || bad "没拿到答复" "$(printf '%s' "$o" | grep -a '外部工具' | tail -2)"
printf '%s' "$o" | grep -q '不是我的知识' && ok "标了「不是我的知识」" || bad "没标出处" "$(printf '%s' "$o" | tail -3)"

echo "== ③ 请求体是 JSON（查 curl 的 @文件 那个坑）=="
if [ -s "$W/body.json" ]; then
    head -c 1 "$W/body.json" | grep -q '{' && ok "请求体以 { 开头（是 JSON）" || bad "请求体不是 JSON" "$(head -c 80 "$W/body.json")"
else
    bad "没有请求体落盘" "body.json 不存在"
fi

echo "== ④ 账：tool.log 有一行 ok =="
[ -f "$W/tool.log" ] && grep -q 'ok' "$W/tool.log" && ok "账里记了 ok" || bad "账里没记" "$(cat "$W/tool.log" 2>/dev/null | head -2)"

echo "== ⑤ 不进图：答复内容不能变成知识 =="
o=$(run '::rel 假端点的答复：北京')
printf '%s' "$o" | grep -q '不在图里' && ok "答复没进图" || bad "答复进图了" "$(printf '%s' "$o" | head -3)"

echo "== ⑥ 失败照实说（指向死端口）=="
o=$(run '::tool set http://127.0.0.1:1/v1 k m\n::tool on\n::tool ask 你好')
printf '%s' "$o" | grep -q '没答上来' && ok "失败照实说（没答上来）" || bad "失败时不说实话" "$(printf '%s' "$o" | tail -2)"
printf '%s' "$o" | grep -q '假端点的答复' && bad "失败却给了答复（编的）" "$(printf '%s' "$o" | tail -2)" || ok "失败时不编答案"

echo "== ⑦ §6.914 系统提示词：请求体里必须是 system+user，且带行动建议口径 =="
o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::tool ask 我该怎么做")
[ -s "$W/body.json" ] || bad "没有请求体" "body.json 缺"
grep -q '"role":"system"' "$W/body.json" && ok "请求体含 system 角色" || bad "请求体没有 system" "$(head -c 160 "$W/body.json")"
grep -q '直接给可执行的行动建议' "$W/body.json" && ok "系统提示词要求行动建议" || bad "系统提示词缺行动建议" "$(head -c 160 "$W/body.json")"
grep -q '先检查他给的材料' "$W/body.json" && ok "系统提示词要求先检查再结论" || bad "系统提示词缺先检查" "$(head -c 160 "$W/body.json")"
grep -q '第 3' "$W/body.json" && bad "系统提示词串了别的规则" "" || ok "系统提示词是固定模板"

echo "== ⑧ 思考强度：low/medium/high → max_tokens 1024/4096/16384 =="
for lv in low medium high; do
    o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::tool think $lv\n::tool ask 你好")
    case "$lv" in low) want=1024;; medium) want=4096;; high) want=16384;; esac
    grep -q "\"max_tokens\":$want" "$W/body.json" && ok "$lv → max_tokens $want" || bad "$lv 的 max_tokens 不对" "$(grep -o '"max_tokens":[0-9]*' "$W/body.json" | head -1)"
done

echo "== ⑨ DeepSeek 默认端点：只填 provider/key 也能用（不联网，只看 status）=="
cat > "$W/tool.txt" <<'CFG'
on=0
provider=deepseek
key=test-key
thinking=high
CFG
o=$(run '::tool status')
printf '%s' "$o" | grep -q 'https://api.deepseek.com/v1' && ok "DeepSeek 默认端点自动补全" || bad "没补 DeepSeek 端点" "$(printf '%s' "$o" | grep -a '端点' | head -2)"
printf '%s' "$o" | grep -q 'deepseek-chat' && ok "DeepSeek 默认模型自动补全" || bad "没补 DeepSeek 模型" "$(printf '%s' "$o" | grep -a '模型' | head -2)"
printf '%s' "$o" | grep -q 'max_tokens=16384' && ok "thinking=high 被读进配置" || bad "thinking 没生效" "$(printf '%s' "$o" | grep -a '思考强度' | head -1)"

echo "== ⑩ system_file 覆盖：自定义提示词要原样进 system 消息 =="
printf '你是自定义顾问：只给三步行动计划。\n' > "$W/my_sys.txt"
cat > "$W/tool.txt" <<CFG
on=1
url=http://127.0.0.1:$PORT/v1
key=k
model=m
thinking=low
system_file=$W/my_sys.txt
CFG
o=$(run '::tool ask 怎么做')
grep -q '只给三步行动计划' "$W/body.json" && ok "system_file 覆盖生效" || bad "system_file 没生效" "$(head -c 200 "$W/body.json")"
grep -q '"max_tokens":1024' "$W/body.json" && ok "覆盖后思考强度仍生效" || bad "覆盖后 max_tokens 不对" "$(grep -o '"max_tokens":[0-9]*' "$W/body.json" | head -1)"

echo "== ⑪ §6.915 升级链路：先搜索（联网关着就照实说），再问大模型 =="
o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::tool escalate 我的 C 程序链接报错怎么做")
printf '%s' "$o" | grep -q '\[升级\] ① 搜索' && ok "升级第一步报告了搜索阶段" || bad "升级没报搜索阶段" "$(printf '%s' "$o" | head -3)"
printf '%s' "$o" | grep -q '联网关着' && ok "没开网时照实说没搜" || bad "没开网却装搜过" "$(printf '%s' "$o" | head -3)"
printf '%s' "$o" | grep -q '\[升级\] ② 问外部大模型' && ok "第二步确实去问了" || bad "没走第二步" "$(printf '%s' "$o" | tail -3)"
grep -q '用户问题' "$W/body.json" && ok "提问体里带了原问题" || bad "提问体没带原问题" "$(head -c 120 "$W/body.json")"
grep -q '搜索没成\|联网关着' "$W/body.json" && ok "提问体里如实写了搜索状态" || bad "提问体没写搜索状态" "$(head -c 200 "$W/body.json")"
grep -qa 'escalate\|升级' "$W/tool.log" && ok "账里记了升级" || bad "账里没记升级" "$(tail -2 "$W/tool.log")"

echo "== ⑫ 升级关着时不动网络：工具没开就明确拒绝 =="
o=$(run '::tool off')
o=$(run '::tool escalate 你好')
printf '%s' "$o" | grep -q '不能升级' && ok "工具关着：拒绝升级" || bad "工具关着还升级" "$(printf '%s' "$o" | head -2)"

echo "== ⑬ §6.916 自动升级：auto=1 时“不会”的题先搜索再问 =="
o=$(run "::tool set http://127.0.0.1:$PORT/v1 k m\n::tool on\n::tool auto on\n::tool status")
printf '%s' "$o" | grep -q '自动升级：开' && ok "status 显示自动升级开" || bad "status 没显示自动升级" "$(printf '%s' "$o" | grep -a 自动升级)"
o=$(run '::tool auto on
紫金葫芦的第三个铆钉为什么会唱歌')
printf '%s' "$o" | grep -q '\[升级\] 这题本地没有依据' && ok "不会时触发了自动升级" || bad "不会时没升级" "$(printf '%s' "$o" | tail -3)"
printf '%s' "$o" | grep -q '\[升级\] ① 搜索' && ok "自动升级先报搜索阶段" || bad "自动升级没报搜索" "$(printf '%s' "$o" | tail -3)"
printf '%s' "$o" | grep -q '假端点的答复' && ok "自动升级拿到了答案" || bad "自动升级没拿到答案" "$(printf '%s' "$o" | tail -3)"
grep -q '【升级】' "$W/body.json" && ok "自动升级的提问带【升级】前缀" || bad "自动升级提问没标记" "$(head -c 120 "$W/body.json")"

echo "== ⑭ auto=0（默认）时不会的题不往外走 =="
o=$(run '::tool auto off
紫金葫芦的第三个铆钉为什么会唱歌')
printf '%s' "$o" | grep -q '\[升级\]' && bad "auto=0 仍然升级了" "$(printf '%s' "$o" | head -3)" || ok "auto=0 不升级（只说不懂）"
printf '%s' "$o" | grep -q '假端点的答复' && bad "auto=0 却拿到外部答复" "" || ok "auto=0 没有外部答复"

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL tool（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS tool（$pass 过 / 0 红）"
