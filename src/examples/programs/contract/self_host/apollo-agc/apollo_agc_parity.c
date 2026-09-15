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
//   - Deterministic white-box parity vectors for the Block II AGC runner.
// - Must-Not:
//   - Claim full Block II or Luminary conformance from this bounded vector set.
// - Allows:
//   - Inputs: the checked-in AGC runner through source inclusion.
//   - Outputs: one canonical parity transcript through guest byte output.
//   - Side effects: fundamental guest byte output only.
// - Split-When:
//   - Historical Luminary differential traces need an independent fixture.
// - Merge-When:
//   - Another fixture owns these exact bounded AGC semantic vectors.
// - Summary:
//   - Make native-C and future Malbolge AGC runner results byte-comparable.
// - Description:
//   - Checks one's-complement arithmetic, banking, memory, fetch, and opcodes.
// - Usage:
//   - Run as guest C now; compile this same harness to Malbolge for parity
//     later.
// - Defaults:
//   - Fail closed on the first mismatching deterministic vector.
//

//! Deterministic AGC parity vectors reusable after C-to-Malbolge lowering.

#define main apollo_agc_guest_main
#include "apollo_agc_runner.c"
#undef main

static void parity_text(const char *text)
{
    while (*text != '\0')
    {
        __malbolge_output_byte((unsigned int)(unsigned char)*text);
        ++text;
    }
}

static void parity_unsigned(unsigned int value)
{
    unsigned int digits[10];
    unsigned int count = 0U;

    if (value == 0U)
    {
        __malbolge_output_byte(48U);
        return;
    }
    while (value != 0U)
    {
        digits[count] = value % 10U;
        value /= 10U;
        ++count;
    }
    while (count != 0U)
    {
        --count;
        __malbolge_output_byte(48U + digits[count]);
    }
}

static int parity_fail(unsigned int identifier)
{
    parity_text("AGC-PARITY-v1\nFAIL ");
    parity_unsigned(identifier);
    __malbolge_output_byte(10U);
    return 1;
}

static void reset_registers(void)
{
    machine.erasable[AGC_REG_A] = 0U;
    machine.erasable[AGC_REG_L] = 0U;
    machine.erasable[AGC_REG_Q] = 0U;
    machine.erasable[AGC_REG_EB] = 0U;
    machine.erasable[AGC_REG_FB] = 0U;
    machine.erasable[AGC_REG_Z] = 0U;
    machine.erasable[AGC_REG_BB] = 0U;
    machine.channels[07] = 0U;
    machine.indexed_instruction = 0U;
    machine.index_pending = 0U;
}

static unsigned int test_arithmetic(void)
{
    return agc_word(0123456U) == 023456U &&
        agc_ones_negate(000001U) == 077776U &&
        agc_ones_add(000001U, 000001U) == 000002U &&
        agc_ones_add(077777U, 000001U) == 000001U &&
        agc_ones_add(040000U, 040000U) == 000001U;
}

static unsigned int test_banking_and_memory(void)
{
    unsigned int valid = 0U;

    reset_registers();
    agc_write_bank_register(&machine, AGC_REG_EB, 5U << 8U);
    if (agc_selected_erasable_bank(&machine) != 5U ||
        (machine.erasable[AGC_REG_BB] & 07U) != 5U)
    {
        return 0U;
    }
    agc_write_bank_register(&machine, AGC_REG_FB, 5U << 10U);
    if (agc_selected_fixed_bank(&machine) != 5U)
    {
        return 0U;
    }
    agc_write_bank_register(&machine, AGC_REG_BB, (6U << 10U) | 3U);
    if (agc_selected_erasable_bank(&machine) != 3U ||
        agc_selected_fixed_bank(&machine) != 6U)
    {
        return 0U;
    }

    machine.erasable[3U * 0400U + 5U] = 01234U;
    if (agc_read(&machine, 01405U, &valid) != 01234U || valid == 0U)
    {
        return 0U;
    }
    machine.fixed[2U * AGC_FIXED_BANK_WORDS + 7U] = 02345U;
    if (agc_read(&machine, 04007U, &valid) != 02345U || valid == 0U)
    {
        return 0U;
    }
    agc_write_bank_register(&machine, AGC_REG_FB, 5U << 10U);
    machine.fixed[5U * AGC_FIXED_BANK_WORDS + 3U] = 03456U;
    if (agc_read(&machine, 02003U, &valid) != 03456U || valid == 0U)
    {
        return 0U;
    }
    agc_write_bank_register(&machine, AGC_REG_FB, 030U << 10U);
    machine.channels[07] = 0100U;
    if (agc_selected_fixed_bank(&machine) != 040U)
    {
        return 0U;
    }
    return agc_write(&machine, 04000U, 1U) == 0U;
}

static unsigned int test_basic_opcodes(void)
{
    reset_registers();
    machine.erasable[0100U] = 0123U;
    if (agc_step_basic(&machine, (3U << 12U) | 0100U) == 0U ||
        machine.erasable[AGC_REG_A] != 0123U)
    {
        return 0U;
    }
    if (agc_step_basic(&machine, (4U << 12U) | 0100U) == 0U ||
        machine.erasable[AGC_REG_A] != agc_ones_negate(0123U))
    {
        return 0U;
    }
    machine.erasable[AGC_REG_A] = 1U;
    machine.erasable[0100U] = 2U;
    if (agc_step_basic(&machine, (6U << 12U) | 0100U) == 0U ||
        machine.erasable[AGC_REG_A] != 3U)
    {
        return 0U;
    }
    machine.erasable[AGC_REG_A] = 0777U;
    machine.erasable[0100U] = 0070U;
    if (agc_step_basic(&machine, (7U << 12U) | 0100U) == 0U ||
        machine.erasable[AGC_REG_A] != 0070U)
    {
        return 0U;
    }

    machine.erasable[AGC_REG_Z] = 04001U;
    if (agc_step_basic(&machine, 04010U) == 0U ||
        machine.erasable[AGC_REG_Q] != 04001U ||
        machine.erasable[AGC_REG_Z] != 04010U)
    {
        return 0U;
    }
    if (agc_step_basic(&machine, (1U << 12U) | 04020U) == 0U ||
        machine.erasable[AGC_REG_Z] != 04020U)
    {
        return 0U;
    }
    return 1U;
}

static unsigned int test_quarter_codes(void)
{
    const unsigned int op2 = 2U << 12U;
    const unsigned int op5 = 5U << 12U;

    reset_registers();
    machine.erasable[0100U] = 7U;
    if (agc_step_basic(&machine, op2 | (2U << 10U) | 0100U) == 0U ||
        machine.erasable[0100U] != 8U)
    {
        return 0U;
    }

    machine.erasable[AGC_REG_A] = 3U;
    machine.erasable[0100U] = 4U;
    if (agc_step_basic(&machine, op2 | (3U << 10U) | 0100U) == 0U ||
        machine.erasable[AGC_REG_A] != 7U ||
        machine.erasable[0100U] != 7U)
    {
        return 0U;
    }

    machine.erasable[0100U] = 5U;
    if (agc_step_basic(&machine, op5 | 0100U) == 0U ||
        machine.index_pending == 0U || machine.indexed_instruction != 5U)
    {
        return 0U;
    }

    machine.erasable[AGC_REG_A] = 012U;
    if (agc_step_basic(&machine, op5 | (2U << 10U) | 0100U) == 0U ||
        machine.erasable[0100U] != 012U)
    {
        return 0U;
    }

    machine.erasable[AGC_REG_A] = 021U;
    machine.erasable[0100U] = 034U;
    if (agc_step_basic(&machine, op5 | (3U << 10U) | 0100U) == 0U ||
        machine.erasable[AGC_REG_A] != 034U ||
        machine.erasable[0100U] != 021U)
    {
        return 0U;
    }

    machine.erasable[AGC_REG_A] = 011U;
    machine.erasable[AGC_REG_L] = 022U;
    machine.erasable[0100U] = 033U;
    machine.erasable[0101U] = 044U;
    if (agc_step_basic(&machine, op5 | (1U << 10U) | 0100U) == 0U ||
        machine.erasable[AGC_REG_A] != 033U ||
        machine.erasable[AGC_REG_L] != 044U ||
        machine.erasable[0100U] != 011U ||
        machine.erasable[0101U] != 022U)
    {
        return 0U;
    }
    return 1U;
}

static unsigned int test_indexed_fetch(void)
{
    unsigned int valid = 0U;
    const unsigned int index = 2U * AGC_FIXED_BANK_WORDS;
    const unsigned int base = (3U << 12U) | 0100U;

    reset_registers();
    machine.erasable[AGC_REG_Z] = 04000U;
    machine.fixed[index] = base;
    machine.indexed_instruction = 1U;
    machine.index_pending = 1U;
    if (agc_fetch(&machine, &valid) != base + 1U || valid == 0U)
    {
        return 0U;
    }
    return machine.erasable[AGC_REG_Z] == 04001U &&
        machine.index_pending == 0U;
}

int main(void)
{
    if (test_arithmetic() == 0U)
    {
        return parity_fail(1U);
    }
    if (test_banking_and_memory() == 0U)
    {
        return parity_fail(2U);
    }
    if (test_basic_opcodes() == 0U)
    {
        return parity_fail(3U);
    }
    if (test_quarter_codes() == 0U)
    {
        return parity_fail(4U);
    }
    if (test_indexed_fetch() == 0U)
    {
        return parity_fail(5U);
    }
    if (run_smoke() == 0U)
    {
        return parity_fail(6U);
    }

    parity_text("AGC-PARITY-v1\nOK\n");
    return 0;
}
