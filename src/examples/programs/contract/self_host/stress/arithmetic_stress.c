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
//   - A compact deterministic arithmetic lowering stress fixture.
// - Must-Not:
//   - Use hosted libc, heap allocation, host callbacks, or undefined behavior.
// - Allows:
//   - Inputs: none.
//   - Outputs: "OK\n" after the exact arithmetic oracle is reached.
//   - Side effects: fundamental guest byte output only.
// - Split-When:
//   - Split when an arithmetic family needs an independent oracle.
// - Merge-When:
//   - Merge when another fixture owns the same arithmetic surface.
// - Summary:
//   - Stress integer lowering with long bounded dependency chains.
// - Description:
//   - Exercises multiply, divide, modulo, shifts, masks, xor, or, and addition.
// - Usage:
//   - Compile as one freestanding guest C translation unit.
// - Defaults:
//   - Emit nothing unless the complete final state matches the oracle.
//

//! Compact deterministic arithmetic lowering stress fixture.

void __malbolge_output_byte(unsigned int value);

enum
{
    EXPECTED_A = 51336,
    EXPECTED_B = 46736,
    EXPECTED_C = 40126,
    EXPECTED_D = 46510,
    EXPECTED_E = 49125,
    EXPECTED_F = 8587,
    MODULUS = 59049,
    ROUNDS = 729
};

static void emit_success(void)
{
    __malbolge_output_byte(79U);
    __malbolge_output_byte(75U);
    __malbolge_output_byte(10U);
}

int main(void)
{
    unsigned int a = 17U;
    unsigned int b = 29U;
    unsigned int c = 43U;
    unsigned int d = 71U;
    unsigned int e = 101U;
    unsigned int f = 131U;
    unsigned int index = 0U;

    while (index < ROUNDS)
    {
        const unsigned int old_a = a;
        const unsigned int old_b = b;
        const unsigned int old_c = c;
        const unsigned int old_d = d;
        const unsigned int old_e = e;
        const unsigned int old_f = f;
        const unsigned int mix =
            (old_a * 17U + old_b * 13U + index * 7U + 19U) % MODULUS;

        a = (old_b + mix + (old_c >> 1U)) % MODULUS;
        b = ((old_c ^ mix) + (old_d << 1U)) % MODULUS;
        c = ((old_d & 32767U) + (old_e | 1U) + (mix % 257U)) %
            MODULUS;
        d = (old_e * 7U + old_f / 3U + mix % 101U) % MODULUS;
        e = (old_f * 11U + (a >> 2U) + (b & 255U)) % MODULUS;
        f = ((a ^ b ^ c ^ d ^ e) + mix / 7U) % MODULUS;
        ++index;
    }

    if (a != EXPECTED_A || b != EXPECTED_B || c != EXPECTED_C ||
        d != EXPECTED_D || e != EXPECTED_E || f != EXPECTED_F)
    {
        return 1;
    }

    emit_success();
    return 0;
}
