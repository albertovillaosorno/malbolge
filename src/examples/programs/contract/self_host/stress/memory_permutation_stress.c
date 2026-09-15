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
//   - A bounded array addressing and permutation stress fixture.
// - Must-Not:
//   - Use dynamic allocation, pointer forgery, out-of-bounds access, or libc.
// - Allows:
//   - Inputs: none.
//   - Outputs: "OK\n" after permutation and restoration oracles pass.
//   - Side effects: fundamental guest byte output only.
// - Split-When:
//   - Split when another memory-access geometry needs a separate oracle.
// - Merge-When:
//   - Merge when another fixture owns the same bounded permutation workload.
// - Summary:
//   - Stress computed array indices while retaining a small memory footprint.
// - Description:
//   - Permutes 81 words, checks a digest, reverses every swap, and verifies all
//     original cells exactly.
// - Usage:
//   - Compile as one freestanding guest C translation unit.
// - Defaults:
//   - Emit nothing unless both the forward and reverse checks succeed.
//

//! Bounded array addressing and permutation stress fixture.

void __malbolge_output_byte(unsigned int value);

enum
{
    ELEMENT_COUNT = 81,
    EXPECTED_DIGEST = 10809,
    MODULUS = 59049,
    PASSES = 9
};

static void emit_success(void)
{
    __malbolge_output_byte(79U);
    __malbolge_output_byte(75U);
    __malbolge_output_byte(10U);
}

static unsigned int right_index(unsigned int index, unsigned int pass,
                                unsigned int left)
{
    return (left + 1U + ((index + pass) % 17U)) % ELEMENT_COUNT;
}

int main(void)
{
    unsigned int data[ELEMENT_COUNT];
    unsigned int digest = 0U;
    unsigned int index = 0U;
    unsigned int pass = 0U;

    while (index < ELEMENT_COUNT)
    {
        data[index] = (index * 17U + 23U) % 257U;
        ++index;
    }

    while (pass < PASSES)
    {
        index = 0U;
        while (index < ELEMENT_COUNT)
        {
            const unsigned int left =
                (index * 10U + pass * 7U) % ELEMENT_COUNT;
            const unsigned int right = right_index(index, pass, left);
            const unsigned int temporary = data[left];

            data[left] = data[right];
            data[right] = temporary;
            ++index;
        }
        ++pass;
    }

    index = 0U;
    while (index < ELEMENT_COUNT)
    {
        digest =
            (digest * 131U + data[index] * 17U + index) % MODULUS;
        ++index;
    }
    if (digest != EXPECTED_DIGEST)
    {
        return 1;
    }

    pass = PASSES;
    while (pass != 0U)
    {
        --pass;
        index = ELEMENT_COUNT;
        while (index != 0U)
        {
            unsigned int left;
            unsigned int right;
            unsigned int temporary;

            --index;
            left = (index * 10U + pass * 7U) % ELEMENT_COUNT;
            right = right_index(index, pass, left);
            temporary = data[left];
            data[left] = data[right];
            data[right] = temporary;
        }
    }

    index = 0U;
    while (index < ELEMENT_COUNT)
    {
        if (data[index] != (index * 17U + 23U) % 257U)
        {
            return 1;
        }
        ++index;
    }

    emit_success();
    return 0;
}
