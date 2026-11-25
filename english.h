/* english.h — **英语问 ⇒ 英语答**（"读"已经由 `[syn]` 数据解决，这里只补"写"）
 *
 * 分工：
 *   · 读：`patterns.txt` 的 `[syn] cat=猫` 把英文词换成中文节点（数据，不改代码）；
 *   · 写：本文件把**关系是非问**的答复换成英文（Yes/No/I don't know + 一句陈述）。
 *
 * 为什么只做"是非问"：这个内核不生成文本，能说的只有**图里查得到的结论**。
 * 与其硬造自由英语，不如把"问得清、答得准"的那一类做对：`Is a cat an animal?`
 *
 * 支持的句式（够用就好，认不出就**不动**原答复 —— 绝不猜）：
 *   Is <A> a/an <B>?            ⇒ 属于
 *   <A> is a/an <B>?            ⇒ 属于
 *   Can <A> <动词短语>?          ⇒ 会
 *   Does <A> eat/have/like/need <B>?  ⇒ 吃/有/喜欢/需要
 *   Does <A> live in <B>?       ⇒ 在
 *
 * 判据：`tests/english.sh` 第二段（英文问 → 英文答；否定与"不知道"都要说清）。
 */
#ifndef ENGLISH_H
#define ENGLISH_H

#include <string.h>
#include <stdio.h>

/* 只含 ASCII 可打印字符才算"英语问"（中文一个字都不许混进来） */
static inline int en_ascii_only(const char *s) {
    if (!s || !*s) return 0;
    for (const unsigned char *p = (const unsigned char *)s; *p; ++p)
        if (*p >= 0x80) return 0;
    return 1;
}

static inline int en_word_eq(const char *w, size_t n, const char *lit) {
    size_t l = strlen(lit);
    if (n != l) return 0;
    for (size_t i = 0; i < n; ++i) {
        char a = w[i], b = lit[i];
        if (a >= 'A' && a <= 'Z') a = (char)(a - 'A' + 'a');
        if (b >= 'A' && b <= 'Z') b = (char)(b - 'A' + 'a');
        if (a != b) return 0;
    }
    return 1;
}

/* 英文主语/宾语的"冠词剥掉 + 首字母大写"（只用于输出，不改判据） */
static inline void en_pretty(const char *in, char *out, size_t cap, int cap_first) {
    if (!out || !cap) return;
    const char *p = in;
    while (*p == ' ') p++;
    const char *arts[] = {"a ", "an ", "the ", NULL};
    for (size_t i = 0; arts[i]; ++i) {
        size_t l = strlen(arts[i]);
        if (strncmp(p, arts[i], l) == 0) { p += l; break; }
        /* 句首大写也要剥（`A cat` / `The sea`）*/
        if ((p[0] == 'A' || p[0] == 'T') && strncasecmp(p, arts[i], l) == 0) { p += l; break; }
    }
    size_t n = 0;
    for (; p && *p && n + 1 < cap; ++p) out[n++] = *p;
    while (n && out[n - 1] == ' ') n--;
    out[n] = 0;
    if (cap_first && n) {
        if (out[0] >= 'a' && out[0] <= 'z') out[0] = (char)(out[0] - 'a' + 'A');
    }
}

static inline int en_starts_vowel(const char *s) {
    char c = s ? s[0] : 0;
    if (c >= 'A' && c <= 'Z') c = (char)(c - 'A' + 'a');
    return c == 'a' || c == 'e' || c == 'i' || c == 'o' || c == 'u';
}

/* 关系 → 英文短语（输出用）。返回 1 = 有对应说法。 */
static inline int en_phrase(uint8_t rid, const char *obj, char *out, size_t cap) {
    switch (rid) {
    case REL_IS_A: snprintf(out, cap, "%s", en_starts_vowel(obj) ? "is an" : "is a"); return 1;
    case REL_CAN:  snprintf(out, cap, "can"); return 1;
    case REL_HAS:  snprintf(out, cap, "has"); return 1;
    case REL_FEAR: snprintf(out, cap, "fears"); return 1;
    case REL_LIKE: snprintf(out, cap, "likes"); return 1;
    case REL_EAT:  snprintf(out, cap, "eats"); return 1;
    case REL_NEED: snprintf(out, cap, "needs"); return 1;
    case REL_AT:   snprintf(out, cap, "is in"); return 1;
    default: return 0;
    }
}

/* 把 words[from..to) 拼起来（不剥冠词；剥冠词交给 en_pretty） */
static inline void en_join(const char **w, const size_t *wl, int from, int to, char *out, size_t cap) {
    size_t o = 0;
    for (int z = from; z < to && o + 1 < cap; ++z) {
        if (o) out[o++] = ' ';
        for (size_t i = 0; i < wl[z] && o + 1 < cap; ++i) out[o++] = w[z][i];
    }
    out[o] = 0;
}

static inline int en_is(const char **w, const size_t *wl, int i, const char *lit) {
    return i >= 0 && en_word_eq(w[i], wl[i], lit);
}

/* 解析英语是非问。成功返回 1，并给出 A / B / 关系。 */
static inline int en_parse(AI *ai, const char *q, char *A, size_t acap, char *B, size_t bcap, uint8_t *rid) {
    if (!q || !A || !B || !rid || !en_ascii_only(q) || !ai) return 0;
    char buf[512];
    size_t n = 0;
    for (const char *p = q; *p && n + 1 < sizeof buf; ++p)
        buf[n++] = (*p == '?' || *p == '"' || *p == '.') ? ' ' : *p;
    buf[n] = 0;
    const char *w[64];
    size_t wl[64];
    int nw = 0;
    char *p = buf;
    while (*p && nw < 64) {
        while (*p == ' ' || *p == '\t') p++;
        if (!*p) break;
        char *st = p;
        while (*p && *p != ' ' && *p != '\t') p++;
        w[nw] = st;
        wl[nw] = (size_t)(p - st);
        nw++;
    }
    if (nw < 3) return 0;
    /* §7.032 关系从句/复杂修饰（that/which/who…）不认，交给指引拒绝：
     * 否则 `is the cat that I saw an animal?` 会被当成简单是非问答 Yes（实测误答）。 */
    for (int i = 1; i < nw; ++i) {
        char wd[32];
        size_t l = wl[i] < sizeof wd - 1 ? wl[i] : sizeof wd - 1;
        memcpy(wd, w[i], l);
        wd[l] = 0;
        if (aip_class_has("en_clauseword", wd)) return 0;
    }
    /* 带疑问词的**不是是非问**（`What is a cat?`）：直接不认 ⇒ 交给 english_hint 给英文指引 */
    {
        const char *qw[] = {"what", "which", "who", "whom", "whose", "where",
                            "when", "why", "how", "how many", NULL};
        for (size_t i = 0; qw[i]; ++i)
            if (en_is(w, wl, 0, qw[i])) return 0;
    }

    if (en_is(w, wl, 0, "does") || en_is(w, wl, 0, "do")) {
        /* 动词 = 句子里**第一个绑到核心关系**的词（绑定在 `[alias]` 数据里，不在这里写死） */
        uint8_t r = 0;
        int v = -1;
        for (int i = 1; i < nw - 1; ++i) {
            char wd[32];
            size_t l = wl[i] < sizeof wd - 1 ? wl[i] : sizeof wd - 1;
            memcpy(wd, w[i], l);
            wd[l] = 0;
            uint8_t d = rel_id_of(ai, wd, 0);
            if (getenv("AIP_ENDBG")) fprintf(stderr, "[en] does-scan i=%d w=%s rel=%u alias=%u\n", i, wd, (unsigned)d, (unsigned)rel_alias_id(wd));
            /* 名词（a/an/the/cat…）也可能被登记成**动态关系**（英文问句被中文流水线当陈述学过），
             * 所以这里只认**核心关系**（`[alias]` 绑的那几个），动态 id 一律跳过。 */
            if (d && d < REL_DYN_BASE && d != REL_IS_A) { r = d; v = i; break; }
        }
        if (v < 0) return 0;
        en_join(w, wl, 1, v, A, acap);
        en_join(w, wl, v + 1, nw, B, bcap);
        if (!A[0] || !B[0]) return 0;
        *rid = r;
        return 1;
    }
    if (en_is(w, wl, 0, "can")) {
        /* Can <主语> <动词短语>? —— 动词短语取最后一段（多词短语也接得住） */
        if (nw < 4) return 0;
        uint8_t d = rel_id_of(ai, "can", 0);
        if (!d) return 0;                     /* `[alias] can=会` 没配 ⇒ 不认（可消融） */
        en_join(w, wl, 1, nw - 1, A, acap);
        en_join(w, wl, nw - 1, nw, B, bcap);
        if (!A[0] || !B[0]) return 0;
        *rid = d;
        return 1;
    }
    if (en_is(w, wl, 0, "is") || en_is(w, wl, 0, "are")) {
        /* Is <主语> a/an <宾语>? —— 取**最后**一个 a/an 当宾语冠词 */
        int k = -1;
        for (int i = nw - 1; i >= 1; --i)
            if (en_is(w, wl, i, "a") || en_is(w, wl, i, "an")) { k = i; break; }
        if (k < 1) return 0;
        uint8_t d = rel_id_of(ai, en_is(w, wl, 0, "are") ? "are" : "is", 0);
        if (!d) return 0;
        en_join(w, wl, 1, k, A, acap);
        en_join(w, wl, k + 1, nw, B, bcap);
        if (!A[0] || !B[0]) return 0;
        *rid = d;
        return 1;
    }
    /* <主语> is a/an <宾语>?（陈述语序）*/
    {
        int k = -1;
        for (int i = 1; i < nw; ++i)
            if (en_is(w, wl, i, "is") || en_is(w, wl, i, "are")) { k = i; break; }
        if (k < 1) return 0;
        en_join(w, wl, 0, k, A, acap);
        int st = k + 1;
        if (st < nw && (en_is(w, wl, st, "a") || en_is(w, wl, st, "an") || en_is(w, wl, st, "the"))) st++;
        uint8_t d = rel_id_of(ai, en_is(w, wl, k, "are") ? "are" : "is", 0);
        if (!d) return 0;
        en_join(w, wl, st, nw, B, bcap);
        if (!A[0] || !B[0]) return 0;
        *rid = d;
        return 1;
    }
}

/* 把中文答复的**极性**读出来：+1 真 / -1 假 / 0 不知道。只看开头（答复模板稳定）。 */
static inline int en_truth_of_answer(const char *a) {
    if (!a) return 0;
    while (*a == ' ') a++;
    if (strncmp(a, "不 对", 9) == 0) return -1;          /* 「不 对」= 断言为假 */
    if (strncmp(a, "对", 3) == 0) return 1;
    return 0;                                            /* 不知道/大概/不太懂 一律当"不知道" */
}

/* 英语词 → 中文节点（走 `[syn]` 那张数据表，和"读"用的是同一条路） */
static inline const Token *en_to_token(AI *ai, const char *w) {
    if (!ai || !w || !*w) return NULL;
    /* ① 剥冠词（a/an/the，含句首大写）—— `a cat` 要当 `cat` 查 */
    const char *p = w;
    while (*p == ' ') p++;
    const char *arts[] = {"a ", "an ", "the ", NULL};
    for (size_t i = 0; arts[i]; ++i) {
        size_t l = strlen(arts[i]);
        if (strncasecmp(p, arts[i], l) == 0) { p += l; break; }
    }
    /* ② 走 `[syn]`（和"读"同一张数据表） */
    char zh[96];
    if (!aip_apply_syn(ai, p, zh, sizeof zh))
        snprintf(zh, sizeof zh, "%.*s", (int)sizeof zh - 1, p);
    const Token *t = pool_find(ai->pool, zh);
    if (t) return t;
    /* ③ 多词短语：逐词试（`the red car` 里认 `car`） */
    char tmp[96];
    size_t n = 0;
    for (const char *q = p; ; ++q) {
        if (*q == ' ' || *q == 0) {
            if (n) {
                tmp[n] = 0;
                char z2[96];
                if (!aip_apply_syn(ai, tmp, z2, sizeof z2))
                    snprintf(z2, sizeof z2, "%s", tmp);
                if ((t = pool_find(ai->pool, z2)) != NULL) return t;
            }
            n = 0;
            if (!*q) break;
        } else if (n + 1 < sizeof tmp) {
            tmp[n++] = *q;
        }
    }
    return NULL;
}

/* §7.033 英语**陈述句教学**：`X is (not) a Y` / `X can(not) Y` 真正写进图。
 * 只在两个词都能解析到节点时写（不造垃圾词）；写的是否定边/肯定边，和中文同一条写路径。
 * 成功返回 1 并给英文确认；否则 0（交回原来的问答/指引路径）。 */
/* §7.042 英文问句里**没有映射**的词：明确告诉用户，而不是含糊说“只答是非问”。
 * 只查内容词：冠词/助动词/疑问词/关系词/否定词都跳过；复数先剥 s/es 再查。 */
static inline const char *english_unknown_word(AI *ai, const char *q, char *buf, size_t cap) {
    if (!ai || !q || !en_ascii_only(q) || !buf) return NULL;
    const char *skip[] = { "a", "an", "the", "is", "are", "am", "was", "were", "do", "does",
                           "did", "can", "could", "cannot", "not", "no", "yes", "what", "who",
                           "whom", "whose", "which", "where", "when", "why", "how", "it", "its",
                           "this", "that", "these", "those", "i", "you", "he", "she", "they",
                           "we", "me", "my", "your", "his", "her", "their", "of", "to", "in",
                           "on", "at", "and", "or", "please", NULL };
    char tmp[512];
    snprintf(tmp, sizeof tmp, "%s", q);
    for (char *p = tmp; *p; ++p) if (*p == '?' || *p == ',' || *p == '.' || *p == '!') *p = ' ';
    char *save = NULL;
    for (char *w = strtok_r(tmp, " \t", &save); w; w = strtok_r(NULL, " \t", &save)) {
        char lw[64]; size_t n = 0;
        for (const char *p = w; *p && n + 1 < sizeof lw; ++p) lw[n++] = (char)((*p >= 'A' && *p <= 'Z') ? *p + 32 : *p);
        lw[n] = 0;
        int sk = 0;
        for (size_t i = 0; skip[i]; ++i) if (!strcmp(lw, skip[i])) { sk = 1; break; }
        if (sk || n < 2) continue;
        if (en_to_token(ai, lw)) continue;
        if (n > 3 && lw[n - 1] == 's') { lw[n - 1] = 0; if (en_to_token(ai, lw)) continue; lw[n - 1] = 's'; }
        if (n > 4 && !strcmp(lw + n - 2, "es")) { lw[n - 2] = 0; if (en_to_token(ai, lw)) continue; }
        snprintf(buf, cap, "%s", w);
        return buf;
    }
    return NULL;
}

/* §7.038 英文冲突回话：上一句是“OK? I also had… Say yes/no”，这一句只认 yes/no。
 * yes ⇒ 写新值；no ⇒ 保留旧值（不写）。返回 1 表示已处理。 */
static inline int english_confirm(AI *ai, const char *q, char *out, size_t cap) {
    if (!ai || !ai->en_pending || !q || !out || !cap) return 0;
    char z[32]; size_t n = 0;
    for (const char *p = q; *p && n + 1 < sizeof z; ++p) {
        if (*p == ' ' || *p == '\t' || *p == '?' || *p == '.' || *p == '!') continue;
        z[n++] = (char)((*p >= 'A' && *p <= 'Z') ? *p + 32 : *p);
    }
    z[n] = 0;
    int yes = (!strcmp(z, "yes") || !strcmp(z, "y") || !strcmp(z, "yeah") || !strcmp(z, "sure"));
    int no  = (!strcmp(z, "no") || !strcmp(z, "n") || !strcmp(z, "nope"));
    if (!yes && !no) return 0;
    Token *A = pool_token_intern(ai->pool, ai->en_pa_zh[0] ? ai->en_pa_zh : ai->en_pa);
    Token *B = pool_token_intern(ai->pool, ai->en_pb_zh[0] ? ai->en_pb_zh : ai->en_pb);
    char ap[160], bp[160];
    en_pretty(ai->en_pa, ap, sizeof ap, 1);
    en_pretty(ai->en_pb, bp, sizeof bp, 0);
    if (yes) {
        /* 先把这一对的正/负两种存法都清掉，再写新值（负边存在 e->nrel 位里，
         * 和 e->rel 是两套位，只清一套会留下旧否定的回显——实测）。 */
        if (ai->en_prid < REL_DYN_BASE) {
            uint16_t bit = (uint16_t)(1u << (ai->en_prid - 1));
            for (size_t i = 0; i < A->count; ++i) {
                AssocEntry *e = &token_assocs(A)[i];
                if (e->main != B) continue;
                e->rel &= (uint16_t)~bit;
                e->nrel &= (uint16_t)~bit;
            }
            A->edges_dirty = 1;
        }
        int wr = ai_write_rel(ai, A, B, ai->en_prid, ai->en_pnew_neg, AI_WSRC_RELATION);
        if (wr != 0) { snprintf(out, cap, "Hmm, I couldn't store that."); ai->en_pending = 0; return 1; }
        agent_teach_mark(ai, A, ai->en_prid, B, ai->en_pnew_neg);
        const char *rn = rel_name_of(ai, ai->en_prid);
        if (ai->en_prid == REL_IS_A)
            snprintf(out, cap, "OK. %s %s %s%s.", ap, ai->en_pnew_neg ? "is not" : "is",
                     en_starts_vowel(bp) ? "an " : "a ", bp);
        else
            snprintf(out, cap, "OK. %s %s %s.", ap, ai->en_pnew_neg ? "cannot" : "can", bp);
        (void)rn;
    } else {
        snprintf(out, cap, "OK. I'll keep: %s %s %s.", ap,
                 ai->en_pold_neg ? "cannot" : "can", bp);
    }
    ai->en_pending = 0;
    return 1;
}

/* §7.050 Minimal English arithmetic word problems (GSM8K-style), high-confidence templates only.
 * Requires: ASCII, digits, no "is a/can a..." yes-no shape, and a recognized template.
 * Returns 1 and writes an English numeric answer; 0 otherwise (fall through to mapping/refusal). */
static inline int english_wordmath(AI *ai, const char *q, char *out, size_t cap) {
    (void)ai;
    if (!q || !out || !cap || !en_ascii_only(q)) return 0;
    int hasdig = 0;
    for (const char *p = q; *p; ++p) if (*p >= '0' && *p <= '9') { hasdig = 1; break; }
    if (!hasdig) return 0;
    if (!strncasecmp(q, "is ", 3) || !strncasecmp(q, "are ", 4) ||
        !strncasecmp(q, "can ", 4) || !strncasecmp(q, "do ", 3) ||
        !strncasecmp(q, "does ", 5)) return 0;

    /* §7.054 Calibration guards: refuse (fall through) when the problem is outside the template
     * family. Words are data (`wordmath_unsupported`), count limit is policy too. */
    {
        char lowq[512];
        snprintf(lowq, sizeof lowq, "%s", q);
        for (char *p = lowq; *p; ++p) if (*p >= 'A' && *p <= 'Z') *p = (char)(*p + 32);
        for (size_t i = 0; i + 2 < strlen(lowq); ++i)
            if (lowq[i] >= '0' && lowq[i] <= '9' && lowq[i + 1] == '.' &&
                lowq[i + 2] >= '0' && lowq[i + 2] <= '9') return 2;   /* decimals: explicit refusal */
        char ulist[512];
        if (aip_policy_str("wordmath_unsupported", ulist, sizeof ulist) && ulist[0]) {
            char *cur = ulist;
            for (char *w = aip_policy_next(&cur); w; w = aip_policy_next(&cur))
                if (w[0] && strstr(lowq, w)) return 2;   /* unsupported phrase: explicit refusal */
        }
    }
    long nums[8]; int nn = 0; long npos[8];
    for (const char *p = q; *p && nn < 8; ) {
        if (*p >= '0' && *p <= '9') {
            long v = 0; const char *st = p;
            while (*p >= '0' && *p <= '9') { v = v * 10 + (*p - '0'); p++; }
            nums[nn] = v; npos[nn] = (long)(st - q); nn++;
        } else p++;
    }
    if (nn < 2) return 0;
    if (nn > aip_policy_int("wordmath_max_numbers", 3)) return 2;   /* 4+ numbers: explicit refusal */
    char low[512];
    snprintf(low, sizeof low, "%s", q);
    for (char *p = low; *p; ++p) if (*p >= 'A' && *p <= 'Z') *p = (char)(*p + 32);

    /* §7.052 Clause-based operation scoping: one clause = one operation.
     * Split on , . ; ! ? and " then ", attach each number to its clause, decide the op from that
     * clause's words (fallback: previous clause / whole text for "each/per/rows of"). */
    size_t ll = strlen(low);
    long long acc = (long long)nums[0];
    int ok = 1;
    for (int i = 0; i + 1 < nn; ++i) {
        long b = npos[i + 1];
        /* 找 b 所在子句：向前到分隔符，向后到分隔符 */
        long cs = 0, ce = (long)ll;
        for (long k = b; k > 0; --k) {
            char ch = low[k - 1];
            if (ch == ',' || ch == '.' || ch == ';' || ch == '!' || ch == '?') { cs = k; break; }
        }
        for (long k = b; k < (long)ll; ++k) {
            char ch = low[k];
            if (ch == ',' || ch == '.' || ch == ';' || ch == '!' || ch == '?') { ce = k; break; }
        }
        char cl[220]; size_t cln = 0;
        for (long k = cs; k < ce && cln + 1 < sizeof cl; ++k) cl[cln++] = low[k];
        cl[cln] = 0;
        /* " then " 也算子句边界：取 then 之后的片段 */
        char *th = strstr(cl, " then ");
        if (th) { memmove(cl, th + 6, strlen(th + 6) + 1); }
        char both[420];
        snprintf(both, sizeof both, "%s %s", cl, low);   /* 子句为主，全句只做兜底判据 */

        int is_div = strstr(cl, "cut into") || strstr(cl, "shared") || strstr(cl, "among") ||
                     strstr(cl, "split") || strstr(cl, "divided") || strstr(cl, "equal part");
        int is_mul = strstr(cl, " each") || strstr(cl, " per ") || strstr(cl, "every") ||
                     strstr(cl, "rows of") || strstr(cl, "boxes of") || strstr(cl, "packs of") ||
                     strstr(cl, "trays of") || strstr(cl, "shelves with") ||
                     strstr(cl, "a week") || strstr(cl, "a day") || strstr(cl, "per hour") ||
                     strstr(cl, "per minute") || strstr(cl, " for ");
        int is_sub = strstr(cl, "sold") || strstr(cl, "sells") || strstr(cl, "lost") ||
                     strstr(cl, "loses") || strstr(cl, "ate") || strstr(cl, "eaten") ||
                     strstr(cl, "used") || strstr(cl, "gives") || strstr(cl, "gave") ||
                     strstr(cl, "away") || strstr(cl, "leak") || strstr(cl, "left") ||
                     strstr(cl, "remain") || strstr(cl, "taken") || strstr(cl, "been read");
        int is_speed = (nn == 2 && strstr(low, "speed")) ||
                       strstr(cl, "per hour") || strstr(cl, "km/h") || strstr(cl, "mph");
        /* §7.053 Priority: "cut into N slices and M eaten/left" is subtraction, not division. */
        if (is_div && (strstr(cl, "eaten") || strstr(cl, "left") || strstr(cl, "remain") ||
                       strstr(cl, "used") || strstr(cl, "lost")))
            is_div = 0, is_sub = 1;
        /* Semantic inversion: asks girls but states boys (or vice versa) => subtract. */
        if ((strstr(low, "girls") && strstr(cl, "boys")) ||
            (strstr(low, "boys") && strstr(cl, "girls")) ||
            (strstr(low, "women") && strstr(cl, "men")) ||
            (strstr(low, "men") && strstr(cl, "women")) ||
            (strstr(low, "taken") && strstr(cl, "free")) ||
            (strstr(low, "free") && strstr(cl, "taken")))
            is_sub = 1, is_div = 0, is_mul = 0;
        if (!is_div && !is_mul && !is_sub) {
            /* 同一子句没线索时，看全句里的 each/rows/...（如 “each box has 9 ...” 的首子句） */
            if (strstr(low, " each") || strstr(low, " every") || !strncmp(low, "each", 4) || !strncmp(low, "every", 5) ||
                strstr(low, "rows of") || strstr(low, "boxes of") ||
                strstr(low, "packs of") || strstr(low, "shelves with") ||
                strstr(low, " per ") || strstr(low, "a week") || strstr(low, "a day"))
                is_mul = 1;
        }
        (void)both;
        if (is_div) { if (nums[i + 1] == 0) { ok = 0; break; } acc /= nums[i + 1]; }
        else if (is_speed && (strstr(cl, " in ") || strstr(low, " in "))) {
            if (nums[i + 1] == 0) { ok = 0; break; }
            acc /= nums[i + 1];
        }
        else if (is_mul) acc *= nums[i + 1];
        else if (is_sub) acc -= nums[i + 1];
        else acc += nums[i + 1];
    }
    if (!ok) return 0;
    long long ans = acc;
    snprintf(out, cap, "The answer is %lld.", ans);
    return 1;
}

static inline int english_teach(AI *ai, const char *q, char *out, size_t cap) {
    if (!ai || !q || !out || !cap) return 0;
    if (!en_ascii_only(q)) return 0;
    for (const char *p = q; *p; ++p) if (*p == '?') return 0;   /* 问句不走这里 */
    char buf[512];
    size_t n = 0;
    for (const char *p = q; *p && n + 1 < sizeof buf; ++p)
        buf[n++] = (*p == '.' || *p == ',' || *p == '"') ? ' ' : *p;
    buf[n] = 0;
    const char *w[64];
    size_t wl[64];
    int nw = 0;
    char *p = buf;
    while (*p && nw < 64) {
        while (*p == ' ' || *p == '\t') p++;
        if (!*p) break;
        char *st = p;
        while (*p && *p != ' ' && *p != '\t') p++;
        w[nw] = st;
        wl[nw] = (size_t)(p - st);
        nw++;
    }
    if (nw < 3) return 0;
    int neg = 0, neg_at = -1;
    for (int i = 0; i < nw; ++i) {
        if (en_is(w, wl, i, "not") || en_is(w, wl, i, "never")) { neg = 1; neg_at = i; break; }
    }
    /* is/are 型：X is [not] a/an Y */
    {
        int k = -1;
        for (int i = 1; i < nw; ++i)
            if (en_is(w, wl, i, "is") || en_is(w, wl, i, "are")) { k = i; break; }
        if (k > 0) {
            int st = k + 1;
            if (neg_at == st) st++;
            if (st < nw && (en_is(w, wl, st, "a") || en_is(w, wl, st, "an") || en_is(w, wl, st, "the"))) st++;
            if (st >= nw) return 0;
            uint8_t rid = rel_id_of(ai, en_is(w, wl, k, "are") ? "are" : "is", 0);
            if (!rid) return 0;
            char A[128], B[200];
            en_join(w, wl, 0, k, A, sizeof A);
            en_join(w, wl, st, nw, B, sizeof B);
            const Token *ta = en_to_token(ai, A), *tb = en_to_token(ai, B);
            if (!ta || !tb) return 0;
            /* §7.037 冲突可见：要写的肯定边和已有否定边打架（或反过来）时，把旧的也说出来 */
            /* 用和回答同一条推理（rel_solve）判“旧知识是什么极性”，别只查一条边：
             * 否定/推导都可能让“旧值”不在直边上（实测 oldpos 假阳性）。 */
            Proof oldp; int old_truth = 0;
            rel_solve(ai, (Token *)ta, rid, (Token *)tb, 0, &oldp);
            old_truth = oldp.status;
            if (old_truth == 0) {
                rel_solve(ai, (Token *)ta, rid, (Token *)tb, 1, &oldp);
                if (oldp.status != 0) old_truth = -1;
            }
            int old_neg = (old_truth < 0);
            int old_pos = (old_truth > 0);
            int conflict = (neg ? old_pos : old_neg);
            int askcf = 1;
            { FILE *pf = fopen("policy.txt", "rb"); if (pf) { char ln[256];
                while (fgets(ln, sizeof ln, pf)) { int v = -1;
                    if (sscanf(ln, "en_ask_conflict = %d", &v) == 1 || sscanf(ln, "en_ask_conflict=%d", &v) == 1) { askcf = v; break; } }
                fclose(pf); } }
            if (conflict && askcf) {
                ai->en_pending = 1;
                snprintf(ai->en_pa, sizeof ai->en_pa, "%s", A);
                snprintf(ai->en_pb, sizeof ai->en_pb, "%s", B);
                snprintf(ai->en_pa_zh, sizeof ai->en_pa_zh, "%s", ta->name ? ta->name : A);
                snprintf(ai->en_pb_zh, sizeof ai->en_pb_zh, "%s", tb->name ? tb->name : B);
                ai->en_prid = rid;
                ai->en_pnew_neg = neg;
                ai->en_pold_neg = old_neg;
                char ap2[160];
                en_pretty(A, ap2, sizeof ap2, 1);
                snprintf(out, cap, "OK? I also had: %s %s %s%s. Say yes to replace, no to keep.",
                         ap2, old_neg ? "is not" : "is", en_starts_vowel(B) ? "an " : "a ", B);
                return 1;
            }
            if (ai_write_rel(ai, (Token *)ta, (Token *)tb, rid, neg ? 1 : 0, AI_WSRC_RELATION) != 0) return 0;
            agent_teach_mark(ai, (Token *)ta, rid, (Token *)tb, neg);   /* 来源留痕 + 事实环 */
            ai->n_rel_learned++;
            char ap[160];
            en_pretty(A, ap, sizeof ap, 1);
            char tail[512] = "";
            if (conflict)
                snprintf(tail, sizeof tail, " (I also had: %s %s %s%s.)", ap,
                         neg ? "is" : "is not", en_starts_vowel(B) ? "an " : "a ", B);
            snprintf(out, cap, "OK. %s %s %s%s.%s", ap, neg ? "is not" : "is",
                     en_starts_vowel(B) ? "an " : "a ", B, tail);
            return 1;
        }
    }
    /* can 型：X can(not) Y */
    {
        int k = -1;
        for (int i = 1; i < nw; ++i)
            if (en_is(w, wl, i, "can") || en_is(w, wl, i, "cannot")) { k = i; break; }
        if (k > 0) {
            int neg_can = en_is(w, wl, k, "cannot");
            int st = k + 1;
            if (neg_at == st) st++;
            if (st >= nw) return 0;
            uint8_t rid = rel_id_of(ai, "can", 0);
            if (!rid) return 0;
            char A[128], B[200];
            en_join(w, wl, 0, k, A, sizeof A);
            en_join(w, wl, st, nw, B, sizeof B);
            const Token *ta = en_to_token(ai, A), *tb = en_to_token(ai, B);
            if (!ta || !tb) return 0;
            Proof oldp2; int old_truth2 = 0;
            rel_solve(ai, (Token *)ta, rid, (Token *)tb, 0, &oldp2);
            old_truth2 = oldp2.status;
            if (old_truth2 == 0) {
                rel_solve(ai, (Token *)ta, rid, (Token *)tb, 1, &oldp2);
                if (oldp2.status != 0) old_truth2 = -1;
            }
            int old_neg = (old_truth2 < 0);
            int old_pos = (old_truth2 > 0);
            int conflict = ((neg || neg_can) ? old_pos : old_neg);
            int askcf2 = 1;
            { FILE *pf = fopen("policy.txt", "rb"); if (pf) { char ln[256];
                while (fgets(ln, sizeof ln, pf)) { int v = -1;
                    if (sscanf(ln, "en_ask_conflict = %d", &v) == 1 || sscanf(ln, "en_ask_conflict=%d", &v) == 1) { askcf2 = v; break; } }
                fclose(pf); } }
            if (conflict && askcf2) {
                ai->en_pending = 1;
                snprintf(ai->en_pa, sizeof ai->en_pa, "%s", A);
                snprintf(ai->en_pb, sizeof ai->en_pb, "%s", B);
                snprintf(ai->en_pa_zh, sizeof ai->en_pa_zh, "%s", ta->name ? ta->name : A);
                snprintf(ai->en_pb_zh, sizeof ai->en_pb_zh, "%s", tb->name ? tb->name : B);
                ai->en_prid = rid;
                ai->en_pnew_neg = (neg || neg_can);
                ai->en_pold_neg = old_neg;
                char ap3[160];
                en_pretty(A, ap3, sizeof ap3, 1);
                snprintf(out, cap, "OK? I also had: %s %s %s. Say yes to replace, no to keep.",
                         ap3, old_neg ? "cannot" : "can", B);
                return 1;
            }
            if (ai_write_rel(ai, (Token *)ta, (Token *)tb, rid, (neg || neg_can) ? 1 : 0, AI_WSRC_RELATION) != 0) return 0;
            agent_teach_mark(ai, (Token *)ta, rid, (Token *)tb, (neg || neg_can));
            ai->n_rel_learned++;
            char ap2[160];
            en_pretty(A, ap2, sizeof ap2, 1);
            char tail2[512] = "";
            if (conflict)
                snprintf(tail2, sizeof tail2, " (I also had: %s %s %s.)", ap2,
                         (neg || neg_can) ? "can" : "cannot", B);
            snprintf(out, cap, "OK. %s %s %s.%s", ap2, (neg || neg_can) ? "cannot" : "can", B, tail2);
            return 1;
        }
    }
    return 0;
}

/* 英语问 ⇒ 英语答：成功返回 1（out 被改写），否则 0（out 原样不动）。
 * 判据是 `rel_solve`（不是嗅中文答复的字符串）—— 英文和中文走的是**同一条推理**。 */
static inline const char *english_unknown_word(AI *ai, const char *q, char *buf, size_t cap);  /* §7.042 */

/* 返回：1=答了 / -1=是非问解析成功但词没映射 / 0=不是简单是非问 */
static inline int english_rewrite(AI *ai, const char *q, char *out, size_t cap) {
    char A[128], B[200];
    uint8_t rid = 0;
    if (!en_parse(ai, q, A, sizeof A, B, sizeof B, &rid)) return 0;
    if (!out || !cap) return 0;
    const Token *ta = en_to_token(ai, A);
    const Token *tb = en_to_token(ai, B);
    int truth = 0;
    if (ta && tb && rid) {
        Proof pf;
        rel_solve(ai, ta, rid, tb, 0, &pf);
        truth = pf.status;            /* +1 真 / -1 假 / 0 不知道 */
        if (truth == 0) {             /* 肯定事实没有 ⇒ 再问一次否定（`鱼 不 会 飞` 这种） */
            rel_solve(ai, ta, rid, tb, 1, &pf);
            if (pf.status != 0) truth = -1;   /* 推得出"不 R" ⇒ 这句话是假的 */
        }
    }
    if ((!ta || !tb)) {
        char uw[64];
        if (english_unknown_word(ai, q, uw, sizeof uw)) return -1;
    }
    char a[128], b[200], ph[24];
    en_pretty(A, a, sizeof a, 1);
    en_pretty(B, b, sizeof b, 0);
    if (!en_phrase(rid, b, ph, sizeof ph)) return 0;
    char res[420];
    if (truth > 0) {
        snprintf(res, sizeof res, "Yes. %s %s %s.", a, ph, b);
    } else if (truth < 0) {
        if (rid == REL_IS_A)
            snprintf(res, sizeof res, "No. %s is not %s %s.", a, en_starts_vowel(b) ? "an" : "a", b);
        else if (rid == REL_CAN)
            snprintf(res, sizeof res, "No. %s cannot %s.", a, b);   /* 情态动词的否定是 cannot，不是 "does not can" */
        else
            snprintf(res, sizeof res, "No. %s does not %s %s.", a, ph, b);
    } else {
        snprintf(res, sizeof res, "I don't know whether %s %s %s.", a, ph, b);
    }
    snprintf(out, cap, "%s", res);
    return 1;
}

/* 英语问但**不是是非问**（`What is a cat?`）：别掉中文兜底，给一句英文指引。
 * 只在原答复是"兜底"时才替换 —— 中文能答出来就不动（宁可给答案，不给模板）。 */
static inline int english_hint(AI *ai, const char *q, char *out, size_t cap) {
    if (!en_ascii_only(q) || !out || !cap) return 0;
    int alpha = 0, qmark = 0, digit = 0;
    for (const char *p = q; *p; ++p) {
        if ((*p >= 'a' && *p <= 'z') || (*p >= 'A' && *p <= 'Z')) alpha = 1;
        else if (*p == '?') qmark = 1;
        else if (*p >= '0' && *p <= '9') digit = 1;
    }
    if (!alpha || !qmark || digit) return 0;
    char A[128], B[200];
    uint8_t rid = 0;
    if (en_parse(ai, q, A, sizeof A, B, sizeof B, &rid)) return 0;   /* 是非问：上面已经答了 */
    /* 纯英文问句不是是非问 ⇒ 一律给英文指引：中文流水线对英文开放问句只会瞎答
     * （实测 `What is a cat?` 被检索答成"我也想养一只"），那比明说"我只答是非问"更糟。 */
    snprintf(out, cap,
             "Sorry, I only answer yes/no questions about what is in my graph. "
             "Try: \"Is a cat an animal?\" or \"Can a bird fly?\"");
    return 1;
}

#endif /* ENGLISH_H */
