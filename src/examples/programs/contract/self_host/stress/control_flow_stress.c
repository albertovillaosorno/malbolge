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
//   - A compact deterministic control-flow lowering stress fixture.
// - Must-Not:
//   - Inflate source size with generated branches or use hosted facilities.
// - Allows:
//   - Inputs: none.
//   - Outputs: "OK\n" after the exact control-flow oracle is reached.
//   - Side effects: fundamental guest byte output only.
// - Split-When:
//   - Split when another control-flow family needs a separate oracle.
// - Merge-When:
//   - Merge when another fixture owns the same branch topology.
// - Summary:
//   - Execute many state-dependent branches from a small static CFG.
// - Description:
//   - Exercises backedges, branch convergence, and data-dependent paths.
// - Usage:
//   - Compile as one freestanding guest C translation unit.
// - Defaults:
//   - Emit nothing unless the complete final state matches the oracle.
//

//! Compact deterministic control-flow lowering stress fixture.

void __malbolge_output_byte(unsigned int value);

enum
{
    EXPECTED_A = 4690,
    EXPECTED_B = 28270,
    EXPECTED_C = 9300,
    EXPECTED_D = 1712,
    EXPECTED_E = 29848,
    MODULUS = 59049,
    ROUNDS = 1458
};

static void emit_success(void)
{
    __malbolge_output_byte(79U);
    __malbolge_output_byte(75U);
    __malbolge_output_byte(10U);
}

int main(void)
{
    unsigned int a = 7U;
    unsigned int b = 11U;
    unsigned int c = 19U;
    unsigned int d = 23U;
    unsigned int e = 31U;
    unsigned int index = 0U;

    while (index < ROUNDS)
    {
        const unsigned int selector = (a + 3U * b + index) % 7U;

        if (selector == 0U)
        {
            a = (a + b * 5U + index) % MODULUS;
            c = (c ^ a) % MODULUS;
        }
        else if (selector == 1U)
        {
            b = (b + c * 7U + (d >> 1U)) % MODULUS;
            e = (e + b + 17U) % MODULUS;
        }
        else if (selector == 2U)
        {
            c = (c + d * 11U + (a & 255U)) % MODULUS;
            a = (a + c / 3U + 29U) % MODULUS;
        }
        else if (selector == 3U)
        {
            d = (d + e * 13U + (b << 1U)) % MODULUS;
            b = (b ^ d) % MODULUS;
        }
        else if (selector == 4U)
        {
            e = (e + a * 17U + c % 97U) % MODULUS;
            d = (d + e / 5U + 37U) % MODULUS;
        }
        else if (selector == 5U)
        {
            a = (a + d + e + index % 257U) % MODULUS;
            b = (b + a * 3U + 41U) % MODULUS;
        }
        else
        {
            c = (c + a + b + e) % MODULUS;
            e = (e ^ (c >> 1U)) % MODULUS;
        }

        d = (d + (a ^ c) + (e & 255U)) % MODULUS;
        e = (e + (b | 1U) + (d >> 2U)) % MODULUS;
        ++index;
    }

    if (a != EXPECTED_A || b != EXPECTED_B || c != EXPECTED_C ||
        d != EXPECTED_D || e != EXPECTED_E)
    {
        return 1;
    }

    emit_success();
    return 0;
}
