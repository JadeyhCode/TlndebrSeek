/* cmp.h — §7.088 P1 收尾：比较/时间线（`::cmp`）。
 *
 * 数据：relations_beh.txt 的 `大于/小于/等于`（dim=数值，ordinal/trans/逆）
 *       与 `先于/后于/同时`（dim=时间，temporal/ordinal/trans）；量纲名在 dims.txt 注册。
 * 单位归一：复用 units.h 的内置单位表（长度/质量/时间/体积/温度），比较前换到同一单位。
 * 语义：只回答 对/不对/不可比；不可比**不说假**，给原因（开放世界）。
 */
#ifndef CMP_H
#define CMP_H

#include <stdio.h>
#include <string.h>
#include <math.h>
#include "units.h"

typedef struct { CalcRat v; const UnitDef *u; int has; } CmpQty;

/* 解析一个操作数：`3` / `3米` / `1.5 小时`（数字+紧邻单位；允许中间空格） */
static inline int cmp_parse_operand(const char *s, CmpQty *q) {
    memset(q, 0, sizeof *q);
    if (!s || !*s) return 0;
    while (*s == ' ' || *s == '\t') s++;
    if (!(*s == '-' || (*s >= '0' && *s <= '9'))) return 0;
    CalcP c; c.p = s; c.err = 0;
    CalcRat v = calc_expr(&c);
    if (c.err || !v.ok) return 0;
    const char *p = c.p;
    while (*p == ' ' || *p == '\t') p++;
    if (!*p) { q->v = v; q->u = NULL; q->has = 1; return 1; }
    size_t l = 0;
    const UnitDef *u = units_at(p, &l);
    if (!u || l == 0) return 0;
    p += l;
    while (*p == ' ' || *p == '\t') p++;
    if (*p) return 0;
    q->v = v; q->u = u; q->has = 1;
    return 1;
}

static inline int cmp_cmd(const char *arg) {
    char a[64] = {0}, op[16] = {0}, b[64] = {0};
    if (!arg || sscanf(arg, "%63s %15s %63s", a, op, b) != 3) {
        printf("[比较] 用法：::cmp <值A> <大于|小于|等于|先于|后于|同时> <值B>\n"
               "  数值例：::cmp 3 小于 5；带单位：::cmp 1小时 先于 90分钟\n");
        return 1;
    }
    int temporal = !strcmp(op, "先于") || !strcmp(op, "后于") || !strcmp(op, "同时");
    if (!temporal && strcmp(op, "大于") && strcmp(op, "小于") && strcmp(op, "等于")) {
        printf("[比较] 不认识的关系「%s」（只认 大于/小于/等于/先于/后于/同时）\n", op);
        return 1;
    }
    CmpQty A, B;
    if (!cmp_parse_operand(a, &A) || !cmp_parse_operand(b, &B)) {
        printf("[比较] 解析不了操作数（要数字，可带单位：3、3米、1小时）\n");
        return 1;
    }
    if (!A.u && !B.u) {
        if (temporal) {
            printf("[比较] 不可比：先于/后于/同时 只用于**时间**（两侧至少一侧要带时间单位）\n");
            return 1;
        }
    } else if (!A.u || !B.u) {
        printf("[比较] 不可比：一侧有单位、另一侧没有（%s vs %s）\n",
               A.u ? A.u->unit : "无量纲", B.u ? B.u->unit : "无量纲");
        return 1;
    } else if (strcmp(A.u->dim, B.u->dim) != 0) {
        printf("[比较] 不可比：%s vs %s（量纲不同）\n", A.u->dim, B.u->dim);
        return 1;
    } else if (temporal && strcmp(A.u->dim, "时间") != 0) {
        printf("[比较] 不可比：先于/后于/同时 只用于时间（这是%s）\n", A.u->dim);
        return 1;
    }
    int sign = 0;
    if (A.u) {
        CalcRat a2;
        if (!units_convert(A.v, A.u, B.u, &a2)) {
            printf("[比较] 不可比：单位换算失败\n");
            return 1;
        }
        CalcRat d = calc_sub(a2, B.v);
        if (!d.ok) { printf("[比较] 不可比：算不出来\n"); return 1; }
        if (d.n > 0) sign = 1; else if (d.n < 0) sign = -1;
    } else {
        CalcRat d = calc_sub(A.v, B.v);
        if (!d.ok) { printf("[比较] 不可比：算不出来\n"); return 1; }
        if (d.n > 0) sign = 1; else if (d.n < 0) sign = -1;
    }
    int yes = 0;
    if (!strcmp(op, "大于") || !strcmp(op, "后于")) yes = sign > 0;
    else if (!strcmp(op, "小于") || !strcmp(op, "先于")) yes = sign < 0;
    else yes = sign == 0;
    const char *dim = A.u ? A.u->dim : "数值";
    printf("[比较] %s %s %s ⇒ %s（%s；单位已归一）\n", a, op, b, yes ? "对" : "不对", dim);
    return 1;
}

#endif /* CMP_H */
