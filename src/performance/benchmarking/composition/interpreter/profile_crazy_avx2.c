// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Benchmark-only AVX2 evidence for N10-N14 padded CRAZY chunk evaluation.
// - Must-Not:
//   - Define VM semantics, change product selection, or require AVX2 at
//     runtime.
// - Allows:
//   - Inputs: the frozen 59,049-pair profile CRAZY corpus and five widths.
//   - Outputs: exact validation plus raw scalar/SIMD timing samples on stdout.
//   - Side effects: benchmark-process CPU time and stdout/stderr only.
// - Split-When:
//   - Split when another SIMD ISA or workload needs independent measurement.
// - Merge-When:
//   - Merge when one portable benchmark owns equivalent SIMD implementations.
// - Summary:
//   - Compares scalar tritwise, scalar padded lookup, and AVX2 padded lookup.
// - Description:
//   - Uses AVX2 gathers for eight independent five-trit lookup lanes at once.
// - Usage:
//   - Compile with repository-pinned Clang and run on an AVX2-capable x86 host.
// - Defaults:
//   - Validates every output before timing and returns 77 when AVX2 is absent.
//

//! Benchmark-only AVX2 CRAZY geometry measurement.

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#if defined(__i386__) || defined(__x86_64__) || defined(_M_IX86) \
    || defined(_M_X64)
#define MALBOLGE_X86 1
#include <immintrin.h>
#else
#define MALBOLGE_X86 0
#endif

#if MALBOLGE_X86 && (defined(__clang__) || defined(__GNUC__))
#define MALBOLGE_AVX2_TARGET __attribute__((target("avx2")))
#else
#define MALBOLGE_AVX2_TARGET
#endif

#define BENCHMARK_ID "cpu-profile-crazy-avx2-v1"
#define CHUNK_VALUES UINT32_C(243)
#define CHUNK_TABLE_ENTRIES UINT32_C(59049)
#define CORPUS_SIZE UINT32_C(59049)
#define CORPUS_STRIDE UINT32_C(104729)
#define REPETITIONS UINT32_C(16)
#define SAMPLE_COUNT UINT32_C(15)
#define SIMD_LANES UINT32_C(8)
#define WIDTH_COUNT 5U

static const uint8_t WIDTHS[WIDTH_COUNT] = {10U, 11U, 12U, 13U, 14U};
static const uint32_t MODULI[WIDTH_COUNT] = {
    UINT32_C(59049), UINT32_C(177147), UINT32_C(531441),
    UINT32_C(1594323), UINT32_C(4782969),
};
static const uint64_t EXPECTED_CHECKSUMS[WIDTH_COUNT] = {
    UINT64_C(27683170464), UINT64_C(69793138128), UINT64_C(255944874432),
    UINT64_C(590667673872), UINT64_C(1594938108864),
};

static uint32_t chunk_table[CHUNK_TABLE_ENTRIES];
static uint32_t words[CORPUS_SIZE];
static uint32_t accumulators[CORPUS_SIZE];
static uint32_t scalar_output[CORPUS_SIZE];
static uint32_t padded_output[CORPUS_SIZE];
static uint32_t avx2_output[CORPUS_SIZE];

static uint32_t crazy_trit(uint32_t data, uint32_t accumulator)
{
    if (((data == 0U || data == 1U) && accumulator == 0U)
        || (data == 2U && accumulator == 2U)) {
        return 1U;
    }
    if ((data == 1U && accumulator == 2U)
        || (data == 2U && (accumulator == 0U || accumulator == 1U))) {
        return 2U;
    }
    return 0U;
}

static uint32_t crazy_scalar(uint32_t data, uint32_t accumulator, uint8_t trits)
{
    uint32_t place = 1U;
    uint32_t result = 0U;
    uint8_t trit = 0U;
    while (trit < trits) {
        result += crazy_trit(data % 3U, accumulator % 3U) * place;
        data /= 3U;
        accumulator /= 3U;
        place *= 3U;
        trit++;
    }
    return result;
}

static void build_chunk_table(void)
{
    uint32_t data = 0U;
    while (data < CHUNK_VALUES) {
        uint32_t accumulator = 0U;
        while (accumulator < CHUNK_VALUES) {
            const uint32_t index = (data * CHUNK_VALUES) + accumulator;
            chunk_table[index] = crazy_scalar(data, accumulator, 5U);
            accumulator++;
        }
        data++;
    }
}

static uint32_t padded_lookup(
    uint32_t data,
    uint32_t accumulator,
    uint32_t semantic_modulus)
{
    const uint32_t low_index =
        ((data % CHUNK_VALUES) * CHUNK_VALUES) + (accumulator % CHUNK_VALUES);
    const uint32_t middle_index =
        (((data / CHUNK_VALUES) % CHUNK_VALUES) * CHUNK_VALUES)
        + ((accumulator / CHUNK_VALUES) % CHUNK_VALUES);
    uint32_t result = chunk_table[low_index]
        + (chunk_table[middle_index] * CHUNK_VALUES);
    if (semantic_modulus == CHUNK_TABLE_ENTRIES) {
        return result;
    }
    const uint32_t high_index =
        (((data / CHUNK_TABLE_ENTRIES) % CHUNK_VALUES) * CHUNK_VALUES)
        + ((accumulator / CHUNK_TABLE_ENTRIES) % CHUNK_VALUES);
    result += chunk_table[high_index] * CHUNK_TABLE_ENTRIES;
    return result % semantic_modulus;
}

static void fill_corpus(uint32_t semantic_modulus)
{
    uint32_t index = 0U;
    while (index < CORPUS_SIZE) {
        const uint32_t product = index * CORPUS_STRIDE;
        words[index] = product % semantic_modulus;
        index++;
    }
    index = 0U;
    while (index < CORPUS_SIZE) {
        accumulators[index] = words[(CORPUS_SIZE - 1U) - index];
        index++;
    }
}

static void scalar_tritwise_batch(uint8_t trits)
{
    uint32_t index = 0U;
    while (index < CORPUS_SIZE) {
        scalar_output[index] =
            crazy_scalar(words[index], accumulators[index], trits);
        index++;
    }
}

static void scalar_padded_batch(uint32_t semantic_modulus)
{
    uint32_t index = 0U;
    while (index < CORPUS_SIZE) {
        padded_output[index] =
            padded_lookup(words[index], accumulators[index], semantic_modulus);
        index++;
    }
}

#if MALBOLGE_X86
MALBOLGE_AVX2_TARGET
static void avx2_padded_batch(uint32_t semantic_modulus)
{
    const __m256i chunk_multiplier = _mm256_set1_epi32((int)CHUNK_VALUES);
    const __m256i high_multiplier = _mm256_set1_epi32((int)CHUNK_TABLE_ENTRIES);
    const bool two_chunks = semantic_modulus == CHUNK_TABLE_ENTRIES;
    uint32_t index = 0U;
    while ((index + SIMD_LANES) <= CORPUS_SIZE) {
        int32_t low_indices[SIMD_LANES];
        int32_t middle_indices[SIMD_LANES];
        int32_t high_indices[SIMD_LANES];
        uint32_t lane = 0U;
        while (lane < SIMD_LANES) {
            const uint32_t data = words[index + lane];
            const uint32_t accumulator = accumulators[index + lane];
            low_indices[lane] = (int32_t)(
                ((data % CHUNK_VALUES) * CHUNK_VALUES)
                + (accumulator % CHUNK_VALUES));
            middle_indices[lane] = (int32_t)(
                (((data / CHUNK_VALUES) % CHUNK_VALUES) * CHUNK_VALUES)
                + ((accumulator / CHUNK_VALUES) % CHUNK_VALUES));
            if (!two_chunks) {
                high_indices[lane] = (int32_t)(
                    (((data / CHUNK_TABLE_ENTRIES) % CHUNK_VALUES)
                        * CHUNK_VALUES)
                    + ((accumulator / CHUNK_TABLE_ENTRIES) % CHUNK_VALUES));
            }
            lane++;
        }
        const __m256i low_index =
            _mm256_loadu_si256((const __m256i *)low_indices);
        const __m256i middle_index =
            _mm256_loadu_si256((const __m256i *)middle_indices);
        const __m256i low = _mm256_i32gather_epi32(
            (const int *)chunk_table, low_index, (int)sizeof(uint32_t));
        const __m256i middle = _mm256_i32gather_epi32(
            (const int *)chunk_table, middle_index, (int)sizeof(uint32_t));
        __m256i combined = _mm256_add_epi32(
            low, _mm256_mullo_epi32(middle, chunk_multiplier));
        if (!two_chunks) {
            const __m256i high_index =
                _mm256_loadu_si256((const __m256i *)high_indices);
            const __m256i high = _mm256_i32gather_epi32(
                (const int *)chunk_table, high_index, (int)sizeof(uint32_t));
            combined = _mm256_add_epi32(
                combined, _mm256_mullo_epi32(high, high_multiplier));
        }
        _mm256_storeu_si256((__m256i *)&avx2_output[index], combined);
        if (!two_chunks) {
            lane = 0U;
            while (lane < SIMD_LANES) {
                avx2_output[index + lane] %= semantic_modulus;
                lane++;
            }
        }
        index += SIMD_LANES;
    }
    while (index < CORPUS_SIZE) {
        avx2_output[index] =
            padded_lookup(words[index], accumulators[index], semantic_modulus);
        index++;
    }
}
#endif

static bool host_has_avx2(void)
{
#if MALBOLGE_X86 && (defined(__clang__) || defined(__GNUC__))
    __builtin_cpu_init();
    return __builtin_cpu_supports("avx2") != 0;
#else
    return false;
#endif
}

static uint64_t checksum(const uint32_t *output)
{
    uint64_t total = 0U;
    uint32_t index = 0U;
    while (index < CORPUS_SIZE) {
        total += (uint64_t)output[index];
        index++;
    }
    return total;
}

static bool validate_width(size_t width_index)
{
    const uint8_t trits = WIDTHS[width_index];
    const uint32_t modulus = MODULI[width_index];
    fill_corpus(modulus);
    scalar_tritwise_batch(trits);
    scalar_padded_batch(modulus);
#if MALBOLGE_X86
    avx2_padded_batch(modulus);
#else
    return false;
#endif
    uint32_t index = 0U;
    while (index < CORPUS_SIZE) {
        if (scalar_output[index] != padded_output[index]
            || scalar_output[index] != avx2_output[index]) {
            fprintf(stderr, "N%u mismatch at %u: scalar=%u padded=%u avx2=%u\n",
                (unsigned)trits, (unsigned)index,
                (unsigned)scalar_output[index],
                (unsigned)padded_output[index], (unsigned)avx2_output[index]);
            return false;
        }
        index++;
    }
    const uint64_t repeated = checksum(scalar_output) * (uint64_t)REPETITIONS;
    if (repeated != EXPECTED_CHECKSUMS[width_index]) {
        fprintf(stderr, "N%u checksum mismatch: expected=%llu observed=%llu\n",
            (unsigned)trits,
            (unsigned long long)EXPECTED_CHECKSUMS[width_index],
            (unsigned long long)repeated);
        return false;
    }
    return true;
}

static uint64_t now_ns(void)
{
    struct timespec value;
    if (timespec_get(&value, TIME_UTC) != TIME_UTC) {
        return 0U;
    }
    return ((uint64_t)value.tv_sec * UINT64_C(1000000000))
        + (uint64_t)value.tv_nsec;
}

typedef enum Route {
    ROUTE_SCALAR_TRITWISE = 0,
    ROUTE_SCALAR_PADDED = 1,
    ROUTE_AVX2_PADDED = 2,
} Route;

static const char *route_name(Route route, uint8_t trits)
{
    switch (route) {
    case ROUTE_SCALAR_TRITWISE:
        return "scalar-tritwise";
    case ROUTE_SCALAR_PADDED:
        return trits == 10U ? "scalar-padded-5+5" : "scalar-padded-5+5+5";
    case ROUTE_AVX2_PADDED:
        return trits == 10U ? "avx2-padded-5+5" : "avx2-padded-5+5+5";
    }
    return "invalid";
}

static uint64_t run_route(Route route, uint8_t trits, uint32_t modulus)
{
    uint64_t result = 0U;
    uint32_t repetition = 0U;
    while (repetition < REPETITIONS) {
        switch (route) {
        case ROUTE_SCALAR_TRITWISE:
            scalar_tritwise_batch(trits);
            result += checksum(scalar_output);
            break;
        case ROUTE_SCALAR_PADDED:
            scalar_padded_batch(modulus);
            result += checksum(padded_output);
            break;
        case ROUTE_AVX2_PADDED:
#if MALBOLGE_X86
            avx2_padded_batch(modulus);
            result += checksum(avx2_output);
#endif
            break;
        }
        repetition++;
    }
    return result;
}

static bool emit_sample(size_t width_index, Route route, uint32_t sample)
{
    const uint8_t trits = WIDTHS[width_index];
    const uint32_t modulus = MODULI[width_index];
    const uint64_t start = now_ns();
    const uint64_t result = run_route(route, trits, modulus);
    const uint64_t finish = now_ns();
    if (start == 0U || finish < start
        || result != EXPECTED_CHECKSUMS[width_index]) {
        return false;
    }
    printf("%s,%u,%s,%u,%llu,%llu\n", BENCHMARK_ID, (unsigned)trits,
        route_name(route, trits), (unsigned)sample,
        (unsigned long long)(finish - start), (unsigned long long)result);
    return true;
}

static bool benchmark_width(size_t width_index)
{
    const uint8_t trits = WIDTHS[width_index];
    const uint32_t modulus = MODULI[width_index];
    fill_corpus(modulus);
    (void)run_route(ROUTE_SCALAR_TRITWISE, trits, modulus);
    (void)run_route(ROUTE_SCALAR_PADDED, trits, modulus);
    (void)run_route(ROUTE_AVX2_PADDED, trits, modulus);
    uint32_t sample = 0U;
    while (sample < SAMPLE_COUNT) {
        Route order[3];
        if ((sample % 3U) == 0U) {
            order[0] = ROUTE_SCALAR_TRITWISE;
            order[1] = ROUTE_SCALAR_PADDED;
            order[2] = ROUTE_AVX2_PADDED;
        } else if ((sample % 3U) == 1U) {
            order[0] = ROUTE_SCALAR_PADDED;
            order[1] = ROUTE_AVX2_PADDED;
            order[2] = ROUTE_SCALAR_TRITWISE;
        } else {
            order[0] = ROUTE_AVX2_PADDED;
            order[1] = ROUTE_SCALAR_TRITWISE;
            order[2] = ROUTE_SCALAR_PADDED;
        }
        size_t position = 0U;
        while (position < 3U) {
            if (!emit_sample(width_index, order[position], sample)) {
                return false;
            }
            position++;
        }
        sample++;
    }
    return true;
}

int main(int argc, char **argv)
{
    if (!host_has_avx2()) {
        fputs("AVX2 is unavailable on this host\n", stderr);
        return 77;
    }
    build_chunk_table();
    size_t width_index = 0U;
    while (width_index < WIDTH_COUNT) {
        if (!validate_width(width_index)) {
            return EXIT_FAILURE;
        }
        width_index++;
    }
    if (argc == 2 && strcmp(argv[1], "--validate-only") == 0) {
        puts("validation,ok");
        return EXIT_SUCCESS;
    }
    if (argc != 1) {
        fputs("usage: profile_crazy_avx2 [--validate-only]\n", stderr);
        return EXIT_FAILURE;
    }
    puts("benchmark_id,width,implementation,sample,nanoseconds,checksum");
    width_index = 0U;
    while (width_index < WIDTH_COUNT) {
        if (!benchmark_width(width_index)) {
            return EXIT_FAILURE;
        }
        width_index++;
    }
    return EXIT_SUCCESS;
}
