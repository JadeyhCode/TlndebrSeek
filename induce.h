/* induce.h — §7.085 P3 第一块：**行为归纳**（只统计 + 待证建议；不自动写图）。
 *
 * 输入：图里已经接受的肯定事实边（核心 rel 位 + 动态 dyn）。
 * 输出：对每个关系的 trans / sym / excl 支持与反例计数、支持率；只有显式
 *       `::induce claim <关系> <行为>` 才经理由闸门写成待证（`[待证:归纳:...]`）。
 * 阈值在 policy：`induce_min_support`（建议最少支持数）、`induce_min_ratio`（建议最低支持率）。
 */
#ifndef INDUCE_H
#define INDUCE_H

#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define INDUCE_MAX_PAIRS 4096
typedef struct { Token *a; Token *b; uint16_t rid; } IndPair;

static inline uint16_t induce_edge_rid(const AssocEntry *e) {
    if (!e || !e->main) return 0;
    if (e->dyn) return (uint16_t)(REL_DYN_BASE + e->dyn - 1);
    for (uint8_t r = 1; r < REL_DYN_BASE; ++r)
        if (e->rel & REL_BIT(r)) return r;
    return 0;
}

static inline size_t induce_collect(AI *ai, IndPair *out, size_t cap) {
    if (!ai || !out) return 0;
    size_t n = 0;
    for (uint32_t i = 0; i < ai->pool->count && n < cap; ++i) {
        Token *t = ai->pool->tokens[i];
        if (!t || t->is_garbage || !t->name) continue;
        for (size_t j = 0; j < t->count && n < cap; ++j) {
            const AssocEntry *e = &token_assocs_ro(t)[j];
            if (!e->main || edge_dyn_neg(e)) continue;
            uint16_t rid = induce_edge_rid(e);
            if (!rid) continue;
            if (rid >= REL_DYN_BASE && edge_is_guess(e)) continue;
            out[n].a = t; out[n].b = e->main; out[n].rid = rid;
            n++;
        }
    }
    return n;
}

static inline int induce_pair_exists(const IndPair *p, size_t n, Token *a, Token *b, uint16_t rid) {
    for (size_t i = 0; i < n; ++i)
        if (p[i].rid == rid && p[i].a == a && p[i].b == b) return 1;
    return 0;
}

typedef struct {
    uint32_t trans_sup, trans_ctr, sym_sup, sym_ctr;
    uint32_t excl_multi, excl_single;
    uint32_t n_edges;
} IndStat;

static inline void induce_stats(AI *ai, uint16_t rid, IndStat *st) {
    memset(st, 0, sizeof *st);
    static IndPair pairs[INDUCE_MAX_PAIRS];
    size_t n = 0;
    for (uint32_t i = 0; i < ai->pool->count && n < INDUCE_MAX_PAIRS; ++i) {
        Token *t = ai->pool->tokens[i];
        if (!t || t->is_garbage || !t->name) continue;
        for (size_t j = 0; j < t->count && n < INDUCE_MAX_PAIRS; ++j) {
            const AssocEntry *e = &token_assocs_ro(t)[j];
            if (!e->main || edge_dyn_neg(e)) continue;
            if (induce_edge_rid(e) != rid) continue;
            if (rid >= REL_DYN_BASE && edge_is_guess(e)) continue;
            pairs[n].a = t; pairs[n].b = e->main; pairs[n].rid = rid; n++;
        }
    }
    st->n_edges = (uint32_t)n;
    /* trans：A→B, B→C ⇒ A→C */
    for (size_t i = 0; i < n; ++i) {
        for (size_t j = 0; j < n; ++j) {
            if (i == j || pairs[i].b != pairs[j].a) continue;
            if (pairs[i].a == pairs[j].b) continue;   /* 自环不算 */
            if (induce_pair_exists(pairs, n, pairs[i].a, pairs[j].b, rid)) st->trans_sup++;
            else st->trans_ctr++;
        }
    }
    /* sym：A→B 且 B→A */
    for (size_t i = 0; i < n; ++i) {
        if (induce_pair_exists(pairs, n, pairs[i].b, pairs[i].a, rid)) st->sym_sup++;
        else st->sym_ctr++;
    }
    /* excl（粗略）：同一主语的对象数 >1 ⇒ multi */
    for (size_t i = 0; i < n; ++i) {
        int distinct = 0;
        for (size_t j = 0; j < n && distinct < 2; ++j)
            if (pairs[j].a == pairs[i].a && pairs[j].b != pairs[i].b) distinct = 1;
        if (distinct) st->excl_multi++;
        else st->excl_single++;
    }
}

static inline void induce_run(AI *ai, int top) {
    if (!ai) return;
    if (top <= 0 || top > 32) top = 12;
    long min_sup = aip_policy_int("induce_min_support", 2);
    double min_ratio = (double)aip_policy_float("induce_min_ratio", 0.6f);
    static IndStat sts[REL_TABLE_MAX + 1];
    static uint8_t has[REL_TABLE_MAX + 1];
    memset(has, 0, sizeof has);
    int shown = 0;
    printf("[归纳] 行为支持率（阈值：支持≥%ld、比例≥%.2f；只建议，不写图）：\n", min_sup, min_ratio);
    for (uint16_t rid = 1; rid <= REL_TABLE_MAX; ++rid) {
        if (!rel_name_of(ai, (uint8_t)rid)) continue;
        IndStat *st = &sts[rid];
        induce_stats(ai, rid, st);
        if (!st->n_edges) continue;
        double tr = (st->trans_sup + st->trans_ctr) ? (double)st->trans_sup / (double)(st->trans_sup + st->trans_ctr) : 0;
        double sy = (st->sym_sup + st->sym_ctr) ? (double)st->sym_sup / (double)(st->sym_sup + st->sym_ctr) : 0;
        int suggest = 0;
        if (st->trans_sup >= (uint32_t)min_sup && tr >= min_ratio) suggest |= 1;
        if (st->sym_sup >= (uint32_t)min_sup && sy >= min_ratio) suggest |= 2;
        if (st->excl_multi == 0 && st->excl_single >= (uint32_t)min_sup) suggest |= 4;
        printf("  %-8s 边%u ｜trans %u/%u(%.2f) ｜sym %u/%u(%.2f) ｜excl 单%u/多%u ⇒ 建议：%s%s%s\n",
               rel_name_of(ai, (uint8_t)rid), st->n_edges, st->trans_sup, st->trans_sup + st->trans_ctr, tr,
               st->sym_sup, st->sym_sup + st->sym_ctr, sy, st->excl_single, st->excl_multi,
               (suggest & 1) ? "trans " : "", (suggest & 2) ? "sym " : "",
               (suggest & 4) ? "excl" : (suggest ? "" : "-"));
        shown++;
        if (shown >= top) break;
    }
    if (!shown) printf("  （没有达到阈值的建议；多教一些同关系的事实用 ::induce 再看）\n");
}

/* 把一条“行为建议”写成**待证**（理由闸门 + 记账，仍不算数）。 */
static inline int induce_claim(AI *ai, const char *rel, const char *beh) {
    if (!ai || !rel || !*rel || !beh || !*beh) {
        printf("[归纳] 用法：::induce claim <关系> <trans|sym|excl>\n");
        return 1;
    }
    if (strcmp(beh, "trans") && strcmp(beh, "sym") && strcmp(beh, "excl")) {
        printf("[归纳] 行为只认 trans / sym / excl\n");
        return 1;
    }
    if (!sym_write_gate()) return 1;
    if (!g_sym_reason[0]) { printf("[归纳] 必须给理由：先 ::sym reason <为什么>\n"); return 1; }
    uint16_t rid = rel_id_of(ai, rel, 0);
    if (!rid) { printf("[归纳] 图里没有关系「%s」\n", rel); return 1; }
    Token *cl = claim_add(ai, "归纳", rel, beh, "成立");
    if (!cl) { printf("[归纳] 待证标记造不出来\n"); return 1; }
    printf("[归纳] 已写成待证：%s 具有 %s（来源「归纳」；**不算数**，::claim 里确认才算）\n", rel, beh);
    mkdir("_t", 0755);
    FILE *f = fopen("_t/induce.tsv", "ab");
    if (f) { fprintf(f, "%ld\t%s\t%s\t理由:%s\n", (long)time(NULL), rel, beh, g_sym_reason); fclose(f); }
    return 1;
}

static inline int induce_cmd(AI *ai, const char *arg) {
    if (!ai || !arg) return 0;
    while (*arg == ' ') arg++;
    if (!strncmp(arg, "claim", 5)) {
        const char *p = arg + 5;
        while (*p == ' ') p++;
        char rel[64] = {0}, beh[16] = {0};
        if (sscanf(p, "%63s %15s", rel, beh) != 2) {
            printf("[归纳] 用法：::induce claim <关系> <trans|sym|excl>\n");
            return 1;
        }
        return induce_claim(ai, rel, beh);
    }
    induce_run(ai, (arg && *arg) ? atoi(arg) : 12);
    return 1;
}

#endif /* INDUCE_H */
