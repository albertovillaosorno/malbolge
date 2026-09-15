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
//   - Deterministic white-box parity vectors for the RV32I runner.
// - Must-Not:
//   - Claim full ISA conformance from this bounded vector set.
// - Allows:
//   - Inputs: the checked-in RV32I runner through source inclusion.
//   - Outputs: one canonical parity transcript through guest byte output.
//   - Side effects: fundamental guest byte output only.
// - Split-When:
//   - Compiler-produced binary differential tests need an independent fixture.
// - Merge-When:
//   - Another fixture owns these exact bounded RV32I semantic vectors.
// - Summary:
//   - Make native-C and future Malbolge RV32I results byte-comparable.
// - Description:
//   - Checks ALU, shifts, branches, jumps, loads, stores, traps, and x0.
// - Usage:
//   - Run as guest C now; compile this same harness to Malbolge for parity
//     later.
// - Defaults:
//   - Fail closed on the first mismatching deterministic vector.
//

//! Deterministic RV32I parity vectors reusable after C-to-Malbolge lowering.

#define main rv32i_guest_main
#include "rv32i_runner.c"
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
    parity_text("RV32I-PARITY-v1\nFAIL ");
    parity_unsigned(identifier);
    __malbolge_output_byte(10U);
    return 1;
}

static void reset_case(void)
{
    unsigned int index = 0U;

    while (index < RV32I_REGISTER_COUNT)
    {
        machine.registers[index] = 0U;
        ++index;
    }
    index = 0U;
    while (index < 512U)
    {
        machine.memory[index] = 0U;
        ++index;
    }
    machine.pc = 0U;
    machine.steps = 0U;
    machine.halted = 0U;
    machine.trap = 0U;
}

static unsigned int encode_i(unsigned int opcode, unsigned int rd,
                             unsigned int funct3, unsigned int rs1,
                             unsigned int immediate)
{
    return ((immediate & 0xfffU) << 20U) | (rs1 << 15U) |
        (funct3 << 12U) | (rd << 7U) | opcode;
}

static unsigned int encode_r(unsigned int rd, unsigned int funct3,
                             unsigned int rs1, unsigned int rs2,
                             unsigned int funct7)
{
    return (funct7 << 25U) | (rs2 << 20U) | (rs1 << 15U) |
        (funct3 << 12U) | (rd << 7U) | 0x33U;
}

static unsigned int encode_s(unsigned int funct3, unsigned int rs1,
                             unsigned int rs2, unsigned int immediate)
{
    const unsigned int imm = immediate & 0xfffU;

    return ((imm >> 5U) << 25U) | (rs2 << 20U) | (rs1 << 15U) |
        (funct3 << 12U) | ((imm & 31U) << 7U) | 0x23U;
}

static unsigned int encode_b(unsigned int funct3, unsigned int rs1,
                             unsigned int rs2, unsigned int immediate)
{
    const unsigned int imm = immediate & 0x1fffU;

    return (((imm >> 12U) & 1U) << 31U) |
        (((imm >> 5U) & 63U) << 25U) | (rs2 << 20U) | (rs1 << 15U) |
        (funct3 << 12U) | (((imm >> 1U) & 15U) << 8U) |
        (((imm >> 11U) & 1U) << 7U) | 0x63U;
}

static unsigned int encode_j(unsigned int rd, unsigned int immediate)
{
    const unsigned int imm = immediate & 0x1fffffU;

    return (((imm >> 20U) & 1U) << 31U) |
        (((imm >> 1U) & 0x3ffU) << 21U) |
        (((imm >> 11U) & 1U) << 20U) |
        (((imm >> 12U) & 0xffU) << 12U) | (rd << 7U) | 0x6fU;
}

static unsigned int run_one(unsigned int instruction)
{
    rv32_load_program_word(&machine, machine.pc, instruction);
    return rv32_step(&machine);
}

static unsigned int test_upper_and_immediate(void)
{
    reset_case();
    if (run_one(0x123450b7U) == 0U ||
        machine.registers[1] != 0x12345000U)
    {
        return 0U;
    }

    reset_case();
    machine.pc = 0x100U;
    if (run_one(0x00012117U) == 0U || machine.registers[2] != 0x12100U)
    {
        return 0U;
    }

    reset_case();
    machine.registers[2] = 0U;
    if (run_one(encode_i(0x13U, 1U, 0U, 2U, 0xfffU)) == 0U ||
        machine.registers[1] != 0xffffffffU)
    {
        return 0U;
    }
    machine.pc = 0U;
    machine.registers[2] = 0xffffffffU;
    if (run_one(encode_i(0x13U, 1U, 2U, 2U, 0U)) == 0U ||
        machine.registers[1] != 1U)
    {
        return 0U;
    }
    machine.pc = 0U;
    if (run_one(encode_i(0x13U, 1U, 3U, 2U, 0U)) == 0U ||
        machine.registers[1] != 0U)
    {
        return 0U;
    }

    machine.pc = 0U;
    machine.registers[2] = 0x0f0U;
    if (run_one(encode_i(0x13U, 1U, 4U, 2U, 0x0ffU)) == 0U ||
        machine.registers[1] != 0x00fU)
    {
        return 0U;
    }
    machine.pc = 0U;
    if (run_one(encode_i(0x13U, 1U, 6U, 2U, 0x00fU)) == 0U ||
        machine.registers[1] != 0x0ffU)
    {
        return 0U;
    }
    machine.pc = 0U;
    if (run_one(encode_i(0x13U, 1U, 7U, 2U, 0x055U)) == 0U ||
        machine.registers[1] != 0x050U)
    {
        return 0U;
    }
    return 1U;
}

static unsigned int test_shifts(void)
{
    reset_case();
    machine.registers[2] = 1U;
    if (run_one(encode_i(0x13U, 1U, 1U, 2U, 31U)) == 0U ||
        machine.registers[1] != 0x80000000U)
    {
        return 0U;
    }

    reset_case();
    machine.registers[2] = 0x80000000U;
    if (run_one(encode_i(0x13U, 1U, 5U, 2U, 31U)) == 0U ||
        machine.registers[1] != 1U)
    {
        return 0U;
    }

    reset_case();
    machine.registers[2] = 0x80000000U;
    if (run_one(encode_i(0x13U, 1U, 5U, 2U, 0x401U)) == 0U ||
        machine.registers[1] != 0xc0000000U)
    {
        return 0U;
    }
    return 1U;
}

static unsigned int test_register_alu(void)
{
    static const unsigned int funct3[10] =
        {0U, 0U, 1U, 2U, 3U, 4U, 5U, 5U, 6U, 7U};
    static const unsigned int funct7[10] =
        {0U, 32U, 0U, 0U, 0U, 0U, 0U, 32U, 0U, 0U};
    static const unsigned int left[10] = {
        0xffffffffU, 1U, 1U, 0xffffffffU, 0xffffffffU,
        0xaa55U, 0x80000000U, 0x80000000U, 0x0f0U, 0x0f0U,
    };
    static const unsigned int right[10] =
        {2U, 2U, 31U, 1U, 1U, 0x0ffU, 31U, 1U, 0x00fU, 0x055U};
    static const unsigned int expected[10] = {
        1U, 0xffffffffU, 0x80000000U, 1U, 0U,
        0xaaaau, 1U, 0xc0000000U, 0x0ffU, 0x050U,
    };
    unsigned int index = 0U;

    while (index < 10U)
    {
        reset_case();
        machine.registers[2] = left[index];
        machine.registers[3] = right[index];
        if (run_one(encode_r(1U, funct3[index], 2U, 3U, funct7[index])) ==
                0U ||
            machine.registers[1] != expected[index])
        {
            return 0U;
        }
        ++index;
    }
    return 1U;
}

static unsigned int branch_case(unsigned int funct3, unsigned int left,
                                unsigned int right, unsigned int taken)
{
    reset_case();
    machine.registers[1] = left;
    machine.registers[2] = right;
    if (run_one(encode_b(funct3, 1U, 2U, 8U)) == 0U)
    {
        return 0U;
    }
    return machine.pc == (taken != 0U ? 8U : 4U);
}

static unsigned int test_branches(void)
{
    return branch_case(0U, 7U, 7U, 1U) != 0U &&
        branch_case(0U, 7U, 8U, 0U) != 0U &&
        branch_case(1U, 7U, 8U, 1U) != 0U &&
        branch_case(1U, 7U, 7U, 0U) != 0U &&
        branch_case(4U, 0xffffffffU, 1U, 1U) != 0U &&
        branch_case(4U, 1U, 0xffffffffU, 0U) != 0U &&
        branch_case(5U, 1U, 0xffffffffU, 1U) != 0U &&
        branch_case(5U, 0xffffffffU, 1U, 0U) != 0U &&
        branch_case(6U, 1U, 2U, 1U) != 0U &&
        branch_case(6U, 2U, 1U, 0U) != 0U &&
        branch_case(7U, 2U, 1U, 1U) != 0U &&
        branch_case(7U, 1U, 2U, 0U) != 0U;
}

static unsigned int test_jumps(void)
{
    reset_case();
    if (run_one(encode_j(1U, 8U)) == 0U || machine.registers[1] != 4U ||
        machine.pc != 8U)
    {
        return 0U;
    }

    reset_case();
    machine.registers[2] = 13U;
    if (run_one(encode_i(0x67U, 1U, 0U, 2U, 0U)) == 0U ||
        machine.registers[1] != 4U || machine.pc != 12U)
    {
        return 0U;
    }
    return 1U;
}

static unsigned int test_loads_and_stores(void)
{
    reset_case();
    machine.registers[2] = 128U;
    machine.memory[128] = 0x80U;
    if (run_one(encode_i(0x03U, 1U, 0U, 2U, 0U)) == 0U ||
        machine.registers[1] != 0xffffff80U)
    {
        return 0U;
    }

    machine.pc = 0U;
    if (run_one(encode_i(0x03U, 1U, 4U, 2U, 0U)) == 0U ||
        machine.registers[1] != 0x80U)
    {
        return 0U;
    }

    machine.memory[128] = 0U;
    machine.memory[129] = 0x80U;
    machine.pc = 0U;
    if (run_one(encode_i(0x03U, 1U, 1U, 2U, 0U)) == 0U ||
        machine.registers[1] != 0xffff8000U)
    {
        return 0U;
    }

    machine.pc = 0U;
    if (run_one(encode_i(0x03U, 1U, 5U, 2U, 0U)) == 0U ||
        machine.registers[1] != 0x8000U)
    {
        return 0U;
    }

    machine.memory[128] = 0x78U;
    machine.memory[129] = 0x56U;
    machine.memory[130] = 0x34U;
    machine.memory[131] = 0x12U;
    machine.pc = 0U;
    if (run_one(encode_i(0x03U, 1U, 2U, 2U, 0U)) == 0U ||
        machine.registers[1] != 0x12345678U)
    {
        return 0U;
    }

    reset_case();
    machine.registers[1] = 128U;
    machine.registers[2] = 0x12345678U;
    if (run_one(encode_s(0U, 1U, 2U, 0U)) == 0U ||
        machine.memory[128] != 0x78U)
    {
        return 0U;
    }
    machine.pc = 0U;
    if (run_one(encode_s(1U, 1U, 2U, 2U)) == 0U ||
        machine.memory[130] != 0x78U || machine.memory[131] != 0x56U)
    {
        return 0U;
    }
    machine.pc = 0U;
    if (run_one(encode_s(2U, 1U, 2U, 4U)) == 0U ||
        machine.memory[132] != 0x78U || machine.memory[133] != 0x56U ||
        machine.memory[134] != 0x34U || machine.memory[135] != 0x12U)
    {
        return 0U;
    }
    return 1U;
}

static unsigned int test_traps_and_system(void)
{
    reset_case();
    machine.registers[2] = 129U;
    if (run_one(encode_i(0x03U, 1U, 2U, 2U, 0U)) != 0U ||
        machine.trap != RV32I_TRAP_MISALIGNED)
    {
        return 0U;
    }

    reset_case();
    machine.registers[2] = RV32I_MEMORY_BYTES;
    if (run_one(encode_i(0x03U, 1U, 2U, 2U, 0U)) != 0U ||
        machine.trap != RV32I_TRAP_BOUNDS)
    {
        return 0U;
    }

    reset_case();
    if (run_one(0U) != 0U || machine.trap != RV32I_TRAP_ILLEGAL)
    {
        return 0U;
    }

    reset_case();
    if (run_one(0x0000000fU) == 0U || machine.trap != 0U)
    {
        return 0U;
    }

    reset_case();
    if (run_one(0x00100073U) == 0U || machine.halted == 0U)
    {
        return 0U;
    }

    reset_case();
    machine.registers[2] = 123U;
    if (run_one(encode_i(0x13U, 0U, 0U, 2U, 1U)) == 0U ||
        machine.registers[0] != 0U)
    {
        return 0U;
    }
    return 1U;
}

int main(void)
{
    if (test_upper_and_immediate() == 0U)
    {
        return parity_fail(1U);
    }
    if (test_shifts() == 0U)
    {
        return parity_fail(2U);
    }
    if (test_register_alu() == 0U)
    {
        return parity_fail(3U);
    }
    if (test_branches() == 0U)
    {
        return parity_fail(4U);
    }
    if (test_jumps() == 0U)
    {
        return parity_fail(5U);
    }
    if (test_loads_and_stores() == 0U)
    {
        return parity_fail(6U);
    }
    if (test_traps_and_system() == 0U)
    {
        return parity_fail(7U);
    }
    if (run_smoke() == 0U)
    {
        return parity_fail(8U);
    }

    parity_text("RV32I-PARITY-v1\nOK\n");
    return 0;
}
