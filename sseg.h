#ifndef SSEG_H
#define SSEG_H
/* sseg.h — §6.965 滑动联想切分（图驱动，无词表）
 *
 * 与 ai_tokenize 的“最长优先、切完就走”不同，这里做**候选格**：
 *   1) 对句中每个位置，枚举所有“图里认识”的子串（多字词必须 pool_find 命中）；
 *      单字始终保留 —— 它不是词，是**字**（语言原语，不占词表）；
 *   2) 用 DP 在所有切分里选一条“图支持度”最高的路：词的度数 + 相邻词在图上有没有边；
 *   3) 对选中的词，把它在图上的联想（邻接词）按“与上下文其它词是否有边”排序：
 *      有边的标“激活”，没边的只作候选。
 *
 * 过程只用图（Token/AssocEntry），代码里**没有**任何具体词、也没有固定答案。
 */
#include <math.h>

#define SSEG_MAX_CH    64
#define SSEG_MAX_CAND 512

typedef struct {
    int start, end;       /* 字下标（不是字节） */
    Token *tok;           /* 图里的词；单字可能为 NULL（只是字） */
    char name[64];
} SsegCand;

static inline int sseg_char_offsets(const char *s, int *off, int cap) {
    int n = 0;
    const unsigned char *p = (const unsigned char *)s;
    while (*p && n < cap - 1) {
        off[n++] = (int)(p - (const unsigned char *)s);
        size_t l = cjk_char_len(p);
        if (l == 0) l = 1;
        p += l;
    }
    off[n] = (int)strlen(s);
    return n;
}

static inline int sseg_edge(const Token *a, const Token *b) {
    if (!a || !b || a == b) return 0;
    for (size_t i = 0; i < a->count; ++i)
        if (token_assocs_ro(a)[i].main == b) return 1;
    return 0;
}

/* 枚举候选（图里的子串 + 单字） */
static inline int sseg_candidates(AI *ai, const char *text, SsegCand *cs, int cap,
                                  int *off, int *nch) {
    *nch = sseg_char_offsets(text, off, SSEG_MAX_CH);
    int n = 0;
    for (int i = 0; i < *nch && n < cap; ++i) {
        for (int j = i + 1; j <= *nch && j - i <= 8 && n < cap; ++j) {
            int b0 = off[i], b1 = off[j];
            char buf[64];
            int len = b1 - b0;
            if (len <= 0 || len >= (int)sizeof buf) continue;
            memcpy(buf, text + b0, (size_t)len);
            buf[len] = 0;
            Token *t = pool_find(ai->pool, buf);    /* 单字也挂上图节点（若图里有），只为看词义 */
            if (j - i > 1 && !t) continue;          /* 多字必须是图里的词 */
            SsegCand *c = &cs[n++];
            c->start = i; c->end = j; c->tok = t;
            snprintf(c->name, sizeof c->name, "%s", buf);
        }
    }
    return n;
}

static inline float sseg_score(const SsegCand *c, const SsegCand *prev) {
    float s = 0.45f;                                 /* 单字：只是字 */
    int one = (c->end - c->start == 1);
    if (c->tok)
        s = one ? 0.50f : 1.20f + 0.35f * logf(1.0f + (float)c->tok->count);
    if (prev && prev->tok && c->tok && sseg_edge(prev->tok, c->tok))
        s += one ? 0.15f : 0.60f;                    /* 词与词相连才算强证据 */
    return s;
}

/* DP：返回最优路的候选下标（-1 结束），写进 path[]；ban 用于算次优 */
static inline int sseg_dp(AI *ai, SsegCand *cs, int n, int nch,
                          int ban, int *path, int pathcap) {
    (void)ai;
    float dp[SSEG_MAX_CH + 2];
    int prevc[SSEG_MAX_CH + 2], previ[SSEG_MAX_CH + 2];
    for (int i = 0; i <= nch; ++i) { dp[i] = -1e9f; prevc[i] = -1; previ[i] = -1; }
    dp[0] = 0;
    for (int i = 0; i < nch; ++i) {
        if (dp[i] <= -1e8f) continue;
        for (int k = 0; k < n; ++k) {
            if (cs[k].start != i || k == ban) continue;
            float v = dp[i] + sseg_score(&cs[k], prevc[i] >= 0 ? &cs[prevc[i]] : NULL);
            if (v > dp[cs[k].end] + 1e-6f) {
                dp[cs[k].end] = v;
                prevc[cs[k].end] = k;
                previ[cs[k].end] = i;
            }
        }
    }
    int m = 0, at = nch;
    while (at > 0 && prevc[at] >= 0) {
        if (m < pathcap) path[m++] = prevc[at];
        at = previ[at];
    }
    for (int i = 0; i < m / 2; ++i) { int t = path[i]; path[i] = path[m - 1 - i]; path[m - 1 - i] = t; }
    return m;
}

static inline void sseg_print_path(SsegCand *cs, const int *path, int m, float score) {
    for (int i = 0; i < m; ++i) printf("%s%s", i ? "/" : "", cs[path[i]].name);
    printf("  分数 %.2f\n", score);
}

static inline float sseg_path_score(SsegCand *cs, const int *path, int m) {
    float s = 0;
    for (int i = 0; i < m; ++i) s += sseg_score(&cs[path[i]], i ? &cs[path[i - 1]] : NULL);
    return s;
}

/* §6.965 主入口：打印候选/最优/次优/词义激活。只用图。 */
static inline void sseg_run(AI *ai, const char *text) {
    if (!ai || !ai->pool || !text || !*text) { printf("[滑动] 没句子\n"); return; }
    SsegCand cs[SSEG_MAX_CAND];
    int off[SSEG_MAX_CH + 1];
    int nch = 0;
    int n = sseg_candidates(ai, text, cs, SSEG_MAX_CAND, off, &nch);
    printf("[滑动] 句：%s（%d 字）\n", text, nch);
    printf("[候选]");
    for (int i = 0; i < n; ++i) {
        if (cs[i].end - cs[i].start == 1) continue;   /* 单字不逐条列 */
        printf(" %s(%d字%s)", cs[i].name, cs[i].end - cs[i].start,
               cs[i].tok ? "·图" : "");
    }
    printf("\n");
    int path[SSEG_MAX_CH + 2];
    int m = sseg_dp(ai, cs, n, nch, -1, path, SSEG_MAX_CH);
    if (m == 0) { printf("[切分] 没有可用候选\n"); return; }
    printf("[最优] ");
    sseg_print_path(cs, path, m, sseg_path_score(cs, path, m));
    /* 次优：禁掉最优里第一个多字词，再看会切到哪 */
    int ban = -1;
    for (int i = 0; i < m; ++i)
        if (cs[path[i]].end - cs[path[i]].start > 1) { ban = path[i]; break; }
    if (ban >= 0) {
        int p2[SSEG_MAX_CH + 2];
        int m2 = sseg_dp(ai, cs, n, nch, ban, p2, SSEG_MAX_CH);
        if (m2 > 0) { printf("[次优] "); sseg_print_path(cs, p2, m2, sseg_path_score(cs, p2, m2)); }
    }
    /* 词义激活：选中词的图上联想，按“与上下文其它选中词有没有边”排序 */
    for (int i = 0; i < m; ++i) {
        SsegCand *c = &cs[path[i]];
        Token *t = c->tok;
        if (!t || t->count == 0) continue;
        Token *seen[16];
        int ns = 0;
        printf("[语义] %s：", c->name);
        for (int round = 0; round < 6; ++round) {
            int best = -1;
            float bestv = -1;
            for (size_t k = 0; k < t->count; ++k) {
                const AssocEntry *e = &token_assocs_ro(t)[k];
                if (!e->main || !e->main->name) continue;
                int dup = 0;
                for (int q = 0; q < ns; ++q) if (seen[q] == e->main) { dup = 1; break; }
                if (dup) continue;
                int ctx = 0;
                for (int q = 0; q < m; ++q) {
                    SsegCand *o = &cs[path[q]];
                    if (o->tok && o->tok != t && o->tok != e->main &&
                        (sseg_edge(e->main, o->tok) || sseg_edge(o->tok, e->main))) ctx = 1;
                }
                float v = (ctx ? 10.0f : 0.0f) + (float)e->main->count + 0.001f * (float)e->hits;
                if (v > bestv) { bestv = v; best = (int)k; }
            }
            if (best < 0) break;
            const AssocEntry *e = &token_assocs_ro(t)[best];
            int ctx = 0;
            for (int q = 0; q < m; ++q) {
                SsegCand *o = &cs[path[q]];
                if (o->tok && o->tok != t && o->tok != e->main &&
                    (sseg_edge(e->main, o->tok) || sseg_edge(o->tok, e->main))) ctx = 1;
            }
            if (ns) printf(" ｜ ");
            printf("%s%s", e->main->name, ctx ? "（与上下文相连·激活）" : "（仅联想）");
            seen[ns++] = e->main;
        }
        printf("\n");
    }
}

#endif
