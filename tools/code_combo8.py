#!/usr/bin/env python3
"""§6.959 组合迁移小盲测（8 题，首跑）：两问句/两个结果，量 pass/refuse/wrong。
不依赖教师：只走 ::code synth（本地合成）。
"""
import os, shutil, subprocess, sys, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(ROOT, "build_aip")
MODEL = os.path.join(ROOT, "code", "code_model.bin")
W = os.path.join(ROOT, "_t", "combo8")
TASKS = [
    ("输入一行整数，输出最大值与最小值", "3 9 2\n", "9 2"),
    ("输入一行整数，输出它们的和与积", "2 3\n", "5 6"),
    ("输入两个整数，输出商与余数", "7 3\n", "2 1"),
    ("输入一行整数，输出最大值的下标", "3 9 2\n", "1"),
    ("输入一行整数，输出和减最大", "1 2 3\n", "3"),
    ("输入一行整数，输出最大加最小", "1 5 2\n", "6"),
    ("输入一行整数，排序后取中位数", "1 3 2\n", "2"),
    ("输入一行整数，输出最大值与第二大的数", "3 9 2\n", "9 3"),
]
def run(desc):
    cmd=[BIN,"--model",MODEL]
    out=subprocess.run(cmd,input="::act on\n::code synth %s\n::quit\n"%desc,text=True,encoding="utf-8",errors="replace",capture_output=True,cwd=W,timeout=120).stdout
    return out
def gen_c(out):
    m=re.search(r"→\s*(synth_[^\s：，]+\.c)",out)
    return m.group(1) if m else None
def main():
    shutil.rmtree(W,ignore_errors=True); os.makedirs(os.path.join(W,"_t","work"))
    shutil.copy(MODEL,os.path.join(W,"model.bin")); shutil.copy(BIN,os.path.join(W,"build_aip"))
    res={"pass":0,"refuse":0,"wrong":0}
    for desc,inp,exp in TASKS:
        out=run(desc)
        c=gen_c(out)
        if not c:
            res["refuse"]+=1; print("  [REFUSE]",desc); continue
        src=os.path.join(W,"_t","work",c)
        exe=src+".out"
        if not os.path.isfile(src):
            res["refuse"]+=1; print("  [REFUSE]",desc,"(没写出来)"); continue
        if not os.path.isfile(exe):
            build=subprocess.run(["gcc","-std=c11","-O2","-o",exe,src],capture_output=True,text=True)
            if build.returncode!=0:
                res["refuse"]+=1; print("  [REFUSE]",desc,"(编不过)"); continue
        try:
            got=subprocess.run([exe],input=inp,text=True,capture_output=True,timeout=10)
            vals=" ".join(got.stdout.splitlines()[0].split()) if got.stdout.strip() else ""
        except Exception:
            vals=""
        if vals==exp.strip(): res["pass"]+=1; print("  [PASS]",desc)
        else:
            res["wrong"]+=1; print("  [WRONG]",desc,"期望 %r 实际 %r"%(exp.strip(),vals))
    print("=> pass %d / refuse %d / wrong %d（共 %d）"%(res["pass"],res["refuse"],res["wrong"],len(TASKS)))
    return 0
if __name__=="__main__": sys.exit(main())
