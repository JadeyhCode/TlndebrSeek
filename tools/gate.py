#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tools/gate.py — 一条命令跑全部门禁，输出一张表（§6.874）。

为什么要有它：每轮手动跑 hidden → capbench → 4~5 个盲测集要 6~10 分钟，
而且**不能并行**（判官共用 _t/work，并行会读出假数据）。这个脚本串行跑、只打印表。

用法：
  python3 tools/gate.py              # hidden + capbench + blind26..30
  python3 tools/gate.py --suite      # 再加整包 tests/all.sh（约 8 分钟）
  python3 tools/gate.py --quick      # 只跑 blind26..30（约 3 分钟）
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETS = [26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44]


def run(cmd, env=None, timeout=1800):
    e = dict(os.environ)
    if env:
        e.update(env)
    r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, env=e, timeout=timeout)
    return r.returncode, (r.stdout.decode('utf-8', 'replace') + r.stderr.decode('utf-8', 'replace'))


def prepare():
    """干净克隆里 build_aip / code_model.bin 都不在（gitignore）—— 先备好，否则判官跑不了。"""
    msgs = []
    if not os.path.exists(os.path.join(ROOT, 'build_aip')):
        rc, out = run('gcc -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror -o build_aip main.c -lm',
                      timeout=600)
        msgs.append('build_aip: ' + ('built' if rc == 0 else 'FAILED\n' + out[-800:]))
    if not os.path.exists(os.path.join(ROOT, 'code', 'code_model.bin')):
        rc, out = run('sh code/build_code_model.sh', timeout=1800)
        msgs.append('code_model.bin: ' + ('built' if rc == 0 else 'FAILED\n' + out[-800:]))
    for m in msgs:
        print('  [准备] ' + m)


def hidden():
    rc, out = run('rm -rf _t/work && mkdir -p _t/work && python3 tools/code_hidden.py')
    ok = sum(int(m) for m in re.findall(r'=> (\d) / 8', out))
    total = 8 * len(re.findall(r'=> \d / 8', out))
    return ok, total, ('PASS' if rc == 0 and ok == total and total > 0 else 'FAIL')


def capbench():
    rc, out = run('AIP_CAPBENCH=1 sh tests/capbench.sh', timeout=2400)
    bad = [l.strip() for l in out.splitlines() if '[FAIL]' in l][:3]
    return ('PASS' if 'PASS capbench' in out else 'FAIL'), bad


def blind(n):
    f = os.path.join(ROOT, 'tools', 'code_blind%d.py' % n)
    if not os.path.exists(f):
        return None
    rc, out = run('rm -rf _t/work && mkdir -p _t/work && python3 tools/code_blind%d.py' % n)
    m = re.search(r'=> pass (\d+) / refuse (\d+) / wrong (\d+)', out)
    if not m:
        return ('?', '?', '?')
    return (m.group(1), m.group(2), m.group(3))


def suite():
    rc, out = run('rm -rf _t/par _t/work && mkdir -p _t/work && sh tests/all.sh', timeout=2400)
    ok = len(re.findall(r'^\[OK\]', out, re.M))
    return ok, ('PASS' if rc == 0 else 'FAIL')


def main(argv):
    prepare()
    quick = '--quick' in argv
    rows = []
    red = []
    if not quick:
        ok, total, verdict = hidden()
        rows.append(('hidden', '%d/%d' % (ok, total), verdict))
        if verdict != 'PASS': red.append('hidden')
        verdict, bad = capbench()
        rows.append(('capbench', '', verdict))
        if verdict != 'PASS': red.append('capbench: ' + '; '.join(bad))
    for n in SETS:
        got = blind(n)
        if not got:
            continue
        p, f, w = got
        rows.append(('blind%d' % n, 'pass %s / refuse %s / wrong %s' % (p, f, w), ''))
    if '--suite' in argv:
        ok, verdict = suite()
        rows.append(('suite', '%d 套' % ok, verdict))
        if verdict != 'PASS': red.append('suite')
    w = max(len(r[0]) for r in rows)
    print('')
    print('== 门禁表 ==')
    for name, val, verdict in rows:
        print('  %-*s  %-38s %s' % (w, name, val, verdict))
    if red:
        print('\n门禁红：' + ' | '.join(red))
        return 1
    print('\n全绿' if not quick else '\n（--quick：只跑盲测集）')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
