#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""train_eval.py — §7.056 reproducible train→eval pipeline with contamination/noise checks (F19).

Steps: fresh sandbox → `::ingest corpus.tsv` (10 novel facts + 1 bad line + 1 comment) →
ask 10 blind questions → score. The blind questions are new combinations, never present
verbatim in the corpus; the pipeline refuses to run if any question text leaks into the corpus.

Readings: ingest (inserted/dup/bad/new), pass/refuse/wrong, contamination count.
"""
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "traineval")

CORPUS_LINES = [
    "佐格\t属于\t兽类",
    "兽类\t属于\t生物",
    "米拉\t属于\t人类",
    "人类\t属于\t生物",
    "佐格\t有\t鳞片",
    "米拉\t有\t长发",
    "佐格\t吃\t矿石",
    "米拉\t吃\t面包",
    "佐格\t在\t北境",
    "米拉\t在\t南城",
    "这一行没有制表符所以是坏行",
    "# 注释行：训练/评测流水线示例",
]
QUESTIONS = [
    ("佐格 属于 什么", "兽类"),
    ("米拉 属于 什么", "人类"),
    ("佐格 有 什么", "鳞片"),
    ("米拉 有 什么", "长发"),
    ("佐格 吃 什么", "矿石"),
    ("米拉 吃 什么", "面包"),
    ("佐格 在 哪里", "北境"),
    ("米拉 在 哪里", "南城"),
    ("佐格 属于 生物 吗", "对"),
    ("米拉 属于 生物 吗", "对"),
]
EXTRA_REFUSE = ("佐格 属于 人类 吗",)
REFUSE = ("不知道", "不 知道", "不 太 懂", "不太懂", "没 记 过", "没记过",
          "不 认识", "不认识", "不确定", "不 确定")


def run(inp):
    p = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                       capture_output=True, cwd=W, timeout=180)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def last_ans(out):
    a = [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]
    return a[-1] if a else ""


def main():
    shutil.rmtree(W, ignore_errors=True)
    os.makedirs(W, exist_ok=True)
    shutil.copy(BIN, os.path.join(W, "build_aip"))
    shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
    for f in ("patterns.txt", "frames.txt", "relations.txt", "policy.txt"):
        src = os.path.join(ROOT, f)
        if os.path.isfile(src):
            shutil.copy(src, os.path.join(W, f))
    corpus = "\n".join(CORPUS_LINES) + "\n"
    with open(os.path.join(W, "corpus.tsv"), "w", encoding="utf-8") as f:
        f.write(corpus)

    # contamination: no blind question may appear verbatim in the corpus
    leak = [q for q, _ in QUESTIONS if q in corpus]
    print("[contamination] 泄漏题目数：%d" % len(leak))
    if leak:
        print("  FAIL: 题目出现在训练语料里：%s" % leak[:3])
        return 1

    # ingest + questions must share one process (graph is in memory)
    qs_all = [q for q, _ in QUESTIONS] + list(EXTRA_REFUSE)
    inp = "::ingest corpus.tsv\n" + "\n".join(qs_all) + "\n::quit\n"
    out = run(inp)
    m = re.search(r"写进去 (\d+)", out)
    bad = re.search(r"坏行 (\d+)", out)
    print("[ingest] 写入 %s 条 / 坏行 %s（期望 10 / 1）" % (m.group(1) if m else "?", bad.group(1) if bad else "?"))
    ok_ingest = bool(m and m.group(1) == "10" and bad and bad.group(1) == "1")

    answers = [l[l.find("AI > ") + 5:] for l in out.splitlines() if "AI > " in l]
    st = {"pass": 0, "refuse": 0, "wrong": 0}
    for idx, (q, want) in enumerate(QUESTIONS):
        a = answers[idx] if idx < len(answers) else ""
        if want in a:
            st["pass"] += 1
        elif any(k in a for k in REFUSE):
            st["refuse"] += 1
        else:
            st["wrong"] += 1
    a = answers[len(QUESTIONS)] if len(answers) > len(QUESTIONS) else ""
    if "不 对" in a or "不对" in a or any(k in a for k in REFUSE):
        st["pass"] += 1
    else:
        st["wrong"] += 1

    total = len(QUESTIONS) + len(EXTRA_REFUSE)
    print("[epoch] pass %d / refuse %d / wrong %d（共 %d）" % (st["pass"], st["refuse"], st["wrong"], total))
    ok = ok_ingest and st["wrong"] == 0 and st["pass"] >= total * 0.8
    print("=> 训练-评测流水线：%s（ingest %s，contamination 0）"
          % ("PASS" if ok else "FAIL", "OK" if ok_ingest else "BAD"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
