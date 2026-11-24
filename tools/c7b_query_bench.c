#define _GNU_SOURCE
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
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <dirent.h>
#ifndef POSIX_FADV_DONTNEED
#define POSIX_FADV_DONTNEED 4   /* Linux 常量；glibc 在 -std=c11 下可能不暴露 */
#endif
#include <time.h>
#include "../ai.h"
#include "../corpus7b.h"

/* §6.949 当前进程常驻内存（MB）：看“开一个分片 + 查 200 次”到底占多少 */
static double rss_mb(void) {
    FILE *f = fopen("/proc/self/statm", "rb");
    if (!f) return -1;
    long pages = 0, res = 0;
    if (fscanf(f, "%ld %ld", &pages, &res) != 2) res = 0;
    fclose(f);
    long pg = sysconf(_SC_PAGESIZE);
    return (double)res * (double)pg / (1024.0 * 1024.0);
}

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

typedef struct { uint64_t hash; uint32_t shard; uint32_t node; } IdxRec;

/* §6.932 带全局路由：--index <idx> <分片目录> <总节点数> <查询数> */
static int bench_index_dir(const char *idxdir, const char *dir, int total, int nq);

static int bench_index(const char *idx, const char *dir, int total, int nq) {
    /* §6.933 桶索引：目录形态 ⇒ 每次只读一个桶（2.5B 的索引不必整份进内存） */
    struct stat stt;
    if (stat(idx, &stt) == 0 && S_ISDIR(stt.st_mode)) return bench_index_dir(idx, dir, total, nq);
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
        /* §6.944 冷读：把该分片的页缓存丢掉，下一轮事实读取就真从介质来 */
        if (getenv("AIP_COLD") && shard >= 0 && shard < 256 && cache[shard])
            { int fr = posix_fadvise(fileno(cache[shard]->f), 0, 0, POSIX_FADV_DONTNEED);
              if (fr && getenv("AIP_COLDDBG")) fprintf(stderr, "[cold] fadvise rc=%d\n", fr); }
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

/* 桶索引查询：hash 高 8 位选桶 → 读该桶 → 二分 */
static int bench_index_dir(const char *idxdir, const char *dir, int total, int nq) {
    int nbuckets = 256, bits = 8;
    {
        char mp[1024];
        snprintf(mp, sizeof mp, "%s/meta.txt", idxdir);
        FILE *mf = fopen(mp, "rb");
        if (mf) {
            char ln[128];
            while (fgets(ln, sizeof ln, mf)) {
                if (sscanf(ln, "buckets %d", &nbuckets) == 1) { }
                else if (sscanf(ln, "bits %d", &bits) == 1) { }
            }
            fclose(mf);
        }
    }
    if (nbuckets < 16) nbuckets = 16;
    if (nbuckets > 65536) nbuckets = 65536;
    IdxRec **bucket = (IdxRec **)calloc((size_t)nbuckets, sizeof *bucket);
    uint32_t *bcount = (uint32_t *)calloc((size_t)nbuckets, sizeof *bcount);
    if (!bucket || !bcount) return 1;
    double *lat = (double *)malloc((size_t)nq * sizeof(double));
    if (!lat) return 1;
    C7B *cache[256]; memset(cache, 0, sizeof cache);
    int opened = 0, hit = 0, miss = 0, nb = 0;
    unsigned seed = 987654321u;
    char err[256] = {0};
    if (total <= 0) total = 100000;
    for (int i = 0; i < nq; ++i) {
        seed = seed * 1103515245u + 12345u;
        int id = (int)(seed % (unsigned)total);
        char name[32];
        snprintf(name, sizeof name, "N%d", id);
        double q0 = now_us();
        uint64_t h = fnv1a64(name);
        uint32_t b = (uint32_t)(h >> (64 - bits));
        if (!bucket[b]) {
            char path[1024];
            snprintf(path, sizeof path, "%s/%05u.idx", idxdir, b);
            FILE *bf = fopen(path, "rb");
            if (bf) {
                char mg[6] = {0};
                uint32_t c2 = 0;
                if (fread(mg, 1, 5, bf) == 5 && !memcmp(mg, "C7BK1", 5) && fread(&c2, 4, 1, bf) == 1) {
                    IdxRec *r = (IdxRec *)malloc((size_t)c2 * sizeof *r);
                    if (r && fread(r, sizeof *r, c2, bf) == c2) { bucket[b] = r; bcount[b] = c2; nb++; }
                    else free(r);
                }
                fclose(bf);
            }
            if (!bucket[b]) { bcount[b] = 0; }
        }
        int shard = -1;
        if (bucket[b]) {
            uint32_t lo = 0, hi = bcount[b];
            while (lo < hi) {
                uint32_t mid = lo + (hi - lo) / 2;
                if (bucket[b][mid].hash < h) lo = mid + 1; else hi = mid;
            }
            if (lo < bcount[b] && bucket[b][lo].hash == h) shard = (int)bucket[b][lo].shard;
        }
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
        if (ok) hit++; else miss++;
        lat[i] = now_us() - q0;
    }
    qsort(lat, (size_t)nq, sizeof(double), cmp_double);
    double sum = 0;
    for (int i = 0; i < nq; ++i) sum += lat[i];
    printf("桶索引: 读到 %d 个桶；打开了 %d 个分片\n", nb, opened);
    printf("查询: %d 次（命中 %d / 未命中 %d，总节点 %d）\n", nq, hit, miss, total);
    printf("延迟: avg %.2f ms  p50 %.2f ms  p95 %.2f ms  max %.2f ms\n",
           sum / nq / 1000.0, lat[nq / 2] / 1000.0, lat[(int)((double)nq * 0.95)] / 1000.0, lat[nq - 1] / 1000.0);
    for (int i = 0; i < 256; ++i) if (cache[i]) c7b_close(cache[i]);
    for (int i = 0; i < nbuckets; ++i) free(bucket[i]);
    free(bucket); free(bcount);
    free(lat);
    return 0;
}

/* §6.948 稳态端到端：分片 keep 住（不重开），每次只丢事实页缓存 + 冷读一个桶。
 * 这是服务跑热之后的每查询成本（热层命中场景）。 */
static int bench_e2e_hot(const char *idxdir, const char *dir, int total, int nq) {
    int nbuckets = 256, bits = 8;
    char mp[1024];
    snprintf(mp, sizeof mp, "%s/meta.txt", idxdir);
    FILE *mf = fopen(mp, "rb");
    if (mf) { char ln[128]; while (fgets(ln, sizeof ln, mf)) {
        if (sscanf(ln, "buckets %d", &nbuckets) == 1) { }
        else if (sscanf(ln, "bits %d", &bits) == 1) { } } fclose(mf); }
    if (total <= 0) total = 100000;
    C7B *cache[512];
    memset(cache, 0, sizeof cache);
    double *tot = (double *)malloc((size_t)nq * sizeof(double));
    double *bkt = (double *)malloc((size_t)nq * sizeof(double));
    if (!tot || !bkt) return 1;
    unsigned seed = 8888;
    int hit = 0, miss = 0, opened = 0;
    for (int i = 0; i < nq; ++i) {
        seed = seed * 1103515245u + 12345u;
        int id = (int)(seed % (unsigned)total);
        char name[32];
        snprintf(name, sizeof name, "N%d", id);
        uint64_t h = fnv1a64(name);
        uint32_t b = (uint32_t)(h >> (64 - bits));
        char bpath[1024];
        snprintf(bpath, sizeof bpath, "%s/%05u.idx", idxdir, b);
        double t0 = now_us();
        int shard = -1; uint32_t nodeid = 0;
        int fd = open(bpath, O_RDONLY);
        if (fd >= 0) {
            off_t sz = lseek(fd, 0, SEEK_END); lseek(fd, 0, SEEK_SET);
            size_t alen = ((size_t)(sz > 0 ? sz : 1) + 4095u) & ~(size_t)4095u;
            void *abuf = NULL;
            if (posix_memalign(&abuf, 4096, alen) == 0) {
                ssize_t r2 = pread(fd, abuf, alen, 0);
                if (r2 > 9) {
                    const char *q = (const char *)abuf + 5;
                    uint32_t cnt = 0; memcpy(&cnt, q, 4);
                    const IdxRec *rr = (const IdxRec *)(q + 4);
                    uint32_t lo = 0, hi = cnt;
                    while (lo < hi) { uint32_t mid = lo + (hi - lo) / 2;
                        if (rr[mid].hash < h) lo = mid + 1; else hi = mid; }
                    if (lo < cnt && rr[lo].hash == h) { shard = (int)rr[lo].shard; nodeid = rr[lo].node; }
                }
                free(abuf);
            }
            close(fd);
        }
        double t_bucket = now_us() - t0;
        int ok = 0;
        if (shard >= 0 && shard < 512) {
            if (!cache[shard]) {
                char sp[1024];
                snprintf(sp, sizeof sp, "%s/s.%03d.c7b2", dir, shard);
                char err[256] = {0};
                int sfd = open(sp, O_RDONLY);
                if (sfd >= 0) { (void)posix_fadvise(sfd, 0, 0, POSIX_FADV_DONTNEED); close(sfd); }
                cache[shard] = c7b_open(sp, err, sizeof err);
                if (cache[shard]) opened++;
            }
            if (cache[shard]) {
                (void)posix_fadvise(fileno(cache[shard]->f), 0, 0, POSIX_FADV_DONTNEED);
                C7B2Fact fa[4];
                if (nodeid && c7b2_facts(cache[shard], nodeid, fa, 4) >= 0) ok = 1;
            }
        }
        if (ok) hit++; else miss++;
        tot[i] = now_us() - t0;
        bkt[i] = t_bucket;
    }
    qsort(tot, (size_t)nq, sizeof(double), cmp_double);
    qsort(bkt, (size_t)nq, sizeof(double), cmp_double);
    double sum = 0, sb = 0;
    for (int i = 0; i < nq; ++i) { sum += tot[i]; sb += bkt[i]; }
    printf("稳态端到端: %s + %s（%d 桶 / 已打开 %d 片）\n", idxdir, dir, nbuckets, opened);
    printf("查询 %d 次（命中 %d / 未命中 %d）\n", nq, hit, miss);
    printf("桶读: avg %.2f ms  p95 %.2f ms\n", sb / nq / 1000.0,
           bkt[(int)((double)nq * 0.95)] / 1000.0);
    printf("总延迟: avg %.2f ms  p50 %.2f ms  p95 %.2f ms  max %.2f ms\n",
           sum / nq / 1000.0, tot[nq / 2] / 1000.0,
           tot[(int)((double)nq * 0.95)] / 1000.0, tot[nq - 1] / 1000.0);
    printf("RSS: %.1f MB（%d 个分片常驻）\n", rss_mb(), opened);
    for (int i = 0; i < 512; ++i) if (cache[i]) c7b_close(cache[i]);
    free(tot); free(bkt);
    return 0;
}

/* §6.946 端到端冷读：桶（O_DIRECT）→ 冷开分片（fadvise）→ 名字扫描 → 事实；
 * 每次查询都重新开分片，模拟“目标分片不在内存”的最坏路径。 */
static uint64_t fnv1a64b(const char *s) {
    uint64_t h = 1469598103934665603ull;
    for (const unsigned char *p = (const unsigned char *)s; p && *p; ++p) { h ^= (uint64_t)*p; h *= 1099511628211ull; }
    return h;
}

static int bench_e2e(const char *idxdir, const char *dir, int total, int nq) {
    int nbuckets = 256, bits = 8;
    char mp[1024];
    snprintf(mp, sizeof mp, "%s/meta.txt", idxdir);
    FILE *mf = fopen(mp, "rb");
    if (mf) { char ln[128]; while (fgets(ln, sizeof ln, mf)) {
        if (sscanf(ln, "buckets %d", &nbuckets) == 1) { }
        else if (sscanf(ln, "bits %d", &bits) == 1) { } } fclose(mf); }
    if (total <= 0) total = 100000;
    double *tot = (double *)malloc((size_t)nq * sizeof(double));
    double *bkt = (double *)malloc((size_t)nq * sizeof(double));
    if (!tot || !bkt) return 1;
    unsigned seed = 20251119u;
    int hit = 0, miss = 0, opened = 0;
    for (int i = 0; i < nq; ++i) {
        seed = seed * 1103515245u + 12345u;
        int id = (int)(seed % (unsigned)total);
        char name[32];
        snprintf(name, sizeof name, "N%d", id);
        uint64_t h = fnv1a64b(name);
        uint32_t b = (uint32_t)(h >> (64 - bits));
        char bpath[1024];
        snprintf(bpath, sizeof bpath, "%s/%05u.idx", idxdir, b);
        double t0 = now_us();
        int shard = -1;
        uint32_t nodeid = 0;
        int fd = open(bpath, O_RDONLY);
        if (fd >= 0) {
            off_t sz = lseek(fd, 0, SEEK_END);
            lseek(fd, 0, SEEK_SET);
            size_t alen = ((size_t)(sz > 0 ? sz : 1) + 4095u) & ~(size_t)4095u;
            void *abuf = NULL;
            if (posix_memalign(&abuf, 4096, alen) == 0) {
                ssize_t r2 = pread(fd, abuf, alen, 0);
                if (r2 > 9) {
                    const char *q = (const char *)abuf + 5;
                    uint32_t cnt = 0; memcpy(&cnt, q, 4);
                    const IdxRec *rr = (const IdxRec *)(q + 4);
                    uint32_t lo = 0, hi = cnt;
                    while (lo < hi) { uint32_t mid = lo + (hi - lo) / 2;
                        if (rr[mid].hash < h) lo = mid + 1; else hi = mid; }
                    if (lo < cnt && rr[lo].hash == h) shard = (int)rr[lo].shard;
                    if (shard >= 0) nodeid = rr[lo].node;
                }
                free(abuf);
            }
            close(fd);
        }
        double t_bucket = now_us() - t0;
        int ok = 0;
        C7B *c = NULL;
        if (shard >= 0) {
            char sp[1024];
            snprintf(sp, sizeof sp, "%s/s.%03d.c7b2", dir, shard);
            int sfd = open(sp, O_RDONLY);
            if (sfd >= 0) { (void)posix_fadvise(sfd, 0, 0, POSIX_FADV_DONTNEED); close(sfd); }
            char err[256] = {0};
            c = c7b_open(sp, err, sizeof err);
            if (c) {
                opened++;
                if (nodeid) {
                    C7B2Fact fa[4];
                    if (c7b2_facts(c, nodeid, fa, 4) >= 0) ok = 1;
                } else {
                    uint32_t nid = 0;
                    if (c7b2_find_node(c, name, &nid) == 0) {
                        C7B2Fact fa[4];
                        if (c7b2_facts(c, nid, fa, 4) >= 0) ok = 1;
                    }
                }
                c7b_close(c);
            }
        }
        if (ok) hit++; else miss++;
        tot[i] = now_us() - t0;
        bkt[i] = t_bucket;
    }
    qsort(tot, (size_t)nq, sizeof(double), cmp_double);
    qsort(bkt, (size_t)nq, sizeof(double), cmp_double);
    double sum = 0, sb = 0;
    for (int i = 0; i < nq; ++i) { sum += tot[i]; sb += bkt[i]; }
    printf("端到端: %s + %s（%d 桶 / bits=%d）\n", idxdir, dir, nbuckets, bits);
    printf("查询 %d 次（命中 %d / 未命中 %d；打开了 %d 次分片）\n", nq, hit, miss, opened);
    printf("桶读: avg %.2f ms  p95 %.2f ms\n", sb / nq / 1000.0,
           bkt[(int)((double)nq * 0.95)] / 1000.0);
    printf("总延迟: avg %.2f ms  p50 %.2f ms  p95 %.2f ms  max %.2f ms\n",
           sum / nq / 1000.0, tot[nq / 2] / 1000.0,
           tot[(int)((double)nq * 0.95)] / 1000.0, tot[nq - 1] / 1000.0);
    printf("RSS: %.1f MB（%d 次冷开）\n", rss_mb(), opened);
    free(tot); free(bkt);
    return 0;
}

/* §6.945 只量“桶索引读取”：AIP_COLD=1 时每次读前丢页缓存，测冷读一个桶要多久 */
static int bench_buckets(const char *idxdir, int nq) {
    int nbuckets = 256, bits = 8;
    char mp[1024];
    snprintf(mp, sizeof mp, "%s/meta.txt", idxdir);
    FILE *mf = fopen(mp, "rb");
    if (mf) {
        char ln[128];
        while (fgets(ln, sizeof ln, mf)) {
            if (sscanf(ln, "buckets %d", &nbuckets) == 1) { }
            else if (sscanf(ln, "bits %d", &bits) == 1) { }
        }
        fclose(mf);
    }
    (void)bits;
    if (nbuckets < 16) nbuckets = 256;
    double *lat = (double *)malloc((size_t)nq * sizeof(double));
    if (!lat) return 1;
    unsigned seed = 777;
    int found = 0;
    for (int i = 0; i < nq; ++i) {
        uint32_t b = 0;
        char path[1024];
        for (int tries = 0; tries < 64; ++tries) {
            seed = seed * 1103515245u + 12345u;
            b = seed % (unsigned)nbuckets;
            snprintf(path, sizeof path, "%s/%05u.idx", idxdir, b);
            FILE *t = fopen(path, "rb");
            if (t) { fclose(t); break; }
        }
        FILE *bf = fopen(path, "rb");
        if (!bf) { lat[i] = 0; continue; }
        if (getenv("AIP_COLD")) (void)posix_fadvise(fileno(bf), 0, 0, POSIX_FADV_DONTNEED);
        fseek(bf, 0, SEEK_END);
        long sz = ftell(bf);
        fseek(bf, 0, SEEK_SET);
        double t0 = now_us();
        size_t rd = 0;
        if (getenv("AIP_O_DIRECT")) {
            /* §6.945b O_DIRECT：真正绕开页缓存（fadvise 对小文件无效） */
            int fd = open(path, O_RDONLY | O_DIRECT);
            if (fd >= 0) {
                size_t alen = ((size_t)(sz > 0 ? sz : 1) + 4095u) & ~(size_t)4095u;
                void *abuf = NULL;
                if (posix_memalign(&abuf, 4096, alen) == 0) {
                    ssize_t r2 = pread(fd, abuf, alen, 0);
                    rd = r2 > 0 ? (size_t)r2 : 0;
                    free(abuf);
                }
                close(fd);
            }
        } else {
            char *buf = (char *)malloc(sz > 0 ? (size_t)sz : 1);
            if (buf) rd = fread(buf, 1, (size_t)sz, bf);
            free(buf);
        }
        lat[i] = now_us() - t0;
        if (rd > 0) found++;
        fclose(bf);
    }
    qsort(lat, (size_t)nq, sizeof(double), cmp_double);
    double sum = 0;
    for (int i = 0; i < nq; ++i) sum += lat[i];
    printf("桶索引: %s（%d 桶）%s\n", idxdir, nbuckets,
           getenv("AIP_COLD") ? " · 每次丢页缓存" : " · 热缓存");
    printf("读取 %d 次（读到 %d 个桶）\n", nq, found);
    printf("延迟: avg %.2f ms  p50 %.2f ms  p95 %.2f ms  max %.2f ms\n",
           sum / nq / 1000.0, lat[nq / 2] / 1000.0,
           lat[(int)((double)nq * 0.95)] / 1000.0, lat[nq - 1] / 1000.0);
    free(lat);
    return 0;
}

/* §6.944b 只量“事实读取”：跳过名字线性扫描，直接按节点 id 读 facts；
 * AIP_COLD=1 时每次读前丢掉页缓存 ⇒ 冷读延迟（HDD 上应到毫秒级）。 */
static int bench_facts(const char *path, int nq) {
    char err[256] = {0};
    C7B *c = c7b_open(path, err, sizeof err);
    if (!c) { fprintf(stderr, "打开失败: %s\n", err); return 1; }
    double *lat = (double *)malloc((size_t)nq * sizeof(double));
    if (!lat) { c7b_close(c); return 1; }
    unsigned seed = 424242;
    int hit = 0;
    for (int i = 0; i < nq; ++i) {
        seed = seed * 1103515245u + 12345u;
        uint32_t id = seed % (c->n_words ? c->n_words : 1);
        if (getenv("AIP_COLD")) (void)posix_fadvise(fileno(c->f), 0, 0, POSIX_FADV_DONTNEED);
        C7B2Fact f[4];
        double t0 = now_us();
        int k = c7b2_facts(c, id, f, 4);
        lat[i] = now_us() - t0;
        if (k > 0) hit++;
    }
    qsort(lat, (size_t)nq, sizeof(double), cmp_double);
    double sum = 0;
    for (int i = 0; i < nq; ++i) sum += lat[i];
    printf("事实读取: %s\n", path);
    printf("节点 %u / 查询 %d（命中 %d / 空 %d）%s\n", c->n_words, nq, hit, nq - hit,
           getenv("AIP_COLD") ? " · 每次丢页缓存" : " · 热缓存");
    printf("延迟: avg %.2f ms  p50 %.2f ms  p95 %.2f ms  max %.2f ms\n",
           sum / nq / 1000.0, lat[nq / 2] / 1000.0,
           lat[(int)((double)nq * 0.95)] / 1000.0, lat[nq - 1] / 1000.0);
    free(lat); c7b_close(c);
    return 0;
}

/* §7.028 分层抽检**答案正确率**：从写入口径的三元组里按 1% 抽样，
 * 先按名字找到主语节点，再读事实，核对“宾语+关系”是否真的在。
 * 这和“命中率”不同：命中的是名字，答案对不对才是数据没丢/没串。 */
static int bench_answers(const char *shard, const char *triples, int pct) {
    /* shard 可以是单个分片，也可以是目录：目录模式按“哪个片有这个名字”路由，
     * 这样 1% 抽样的答案核对才覆盖全库（否则只查一片会大面积 not_found）。 */
    C7B *cs[32]; int nc = 0;
    DIR *dp = opendir(shard);
    if (dp) {
        struct dirent *de;
        while ((de = readdir(dp)) && nc < 32) {
            size_t l = strlen(de->d_name);
            if (l < 6 || strcmp(de->d_name + l - 5, ".c7b2") != 0) continue;
            char fp[512];
            snprintf(fp, sizeof fp, "%s/%s", shard, de->d_name);
            char e2[256];
            C7B *c2 = c7b_open(fp, e2, sizeof e2);
            if (c2) cs[nc++] = c2;
        }
        closedir(dp);
    }
    if (!nc) {
        char err[256] = {0};
        C7B *c = c7b_open(shard, err, sizeof err);
        if (!c) { fprintf(stderr, "打开失败: %s\n", err); return 1; }
        cs[nc++] = c;
    }
    FILE *tf = fopen(triples, "rb");
    if (!tf) { fprintf(stderr, "读不开三元组: %s\n", triples); return 1; }
    if (pct < 1) pct = 1;
    if (pct > 100) pct = 100;
    long step = 100 / pct;
    if (step < 1) step = 1;
    char s[64], p[64], o[64];
    long line = 0, checked = 0, right = 0;
    double lat[4096];
    int nl = 0;
    while (fscanf(tf, "%63s %63s %63s", s, p, o) == 3) {
        line++;
        if (step > 1 && (line % step) != 0) continue;
        double t0 = now_us();
        uint32_t nid = 0;
        int ok = 0;
        for (int si = 0; si < nc && !ok; ++si) {
            if (c7b2_find_node(cs[si], s, &nid) != 0) continue;
            C7B2Fact f[16];
            int k = c7b2_facts(cs[si], nid, f, 16);
            for (int i = 0; i < k; ++i)
                if (!strcmp(f[i].obj, o) && !strcmp(f[i].prop, p)) { ok = 1; break; }
        }
        double dt = now_us() - t0;
        if (nl < (int)(sizeof lat / sizeof lat[0])) lat[nl++] = dt;
        checked++;
        right += ok;
    }
    fclose(tf);
    if (nl) qsort(lat, (size_t)nl, sizeof(double), cmp_double);
    double p95 = nl ? lat[(int)((double)nl * 0.95)] / 1000.0 : 0.0;
    printf("答案抽检（%d%% 分层抽样，%s）\n", pct, shard);
    printf("检查 %ld 条 / 正确 %ld（%.2f%%） / p95 %.2f ms\n",
           checked, right, checked ? 100.0 * (double)right / (double)checked : 0.0, p95);
    for (int i = 0; i < nc; ++i) c7b_close(cs[i]);
    return 0;
}

int main(int argc, char **argv) {
    if (argc >= 5 && !strcmp(argv[1], "--answers")) return bench_answers(argv[2], argv[3], atoi(argv[4]));
    if (argc >= 4 && !strcmp(argv[1], "--facts")) return bench_facts(argv[2], atoi(argv[3]));
    if (argc >= 4 && !strcmp(argv[1], "--bucket")) return bench_buckets(argv[2], atoi(argv[3]));
    if (argc >= 6 && !strcmp(argv[1], "--e2e")) return bench_e2e(argv[2], argv[3], atoi(argv[4]), atoi(argv[5]));
    if (argc >= 6 && !strcmp(argv[1], "--e2e-hot")) return bench_e2e_hot(argv[2], argv[3], atoi(argv[4]), atoi(argv[5]));
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
