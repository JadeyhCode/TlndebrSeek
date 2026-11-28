/* path.h — §7.090 P4/新目标核心：**类型化路径签名**的点对相似（不引入稠密向量）。
 *
 * 路径：从词出发、长度 ≤3、每节点度截断 64、保留 top-32；每条记
 *   (关系序列, 方向序列, 终点)，w = 1/len。
 * 规范化：逆关系翻转方向并换成 id 较小的一侧；对称关系不计方向。
 * 相似：path_match = 加权 Jaccard（关系序列+方向+终点）；neighbor = 一跳集合 Jaccard；
 *   sim = w_path*path_match + w_nbr*neighbor；无路径 ⇒ **unknown**（不是 0）。
 * 权重/模式进 policy：`sim_w_path`、`sim_w_nbr`、`sim_mode=path|emb`。
 * ⚠ 禁止把语言统计写成边/向量；这里只读图里已有的关系边。
 */
#ifndef PATH_H
#define PATH_H

#include <stdio.h>
#include <string.h>
#include <math.h>

#define PATH_MAX_LEN   3
#define PATH_MAX_OUT   32
#define PATH_DEG_CAP   64
#define PATH_KEY_LEN   96

typedef struct {
    uint8_t  len;
    RelId    rel[PATH_MAX_LEN];
    uint8_t  dir[PATH_MAX_LEN];     /* 0 = 正向，1 = 反向（逆关系规范化后） */
    uint32_t end;                   /* 终点 token id */
    float    w;                     /* 1/len */
} PathSig;

typedef struct { PathSig p[PATH_MAX_OUT]; size_t n; } PathSet;

static inline void path_key(const PathSig *s, char *buf, size_t cap) {
    size_t o = 0;
    if (!s || !buf || !cap) return;
    o += (size_t)snprintf(buf + o, cap - o, "%u", (unsigned)s->end);
    for (uint8_t i = 0; i < s->len && o < cap; ++i)
        o += (size_t)snprintf(buf + o, cap - o, "|%u:%u", (unsigned)s->rel[i], (unsigned)s->dir[i]);
}

/* 规范一条边：返回 rel/dir（对称 ⇒ dir=0；否则逆关系取 id 小的一侧、方向翻转）。 */
static inline void path_edge_norm(AI *ai, RelId rid, uint8_t *dir) {
    *dir = 0;
    if (!ai || !rid) return;
    if (rel_is_sym(ai, rid)) return;
    RelId inv = rel_inv_of(ai, rid);
    if (inv && inv < rid) *dir = 1;
}

/* 从根枚举路径（BFS 深 3、度 64、总 32），去重后返回条数。 */
static inline size_t path_enum(AI *ai, Token *root, PathSet *out) {
    if (!ai || !root || !out) return 0;
    out->n = 0;
    typedef struct { Token *t; uint8_t len; RelId rel[PATH_MAX_LEN]; uint8_t dir[PATH_MAX_LEN]; } Node;
    static Node q[PATH_MAX_OUT * PATH_DEG_CAP];
    size_t qn = 0, qh = 0;
    q[qn].t = root; q[qn].len = 0; qn++;
    char seen[PATH_MAX_OUT][PATH_KEY_LEN];
    size_t nseen = 0;
    while (qh < qn && qn < sizeof q / sizeof q[0]) {
        Node cur = q[qh++];
        if (cur.len >= PATH_MAX_LEN) continue;
        size_t deg = 0;
        for (size_t i = 0; i < cur.t->count && deg < PATH_DEG_CAP; ++i) {
            const AssocEntry *e = &token_assocs_ro(cur.t)[i];
            if (!e->main || edge_dyn_neg(e)) continue;
            if (edge_is_guess(e)) continue;
            RelId rid = 0;
            if (e->dyn) rid = (RelId)(REL_DYN_BASE + e->dyn - 1);
            else for (RelId r = 1; r < REL_DYN_BASE; ++r)
                if (e->rel & REL_BIT(r)) { rid = r; break; }
            if (!rid) continue;
            uint8_t dir = 0;
            path_edge_norm(ai, rid, &dir);
            Node nx = cur;
            nx.t = e->main;
            nx.rel[nx.len] = rid;
            nx.dir[nx.len] = dir;
            nx.len = (uint8_t)(cur.len + 1);
            q[qn++] = nx;
            deg++;
        }
    }
    for (size_t i = 1; i < qn && out->n < PATH_MAX_OUT; ++i) {
        PathSig *s = &out->p[out->n];
        memset(s, 0, sizeof *s);
        s->len = q[i].len;
        for (uint8_t k = 0; k < s->len; ++k) { s->rel[k] = q[i].rel[k]; s->dir[k] = q[i].dir[k]; }
        s->end = q[i].t->id;
        s->w = 1.0f / (float)s->len;
        char key[PATH_KEY_LEN];
        path_key(s, key, sizeof key);
        int dup = 0;
        for (size_t j = 0; j < nseen; ++j) if (!strcmp(seen[j], key)) { dup = 1; break; }
        if (dup) continue;
        if (nseen < PATH_MAX_OUT) snprintf(seen[nseen++], PATH_KEY_LEN, "%s", key);
        out->n++;
    }
    return out->n;
}

static inline int path_find(const PathSet *s, const char *key) {
    for (size_t i = 0; i < s->n; ++i) {
        char kb[PATH_KEY_LEN];
        path_key(&s->p[i], kb, sizeof kb);
        if (!strcmp(kb, key)) return (int)i;
    }
    return -1;
}

/* 加权 Jaccard：匹配路径权重和 / 并集权重和。 */
static inline float path_jaccard(const PathSet *a, const PathSet *b) {
    float inter = 0, uni = 0;
    for (size_t i = 0; i < a->n; ++i) {
        char k[PATH_KEY_LEN]; path_key(&a->p[i], k, sizeof k);
        uni += a->p[i].w;
        if (path_find(b, k) >= 0) inter += a->p[i].w;
    }
    for (size_t i = 0; i < b->n; ++i) {
        char k[PATH_KEY_LEN]; path_key(&b->p[i], k, sizeof k);
        if (path_find(a, k) < 0) uni += b->p[i].w;
    }
    return uni > 0 ? inter / uni : 0.0f;
}

/* 只取一跳集合做邻居 Jaccard（避免与 path 完全重复）。 */
static inline float path_neighbor_jaccard(const PathSet *a, const PathSet *b) {
    PathSet na = {0}, nb = {0};
    for (size_t i = 0; i < a->n && na.n < PATH_MAX_OUT; ++i)
        if (a->p[i].len == 1) na.p[na.n++] = a->p[i];
    for (size_t i = 0; i < b->n && nb.n < PATH_MAX_OUT; ++i)
        if (b->p[i].len == 1) nb.p[nb.n++] = b->p[i];
    if (!na.n && !nb.n) return 0.0f;
    return path_jaccard(&na, &nb);
}

/* 返回相似度；*known=0 表示两边都没有路径（未知，不是 0）。 */
static inline float path_sim(AI *ai, Token *x, Token *y, int *known,
                             float *out_path, float *out_nbr) {
    if (known) *known = 0;
    if (out_path) *out_path = 0;
    if (out_nbr) *out_nbr = 0;
    if (!ai || !x || !y) return 0.0f;
    static PathSet sa, sb;
    size_t na = path_enum(ai, x, &sa);
    size_t nb = path_enum(ai, y, &sb);
    if (!na || !nb) return 0.0f;
    float pj = path_jaccard(&sa, &sb);
    float nj = path_neighbor_jaccard(&sa, &sb);
    if (out_path) *out_path = pj;
    if (out_nbr) *out_nbr = nj;
    if (known) *known = 1;
    float wp = aip_policy_float("sim_w_path", 0.7f);
    float wn = aip_policy_float("sim_w_nbr", 0.3f);
    if (wp < 0) wp = 0;
    if (wn < 0) wn = 0;
    return wp * pj + wn * nj;
}

static inline const char *path_rel_name(AI *ai, RelId rid) {
    const char *n = rel_name_of(ai, rid);
    return n ? n : "?";
}

static inline void path_print(AI *ai, Token *t, int max) {
    if (!t) return;
    PathSet s;
    size_t n = path_enum(ai, t, &s);
    printf("[路径] %s 的类型化路径 %zu 条（长度≤3、度≤%d、top-%d）：\n",
           t->name ? t->name : "?", n, PATH_DEG_CAP, PATH_MAX_OUT);
    for (size_t i = 0; i < n && (int)i < max; ++i) {
        printf("  %zu) ", i + 1);
        for (uint8_t k = 0; k < s.p[i].len; ++k)
            printf("%s-%s-> ", s.p[i].dir[k] ? "<" : "",
                   path_rel_name(ai, s.p[i].rel[k]));
        uint32_t eid = s.p[i].end;
        const char *en = "?";
        if (t->owner && eid < t->owner->count && t->owner->tokens[eid]->name)
            en = t->owner->tokens[eid]->name;
        printf("%s（w=%.2f）\n", en, s.p[i].w);
    }
    if (!n) printf("  （没有可枚举的关系路径）\n");
}

static inline int path_sim_cmd(AI *ai, const char *arg) {
    char a[64] = {0}, b[64] = {0};
    if (!arg || sscanf(arg, "%63s %63s", a, b) != 2) {
        printf("[相似] 用法：::pathsim <词A> <词B>（只读；无路径 ⇒ 未知）\n");
        return 1;
    }
    char mbuf[32] = {0};
    (void)aip_policy_str("sim_mode", mbuf, sizeof mbuf);
    const char *mode = mbuf[0] ? mbuf : "path";
    if (!strcmp(mode, "emb")) {
        printf("[相似] sim_mode=emb 未启用：本项目**禁止**稠密向量进核（用 path 模式）\n");
        return 1;
    }
    Token *x = pool_find(ai->pool, a), *y = pool_find(ai->pool, b);
    if (!x || !y) { printf("[相似] 图里没有「%s」或「%s」\n", !x ? a : b, !x ? b : a); return 1; }
    float pj = 0, nj = 0;
    int known = 0;
    float sim = path_sim(ai, x, y, &known, &pj, &nj);
    if (!known) { printf("[相似] %s vs %s ⇒ 未知（至少一边没有关系路径；不是 0）\n", a, b); return 1; }
    printf("[相似] %s vs %s ⇒ %.2f（路径 %.2f / 邻居 %.2f；w_path=%.2f w_nbr=%.2f）\n",
           a, b, sim, pj, nj, aip_policy_float("sim_w_path", 0.7f),
           aip_policy_float("sim_w_nbr", 0.3f));
    /* top-3 共享证据 */
    static PathSet sa, sb;
    path_enum(ai, x, &sa); path_enum(ai, y, &sb);
    int shown = 0;
    for (size_t i = 0; i < sa.n && shown < 3; ++i) {
        char k[PATH_KEY_LEN]; path_key(&sa.p[i], k, sizeof k);
        int j = path_find(&sb, k);
        if (j < 0) continue;
        printf("  证据: ");
        for (uint8_t q = 0; q < sa.p[i].len; ++q)
            printf("%s-%s-> ", sa.p[i].dir[q] ? "<" : "", path_rel_name(ai, sa.p[i].rel[q]));
        const char *en = "?";
        if (x->owner && sa.p[i].end < x->owner->count && x->owner->tokens[sa.p[i].end]->name)
            en = x->owner->tokens[sa.p[i].end]->name;
        printf("%s\n", en);
        shown++;
    }
    if (!shown) printf("  证据: （没有完全相同的路径；分数来自邻居重叠）\n");
    return 1;
}

#endif /* PATH_H */
