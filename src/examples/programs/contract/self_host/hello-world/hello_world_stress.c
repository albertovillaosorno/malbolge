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
//   - A freestanding self-checking Hello World stress fixture.
// - Must-Not:
//   - Use hosted libc, threads, dynamic allocation, or host-side construction.
// - Allows:
//   - Inputs: no guest input.
//   - Outputs: the byte sequence "Hello, World!\n" after all checks pass.
//   - Side effects: fundamental guest byte output only.
// - Split-When:
//   - Split when a stress kernel gains independent conformance value.
// - Merge-When:
//   - Merge when another fixture owns the same deterministic validation
//     surface.
// - Summary:
//   - Exercise nontrivial guest-C lowering before emitting a fixed byte stream.
// - Description:
//   - Uses intentionally damaged redundant encodings and checked arithmetic
//     kernels so each major code path contributes to an observable pass/fail
//     decision.
// - Usage:
//   - Compile as one guest C translation unit without hosted services.
// - Defaults:
//   - Emit nothing unless every validation and stress kernel succeeds.
//

//! Self-checking Hello World stress fixture for the admitted freestanding C
//! surface. Complexity is retained only where it contributes either to data
//! integrity or to an explicitly verified compiler/runtime stress kernel.

void __malbolge_output_byte(unsigned int value);

enum
{
    BYTE_CARDINALITY = 256,
    DIGEST_MODULUS = 59049,
    MATRIX_DIMENSION = 4,
    MATRIX_MODULUS = 257,
    MESSAGE_DIGEST = 4586,
    MESSAGE_LENGTH = 14,
    QUORUM_NODE_COUNT = 5,
    QUORUM_REQUIRED = 3,
    RESIDUE_MODULUS_A = 5,
    RESIDUE_MODULUS_B = 7,
    RESIDUE_MODULUS_C = 11,
    SEAL_MODULUS = 257,
    STATUS_FAILURE = 1,
    STATUS_SUCCESS = 0,
    STRESS_ROUNDS = 729,
    WORD_STRESS_EXPECTED = 44471
};

typedef struct EncodedSymbol
{
    unsigned int low_codeword;
    unsigned int high_codeword;
    unsigned int residue_a;
    unsigned int residue_b;
    unsigned int residue_c;
    unsigned int seal;
} EncodedSymbol;

typedef struct ReplicaVote
{
    unsigned int valid;
    unsigned int value;
} ReplicaVote;

typedef struct DecodeStats
{
    unsigned int corrected_codewords;
    unsigned int dissenting_votes;
    unsigned int invalid_votes;
} DecodeStats;

/*
 * Replica layout for every byte position:
 *
 *   node 0: canonical symbol
 *   node 1: one low-nibble codeword bit flipped; SECDED must correct it
 *   node 2: one high-nibble codeword bit flipped; SECDED must correct it
 *   node 3: internally valid but intentionally wrong byte
 *   node 4: two low-nibble codeword bits flipped; SECDED must reject it
 *
 * Correct decoding therefore requires both error correction and quorum logic.
 * The fixture validates the expected correction/rejection counts on every pass.
 */
static const EncodedSymbol message_replicas[QUORUM_NODE_COUNT][MESSAGE_LENGTH] =
    {
        {
            {75U, 170U, 2U, 2U, 6U, 117U},
            {45U, 51U, 1U, 3U, 2U, 179U},
            {225U, 51U, 3U, 3U, 9U, 198U},
            {225U, 51U, 3U, 3U, 9U, 215U},
            {255U, 51U, 1U, 6U, 1U, 86U},
            {225U, 153U, 4U, 2U, 0U, 194U},
            {0U, 153U, 2U, 4U, 10U, 24U},
            {180U, 45U, 2U, 3U, 10U, 20U},
            {255U, 51U, 1U, 6U, 1U, 154U},
            {153U, 180U, 4U, 2U, 4U, 25U},
            {225U, 51U, 3U, 3U, 9U, 77U},
            {170U, 51U, 0U, 2U, 1U, 55U},
            {135U, 153U, 3U, 5U, 0U, 163U},
            {210U, 0U, 0U, 3U, 10U, 100U},
        },
        {
            {74U, 170U, 2U, 2U, 6U, 117U},
            {44U, 51U, 1U, 3U, 2U, 179U},
            {224U, 51U, 3U, 3U, 9U, 198U},
            {224U, 51U, 3U, 3U, 9U, 215U},
            {254U, 51U, 1U, 6U, 1U, 86U},
            {224U, 153U, 4U, 2U, 0U, 194U},
            {1U, 153U, 2U, 4U, 10U, 24U},
            {181U, 45U, 2U, 3U, 10U, 20U},
            {254U, 51U, 1U, 6U, 1U, 154U},
            {152U, 180U, 4U, 2U, 4U, 25U},
            {224U, 51U, 3U, 3U, 9U, 77U},
            {171U, 51U, 0U, 2U, 1U, 55U},
            {134U, 153U, 3U, 5U, 0U, 163U},
            {211U, 0U, 0U, 3U, 10U, 100U},
        },
        {
            {75U, 168U, 2U, 2U, 6U, 117U},
            {45U, 49U, 1U, 3U, 2U, 179U},
            {225U, 49U, 3U, 3U, 9U, 198U},
            {225U, 49U, 3U, 3U, 9U, 215U},
            {255U, 49U, 1U, 6U, 1U, 86U},
            {225U, 155U, 4U, 2U, 0U, 194U},
            {0U, 155U, 2U, 4U, 10U, 24U},
            {180U, 47U, 2U, 3U, 10U, 20U},
            {255U, 49U, 1U, 6U, 1U, 154U},
            {153U, 182U, 4U, 2U, 4U, 25U},
            {225U, 49U, 3U, 3U, 9U, 77U},
            {170U, 49U, 0U, 2U, 1U, 55U},
            {135U, 155U, 3U, 5U, 0U, 163U},
            {210U, 2U, 0U, 3U, 10U, 100U},
        },
        {
            {102U, 135U, 4U, 1U, 7U, 68U},
            {0U, 30U, 3U, 6U, 4U, 17U},
            {204U, 30U, 2U, 1U, 2U, 110U},
            {204U, 30U, 2U, 1U, 2U, 127U},
            {210U, 30U, 3U, 2U, 3U, 181U},
            {204U, 180U, 1U, 2U, 0U, 216U},
            {45U, 180U, 2U, 5U, 7U, 85U},
            {153U, 0U, 2U, 2U, 2U, 216U},
            {210U, 30U, 3U, 2U, 3U, 249U},
            {180U, 153U, 4U, 4U, 6U, 77U},
            {204U, 30U, 2U, 1U, 2U, 246U},
            {135U, 30U, 4U, 0U, 5U, 224U},
            {170U, 180U, 1U, 4U, 6U, 150U},
            {255U, 45U, 0U, 4U, 7U, 161U},
        },
        {
            {72U, 170U, 2U, 2U, 6U, 117U},
            {46U, 51U, 1U, 3U, 2U, 179U},
            {226U, 51U, 3U, 3U, 9U, 198U},
            {226U, 51U, 3U, 3U, 9U, 215U},
            {252U, 51U, 1U, 6U, 1U, 86U},
            {226U, 153U, 4U, 2U, 0U, 194U},
            {3U, 153U, 2U, 4U, 10U, 24U},
            {183U, 45U, 2U, 3U, 10U, 20U},
            {252U, 51U, 1U, 6U, 1U, 154U},
            {154U, 180U, 4U, 2U, 4U, 25U},
            {226U, 51U, 3U, 3U, 9U, 77U},
            {169U, 51U, 0U, 2U, 1U, 55U},
            {132U, 153U, 3U, 5U, 0U, 163U},
            {209U, 0U, 0U, 3U, 10U, 100U},
        },
};

static const unsigned int stress_matrix[MATRIX_DIMENSION][MATRIX_DIMENSION] = {
    {3U, 5U, 7U, 11U},
    {13U, 17U, 19U, 23U},
    {29U, 31U, 37U, 41U},
    {43U, 47U, 53U, 59U},
};

static const unsigned int stress_vector[MATRIX_DIMENSION] = {
    17U,
    29U,
    43U,
    71U,
};

static const unsigned int stress_matrix_expected[MATRIX_DIMENSION] = {
    250U,
    80U,
    240U,
    81U,
};

static unsigned int code_bit(unsigned int codeword, unsigned int position)
{
    return (codeword >> (position - 1U)) & 1U;
}

static int decode_secded_nibble(unsigned int codeword, unsigned int *nibble,
                                unsigned int *corrected)
{
    unsigned int overall;
    unsigned int syndrome;
    unsigned int sanitized = codeword & 255U;

    syndrome = code_bit(sanitized, 1U) ^ code_bit(sanitized, 3U) ^
               code_bit(sanitized, 5U) ^ code_bit(sanitized, 7U);
    syndrome |= (code_bit(sanitized, 2U) ^ code_bit(sanitized, 3U) ^
                 code_bit(sanitized, 6U) ^ code_bit(sanitized, 7U))
                << 1U;
    syndrome |= (code_bit(sanitized, 4U) ^ code_bit(sanitized, 5U) ^
                 code_bit(sanitized, 6U) ^ code_bit(sanitized, 7U))
                << 2U;

    overall = code_bit(sanitized, 1U) ^ code_bit(sanitized, 2U) ^
              code_bit(sanitized, 3U) ^ code_bit(sanitized, 4U) ^
              code_bit(sanitized, 5U) ^ code_bit(sanitized, 6U) ^
              code_bit(sanitized, 7U) ^ code_bit(sanitized, 8U);
    *corrected = 0U;

    if (syndrome != 0U && overall == 0U)
    {
        return 0;
    }
    if (syndrome != 0U)
    {
        sanitized ^= 1U << (syndrome - 1U);
        *corrected = 1U;
    }
    else if (overall != 0U)
    {
        sanitized ^= 1U << 7U;
        *corrected = 1U;
    }

    *nibble = code_bit(sanitized, 3U) | (code_bit(sanitized, 5U) << 1U) |
              (code_bit(sanitized, 6U) << 2U) | (code_bit(sanitized, 7U) << 3U);
    return 1;
}

static unsigned int expected_seal(unsigned int position, unsigned int value)
{
    return (value * 37U + position * 17U + 23U) % SEAL_MODULUS;
}

static int residues_match(const EncodedSymbol *symbol, unsigned int value)
{
    return value % RESIDUE_MODULUS_A == symbol->residue_a &&
           value % RESIDUE_MODULUS_B == symbol->residue_b &&
           value % RESIDUE_MODULUS_C == symbol->residue_c;
}

static ReplicaVote decode_replica(unsigned int node, unsigned int position,
                                  DecodeStats *stats)
{
    const EncodedSymbol *const symbol = &message_replicas[node][position];
    ReplicaVote vote;
    unsigned int corrected_high = 0U;
    unsigned int corrected_low = 0U;
    unsigned int high = 0U;
    unsigned int low = 0U;
    unsigned int value;

    vote.valid = 0U;
    vote.value = 0U;

    if (!decode_secded_nibble(symbol->low_codeword, &low, &corrected_low) ||
        !decode_secded_nibble(symbol->high_codeword, &high, &corrected_high))
    {
        stats->invalid_votes += 1U;
        return vote;
    }

    stats->corrected_codewords += corrected_low + corrected_high;
    value = low | (high << 4U);
    if (!residues_match(symbol, value) ||
        expected_seal(position, value) != symbol->seal)
    {
        stats->invalid_votes += 1U;
        return vote;
    }

    vote.valid = 1U;
    vote.value = value;
    return vote;
}

static int consensus_decode(unsigned int position, unsigned int *value,
                            DecodeStats *stats)
{
    ReplicaVote votes[QUORUM_NODE_COUNT];
    unsigned int candidate = 0U;
    unsigned int node = 0U;
    unsigned int quorum_matches = 0U;
    unsigned int selected = 0U;

    while (node < QUORUM_NODE_COUNT)
    {
        votes[node] = decode_replica(node, position, stats);
        ++node;
    }

    while (candidate < BYTE_CARDINALITY)
    {
        unsigned int votes_for_candidate = 0U;

        node = 0U;
        while (node < QUORUM_NODE_COUNT)
        {
            votes_for_candidate +=
                (unsigned int)(votes[node].valid != 0U &&
                               votes[node].value == candidate);
            ++node;
        }
        if (votes_for_candidate >= QUORUM_REQUIRED)
        {
            selected = candidate;
            ++quorum_matches;
        }
        ++candidate;
    }

    if (quorum_matches != 1U)
    {
        return 0;
    }

    node = 0U;
    while (node < QUORUM_NODE_COUNT)
    {
        stats->dissenting_votes +=
            (unsigned int)(votes[node].valid != 0U &&
                           votes[node].value != selected);
        ++node;
    }

    *value = selected;
    return 1;
}

static unsigned int extend_digest(unsigned int digest, unsigned int position,
                                  unsigned int value)
{
    return (digest * 3U + value + position) % DIGEST_MODULUS;
}

static int decode_pass(unsigned int output[MESSAGE_LENGTH], DecodeStats *stats)
{
    unsigned int digest = 0U;
    unsigned int position = 0U;

    while (position < MESSAGE_LENGTH)
    {
        unsigned int value = 0U;

        if (!consensus_decode(position, &value, stats))
        {
            return 0;
        }
        output[position] = value;
        digest = extend_digest(digest, position, value);
        ++position;
    }

    return digest == MESSAGE_DIGEST &&
           stats->corrected_codewords == MESSAGE_LENGTH * 2U &&
           stats->dissenting_votes == MESSAGE_LENGTH &&
           stats->invalid_votes == MESSAGE_LENGTH;
}

static int buffers_equal(const unsigned int left[MESSAGE_LENGTH],
                         const unsigned int right[MESSAGE_LENGTH])
{
    unsigned int index = 0U;

    while (index < MESSAGE_LENGTH)
    {
        if (left[index] != right[index])
        {
            return 0;
        }
        ++index;
    }
    return 1;
}

/*
 * This kernel deliberately exercises multiplication, modulo, shifts, xor,
 * division, and a long dependency chain. The final constant makes the work a
 * checked execution test rather than unobserved busywork.
 */
static int run_word_stress(void)
{
    unsigned int index = 0U;
    unsigned int state = 1U;

    while (index < STRESS_ROUNDS)
    {
        unsigned int divisor;
        unsigned int quotient;

        state = (state * 73U + index * 19U + 7U) % DIGEST_MODULUS;
        state ^= state >> 3U;
        state %= DIGEST_MODULUS;
        state = (state + (index * index + 11U) % MATRIX_MODULUS) %
                DIGEST_MODULUS;
        divisor = index % 17U + 1U;
        quotient = (state + index + 1U) / divisor;
        state = (state + quotient) % DIGEST_MODULUS;
        ++index;
    }

    return state == WORD_STRESS_EXPECTED;
}

/* Nested array indexing and modular matrix multiplication are verified against
 * an independently precomputed result. */
static int run_matrix_stress(void)
{
    unsigned int row = 0U;

    while (row < MATRIX_DIMENSION)
    {
        unsigned int column = 0U;
        unsigned int result = 0U;

        while (column < MATRIX_DIMENSION)
        {
            result =
                (result + stress_matrix[row][column] * stress_vector[column]) %
                MATRIX_MODULUS;
            ++column;
        }
        if (result != stress_matrix_expected[row])
        {
            return 0;
        }
        ++row;
    }
    return 1;
}

static void emit_message(const unsigned int message[MESSAGE_LENGTH])
{
    unsigned int index = 0U;

    while (index < MESSAGE_LENGTH)
    {
        __malbolge_output_byte(message[index]);
        ++index;
    }
}

int main(void)
{
    DecodeStats first_stats;
    DecodeStats second_stats;
    unsigned int first_pass[MESSAGE_LENGTH];
    unsigned int second_pass[MESSAGE_LENGTH];

    first_stats.corrected_codewords = 0U;
    first_stats.dissenting_votes = 0U;
    first_stats.invalid_votes = 0U;
    second_stats.corrected_codewords = 0U;
    second_stats.dissenting_votes = 0U;
    second_stats.invalid_votes = 0U;

    if (!run_word_stress() || !run_matrix_stress() ||
        !decode_pass(first_pass, &first_stats) ||
        !decode_pass(second_pass, &second_stats) ||
        !buffers_equal(first_pass, second_pass))
    {
        return STATUS_FAILURE;
    }

    emit_message(first_pass);
    return STATUS_SUCCESS;
}
