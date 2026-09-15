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
//   - A compact deterministic state-machine stress fixture.
// - Must-Not:
//   - Use generated transition tables, heap allocation, libc, or host services.
// - Allows:
//   - Inputs: none.
//   - Outputs: "OK\n" after the exact final machine state is reached.
//   - Side effects: fundamental guest byte output only.
// - Split-When:
//   - Split when another transition topology needs an independent oracle.
// - Merge-When:
//   - Merge when another fixture owns the same deterministic state evolution.
// - Summary:
//   - Execute hundreds of fully coupled transitions from a tiny static machine.
// - Description:
//   - Five phases mutate six fields, with every transition feeding later work.
// - Usage:
//   - Compile as one freestanding guest C translation unit.
// - Defaults:
//   - Emit nothing unless every final field matches the oracle.
//

//! Compact deterministic state-machine stress fixture.

void __malbolge_output_byte(unsigned int value);

enum
{
    EXPECTED_PHASE = 4,
    EXPECTED_V = 37357,
    EXPECTED_W = 2830,
    EXPECTED_X = 4392,
    EXPECTED_Y = 40274,
    EXPECTED_Z = 57871,
    MODULUS = 59049,
    ROUNDS = 729
};

typedef struct MachineState
{
    unsigned int x;
    unsigned int y;
    unsigned int z;
    unsigned int w;
    unsigned int v;
    unsigned int phase;
} MachineState;

static void emit_success(void)
{
    __malbolge_output_byte(79U);
    __malbolge_output_byte(75U);
    __malbolge_output_byte(10U);
}

static void transition(MachineState *state, unsigned int index)
{
    if (state->phase == 0U)
    {
        state->x = (state->x + state->y * 3U + index) % MODULUS;
        state->z = (state->z ^ state->x) % MODULUS;
        state->v = (state->v + state->z + 11U) % MODULUS;
        state->phase = 1U;
    }
    else if (state->phase == 1U)
    {
        state->y =
            (state->y + state->z * 5U + (state->x >> 1U)) % MODULUS;
        state->w = (state->w + state->y + 13U) % MODULUS;
        state->x = (state->x ^ state->w) % MODULUS;
        state->phase = 2U;
    }
    else if (state->phase == 2U)
    {
        state->z =
            (state->z + state->w * 7U + (state->y & 255U)) % MODULUS;
        state->v = (state->v + state->z / 3U + 17U) % MODULUS;
        state->y = (state->y ^ state->v) % MODULUS;
        state->phase = 3U;
    }
    else if (state->phase == 3U)
    {
        state->w =
            (state->w + state->v * 11U + state->z % 97U) % MODULUS;
        state->x = (state->x + state->w / 5U + 19U) % MODULUS;
        state->z = (state->z ^ state->x) % MODULUS;
        state->phase = 4U;
    }
    else
    {
        state->v =
            (state->v + state->x * 13U + state->y + 23U) % MODULUS;
        state->y =
            (state->y + (state->v >> 2U) + state->w) % MODULUS;
        state->w = (state->w ^ state->y) % MODULUS;
        state->phase = 0U;
    }

    state->x =
        (state->x + (state->v & 511U) + (state->w >> 3U)) % MODULUS;
    state->z =
        (state->z + (state->x ^ state->y) + index % 31U) % MODULUS;
}

int main(void)
{
    MachineState state;
    unsigned int index = 0U;

    state.x = 5U;
    state.y = 8U;
    state.z = 13U;
    state.w = 21U;
    state.v = 34U;
    state.phase = 0U;

    while (index < ROUNDS)
    {
        transition(&state, index);
        ++index;
    }

    if (state.x != EXPECTED_X || state.y != EXPECTED_Y ||
        state.z != EXPECTED_Z || state.w != EXPECTED_W ||
        state.v != EXPECTED_V || state.phase != EXPECTED_PHASE)
    {
        return 1;
    }

    emit_success();
    return 0;
}
