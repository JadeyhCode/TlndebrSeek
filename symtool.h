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

static int g_sym_write = 0;   /* 进程内开关：::sym write on */

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
    const char *rn = rid ? rel_name_of(ai, rid) : "?";
    const char *role = (e->role == ASSOC_ROLE_DERIVED) ? "推论"
                     : (e->role == ASSOC_ROLE_INNATE) ? "基准" : "观测";
    printf("  %s%s%s -> %s  （hits %u，%s%s）\n", neg ? "不 " : "", rn ? rn : "?",
           neg ? "" : "", other, e->hits, role,
           e->action && e->action->name ? "，带动作槽" : "");
}

static inline Token *sym_find(AI *ai, const char *name) {
    if (!ai || !ai->pool || !name) return NULL;
    return pool_find(ai->pool, name);
}

static inline void sym_cmd_active(AI *ai, int lim) {
    if (lim <= 0) lim = 12;
    printf("[活跃符号] 焦点环 %zu 个（权重高→低），最多列 %d：\n", ai->focus_n, lim);
    size_t shown = 0;
    for (size_t i = 0; i < ai->focus_n && (int)shown < lim; ++i) {
        Token *t = ai->focus_ring[i];
        if (!t || t->is_garbage || !t->name) continue;
        printf("  id=%u  %s  权重 %.2f  度 %zu  触碰 %llu  %s\n", t->id,
               t->name, ai->focus_weight[i], t->count,
               (unsigned long long)t->last_touch_tick, sym_state(t));
        shown++;
    }
    /* §6.989 「当前激活」不能只看焦点环（刚启动是空的）：再按 last_touch_tick 取全池最近触碰 */
    printf("[最近触碰] 全池按 last_touch_tick 取前 %d（不含上面已列的）：\n", lim);
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
        printf("  id=%u  %s  度 %zu  触碰 %llu  %s\n", t->id, t->name, t->count,
               (unsigned long long)t->last_touch_tick, sym_state(t));
        shown2++;
    }
    printf("[活跃符号] 池子共 %zu 个符号（焦点环 %zu 个）\n",
           ai->pool ? ai->pool->count : 0, ai->focus_n);
}

static inline void sym_cmd_links(AI *ai, const char *name) {
    Token *t = sym_find(ai, name);
    if (!t) { printf("[符号] 图里没有「%s」\n", name); return; }
    printf("[符号] %s  id=%u  度 %zu  %s\n", t->name, t->id, t->count, sym_state(t));
    printf("出边：\n");
    size_t no = 0;
    for (size_t i = 0; i < t->count; ++i) {
        AssocEntry *e = &token_assocs(t)[i];
        if (!e->main || !e->main->name) continue;
        sym_print_edge(ai, e, e->main->name);
        no++;
    }
    if (!no) printf("  （没有出边）\n");
    printf("入边（反查表）：\n");
    size_t ni = 0;
    for (uint32_t ent = t->rev_head; ent && ni < 64; ent = ai->pool->rev_next[ent - 1]) {
        uint32_t meta = ai->pool->rev_meta[ent - 1];
        uint8_t rid = (uint8_t)(meta & 0x7FFFu);
        int neg = (meta & 0x8000u) ? 1 : 0;
        uint32_t sid = ai->pool->rev_src[ent - 1];
        if (sid >= ai->pool->count) continue;
        Token *s = ai->pool->tokens[sid];
        if (!s || s->is_garbage || !s->name) continue;
        printf("  %s -> %s%s%s  （反查）\n", s->name, neg ? "不 " : "",
               rel_name_of(ai, rid) ? rel_name_of(ai, rid) : "?", t->name);
        ni++;
    }
    if (!ni) printf("  （没有入边）\n");
    printf("[符号] 出边 %zu / 入边 %zu（入边只列前 64 条）\n", no, ni);
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
    printf("[符号] 只读模式：先 `::sym write on`（或 AIP_SYM_WRITE=1）再改图\n");
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

static inline void sym_after_write(AI *ai, const char *what) {
    ai->n_rel_learned++;
    int ok = sym_check(ai);
    printf("[符号] 已写入：%s；不变式 %s\n", what, ok ? "干净（最小检查：边目标非空）" : "**有问题**（跑 ::verifywrites / ::whyfor 查）");
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
            printf("[撤销] 加边已回滚：%s %s %s\n", u.a->name, rel_name_of(ai, u.rid), u.b->name);
        } else if (u.kind == 2) {          /* 删边 ⇒ 加回 */
            ai_write_rel(ai, u.a, u.b, u.rid, u.neg, AI_WSRC_RELATION);
            printf("[撤销] 删边已加回：%s %s %s\n", u.a->name, rel_name_of(ai, u.rid), u.b->name);
        } else if (u.kind == 3) {          /* 改边 ⇒ 删新的、加旧的 */
            sym_drop_edge(u.a, u.b, u.rid);
            ai_write_rel(ai, u.a, u.b, u.old_rid, 0, AI_WSRC_RELATION);
            printf("[撤销] 改边已还原：%s %s %s\n", u.a->name, rel_name_of(ai, u.old_rid), u.b->name);
        } else if (u.kind == 4) {          /* 删符号 ⇒ 清垃圾 */
            if (u.sym) { u.sym->is_garbage = 0; u.sym->mem_state = MEM_ACTIVE; }
            printf("[撤销] 符号删除已回滚：%s\n", u.sym && u.sym->name ? u.sym->name : "?");
        }
        if (ai->n_rel_learned > 0) ai->n_rel_learned--;
    }
    printf("[撤销] 剩余可撤销 %d 条\n", g_sym_undo_n);
}
/* 主入口：::sym <子命令…> */
static inline void sym_cmd(AI *ai, const char *arg) {
    if (!ai || !ai->pool) { printf("[符号] 没有图\n"); return; }
    { static int inited = 0;
      if (!inited) { const char *e = getenv("AIP_SYM_WRITE"); if (e && e[0] == '1') g_sym_write = 1; inited = 1; } }
    char line[512];
    snprintf(line, sizeof line, "%s", arg ? arg : "");
    char *save = NULL;
    char *sub = strtok_r(line, " \t", &save);
    if (!sub) { printf("[用法] ::sym active|links <名>|add <名>|del <名>|rename <旧> <新>|merge <源> <目标>|write on|off|edge add|del|mod …\n"); return; }
    if (!strcmp(sub, "active")) {
        char *n = strtok_r(NULL, " \t", &save);
        sym_cmd_active(ai, n ? atoi(n) : 12);
        return;
    }
    if (!strcmp(sub, "links")) {
        char *name = strtok_r(NULL, " \t", &save);
        if (!name) { printf("[用法] ::sym links <名字>\n"); return; }
        sym_cmd_links(ai, name);
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
        printf("[符号] 写入门 = %s\n", g_sym_write ? "开" : "关（只读）");
        return;
    }
    if (!strcmp(sub, "add")) {
        char *name = strtok_r(NULL, " \t", &save);
        if (!name) { printf("[用法] ::sym add <名字>\n"); return; }
        if (!sym_write_gate()) return;
        Token *t = pool_token_intern(ai->pool, name);
        if (!t) { printf("[符号] 造不出「%s」\n", name); return; }
        printf("[符号] 已确保存在：%s  id=%u\n", t->name, t->id);
        sym_after_write(ai, "新增符号（若原本不存在）");
        return;
    }
    if (!strcmp(sub, "del")) {
        char *name = strtok_r(NULL, " \t", &save);
        if (!name) { printf("[用法] ::sym del <名字>\n"); return; }
        if (!sym_write_gate()) return;
        Token *t = sym_find(ai, name);
        if (!t) { printf("[符号] 图里没有「%s」\n", name); return; }
        t->is_garbage = 1;
        sym_undo_push(4, NULL, NULL, 0, 0, 0, t);
        sym_after_write(ai, "符号标垃圾（不物理删；GC/存盘会收）");
        return;
    }
    if (!strcmp(sub, "rename") || !strcmp(sub, "merge")) {
        char *a = strtok_r(NULL, " \t", &save);
        char *b = strtok_r(NULL, " \t", &save);
        if (!a || !b) { printf("[用法] ::sym rename|merge <旧/源> <新/目标>\n"); return; }
        if (!sym_write_gate()) return;
        Token *from = sym_find(ai, a);
        if (!from && !strcmp(sub, "rename")) from = pool_token_intern(ai->pool, a);
        if (!from) { printf("[符号] 源「%s」不在图里\n", a); return; }
        Token *to = pool_find(ai->pool, b);
        if (!to) to = pool_token_intern(ai->pool, b);
        if (!to || to == from) { printf("[符号] 目标「%s」有问题\n", b); return; }
        size_t moved = sym_move_edges(ai, from, to);
        from->is_garbage = 1;
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
        if (!op || !a || !r || !b) { printf("[用法] ::sym edge add|del|mod <A> <关系> <B> [新关系]\n"); return; }
        if (!sym_write_gate()) return;
        Token *A = pool_token_intern(ai->pool, a);
        Token *B = pool_token_intern(ai->pool, b);
        uint8_t rid = rel_id_of(ai, r, 1);
        if (!A || !B || !rid) { printf("[符号] 参数不对（A/B/关系 至少一个不认识）\n"); return; }
        if (!strcmp(op, "add")) {
            if (ai_write_rel(ai, A, B, rid, 0, AI_WSRC_RELATION) != 0) { printf("[符号] 写不进\n"); return; }
            agent_teach_mark(ai, A, rid, B, 0);
            sym_undo_push(1, A, B, rid, 0, 0, NULL);
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
                removed = 1;
                break;
            }
            printf("[符号] 删边 %s %s %s：%s\n", a, rel_name_of(ai, rid), b,
                   removed ? "已删（反查表留陈旧项，查询会过滤）" : "没找到这条边");
            if (removed) sym_after_write(ai, "删除一条边");
            return;
        }
        if (!strcmp(op, "mod")) {
            char *nr = strtok_r(NULL, " \t", &save);
            uint8_t nrid = nr ? rel_id_of(ai, nr, 1) : 0;
            if (!nrid) { printf("[用法] ::sym edge mod <A> <旧关系> <B> <新关系>\n"); return; }
            for (size_t i = 0; i < A->count; ++i) {
                AssocEntry *e = &token_assocs(A)[i];
                if (e->main != B) continue;
                int neg = 0;
                if (sym_assoc_rid(ai, e, &neg) != rid) continue;
                token_remove_assoc(A, B);
                sym_undo_push(3, A, B, nrid, rid, 0, NULL);
                break;
            }
            if (ai_write_rel(ai, A, B, nrid, 0, AI_WSRC_RELATION) != 0) { printf("[符号] 新关系写不进\n"); return; }
            agent_teach_mark(ai, A, nrid, B, 0);
            char what[192];
            snprintf(what, sizeof what, "%s %s %s → %s", a, rel_name_of(ai, rid), b, rel_name_of(ai, nrid));
            sym_after_write(ai, what);
            return;
        }
        printf("[用法] ::sym edge add|del|mod …\n");
        return;
    }
    printf("[用法] ::sym active|links|add|del|rename|merge|write|edge …\n");
}

#endif
