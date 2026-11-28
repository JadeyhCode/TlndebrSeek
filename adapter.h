/* adapter.h — 语言适配器侧（§7.113 P4：把 [syn]/[affix] 从核里挪出来）
 *
 * 核只接 IR/规范词项；同义词/词缀这类**语言变体归一**属于适配器。
 * 本文件是**单二进制内的默认适配器实现**（数据仍来自 patterns.txt），
 * 表与替换逻辑都在这里；agent.h 只调用 aip_apply_syn()。
 * 回退：policy `adapter_syn=0` 时调用方跳过替换（逐字对照）。
 */
#ifndef ADAPTER_H
#define ADAPTER_H

#include "ai.h"

#define AIP_SYN_MAX 160
#define AIP_AFFIX_MAX 16
static char g_syn_from[AIP_SYN_MAX][48], g_syn_to[AIP_SYN_MAX][48];
static size_t g_syn_n;
static char g_aff[AIP_AFFIX_MAX][16];
static char g_aff_kind[AIP_AFFIX_MAX];      /* 'p' = 前缀，'s' = 后缀 */
static size_t g_aff_n;

static inline int adapter_syn_add(const char *from, const char *to) {
    if (!from || !to || !*from || !*to || g_syn_n >= AIP_SYN_MAX) return 0;
    if (strlen(from) >= sizeof g_syn_from[0] || strlen(to) >= sizeof g_syn_to[0]) return 0;
    snprintf(g_syn_from[g_syn_n], sizeof g_syn_from[0], "%s", from);
    snprintf(g_syn_to[g_syn_n], sizeof g_syn_to[0], "%s", to);
    g_syn_n++;
    return 1;
}

static inline int adapter_affix_add(const char *text, char kind) {
    if (!text || !*text || g_aff_n >= AIP_AFFIX_MAX) return 0;
    if (strlen(text) >= sizeof g_aff[0]) return 0;
    snprintf(g_aff[g_aff_n], sizeof g_aff[0], "%s", text);
    g_aff_kind[g_aff_n] = kind;
    g_aff_n++;
    return 1;
}

static inline size_t adapter_u8len(const char *s) {
    unsigned char c = (unsigned char)s[0];
    if (c < 0x80) return 1;
    if ((c & 0xE0) == 0xC0) return 2;
    if ((c & 0xF0) == 0xE0) return 3;
    if ((c & 0xF8) == 0xF0) return 4;
    return 1;
}

/* 同义词/词缀替换（逐位置最长匹配）：返回 1=改过，0=没改。 */
static inline int aip_apply_syn(AI *ai, const char *in, char *out, size_t cap) {
    if (!in || !out || !cap || (!g_syn_n && !g_aff_n)) return 0;
    size_t o = 0;
    int changed = 0;
    const char *p = in;
    while (*p) {
        /* §6.307 词缀：先试前缀（剥掉后基词要在池里），再试后缀 */
        if (ai) {
            int hit_affix = 0;
            for (size_t i = 0; i < g_aff_n && !hit_affix; ++i) {
                size_t al = strlen(g_aff[i]);
                if (g_aff_kind[i] == 'p') {
                    if (strncmp(p, g_aff[i], al) != 0) continue;
                    const char *base = p + al;
                    size_t bl = 0;
                    for (int k = 0; k < 3 && base[bl]; ++k) {   /* 基词 1~4 个汉字 */
                        bl += adapter_u8len(base + bl);
                        /* §6.307 **前缀不给单字基词**：否则 `小明`/`小红`/`小刚`
                         * 会被剥成 明/红/刚（interact/belief 当场红）。
                         * §6.310 **后缀可以**：`猫们` ⇒ `猫`，而 `我们/他们` 是词池里的词、
                         * 会被下面的"整词在池就不动"挡住。 */
                        if (g_aff_kind[i] == 'p' && bl < 6) continue;
                        char tmp[32], whole[40];
                        if (bl >= sizeof tmp) break;
                        memcpy(tmp, base, bl); tmp[bl] = 0;
                        if (al + bl < sizeof whole) {          /* 整个变体本身就是词 ⇒ 不动 */
                            memcpy(whole, p, al); memcpy(whole + al, base, bl);
                            whole[al + bl] = 0;
                            if (pool_find(ai->pool, whole)) continue;
                        }
                        if (pool_find(ai->pool, tmp)) {
                            size_t tl = bl;
                            if (o + tl + 1 >= cap) return changed;
                            memcpy(out + o, base, tl); o += tl; p = base + tl;
                            changed = 1; hit_affix = 1; break;
                        }
                    }
                } else if (g_aff_kind[i] == 's') {
                    size_t bl = 0;
                    for (int k = 0; k < 3 && p[bl]; ++k) {
                        bl += adapter_u8len(p + bl);
                        char tmp[32];
                        if (bl >= sizeof tmp) break;
                        memcpy(tmp, p, bl); tmp[bl] = 0;
                        if (strncmp(p + bl, g_aff[i], al) != 0) continue;
                        if (!pool_find(ai->pool, tmp)) continue;
                        /* §6.310 **人称代词 + 们 不剥**：`他们` 剥成 `他` 会把"复数立场"
                         * 数错（interact 53/54 当场红）。`猫们` 照剥。 */
                        if (g_aff_kind[i] == 's' && !strcmp(g_aff[i], "们")) {
                            static const char *pron1[] = {"他", "她", "它", "我", "你", "咱", NULL};
                            int is_pron = 0;
                            for (size_t z = 0; pron1[z]; ++z) if (!strcmp(tmp, pron1[z])) is_pron = 1;
                            if (is_pron) continue;
                        }
                        size_t tl = bl;
                        if (o + tl + 1 >= cap) return changed;
                        memcpy(out + o, p, tl); o += tl; p += bl + al;
                        changed = 1; hit_affix = 1; break;
                    }
                }
            }
            if (hit_affix) continue;
        }
        size_t best = 0, bi = 0;
        for (size_t i = 0; i < g_syn_n; ++i) {
            size_t l = strlen(g_syn_from[i]);
            if (l > best && strncmp(p, g_syn_from[i], l) == 0) { best = l; bi = i; }
        }
        if (best) {
            size_t tl = strlen(g_syn_to[bi]);
            if (o + tl + 1 >= cap) return changed;
            memcpy(out + o, g_syn_to[bi], tl);
            o += tl;
            p += best;
            changed = 1;
        } else {
            if (o + 2 >= cap) return changed;
            out[o++] = *p++;
        }
    }
    out[o] = 0;
    return changed;
}

#endif /* ADAPTER_H */
