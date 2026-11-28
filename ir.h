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

typedef enum { IR_UNKNOWN = 0, IR_REL, IR_QUERY, IR_CMD } IrKind;

typedef struct {
    IrKind kind;
    char   a[64];
    char   rel[40];
    char   b[64];
    int    neg;
    int    q;
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

#endif /* IR_H */
