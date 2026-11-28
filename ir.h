/* ir.h — §7.097 P4：**IR 边界**（原子/过程/声明/证据/问题 + text→IR 适配器）。
 *
 * 这一版只做**只读对照**：把一句话解析成 IR 原子，再回写成规范文本；
 * 不改变现有理解路径、不写图。目标是先把“核只吃 IR”的边界划出来，
 * 后续再把 english/词表/共现统计移到适配器侧。
 *
 * 结构：
 *   IrAtom{kind, a, rel, b, neg, q, cmd, note}
 *   kind = REL（陈述关系）/ QUERY（关系问句）/ CMD（元命令）/ UNKNOWN（适配器接不住）
 */
#ifndef IR_H
#define IR_H

#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <time.h>
#include <sys/stat.h>

typedef enum { IR_UNKNOWN = 0, IR_REL, IR_QUERY, IR_CMD } IrKind;

typedef struct {
    IrKind kind;
    char   a[64];
    char   rel[40];
    char   b[64];
    int    neg;
    int    q;
    RelId  rid;          /* §7.099 关系 id（0=没解析出来） */
    int    evidence;     /* 0=未知 1=直接事实 2=推导 3=推测 */
    char   cmd[256];
    char   note[128];
} IrAtom;

static inline const char *ir_kind_name(IrKind k) {
    switch (k) {
        case IR_REL:   return "REL";
        case IR_QUERY: return "QUERY";
        case IR_CMD:   return "CMD";
        default:       return "UNKNOWN";
    }
}

/* text → IR（只读；不改图）。返回 1 = 产出了非 UNKNOWN 原子。 */
static inline int ir_from_text(AI *ai, const char *text, IrAtom *out) {
    if (!ai || !text || !out) return 0;
    memset(out, 0, sizeof *out);
    const char *p = text;
    while (*p == ' ' || *p == '\t') p++;
    if (!*p) { snprintf(out->note, sizeof out->note, "空输入"); return 0; }
    if (p[0] == ':' && p[1] == ':') {
        out->kind = IR_CMD;
        snprintf(out->cmd, sizeof out->cmd, "%s", p);
        return 1;
    }
    size_t n = 0;
    char **words = ai_tokenize(ai, p, &n);
    if (!words || n < 3) {
        if (words) ai_free_words(words, n);
        out->kind = IR_UNKNOWN;
        snprintf(out->note, sizeof out->note, "分词不足 3 个词，适配器不接");
        return 0;
    }
    char jbuf[512];
    const char *aw = NULL, *bw = NULL, *rw = NULL;
    RelId rid = 0;
    int neg = 0, isq = 0;
    int ok = rel_parse(ai, words, n, jbuf, sizeof jbuf, &aw, &rid, &neg, &bw, &isq, &rw, 0);
    if (ok && aw && bw && rid) {
        out->kind = isq ? IR_QUERY : IR_REL;
        snprintf(out->a, sizeof out->a, "%s", aw);
        snprintf(out->b, sizeof out->b, "%s", bw);
        const char *rn = rel_name_of(ai, rid);
        snprintf(out->rel, sizeof out->rel, "%s", rn ? rn : "?");
        out->neg = neg;
        out->q = isq;
        out->rid = rid;
    } else {
        out->kind = IR_UNKNOWN;
        snprintf(out->note, sizeof out->note, "关系解析没接住（可降到语言适配器）");
    }
    ai_free_words(words, n);
    return out->kind != IR_UNKNOWN;
}

/* IR → 规范文本（回写；用于对照与证据）。 */
static inline void ir_render(const IrAtom *at, char *buf, size_t cap) {
    if (!at || !buf || !cap) return;
    switch (at->kind) {
        case IR_CMD:
            snprintf(buf, cap, "%s", at->cmd);
            break;
        case IR_REL:
        case IR_QUERY:
            snprintf(buf, cap, "%s %s%s %s%s", at->a, at->neg ? "不 " : "",
                     at->rel, at->b, at->q ? " 吗" : "");
            break;
        default:
            snprintf(buf, cap, "（UNKNOWN：%s）", at->note);
            break;
    }
}

/* §7.101 前置统计（进程内计数 + 命中账本）：tries=非命令输入、rewrites=实际回写、
 * unknown=适配器接不住、same=回写后与原文相同、cmds=命令跳过。 */
typedef struct { size_t tries, rewrites, unknown, same, cmds; } IrFrontStats;
static IrFrontStats g_irf;

/* §7.100 IR 前置（受控开关）：把能解析的句子回写成规范文本再送进现有管线。
 * 只做“文本等价替换”，不改变管线内部；UNKNOWN/CMD 原样透传。 */
static inline int ir_front_observe(AI *ai, const char *in, char *out, size_t cap) {
    if (!ai || !in || !out || !cap || !*in) return 0;
    if (in[0] == ':') { g_irf.cmds++; return 0; }
    if (!aip_policy_int("ir_adapter", 1)) return 0;
    if (!aip_policy_int("ir_front", 0)) return 0;
    g_irf.tries++;
    IrAtom at;
    if (!ir_from_text(ai, in, &at) || (at.kind != IR_REL && at.kind != IR_QUERY)) {
        g_irf.unknown++;
        return 0;
    }
    ir_render(&at, out, cap);
    if (!strcmp(in, out)) { g_irf.same++; return 0; }
    g_irf.rewrites++;
    if (getenv("AIP_IRFRONT_DBG"))
        fprintf(stderr, "[irfront] %s => %s\n", in, out);
    mkdir("_t", 0755);
    FILE *f = fopen("_t/ir_front_stats.tsv", "ab");
    if (f) { fprintf(f, "%ld\t%s\t%s\n", (long)time(NULL), in, out); fclose(f); }
    return 1;
}

static inline int irfront_cmd(AI *ai, const char *arg) {
    (void)ai;
    const char *p = arg ? arg : "";
    while (*p == ' ') p++;
    if (!strncmp(p, "reset", 5)) {
        memset(&g_irf, 0, sizeof g_irf);
        printf("[IR前置] 统计已清零\n");
        return 1;
    }
    printf("[IR前置] 开关：ir_adapter=%ld ir_front=%ld\n",
           aip_policy_int("ir_adapter", 1), aip_policy_int("ir_front", 0));
    printf("[IR前置] 本进程：尝试 %zu，回写 %zu，UNKNOWN %zu，原样 %zu，命令跳过 %zu\n",
           g_irf.tries, g_irf.rewrites, g_irf.unknown, g_irf.same, g_irf.cmds);
    printf("          命中账本：_t/ir_front_stats.tsv（有回写才追加）\n");
    return 1;
}

/* `::ir <文本>`：只读对照，不喂给理解管线，也不写图。 */
static inline int ir_cmd(AI *ai, const char *arg) {
    if (!arg || !*arg) {
        printf("[IR] 用法：::ir <一句话|::命令>（只读；text→IR→规范文本）\n");
        return 1;
    }
    long on = aip_policy_int("ir_adapter", 1);
    if (!on) {
        printf("[IR] 适配器关（ir_adapter=0）：保持旧行为，直接走分词/理解\n");
        return 1;
    }
    IrAtom at;
    int ok = ir_from_text(ai, arg, &at);
    char back[512];
    ir_render(&at, back, sizeof back);
    printf("[IR] kind=%s", ir_kind_name(at.kind));
    if (at.kind == IR_CMD) printf(" cmd=%s", at.cmd);
    if (at.kind == IR_REL || at.kind == IR_QUERY)
        printf(" a=%s rel=%s b=%s neg=%d q=%d", at.a, at.rel, at.b, at.neg, at.q);
    if (at.kind == IR_UNKNOWN) printf(" note=%s", at.note);
    printf("\n[IR→文本] %s\n", back);
    if (!ok) return 0;
    return 1;
}

/* §7.098 只读双跑对照：原文 → IR → 规范文本 → IR，再对同一关系问题做只读求解，
 * 比较两边的原子与真值。**不写图、不改理解管线**。 */
static inline int ir_atom_equal(const IrAtom *x, const IrAtom *y) {
    if (!x || !y || x->kind != y->kind) return 0;
    if (x->kind == IR_CMD) return !strcmp(x->cmd, y->cmd);
    if (x->kind == IR_REL || x->kind == IR_QUERY)
        return !strcmp(x->a, y->a) && !strcmp(x->rel, y->rel) && !strcmp(x->b, y->b)
               && x->neg == y->neg && x->q == y->q;
    return 1;
}

/* 只读求解：0=能解（truth 带回 +1/-1/0），1=缺词/缺关系（未知），2=结构不对 */
static inline int ir_solve(AI *ai, const IrAtom *at, int *truth, int *ev) {
    if (truth) *truth = 0;
    if (ev) *ev = 0;
    if (!ai || !at || (at->kind != IR_REL && at->kind != IR_QUERY)) return 2;
    Token *a = pool_find(ai->pool, at->a);
    Token *b = pool_find(ai->pool, at->b);
    if (!a || !b) return 1;
    RelId rid = rel_id_of(ai, at->rel, 0);
    if (!rid) return 1;
    Proof pf;
    memset(&pf, 0, sizeof pf);
    rel_solve(ai, a, rid, b, at->neg ? 1 : 0, &pf);
    if (truth) *truth = pf.status;
    if (ev) {
        int direct = at->neg ? rel_direct_neg(a, rid, b) : rel_direct(a, rid, b);
        *ev = direct ? 1 : (pf.guessed ? 3 : (pf.status != 0 ? 2 : 0));
    }
    return 0;
}

static inline int irparity_cmd(AI *ai, const char *arg) {
    if (!arg || !*arg) {
        printf("[IR对照] 用法：::irparity <一句话>（原文 vs IR 回写；只读）\n");
        return 1;
    }
    long on = aip_policy_int("ir_adapter", 1);
    if (!on) {
        printf("[IR对照] 适配器关（ir_adapter=0）：不做 IR 中转\n");
        return 1;
    }
    IrAtom x;
    (void)ir_from_text(ai, arg, &x);
    char back[512];
    ir_render(&x, back, sizeof back);
    IrAtom y;
    (void)ir_from_text(ai, back, &y);
    int same = ir_atom_equal(&x, &y);
    int tx = 0, ty = 0, ex = 0, ey = 0;
    int rx = ir_solve(ai, &x, &tx, &ex);
    int ry = ir_solve(ai, &y, &ty, &ey);
    static const char *EVN[4] = {"未知", "直接", "推导", "推测"};
    printf("[IR对照] 原文 → %s ｜ 回写 → %s\n", back, ir_kind_name(y.kind));
    printf("[IR对照] 原子一致=%s", same ? "是" : "否");
    if (x.kind == IR_REL || x.kind == IR_QUERY)
        printf(" ｜ 只读真值：原文=%s(%s) / 回写=%s(%s)",
               rx ? "未知" : (tx > 0 ? "成立" : (tx < 0 ? "不成立" : "未知")), EVN[ex & 3],
               ry ? "未知" : (ty > 0 ? "成立" : (ty < 0 ? "不成立" : "未知")), EVN[ey & 3]);
    printf("\n");
    /* §7.099 不一致原因分类 + 迁移账本（默认只记不一致；`ir_migrate_all=1` 全记） */
    const char *reason = "none";
    if (x.kind != y.kind) reason = "kind";
    else if (x.kind == IR_REL || x.kind == IR_QUERY) {
        if (!strcmp(x.a, y.a) == 0) reason = "a";
        else if (!strcmp(x.rel, y.rel) == 0) reason = "rel";
        else if (!strcmp(x.b, y.b) == 0) reason = "b";
        else if (x.neg != y.neg) reason = "neg";
        else if (x.q != y.q) reason = "q";
        else if (rx != ry || tx != ty) reason = "truth";
    }
    int mismatch = same ? 0 : 1;
    if (mismatch || aip_policy_int("ir_migrate_all", 0)) {
        mkdir("_t", 0755);
        FILE *f = fopen("_t/ir_migration.tsv", "ab");
        if (f) {
            fprintf(f, "%ld\t%s\t%s\t%s\t%s\t%s\t%s\n", (long)time(NULL),
                    mismatch ? "MISMATCH" : "ok", reason, x.kind == IR_CMD ? x.cmd : back,
                    mismatch ? "≠" : "=", EVN[ex & 3], EVN[ey & 3]);
            fclose(f);
        }
        printf("[IR对照] 迁移账本：%s（reason=%s）\n", mismatch ? "已记不一致" : "已记一致", reason);
    }
    if (x.kind == IR_REL || x.kind == IR_QUERY)
        printf("[IR对照] 结论：%s\n",
               (same && rx == ry && tx == ty) ? "一致（可安全走 IR）" : "不一致（迁移清单 +1）");
    else
        printf("[IR对照] 结论：%s\n", same ? "一致（非关系原子）" : "不一致");
    return 1;
}

#endif /* IR_H */
