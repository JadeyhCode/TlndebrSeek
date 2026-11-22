#ifndef SYMTOOL_H
#define SYMTOOL_H
/* symtool.h — §6.988 自省/自修改工具 `::sym`
 *
 * 设计约束（照用户要求）：
 *   · **默认只读**：任何写操作都要先 `::sym write on`（或 AIP_SYM_WRITE=1）；
 *   · 写入走**已有通道**：ai_write_rel（关系层写入）+ agent_teach_mark（留痕），
 *     不另开写图后门；写完跑 ai_check_ok 报告不变式；
 *   · 所有“重命名/合并”用**搬边**实现（不偷改名字哈希）：新名字 intern → 搬出边+入边 → 旧符号标垃圾；
 *   · 反查表只追加（陈旧项由 rel_direct 过滤），删边只删正向 assoc。
 */

/* §6.993 输出重定向：默认 stdout；模型调用工具时切到临时文件，把结果当答复返回。 */
static FILE *g_sym_out = NULL;
static inline FILE *sym_out(void) { return g_sym_out ? g_sym_out : stdout; }
static inline void sym_printf(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vfprintf(sym_out(), fmt, ap);
    va_end(ap);
}
static inline void sym_putc(int ch) { fputc(ch, sym_out()); }
static inline void sym_puts(const char *s) { fputs(s ? s : "", sym_out()); }

/* §6.993 工具调用账本（借鉴 路线C runtime/gates.py 的“来源 + 限额 + 判定”三件套）：
 *   · 来源白名单 operator/self/test；未知来源拒绝；
 *   · 模型（self）发起的**写操作**必须先由人打开写入门，且受总写次数限额（默认 50，AIP_TOOLWRITE_LIMIT）；
 *   · 每次调用记一条判定（allow/reject_*），`::sym gate` 查看最近 10 条与违规计数；
 *   · 账本有界（256 条），不随对话无限长。 */
#define TOOL_LEDGER_MAX 256
typedef struct { char owner[12]; char name[40]; char verdict[24]; } ToolLedgerRec;
static ToolLedgerRec g_tool_ledger[TOOL_LEDGER_MAX];
static int g_tool_ledger_n = 0;
static int g_tool_damage = 0;
static int g_tool_writes = 0;

static inline int tool_owner_ok(const char *o) {
    return o && (!strcmp(o, "operator") || !strcmp(o, "self") || !strcmp(o, "test"));
}
static inline void tool_ledger_add(const char *owner, const char *name, const char *verdict) {
    if (g_tool_ledger_n == TOOL_LEDGER_MAX) {
        memmove(&g_tool_ledger[0], &g_tool_ledger[1], sizeof g_tool_ledger[0] * (TOOL_LEDGER_MAX - 1));
        g_tool_ledger_n--;
    }
    ToolLedgerRec *r = &g_tool_ledger[g_tool_ledger_n++];
    snprintf(r->owner, sizeof r->owner, "%s", owner ? owner : "?");
    snprintf(r->name, sizeof r->name, "%s", name ? name : "");
    snprintf(r->verdict, sizeof r->verdict, "%s", verdict ? verdict : "");
}
static inline int tool_is_write(const char *sub) {
    return sub && (!strcmp(sub, "add") || !strcmp(sub, "del") || !strcmp(sub, "rename") ||
                   !strcmp(sub, "merge") || !strcmp(sub, "undo") || !strcmp(sub, "edge") ||
                   !strcmp(sub, "write") || !strcmp(sub, "dry"));
}
static inline void tool_gate_report(void) {
    long lim_now = getenv("AIP_TOOLWRITE_LIMIT") ? atol(getenv("AIP_TOOLWRITE_LIMIT"))
                                                 : aip_policy_int("toolwrite_limit", 50);
    sym_printf("[工具网关] 记录 %d 条，违规 %d 次，模型已写 %d 次（限额 %ld，来自 policy.txt/环境变量）\n",
               g_tool_ledger_n, g_tool_damage, g_tool_writes, lim_now);
    int from = g_tool_ledger_n > 10 ? g_tool_ledger_n - 10 : 0;
    for (int i = from; i < g_tool_ledger_n; ++i)
        sym_printf("  %-8s %-24s %s\n", g_tool_ledger[i].owner, g_tool_ledger[i].name, g_tool_ledger[i].verdict);
}

static int g_sym_write = 0;   /* 进程内开关：::sym write on */
static char g_sym_reason[192]; /* §6.991 下一条写操作的理由（::sym reason …） */
static int g_sym_dry = 0;      /* §6.992 只预览不写：::sym dry … */

static inline void sym_log_append(const char *op, const char *a, const char *r, const char *b) {
    mkdir("_t", 0755);
    FILE *f = fopen("_t/sym_log.tsv", "ab");
    if (!f) return;
    fprintf(f, "%s\t%s\t%s\t%s\t%s\n", op, a ? a : "", r ? r : "", b ? b : "",
            g_sym_reason[0] ? g_sym_reason : "（未给理由）");
    fclose(f);
}

static inline void sym_cmd_log(int n) {
    if (n <= 0) n = 10;
    FILE *f = fopen("_t/sym_log.tsv", "rb");
    if (!f) { sym_printf("[符号日志] 还没有写操作记录（_t/sym_log.tsv）\n"); return; }
    char lines[64][512];
    size_t nl = 0;
    char buf[512];
    while (fgets(buf, sizeof buf, f)) {
        size_t l = strlen(buf);
        while (l && (buf[l-1] == '\n' || buf[l-1] == '\r')) buf[--l] = 0;
        snprintf(lines[nl % 64], sizeof lines[0], "%s", buf);
        nl++;
    }
    fclose(f);
    size_t start = nl > 64 ? nl - 64 : 0;
    size_t total = nl - start;
    size_t from = total > (size_t)n ? total - (size_t)n : 0;
    sym_printf("[符号日志] 最近 %zu 条（共 %zu，_t/sym_log.tsv）：\n", total - from, nl);
    for (size_t i = from; i < total; ++i)
        sym_printf("  %s\n", lines[(start + i) % 64]);
}

static inline const char *sym_state(const Token *t) {
    if (!t) return "?";
    if (t->is_garbage) return "垃圾";
    switch (t->mem_state) {
    case MEM_ACTIVE: return "活跃";
    case MEM_FADING: return "淡化";
    case MEM_DORMANT:return "休眠";
    case MEM_FORGOTTEN: return "遗忘";
    default: return "?";
    }
}

/* 一条边的关系名（静态关系按位，动态关系按 dyn）：返回 rid，neg 回填 */
static inline uint8_t sym_assoc_rid(AI *ai, const AssocEntry *e, int *neg) {
    (void)ai;
    if (neg) *neg = 0;
    if (!e) return 0;
    for (size_t k = 0; AI_RELS[k].name; ++k) {
        uint8_t id = AI_RELS[k].id;
        if (!id) continue;
        uint16_t bit = (uint16_t)(1u << (id - 1));
        if ((e->rel & bit) || (e->nrel & bit)) {
            if (neg) *neg = (e->nrel & bit) ? 1 : 0;
            return id;
        }
    }
    if (e->dyn) return (uint8_t)(REL_DYN_BASE + e->dyn - 1);
    return 0;
}

static inline void sym_print_edge(AI *ai, const AssocEntry *e, const char *other) {
    int neg = 0;
    uint8_t rid = sym_assoc_rid(ai, e, &neg);
    const char *rn = rid ? rel_name_of(ai, rid) : "共现";
    const char *role = (e->role == ASSOC_ROLE_DERIVED) ? "推论"
                     : (e->role == ASSOC_ROLE_INNATE) ? "基准" : "观测";
    sym_printf("  %s%s%s -> %s  （hits %u，%s%s）\n", neg ? "不 " : "", rn ? rn : "?",
           neg ? "" : "", other, e->hits, role,
           e->action && e->action->name ? "，带动作槽" : "");
}

/* §6.990 JSON 输出：名字里的引号/反斜杠转义；UTF-8 原样输出 */
static inline void sym_json_str(const char *s) {
    sym_putc('"');
    const unsigned char *p = (const unsigned char *)(s ? s : "");
    while (*p) {
        unsigned char ch = *p;
        if (ch == '"' || ch == '\\') { sym_putc('\\'); sym_putc(ch); p++; continue; }
        if (ch == '\n') { sym_puts("\\n"); p++; continue; }
        if (ch < 0x80) { sym_putc(ch); p++; continue; }
        /* 多字节：校验长度与续字节；坏序列输出 ?（JSON 必须是合法 UTF-8） */
        size_t need = (ch & 0xE0) == 0xC0 ? 1 : (ch & 0xF0) == 0xE0 ? 2 : (ch & 0xF8) == 0xF0 ? 3 : 0;
        int ok = need > 0;
        for (size_t k = 1; ok && k <= need; ++k)
            if ((p[k] & 0xC0) != 0x80) ok = 0;
        if (!ok) { sym_putc('?'); p++; continue; }
        for (size_t k = 0; k <= need; ++k) sym_putc(p[k]);
        p += need + 1;
    }
    sym_putc('"');
}

static inline void sym_links_json(AI *ai, Token *t) {
    sym_printf("{\"name\":"); sym_json_str(t->name);
    sym_printf(",\"id\":%u,\"degree\":%zu,\"state\":", t->id, t->count); sym_json_str(sym_state(t));
    sym_printf(",\"out\":[");
    size_t no = 0;
    for (size_t i = 0; i < t->count; ++i) {
        AssocEntry *e = &token_assocs(t)[i];
        if (!e->main || !e->main->name) continue;
        int neg = 0;
        uint8_t rid = sym_assoc_rid(NULL, e, &neg);
        const char *rn = rid ? rel_name_of(ai, rid) : "共现";
        const char *role = (e->role == ASSOC_ROLE_DERIVED) ? "推论"
                         : (e->role == ASSOC_ROLE_INNATE) ? "基准" : "观测";
        sym_printf("%s{\"rel\":", no ? "," : "");
        sym_json_str(rn ? rn : "");
        sym_printf(",\"to\":"); sym_json_str(e->main->name);
        sym_printf(",\"hits\":%u,\"neg\":%d,\"role\":", e->hits, neg);
        sym_json_str(role);
        sym_printf(",\"action\":%s}", (e->action && e->action->name) ? "true" : "false");
        no++;
    }
    sym_printf("],\"in\":[");
    size_t ni = 0;
    for (uint32_t ent = t->rev_head; ent && ni < 64; ent = ai->pool->rev_next[ent - 1]) {
        uint32_t meta = ai->pool->rev_meta[ent - 1];
        uint32_t sid = ai->pool->rev_src[ent - 1];
        if (sid >= ai->pool->count) continue;
        Token *s = ai->pool->tokens[sid];
        if (!s || s->is_garbage || !s->name) continue;
        uint8_t rid = (uint8_t)(meta & 0x7FFFu);
        const char *rn = rel_name_of(ai, rid);
        sym_printf("%s{\"from\":", ni ? "," : "");
        sym_json_str(s->name);
        sym_printf(",\"rel\":"); sym_json_str(rn ? rn : "");
        sym_printf(",\"neg\":%d}", (meta & 0x8000u) ? 1 : 0);
        ni++;
    }
    sym_printf("],\"in_count\":%zu}\n", ni);
}

static inline void sym_active_json(AI *ai, int lim) {
    if (lim <= 0) lim = 12;
    sym_printf("{\"focus\":[");
    size_t shown = 0;
    for (size_t i = 0; i < ai->focus_n && (int)shown < lim; ++i) {
        Token *t = ai->focus_ring[i];
        if (!t || t->is_garbage || !t->name) continue;
        sym_printf("%s{\"id\":%u,\"name\":", shown ? "," : "", t->id); sym_json_str(t->name);
        sym_printf(",\"weight\":%.3f,\"degree\":%zu,\"state\":", ai->focus_weight[i], t->count);
        sym_json_str(sym_state(t));
        sym_printf("}");
        shown++;
    }
    sym_printf("],\"recent\":[");
    size_t shown2 = 0;
    uint32_t best[64]; size_t nb = 0;
    for (size_t i = 0; i < ai->pool->count; ++i) {
        Token *t = ai->pool->tokens[i];
        if (!t || t->is_garbage || !t->name || t->last_touch_tick == 0) continue;
        if (nb < 64) best[nb++] = t->id;
        else {
            size_t worst = 0;
            for (size_t k = 1; k < nb; ++k)
                if (ai->pool->tokens[best[k]]->last_touch_tick < ai->pool->tokens[best[worst]]->last_touch_tick) worst = k;
            if (t->last_touch_tick > ai->pool->tokens[best[worst]]->last_touch_tick) best[worst] = t->id;
        }
    }
    while ((int)shown2 < lim) {
        size_t bi = 0; int found = 0;
        for (size_t k = 0; k < nb; ++k) {
            if (!best[k]) continue;
            if (!found || ai->pool->tokens[best[k]]->last_touch_tick >
                          ai->pool->tokens[best[bi]]->last_touch_tick) { bi = k; found = 1; }
        }
        if (!found) break;
        Token *t = ai->pool->tokens[best[bi]]; best[bi] = 0;
        int dup = 0;
        for (size_t i = 0; i < ai->focus_n; ++i) if (ai->focus_ring[i] == t) { dup = 1; break; }
        if (dup) continue;
        sym_printf("%s{\"id\":%u,\"name\":", shown2 ? "," : "", t->id); sym_json_str(t->name);
        sym_printf(",\"degree\":%zu,\"touched\":%llu,\"state\":", t->count,
               (unsigned long long)t->last_touch_tick);
        sym_json_str(sym_state(t));
        sym_printf("}");
        shown2++;
    }
    sym_printf("],\"pool\":%zu,\"focus_n\":%zu}\n", ai->pool ? ai->pool->count : 0, ai->focus_n);
}

static inline Token *sym_find(AI *ai, const char *name) {
    if (!ai || !ai->pool || !name) return NULL;
    return pool_find(ai->pool, name);
}

static inline void sym_cmd_active(AI *ai, int lim) {
    if (lim <= 0) lim = 12;
    sym_printf("[活跃符号] 焦点环 %zu 个（权重高→低），最多列 %d：\n", ai->focus_n, lim);
    size_t shown = 0;
    for (size_t i = 0; i < ai->focus_n && (int)shown < lim; ++i) {
        Token *t = ai->focus_ring[i];
        if (!t || t->is_garbage || !t->name) continue;
        sym_printf("  id=%u  %s  权重 %.2f  度 %zu  触碰 %llu  %s\n", t->id,
               t->name, ai->focus_weight[i], t->count,
               (unsigned long long)t->last_touch_tick, sym_state(t));
        shown++;
    }
    /* §6.989 「当前激活」不能只看焦点环（刚启动是空的）：再按 last_touch_tick 取全池最近触碰 */
    sym_printf("[最近触碰] 全池按 last_touch_tick 取前 %d（不含上面已列的）：\n", lim);
    uint32_t best[64];
    size_t nb = 0;
    for (size_t i = 0; i < ai->pool->count; ++i) {
        Token *t = ai->pool->tokens[i];
        if (!t || t->is_garbage || !t->name || t->last_touch_tick == 0) continue;
        if (nb < 64) {
            best[nb++] = t->id;
        } else {
            size_t worst = 0;
            for (size_t k = 1; k < nb; ++k)
                if (ai->pool->tokens[best[k]]->last_touch_tick < ai->pool->tokens[best[worst]]->last_touch_tick) worst = k;
            if (t->last_touch_tick > ai->pool->tokens[best[worst]]->last_touch_tick) best[worst] = t->id;
        }
    }
    size_t shown2 = 0;
    while ((int)shown2 < lim) {
        size_t bi = 0;
        int found = 0;
        for (size_t k = 0; k < nb; ++k) {
            if (!best[k]) continue;
            if (!found || ai->pool->tokens[best[k]]->last_touch_tick >
                          ai->pool->tokens[best[bi]]->last_touch_tick) { bi = k; found = 1; }
        }
        if (!found) break;
        Token *t = ai->pool->tokens[best[bi]];
        best[bi] = 0;
        int dup = 0;
        for (size_t i = 0; i < ai->focus_n; ++i) if (ai->focus_ring[i] == t) { dup = 1; break; }
        if (dup) continue;
        sym_printf("  id=%u  %s  度 %zu  触碰 %llu  %s\n", t->id, t->name, t->count,
               (unsigned long long)t->last_touch_tick, sym_state(t));
        shown2++;
    }
    sym_printf("[活跃符号] 池子共 %zu 个符号（焦点环 %zu 个）\n",
           ai->pool ? ai->pool->count : 0, ai->focus_n);
}

static inline void sym_cmd_links(AI *ai, const char *name) {
    Token *t = sym_find(ai, name);
    if (!t) { sym_printf("[符号] 图里没有「%s」\n", name); return; }
    sym_printf("[符号] %s  id=%u  度 %zu  %s\n", t->name, t->id, t->count, sym_state(t));
    sym_printf("出边：\n");
    size_t no = 0;
    for (size_t i = 0; i < t->count; ++i) {
        AssocEntry *e = &token_assocs(t)[i];
        if (!e->main || !e->main->name) continue;
        sym_print_edge(ai, e, e->main->name);
        no++;
    }
    if (!no) sym_printf("  （没有出边）\n");
    sym_printf("入边（反查表）：\n");
    size_t ni = 0;
    for (uint32_t ent = t->rev_head; ent && ni < 64; ent = ai->pool->rev_next[ent - 1]) {
        uint32_t meta = ai->pool->rev_meta[ent - 1];
        uint8_t rid = (uint8_t)(meta & 0x7FFFu);
        int neg = (meta & 0x8000u) ? 1 : 0;
        uint32_t sid = ai->pool->rev_src[ent - 1];
        if (sid >= ai->pool->count) continue;
        Token *s = ai->pool->tokens[sid];
        if (!s || s->is_garbage || !s->name) continue;
        sym_printf("  %s -> %s%s%s  （反查）\n", s->name, neg ? "不 " : "",
               rel_name_of(ai, rid) ? rel_name_of(ai, rid) : "?", t->name);
        ni++;
    }
    if (!ni) sym_printf("  （没有入边）\n");
    sym_printf("[符号] 出边 %zu / 入边 %zu（入边只列前 64 条）\n", no, ni);
}

/* 搬边：from 的所有出边+入边 → to（只搬关系位，动作槽/权重不搬） */
static inline size_t sym_move_edges(AI *ai, Token *from, Token *to) {
    if (!ai || !from || !to || from == to) return 0;
    size_t moved = 0;
    for (size_t i = 0; i < from->count; ++i) {
        AssocEntry *e = &token_assocs(from)[i];
        if (!e->main || e->main == from) continue;
        int neg = 0;
        uint8_t rid = sym_assoc_rid(ai, e, &neg);
        if (!rid) continue;
        if (ai_write_rel(ai, to, e->main, rid, neg, AI_WSRC_RELATION) == 0) moved++;
        agent_teach_mark(ai, to, rid, e->main, neg);
    }
    for (size_t k = 0; k < ai->pool->count; ++k) {
        Token *t = ai->pool->tokens[k];
        if (!t || t == from || t == to || t->is_garbage) continue;
        for (size_t i = 0; i < t->count; ++i) {
            AssocEntry *e = &token_assocs(t)[i];
            if (e->main != from) continue;
            int neg = 0;
            uint8_t rid = sym_assoc_rid(ai, e, &neg);
            if (!rid) continue;
            if (ai_write_rel(ai, t, to, rid, neg, AI_WSRC_RELATION) == 0) moved++;
            agent_teach_mark(ai, t, rid, to, neg);
        }
    }
    return moved;
}

static inline int sym_write_gate(void) {
    if (g_sym_write) return 1;
    sym_printf("[符号] 只读模式：先 `::sym write on`（或 AIP_SYM_WRITE=1）再改图\n");
    return 0;
}

static inline int sym_check(AI *ai) {
    if (!ai || !ai->pool) return 0;
    for (size_t i = 0; i < ai->pool->count; ++i) {
        Token *t = ai->pool->tokens[i];
        if (!t) continue;
        for (size_t k = 0; k < t->count; ++k)
            if (!token_assocs(t)[k].main) return 0;
    }
    return 1;
}

/* §6.994 理由节点：`[理由:…]` 进池（随存盘），并把 id 挂到修改账最后一条 */
static inline void sym_note_reason(AI *ai) {
    if (!ai || !ai->pool || !g_sym_reason[0]) return;
    char name[256];
    snprintf(name, sizeof name, "[理由:%.*s]", (int)(sizeof name - 12), g_sym_reason);
    Token *t = pool_token_intern(ai->pool, name);
    if (t) ai_modlog_set_why(ai, t->id);
}

static inline void sym_after_write(AI *ai, const char *what) {
    ai->n_rel_learned++;
    int ok = sym_check(ai);
    sym_printf("[符号] 已写入：%s；不变式 %s\n", what, ok ? "干净（最小检查：边目标非空）" : "**有问题**（跑 ::verifywrites / ::whyfor 查）");
}

/* §6.989 撤销日志（进程内，最多 32 条）：只覆盖**边级操作 + 符号删除**。
 * rename/merge 搬边不可逆（会打印“不可撤销”），避免半吊子回滚。 */
#define SYM_UNDO_MAX 32
typedef struct {
    int kind;        /* 1=加边 2=删边 3=改边 4=删符号 */
    Token *a, *b, *sym;
    uint8_t rid, old_rid;
    int neg;
} SymUndo;
static SymUndo g_sym_undo[SYM_UNDO_MAX];
static int g_sym_undo_n = 0;

static inline void sym_undo_push(int kind, Token *a, Token *b, uint8_t rid, uint8_t old_rid, int neg, Token *sym) {
    if (g_sym_undo_n == SYM_UNDO_MAX) {
        memmove(&g_sym_undo[0], &g_sym_undo[1], sizeof g_sym_undo[0] * (SYM_UNDO_MAX - 1));
        g_sym_undo_n--;
    }
    SymUndo *u = &g_sym_undo[g_sym_undo_n++];
    u->kind = kind; u->a = a; u->b = b; u->rid = rid; u->old_rid = old_rid; u->neg = neg; u->sym = sym;
}

static inline int sym_drop_edge(Token *a, Token *b, uint8_t rid) {
    if (!a || !b) return 0;
    for (size_t i = 0; i < a->count; ++i) {
        AssocEntry *e = &token_assocs(a)[i];
        if (e->main != b) continue;
        if (rid) {
            /* 只删关系匹配的那条 */
            int rneg = 0;
            uint8_t have = sym_assoc_rid(NULL, e, &rneg);
            if (have != rid) continue;
        }
        token_remove_assoc(a, b);
        return 1;
    }
    return 0;
}

static inline void sym_cmd_undo(AI *ai, int times) {
    if (!sym_write_gate()) return;
    if (times <= 0) times = 1;
    for (int t = 0; t < times && g_sym_undo_n > 0; ++t) {
        SymUndo u = g_sym_undo[--g_sym_undo_n];
        if (u.kind == 1) {                 /* 加边 ⇒ 删掉 */
            sym_drop_edge(u.a, u.b, u.rid);
            sym_printf("[撤销] 加边已回滚：%s %s %s\n", u.a->name, rel_name_of(ai, u.rid), u.b->name);
        } else if (u.kind == 2) {          /* 删边 ⇒ 加回 */
            ai_write_rel(ai, u.a, u.b, u.rid, u.neg, AI_WSRC_RELATION);
            sym_printf("[撤销] 删边已加回：%s %s %s\n", u.a->name, rel_name_of(ai, u.rid), u.b->name);
        } else if (u.kind == 3) {          /* 改边 ⇒ 删新的、加旧的 */
            sym_drop_edge(u.a, u.b, u.rid);
            ai_write_rel(ai, u.a, u.b, u.old_rid, 0, AI_WSRC_RELATION);
            sym_printf("[撤销] 改边已还原：%s %s %s\n", u.a->name, rel_name_of(ai, u.old_rid), u.b->name);
        } else if (u.kind == 4) {          /* 删符号 ⇒ 清垃圾 */
            if (u.sym) { u.sym->is_garbage = 0; u.sym->mem_state = MEM_ACTIVE; }
            sym_printf("[撤销] 符号删除已回滚：%s\n", u.sym && u.sym->name ? u.sym->name : "?");
        }
        if (ai->n_rel_learned > 0) ai->n_rel_learned--;
    }
    sym_printf("[撤销] 剩余可撤销 %d 条\n", g_sym_undo_n);
}
/* 主入口：::sym <子命令…> */
static inline void sym_cmd(AI *ai, const char *arg) {
    if (!ai || !ai->pool) { sym_printf("[符号] 没有图\n"); return; }
    { static int inited = 0;
      if (!inited) { const char *e = getenv("AIP_SYM_WRITE"); if (e && e[0] == '1') g_sym_write = 1; inited = 1; } }
    char line[512];
    snprintf(line, sizeof line, "%s", arg ? arg : "");
    char *save = NULL;
    char *sub = strtok_r(line, " \t", &save);
    if (!sub) { sym_printf("[用法] ::sym active|links <名>|add <名>|del <名>|rename <旧> <新>|merge <源> <目标>|write on|off|edge add|del|mod …\n"); return; }
    if (!strcmp(sub, "active")) {
        char *n = strtok_r(NULL, " \t", &save);
        char *fmt = strtok_r(NULL, " \t", &save);
        if (fmt && !strcmp(fmt, "json")) sym_active_json(ai, n ? atoi(n) : 12);
        else sym_cmd_active(ai, n ? atoi(n) : 12);
        return;
    }
    if (!strcmp(sub, "links")) {
        char *name = strtok_r(NULL, " \t", &save);
        char *fmt = strtok_r(NULL, " \t", &save);
        if (!name) { sym_printf("[用法] ::sym links <名字> [json]\n"); return; }
        Token *t = sym_find(ai, name);
        if (!t) { sym_printf("[符号] 图里没有「%s」\n", name); return; }
        if (fmt && !strcmp(fmt, "json")) sym_links_json(ai, t);
        else sym_cmd_links(ai, name);
        return;
    }
    if (!strcmp(sub, "dry")) {
        const char *rest = save;
        while (rest && (*rest == ' ' || *rest == '\t')) rest++;
        if (!rest || !*rest) { sym_printf("[用法] ::sym dry <子命令…>（只预览不写）\n"); return; }
        if (!sym_write_gate()) return;
        char tmp[512];
        snprintf(tmp, sizeof tmp, "%s", rest);
        g_sym_dry = 1;
        sym_cmd(ai, tmp);
        g_sym_dry = 0;
        return;
    }
    if (!strcmp(sub, "reason")) {
        const char *rest = save;
        while (rest && (*rest == ' ' || *rest == '\t')) rest++;
        if (!rest || !*rest) { sym_printf("[符号] 当前理由：%s\n[用法] ::sym reason <文字>\n", g_sym_reason[0] ? g_sym_reason : "（空）"); return; }
        snprintf(g_sym_reason, sizeof g_sym_reason, "%s", rest);
        sym_printf("[符号] 下一条写操作的理由：%s\n", g_sym_reason);
        return;
    }
    if (!strcmp(sub, "log")) {
        char *n = strtok_r(NULL, " \t", &save);
        sym_cmd_log(n ? atoi(n) : 10);
        return;
    }
    if (!strcmp(sub, "undo")) {
        char *n = strtok_r(NULL, " \t", &save);
        sym_cmd_undo(ai, n ? atoi(n) : 1);
        return;
    }
    if (!strcmp(sub, "write")) {
        char *v = strtok_r(NULL, " \t", &save);
        if (v && !strcmp(v, "on")) g_sym_write = 1;
        else if (v && !strcmp(v, "off")) g_sym_write = 0;
        sym_printf("[符号] 写入门 = %s\n", g_sym_write ? "开" : "关（只读）");
        return;
    }
    if (!strcmp(sub, "add")) {
        char *name = strtok_r(NULL, " \t", &save);
        if (!name) { sym_printf("[用法] ::sym add <名字>\n"); return; }
        if (!sym_write_gate()) return;
        Token *t = pool_token_intern(ai->pool, name);
        if (!t) { sym_printf("[符号] 造不出「%s」\n", name); return; }
        sym_printf("[符号] 已确保存在：%s  id=%u\n", t->name, t->id);
        sym_after_write(ai, "新增符号（若原本不存在）");
        return;
    }
    if (!strcmp(sub, "del")) {
        char *name = strtok_r(NULL, " \t", &save);
        if (!name) { sym_printf("[用法] ::sym del <名字>\n"); return; }
        if (!sym_write_gate()) return;
        if (g_sym_dry) {
            Token *t0 = sym_find(ai, name);
            sym_printf("[预览] 删除符号 %s：%s（不写）\n", name, t0 ? "存在，会标垃圾" : "不存在");
            return;
        }
        Token *t = sym_find(ai, name);
        if (!t) { sym_printf("[符号] 图里没有「%s」\n", name); return; }
        t->is_garbage = 1;
        sym_undo_push(4, NULL, NULL, 0, 0, 0, t);
        sym_log_append("sym.del", t->name, "", "");
        sym_note_reason(ai);
        sym_after_write(ai, "符号标垃圾（不物理删；GC/存盘会收）");
        return;
    }
    if (!strcmp(sub, "rename") || !strcmp(sub, "merge")) {
        char *a = strtok_r(NULL, " \t", &save);
        char *b = strtok_r(NULL, " \t", &save);
        if (!a || !b) { sym_printf("[用法] ::sym rename|merge <旧/源> <新/目标>\n"); return; }
        if (!sym_write_gate()) return;
        if (g_sym_dry) { sym_printf("[预览] %s %s → %s（不写）\n", sub, a, b); return; }
        Token *from = sym_find(ai, a);
        if (!from && !strcmp(sub, "rename")) from = pool_token_intern(ai->pool, a);
        if (!from) { sym_printf("[符号] 源「%s」不在图里\n", a); return; }
        Token *to = pool_find(ai->pool, b);
        if (!to) to = pool_token_intern(ai->pool, b);
        if (!to || to == from) { sym_printf("[符号] 目标「%s」有问题\n", b); return; }
        size_t moved = sym_move_edges(ai, from, to);
        from->is_garbage = 1;
        sym_log_append(sub, from->name, "→", to->name);
        sym_note_reason(ai);
        char what[160];
        snprintf(what, sizeof what, "%s → %s（搬 %zu 条边，旧符号标垃圾）", a, b, moved);
        sym_after_write(ai, what);
        return;
    }
    if (!strcmp(sub, "edge")) {
        char *op = strtok_r(NULL, " \t", &save);
        char *a = strtok_r(NULL, " \t", &save);
        char *r = strtok_r(NULL, " \t", &save);
        char *b = strtok_r(NULL, " \t", &save);
        if (!op || !a || !r || !b) { sym_printf("[用法] ::sym edge add|del|mod <A> <关系> <B> [新关系]\n"); return; }
        if (!sym_write_gate()) return;
        if (g_sym_dry) {
            Token *A0 = pool_find(ai->pool, a), *B0 = pool_find(ai->pool, b);
            uint8_t rid0 = rel_id_of(ai, r, 0);
            int has = (A0 && B0 && rid0 && rel_direct(A0, rid0, B0));
            sym_printf("[预览] %s %s %s %s：", op, a, r, b);
            if (!strcmp(op, "add")) sym_printf(has ? "已存在，不需要写\n" : "会新增一条边（不写）\n");
            else if (!strcmp(op, "del")) sym_printf(has ? "会删除一条边（不写）\n" : "没有这条边，删不了\n");
            else sym_printf("会把关系改成 %s（不写）\n", save ? save : "?");
            return;
        }
        Token *A = pool_token_intern(ai->pool, a);
        Token *B = pool_token_intern(ai->pool, b);
        uint8_t rid = rel_id_of(ai, r, 1);
        if (!A || !B || !rid) { sym_printf("[符号] 参数不对（A/B/关系 至少一个不认识）\n"); return; }
        if (!strcmp(op, "add")) {
            if (ai_write_rel(ai, A, B, rid, 0, AI_WSRC_RELATION) != 0) { sym_printf("[符号] 写不进\n"); return; }
            agent_teach_mark(ai, A, rid, B, 0);
            sym_undo_push(1, A, B, rid, 0, 0, NULL);
            sym_log_append("edge.add", a, rel_name_of(ai, rid), b);
            sym_note_reason(ai);
            char what[160];
            snprintf(what, sizeof what, "%s %s %s", a, rel_name_of(ai, rid), b);
            sym_after_write(ai, what);
            return;
        }
        if (!strcmp(op, "del")) {
            int removed = 0;
            for (size_t i = 0; i < A->count; ++i) {
                AssocEntry *e = &token_assocs(A)[i];
                if (e->main != B) continue;
                int neg = 0;
                if (sym_assoc_rid(ai, e, &neg) != rid) continue;
                int rneg = 0;
                (void)sym_assoc_rid(NULL, e, &rneg);
                token_remove_assoc(A, B);
                sym_undo_push(2, A, B, rid, 0, rneg, NULL);
                sym_log_append("edge.del", a, rel_name_of(ai, rid), b);
                removed = 1;
                break;
            }
            sym_printf("[符号] 删边 %s %s %s：%s\n", a, rel_name_of(ai, rid), b,
                   removed ? "已删（反查表留陈旧项，查询会过滤）" : "没找到这条边");
            if (removed) sym_after_write(ai, "删除一条边");
            return;
        }
        if (!strcmp(op, "mod")) {
            char *nr = strtok_r(NULL, " \t", &save);
            uint8_t nrid = nr ? rel_id_of(ai, nr, 1) : 0;
            if (!nrid) { sym_printf("[用法] ::sym edge mod <A> <旧关系> <B> <新关系>\n"); return; }
            for (size_t i = 0; i < A->count; ++i) {
                AssocEntry *e = &token_assocs(A)[i];
                if (e->main != B) continue;
                int neg = 0;
                if (sym_assoc_rid(ai, e, &neg) != rid) continue;
                token_remove_assoc(A, B);
                sym_undo_push(3, A, B, nrid, rid, 0, NULL);
                sym_log_append("edge.mod", a, rel_name_of(ai, nrid), b);
                break;
            }
            if (ai_write_rel(ai, A, B, nrid, 0, AI_WSRC_RELATION) != 0) { sym_printf("[符号] 新关系写不进\n"); return; }
            agent_teach_mark(ai, A, nrid, B, 0);
            char what[192];
            snprintf(what, sizeof what, "%s %s %s → %s", a, rel_name_of(ai, rid), b, rel_name_of(ai, nrid));
            sym_after_write(ai, what);
            return;
        }
        sym_printf("[用法] ::sym edge add|del|mod …\n");
        return;
    }
    sym_printf("[用法] ::sym active|links|add|del|rename|merge|write|edge …\n");
}


/* §6.993 模型可调用工具：自然语言里的「工具 …」前缀 → ::sym 子命令（默认只读，写操作过网关）。
 * 借鉴 路线C gates.py：来源白名单 + 写入门 + 限额 + 判定账本；模型来源固定 "self"。 */
/* 策略词表里有没有任意一个词出现在 text 里 */
static inline int tool_str_has_list(const char *key, const char *deflist, const char *text) {
    if (!text) return 0;
    char buf[256];
    if (!aip_policy_str(key, buf, sizeof buf))
        snprintf(buf, sizeof buf, "%s", deflist ? deflist : "");
    char *cur = buf;
    for (char *w = aip_policy_next(&cur); w; w = aip_policy_next(&cur))
        if (*w && strstr(text, w)) return 1;
    return 0;
}

static inline int tool_detect(const char *input) {
    if (!input) return 0;
    const char *p = input;
    while (*p == ' ' || *p == '\t') p++;
    char buf[128];
    if (!aip_policy_str("tool_prefix", buf, sizeof buf))
        snprintf(buf, sizeof buf, "%s", "工具,tool:,TOOL:");
    char *cur = buf;
    for (char *w = aip_policy_next(&cur); w; w = aip_policy_next(&cur)) {
        size_t l = strlen(w);
        if (l && strncmp(p, w, l) == 0) return (int)l;
    }
    return 0;
}

/* 自然说法 → 子命令；已经是子命令就原样返回 1 */
static inline int tool_resolve(AI *ai, const char *rest, char *cmd, size_t cap) {
    while (rest && (*rest == ' ' || *rest == '\t' || *rest == ':')) rest++;
    if (!rest || !*rest) return 0;
    static const char *subs[] = { "active", "links", "add", "del", "rename", "merge", "edge",
                                  "write", "reason", "log", "undo", "dry", "gate", NULL };
    for (size_t i = 0; subs[i]; ++i) {
        size_t l = strlen(subs[i]);
        if (strncmp(rest, subs[i], l) == 0 && (rest[l] == 0 || rest[l] == ' ')) {
            snprintf(cmd, cap, "%s", rest);
            return 1;
        }
    }
    /* 「看看猫的连接 / 猫连着哪些符号」→ links <猫> */
    if (tool_str_has_list("tool_link_words", "连接,连着,相连", rest)) {
        /* 子串匹配池里最长的符号名：自然句没空格（「看看猫的连接」），按词切抓不到「猫」 */
        const char *best = NULL;
        size_t bl = 0, bdeg = 0;
        for (size_t i = 0; i < ai->pool->count; ++i) {
            Token *t = ai->pool->tokens[i];
            if (!t || t->is_garbage || !t->name || t->name[0] == '[') continue;
            size_t tl = strlen(t->name);
            if (tl < 3 || tl > 24) continue;
            if (!strstr(rest, t->name)) continue;
            /* **有关系边的才是“符号”**：普通词（看看）只有共现边，别抢实体（猫） */
            size_t rd = 0;
            for (size_t k = 0; k < t->count; ++k)
                if (token_assocs(t)[k].main && token_assocs(t)[k].rel) { rd++; if (rd > 8) break; }
            if (rd == 0) continue;
            if (tl > bl || (tl == bl && rd > bdeg)) { best = t->name; bl = tl; bdeg = rd; }
        }
        if (best) {
            snprintf(cmd, cap, "links %s", best);
            return 1;
        }
        return 0;
    }
    if (tool_str_has_list("tool_active_words", "活跃,激活,符号", rest)) {
        snprintf(cmd, cap, "active 8");
        return 1;
    }
    if (tool_str_has_list("tool_gate_words", "网关,gate", rest)) {
        snprintf(cmd, cap, "gate");
        return 1;
    }
    return 0;
}

static inline int toolcall_hook(AI *ai, const char *input, char *out, size_t cap) {
    if (!ai || !out || cap == 0 || !tool_detect(input)) return 0;
    const char *p = input;
    while (*p == ' ' || *p == '\t') p++;
    int plen = tool_detect(input);
    p += plen > 0 ? plen : 0;
    char cmd[512];
    if (!tool_resolve(ai, p, cmd, sizeof cmd)) {
        snprintf(out, cap, "（工具）用法：工具 active | 工具 links 猫 | 工具 看看猫的连接 | 工具 gate…（写操作要先 ::sym write on）");
        tool_ledger_add("self", "?", "reject_parse");
        g_tool_damage++;
        return 1;
    }
    char sub[32] = {0};
    sscanf(cmd, "%31s", sub);
    if (!strcmp(sub, "gate")) {
        FILE *tmp = tmpfile();
        if (!tmp) { snprintf(out, cap, "（工具）网关账本打不开"); return 1; }
        FILE *old = g_sym_out;
        g_sym_out = tmp;
        tool_gate_report();
        g_sym_out = old;
        rewind(tmp);
        size_t got = fread(out, 1, cap ? cap - 1 : 0, tmp);
        out[got] = 0;
        fclose(tmp);
        tool_ledger_add("self", "gate", "allow");
        return 1;
    }
    int write = tool_is_write(sub);
    if (write) {
        if (!g_sym_write) {
            snprintf(out, cap, "（工具）写入门没开：让操作者先 ::sym write on，我不自己开门");
            tool_ledger_add("self", sub, "reject_write_gate");
            g_tool_damage++;
            return 1;
        }
        if (!g_sym_reason[0]) {
            snprintf(out, cap, "（工具）模型写图要先给理由：`工具 reason 因为…`，没有理由我不落盘");
            tool_ledger_add("self", sub, "reject_no_reason");
            g_tool_damage++;
            return 1;
        }
        long limit = getenv("AIP_TOOLWRITE_LIMIT") ? atol(getenv("AIP_TOOLWRITE_LIMIT"))
                                                    : aip_policy_int("toolwrite_limit", 50);
        if (limit > 0 && g_tool_writes >= limit) {
            snprintf(out, cap, "（工具）这个会话里模型已经改图 %d 次，到限额 %ld 了", g_tool_writes, limit);
            tool_ledger_add("self", sub, "reject_limit");
            g_tool_damage++;
            return 1;
        }
    }
    FILE *tmp = tmpfile();
    if (!tmp) { snprintf(out, cap, "（工具）临时输出打不开"); return 1; }
    FILE *old = g_sym_out;
    g_sym_out = tmp;
    sym_cmd(ai, cmd);
    g_sym_out = old;
    rewind(tmp);
    size_t got = fread(out, 1, cap ? cap - 1 : 0, tmp);
    out[got] = 0;
    fclose(tmp);
    while (got > 0 && (out[got - 1] == '\n' || out[got - 1] == '\r')) out[--got] = 0;
    if (write) { g_tool_writes++; g_sym_reason[0] = 0; }   /* §6.994 理由一条一用：写成就消费掉 */
    tool_ledger_add("self", sub, write ? "allow_write" : "allow");
    return 1;
}

#endif
