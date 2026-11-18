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

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "用法: %s <分片.c7b2> [查询数]\n", argv[0]); return 2; }
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
