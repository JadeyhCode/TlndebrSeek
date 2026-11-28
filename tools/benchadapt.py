#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""benchadapt.py — §7.116 P4 外部评测适配：GSM8K 官方 test 确定性子集 20 题。

诚实口径：
- 题目来自官方 test.jsonl 的确定性抽样（每 65 题取 1），未看题挑题；
- 逐题跑真实二进制，按“期望整数是否出现”判 pass；明确拒绝算 refuse；其余 wrong；
- 同时跑 adapter_en_math=0 消融，报告 pass 变化；
- 污染检查：问题逐字检索 + 5-gram 命中（排除数据文件自身），命中文件如实列出。
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
DATA = os.path.join(ROOT, "tests", "data", "gsm8k_test20.jsonl")
README = os.path.join(ROOT, "tests", "data", "README.md")
W = os.path.join(ROOT, "_t", "benchadapt")
REFUSE = ("can't solve this word problem", "won't guess", "don't know", "do not know",
          "no [syn]", "not in my graph", "不知道", "不 知道")


def items():
    out = []
    for line in open(DATA, encoding="utf-8"):
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def answer_of(r):
    m = re.search(r"####\s*(-?[\d,]+)", r.get("answer", ""))
    return int(m.group(1).replace(",", "")) if m else None


def fresh():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt",
              "policy.txt", "relations_beh.txt", "dims.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))


def ask(q):
    p = subprocess.run([BIN, "--model", "model.bin"], input=(q + "\n::quit\n").encode(),
                       capture_output=True, cwd=W, timeout=120)
    out = (p.stdout + p.stderr).decode("utf-8", "replace")
    for l in out.splitlines():
        if "AI > " in l:
            return l.split("AI > ", 1)[1]
    return ""


def grade(ans, want):
    if want is None:
        return "wrong"
    if re.search(r"(?<![\d])%d(?![\d])" % want, ans.replace(",", "")):
        return "pass"
    low = ans.lower()
    if any(r in low for r in REFUSE):
        return "refuse"
    return "wrong"


def set_math(off):
    pol = open(os.path.join(ROOT, "policy.txt"), encoding="utf-8").read()
    lines = [l for l in pol.splitlines() if not l.startswith("adapter_en_math=")]
    lines.append("adapter_en_math=%d" % (0 if off else 1))
    open(os.path.join(W, "policy.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def contamination(qs):
    exact = 0; hit_files = set()
    exts = (".h", ".c", ".md", ".txt", ".py", ".sh", ".jsonl")
    skip = {os.path.abspath(DATA)}
    for base, dirs, files in os.walk(ROOT):
        if ".git" in base or "_t" in base.split(os.sep):
            continue
        for fn in files:
            if not fn.endswith(exts):
                continue
            fp = os.path.join(base, fn)
            if os.path.abspath(fp) in skip:
                continue
            try:
                if os.path.getsize(fp) > 2_000_000:
                    continue
                txt = open(fp, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            norm = re.sub(r"\s+", " ", txt.lower())
            for q in qs:
                if q in norm:
                    exact += 1
                    hit_files.add(os.path.relpath(fp, ROOT))
    # 5-gram 抽样：每题的归一化前 5 词，在 patterns/relations/docs/tools 里查
    scope = []
    for rel in ("patterns.txt", "relations.txt", "docs", "tools"):
        p = os.path.join(ROOT, rel)
        if os.path.isdir(p):
            for base, _, files in os.walk(p):
                scope.extend(os.path.join(base, f) for f in files
                             if f.endswith((".md", ".txt", ".py", ".h", ".c")))
        elif os.path.isfile(p):
            scope.append(p)
    blob = ""
    for fp in scope:
        try:
            if os.path.getsize(fp) < 2_000_000:
                blob += " " + open(fp, encoding="utf-8", errors="replace").read().lower()
        except OSError:
            pass
    blob = re.sub(r"\s+", " ", blob)
    gram = 0
    for q in qs:
        words = q.split()
        if len(words) >= 5 and " ".join(words[:5]) in blob:
            gram += 1
    return exact, sorted(hit_files), gram


def run_batch(qs, wants, tag):
    res = []
    for i, (q, want) in enumerate(zip(qs, wants), 1):
        ans = ask(q)
        res.append((i, want, ans, grade(ans, want)))
    npass = sum(1 for r in res if r[3] == "pass")
    nref = sum(1 for r in res if r[3] == "refuse")
    nwrong = sum(1 for r in res if r[3] == "wrong")
    print("[benchadapt] %s：pass %d / refuse %d / wrong %d（共 %d）" %
          (tag, npass, nref, nwrong, len(res)))
    return res, npass, nref, nwrong


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-ablate", action="store_true")
    a = ap.parse_args()
    its = items()
    qs = [re.sub(r"\s+", " ", it["question"].lower()).strip() for it in its]
    wants = [answer_of(it) for it in its]
    fresh()
    set_math(False)
    res, npass, nref, nwrong = run_batch(qs, wants, "GSM8K 官方 test 子集 20 题（确定性抽样）")
    tsv = os.path.join(ROOT, "_t", "benchadapt_gsm8k.tsv")
    with open(tsv, "w", encoding="utf-8") as f:
        for i, want, ans, verdict in res:
            f.write("%d\t%s\t%s\t%s\n" % (i, want, verdict, ans.replace("\t", " ")))
    print("[benchadapt] TSV：%s" % os.path.relpath(tsv, ROOT))
    if not a.no_ablate:
        set_math(True)
        _, apass, _, _ = run_batch(qs, wants, "消融 adapter_en_math=0")
        print("[benchadapt] 消融变化：pass %d → %d（应不增）" % (npass, apass))
        set_math(False)
    exact, hit_files, gram = contamination(qs)
    print("[benchadapt] 污染：问题逐字命中 %d 题 %s；5-gram 命中 %d 题（检查范围 patterns/relations/docs/tools）" %
          (exact, ("(" + ",".join(hit_files) + ")") if hit_files else "", gram))
    print("[benchadapt] 注意：这是**官方题库子集**读数；pass 低是如实结果，不调题、不改判分。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
