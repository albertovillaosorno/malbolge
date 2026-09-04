# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Shared exact resident CUDA kernel generator for modular Malbolge profiles.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#

"""Shared exact resident CUDA kernel generator for modular Malbolge profiles."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import cache

from accelerator.cuda.classic_step import XLAT1
from accelerator.cuda.classic_step import XLAT2
from accelerator.exact_primitives import CRAZY_TRIT_TABLE

CRAZY_CHUNK_VALUES = 243
CRAZY_TABLE_ENTRIES = CRAZY_CHUNK_VALUES * CRAZY_CHUNK_VALUES
MINIMUM_RESEARCH_CRAZY_WIDTH = 10
RESEARCH_CRAZY_WIDTHS = range(MINIMUM_RESEARCH_CRAZY_WIDTH, 15)
STATE_WORDS = 16


class ResidentCrazyGeometry(Enum):
    """Crazy arithmetic implementation selected for one rendered kernel."""

    NATIVE = "native-5+5+r"
    PADDED = "padded-5+5+5"
    TRITWISE = "tritwise"


@dataclass(frozen=True, slots=True)
class ResidentGeometry:
    """Compile-time geometry and semantics for one resident profile."""

    interpreter_authority: bool
    eof_word: int
    input_instruction: int
    memory_words: int
    output_instruction: int
    word_modulus: int
    word_trits: int


def resident_kernel_source(
    geometry: ResidentGeometry,
    kernel_name: str,
    *,
    crazy_geometry: object = ResidentCrazyGeometry.TRITWISE,
) -> str:
    """Render one exact CUDA kernel for a validated resident geometry.

    Returns:
        CUDA C++ source compiled by the pinned NVRTC boundary.

    """
    admitted_crazy_geometry = _validate_crazy_geometry(
        geometry.word_trits,
        crazy_geometry,
    )
    crazy_table = _crazy_table_source(admitted_crazy_geometry)
    crazy_word = _crazy_word_source(
        geometry.word_trits,
        admitted_crazy_geometry,
    )
    interpreter_authority = int(geometry.interpreter_authority)
    xlat1 = ",".join(str(value) for value in XLAT1)
    xlat2 = ",".join(str(value) for value in XLAT2)
    return f"""
#define INTERPRETER_AUTHORITY {interpreter_authority}u
#define MEMORY_WORDS {geometry.memory_words}u
#define STATE_WORDS {STATE_WORDS}u
#define MAX_WORD {geometry.word_modulus - 1}u
#define WORD_MODULUS {geometry.word_modulus}u
#define WORD_TRITS {geometry.word_trits}u
#define ROTATE_HIGH_WEIGHT {geometry.word_modulus // 3}u
#define EOF_WORD {geometry.eof_word}u
#define INPUT_INSTRUCTION {geometry.input_instruction}u
#define OUTPUT_INSTRUCTION {geometry.output_instruction}u
#define STATUS_BUDGET 0u
#define STATUS_TERMINATED 1u
#define STATUS_ERROR 2u
#define ERROR_NONE 0u
#define ERROR_INVALID_ENCRYPTION 1u
#define ERROR_INVALID_REQUEST 2u
#define TERMINATION_NONE 0u
#define TERMINATION_HALT 1u
#define TERMINATION_NON_GRAPHICAL 2u

static __device__ __constant__ unsigned char XLAT1[94] = {{{xlat1}}};
static __device__ __constant__ unsigned char XLAT2[94] = {{{xlat2}}};
{crazy_table}
static __device__ unsigned int successor(unsigned int value) {{
    return value == MAX_WORD ? 0u : value + 1u;
}}

static __device__ unsigned int rotate_word(unsigned int value) {{
    return (value / 3u) + ((value % 3u) * ROTATE_HIGH_WEIGHT);
}}

static __device__ unsigned int crazy_trit(
    unsigned int data,
    unsigned int acc
) {{
    if (((data == 0u || data == 1u) && acc == 0u)
        || (data == 2u && acc == 2u)) {{
        return 1u;
    }}
    if ((data == 1u && acc == 2u)
        || (data == 2u && (acc == 0u || acc == 1u))) {{
        return 2u;
    }}
    return 0u;
}}

{crazy_word}

static __device__ bool graphical(unsigned int value) {{
    return value >= 33u && value <= 126u;
}}

static __device__ void reject(
    unsigned int* state,
    unsigned int error,
    unsigned int pointer,
    unsigned int value
) {{
    state[11] = STATUS_ERROR;
    state[12] = error;
    state[13] = pointer;
    state[14] = value;
}}

extern "C" __global__ void {kernel_name}(
    unsigned int* states,
    unsigned int* memories,
    const unsigned int* inputs,
    unsigned int* outputs,
    unsigned int count
) {{
    unsigned int index = blockIdx.x * blockDim.x + threadIdx.x;
    if (index >= count) {{
        return;
    }}
    unsigned int* state = states + (index * STATE_WORDS);
    unsigned int* memory = memories + (index * MEMORY_WORDS);
    unsigned int a = state[0];
    unsigned int c = state[1];
    unsigned int d = state[2];
    unsigned int input_offset = state[3];
    unsigned int input_len = state[4];
    unsigned int input_consumed = state[5];
    unsigned int output_offset = state[6];
    unsigned int output_len = state[7];
    unsigned int output_capacity = state[8];
    unsigned int step_budget = state[9];
    unsigned int termination = state[10];

    state[11] = STATUS_BUDGET;
    state[12] = ERROR_NONE;
    state[13] = 0u;
    state[14] = 0u;
    state[15] = 0u;
    if (a > MAX_WORD || c > MAX_WORD || d > MAX_WORD
        || termination > TERMINATION_NON_GRAPHICAL
        || input_consumed > input_len || output_len > output_capacity) {{
        reject(state, ERROR_INVALID_REQUEST, 0u, 0u);
        return;
    }}
    if (termination != TERMINATION_NONE) {{
        state[11] = STATUS_TERMINATED;
        return;
    }}

    for (unsigned int step = 0u; step < step_budget; ++step) {{
        unsigned int cell = memory[c];
        if (cell > MAX_WORD) {{
            reject(state, ERROR_INVALID_REQUEST, c, cell);
            break;
        }}
        if (!graphical(cell)) {{
#if INTERPRETER_AUTHORITY
            state[15] += 1u;
            continue;
#else
            termination = TERMINATION_NON_GRAPHICAL;
            state[11] = STATUS_TERMINATED;
            state[15] += 1u;
            break;
#endif
        }}
        unsigned int decoded = XLAT1[((cell - 33u) + (c % 94u)) % 94u];
        if (decoded == (unsigned int)'v') {{
            termination = TERMINATION_HALT;
            state[11] = STATUS_TERMINATED;
            state[15] += 1u;
            break;
        }}
        unsigned int planned_a = a;
        unsigned int planned_c = c;
        unsigned int planned_d = d;
        unsigned int data_before = 0u;
        unsigned int data_after = 0u;
        bool data_write = false;
        bool input_advance = false;
        bool output_present = false;
        unsigned int output_value = 0u;

        if (decoded == (unsigned int)'p' || decoded == (unsigned int)'*'
            || decoded == (unsigned int)'i' || decoded == (unsigned int)'j') {{
            data_before = memory[d];
            if (data_before > MAX_WORD) {{
                reject(state, ERROR_INVALID_REQUEST, d, data_before);
                break;
            }}
        }}
        if (decoded == (unsigned int)'p') {{
            data_after = crazy_word(data_before, a);
            planned_a = data_after;
            data_write = true;
        }} else if (decoded == (unsigned int)'*') {{
            data_after = rotate_word(data_before);
            planned_a = data_after;
            data_write = true;
        }} else if (decoded == (unsigned int)'i') {{
            planned_c = data_before;
        }} else if (decoded == (unsigned int)'j') {{
            planned_d = data_before;
        }} else if (decoded == INPUT_INSTRUCTION) {{
            if (input_consumed < input_len) {{
                planned_a = inputs[input_offset + input_consumed];
                input_advance = true;
            }} else {{
                planned_a = EOF_WORD;
            }}
        }} else if (decoded == OUTPUT_INSTRUCTION) {{
            if (output_len >= output_capacity) {{
                reject(state, ERROR_INVALID_REQUEST, 0u, 0u);
                break;
            }}
            output_present = true;
            output_value = a & 255u;
        }}

        unsigned int encryption_pointer = planned_c;
        unsigned int encryption_before = memory[encryption_pointer];
        if (encryption_before > MAX_WORD) {{
            reject(
                state,
                ERROR_INVALID_REQUEST,
                encryption_pointer,
                encryption_before
            );
            break;
        }}
        unsigned int encryption_input = encryption_before;
        if (data_write && d == encryption_pointer) {{
            encryption_input = data_after;
        }}
        if (!graphical(encryption_input)) {{
            reject(
                state,
                ERROR_INVALID_ENCRYPTION,
                encryption_pointer,
                encryption_input
            );
            break;
        }}
        unsigned int encryption_after = XLAT2[encryption_input - 33u];

        if (data_write && d != encryption_pointer) {{
            memory[d] = data_after;
        }}
        memory[encryption_pointer] = encryption_after;
        a = planned_a;
        c = successor(planned_c);
        d = successor(planned_d);
        if (input_advance) {{
            input_consumed += 1u;
        }}
        if (output_present) {{
            outputs[output_offset + output_len] = output_value;
            output_len += 1u;
        }}
        state[15] += 1u;
    }}

    state[0] = a;
    state[1] = c;
    state[2] = d;
    state[5] = input_consumed;
    state[7] = output_len;
    state[10] = termination;
}}
"""


@cache
def _crazy_chunk_table_values() -> tuple[int, ...]:
    """Return the exact five-trit crazy lookup table.

    Returns:
        Row-major outputs indexed by ``data * 243 + accumulator``.

    """
    values: list[int] = []
    for data in range(CRAZY_CHUNK_VALUES):
        for accumulator in range(CRAZY_CHUNK_VALUES):
            remaining_data = data
            remaining_accumulator = accumulator
            result = 0
            place = 1
            for _ in range(5):
                output = CRAZY_TRIT_TABLE[remaining_data % 3][
                    remaining_accumulator % 3
                ]
                result += output * place
                place *= 3
                remaining_data //= 3
                remaining_accumulator //= 3
            values.append(result)
    return tuple(values)


def _crazy_table_source(crazy_geometry: ResidentCrazyGeometry) -> str:
    if crazy_geometry is ResidentCrazyGeometry.TRITWISE:
        return ""
    values = ",".join(str(value) for value in _crazy_chunk_table_values())
    return (
        f"#define CRAZY_CHUNK_VALUES {CRAZY_CHUNK_VALUES}u\n"
        f"static __device__ __constant__ unsigned char "
        f"CRAZY_CHUNK_TABLE[{CRAZY_TABLE_ENTRIES}] = {{{values}}};\n"
        "static __device__ unsigned int crazy_chunk_lookup(\n"
        "    unsigned int data,\n"
        "    unsigned int acc\n"
        ") {\n"
        "    return CRAZY_CHUNK_TABLE[(data * CRAZY_CHUNK_VALUES) + acc];\n"
        "}\n"
    )


def _crazy_word_source(
    word_trits: int,
    crazy_geometry: ResidentCrazyGeometry,
) -> str:
    if crazy_geometry is ResidentCrazyGeometry.TRITWISE:
        return r"""static __device__ unsigned int crazy_word(
    unsigned int data,
    unsigned int acc
) {
    unsigned int result = 0u;
    unsigned int place = 1u;
    for (unsigned int trit = 0u; trit < WORD_TRITS; ++trit) {
        result += crazy_trit(data % 3u, acc % 3u) * place;
        place *= 3u;
        data /= 3u;
        acc /= 3u;
    }
    return result;
}"""
    if crazy_geometry is ResidentCrazyGeometry.NATIVE:
        return r"""static __device__ unsigned int crazy_word(
    unsigned int data,
    unsigned int acc
) {
    unsigned int low = crazy_chunk_lookup(
        data % CRAZY_CHUNK_VALUES,
        acc % CRAZY_CHUNK_VALUES
    );
    data /= CRAZY_CHUNK_VALUES;
    acc /= CRAZY_CHUNK_VALUES;
    unsigned int middle = crazy_chunk_lookup(
        data % CRAZY_CHUNK_VALUES,
        acc % CRAZY_CHUNK_VALUES
    );
    data /= CRAZY_CHUNK_VALUES;
    acc /= CRAZY_CHUNK_VALUES;
    unsigned int result = low + (middle * CRAZY_CHUNK_VALUES);
    unsigned int place = CRAZY_CHUNK_VALUES * CRAZY_CHUNK_VALUES;
    for (unsigned int trit = 10u; trit < WORD_TRITS; ++trit) {
        result += crazy_trit(data % 3u, acc % 3u) * place;
        place *= 3u;
        data /= 3u;
        acc /= 3u;
    }
    return result;
}"""
    high = "" if word_trits == MINIMUM_RESEARCH_CRAZY_WIDTH else r"""
    unsigned int high = crazy_chunk_lookup(
        (data / (CRAZY_CHUNK_VALUES * CRAZY_CHUNK_VALUES)) % CRAZY_CHUNK_VALUES,
        (acc / (CRAZY_CHUNK_VALUES * CRAZY_CHUNK_VALUES)) % CRAZY_CHUNK_VALUES
    );
    result += high * CRAZY_CHUNK_VALUES * CRAZY_CHUNK_VALUES;
"""
    return r"""static __device__ unsigned int crazy_word(
    unsigned int data,
    unsigned int acc
) {
    unsigned int low = crazy_chunk_lookup(
        data % CRAZY_CHUNK_VALUES,
        acc % CRAZY_CHUNK_VALUES
    );
    unsigned int middle = crazy_chunk_lookup(
        (data / CRAZY_CHUNK_VALUES) % CRAZY_CHUNK_VALUES,
        (acc / CRAZY_CHUNK_VALUES) % CRAZY_CHUNK_VALUES
    );
    unsigned int result = low + (middle * CRAZY_CHUNK_VALUES);
""" + high + r"""    return result % WORD_MODULUS;
}"""


def _validate_crazy_geometry(
    word_trits: int,
    crazy_geometry: object,
) -> ResidentCrazyGeometry:
    if not isinstance(crazy_geometry, ResidentCrazyGeometry):
        message = "resident crazy geometry must use the exact enum"
        raise TypeError(message)
    if (
        crazy_geometry is not ResidentCrazyGeometry.TRITWISE
        and word_trits not in RESEARCH_CRAZY_WIDTHS
    ):
        message = (
            "chunked resident crazy geometry is limited to N10 through N14"
        )
        raise ValueError(message)
    return crazy_geometry
