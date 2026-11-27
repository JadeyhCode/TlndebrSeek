/* effect.h — §7.074 P1：效果执行器（模型无关、只认 schema 的 post 数据）。
 *
 * 设计约束（用户 P1 规格）：
 *   · 执行器只有固定原语：bind(args) → assert_state(template) → 记录来源与时刻；
 *     撤销用 retract_state。**不得**出现“看到名字「效果」就执行”的分支。
 *   · 效果是 schema 的 post 模板（`数量($2,-1)`），不是新的特权关系。
 *   · 约束 defeasible：违反时输出“奇怪/需要解释”，默认**拒执行**（--force 才落）。
 *   · 帧问题：不静默覆盖旧状态；同一 (主语,关系,值) 重复应用只计数（hits），不重复造边。
 *   · 写入门 + 理由：沿用 ::sym write on / ::sym reason（不另开特权通道）。
 *   · 来源与时刻：每次 apply/retract 记 `_t/effects.tsv`（tick / 事件 / 参数 / 模板 / 结果）。
 */
#ifndef EFFECT_H
#define EFFECT_H

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdint.h>

/* 约束里“类”是否可达：沿 属于（REL_IS_A）正边 BFS，深度 ≤4。 */
static inline int effect_is_a(AI *ai, Token *t, const char *cls, int depth) {
    if (!ai || !t || !cls || !*cls || depth < 0) return 0;
    if (t->name && !strcmp(t->name, cls)) return 1;
    if (depth == 0) return 0;
    for (size_t i = 0; i < t->count; ++i) {
        const AssocEntry *e = &token_assocs_ro(t)[i];
        if (!e->main || !(e->rel & REL_BIT(REL_IS_A)) || e->nrel) continue;
        if (e->main->name && !strcmp(e->main->name, cls)) return 1;
        if (effect_is_a(ai, e->main, cls, depth - 1)) return 1;
    }
    return 0;
}

/* 解析一条 post 模板：`名字($2,值)`；返回 1 成功。subj_sel: 1/2（$N），value 字面量。 */
static inline int effect_parse_post(const char *tpl, char *name, size_t ncap,
                                    int *subj_sel, char *value, size_t vcap) {
    if (!tpl || !*tpl) return 0;
    const char *lp = strchr(tpl, '(');
    const char *rp = lp ? strrchr(lp, ')') : NULL;
    if (!lp || !rp || rp <= lp) return 0;
    size_t nl = (size_t)(lp - tpl);
    while (nl && (tpl[nl-1] == ' ' || tpl[nl-1] == '\t')) nl--;
    if (!nl || nl >= ncap) return 0;
    memcpy(name, tpl, nl); name[nl] = 0;
    char inside[128];
    size_t il = (size_t)(rp - lp - 1);
    if (il >= sizeof inside) return 0;
    memcpy(inside, lp + 1, il); inside[il] = 0;
    char *comma = strchr(inside, ',');
    if (!comma) return 0;
    *comma = 0;
    char *a = inside, *b = comma + 1;
    while (*a == ' ' || *a == '\t') a++;
    while (*b == ' ' || *b == '\t') b++;
    size_t al = strlen(a); while (al && (a[al-1] == ' ' || a[al-1] == '\t')) a[--al] = 0;
    size_t bl = strlen(b); while (bl && (b[bl-1] == ' ' || b[bl-1] == '\t')) b[--bl] = 0;
    if (a[0] != '$' || (a[1] != '1' && a[1] != '2') || a[2]) return 0;
    *subj_sel = a[1] - '0';
    snprintf(value, vcap, "%s", b);
    return value[0] != 0;
}


/* 约束状态：3=没有约束，2=类词都不知道，1=通过，0=奇怪（不满足）。 */
static inline int effect_cons_status(AI *ai, const RelSchema *sc, uint8_t k,
                                     Token *a1, Token *a2, char *note, size_t cap) {
    if (!sc || k >= sc->n_roles || !sc->cons[k][0]) {
        if (note && cap) snprintf(note, cap, "（没有约束）");
        return 3;
    }
    char consbuf[REL_SCHEMA_CONS];
    snprintf(consbuf, sizeof consbuf, "%s", sc->cons[k]);
    char *colon = strchr(consbuf, ':');
    if (!colon) { if (note && cap) snprintf(note, cap, "（约束格式坏：%s）", consbuf); return 2; }
    *colon = 0;
    const char *cls = colon + 1;
    Token *who = (k == 0) ? a1 : a2;
    if (!who) { if (note && cap) snprintf(note, cap, "（没有绑定参数）"); return 2; }
    if (effect_is_a(ai, who, cls, 4)) {
        if (note && cap) snprintf(note, cap, "通过（属于链）");
        return 1;
    }
    {   /* P1：复用 pred.h 的谓词原子 `可食(石头)`，不只靠 属于 链 */
        char *args[1];
        args[0] = (char *)who->name;
        if (who->name && pred_find(ai, cls, args, 1)) {
            if (note && cap) snprintf(note, cap, "通过（谓词原子 %s(%s)）", cls, who->name);
            return 1;
        }
    }
    if (!pool_find(ai->pool, cls)) {
        if (note && cap) snprintf(note, cap, "不知道「%s」是什么（类词不在图里）", cls);
        return 2;
    }
    if (note && cap) snprintf(note, cap, "奇怪：%s 不是/推不出 %s", who->name ? who->name : "?", cls);
    return 0;
}

/* `::rolecheck <关系> <主语> <宾语>`：只读，不写图；角色绑定 + 约束状态。 */
static inline int rolecheck_cmd(AI *ai, const char *arg) {
    if (!ai || !arg) return 0;
    while (*arg == ' ') arg++;
    if (!*arg) { printf("[角色] 用法：::rolecheck <关系> <主语> <宾语>\n"); return 1; }
    char buf[384];
    snprintf(buf, sizeof buf, "%s", arg);
    char *tok[4] = {0}; int nw = 0;
    for (char *p = buf; *p && nw < 4; ) {
        while (*p == ' ' || *p == '\t') p++;
        if (!*p) break;
        tok[nw++] = p;
        while (*p && *p != ' ' && *p != '\t') p++;
        if (*p) *p++ = 0;
    }
    if (nw < 3) { printf("[角色] 用法：::rolecheck <关系> <主语> <宾语>\n"); return 1; }
    const RelSchema *sc = rel_schema_by_name(tok[0]);
    if (!sc) { printf("[角色] 关系「%s」没有 schema：纯标签，没有角色/约束可查\n", tok[0]); return 1; }
    Token *a1 = pool_find(ai->pool, tok[1]);
    Token *a2 = pool_find(ai->pool, tok[2]);
    if (!a1 || !a2) {
        printf("[角色] 图里没有「%s」\n", !a1 ? tok[1] : tok[2]);
        return 1;
    }
    printf("[角色] %s：", sc->name);
    for (uint8_t k = 0; k < sc->n_roles; ++k)
        printf("%s%s=%s", k ? "，" : "", sc->roles[k][0] ? sc->roles[k] : "?",
               (k == 0) ? a1->name : a2->name);
    printf("\n");
    if ((int)aip_policy_int("role_constraint", 1) == 0) {
        printf("[约束] 检查关闭（role_constraint=0）\n");
        return 1;
    }
    int pass = 0, bad = 0, unk = 0;
    for (uint8_t k = 0; k < sc->n_roles; ++k) {
        char note[192];
        int st = effect_cons_status(ai, sc, k, a1, a2, note, sizeof note);
        printf("[约束] %s：%s\n", sc->cons[k][0] ? sc->cons[k] : sc->roles[k], note);
        if (st == 1) pass++;
        else if (st == 0) bad++;
        else if (st == 2) unk++;
    }
    printf("[角色] 小结：通过 %d / 奇怪 %d / 不知道 %d\n", pass, bad, unk);
    return 1;
}

static inline void effect_log(const char *fmt, ...) {
    mkdir("_t", 0755);
    FILE *f = fopen("_t/effects.tsv", "ab");
    if (!f) return;
    va_list ap;
    va_start(ap, fmt);
    vfprintf(f, fmt, ap);
    va_end(ap);
    fclose(f);
}

/* 找到 subject 下 (dyn 关系, 值) 的边；返回 hits。 */
static inline uint32_t effect_edge_hits(Token *subj, uint8_t dyn, Token *val) {
    for (size_t i = 0; i < subj->count; ++i) {
        AssocEntry *e = &token_assocs(subj)[i];
        if (e->main == val && e->dyn == dyn) return e->hits;
    }
    return 0;
}

static inline void effect_bump_edge(Token *subj, uint8_t dyn, Token *val) {
    for (size_t i = 0; i < subj->count; ++i) {
        AssocEntry *e = &token_assocs(subj)[i];
        if (e->main == val && e->dyn == dyn) { e->hits += REL_BOOST; return; }
    }
}

static inline int effect_retract_edge(Token *subj, uint8_t dyn, Token *val) {
    for (size_t i = 0; i < subj->count; ++i) {
        AssocEntry *e = &token_assocs(subj)[i];
        if (e->main != val || e->dyn != dyn) continue;
        memmove(&token_assocs(subj)[i], &token_assocs(subj)[i + 1],
                (subj->count - i - 1) * sizeof token_assocs(subj)[0]);
        subj->count--;
        return 1;
    }
    return 0;
}


/* §7.075 事件具体化：`[事件:吃(张三,米饭)] --[结果]--> [状态:数量(米饭,-1)]`
 * 结果边是**普通动态关系边**（关系名来自数据 `结果`），没有“看到效果就执行”的分支。 */
static inline void effect_event_name(char *out, size_t cap, const char *rel,
                                     const char *a1, const char *a2) {
    snprintf(out, cap, "[事件:%s(%s,%s)]", rel, a1, a2);
}

static inline int effect_trace(AI *ai, const char *ev) {
    if (!ai || !ev || !*ev) return 0;
    Token *e = pool_find(ai->pool, ev);
    if (!e) { printf("[效果] 图里没有事件「%s」\n", ev); return 1; }
    int n = 0;
    printf("[效果] 事件 %s 的结果：\n", ev);
    for (size_t i = 0; i < e->count; ++i) {
        const AssocEntry *a = &token_assocs_ro(e)[i];
        if (!a->main || !a->dyn) continue;
        const char *nm = rel_dyn_name(ai, (uint8_t)(REL_DYN_BASE + a->dyn - 1));
        printf("  --[%s]--> %s（计数 %u，tick %llu）\n", nm ? nm : "?",
               a->main->name ? a->main->name : "?", a->hits,
               (unsigned long long)a->last_touch_tick);
        n++;
    }
    if (!n) printf("  （没有结果边；可能只做了 apply 没做 event）\n");
    return 1;
}

static inline int effect_cmd(AI *ai, const char *arg) {
    if (!ai || !arg) return 0;
    while (*arg == ' ') arg++;
    if (!*arg) {
        printf("[效果] 用法：::effect apply <关系> <主语> <宾语> [--force] | state <主语> | retract <关系> <主语> <宾语> | log\n");
        return 1;
    }
    if (!strncmp(arg, "trace", 5)) {
        const char *ev = arg + 5;
        while (*ev == ' ') ev++;
        if (!*ev) { printf("[效果] 用法：::effect trace <事件名，如 [事件:吃(张三,米饭)]>\n"); return 1; }
        return effect_trace(ai, ev);
    }
    if (!strncmp(arg, "state", 5)) {
        const char *s = arg + 5;
        while (*s == ' ') s++;
        if (!*s) { printf("[效果] 用法：::effect state <主语>\n"); return 1; }
        Token *t = pool_find(ai->pool, s);
        if (!t) { printf("[效果] 图里没有「%s」\n", s); return 1; }
        int n = 0;
        printf("[效果] 「%s」的状态（关系 / 值 / 计数 / 时刻）：\n", s);
        for (size_t i = 0; i < t->count; ++i) {
            const AssocEntry *e = &token_assocs_ro(t)[i];
            if (!e->main || !e->dyn) continue;
            const char *nm = rel_dyn_name(ai, (uint8_t)(REL_DYN_BASE + e->dyn - 1));
            printf("  %s = %s（计数 %u，tick %llu）\n", nm ? nm : "?",
                   e->main->name ? e->main->name : "?", e->hits,
                   (unsigned long long)e->last_touch_tick);
            n++;
        }
        if (!n) printf("  （没有状态边）\n");
        return 1;
    }
    if (!strncmp(arg, "log", 3)) {
        FILE *f = fopen("_t/effects.tsv", "rb");
        if (!f) { printf("[效果] 还没有执行记录\n"); return 1; }
        char line[512]; int n = 0;
        while (fgets(line, sizeof line, f) && n < 12) { printf("  %s", line); n++; }
        fclose(f);
        return 1;
    }
    int do_retract = !strncmp(arg, "retract", 7);
    int do_event = !strncmp(arg, "event", 5);
    int do_apply = !strncmp(arg, "apply", 5) || do_retract || do_event;
    if (!do_apply) { printf("[效果] 只认 apply / event / state / trace / retract / log\n"); return 1; }
    const char *rest = arg + (do_retract ? 7 : (do_event ? 5 : 5));
    if (do_event) {
        const char *p = rest;
        while (*p == ' ') p++;
        /* ::effect event <关系> <主语> <宾语>：走同一条 apply 逻辑，成功后再具体化事件 */
        rest = p;
    }
    while (*rest == ' ') rest++;
    int force = 0;
    char buf[512];
    snprintf(buf, sizeof buf, "%s", rest);
    char *fp = strstr(buf, "--force");
    if (fp) { force = 1; *fp = 0; }
    char *tok[4] = {0}; int nw = 0;
    for (char *p = buf; *p && nw < 4; ) {
        while (*p == ' ' || *p == '\t') p++;
        if (!*p) break;
        tok[nw++] = p;
        while (*p && *p != ' ' && *p != '\t') p++;
        if (*p) *p++ = 0;
    }
    if (nw < 3) { printf("[效果] 用法：::effect %s <关系> <主语> <宾语>\n", do_retract ? "retract" : "apply"); return 1; }
    if (aip_policy_int("effect_enable", 1) == 0) {
        printf("[效果] 策略关闭（effect_enable=0），不执行\n");
        return 1;
    }
    if (!sym_write_gate()) return 1;
    if (!g_sym_reason[0]) { printf("[效果] 必须给理由：先 ::sym reason <为什么>\n"); return 1; }

    const RelSchema *sc = rel_schema_by_name(tok[0]);
    if (!sc) { printf("[效果] 关系「%s」没有 schema，效果无定义，不执行\n", tok[0]); return 1; }
    if (!sc->post[0][0]) { printf("[效果] 关系「%s」没有 post 模板，不执行\n", tok[0]); return 1; }

    Token *a1 = pool_find(ai->pool, tok[1]);
    Token *a2 = pool_find(ai->pool, tok[2]);
    if (!a1 || !a2) {
        printf("[效果] 图里没有「%s」，先教这个词（不造脏实体）\n", !a1 ? tok[1] : tok[2]);
        return 1;
    }
    /* 约束（defeasible）：违反 → “奇怪”，默认拒绝；--force 才落。P1 起同时查 pred.h 谓词原子。 */
    if ((int)aip_policy_int("role_constraint", 1) != 0) {
        for (uint8_t k = 0; k < sc->n_roles && k < REL_SCHEMA_ROLES; ++k) {
            if (!sc->cons[k][0]) continue;
            char note[192];
            int st = effect_cons_status(ai, sc, k, a1, a2, note, sizeof note);
            if (st == 1 || st == 3) continue;
            printf("[效果] 奇怪：约束「%s」%s%s\n", sc->cons[k], note,
                   force ? "；--force ⇒ 仍然执行（已记账）" : "；不执行");
            effect_log("%llu\t%s\t%s\t%s\t%s\t约束不满足:%s\n",
                       (unsigned long long)(ai->pool ? ai->pool->current_tick : 0),
                       sc->name, tok[1], tok[2], force ? "force" : "refused", sc->cons[k]);
            if (!force) return 1;
        }
    }

    int did = 0;
    for (uint8_t k = 0; k < REL_SCHEMA_ROLES && sc->post[k][0]; ++k) {
        char nm[32], val[64]; int sel = 0;
        if (!effect_parse_post(sc->post[k], nm, sizeof nm, &sel, val, sizeof val)) {
            printf("[效果] post 模板看不懂：%s（跳过）\n", sc->post[k]);
            continue;
        }
        Token *subj = (sel == 1) ? a1 : a2;
        Token *vt = pool_token_intern(ai->pool, val);
        uint8_t rid = rel_id_of(ai, nm, 1);
        if (!rid || !vt) { printf("[效果] 建不了状态谓词「%s」\n", nm); continue; }
        uint8_t dyn = (uint8_t)(rid - REL_DYN_BASE + 1);
        if (do_retract) {
            int rm = effect_retract_edge(subj, dyn, vt);
            printf("[效果] 撤销 %s.%s = %s：%s\n", subj->name, nm, val, rm ? "已撤" : "本来就没有");
            effect_log("%llu\t%s\t%s\t%s\tretract:%s\t%s\n",
                       (unsigned long long)(ai->pool ? ai->pool->current_tick : 0),
                       sc->name, tok[1], tok[2], rm ? "removed" : "absent", g_sym_reason);
            did += rm;
        } else {
            uint32_t before = effect_edge_hits(subj, dyn, vt);
            /* 效果是**状态断言**，必须同步落图（不能进 micro 审查队列等下一轮）：
             * 执行器本身已经过 ::sym write on + 理由闸门，并在 _t/effects.tsv 记账。 */
            int saved_route = ai->route_writes;
            ai->route_writes = 0;
            int rc = ai_write_rel(ai, subj, vt, rid, 0, AI_WSRC_RELATION);
            ai->route_writes = saved_route;
            if (rc == 0 && before) effect_bump_edge(subj, dyn, vt);   /* 幂等 + 计数 */
            uint32_t after = effect_edge_hits(subj, dyn, vt);
            printf("[效果] %s.%s = %s：%s（%s；计数 %u）\n",
                   subj->name, nm, val,
                   rc == 0 ? "已写入" : "写入失败",
                   before ? "重复应用只计数、不重复造边" : "新状态",
                   after ? after : before);
            effect_log("%llu\t%s\t%s\t%s\tassert:%s\t%s\t理由:%s\n",
                       (unsigned long long)(ai->pool ? ai->pool->current_tick : 0),
                       sc->name, tok[1], tok[2], nm, val, g_sym_reason);
            did += (rc == 0);
        }
    }
    if (!did) printf("[效果] 没有可执行的效果（模板为空/全部失败）\n");
    if (do_event && did) {
        char ev[256];
        effect_event_name(ev, sizeof ev, sc->name, tok[1], tok[2]);
        Token *et = pool_token_intern(ai->pool, ev);
        uint8_t rrid = rel_id_of(ai, "结果", 1);
        int links = 0;
        if (et && rrid) {
            for (uint8_t k = 0; k < REL_SCHEMA_ROLES && sc->post[k][0]; ++k) {
                char nm[32], val[64]; int sel = 0;
                if (!effect_parse_post(sc->post[k], nm, sizeof nm, &sel, val, sizeof val)) continue;
                const char *arg = (sel == 1) ? tok[1] : tok[2];
                char st[256];
                snprintf(st, sizeof st, "[状态:%s(%s,%s)]", nm, arg, val);
                Token *stt = pool_token_intern(ai->pool, st);
                if (!stt) continue;
                int saved_route = ai->route_writes;
                ai->route_writes = 0;
                int rc = ai_write_rel(ai, et, stt, rrid, 0, AI_WSRC_RELATION);
                ai->route_writes = saved_route;
                if (rc == 0) links++;
            }
        }
        printf("[效果] 事件已具体化：%s（结果边 %d 条；结果关系 id=%u，**普通关系边**）\n",
               ev, links, rrid);
        effect_log("%llu\t%s\t%s\t%s\tevent:%s\t结果边:%d\t理由:%s\n",
                   (unsigned long long)(ai->pool ? ai->pool->current_tick : 0),
                   sc->name, tok[1], tok[2], ev, links, g_sym_reason);
    }
    return 1;
}

#endif /* EFFECT_H */
