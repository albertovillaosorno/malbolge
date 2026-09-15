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
//   - A project-authored Block II AGC execution-core fixture.
// - Must-Not:
//   - Claim Luminary execution before the complete AGC contract is implemented.
//   - Copy third-party emulator implementation code into this fixture.
//   - Use hosted libc, heap allocation, threads, files, or host callbacks.
// - Allows:
//   - Inputs: one embedded project-authored AGC instruction smoke image.
//   - Outputs: "OK\n" after the exact AGC state oracle is reached.
//   - Side effects: fundamental guest byte output only.
// - Split-When:
//   - Rope-image ingestion or DSKY I/O gains an independent guest contract.
// - Merge-When:
//   - Another fixture owns the same complete Block II execution boundary.
// - Summary:
//   - Exercise a real AGC-shaped machine model before Luminary integration.
// - Description:
//   - Models Block II word arithmetic, banked erasable/fixed memory, registers,
//     and the basic instruction families used by the embedded smoke program.
// - Usage:
//   - Compile as one freestanding guest C translation unit.
// - Defaults:
//   - Execute eight AGC instructions from fixed-fixed bank 02.
//

//! Project-authored Apollo Guidance Computer Block II runner bootstrap.

void __malbolge_output_byte(unsigned int value);

enum
{
    AGC_CHANNEL_COUNT = 512,
    AGC_ERASABLE_WORDS = 2048,
    AGC_FIXED_BANK_WORDS = 1024,
    AGC_FIXED_WORDS = 36864,
    AGC_LOGICAL_ADDRESS_MASK = 07777,
    AGC_REG_A = 00000,
    AGC_REG_L = 00001,
    AGC_REG_Q = 00002,
    AGC_REG_EB = 00003,
    AGC_REG_FB = 00004,
    AGC_REG_Z = 00005,
    AGC_REG_BB = 00006,
    AGC_SMOKE_RESULT = 00101,
    AGC_SMOKE_SCRATCH = 00100,
    AGC_WORD_MASK = 077777
};

typedef struct AgcMachine
{
    unsigned int erasable[AGC_ERASABLE_WORDS];
    unsigned int fixed[AGC_FIXED_WORDS];
    unsigned int channels[AGC_CHANNEL_COUNT];
    unsigned int indexed_instruction;
    unsigned int index_pending;
} AgcMachine;

static AgcMachine machine;

static unsigned int agc_word(unsigned int value)
{
    return value & AGC_WORD_MASK;
}

static unsigned int agc_ones_add(unsigned int left, unsigned int right)
{
    unsigned int sum = agc_word(left) + agc_word(right);

    sum = (sum & AGC_WORD_MASK) + (sum >> 15U);
    sum = (sum & AGC_WORD_MASK) + (sum >> 15U);
    return agc_word(sum);
}

static unsigned int agc_ones_negate(unsigned int value)
{
    return agc_word(~value);
}

static unsigned int agc_selected_erasable_bank(const AgcMachine *state)
{
    return (state->erasable[AGC_REG_EB] >> 8U) & 07U;
}

static unsigned int agc_selected_fixed_bank(const AgcMachine *state)
{
    unsigned int bank = (state->erasable[AGC_REG_FB] >> 10U) & 037U;
    const unsigned int superbank = state->channels[07] & 0100U;

    if (superbank != 0U && bank >= 030U && bank <= 033U)
    {
        bank += 010U;
    }
    return bank;
}

static void agc_write_bank_register(AgcMachine *state, unsigned int address,
                                    unsigned int value)
{
    const unsigned int word = agc_word(value);

    if (address == AGC_REG_EB)
    {
        const unsigned int bank = (word >> 8U) & 07U;

        state->erasable[AGC_REG_EB] = word;
        state->erasable[AGC_REG_BB] =
            (state->erasable[AGC_REG_BB] & 076000U) | bank;
        return;
    }
    if (address == AGC_REG_FB)
    {
        state->erasable[AGC_REG_FB] = word;
        state->erasable[AGC_REG_BB] =
            (state->erasable[AGC_REG_BB] & 07U) | (word & 076000U);
        return;
    }
    if (address == AGC_REG_BB)
    {
        const unsigned int ebank = word & 07U;

        state->erasable[AGC_REG_BB] = word;
        state->erasable[AGC_REG_EB] = ebank << 8U;
        state->erasable[AGC_REG_FB] = word & 076000U;
        return;
    }
    state->erasable[address] = word;
}

static unsigned int agc_fixed_index(const AgcMachine *state,
                                    unsigned int address,
                                    unsigned int *valid)
{
    unsigned int bank;
    unsigned int offset;

    if (address >= 04000U && address < 06000U)
    {
        bank = 02U;
        offset = address - 04000U;
    }
    else if (address >= 06000U && address <= 07777U)
    {
        bank = 03U;
        offset = address - 06000U;
    }
    else if (address >= 02000U && address < 04000U)
    {
        bank = agc_selected_fixed_bank(state);
        offset = address - 02000U;
    }
    else
    {
        *valid = 0U;
        return 0U;
    }

    if (bank >= 044U)
    {
        *valid = 0U;
        return 0U;
    }
    *valid = 1U;
    return bank * AGC_FIXED_BANK_WORDS + offset;
}

static unsigned int agc_read(const AgcMachine *state, unsigned int address,
                             unsigned int *valid)
{
    address &= AGC_LOGICAL_ADDRESS_MASK;
    if (address < 01400U)
    {
        *valid = 1U;
        return state->erasable[address];
    }
    if (address < 02000U)
    {
        const unsigned int bank = agc_selected_erasable_bank(state);
        const unsigned int offset = address - 01400U;

        *valid = 1U;
        return state->erasable[bank * 0400U + offset];
    }

    {
        const unsigned int index = agc_fixed_index(state, address, valid);

        if (*valid == 0U)
        {
            return 0U;
        }
        return state->fixed[index];
    }
}

static unsigned int agc_write(AgcMachine *state, unsigned int address,
                              unsigned int value)
{
    address &= AGC_LOGICAL_ADDRESS_MASK;
    if (address < 01400U)
    {
        agc_write_bank_register(state, address, value);
        return 1U;
    }
    if (address < 02000U)
    {
        const unsigned int bank = agc_selected_erasable_bank(state);
        const unsigned int offset = address - 01400U;

        state->erasable[bank * 0400U + offset] = agc_word(value);
        return 1U;
    }
    return 0U;
}

static unsigned int agc_fetch(AgcMachine *state, unsigned int *valid)
{
    const unsigned int pc = state->erasable[AGC_REG_Z] &
        AGC_LOGICAL_ADDRESS_MASK;
    unsigned int instruction = agc_read(state, pc, valid);

    if (*valid == 0U)
    {
        return 0U;
    }
    state->erasable[AGC_REG_Z] = (pc + 1U) & AGC_LOGICAL_ADDRESS_MASK;
    if (state->index_pending != 0U)
    {
        instruction = agc_ones_add(instruction, state->indexed_instruction);
        state->index_pending = 0U;
    }
    return instruction;
}

static unsigned int agc_step_basic(AgcMachine *state,
                                   unsigned int instruction)
{
    const unsigned int opcode = (instruction >> 12U) & 07U;
    const unsigned int address = instruction & AGC_LOGICAL_ADDRESS_MASK;
    unsigned int valid = 0U;
    unsigned int value;

    if (opcode == 0U)
    {
        state->erasable[AGC_REG_Q] = state->erasable[AGC_REG_Z];
        state->erasable[AGC_REG_Z] = address;
        return 1U;
    }
    if (opcode == 1U)
    {
        if (address < 02000U)
        {
            return 0U;
        }
        state->erasable[AGC_REG_Z] = address;
        return 1U;
    }
    if (opcode == 2U)
    {
        const unsigned int quarter = (instruction >> 10U) & 03U;
        const unsigned int operand = instruction & 01777U;

        value = agc_read(state, operand, &valid);
        if (valid == 0U)
        {
            return 0U;
        }
        if (quarter == 1U)
        {
            const unsigned int old_l = state->erasable[AGC_REG_L];

            state->erasable[AGC_REG_L] = value;
            return agc_write(state, operand, old_l);
        }
        if (quarter == 2U)
        {
            value = agc_ones_add(value, 1U);
            return agc_write(state, operand, value);
        }
        if (quarter == 3U)
        {
            value = agc_ones_add(value, state->erasable[AGC_REG_A]);
            state->erasable[AGC_REG_A] = value;
            return agc_write(state, operand, value);
        }
        return 0U;
    }
    if (opcode == 3U)
    {
        value = agc_read(state, address, &valid);
        if (valid != 0U)
        {
            state->erasable[AGC_REG_A] = value;
        }
        return valid;
    }
    if (opcode == 4U)
    {
        value = agc_read(state, address, &valid);
        if (valid != 0U)
        {
            state->erasable[AGC_REG_A] = agc_ones_negate(value);
        }
        return valid;
    }
    if (opcode == 5U)
    {
        const unsigned int quarter = (instruction >> 10U) & 03U;
        const unsigned int operand = instruction & 01777U;

        value = agc_read(state, operand, &valid);
        if (valid == 0U)
        {
            return 0U;
        }
        if (quarter == 0U)
        {
            state->indexed_instruction = value;
            state->index_pending = 1U;
            return 1U;
        }
        if (quarter == 1U)
        {
            const unsigned int old_a = state->erasable[AGC_REG_A];
            const unsigned int old_l = state->erasable[AGC_REG_L];
            unsigned int next = agc_read(state, operand + 1U, &valid);

            if (valid == 0U || agc_write(state, operand, old_a) == 0U ||
                agc_write(state, operand + 1U, old_l) == 0U)
            {
                return 0U;
            }
            state->erasable[AGC_REG_A] = value;
            state->erasable[AGC_REG_L] = next;
            return 1U;
        }
        if (quarter == 2U)
        {
            return agc_write(state, operand, state->erasable[AGC_REG_A]);
        }
        {
            const unsigned int old_a = state->erasable[AGC_REG_A];

            state->erasable[AGC_REG_A] = value;
            return agc_write(state, operand, old_a);
        }
    }
    if (opcode == 6U)
    {
        value = agc_read(state, address, &valid);
        if (valid != 0U)
        {
            state->erasable[AGC_REG_A] =
                agc_ones_add(state->erasable[AGC_REG_A], value);
        }
        return valid;
    }

    value = agc_read(state, address, &valid);
    if (valid != 0U)
    {
        state->erasable[AGC_REG_A] &= value;
    }
    return valid;
}

static unsigned int agc_step(AgcMachine *state)
{
    unsigned int valid = 0U;
    const unsigned int instruction = agc_fetch(state, &valid);

    if (valid == 0U)
    {
        return 0U;
    }
    return agc_step_basic(state, instruction);
}

static void load_smoke_rope(AgcMachine *state)
{
    const unsigned int bank_two = 02U * AGC_FIXED_BANK_WORDS;

    state->fixed[bank_two + 0000U] = 034010U;
    state->fixed[bank_two + 0001U] = 064011U;
    state->fixed[bank_two + 0002U] = 054100U;
    state->fixed[bank_two + 0003U] = 030100U;
    state->fixed[bank_two + 0004U] = 074012U;
    state->fixed[bank_two + 0005U] = 064013U;
    state->fixed[bank_two + 0006U] = 054101U;
    state->fixed[bank_two + 0007U] = 004007U;
    state->fixed[bank_two + 0010U] = 000021U;
    state->fixed[bank_two + 0011U] = 000031U;
    state->fixed[bank_two + 0012U] = AGC_WORD_MASK;
    state->fixed[bank_two + 0013U] = 000001U;
}

static unsigned int run_smoke(void)
{
    unsigned int step = 0U;

    machine.erasable[AGC_REG_A] = 0U;
    machine.erasable[AGC_REG_L] = 0U;
    machine.erasable[AGC_REG_Q] = 0U;
    machine.erasable[AGC_REG_EB] = 0U;
    machine.erasable[AGC_REG_FB] = 0U;
    machine.erasable[AGC_REG_Z] = 04000U;
    machine.erasable[AGC_REG_BB] = 0U;
    machine.erasable[AGC_SMOKE_SCRATCH] = 0U;
    machine.erasable[AGC_SMOKE_RESULT] = 0U;
    machine.channels[07] = 0U;
    machine.index_pending = 0U;
    machine.indexed_instruction = 0U;
    load_smoke_rope(&machine);

    while (step < 8U)
    {
        if (agc_step(&machine) == 0U)
        {
            return 0U;
        }
        ++step;
    }

    return machine.erasable[AGC_SMOKE_SCRATCH] == 42U &&
        machine.erasable[AGC_SMOKE_RESULT] == 43U &&
        machine.erasable[AGC_REG_A] == 43U &&
        machine.erasable[AGC_REG_Z] == 04007U &&
        machine.erasable[AGC_REG_Q] == 04010U;
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
