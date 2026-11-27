/* rel_schema.h — §7.073 图原生关系层 P0：行为/角色/约束/效果的数据化 schema。
 *
 * 纯数据层：不依赖 AI/Token，可单独编译测试。
 *   rel_schema_load(path, hooks)  读 `relations_beh.txt`（一行一条 `|` 分隔）
 *   rel_schema_by_name / by_id     查行
 *   rel_schema_hook_id/inv         核心名 → id / 逆名（由 rel.h 提供，兼容 NOSCHEMA）
 *
 * 非法行**逐行报行号与原因**并拒绝，不静默。
 */
#ifndef REL_SCHEMA_H
#define REL_SCHEMA_H

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <ctype.h>

#define REL_SCHEMA_MAX      128
#define REL_SCHEMA_ROLES    4
#define REL_SCHEMA_NAME     24
#define REL_SCHEMA_CONS     64
#define REL_SCHEMA_POST     96
#define REL_SCHEMA_ATTRS    64

enum {
    RELB_TRANS      = 1u << 0,
    RELB_INHERIT    = 1u << 1,
    RELB_SYM        = 1u << 2,
    RELB_EXCL       = 1u << 3,
    RELB_PREREQ     = 1u << 4,
    RELB_MUTATES    = 1u << 5,
    RELB_TEMPORAL   = 1u << 6,
    RELB_ORDINAL    = 1u << 7,
    RELB_CAUSAL     = 1u << 8,
    RELB_DEFEASIBLE = 1u << 9,
    RELB_EQUIV      = 1u << 10   /* 只能由 sym+trans+irreflexive 推导 */
};
enum { REL_CARD_ANY = 0, REL_CARD_SINGLE = 1, REL_CARD_MULTI = 2 };
enum { REL_EV_AXIOM = 0, REL_EV_OBSERVED = 1, REL_EV_INFERRED = 2 };

typedef struct {
    uint32_t id;                     /* 0 = 动态/未绑定 */
    char     name[REL_SCHEMA_NAME];
    char     neg[REL_SCHEMA_NAME];
    char     alias[REL_SCHEMA_NAME]; /* 非空 = 别名行 */
    char     inv_name[REL_SCHEMA_NAME];
    uint32_t flags;
    uint32_t inv;                    /* 解析出的 id，0=未解析 */
    uint32_t dim;
    uint8_t  card;
    uint8_t  evidence;
    uint8_t  n_roles;
    char     roles[REL_SCHEMA_ROLES][REL_SCHEMA_NAME];
    char     cons[REL_SCHEMA_ROLES][REL_SCHEMA_CONS];
    char     post[REL_SCHEMA_ROLES][REL_SCHEMA_POST];
    char     attrs[REL_SCHEMA_ATTRS];
    int      line;
    int      illegal;
} RelSchema;

typedef struct {
    uint8_t     (*id_of)(const char *name);      /* 核心关系名 → id（无则 0） */
    const char *(*inv_of_name)(const char *name);/* 核心关系名 → 逆关系名（无则 NULL） */
} RelSchemaHooks;

static RelSchema g_rs[REL_SCHEMA_MAX];
static int       g_rs_n;
static int       g_rs_ok;
static int       g_rs_illegal;
static int       g_rs_active;
static int       g_rs_loaded;
static size_t    g_rs_hits, g_rs_misses;

static inline void rel_schema_trim(char *s) {
    if (!s) return;
    char *p = s;
    while (*p == ' ' || *p == '\t') p++;
    if (p != s) memmove(s, p, strlen(p) + 1);
    size_t n = strlen(s);
    while (n && (s[n-1] == ' ' || s[n-1] == '\t' || s[n-1] == '\r' || s[n-1] == '\n')) s[--n] = 0;
}

static inline const char *rel_schema_flag_name(uint32_t bit) {
    switch (bit) {
    case RELB_TRANS: return "trans";
    case RELB_INHERIT: return "inherit";
    case RELB_SYM: return "sym";
    case RELB_EXCL: return "excl";
    case RELB_PREREQ: return "prereq";
    case RELB_MUTATES: return "mutates";
    case RELB_TEMPORAL: return "temporal";
    case RELB_ORDINAL: return "ordinal";
    case RELB_CAUSAL: return "causal";
    case RELB_DEFEASIBLE: return "defeasible";
    case RELB_EQUIV: return "equiv";
    default: return "?";
    }
}

static inline int rel_schema_cmp(const void *a, const void *b) {
    const RelSchema *x = (const RelSchema *)a, *y = (const RelSchema *)b;
    return strcmp(x->name, y->name);
}

static inline RelSchema *rel_schema_by_name_mut(const char *name) {
    if (!name || !g_rs_active) return NULL;
    for (int i = 0; i < g_rs_n; ++i)
        if (!g_rs[i].illegal && !g_rs[i].alias[0] && !strcmp(g_rs[i].name, name)) return &g_rs[i];
    return NULL;
}
static inline const RelSchema *rel_schema_by_name(const char *name) {
    RelSchema *s = rel_schema_by_name_mut(name);
    if (s) g_rs_hits++; else g_rs_misses++;
    return s;
}
static inline const RelSchema *rel_schema_by_id(uint32_t id) {
    if (!g_rs_active || !id) return NULL;
    for (int i = 0; i < g_rs_n; ++i)
        if (!g_rs[i].illegal && g_rs[i].id == id) { g_rs_hits++; return &g_rs[i]; }
    g_rs_misses++;
    return NULL;
}
static inline size_t rel_schema_count(void) { return (size_t)g_rs_n; }
static inline const RelSchema *rel_schema_at(size_t i) { return i < (size_t)g_rs_n ? &g_rs[i] : NULL; }
static inline int rel_schema_active(void) { return g_rs_active; }
static inline int rel_schema_loaded(void) { return g_rs_loaded; }
static inline int rel_schema_illegal_count(void) { return g_rs_illegal; }
static inline size_t rel_schema_hits(void) { return g_rs_hits; }
static inline size_t rel_schema_misses(void) { return g_rs_misses; }

static inline void rel_schema_err(const char *path, int line, const char *why) {
    printf("[关系schema] %s:%d 非法：%s\n", path ? path : "?", line, why);
    g_rs_illegal++;
}

/* 解析一行；返回 1 成功。 */
static inline int rel_schema_parse_line(const char *path, int line, char *row, const RelSchemaHooks *hk) {
    RelSchema s;
    memset(&s, 0, sizeof s);
    s.line = line;
    s.card = REL_CARD_ANY;
    s.evidence = REL_EV_OBSERVED;

    char *fields[10]; int nf = 0;
    {
        char *f = row;
        while (f && nf < 10) {
            char *bar = strchr(f, '|');
            if (bar) *bar = 0;
            rel_schema_trim(f);
            if (*f) fields[nf++] = f;
            f = bar ? bar + 1 : NULL;
        }
    }
    if (nf == 0) return 0;
    snprintf(s.name, sizeof s.name, "%s", fields[0]);
    if (!s.name[0]) { rel_schema_err(path, line, "名字为空"); return 0; }

    int alias = 0;
    for (int k = 1; k < nf; ++k) {
        char *tok = fields[k];
        char *eq = strchr(tok, '=');
        if (eq) {
            *eq = 0;
            char *key = tok; char *val = eq + 1;
            rel_schema_trim(key); rel_schema_trim(val);
            if (!strcmp(key, "alias")) {
                snprintf(s.alias, sizeof s.alias, "%s", val);
                alias = 1;
            } else if (!strcmp(key, "inv")) {
                snprintf(s.inv_name, sizeof s.inv_name, "%s", val);
            } else if (!strcmp(key, "roles")) {
                char *r = val;
                while (r && s.n_roles < REL_SCHEMA_ROLES) {
                    char *comma = strchr(r, ',');
                    if (comma) *comma = 0;
                    rel_schema_trim(r);
                    if (*r) snprintf(s.roles[s.n_roles++], REL_SCHEMA_NAME, "%s", r);
                    r = comma ? comma + 1 : NULL;
                }
            } else if (!strcmp(key, "cons")) {
                char *r = val; int ci = 0;
                while (r && ci < REL_SCHEMA_ROLES) {
                    char *comma = strchr(r, ',');
                    if (comma) *comma = 0;
                    rel_schema_trim(r);
                    if (*r) snprintf(s.cons[ci++], REL_SCHEMA_CONS, "%s", r);
                    r = comma ? comma + 1 : NULL;
                }
            } else if (!strcmp(key, "post")) {
                char *r = val; int pi = 0;
                while (r && pi < REL_SCHEMA_ROLES) {
                    char *comma = strchr(r, ',');
                    if (comma) *comma = 0;
                    rel_schema_trim(r);
                    if (*r) snprintf(s.post[pi++], REL_SCHEMA_POST, "%s", r);
                    r = comma ? comma + 1 : NULL;
                }
            } else if (!strcmp(key, "card")) {
                if (!strcmp(val, "single")) s.card = REL_CARD_SINGLE;
                else if (!strcmp(val, "multi")) s.card = REL_CARD_MULTI;
                else if (!strcmp(val, "any")) s.card = REL_CARD_ANY;
                else { rel_schema_err(path, line, "card 只认 single|multi|any"); return 0; }
                if (s.card == REL_CARD_SINGLE) s.flags |= RELB_EXCL;
            } else if (!strcmp(key, "evidence")) {
                if (!strcmp(val, "axiom")) s.evidence = REL_EV_AXIOM;
                else if (!strcmp(val, "observed")) s.evidence = REL_EV_OBSERVED;
                else if (!strcmp(val, "inferred")) s.evidence = REL_EV_INFERRED;
                else { rel_schema_err(path, line, "evidence 只认 axiom|observed|inferred"); return 0; }
            } else if (!strcmp(key, "dim")) {
                s.dim = (uint32_t)strtoul(val, NULL, 10);
                if (s.dim != 0) { rel_schema_err(path, line, "dim 未注册（P0 只允许 dim=0；P1 才开放量纲）"); return 0; }
            } else if (!strcmp(key, "neg")) {
                snprintf(s.neg, sizeof s.neg, "%s", val);
            } else {
                rel_schema_err(path, line, "不认识的键（只认 alias/inv/roles/cons/post/card/evidence/dim/neg）");
                return 0;
            }
            continue;
        }
        int tok_bad = 0;
        char *p2 = tok;
        while (p2 && *p2 && !tok_bad) {
            char *comma = strchr(p2, ',');
            if (comma) *comma = 0;
            rel_schema_trim(p2);
            if (*p2) {
                if (!strcmp(p2, "single") || !strcmp(p2, "multi") || !strcmp(p2, "any")) {
                    s.card = !strcmp(p2, "single") ? REL_CARD_SINGLE
                           : !strcmp(p2, "multi") ? REL_CARD_MULTI : REL_CARD_ANY;
                    if (s.card == REL_CARD_SINGLE) s.flags |= RELB_EXCL;
                } else {
                    uint32_t bit = 0;
                    if (!strcmp(p2, "trans")) bit = RELB_TRANS;
                    else if (!strcmp(p2, "inherit")) bit = RELB_INHERIT;
                    else if (!strcmp(p2, "sym")) bit = RELB_SYM;
                    else if (!strcmp(p2, "excl")) bit = RELB_EXCL;
                    else if (!strcmp(p2, "prereq")) bit = RELB_PREREQ;
                    else if (!strcmp(p2, "mutates")) bit = RELB_MUTATES;
                    else if (!strcmp(p2, "temporal")) bit = RELB_TEMPORAL;
                    else if (!strcmp(p2, "ordinal")) bit = RELB_ORDINAL;
                    else if (!strcmp(p2, "causal")) bit = RELB_CAUSAL;
                    else if (!strcmp(p2, "defeasible")) bit = RELB_DEFEASIBLE;
                    else if (!strcmp(p2, "functional")) {
                        s.flags |= RELB_EXCL;
                        if (s.card == REL_CARD_MULTI) tok_bad = 1;
                    } else if (!strcmp(p2, "anti-trans") || !strcmp(p2, "dir") ||
                               !strcmp(p2, "non-trans") || !strcmp(p2, "subclass") ||
                               !strcmp(p2, "irreflexive")) {
                        size_t al = strlen(s.attrs);
                        snprintf(s.attrs + al, sizeof s.attrs - al, "%s%s", al ? "," : "", p2);
                    } else {
                        tok_bad = 1;
                    }
                    if (bit) {
                        if (bit == RELB_TRANS && strstr(s.attrs, "anti-trans")) tok_bad = 1;
                        s.flags |= bit;
                    }
                }
            }
            p2 = comma ? comma + 1 : NULL;
        }
        if (tok_bad) { rel_schema_err(path, line, "不认识的标志/注解或冲突（trans+anti-trans 等）"); return 0; }
        continue;
    }

    if (alias) {
        if (s.flags || s.n_roles || s.inv_name[0]) { rel_schema_err(path, line, "alias 行不能再带 flags/roles/inv"); return 0; }
        s.id = 0;
    } else {
        if (!s.flags && s.card == REL_CARD_ANY && s.n_roles == 0) {
            /* 允许“只有角色”的最小行，但完全空的第二段没有意义 */
        }
        /* 语义冲突检查 */
        if ((s.flags & RELB_CAUSAL) && (s.flags & RELB_SYM)) { rel_schema_err(path, line, "causal+sym 不能同时声明"); return 0; }
        if ((s.flags & RELB_CAUSAL) && (s.flags & RELB_TRANS) == 0 && 0) { }
        if (s.card == REL_CARD_MULTI && (s.flags & RELB_EXCL)) { rel_schema_err(path, line, "functional+multi 不能同时声明"); return 0; }
        if (strstr(s.attrs, "anti-trans") && (s.flags & RELB_TRANS)) { rel_schema_err(path, line, "trans+anti-trans 不能同时声明"); return 0; }
        if ((s.flags & RELB_SYM) && (s.flags & RELB_TRANS) && strstr(s.attrs, "irreflexive"))
            s.flags |= RELB_EQUIV;
    }

    /* 名字与别名重复检查 */
    for (int i = 0; i < g_rs_n; ++i) {
        if (!strcmp(g_rs[i].name, s.name)) {
            rel_schema_err(path, line, "同名关系重复声明"); return 0;
        }
        if (s.alias[0] && !strcmp(g_rs[i].alias, s.alias) && 0) { }
    }
    if (s.alias[0] && !strcmp(s.alias, s.name)) { rel_schema_err(path, line, "alias 指向自己"); return 0; }

    if (!alias && hk && hk->id_of) s.id = hk->id_of(s.name);
    g_rs[g_rs_n++] = s;
    g_rs_ok++;
    return 1;
}

static inline size_t rel_schema_load(const char *path, const RelSchemaHooks *hk) {
    g_rs_n = 0; g_rs_ok = 0; g_rs_illegal = 0; g_rs_active = 0; g_rs_loaded = 1;
    g_rs_hits = g_rs_misses = 0;
    const char *off = getenv("AIP_NOSCHEMA");
    if (off && off[0] == '1') {
        printf("[关系schema] AIP_NOSCHEMA=1 ⇒ 不装载，回退 AI_RELS（消融模式）\n");
        return 0;
    }
    FILE *f = path ? fopen(path, "r") : NULL;
    if (!f) {
        printf("[关系schema] 没有 %s ⇒ 回退 AI_RELS\n", path ? path : "?");
        return 0;
    }
    char line[512];
    int ln = 0;
    while (fgets(line, sizeof line, f)) {
        ln++;
        size_t n = strlen(line);
        while (n && (line[n-1] == '\n' || line[n-1] == '\r')) line[--n] = 0;
        char *p = line;
        while (*p == ' ' || *p == '\t') p++;
        if (!*p || *p == '#') continue;
        char *h = strchr(p, '#');
        if (h && (h == p || h[-1] == ' ' || h[-1] == '\t')) { while (h > p && (h[-1] == ' ' || h[-1] == '\t')) h--; *h = 0; }
        if (!*p) continue;
        rel_schema_parse_line(path, ln, p, hk);
    }
    fclose(f);

    /* 跨行检查：inv 必须互相指向；alias 必须指向已有行或核心 */
    for (int i = 0; i < g_rs_n; ++i) {
        RelSchema *s = &g_rs[i];
        if (s->illegal || !s->inv_name[0]) continue;
        RelSchema *t = rel_schema_by_name_mut(s->inv_name);
        if (t) {
            if (s->id && t->id) s->inv = t->id;
            if (strcmp(t->inv_name, s->name) != 0) {
                printf("[关系schema] %s:%d 非法：inv=%s 没有反向指向（%s 的 inv=%s）\n",
                       path, s->line, s->inv_name, t->name, t->inv_name[0] ? t->inv_name : "（空）");
                s->illegal = 1;
                g_rs_illegal++;
            }
        } else if (hk && hk->id_of) {
            uint8_t cid = hk->id_of(s->inv_name);
            const char *cinv = hk->inv_of_name ? hk->inv_of_name(s->inv_name) : NULL;
            if (!cid) {
                printf("[关系schema] %s:%d 非法：inv=%s 既不在文件里也不是核心关系\n", path, s->line, s->inv_name);
                s->illegal = 1; g_rs_illegal++;
            } else if (!cinv || strcmp(cinv, s->name) != 0) {
                printf("[关系schema] %s:%d 非法：inv=%s 没有反向指向（核心声明的是 %s）\n",
                       path, s->line, s->inv_name, cinv ? cinv : "（无）");
                s->illegal = 1; g_rs_illegal++;
            } else if (s->id) {
                s->inv = cid;
            }
        }
    }
    for (int i = 0; i < g_rs_n; ++i) {
        RelSchema *s = &g_rs[i];
        if (s->illegal || !s->alias[0]) continue;
        if (rel_schema_by_name_mut(s->alias) || (hk && hk->id_of && hk->id_of(s->alias))) continue;
        printf("[关系schema] %s:%d 非法：alias=%s 目标不存在\n", path, s->line, s->alias);
        s->illegal = 1; g_rs_illegal++;
    }
    int valid = 0;
    for (int i = 0; i < g_rs_n; ++i) if (!g_rs[i].illegal) valid++;
    g_rs_active = valid > 0;
    printf("[关系schema] 有效 %d 条，非法 %d 行，%s\n",
           valid, g_rs_illegal,
           g_rs_active ? "推理读 schema" : "回退 AI_RELS");
    return (size_t)valid;
}

#endif /* REL_SCHEMA_H */
