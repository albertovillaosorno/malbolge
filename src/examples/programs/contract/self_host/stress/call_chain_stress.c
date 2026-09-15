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
//   - A bounded multi-function calling-convention stress fixture.
// - Must-Not:
//   - Use recursion, function pointers, libc, heap allocation, or host
//     services.
// - Allows:
//   - Inputs: none.
//   - Outputs: "OK\n" after the exact call-chain oracle is reached.
//   - Side effects: fundamental guest byte output only.
// - Split-When:
//   - Split when recursion or indirect calls gain an independent contract.
// - Merge-When:
//   - Merge when another fixture owns the same direct-call workload.
// - Summary:
//   - Exercise repeated direct calls, arguments, returns, and temporaries.
// - Description:
//   - Eight distinct transformations form a deep repeated acyclic call chain.
// - Usage:
//   - Compile as one freestanding guest C translation unit.
// - Defaults:
//   - Emit nothing unless the complete final state matches the oracle.
//

//! Bounded direct-call and calling-convention stress fixture.

void __malbolge_output_byte(unsigned int value);

enum
{
    EXPECTED_A = 3061,
    EXPECTED_B = 402,
    EXPECTED_C = 53764,
    MODULUS = 59049,
    ROUNDS = 729
};

static unsigned int stage_one(unsigned int value, unsigned int other)
{
    return (value * 3U + other + 17U) % MODULUS;
}

static unsigned int stage_two(unsigned int value, unsigned int other)
{
    return ((value ^ (other << 1U)) + 29U) % MODULUS;
}

static unsigned int stage_three(unsigned int value, unsigned int other)
{
    return (value * 5U + (other >> 1U) + 31U) % MODULUS;
}

static unsigned int stage_four(unsigned int value, unsigned int other)
{
    return (value + other * 7U + (value & 255U) + 37U) % MODULUS;
}

static unsigned int stage_five(unsigned int value, unsigned int other)
{
    return ((value | 1U) * (1U + other % 13U) + (other >> 2U) + 41U) %
        MODULUS;
}

static unsigned int stage_six(unsigned int value, unsigned int other)
{
    return ((value ^ other) + (value % 97U) * 11U + 43U) % MODULUS;
}

static unsigned int stage_seven(unsigned int a, unsigned int b,
                                unsigned int c)
{
    return (a * 3U + b * 5U + c * 7U + 47U) % MODULUS;
}

static unsigned int stage_eight(unsigned int a, unsigned int b,
                                unsigned int c)
{
    return ((a ^ (b >> 1U) ^ (c << 1U)) + 53U) % MODULUS;
}

static void emit_success(void)
{
    __malbolge_output_byte(79U);
    __malbolge_output_byte(75U);
    __malbolge_output_byte(10U);
}

int main(void)
{
    unsigned int a = 61U;
    unsigned int b = 103U;
    unsigned int c = 157U;
    unsigned int index = 0U;

    while (index < ROUNDS)
    {
        a = stage_one(a, b);
        b = stage_two(b, c);
        c = stage_three(c, a);
        a = stage_four(a, c);
        b = stage_five(b, a);
        c = stage_six(c, b);
        a = stage_seven(a, b, c);
        b = stage_eight(b, c, a);
        c = (c + a + b + index % 257U) % MODULUS;
        ++index;
    }

    if (a != EXPECTED_A || b != EXPECTED_B || c != EXPECTED_C)
    {
        return 1;
    }

    emit_success();
    return 0;
}
