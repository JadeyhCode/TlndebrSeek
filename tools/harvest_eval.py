#!/usr/bin/env python3
"""§6.957 扩图 S3 首跑：事实去重率 + 抽检有效率。

用法：harvest_eval.py <facts.triples...>
输出：总条数 / 精确重复率 / 归一化重复率（空白折叠）/ 1% 抽检有效率 / 主谓宾字段数分布。
抽检确定性：每 100 行取第 1 行（可复现），不随机。
"""
import sys, os

def norm(s):
    return " ".join(s.split())

def records(path):
    """按“行尾 \\ 续行”把逻辑记录拼起来（片段代码是跨行的）。"""
    buf = ""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.endswith("\\"):
                buf += line[:-1] + "\n"
                continue
            buf += line
            if buf.strip():
                yield buf
            buf = ""
    if buf.strip():
        yield buf

def main(paths):
    total = 0
    exact = set()
    normed = set()
    bad = 0
    sampled = 0
    nsamp_bad = 0
    field_hist = {}
    for p in paths:
        if not os.path.isfile(p):
            print("缺文件:", p); continue
        if True:
            for i, line in enumerate(records(p)):
                if not line.strip():
                    continue
                total += 1
                exact.add(line)
                cols = line.split("\t")
                nf = len(cols)
                field_hist[nf] = field_hist.get(nf, 0) + 1
                if nf >= 3:
                    normed.add((norm(cols[0]), norm(cols[1]), "\t".join(norm(c) for c in cols[2:])))
                else:
                    bad += 1
                if i % 100 == 0:
                    sampled += 1
                    ok = nf >= 3 and all(norm(c) for c in cols[:3]) and len(line) <= 4096
                    if not ok:
                        nsamp_bad += 1
    if total == 0:
        print("空输入"); return 1
    print("总条数         %d" % total)
    print("精确重复率     %.2f%%（唯一 %d）" % (100.0 * (total - len(exact)) / total, len(exact)))
    print("归一重复率     %.2f%%（唯一 %d）" % (100.0 * (total - len(normed)) / total, len(normed)))
    print("字段数分布     %s" % dict(sorted(field_hist.items())))
    print("1%% 抽检        %d 条，合格 %d，不合格 %d（有效率 %.2f%%）"
          % (sampled, sampled - nsamp_bad, nsamp_bad,
             100.0 * (sampled - nsamp_bad) / sampled if sampled else 0.0))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
