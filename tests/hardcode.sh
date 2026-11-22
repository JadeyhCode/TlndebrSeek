#!/bin/sh
# tests/hardcode.sh — 目标⑦红线：code.h 里的语义/策略表必须在 docs/硬编码登记.md 里
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"
REG="docs/硬编码登记.md"
[ -f "$REG" ] || { echo "FAIL: 缺 $REG"; exit 1; }
pass=0; fail=0
ok()  { echo "  [OK]   $1"; pass=$((pass + 1)); }
bad() { echo "  [FAIL] $1"; echo "         证据: $2"; fail=$((fail + 1)); }

echo "== ① code.h 的 static const char *X[] 表逐个查登记 =="
syms=$(grep -oE 'static const char \*[A-Za-z_][A-Za-z0-9_]*\[\] = \{' code.h | sed 's/.*const char \*//; s/\[\].*//' | sort -u) || true
n=0
for s in $syms; do
    n=$((n + 1))
    grep -qE "\`$s\`|\b$s\b" "$REG" && ok "$s 已登记" || bad "$s 没登记" "在 $REG 里加一行"
done
if [ "$n" -eq 0 ]; then ok "扫到 0 张表（都已下沉）"; else ok "扫到 $n 张表（不是空扫）"; fi

echo "== ② 登记表里每条都要写清“为什么/消融” =="
grep -q '为什么还在代码里' "$REG" && ok "登记表有“为什么”列" || bad "缺“为什么”列" ""
grep -q '消融测试' "$REG" && ok "登记表有“消融测试”列" || bad "缺“消融测试”列" ""

echo "== ③ policy.txt 的策略键必须登记（§6.998） =="
if [ -f policy.txt ]; then
    np=0
    for k in $(sed 's/#.*//' policy.txt | grep -oE '^[A-Za-z_][A-Za-z0-9_]*=' | tr -d '='); do
        np=$((np + 1))
        grep -q "\`$k\`" "$REG" && ok "策略 $k 已登记" || bad "策略 $k 没登记" "在 $REG 里加一行"
    done
    [ "$np" -gt 0 ] && ok "扫到 $np 个策略键（不是空扫）" || bad "policy.txt 里没有策略键" ""
else
    ok "没有 policy.txt（哨兵：策略全在环境变量里）"
fi

echo ""
if [ "$fail" -ne 0 ]; then echo "FAIL hardcode（$pass 过 / $fail 红）"; exit 1; fi
echo "PASS hardcode（$pass 过 / 0 红）"
