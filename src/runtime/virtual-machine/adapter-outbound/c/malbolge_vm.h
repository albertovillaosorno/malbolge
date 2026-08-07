// File:
//   - malbolge_vm.h
// Path:
//   - src/runtime/virtual-machine/adapter-outbound/c/malbolge_vm.h
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Public pure-C classic Malbolge VM state and execution interface.
// - Must-Not:
//   - Depend on Rust VM implementation details or historical C defects.
// - Allows:
//   - Inputs: validated source bytes, classic state, and byte input.
//   - Outputs: deterministic transitions, byte output, traces, diagnostics.
//   - Side effects: mutation only of caller-owned machine and output storage.
// - Split-When:
//   - Split when separate public C interfaces gain independent lifecycles.
// - Merge-When:
//   - Merge when another header owns the exact same public VM boundary.
// - Description:
//   - Declares fixed-memory classic VM state, diagnostics, tracing, and runs.
// - Usage:
//   - Included by the C implementation and independent C conformance harness.
// - Defaults:
//   - Exposes deterministic classic semantics without heap ownership.
// - Summary:
//   - Small auditable C interface for the normative classic machine.
//
// Related documents:
// - docs/technical/specification/malbolge-1998.md
// - docs/technical/runtime/vm/independent-pure-c-malbolge-vm.md
//
// Large file:
//   - false

#ifndef MALBOLGE_VM_C_MALBOLGE_VM_H
#define MALBOLGE_VM_C_MALBOLGE_VM_H

#include <stddef.h>
#include <stdint.h>

enum {
    MALBOLGE_MEMORY_WORDS = 59049,
    MALBOLGE_MAX_WORD = 59048,
};

typedef uint16_t MalbolgeWord;

typedef struct MalbolgeRegisters {
    MalbolgeWord accumulator;
    MalbolgeWord code_pointer;
    MalbolgeWord data_pointer;
} MalbolgeRegisters;

typedef enum MalbolgeTermination {
    MALBOLGE_TERMINATION_NONE = 0,
    MALBOLGE_TERMINATION_HALT,
    MALBOLGE_TERMINATION_NON_GRAPHICAL,
} MalbolgeTermination;

typedef enum MalbolgeDiagnosticCode {
    MALBOLGE_DIAGNOSTIC_NONE = 0,
    MALBOLGE_DIAGNOSTIC_INSUFFICIENT_RECURRENCE_BASE,
    MALBOLGE_DIAGNOSTIC_SOURCE_TOO_LONG,
    MALBOLGE_DIAGNOSTIC_INVALID_SOURCE_BYTE,
    MALBOLGE_DIAGNOSTIC_INVALID_SOURCE_INSTRUCTION,
    MALBOLGE_DIAGNOSTIC_INVALID_ENCRYPTION_TARGET,
    MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE,
    MALBOLGE_DIAGNOSTIC_OUTPUT_CAPACITY,
} MalbolgeDiagnosticCode;

typedef struct MalbolgeDiagnostic {
    MalbolgeDiagnosticCode code;
    size_t position;
    MalbolgeWord value;
} MalbolgeDiagnostic;

typedef enum MalbolgeStepOutcome {
    MALBOLGE_STEP_CONTINUED = 0,
    MALBOLGE_STEP_TERMINATED,
    MALBOLGE_STEP_REJECTED,
} MalbolgeStepOutcome;

typedef struct MalbolgeObservation {
    MalbolgeRegisters registers;
    size_t input_consumed;
    size_t output_length;
    MalbolgeTermination termination;
} MalbolgeObservation;

typedef struct MalbolgeTrace {
    MalbolgeObservation before;
    MalbolgeObservation after;
    MalbolgeStepOutcome outcome;
    MalbolgeDiagnostic diagnostic;
    MalbolgeWord fetched_cell;
    uint8_t decoded_instruction;
    uint8_t input_byte;
    uint8_t output_byte;
    uint8_t has_fetched_cell;
    uint8_t has_decoded_instruction;
    uint8_t has_input_byte;
    uint8_t input_was_eof;
    uint8_t has_output_byte;
} MalbolgeTrace;

/*
 * Storage note: memory[] alone occupies 118098 bytes because MalbolgeWord is
 * uint16_t. The complete machine is therefore unsuitable for automatic local
 * storage on stack-constrained threads or embedded targets. Prefer static
 * storage, a caller-owned arena, or caller-managed heap storage.
 */
typedef struct MalbolgeMachine {
    MalbolgeWord memory[MALBOLGE_MEMORY_WORDS];
    MalbolgeRegisters registers;
    const uint8_t *input;
    size_t input_length;
    size_t input_cursor;
    uint8_t *output;
    size_t output_capacity;
    size_t output_length;
    MalbolgeTermination termination;
} MalbolgeMachine;

MalbolgeWord malbolge_crazy(MalbolgeWord data, MalbolgeWord accumulator);
MalbolgeWord malbolge_rotate(MalbolgeWord value);

MalbolgeDiagnostic malbolge_machine_init(MalbolgeMachine *machine,
                                         const uint8_t *source,
                                         size_t source_length,
                                         const uint8_t *input,
                                         size_t input_length,
                                         uint8_t *output,
                                         size_t output_capacity);

void malbolge_machine_init_state(MalbolgeMachine *machine,
                                 MalbolgeWord fill,
                                 const uint8_t *input,
                                 size_t input_length,
                                 uint8_t *output,
                                 size_t output_capacity);

MalbolgeStepOutcome malbolge_step(MalbolgeMachine *machine,
                                  MalbolgeTrace *trace);

MalbolgeStepOutcome malbolge_run(MalbolgeMachine *machine,
                                 size_t step_budget,
                                 size_t *steps_executed,
                                 MalbolgeDiagnostic *diagnostic);

#endif
