#!/bin/sh
# tests/sseg.sh — §6.965 滑动联想切分：候选/最优/次优/词义激活，全部只读图
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
[ -x build_aip ] || { echo "FAIL: 缺 build_aip"; exit 1; }
W="$ROOT/_t/sseg"; rm -rf "$W"; mkdir -p "$W/_t/work"
cp build_aip model.bin "$W/"
cat > "$W/fix.triples" <<'T'
号	联想	名号
号	联想	号角
名号	指向	张楚
号角	属于	乐器
张楚	属于	楚国
张楚	词性	名词
号	词性	名词
国号	指向	张楚
大张	联想	楚国
为	属于	虚词
张	属于	姓
楚	属于	国名
T
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }
run() { ( cd "$W" && printf '%b\n::quit\n' "$1" | ./build_aip --model model.bin 2>&1 ); }
o=$(run '::ingest fix.triples\n::sseg 号为张楚\n::sseg 大张楚国')
printf '%s' "$o" | grep -qa '最优.*号/为/张楚' && ok "最优：号/为/张楚（词优先）" || bad "最优不对" "$(printf '%s' "$o" | grep -a '最优')"
printf '%s' "$o" | grep -qa '候选2.*号/为/张/楚' && ok "候选2：号/为/张/楚（候选保留）" || bad "次优不对" "$(printf '%s' "$o" | grep -a '候选2')"
printf '%s' "$o" | grep -qa '名号（与上下文相连·激活）' && ok "名号被上下文激活" || bad "名号没激活" "$(printf '%s' "$o" | grep -a '语义.*号')"
printf '%s' "$o" | grep -qa '号角（仅联想）' && ok "号角仅作联想" || bad "号角状态不对" "$(printf '%s' "$o" | grep -a '语义.*号')"
printf '%s' "$o" | grep -qa '最优.*大张/楚国' && ok "大张楚国：大张/楚国" || bad "大张楚国最优不对" "$(printf '%s' "$o" | grep -a '最优')"
printf '%s' "$o" | grep -qa '候选2.*大/张楚/国' && ok "另一读法保留：大/张楚/国" || bad "另一读法丢了" "$(printf '%s' "$o" | grep -a '候选2')"

printf '%s' "$o" | grep -qa '\[词性\] 张楚：名词' && ok "词性来自图边（张楚：名词）" || bad "词性没出" "$(printf '%s' "$o" | grep -a '词性')"

echo "== 消融：把词权重压低、单字权重抬到 2.0，最优应翻成字串（证明权重生效） =="
o2=$(cd "$W" && printf '::ingest fix.triples\n::sseg 号为张楚\n::quit\n' | AIP_SSEG_WORD=0.2 AIP_SSEG_CH=2.0 ./build_aip --model model.bin 2>&1)
printf '%s' "$o2" | grep -qa '最优.*号/为/张/楚' && ok "消融后翻成字串" || bad "消融没生效" "$(printf '%s' "$o2" | grep -a '最优')"
o3=$(run '::seg sliding\n::seg greedy')
printf '%s' "$o3" | grep -qa '分词 = 滑动联想' && ok "::seg sliding 打开" || bad "::seg sliding 没生效" ""
printf '%s' "$o3" | grep -qa '分词 = 最长匹配' && ok "::seg greedy 关掉" || bad "::seg greedy 没生效" ""

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL sseg（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS sseg（$pass 过 / 0 红）"
