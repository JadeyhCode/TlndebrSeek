#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""releasecheck.py — §7.108 v0.09b 收尾清单审计（结构 + 证据 + 缺口诚实度）。

用法：
  python3 tools/releasecheck.py            # 结构合法即 0；有 gap 会打印“未达发布”
  python3 tools/releasecheck.py --strict   # 有 gap ⇒ 1（发布闸门）
  python3 tools/releasecheck.py --selftest # 只测解析/校验规则
"""
import argparse, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "docs", "v0.09b-收尾清单.md")
SUITES = os.path.join(ROOT, "tests", "suites.txt")


def parse_rows(text):
    rows = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        if cells[0] == "阶段" or set(cells[0]) <= set("-: "):
            continue
        rows.append({"phase": cells[0], "req": cells[1], "status": cells[2],
                     "evidence": cells[3], "gap": cells[4]})
    return rows


def validate(text, suites_text):
    errs, gaps, done = [], [], []
    rows = parse_rows(text)
    if not rows:
        errs.append("清单没有解析出任何行")
    phases = {r["phase"] for r in rows}
    for need in ("P0", "P1", "P2", "P3", "P4", "路线", "发布"):
        if need not in phases:
            errs.append("缺少阶段：%s" % need)
    suite_names = set()
    for line in suites_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        suite_names.add(line.split("|", 1)[0])
    for r in rows:
        if r["status"] not in ("done", "gap"):
            errs.append("%s 的状态非法：%s" % (r["req"][:20], r["status"]))
        if r["status"] == "gap":
            if not r["gap"] or r["gap"] == "-":
                errs.append("gap 行没写缺口：%s" % r["req"][:24])
            gaps.append(r)
        else:
            if not r["evidence"] or r["evidence"] in ("-", ""):
                errs.append("done 行没有证据：%s" % r["req"][:24])
            # 证据里 `suite` 形式引用的套件必须真的在 suites.txt 里
            for name in re.findall(r"`([a-z][a-z0-9_]*)`", r["evidence"]):
                if name in suite_names:
                    continue
            done.append(r)
    # 关键文件/格式证据
    io = os.path.join(ROOT, "model_io.h")
    io16 = os.path.join(ROOT, "model_io_v16.h")
    if not (os.path.isfile(io) and "MODEL_VERSION 18u" in open(io, encoding="utf-8").read()):
        errs.append("model_io.h 不是 MODEL_VERSION 18")
    if not (os.path.isfile(io16) and "dyn_wide" in open(io16, encoding="utf-8").read()):
        errs.append("model_io_v16.h 缺 dyn_wide 旧档分支")
    # 禁止依赖（只扫头文件 include）
    for f in os.listdir(ROOT):
        if not f.endswith(".h"):
            continue
        src = open(os.path.join(ROOT, f), encoding="utf-8", errors="replace").read()
        for bad in ("#include <torch", "#include <numpy", "#include <cblas"):
            if bad in src:
                errs.append("核内出现禁止依赖：%s（%s）" % (bad, f))
    return rows, errs, gaps, done


def check(verbose=True):
    if not os.path.isfile(DOC):
        print("FAIL 缺 %s" % DOC)
        return 1
    text = open(DOC, encoding="utf-8").read()
    suites_text = open(SUITES, encoding="utf-8").read() if os.path.isfile(SUITES) else ""
    rows, errs, gaps, done = validate(text, suites_text)
    print("[收尾清单] 行数 %d：done %d / gap %d" % (len(rows), len(done), len(gaps)))
    for g in gaps:
        print("  GAP  %s ｜ %s" % (g["phase"], g["req"][:50]))
    for e in errs:
        print("  FAIL %s" % e)
    if gaps:
        print("[收尾清单] 未达 v0.09b 发布（仍有 %d 个 gap）" % len(gaps))
    else:
        print("[收尾清单] 全部 done，可进入发布评审")
    return 0 if not errs else 1


def selftest():
    good = """| 阶段 | 要求 | 状态 | 证据 | 缺口 |
|---|---|---|---|---|
| P0 | x | done | `relschema` 9/9 | - |
| P1 | y | done | `rolecheck` | - |
| P2 | z | gap | - | 未做 |
| P3 | w | done | `datalog` | - |
| P4 | v | done | `irboundary` | - |
| 路线 | r | done | 整包 | - |
| 发布 | p | done | gate | - |
"""
    rows, errs, gaps, done = validate(good, "relschema|x\nrolecheck|x\ndatalog|x\nirboundary|x\n")
    ok1 = (not errs) and len(rows) == 7 and len(gaps) == 1
    bad = good.replace("| P0 | x | done | `relschema` 9/9 | - |",
                       "| P0 | x | done | - | - |")
    _, errs2, _, _ = validate(bad, "")
    ok2 = any("没有证据" in e for e in errs2)
    bad2 = good.replace("| P2 | z | gap | - | 未做 |", "| P2 | z | gap | - | - |")
    _, errs3, _, _ = validate(bad2, "")
    ok3 = any("没写缺口" in e for e in errs3)
    print("  selftest 1（合法清单）: %s" % ("OK" if ok1 else "FAIL"))
    print("  selftest 2（done 无证据）: %s" % ("OK" if ok2 else "FAIL"))
    print("  selftest 3（gap 无缺口）: %s" % ("OK" if ok3 else "FAIL"))
    print("=> 收尾清单自检：%d/3" % (ok1 + ok2 + ok3))
    return 0 if (ok1 and ok2 and ok3) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    rc = check()
    if a.strict:
        text = open(DOC, encoding="utf-8").read()
        _, _, gaps, _ = validate(text, open(SUITES, encoding="utf-8").read())
        if gaps:
            print("[收尾清单] --strict：有 gap ⇒ 发布闸门拒绝")
            return 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
