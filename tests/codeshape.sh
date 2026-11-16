#!/bin/sh
# tests/codeshape.sh — 合成器的**结构性行为**钉成回归（§6.881/§6.882）
#
# 这些行为以前只在盲测集里被间接覆盖；盲测集会随轮次变化，所以把"为什么这么拼"钉在这里：
#   ① 括号里是解释：`输出交替和（第一个减第二个…）` 不许把索引算子拼进链；
#   ② 括号里的词也得能用：`（凯撒加密）` 这种"词只在括号里"的题要能答；
#   ③ 链的形状连通：数组输出 → 标量输入算子必须剔除（`反转 → 数组和` 而不是 `反转 → 加一`）；
#   ④ 中文数字参数：`第三个` 要读出 3（模式参数、长关键词门限）；
#   ⑤ 去重变体不许叠三重：`去重后求和` = 去重 → 数组和；`排序后去重` = 排序 → 去重；
#   ⑥ 归约/计数同族：`去重后个数乘二` = 去重 → 计数 → 乘二；`奇数之和` 走数组奇数和；
#   ⑦ 回退路：`两个整数的和` 仍能走配方（链编不过时不许堵死回退）。
#
# 判据全部是**行为**（喂 stdin 比输出）+ **链名**（note 里必须出现/不许出现的算子）。
# 用法：sh tests/codeshape.sh
set -u
ROOT=$(cd "$(dirname "$0")/.." && pwd)
WORK="$ROOT/_t/codeshape"
rm -rf "$WORK"; mkdir -p "$WORK/_t/work"
cd "$WORK"
cp "$ROOT/build_aip" . || { echo "FAIL: 缺 build_aip"; exit 1; }
cp "$ROOT/model.bin" m.bin || { echo "FAIL: 缺 model.bin"; exit 1; }
K="$ROOT/code/knowledge"

pass=0; fail=0
ok() { printf '  [OK]   %s\n' "$1"; pass=$((pass + 1)); }
bad() { printf '  [FAIL] %s\n        证据: %s\n' "$1" "${2:-}"; fail=$((fail + 1)); }

# 现场造一份"够合成用"的模型（不带 13 MB 的 capi：合成器用不到它）
{
    for f in c2 generalized searched prim plan opclass rewrite skeletons compose; do
        [ -s "$K/$f.triples" ] && printf '::ingest %s/%s.triples\n' "$K" "$f"
    done
    printf '::save %s/model.bin\n::quit\n' "$WORK"
} > build.in
./build_aip --model m.bin < build.in > build.log 2>&1
[ -s model.bin ] || { echo "FAIL: 模型没造出来"; tail -5 build.log; exit 1; }

note_of() { grep -a '\[合成\]' "$1" | tail -1; }

# synth <描述> <日志>：清掉旧 .c，跑一次合成，回最新 .c 路径
synth() {
    rm -f _t/work/synth_*.c _t/work/synth_*.out
    printf '::act on\n::code synth %s\n::quit\n' "$1" | ./build_aip --model model.bin > "$2" 2>&1
    ls -t _t/work/synth_*.c 2>/dev/null | head -1
}
run_in() {   # <源文件> <stdin>：编 + 跑，打印任务输出（去掉骨架自测行）
    b="${1%.c}"
    gcc -std=c11 -O1 -w -o "$b" "$1" -lm 2>/dev/null || { echo "__COMPILE_FAIL__"; return; }
    printf '%s' "$2" | "$b" 2>&1 | grep -av '^\(ok\|FAIL\)' | tr -d '\n'
}

echo "== ① 括号里是解释（交替和）=="
C=$(synth '写一个程序：读入一行整数（标准输入），输出交替和（第一个减第二个加第三个……）。' s1.log)
if [ -n "$C" ] && [ "$(run_in "$C" '1 2 3
')" = "2" ]; then ok "交替和 = 2（索引算子没被括号里的『第一个』骗进链）"
else bad "交替和输出不对" "$(note_of s1.log)"; fi
note_of s1.log | grep -qa '概念_第' && bad "链里还是混进了索引算子" "$(note_of s1.log)" || ok "链里没有索引算子（括号命中已降级）"

echo "== ② 词只在括号里也要能用（凯撒）=="
C=$(synth '写一个程序：把字符串里的字母往后移 3 位（凯撒加密）。' s2.log)
if [ -n "$C" ] && [ "$(run_in "$C" 'abc
')" = "def" ]; then ok "凯撒加密：abc → def（括号里的关键词被采用）"
else bad "凯撒加密答不出/答错" "$(note_of s2.log)"; fi

echo "== ③ 链的形状连通：数组输出 → 标量输入必须剔除 =="
C=$(synth '读入一行整数（标准输入），反转后输出总和。' s3.log)
if [ -n "$C" ] && [ "$(run_in "$C" '1 2 3
')" = "6" ]; then ok "反转后总和 = 6"
else bad "反转后总和不对" "$(note_of s3.log)"; fi
note_of s3.log | grep -qa '数组翻转' && note_of s3.log | grep -qa '数组和' && ok "链是 数组翻转 → 数组和（形状连上了）" || bad "链的形状不对" "$(note_of s3.log)"

echo "== ④ 中文数字参数（第三个）=="
C=$(synth '读入一行整数（标准输入），从小到大排序后输出第三个数。' s4.log)
if [ -n "$C" ] && [ "$(run_in "$C" '3 1 2
')" = "3" ]; then ok "排序后第三个数 = 3"
else bad "第三个没读成 3" "$(note_of s4.log)"; fi

echo "== ⑤ 去重变体：不许叠三重；排序后去重 = 排序 → 去重 =="
C=$(synth '读入一行整数（标准输入），去重后输出它们的和。' s5.log)
if [ -n "$C" ] && [ "$(run_in "$C" '1 1 2
')" = "3" ]; then ok "去重后求和 = 3（一趟去重 + 求和）"
else bad "去重后求和不对" "$(note_of s5.log)"; fi
C=$(synth '读入一行整数（标准输入），从小到大排序后去掉重复的数输出。' s5b.log)
if [ -n "$C" ] && [ "$(run_in "$C" '3 1 3 2
')" = "1 2 3" ]; then ok "排序后去重输出 = 1 2 3（排序 → 去重，不是三连去重）"
else bad "排序后去重输出不对" "$(note_of s5b.log)"; fi

echo "== ⑥ 归约/计数同族 =="
C=$(synth '读入一行整数（标准输入），去重后输出不同数的个数再乘二。' s6.log)
if [ -n "$C" ] && [ "$(run_in "$C" '1 1 2
')" = "4" ]; then ok "去重后个数乘二 = 4（去重 → 计数 → 乘二）"
else bad "去重后个数乘二不对" "$(note_of s6.log)"; fi
C=$(synth '读入一行整数（标准输入），输出其中奇数的和。' s6b.log)
if [ -n "$C" ] && [ "$(run_in "$C" '1 2 3
')" = "4" ]; then ok "奇数之和 = 4（走数组奇数和，不是 1..N 求和）"
else bad "奇数之和不对" "$(note_of s6b.log)"; fi

echo "== ⑥b 字符串链 / 切片 / 条件变换（§6.884）=="
C=$(synth '写一个程序：把读入的字符串反转后转成大写输出。' s6c.log)
if [ -n "$C" ] && [ "$(run_in "$C" 'abc
')" = "CBA" ]; then ok "字符串反转 → 转大写 = CBA（同位置按类别消歧）"
else bad "字符串反转链不对" "$(note_of s6c.log)"; fi
C=$(synth '读入一行整数（标准输入），反转之后输出前三个数。' s6d.log)
if [ -n "$C" ] && [ "$(run_in "$C" '1 2 3 4
')" = "4 3 2" ]; then ok "反转后前三个 = 4 3 2（前N个切片）"
else bad "反转后前三个不对" "$(note_of s6d.log)"; fi
C=$(synth '读入一行整数（标准输入），把负数都变成 0 之后输出总和。' s6e.log)
if [ -n "$C" ] && [ "$(run_in "$C" '-2 3 -1 5
')" = "8" ]; then ok "负数清零后求和 = 8（条件变换）"
else bad "负数清零后求和不对" "$(note_of s6e.log)"; fi
C=$(synth '写一个程序：读入一个整数（命令行参数），输出它反转后再加一。' s6f.log)
if [ -n "$C" ] && note_of s6f.log | grep -qa '反转 → 加一'; then ok "整数反转后加一仍走标量支（未点名形状时默认标量）"
else bad "标量反转被非标量支抢走" "$(note_of s6f.log)"; fi

C=$(synth '读入一行整数（标准输入），反转之后输出前两个数。' s6g.log)
if [ -n "$C" ] && [ "$(run_in "$C" '1 2 3 4
')" = "4 3" ]; then ok "反转后前两个 = 4 3（『两』也算 2）"
else bad "反转后前两个不对" "$(note_of s6g.log)"; fi
C=$(synth '读入一行整数（标准输入），输出前三个数的和。' s6h.log)
if [ -n "$C" ] && [ "$(run_in "$C" '1 2 3 4
')" = "6" ]; then ok "前三个数的和 = 6（切片 → 归约同族）"
else bad "前三个数的和不对" "$(note_of s6h.log)"; fi

C=$(synth '写一个程序：把读入的字符串转成大写后输出长度再乘二。' s6i.log)
if [ -n "$C" ] && [ "$(run_in "$C" 'abcd
')" = "8" ]; then ok "大写后长度乘二 = 8（字符串链 → 标量参数乘）"
else bad "大写后长度乘二不对" "$(note_of s6i.log)"; fi
C=$(synth '读入一行整数（标准输入），输出其中奇数的个数再乘三。' s6j.log)
if [ -n "$C" ] && [ "$(run_in "$C" '1 2 3
')" = "6" ]; then ok "奇数个数乘三 = 6（归约 → 标量参数乘）"
else bad "奇数个数乘三不对" "$(note_of s6j.log)"; fi

C=$(synth '读入一行整数（标准输入），输出前四个数里最大的。' s6k.log)
if [ -n "$C" ] && [ "$(run_in "$C" '1 5 3 2
')" = "5" ]; then ok "前四个数里最大 = 5（模式分支 5 个都要展开）"
else bad "前四个数里最大不对" "$(note_of s6k.log)"; fi
C=$(synth '读入一行整数（标准输入），每个数乘 2 之后输出前三个数。' s6l.log)
if [ -n "$C" ] && [ "$(run_in "$C" '1 2 3 4 5
')" = "2 4 6" ]; then ok "乘2后前三个 = 2 4 6（模式参数不被前面的数字抢走）"
else bad "乘2后前三个不对" "$(note_of s6l.log)"; fi
C=$(synth '读入一行整数（标准输入），把负数变成 0 之后输出正数的个数。' s6m.log)
if [ -n "$C" ] && [ "$(run_in "$C" '-1 2 3
')" = "2" ]; then ok "负数清零后正数个数 = 2（条件计数同族）"
else bad "正数个数不对" "$(note_of s6m.log)"; fi

C=$(synth '写一个程序：统计读入一行字符串里的单词个数再乘二。' s6n.log)
if [ -n "$C" ] && [ "$(run_in "$C" 'a bb c
')" = "6" ]; then ok "单词个数乘二 = 6（计数算子能进链）"
else bad "单词个数乘二不对" "$(note_of s6n.log)"; fi
C=$(synth '写一个程序：输出读入一行字符串里最长单词的长度再加一。' s6o.log)
if [ -n "$C" ] && [ "$(run_in "$C" 'abcXYZ
')" = "7" ]; then ok "最长单词加一 = 7（换行算分隔符）"
else bad "最长单词加一不对" "$(note_of s6o.log)"; fi
C=$(synth '读入一行整数（标准输入），输出最大值减最小值再加一。' s6p.log)
if [ -n "$C" ] && [ "$(run_in "$C" '4 1 9
')" = "9" ]; then ok "最大值减最小值加一 = 9（极差进链）"
else bad "最大值减最小值加一不对" "$(note_of s6p.log)"; fi

echo "== ⑥c 矩阵族（§6.891）=="
C=$(synth '读入一个矩阵（标准输入），输出所有元素的和。' s6q.log)
if [ -n "$C" ] && [ "$(run_in "$C" '2 3
1 2 3
4 5 6
')" = "21" ]; then ok "矩阵元素和 = 21（标量产出）"
else bad "矩阵元素和不对" "$(note_of s6q.log)"; fi
C=$(synth '读入一个矩阵（标准输入），输出每一行的和。' s6r.log)
if [ -n "$C" ] && [ "$(run_in "$C" '2 3
1 2 3
4 5 6
')" = "6 15" ]; then ok "矩阵行和 = 6 15（数组产出有打印契约）"
else bad "矩阵行和不对" "$(note_of s6r.log)"; fi
C=$(synth '读入一个矩阵（标准输入），输出每一列中最大的数。' s6s.log)
if [ -n "$C" ] && [ "$(run_in "$C" '2 3
1 2 3
4 5 6
')" = "4 5 6" ]; then ok "矩阵列最大 = 4 5 6（长关键词盖住『最大的数』）"
else bad "矩阵列最大不对" "$(note_of s6s.log)"; fi

C=$(synth '读入一个矩阵（标准输入），输出每一行的和再加一。' s6t.log)
if [ -n "$C" ] && [ "$(run_in "$C" '2 3
1 2 3
4 5 6
')" = "7 16" ]; then ok "矩阵行和再加一 = 7 16（数组产出 → 标量算子逐元素提升）"
else bad "矩阵行和再加一不对" "$(note_of s6t.log)"; fi
C=$(synth '读入一个矩阵（标准输入），输出矩阵中最大的数再减二。' s6u.log)
if [ -n "$C" ] && [ "$(run_in "$C" '2 3
1 2 3
4 5 6
')" = "4" ]; then ok "矩阵最大减二 = 4（标量参数化减）"
else bad "矩阵最大减二不对" "$(note_of s6u.log)"; fi

C=$(synth '读入一行整数（标准输入），反转之后每个数加一输出。' s6v.log)
if [ -n "$C" ] && [ "$(run_in "$C" '1 2 3
')" = "4 3 2" ]; then ok "反转后每个数加一 = 4 3 2（数组变换算子有输出契约）"
else bad "反转后每个数加一不对" "$(note_of s6v.log)"; fi

echo "== ⑦ 回退路：链编不过时任务/配方仍可达 =="
C=$(synth '读入两个整数（命令行参数），输出它们的和。' s7.log)
if [ -n "$C" ] && note_of s7.log | grep -qa '合成\|配方\|任务'; then ok "两个整数的和仍能合成（回退没被堵死）"
else bad "回退路被堵死" "$(note_of s7.log)"; fi
if [ -n "$C" ] && gcc -std=c11 -O1 -w -o /dev/null "$C" -lm 2>/dev/null; then ok "回退产物能编过"
else bad "回退产物编不过" "$(note_of s7.log)"; fi

echo
printf 'codeshape：通过 %d / 失败 %d\n' "$pass" "$fail"
[ "$fail" -eq 0 ] && printf 'PASS codeshape（括号语义 / 形状连通 / 中文数字参数 / 去重变体 / 归约计数 / 回退路）\n' || printf 'FAIL codeshape\n'
[ "$fail" -eq 0 ]
