#define _POSIX_C_SOURCE 200809L
/* tools/c7b_query_bench.c — §6.931 `.c7b2` 分片查询延迟压测（名字→节点→事实）
 *
 * 为什么是它：2.5B 边的方案里，最大的未知不是“写得下”，而是**查得动**。
 * 这个工具只量真路径：`c7b2_find_node`（线性扫描名字）+ `c7b2_facts`（读前 4 条）。
 * 节点名约定 `N<数字>`（和生成脚本一致），不猜、不缓存第二次。
 *
 * 用法：c7b_query_bench <分片.c7b2> [查询数=200]
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "../ai.h"
#include "../corpus7b.h"

static int cmp_double(const void *a, const void *b) {
    double x = *(const double *)a, y = *(const double *)b;
    return (x > y) - (x < y);
}

static double now_us(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec * 1e6 + (double)ts.tv_nsec / 1e3;
}

static uint64_t fnv1a64(const char *s) {
    uint64_t h = 1469598103934665603ull;
    for (const unsigned char *p = (const unsigned char *)s; p && *p; ++p) { h ^= (uint64_t)*p; h *= 1099511628211ull; }
    return h;
}

typedef struct { uint64_t hash; uint32_t shard; } IdxRec;

/* §6.932 带全局路由：--index <idx> <分片目录> <总节点数> <查询数> */
static int bench_index(const char *idx, const char *dir, int total, int nq) {
    FILE *f = fopen(idx, "rb");
    if (!f) { fprintf(stderr, "打不开索引 %s\n", idx); return 1; }
    char magic[6] = {0};
    uint32_t cnt = 0;
    if (fread(magic, 1, 5, f) != 5 || memcmp(magic, "C7BI1", 5) != 0 || fread(&cnt, 4, 1, f) != 1) {
        fprintf(stderr, "索引格式不对\n"); fclose(f); return 1;
    }
    IdxRec *rec = (IdxRec *)malloc((size_t)cnt * sizeof *rec);
    if (!rec) { fclose(f); return 1; }
    if (fread(rec, sizeof *rec, cnt, f) != cnt) { fprintf(stderr, "索引读不全\n"); free(rec); fclose(f); return 1; }
    fclose(f);
    double *lat = (double *)malloc((size_t)nq * sizeof(double));
    C7B *cache[256]; memset(cache, 0, sizeof cache);
    int opened = 0;
    unsigned seed = 987654321u;
    int hit = 0, miss = 0;
    char err[256] = {0};
    if (total <= 0) total = 100000;
    for (int i = 0; i < nq; ++i) {
        seed = seed * 1103515245u + 12345u;
        int id = (int)(seed % (unsigned)total);
        char name[32];
        snprintf(name, sizeof name, "N%d", id);
        double q0 = now_us();
        uint64_t h = fnv1a64(name);
        uint32_t lo = 0, hi = cnt;
        int shard = -1;
        while (lo < hi) {
            uint32_t mid = lo + (hi - lo) / 2;
            if (rec[mid].hash < h) lo = mid + 1; else hi = mid;
        }
        if (lo < cnt && rec[lo].hash == h) shard = (int)rec[lo].shard;
        int ok = 0;
        if (shard >= 0) {
            if (shard < 256 && !cache[shard]) {
                char path[1024];
                snprintf(path, sizeof path, "%s/s.%03d.c7b2", dir, shard);
                cache[shard] = c7b_open(path, err, sizeof err);
                if (cache[shard]) opened++;
            }
            if (shard < 256 && cache[shard]) {
                uint32_t nid = 0;
                C7B2Fact fa[4];
                if (c7b2_find_node(cache[shard], name, &nid) == 0) { (void)c7b2_facts(cache[shard], nid, fa, 4); ok = 1; }
            }
        }
        if (getenv("AIP_QDBG") && i < 3)
            printf("[dbg] name=%s hash=%llu shard=%d ok=%d opened=%d err=%s\n",
                   name, (unsigned long long)h, shard, ok, opened, err);
        if (ok) hit++; else miss++;
        lat[i] = now_us() - q0;
    }
    qsort(lat, (size_t)nq, sizeof(double), cmp_double);
    double sum = 0;
    for (int i = 0; i < nq; ++i) sum += lat[i];
    printf("索引: %u 个节点；本次打开了 %d 个分片\n", cnt, opened);
    printf("查询: %d 次（命中 %d / 未命中 %d，总节点 %d）\n", nq, hit, miss, total);
    printf("延迟: avg %.2f ms  p50 %.2f ms  p95 %.2f ms  max %.2f ms\n",
           sum / nq / 1000.0, lat[nq / 2] / 1000.0, lat[(int)((double)nq * 0.95)] / 1000.0, lat[nq - 1] / 1000.0);
    for (int i = 0; i < 256; ++i) if (cache[i]) c7b_close(cache[i]);
    free(rec); free(lat);
    return 0;
}

int main(int argc, char **argv) {
    if (argc >= 6 && !strcmp(argv[1], "--index")) {
        int total = atoi(argv[4]);
        int nq = atoi(argv[5]);
        return bench_index(argv[2], argv[3], total, nq);
    }
    if (argc < 2) { fprintf(stderr, "用法: %s <分片.c7b2> [查询数] | --index <idx> <目录> <总节点> <查询数>\n", argv[0]); return 2; }
    int nq = (argc > 2) ? atoi(argv[2]) : 200;
    if (nq < 1) nq = 200;
    char err[256] = {0};
    double t0 = now_us();
    C7B *c = c7b_open(argv[1], err, sizeof err);
    double t_open = now_us() - t0;
    if (!c) { fprintf(stderr, "打开失败: %s\n", err[0] ? err : "?"); return 1; }
    unsigned seed = 12345;
    double *lat = (double *)malloc((size_t)nq * sizeof(double));
    if (!lat) return 1;
    int hit = 0, miss = 0;
    for (int i = 0; i < nq; ++i) {
        seed = seed * 1103515245u + 12345u;
        uint32_t id = seed % (c->n_words ? c->n_words : 1);
        char name[32];
        snprintf(name, sizeof name, "N%u", id);
        double q0 = now_us();
        uint32_t nid = 0;
        int rc = c7b2_find_node(c, name, &nid);
        C7B2Fact f[4];
        if (rc == 0) { (void)c7b2_facts(c, nid, f, 4); hit++; } else miss++;
        lat[i] = now_us() - q0;
    }
    qsort(lat, (size_t)nq, sizeof(double), cmp_double);
    double sum = 0;
    for (int i = 0; i < nq; ++i) sum += lat[i];
    printf("分片: %s\n节点数: %u 边数: %llu\n打开耗时: %.1f ms\n",
           argv[1], c->n_words, (unsigned long long)c->n_edges, t_open / 1000.0);
    printf("查询: %d 次（命中 %d / 未命中 %d）\n", nq, hit, miss);
    printf("延迟: avg %.2f ms  p50 %.2f ms  p95 %.2f ms  max %.2f ms\n",
           sum / nq / 1000.0, lat[nq / 2] / 1000.0,
           lat[(int)((double)nq * 0.95)] / 1000.0, lat[nq - 1] / 1000.0);
    free(lat);
    c7b_close(c);
    return 0;
}
