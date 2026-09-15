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
//   - A project-authored deterministic RV32I interpreter fixture.
// - Must-Not:
//   - Copy a third-party RISC-V emulator implementation.
//   - Use hosted libc, heap allocation, threads, files, or host callbacks.
// - Allows:
//   - Inputs: one embedded project-authored RV32I machine-code program.
//   - Outputs: "OK\n" after the exact architectural oracle is reached.
//   - Side effects: fundamental guest byte output only.
// - Split-When:
//   - Binary ingestion or a richer RISC-V platform gains its own contract.
// - Merge-When:
//   - Another fixture owns the same complete RV32I execution boundary.
// - Summary:
//   - Exercise a standard 32-bit ISA interpreter inside guest C.
// - Description:
//   - Implements base RV32I integer, branch, load/store, jump, fence, and
//     system decoding over a deterministic little-endian memory image.
// - Usage:
//   - Compile as one freestanding guest C translation unit.
// - Defaults:
//   - Run an embedded summation loop and stop on EBREAK.
//

//! Project-authored RV32I interpreter bootstrap for Malbolge execution.

void __malbolge_output_byte(unsigned int value);

enum
{
    RV32I_MEMORY_BYTES = 4096,
    RV32I_REGISTER_COUNT = 32,
    RV32I_STEP_LIMIT = 256,
    RV32I_TRAP_BOUNDS = 1,
    RV32I_TRAP_ILLEGAL = 2,
    RV32I_TRAP_MISALIGNED = 3
};

typedef struct Rv32Machine
{
    unsigned int registers[RV32I_REGISTER_COUNT];
    unsigned int pc;
    unsigned int steps;
    unsigned int halted;
    unsigned int trap;
    unsigned char memory[RV32I_MEMORY_BYTES];
} Rv32Machine;

static Rv32Machine machine;

static unsigned int rv32_sign_extend(unsigned int value, unsigned int bits)
{
    const unsigned int sign = 1U << (bits - 1U);
    const unsigned int mask = (1U << bits) - 1U;
    const unsigned int narrowed = value & mask;

    return (narrowed ^ sign) - sign;
}

static int rv32_signed(unsigned int value)
{
    if (value <= 2147483647U)
    {
        return (int)value;
    }
    return -1 - (int)(~value);
}

static unsigned int rv32_bounds(unsigned int address, unsigned int width)
{
    if (address >= RV32I_MEMORY_BYTES)
    {
        return 0U;
    }
    return width <= RV32I_MEMORY_BYTES - address;
}

static unsigned int rv32_load8(const Rv32Machine *state,
                               unsigned int address,
                               unsigned int *valid)
{
    if (rv32_bounds(address, 1U) == 0U)
    {
        *valid = 0U;
        return 0U;
    }
    *valid = 1U;
    return state->memory[address];
}

static unsigned int rv32_load16(const Rv32Machine *state,
                                unsigned int address,
                                unsigned int *valid)
{
    if ((address & 1U) != 0U || rv32_bounds(address, 2U) == 0U)
    {
        *valid = 0U;
        return 0U;
    }
    *valid = 1U;
    return (unsigned int)state->memory[address] |
        ((unsigned int)state->memory[address + 1U] << 8U);
}

static unsigned int rv32_load32(const Rv32Machine *state,
                                unsigned int address,
                                unsigned int *valid)
{
    if ((address & 3U) != 0U || rv32_bounds(address, 4U) == 0U)
    {
        *valid = 0U;
        return 0U;
    }
    *valid = 1U;
    return (unsigned int)state->memory[address] |
        ((unsigned int)state->memory[address + 1U] << 8U) |
        ((unsigned int)state->memory[address + 2U] << 16U) |
        ((unsigned int)state->memory[address + 3U] << 24U);
}

static unsigned int rv32_store8(Rv32Machine *state, unsigned int address,
                                unsigned int value)
{
    if (rv32_bounds(address, 1U) == 0U)
    {
        return 0U;
    }
    state->memory[address] = (unsigned char)value;
    return 1U;
}

static unsigned int rv32_store16(Rv32Machine *state, unsigned int address,
                                 unsigned int value)
{
    if ((address & 1U) != 0U || rv32_bounds(address, 2U) == 0U)
    {
        return 0U;
    }
    state->memory[address] = (unsigned char)value;
    state->memory[address + 1U] = (unsigned char)(value >> 8U);
    return 1U;
}

static unsigned int rv32_store32(Rv32Machine *state, unsigned int address,
                                 unsigned int value)
{
    if ((address & 3U) != 0U || rv32_bounds(address, 4U) == 0U)
    {
        return 0U;
    }
    state->memory[address] = (unsigned char)value;
    state->memory[address + 1U] = (unsigned char)(value >> 8U);
    state->memory[address + 2U] = (unsigned char)(value >> 16U);
    state->memory[address + 3U] = (unsigned char)(value >> 24U);
    return 1U;
}

static unsigned int rv32_i_imm(unsigned int instruction)
{
    return rv32_sign_extend(instruction >> 20U, 12U);
}

static unsigned int rv32_s_imm(unsigned int instruction)
{
    const unsigned int value = ((instruction >> 25U) << 5U) |
        ((instruction >> 7U) & 31U);

    return rv32_sign_extend(value, 12U);
}

static unsigned int rv32_b_imm(unsigned int instruction)
{
    const unsigned int value = ((instruction >> 31U) << 12U) |
        (((instruction >> 7U) & 1U) << 11U) |
        (((instruction >> 25U) & 63U) << 5U) |
        (((instruction >> 8U) & 15U) << 1U);

    return rv32_sign_extend(value, 13U);
}

static unsigned int rv32_j_imm(unsigned int instruction)
{
    const unsigned int value = ((instruction >> 31U) << 20U) |
        (((instruction >> 12U) & 255U) << 12U) |
        (((instruction >> 20U) & 1U) << 11U) |
        (((instruction >> 21U) & 1023U) << 1U);

    return rv32_sign_extend(value, 21U);
}

static void rv32_write_register(Rv32Machine *state, unsigned int index,
                                unsigned int value)
{
    if (index != 0U)
    {
        state->registers[index] = value;
    }
}

static unsigned int rv32_execute_load(Rv32Machine *state,
                                      unsigned int instruction)
{
    const unsigned int rd = (instruction >> 7U) & 31U;
    const unsigned int funct3 = (instruction >> 12U) & 7U;
    const unsigned int rs1 = (instruction >> 15U) & 31U;
    const unsigned int address = state->registers[rs1] +
        rv32_i_imm(instruction);
    unsigned int valid = 0U;
    unsigned int value;

    if (funct3 == 0U || funct3 == 4U)
    {
        value = rv32_load8(state, address, &valid);
        if (valid != 0U && funct3 == 0U)
        {
            value = rv32_sign_extend(value, 8U);
        }
    }
    else if (funct3 == 1U || funct3 == 5U)
    {
        value = rv32_load16(state, address, &valid);
        if (valid != 0U && funct3 == 1U)
        {
            value = rv32_sign_extend(value, 16U);
        }
    }
    else if (funct3 == 2U)
    {
        value = rv32_load32(state, address, &valid);
    }
    else
    {
        state->trap = RV32I_TRAP_ILLEGAL;
        return 0U;
    }

    if (valid == 0U)
    {
        state->trap = (funct3 == 1U || funct3 == 2U || funct3 == 5U) &&
                (address & ((funct3 == 2U) ? 3U : 1U)) != 0U
            ? RV32I_TRAP_MISALIGNED
            : RV32I_TRAP_BOUNDS;
        return 0U;
    }
    rv32_write_register(state, rd, value);
    return 1U;
}

static unsigned int rv32_execute_store(Rv32Machine *state,
                                       unsigned int instruction)
{
    const unsigned int funct3 = (instruction >> 12U) & 7U;
    const unsigned int rs1 = (instruction >> 15U) & 31U;
    const unsigned int rs2 = (instruction >> 20U) & 31U;
    const unsigned int address = state->registers[rs1] +
        rv32_s_imm(instruction);
    unsigned int success;

    if (funct3 == 0U)
    {
        success = rv32_store8(state, address, state->registers[rs2]);
    }
    else if (funct3 == 1U)
    {
        success = rv32_store16(state, address, state->registers[rs2]);
    }
    else if (funct3 == 2U)
    {
        success = rv32_store32(state, address, state->registers[rs2]);
    }
    else
    {
        state->trap = RV32I_TRAP_ILLEGAL;
        return 0U;
    }

    if (success == 0U)
    {
        state->trap = (funct3 == 1U || funct3 == 2U) &&
                (address & ((funct3 == 2U) ? 3U : 1U)) != 0U
            ? RV32I_TRAP_MISALIGNED
            : RV32I_TRAP_BOUNDS;
        return 0U;
    }
    return 1U;
}

static unsigned int rv32_execute_branch(Rv32Machine *state,
                                        unsigned int instruction,
                                        unsigned int current_pc)
{
    const unsigned int funct3 = (instruction >> 12U) & 7U;
    const unsigned int rs1 = (instruction >> 15U) & 31U;
    const unsigned int rs2 = (instruction >> 20U) & 31U;
    const unsigned int left = state->registers[rs1];
    const unsigned int right = state->registers[rs2];
    unsigned int taken = 0U;

    if (funct3 == 0U)
    {
        taken = left == right;
    }
    else if (funct3 == 1U)
    {
        taken = left != right;
    }
    else if (funct3 == 4U)
    {
        taken = rv32_signed(left) < rv32_signed(right);
    }
    else if (funct3 == 5U)
    {
        taken = rv32_signed(left) >= rv32_signed(right);
    }
    else if (funct3 == 6U)
    {
        taken = left < right;
    }
    else if (funct3 == 7U)
    {
        taken = left >= right;
    }
    else
    {
        state->trap = RV32I_TRAP_ILLEGAL;
        return 0U;
    }

    if (taken != 0U)
    {
        state->pc = current_pc + rv32_b_imm(instruction);
    }
    return 1U;
}

static unsigned int rv32_execute_op_imm(Rv32Machine *state,
                                        unsigned int instruction)
{
    const unsigned int rd = (instruction >> 7U) & 31U;
    const unsigned int funct3 = (instruction >> 12U) & 7U;
    const unsigned int rs1 = (instruction >> 15U) & 31U;
    const unsigned int left = state->registers[rs1];
    const unsigned int immediate = rv32_i_imm(instruction);
    const unsigned int shamt = (instruction >> 20U) & 31U;
    const unsigned int funct7 = instruction >> 25U;
    unsigned int result;

    if (funct3 == 0U)
    {
        result = left + immediate;
    }
    else if (funct3 == 2U)
    {
        result = rv32_signed(left) < rv32_signed(immediate);
    }
    else if (funct3 == 3U)
    {
        result = left < immediate;
    }
    else if (funct3 == 4U)
    {
        result = left ^ immediate;
    }
    else if (funct3 == 6U)
    {
        result = left | immediate;
    }
    else if (funct3 == 7U)
    {
        result = left & immediate;
    }
    else if (funct3 == 1U && funct7 == 0U)
    {
        result = left << shamt;
    }
    else if (funct3 == 5U && funct7 == 0U)
    {
        result = left >> shamt;
    }
    else if (funct3 == 5U && funct7 == 32U)
    {
        result = (unsigned int)(rv32_signed(left) >> shamt);
    }
    else
    {
        state->trap = RV32I_TRAP_ILLEGAL;
        return 0U;
    }

    rv32_write_register(state, rd, result);
    return 1U;
}

static unsigned int rv32_execute_op(Rv32Machine *state,
                                    unsigned int instruction)
{
    const unsigned int rd = (instruction >> 7U) & 31U;
    const unsigned int funct3 = (instruction >> 12U) & 7U;
    const unsigned int rs1 = (instruction >> 15U) & 31U;
    const unsigned int rs2 = (instruction >> 20U) & 31U;
    const unsigned int funct7 = instruction >> 25U;
    const unsigned int left = state->registers[rs1];
    const unsigned int right = state->registers[rs2];
    unsigned int result;

    if (funct3 == 0U && funct7 == 0U)
    {
        result = left + right;
    }
    else if (funct3 == 0U && funct7 == 32U)
    {
        result = left - right;
    }
    else if (funct3 == 1U && funct7 == 0U)
    {
        result = left << (right & 31U);
    }
    else if (funct3 == 2U && funct7 == 0U)
    {
        result = rv32_signed(left) < rv32_signed(right);
    }
    else if (funct3 == 3U && funct7 == 0U)
    {
        result = left < right;
    }
    else if (funct3 == 4U && funct7 == 0U)
    {
        result = left ^ right;
    }
    else if (funct3 == 5U && funct7 == 0U)
    {
        result = left >> (right & 31U);
    }
    else if (funct3 == 5U && funct7 == 32U)
    {
        result = (unsigned int)(rv32_signed(left) >> (right & 31U));
    }
    else if (funct3 == 6U && funct7 == 0U)
    {
        result = left | right;
    }
    else if (funct3 == 7U && funct7 == 0U)
    {
        result = left & right;
    }
    else
    {
        state->trap = RV32I_TRAP_ILLEGAL;
        return 0U;
    }

    rv32_write_register(state, rd, result);
    return 1U;
}

static unsigned int rv32_step(Rv32Machine *state)
{
    unsigned int valid = 0U;
    const unsigned int current_pc = state->pc;
    const unsigned int instruction = rv32_load32(state, current_pc, &valid);
    const unsigned int opcode = instruction & 127U;
    const unsigned int rd = (instruction >> 7U) & 31U;
    const unsigned int rs1 = (instruction >> 15U) & 31U;

    if (valid == 0U)
    {
        state->trap = (current_pc & 3U) != 0U ? RV32I_TRAP_MISALIGNED
                                             : RV32I_TRAP_BOUNDS;
        return 0U;
    }
    state->pc = current_pc + 4U;
    ++state->steps;

    if (opcode == 0x37U)
    {
        rv32_write_register(state, rd, instruction & 0xfffff000U);
    }
    else if (opcode == 0x17U)
    {
        rv32_write_register(state, rd,
                            current_pc + (instruction & 0xfffff000U));
    }
    else if (opcode == 0x6fU)
    {
        rv32_write_register(state, rd, current_pc + 4U);
        state->pc = current_pc + rv32_j_imm(instruction);
    }
    else if (opcode == 0x67U)
    {
        const unsigned int target =
            (state->registers[rs1] + rv32_i_imm(instruction)) & ~1U;

        if (((instruction >> 12U) & 7U) != 0U)
        {
            state->trap = RV32I_TRAP_ILLEGAL;
            return 0U;
        }
        rv32_write_register(state, rd, current_pc + 4U);
        state->pc = target;
    }
    else if (opcode == 0x63U)
    {
        if (rv32_execute_branch(state, instruction, current_pc) == 0U)
        {
            return 0U;
        }
    }
    else if (opcode == 0x03U)
    {
        if (rv32_execute_load(state, instruction) == 0U)
        {
            return 0U;
        }
    }
    else if (opcode == 0x23U)
    {
        if (rv32_execute_store(state, instruction) == 0U)
        {
            return 0U;
        }
    }
    else if (opcode == 0x13U)
    {
        if (rv32_execute_op_imm(state, instruction) == 0U)
        {
            return 0U;
        }
    }
    else if (opcode == 0x33U)
    {
        if (rv32_execute_op(state, instruction) == 0U)
        {
            return 0U;
        }
    }
    else if (opcode == 0x0fU)
    {
        if (((instruction >> 12U) & 7U) > 1U)
        {
            state->trap = RV32I_TRAP_ILLEGAL;
            return 0U;
        }
    }
    else if (opcode == 0x73U && instruction == 0x00100073U)
    {
        state->halted = 1U;
    }
    else
    {
        state->trap = RV32I_TRAP_ILLEGAL;
        return 0U;
    }

    state->registers[0] = 0U;
    return 1U;
}

static void rv32_load_program_word(Rv32Machine *state, unsigned int address,
                                   unsigned int word)
{
    (void)rv32_store32(state, address, word);
}

static void rv32_load_smoke_program(Rv32Machine *state)
{
    rv32_load_program_word(state, 0U, 0x00a00093U);
    rv32_load_program_word(state, 4U, 0x00000113U);
    rv32_load_program_word(state, 8U, 0x10000193U);
    rv32_load_program_word(state, 12U, 0x00110133U);
    rv32_load_program_word(state, 16U, 0xfff08093U);
    rv32_load_program_word(state, 20U, 0xfe009ce3U);
    rv32_load_program_word(state, 24U, 0x0021a023U);
    rv32_load_program_word(state, 28U, 0x00100073U);
}

static unsigned int run_smoke(void)
{
    unsigned int index = 0U;
    unsigned int valid = 0U;
    unsigned int result;

    while (index < RV32I_REGISTER_COUNT)
    {
        machine.registers[index] = 0U;
        ++index;
    }
    machine.pc = 0U;
    machine.steps = 0U;
    machine.halted = 0U;
    machine.trap = 0U;
    rv32_load_smoke_program(&machine);

    while (machine.halted == 0U && machine.steps < RV32I_STEP_LIMIT)
    {
        if (rv32_step(&machine) == 0U)
        {
            return 0U;
        }
    }
    if (machine.halted == 0U || machine.trap != 0U)
    {
        return 0U;
    }

    result = rv32_load32(&machine, 256U, &valid);
    return valid != 0U && result == 55U && machine.registers[1] == 0U &&
        machine.registers[2] == 55U && machine.registers[3] == 256U &&
        machine.registers[0] == 0U;
}

static void emit_success(void)
{
    __malbolge_output_byte(79U);
    __malbolge_output_byte(75U);
    __malbolge_output_byte(10U);
}

int main(void)
{
    if (run_smoke() == 0U)
    {
        return 1;
    }
    emit_success();
    return 0;
}
