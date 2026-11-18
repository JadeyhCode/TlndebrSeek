/* tools/c7b_index.c — §6.932 全局“名字→分片”路由索引（2.5B 跨分片查询的前提）
 *
 * 为什么需要：`c7b2_find_node` 只在**单个分片内**线性扫名字；500 个分片逐个开/扫会到秒级。
 * 这里给每个分片的每个节点名算 FNV-1a 64 位哈希，写一份**按哈希排序**的索引：
 *   u64 hash + u32 shard（12 B/节点），查询时二分找到候选分片，只打开那一个。
 *
 * 用法：c7b_index <分片目录> <输出.idx>
 * 输出格式：magic "C7BI1" | u32 count | count × {u64 hash, u32 shard}
 */
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <dirent.h>
#include "../ai.h"
#include "../corpus7b.h"

static uint64_t fnv1a(const char *s) {
    uint64_t h = 1469598103934665603ull;
    for (const unsigned char *p = (const unsigned char *)s; p && *p; ++p) {
        h ^= (uint64_t)*p;
        h *= 1099511628211ull;
    }
    return h;
}

typedef struct { uint64_t hash; uint32_t shard; } C7BIRec;

static int cmp_rec(const void *a, const void *b) {
    const C7BIRec *x = (const C7BIRec *)a, *y = (const C7BIRec *)b;
    if (x->hash < y->hash) return -1;
    if (x->hash > y->hash) return 1;
    return (x->shard > y->shard) - (x->shard < y->shard);
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "用法: %s <分片目录> <输出.idx>\n", argv[0]); return 2; }
    const char *dir = argv[1], *out = argv[2];
    DIR *dp = opendir(dir);
    if (!dp) { fprintf(stderr, "打不开目录 %s\n", dir); return 1; }
    char paths[2048][1024];
    int shard_id[2048];
    int nshard = 0;
    struct dirent *de;
    while ((de = readdir(dp)) && nshard < 2048) {
        size_t l = strlen(de->d_name);
        if (l < 6 || strcmp(de->d_name + l - 5, ".c7b2")) continue;
        snprintf(paths[nshard], sizeof paths[0], "%s/%s", dir, de->d_name);
        /* §6.932 分片号取文件名后缀（s.000.c7b2 ⇒ 0），**不依赖 readdir 顺序** */
        int sid = 0;
        {
            const char *dot = strrchr(de->d_name, '.');
            if (dot) {
                const char *q = dot - 1;
                while (q > de->d_name && *q >= '0' && *q <= '9') q--;
                if (*q < '0' || *q > '9') q++;
                sid = atoi(q);
            }
        }
        shard_id[nshard] = sid;
        nshard++;
    }
    closedir(dp);
    if (nshard == 0) { fprintf(stderr, "目录里没有 .c7b2 分片\n"); return 1; }
    size_t cap = 1u << 20, n = 0;
    C7BIRec *rec = (C7BIRec *)malloc(cap * sizeof *rec);
    if (!rec) return 1;
    for (int s = 0; s < nshard; ++s) {
        char err[256] = {0};
        C7B *c = c7b_open(paths[s], err, sizeof err);
        if (!c) { fprintf(stderr, "打开 %s 失败: %s\n", paths[s], err); free(rec); return 1; }
        if (c7b2_load_names_idx(c) != 0) { fprintf(stderr, "名字表读不了: %s\n", paths[s]); c7b_close(c); free(rec); return 1; }
        for (uint32_t i = 0; i < c->n_words; ++i) {
            uint32_t o = c->iid[i]; uint16_t l = (uint16_t)c->icnt[i];
            if (!l || o + l > c->names_len) continue;
            char name[512];
            size_t take = l < sizeof name - 1 ? l : sizeof name - 1;
            memcpy(name, c->names + o, take); name[take] = 0;
            if (n == cap) { cap *= 2; C7BIRec *nr = (C7BIRec *)realloc(rec, cap * sizeof *rec); if (!nr) { free(rec); return 1; } rec = nr; }
            rec[n].hash = fnv1a(name); rec[n].shard = (uint32_t)shard_id[s]; n++;
        }
        c7b_close(c);
    }
    qsort(rec, n, sizeof *rec, cmp_rec);
    FILE *f = fopen(out, "wb");
    if (!f) { fprintf(stderr, "写不开 %s\n", out); free(rec); return 1; }
    fwrite("C7BI1", 1, 5, f);
    uint32_t cnt = (uint32_t)n;
    fwrite(&cnt, 4, 1, f);
    fwrite(rec, sizeof *rec, n, f);
    fclose(f);
    printf("分片 %d 个 / 节点 %zu 个 ⇒ %s（%zu 字节，约 %.1f B/节点）\n",
           nshard, n, out, 5u + 4u + n * sizeof *rec, n ? (double)(9u + n * sizeof *rec) / (double)n : 0.0);
    free(rec);
    return 0;
}
