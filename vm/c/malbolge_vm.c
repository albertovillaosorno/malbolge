// File:
//   - malbolge_vm.c
// Path:
//   - vm/c/malbolge_vm.c
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Independent pure-C implementation of classic Malbolge semantics.
// - Must-Not:
//   - Share transition implementation code with the Rust VM.
// - Allows:
//   - Inputs: classic source/state plus caller-owned byte streams.
//   - Outputs: deterministic state transitions, traces, and diagnostics.
//   - Side effects: mutation only of caller-owned machine/output storage.
// - Split-When:
//   - Split when one semantic subsystem needs an independent audit boundary.
// - Merge-When:
//   - Merge when another C module owns the exact same transition semantics.
// - Summary:
//   - Specification-derived C oracle for classic Malbolge execution.
// - Description:
//   - Implements the written classic profile independently from the Rust VM.
// - Usage:
//   - Called through the public interface in `vm/c/malbolge_vm.h`.
// - Defaults:
//   - Executes only the normative classic profile with caller-owned I/O.
//
// Related documents:
// - docs/technical/specification/malbolge-1998.md
// - math/specification/malbolge-1998.tex
//
// Large file:
//   - false
//

//! Independent specification-derived classic Malbolge VM oracle.

#include "malbolge_vm.h"

#include <stdbool.h>

static const uint8_t XLAT1[] =
    "+b(29e*j1VMEKLyC})8&m#~W>qxdRp0wkrUo[D7,XTcA\"lI"
    ".v%{gJh4G\\-=O@5`_3i<?Z';FNQuY]szf$!BS/|t:Pn6^Ha";
static const uint8_t XLAT2[] =
    "5z]&gqtyfr$(we4{WP)H-Zn,[%\\3dL+Q;>U!pJS72FhOA1C"
    "B6v^=I_0/8|jsb9m<.TVac`uY*MK'X~xDl}REokN:#?G\"i@";

static const MalbolgeWord GRAPHICAL_START = 33U;
static const MalbolgeWord GRAPHICAL_END = 126U;
static const size_t TRANSLATION_LENGTH = 94U;
static const MalbolgeWord RADIX = 3U;
static const MalbolgeWord ROTATE_WEIGHT = 19683U;
static const size_t TRIT_COUNT = 10U;

static MalbolgeDiagnostic diagnostic(MalbolgeDiagnosticCode code,
                                     size_t position,
                                     MalbolgeWord value)
{
    MalbolgeDiagnostic result = {code, position, value};
    return result;
}

static bool is_ascii_whitespace(uint8_t byte)
{
    return byte == UINT8_C(9) || byte == UINT8_C(10) ||
           byte == UINT8_C(11) || byte == UINT8_C(12) ||
           byte == UINT8_C(13) || byte == UINT8_C(32);
}

static bool is_graphical(MalbolgeWord value)
{
    return value >= GRAPHICAL_START && value <= GRAPHICAL_END;
}

static bool is_classic_word(MalbolgeWord value)
{
    return value <= (MalbolgeWord)MALBOLGE_MAX_WORD;
}

static MalbolgeDiagnostic validate_registers(const MalbolgeMachine *machine)
{
    if (!is_classic_word(machine->registers.accumulator)) {
        return diagnostic(MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE,
                          0U, machine->registers.accumulator);
    }
    if (!is_classic_word(machine->registers.code_pointer)) {
        return diagnostic(MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE,
                          1U, machine->registers.code_pointer);
    }
    if (!is_classic_word(machine->registers.data_pointer)) {
        return diagnostic(MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE,
                          2U, machine->registers.data_pointer);
    }
    return diagnostic(MALBOLGE_DIAGNOSTIC_NONE, 0U, 0U);
}

static MalbolgeWord successor(MalbolgeWord value)
{
    if (value == (MalbolgeWord)MALBOLGE_MAX_WORD) {
        return 0U;
    }
    return (MalbolgeWord)(value + 1U);
}

static uint8_t decode(MalbolgeWord cell, MalbolgeWord code_pointer)
{
    const size_t offset = (size_t)(cell - GRAPHICAL_START);
    const size_t pointer = (size_t)code_pointer;
    const size_t index = (offset + pointer) % TRANSLATION_LENGTH;
    return XLAT1[index];
}

static MalbolgeWord encrypt(MalbolgeWord cell)
{
    const size_t index = (size_t)(cell - GRAPHICAL_START);
    return (MalbolgeWord)XLAT2[index];
}

static bool instruction_reads_data(uint8_t decoded)
{
    return decoded == (uint8_t)'j' || decoded == (uint8_t)'i' ||
           decoded == (uint8_t)'*' || decoded == (uint8_t)'p';
}

static bool admitted_instruction(uint8_t decoded)
{
    switch (decoded) {
    case 'j':
    case 'i':
    case '*':
    case 'p':
    case '<':
    case '/':
    case 'v':
    case 'o':
        return true;
    default:
        return false;
    }
}

MalbolgeWord malbolge_crazy(MalbolgeWord data, MalbolgeWord accumulator)
{
    static const MalbolgeWord CRAZY_TRITS[3][3] = {
        {1U, 0U, 0U},
        {1U, 0U, 2U},
        {2U, 2U, 1U},
    };
    MalbolgeWord result = 0U;
    MalbolgeWord place = 1U;
    size_t trit_index = 0U;

    for (trit_index = 0U; trit_index < TRIT_COUNT; ++trit_index) {
        const MalbolgeWord data_trit = (MalbolgeWord)(data % RADIX);
        const MalbolgeWord accumulator_trit =
            (MalbolgeWord)(accumulator % RADIX);
        result = (MalbolgeWord)(
            result + CRAZY_TRITS[data_trit][accumulator_trit] * place);
        place = (MalbolgeWord)(place * RADIX);
        data = (MalbolgeWord)(data / RADIX);
        accumulator = (MalbolgeWord)(accumulator / RADIX);
    }
    return result;
}

MalbolgeWord malbolge_rotate(MalbolgeWord value)
{
    const MalbolgeWord low_trit = (MalbolgeWord)(value % RADIX);
    return (MalbolgeWord)(value / RADIX + low_trit * ROTATE_WEIGHT);
}

static MalbolgeDiagnostic validate_source(const uint8_t *source,
                                          size_t source_length,
                                          size_t *admitted_length)
{
    size_t loaded_position = 0U;
    size_t offset = 0U;

    for (offset = 0U; offset < source_length; ++offset) {
        const uint8_t byte = source[offset];
        uint8_t decoded = 0U;
        if (is_ascii_whitespace(byte)) {
            continue;
        }
        if (byte < (uint8_t)GRAPHICAL_START ||
            byte > (uint8_t)GRAPHICAL_END) {
            return diagnostic(MALBOLGE_DIAGNOSTIC_INVALID_SOURCE_BYTE,
                              offset, (MalbolgeWord)byte);
        }
        if (loaded_position >= (size_t)MALBOLGE_MEMORY_WORDS) {
            return diagnostic(MALBOLGE_DIAGNOSTIC_SOURCE_TOO_LONG,
                              loaded_position, (MalbolgeWord)byte);
        }
        decoded = decode((MalbolgeWord)byte,
                         (MalbolgeWord)loaded_position);
        if (!admitted_instruction(decoded)) {
            return diagnostic(
                MALBOLGE_DIAGNOSTIC_INVALID_SOURCE_INSTRUCTION,
                loaded_position, (MalbolgeWord)byte);
        }
        ++loaded_position;
    }
    if (loaded_position < 2U) {
        return diagnostic(
            MALBOLGE_DIAGNOSTIC_INSUFFICIENT_RECURRENCE_BASE,
            loaded_position, 0U);
    }
    *admitted_length = loaded_position;
    return diagnostic(MALBOLGE_DIAGNOSTIC_NONE, 0U, 0U);
}

static void load_validated(MalbolgeMachine *machine,
                           const uint8_t *source,
                           size_t source_length,
                           size_t admitted_length)
{
    size_t source_offset = 0U;
    size_t memory_index = 0U;

    for (source_offset = 0U; source_offset < source_length; ++source_offset) {
        const uint8_t byte = source[source_offset];
        if (!is_ascii_whitespace(byte)) {
            machine->memory[memory_index] = (MalbolgeWord)byte;
            ++memory_index;
        }
    }
    while (memory_index < (size_t)MALBOLGE_MEMORY_WORDS) {
        machine->memory[memory_index] = malbolge_crazy(
            machine->memory[memory_index - 2U],
            machine->memory[memory_index - 1U]);
        ++memory_index;
    }
    (void)admitted_length;
}

void malbolge_machine_init_state(MalbolgeMachine *machine,
                                 MalbolgeWord fill,
                                 const uint8_t *input,
                                 size_t input_length,
                                 uint8_t *output,
                                 size_t output_capacity)
{
    size_t index = 0U;
    for (index = 0U; index < (size_t)MALBOLGE_MEMORY_WORDS; ++index) {
        machine->memory[index] = fill;
    }
    machine->registers.accumulator = 0U;
    machine->registers.code_pointer = 0U;
    machine->registers.data_pointer = 0U;
    machine->input = input;
    machine->input_length = input_length;
    machine->input_cursor = 0U;
    machine->output = output;
    machine->output_capacity = output_capacity;
    machine->output_length = 0U;
    machine->termination = MALBOLGE_TERMINATION_NONE;
}

MalbolgeDiagnostic malbolge_machine_init(MalbolgeMachine *machine,
                                         const uint8_t *source,
                                         size_t source_length,
                                         const uint8_t *input,
                                         size_t input_length,
                                         uint8_t *output,
                                         size_t output_capacity)
{
    size_t admitted_length = 0U;
    const MalbolgeDiagnostic result =
        validate_source(source, source_length, &admitted_length);
    if (result.code != MALBOLGE_DIAGNOSTIC_NONE) {
        return result;
    }
    malbolge_machine_init_state(machine, 0U, input, input_length, output,
                                output_capacity);
    load_validated(machine, source, source_length, admitted_length);
    return result;
}

static MalbolgeObservation observe(const MalbolgeMachine *machine)
{
    MalbolgeObservation observation = {
        machine->registers,
        machine->input_cursor,
        machine->output_length,
        machine->termination,
    };
    return observation;
}

static void trace_begin(MalbolgeTrace *trace, const MalbolgeMachine *machine)
{
    if (trace == NULL) {
        return;
    }
    *trace = (MalbolgeTrace){0};
    trace->before = observe(machine);
    trace->after = trace->before;
    trace->diagnostic = diagnostic(MALBOLGE_DIAGNOSTIC_NONE, 0U, 0U);
}

static void trace_finish(MalbolgeTrace *trace,
                         const MalbolgeMachine *machine,
                         MalbolgeStepOutcome outcome,
                         MalbolgeDiagnostic result)
{
    if (trace == NULL) {
        return;
    }
    trace->after = observe(machine);
    trace->outcome = outcome;
    trace->diagnostic = result;
}

static MalbolgeStepOutcome terminate(MalbolgeMachine *machine,
                                     MalbolgeTermination reason,
                                     MalbolgeTrace *trace)
{
    machine->termination = reason;
    trace_finish(trace, machine, MALBOLGE_STEP_TERMINATED,
                 diagnostic(MALBOLGE_DIAGNOSTIC_NONE, 0U, 0U));
    return MALBOLGE_STEP_TERMINATED;
}

typedef struct Transition {
    MalbolgeRegisters registers;
    MalbolgeWord memory_address;
    MalbolgeWord memory_value;
    uint8_t output_byte;
    bool writes_memory;
    bool consumes_input;
    bool emits_output;
} Transition;

static Transition transition_start(const MalbolgeMachine *machine)
{
    Transition next = {
        machine->registers,
        0U,
        0U,
        0U,
        false,
        false,
        false,
    };
    return next;
}

static void apply_instruction(const MalbolgeMachine *machine,
                              uint8_t decoded,
                              Transition *next)
{
    const MalbolgeWord data_value =
        machine->memory[machine->registers.data_pointer];
    switch (decoded) {
    case 'j':
        next->registers.data_pointer = data_value;
        break;
    case 'i':
        next->registers.code_pointer = data_value;
        break;
    case '*':
        next->memory_address = machine->registers.data_pointer;
        next->memory_value = malbolge_rotate(data_value);
        next->registers.accumulator = next->memory_value;
        next->writes_memory = true;
        break;
    case 'p':
        next->memory_address = machine->registers.data_pointer;
        next->memory_value =
            malbolge_crazy(data_value, machine->registers.accumulator);
        next->registers.accumulator = next->memory_value;
        next->writes_memory = true;
        break;
    case '<':
        if (machine->input_cursor < machine->input_length) {
            next->registers.accumulator =
                (MalbolgeWord)machine->input[machine->input_cursor];
            next->consumes_input = true;
        } else {
            next->registers.accumulator = (MalbolgeWord)MALBOLGE_MAX_WORD;
        }
        break;
    case '/':
        next->output_byte = (uint8_t)machine->registers.accumulator;
        next->emits_output = true;
        break;
    case 'o':
    default:
        break;
    }
}

static MalbolgeWord encryption_target(const MalbolgeMachine *machine,
                                      const Transition *next)
{
    if (next->writes_memory &&
        next->memory_address == next->registers.code_pointer) {
        return next->memory_value;
    }
    return machine->memory[next->registers.code_pointer];
}

static MalbolgeDiagnostic validate_transition(const MalbolgeMachine *machine,
                                              const Transition *next)
{
    const MalbolgeWord target = encryption_target(machine, next);
    if (!is_graphical(target)) {
        return diagnostic(MALBOLGE_DIAGNOSTIC_INVALID_ENCRYPTION_TARGET,
                          (size_t)next->registers.code_pointer, target);
    }
    if (next->emits_output &&
        machine->output_length >= machine->output_capacity) {
        return diagnostic(MALBOLGE_DIAGNOSTIC_OUTPUT_CAPACITY,
                          machine->output_length, 0U);
    }
    return diagnostic(MALBOLGE_DIAGNOSTIC_NONE, 0U, 0U);
}

static void commit_transition(MalbolgeMachine *machine,
                              const Transition *next)
{
    const MalbolgeWord encryption_pointer = next->registers.code_pointer;
    const MalbolgeWord target = encryption_target(machine, next);
    if (next->writes_memory && next->memory_address != encryption_pointer) {
        machine->memory[next->memory_address] = next->memory_value;
    }
    machine->memory[encryption_pointer] = encrypt(target);
    machine->registers = next->registers;
    machine->registers.code_pointer =
        successor(machine->registers.code_pointer);
    machine->registers.data_pointer =
        successor(machine->registers.data_pointer);
    if (next->consumes_input) {
        ++machine->input_cursor;
    }
    if (next->emits_output) {
        machine->output[machine->output_length] = next->output_byte;
        ++machine->output_length;
    }
}

MalbolgeStepOutcome malbolge_step(MalbolgeMachine *machine,
                                  MalbolgeTrace *trace)
{
    MalbolgeWord cell = 0U;
    uint8_t decoded = 0U;
    Transition next;
    MalbolgeDiagnostic result;

    trace_begin(trace, machine);
    if (machine->termination != MALBOLGE_TERMINATION_NONE) {
        trace_finish(trace, machine, MALBOLGE_STEP_TERMINATED,
                     diagnostic(MALBOLGE_DIAGNOSTIC_NONE, 0U, 0U));
        return MALBOLGE_STEP_TERMINATED;
    }
    result = validate_registers(machine);
    if (result.code != MALBOLGE_DIAGNOSTIC_NONE) {
        trace_finish(trace, machine, MALBOLGE_STEP_REJECTED, result);
        return MALBOLGE_STEP_REJECTED;
    }
    cell = machine->memory[machine->registers.code_pointer];
    if (trace != NULL) {
        trace->has_fetched_cell = 1U;
        trace->fetched_cell = cell;
    }
    if (!is_graphical(cell)) {
        return terminate(machine, MALBOLGE_TERMINATION_NON_GRAPHICAL, trace);
    }
    decoded = decode(cell, machine->registers.code_pointer);
    if (trace != NULL) {
        trace->has_decoded_instruction = 1U;
        trace->decoded_instruction = decoded;
    }
    if (decoded == (uint8_t)'v') {
        return terminate(machine, MALBOLGE_TERMINATION_HALT, trace);
    }
    if (instruction_reads_data(decoded) &&
        !is_classic_word(machine->memory[machine->registers.data_pointer])) {
        result = diagnostic(MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE,
                            (size_t)machine->registers.data_pointer,
                            machine->memory[machine->registers.data_pointer]);
        trace_finish(trace, machine, MALBOLGE_STEP_REJECTED, result);
        return MALBOLGE_STEP_REJECTED;
    }
    next = transition_start(machine);
    apply_instruction(machine, decoded, &next);
    result = validate_transition(machine, &next);
    if (result.code != MALBOLGE_DIAGNOSTIC_NONE) {
        trace_finish(trace, machine, MALBOLGE_STEP_REJECTED, result);
        return MALBOLGE_STEP_REJECTED;
    }
    commit_transition(machine, &next);
    if (trace != NULL && decoded == (uint8_t)'<') {
        if (next.consumes_input) {
            trace->has_input_byte = 1U;
            trace->input_byte = (uint8_t)next.registers.accumulator;
        } else {
            trace->input_was_eof = 1U;
        }
    }
    if (trace != NULL && next.emits_output) {
        trace->has_output_byte = 1U;
        trace->output_byte = next.output_byte;
    }
    trace_finish(trace, machine, MALBOLGE_STEP_CONTINUED, result);
    return MALBOLGE_STEP_CONTINUED;
}

MalbolgeStepOutcome malbolge_run(MalbolgeMachine *machine,
                                 size_t step_budget,
                                 size_t *steps_executed,
                                 MalbolgeDiagnostic *result)
{
    size_t steps = 0U;
    MalbolgeStepOutcome outcome = MALBOLGE_STEP_CONTINUED;
    MalbolgeTrace trace;

    *result = diagnostic(MALBOLGE_DIAGNOSTIC_NONE, 0U, 0U);
    if (machine->termination != MALBOLGE_TERMINATION_NONE) {
        *steps_executed = 0U;
        return MALBOLGE_STEP_TERMINATED;
    }
    while (steps < step_budget) {
        outcome = malbolge_step(machine, &trace);
        ++steps;
        if (outcome != MALBOLGE_STEP_CONTINUED) {
            *steps_executed = steps;
            *result = trace.diagnostic;
            return outcome;
        }
    }
    *steps_executed = steps;
    return MALBOLGE_STEP_CONTINUED;
}
