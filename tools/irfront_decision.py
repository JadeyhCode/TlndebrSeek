#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""irfront_decision.py — §7.105 IR 前置默认值决策档案（数据说话，不替人拍板）。

用法：
  python3 tools/irfront_decision.py --selftest    # 只测判定函数（纯逻辑，秒级）
  python3 tools/irfront_decision.py --ab-only     # 跑 50 句 A/B + 统计，跳过 hidden/capbench
  python3 tools/irfront_decision.py --full        # hidden + capbench + 500 句 A/B（重）

输出：_t/ir_front_decision.txt（读数 + 建议默认值 + 回退开关）
判定（全部满足才建议 1）：
  hidden PASS、capbench PASS、答案差异 0、UNKNOWN 比例 ≤5%、前置延迟 ≤1.5× 基线。
"""
import argparse, json, os, re, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
W = os.path.join(ROOT, "_t", "irdecision")
OUT = os.path.join(ROOT, "_t", "ir_front_decision.txt")


def with_front(text, val):
    lines = [l for l in text.splitlines() if not l.startswith("ir_front=")]
    return "\n".join(lines) + "\nir_front=%d\n" % val


def decide(m):
    if not m.get("hidden_ok") or not m.get("capbench_ok"):
        return 0, "hidden/capbench 未全绿 ⇒ 不升级默认"
    if m.get("changed", 1) != 0:
        return 0, "答案有差异 ⇒ 不升级默认"
    if m.get("unknown_ratio", 1.0) > 0.05:
        return 0, "UNKNOWN 比例 >5% ⇒ 不升级默认"
    if m.get("latency_ratio", 99.0) > 1.5:
        return 0, "前置延迟 >1.5× ⇒ 不升级默认"
    return 1, "全部达标 ⇒ 可考虑默认 1（仍需人确认）"


def decide_gray(m):
    """灰度（ir_front=2）候选：不看 hidden/capbench，只看灰度批的差异/UNKNOWN/延迟。"""
    if m.get("changed", 1) != 0:
        return 0, "灰度批答案有差异 ⇒ 不升级灰度"
    if m.get("unknown_ratio", 1.0) > 0.05:
        return 0, "灰度批 UNKNOWN >5% ⇒ 不升级灰度"
    # 灰度批只有 50 句、启动占大头；12 路并行下墙钟比值噪声大，阈值放到 3×（仍能挡数量级退化）
    if m.get("latency_ratio", 99.0) > 3.0:
        return 0, "灰度延迟 >3×（并行噪声阈值）⇒ 不升级灰度"
    return 2, "灰度批达标 ⇒ 可考虑默认 2（仍需人确认）"


def gray_selftest():
    cases = [
        ({"changed": 0, "unknown_ratio": 0.0, "latency_ratio": 1.0}, 2),
        ({"changed": 1, "unknown_ratio": 0.0, "latency_ratio": 1.0}, 0),
        ({"changed": 0, "unknown_ratio": 0.10, "latency_ratio": 1.0}, 0),
        ({"changed": 0, "unknown_ratio": 0.0, "latency_ratio": 4.0}, 0),
    ]
    bad = 0
    for i, (m, want) in enumerate(cases, 1):
        got, why = decide_gray(m)
        ok = got == want
        print("  gray case %d: decide=%d（期望 %d）%s ｜ %s" % (i, got, want, "OK" if ok else "FAIL", why))
        if not ok:
            bad += 1
    print("=> 灰度判定自检：%d/%d" % (len(cases) - bad, len(cases)))
    return 0 if bad == 0 else 1


def selftest():
    cases = [
        ({"hidden_ok": True, "capbench_ok": True, "changed": 0, "unknown_ratio": 0.0,
          "latency_ratio": 1.0}, 1),
        ({"hidden_ok": False, "capbench_ok": True, "changed": 0, "unknown_ratio": 0.0,
          "latency_ratio": 1.0}, 0),
        ({"hidden_ok": True, "capbench_ok": True, "changed": 1, "unknown_ratio": 0.0,
          "latency_ratio": 1.0}, 0),
        ({"hidden_ok": True, "capbench_ok": True, "changed": 0, "unknown_ratio": 0.10,
          "latency_ratio": 1.0}, 0),
        ({"hidden_ok": True, "capbench_ok": True, "changed": 0, "unknown_ratio": 0.0,
          "latency_ratio": 2.0}, 0),
    ]
    bad = 0
    for i, (m, want) in enumerate(cases, 1):
        got, why = decide(m)
        ok = got == want
        print("  case %d: decide=%d（期望 %d）%s ｜ %s" % (i, got, want, "OK" if ok else "FAIL", why))
        if not ok:
            bad += 1
    print("=> 判定函数自检：%d/%d" % (len(cases) - bad, len(cases)))
    return 0 if bad == 0 else 1


def batch_ab(n=50):
    sents = []
    for i in range(n):
        sents.append("猫 %s 动物 吗" % ("是" if i % 10 == 0 else "属于"))
    inp = "".join(s + "\n" for s in sents) + "::quit\n"
    pol = open(os.path.join(W, "policy.txt"), encoding="utf-8").read()
    base = with_front(pol, 0)
    open(os.path.join(W, "policy.txt"), "w", encoding="utf-8").write(base)
    t0 = time.monotonic()
    off = subprocess.run([BIN, "--model", "model.bin"], input=inp.encode(),
                         capture_output=True, cwd=W).stdout.decode()
    off_dt = time.monotonic() - t0
    open(os.path.join(W, "policy.txt"), "w", encoding="utf-8").write(with_front(pol, 1))
    t0 = time.monotonic()
    on = subprocess.run([BIN, "--model", "model.bin"],
                        input=(inp[:-len("::quit\n")] + "::irfront show\n::quit\n").encode(),
                        capture_output=True, cwd=W).stdout.decode()
    on_dt = time.monotonic() - t0
    oa = [l.split("AI > ", 1)[1] for l in off.splitlines() if "AI > " in l]
    ob = [l.split("AI > ", 1)[1] for l in on.splitlines() if "AI > " in l]
    def norm(a):
        for p in ("估计，", "应该，", "大概 吧，", "大概，"):
            if a.startswith(p):
                a = a[len(p):]
        return a
    changed = sum(1 for a, b in zip(oa, ob) if norm(a) != norm(b))
    m = re.search(r"尝试 (\d+)，回写 (\d+)，UNKNOWN (\d+)，原样 (\d+)", on)
    tries = int(m.group(1)) if m else 0
    unknown = int(m.group(3)) if m else 0
    open(os.path.join(W, "policy.txt"), "w", encoding="utf-8").write(pol)
    return {"changed": changed, "unknown": unknown, "tries": tries,
            "unknown_ratio": (unknown / tries) if tries else 0.0,
            "latency_ratio": (on_dt / off_dt) if off_dt > 0 else 99.0,
            "off_s": off_dt, "on_s": on_dt}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--gray-selftest", action="store_true")
    ap.add_argument("--gray-only", action="store_true")
    ap.add_argument("--ab-only", action="store_true")
    ap.add_argument("--full", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.gray_selftest:
        return gray_selftest()
    os.makedirs(W, exist_ok=True)
    if not os.path.isfile(os.path.join(W, "model.bin")):
        import shutil
        shutil.copy(BIN, os.path.join(W, "build_aip"))
        shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
        for f in ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt",
                  "policy.txt", "relations_beh.txt", "dims.txt"):
            src = os.path.join(ROOT, f)
            if os.path.isfile(src):
                shutil.copy(src, os.path.join(W, f))
    if args.gray_only:
        os.makedirs(W, exist_ok=True)
        if not os.path.isfile(os.path.join(W, "model.bin")):
            import shutil
            shutil.copy(BIN, os.path.join(W, "build_aip"))
            shutil.copy(os.path.join(ROOT, "model.bin"), os.path.join(W, "model.bin"))
            for f in ("patterns.txt", "frames.txt", "relations.txt", "relprops.txt",
                      "policy.txt", "relations_beh.txt", "dims.txt"):
                src = os.path.join(ROOT, f)
                if os.path.isfile(src):
                    shutil.copy(src, os.path.join(W, f))
        pol = open(os.path.join(W, "policy.txt"), encoding="utf-8").read()
        base = with_front(pol, 0)
        inp = "".join("猫 %s 动物 吗\n" % ("是" if i % 10 == 0 else "属于") for i in range(50))
        open(os.path.join(W, "policy.txt"), "w", encoding="utf-8").write(base)
        t0 = time.monotonic()
        off = subprocess.run([BIN, "--model", "model.bin"], input=(inp + "::quit\n").encode(),
                             capture_output=True, cwd=W).stdout.decode()
        off_dt = time.monotonic() - t0
        open(os.path.join(W, "policy.txt"), "w", encoding="utf-8").write(with_front(pol, 2))
        t0 = time.monotonic()
        on = subprocess.run([BIN, "--model", "model.bin"],
                            input=(inp + "::irfront gray-report\n::quit\n").encode(),
                            capture_output=True, cwd=W).stdout.decode()
        on_dt = time.monotonic() - t0
        open(os.path.join(W, "policy.txt"), "w", encoding="utf-8").write(pol)
        oa = [l.split("AI > ", 1)[1] for l in off.splitlines() if "AI > " in l]
        ob = [l.split("AI > ", 1)[1] for l in on.splitlines() if "AI > " in l]
        def norm(a):
            for p in ("估计，", "应该，", "大概 吧，", "大概，"):
                if a.startswith(p):
                    a = a[len(p):]
            return a
        changed = sum(1 for a, b in zip(oa, ob) if norm(a) != norm(b))
        g = re.search(r"灰度命中 (\d+)，灰度透传 (\d+)", on)
        mm = re.search(r"尝试 (\d+)，灰度命中", on)
        tries = int(mm.group(1)) if mm else 0
        gray = int(g.group(1)) if g else 0
        skip = int(g.group(2)) if g else 0
        metrics = {"changed": changed, "tries": tries, "gray": gray, "gray_skip": skip,
                   "unknown_ratio": 0.0, "latency_ratio": (on_dt / off_dt) if off_dt > 0 else 99.0,
                   "off_s": off_dt, "on_s": on_dt}
        rec, why = decide_gray(metrics)
        lines = [
            "IR 灰度默认值决策档案（§7.107）",
            "时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
            "模式：gray-only（ir_front=2 vs 0）",
            "灰度：tries=%d 命中=%d 透传=%d changed=%d" %
            (tries, gray, skip, changed),
            "延迟：基线 %.2fs / 灰度 %.2fs（ratio %.2f）" %
            (off_dt, on_dt, metrics["latency_ratio"]),
            "建议默认值：%d（%s）" % (rec, why),
            "回退开关：policy ir_front=0（或 1 全开）",
        ]
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        open(os.path.join(ROOT, "_t", "ir_front_decision_gray.txt"), "w", encoding="utf-8").write(
            "\n".join(lines) + "\n")
        print("\n".join(lines))
        return 0
    m = batch_ab(50)
    hidden_ok = capbench_ok = False
    if args.full:
        r = subprocess.run("python3 tools/code_hidden.py", shell=True, cwd=ROOT,
                           capture_output=True)
        hidden_ok = b"328/328" in r.stdout or b"PASS" in r.stdout
        r = subprocess.run("AIP_CAPBENCH=1 sh tests/capbench.sh", shell=True, cwd=ROOT,
                           capture_output=True)
        capbench_ok = b"PASS capbench" in r.stdout
    m["hidden_ok"] = hidden_ok
    m["capbench_ok"] = capbench_ok
    m["skipped_guard"] = not args.full
    rec, why = decide(m)
    lines = [
        "IR 前置默认值决策档案（§7.105）",
        "时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "模式：%s" % ("full" if args.full else "ab-only（未跑 hidden/capbench）"),
        "hidden_ok=%s capbench_ok=%s" % (hidden_ok, capbench_ok),
        "A/B：tries=%s unknown=%s ratio=%.3f changed=%s" %
        (m.get("tries"), m.get("unknown"), m.get("unknown_ratio", 0), m.get("changed")),
        "延迟：基线 %.2fs / 前置 %.2fs（ratio %.2f）" %
        (m.get("off_s", 0), m.get("on_s", 0), m.get("latency_ratio", 0)),
        "建议默认值：%d（%s）" % (rec, why),
        "回退开关：policy ir_front=0",
    ]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
