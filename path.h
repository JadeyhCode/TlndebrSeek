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
#include "units.h"

#define PATH_MAX_LEN   3
#define PATH_MAX_OUT   32
#define PATH_DEG_CAP   64
#define PATH_KEY_LEN   96

typedef struct {
    uint8_t  len;
    RelId    rel[PATH_MAX_LEN];
    uint8_t  dir[PATH_MAX_LEN];     /* 0 = 正向，1 = 反向（逆关系规范化后） */
    uint32_t end;                   /* 终点 token id */
    uint32_t end_class;             /* §7.091 终点类别（沿属于 ≤3 跳；0=无） */
    float    w;                     /* 1/len */
} PathSig;

typedef struct { PathSig p[PATH_MAX_OUT]; size_t n; } PathSet;

static inline void path_key(const PathSig *s, char *buf, size_t cap) {
    size_t o = 0;
    if (!s || !buf || !cap) return;
    /* 终点优先用**类别**（同类的实例共享路径结尾；没有类才退回 token id） */
    o += (size_t)snprintf(buf + o, cap - o, "%u", (unsigned)(s->end_class ? s->end_class : s->end));
    for (uint8_t i = 0; i < s->len && o < cap; ++i)
        o += (size_t)snprintf(buf + o, cap - o, "|%u:%u", (unsigned)s->rel[i], (unsigned)s->dir[i]);
}

/* 规范一条边：返回**规范化后的 rel** 与方向（对称 ⇒ dir=0；
 * 逆关系取 id 小的一侧：A -包含-> B 记成 A -(反向 属于)-> B，方向 1）。 */
static inline RelId path_edge_norm(AI *ai, RelId rid, uint8_t *dir) {
    *dir = 0;
    if (!ai || !rid) return rid;
    if (rel_is_sym(ai, rid)) return rid;
    RelId inv = rel_inv_of(ai, rid);
    if (inv && inv < rid) { *dir = 1; return inv; }
    return rid;
}

/* §7.091 终点类别：沿「属于」正向 BFS ≤3 跳，取最远可达（无环）；找不到返回 0。 */
static inline uint32_t path_end_class(AI *ai, Token *t, int depth) {
    if (!ai || !t || depth <= 0) return 0;
    RelId isa = rel_id_of(ai, "属于", 0);
    if (!isa) return 0;
    uint32_t best = 0;
    Token *q[32]; int qd[32]; size_t qn = 1, qh = 0;
    q[0] = t; qd[0] = 0;
    while (qh < qn && qn < 32) {
        Token *cur = q[qh]; int d = qd[qh]; qh++;
        if (d >= depth) continue;
        for (size_t i = 0; i < cur->count; ++i) {
            const AssocEntry *e = &token_assocs_ro(cur)[i];
            if (!e->main || e->nrel || !(e->rel & REL_BIT(isa))) continue;
            if (e->main == t) continue;
            if (e->main->id) best = e->main->id;
            q[qn] = e->main; qd[qn] = d + 1; qn++;
        }
    }
    return best;
}

/* 从根枚举路径（BFS 深 3、度 64、总 32），去重后返回条数。 */
static inline size_t path_enum_raw(AI *ai, Token *root, PathSet *out) {
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
            RelId nrid = path_edge_norm(ai, rid, &dir);
            Node nx = cur;
            nx.t = e->main;
            nx.rel[nx.len] = nrid;
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
        s->end_class = path_end_class(ai, q[i].t, 3);
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

/* §7.095 路径缓存：键 = (pool serial, pool epoch, root)；边写一次 epoch+1 ⇒ 全部失效。
 * 容量 64 条（每条约 32 路径）；policy `path_cache=0` 关闭（消融）。 */
#define PATH_CACHE_SLOTS 64
typedef struct {
    uint64_t serial, epoch;
    Token   *root;
    size_t   n;
    PathSig  p[PATH_MAX_OUT];
} PathCacheEnt;
static PathCacheEnt g_path_cache[PATH_CACHE_SLOTS];
static size_t g_path_cache_rr;

static inline size_t path_enum(AI *ai, Token *root, PathSet *out) {
    if (!ai || !root || !out) return 0;
    long on = aip_policy_int("path_cache", 1);
    uint64_t ser = root->owner ? root->owner->serial : 0;
    uint64_t ep  = root->owner ? root->owner->epoch : 0;
    if (on) {
        for (size_t i = 0; i < PATH_CACHE_SLOTS; ++i) {
            PathCacheEnt *c = &g_path_cache[i];
            if (c->serial == ser && c->epoch == ep && c->root == root) {
                out->n = c->n;
                memcpy(out->p, c->p, c->n * sizeof c->p[0]);
                return c->n;
            }
        }
    }
    size_t n = path_enum_raw(ai, root, out);
    if (on) {
        PathCacheEnt *c = &g_path_cache[g_path_cache_rr++ % PATH_CACHE_SLOTS];
        c->serial = ser; c->epoch = ep; c->root = root; c->n = n;
        memcpy(c->p, out->p, n * sizeof out->p[0]);
    }
    return n;
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

/* §7.091 属性重叠：`属性` 关系 + 值/单位（units.h 归一）。 */
typedef struct { int dim; double base; char key[48]; } AttrVal;
#define PATH_ATTR_MAX 32

static inline int path_attrs(AI *ai, Token *t, AttrVal *out) {
    if (!ai || !t || !out) return 0;
    RelId rid_attr = rel_id_of(ai, "属性", 0);
    if (!rid_attr) return 0;
    int n = 0;
    for (size_t i = 0; i < t->count && n < PATH_ATTR_MAX; ++i) {
        const AssocEntry *e = &token_assocs_ro(t)[i];
        if (!e->main || e->nrel || edge_is_guess(e) || !e->main->name) continue;
        int hit = 0;
        if (rid_attr >= REL_DYN_BASE) hit = (e->dyn == (uint32_t)(rid_attr - REL_DYN_BASE + 1));
        else hit = (e->rel & REL_BIT(rid_attr)) != 0;
        if (!hit) continue;
        const char *nm = e->main->name;
        const char *end = NULL;
        CalcRat v = u_num(nm, &end);
        if (!v.ok || !end) continue;
        while (*end == ' ') end++;
        size_t ul = 0;
        const UnitDef *u = units_at(end, &ul);
        int dim = -1; double base = (double)v.n / (double)v.d;
        if (u) {
            dim = (int)(u - units_find(u->unit));
            if (dim < 0) dim = 0;
            CalcRat sc = u->scale, of = u->offset;
            base = (double)v.n / (double)v.d;
            if (sc.d) base = base * ((double)sc.n / (double)sc.d);
            if (of.d) base += (double)of.n / (double)of.d;
        }
        snprintf(out[n].key, sizeof out[n].key, "%d|%.9g", dim, base);
        out[n].dim = dim; out[n].base = base;
        n++;
    }
    /* 去重（同属性的重复边） */
    for (int i = 0; i < n; ++i)
        for (int j = i + 1; j < n; ++j)
            if (!strcmp(out[i].key, out[j].key)) {
                memmove(&out[j], &out[j + 1], (size_t)(n - j - 1) * sizeof out[0]);
                n--; j--;
            }
    return n;
}

static inline float path_attr_jaccard(AI *ai, Token *x, Token *y, int *has_attrs) {
    if (has_attrs) *has_attrs = 0;
    AttrVal ax[PATH_ATTR_MAX], ay[PATH_ATTR_MAX];
    int nx = path_attrs(ai, x, ax), ny = path_attrs(ai, y, ay);
    if (nx || ny) { if (has_attrs) *has_attrs = 1; }
    if (!nx || !ny) return 0.0f;
    int inter = 0;
    for (int i = 0; i < nx; ++i)
        for (int j = 0; j < ny; ++j)
            if (!strcmp(ax[i].key, ay[j].key)) { inter++; break; }
    int uni = nx + ny - inter;
    return uni > 0 ? (float)inter / (float)uni : 0.0f;
}

/* 返回相似度；*known=0 表示两边都没有路径（未知，不是 0）。 */
static inline float path_sim(AI *ai, Token *x, Token *y, int *known,
                             float *out_path, float *out_nbr, float *out_attr) {
    if (known) *known = 0;
    if (out_path) *out_path = 0;
    if (out_nbr) *out_nbr = 0;
    if (out_attr) *out_attr = 0;
    if (!ai || !x || !y) return 0.0f;
    static PathSet sa, sb;
    size_t na = path_enum(ai, x, &sa);
    size_t nb = path_enum(ai, y, &sb);
    int has_attr = 0;
    float aj = path_attr_jaccard(ai, x, y, &has_attr);
    if (!na || !nb) {
        if (!has_attr) return 0.0f;
        /* 只有属性也能比（属性关系本身就是一条路径，这里兜底） */
        if (known) *known = 1;
        if (out_attr) *out_attr = aj;
        return aip_policy_float("sim_w_attr", 0.3f) * aj;
    }
    float pj = path_jaccard(&sa, &sb);
    float nj = path_neighbor_jaccard(&sa, &sb);
    if (out_path) *out_path = pj;
    if (out_nbr) *out_nbr = nj;
    if (out_attr) *out_attr = aj;
    if (known) *known = 1;
    float wa = aip_policy_float("sim_w_attr", 0.3f);
    float wp = aip_policy_float("sim_w_path", 0.5f);
    float wn = aip_policy_float("sim_w_nbr", 0.2f);
    if (wa < 0) wa = 0;
    if (wp < 0) wp = 0;
    if (wn < 0) wn = 0;
    return wa * aj + wp * pj + wn * nj;
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
        const char *cn = NULL;
        if (s.p[i].end_class && t->owner && s.p[i].end_class < t->owner->count)
            cn = t->owner->tokens[s.p[i].end_class]->name;
        if (cn && cn[0]) printf("%s [类:%s]（w=%.2f）\n", en, cn, s.p[i].w);
        else printf("%s（w=%.2f）\n", en, s.p[i].w);
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
    float pj = 0, nj = 0, aj = 0;
    int known = 0;
    float sim = path_sim(ai, x, y, &known, &pj, &nj, &aj);
    if (!known) { printf("[相似] %s vs %s ⇒ 未知（两边都没有关系路径/属性；不是 0）\n", a, b); return 1; }
    printf("[相似] %s vs %s ⇒ %.2f（属性 %.2f / 路径 %.2f / 邻居 %.2f；w_attr=%.2f w_path=%.2f w_nbr=%.2f）\n",
           a, b, sim, aj, pj, nj, aip_policy_float("sim_w_attr", 0.3f),
           aip_policy_float("sim_w_path", 0.5f), aip_policy_float("sim_w_nbr", 0.2f));
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

/* §7.092 R5 钩子包装：返回 0..1，known=0 表示没有路径证据。 */
static inline float path_sim_hook_pct(AI *ai, const Token *a, const Token *b, int *known) {
    float pj = 0, nj = 0, aj = 0;
    return path_sim(ai, (Token *)a, (Token *)b, known, &pj, &nj, &aj);
}

/* §7.093 类比：A : B :: C : D —— 用**类型化路径同构**（≤3 跳）：
 * 取 A→B 的路径签名（关系序列+方向），在 C 的路径里找同序列、终点不同的 D；
 * 优先短路径、再按权重；没有同构路径 ⇒ 未知（不猜）。 */
static inline int analogy_cmd(AI *ai, const char *arg) {
    char a[64] = {0}, b[64] = {0}, c[64] = {0};
    if (!arg || sscanf(arg, "%63s %63s %63s", a, b, c) != 3) {
        printf("[类比] 用法：::analogy <A> <B> <C>（找 D：A:B :: C:D）\n");
        return 1;
    }
    Token *A = pool_find(ai->pool, a), *B = pool_find(ai->pool, b), *C = pool_find(ai->pool, c);
    if (!A || !B || !C) { printf("[类比] 图里没有「%s」\n", !A ? a : (!B ? b : c)); return 1; }
    /* ① 直边优先：A→B 的直接关系边，在 C 的出边里找同规范关系/方向（长度 1 的类比）。
     * 路径枚举有 top-32 截断，热门词可能把这条直边挤掉；所以直边单独走一遍。 */
    {
        RelId ar[64]; uint8_t ad[64]; size_t an = 0;
        for (size_t i = 0; i < A->count && an < 64; ++i) {
            const AssocEntry *e = &token_assocs_ro(A)[i];
            if (!e->main || e->main != B || e->nrel || edge_is_guess(e)) continue;
            RelId rid = e->dyn ? (RelId)(REL_DYN_BASE + e->dyn - 1) : 0;
            if (!rid) for (RelId r = 1; r < REL_DYN_BASE; ++r)
                if (e->rel & REL_BIT(r)) { rid = r; break; }
            if (!rid) continue;
            uint8_t dir = 0;
            ar[an] = path_edge_norm(ai, rid, &dir); ad[an++] = dir;
        }
        if (an) {
            int shown = 0;
            for (size_t i = 0; i < C->count && shown < 3; ++i) {
                const AssocEntry *e = &token_assocs_ro(C)[i];
                if (!e->main || e->nrel || edge_is_guess(e) || !e->main->name) continue;
                RelId rid = e->dyn ? (RelId)(REL_DYN_BASE + e->dyn - 1) : 0;
                if (!rid) for (RelId r = 1; r < REL_DYN_BASE; ++r)
                    if (e->rel & REL_BIT(r)) { rid = r; break; }
                if (!rid) continue;
                uint8_t dir = 0;
                RelId nrid = path_edge_norm(ai, rid, &dir);
                for (size_t k = 0; k < an; ++k)
                    if (ar[k] == nrid && ad[k] == dir) {
                        printf("[类比] %s : %s :: %s : %s（依据：同关系 %s%s）\n",
                               a, b, c, e->main->name, path_rel_name(ai, nrid),
                               dir ? "（反向）" : "");
                        shown++;
                        break;
                    }
            }
            if (shown) return 1;
        }
    }
    static PathSet sa, sc;
    size_t na = path_enum(ai, A, &sa);
    size_t nc = path_enum(ai, C, &sc);
    if (!na || !nc) {
        printf("[类比] %s 或 %s 没有可枚举路径 ⇒ 未知（不猜）\n", a, c);
        return 1;
    }
    /* 先给 A→B 的路径挑出来（按长度、权重）；再去 C 里找同序列 */
    int best_idx[64]; size_t bidx_n = 0;
    for (size_t i = 0; i < sa.n; ++i) {
        if (sa.p[i].end != B->id) continue;
        if (bidx_n < 64) best_idx[bidx_n++] = (int)i;
    }
    if (!bidx_n) { printf("[类比] %s 到 %s 没有路径 ⇒ 未知（不猜）\n", a, b); return 1; }
    for (size_t i = 0; i + 1 < bidx_n; ++i)
        for (size_t j = i + 1; j < bidx_n; ++j) {
            const PathSig *x = &sa.p[best_idx[i]], *y = &sa.p[best_idx[j]];
            int swap = (y->len < x->len) || (y->len == x->len && y->w > x->w);
            if (swap) { int t = best_idx[i]; best_idx[i] = best_idx[j]; best_idx[j] = t; }
        }
    int shown = 0;
    for (size_t k = 0; k < bidx_n && shown < 3; ++k) {
        const PathSig *pa = &sa.p[best_idx[k]];
        for (size_t i = 0; i < sc.n && shown < 3; ++i) {
            const PathSig *pc = &sc.p[i];
            if (pc->len != pa->len || pc->end == C->id) continue;
            int same = 1;
            for (uint8_t q = 0; q < pa->len; ++q)
                if (pa->rel[q] != pc->rel[q] || pa->dir[q] != pc->dir[q]) { same = 0; break; }
            if (!same) continue;
            /* 同名终点（D==B）只在没有别的候选时才用：先记下，继续找不同的 */
            uint32_t did = pc->end;
            const char *dn = (did < ai->pool->count && ai->pool->tokens[did]->name)
                                 ? ai->pool->tokens[did]->name : "?";
            if (did == B->id && bidx_n > 1) continue;
            printf("[类比] %s : %s :: %s : %s（依据：路径 ", a, b, c, dn);
            for (uint8_t q = 0; q < pa->len; ++q)
                printf("%s%s%s ", q ? "→" : "", pa->dir[q] ? "<" : "", path_rel_name(ai, pa->rel[q]));
            printf("，%u 跳）\n", (unsigned)pa->len);
            shown++;
        }
    }
    if (!shown) {
        /* 兜底：A→B 没有路径时给直边诊断（都找不到就未知） */
        printf("[类比] %s 找不到与 %s→%s 同构的路径 ⇒ 未知（不猜）\n", c, a, b);
    }
    return 1;
}

#endif /* PATH_H */
