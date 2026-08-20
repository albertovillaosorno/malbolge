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
//   - Independent executable conformance evidence for the pure-C VM.
// - Must-Not:
//   - Call the Rust VM or reproduce undefined host-C behavior.
// - Allows:
//   - Inputs: public C VM API and canonical interpreter fixture values.
//   - Outputs: zero for success or a deterministic failure count.
//   - Side effects: mutation of test-local machine and output storage only.
// - Split-When:
//   - Split when one conformance family requires independent executable
//     evidence.
// - Merge-When:
//   - Merge when another C harness owns the same interpreter evidence.
// - Summary:
//   - C-level tests for loader, primitives, instructions, and atomic rejection.
// - Description:
//   - Exercises the pure-C VM without calling the Rust implementation.
// - Usage:
//   - Compile as a standalone test or export its conformance entry points.
// - Defaults:
//   - Uses deterministic classic fixtures and a fixed semantic fingerprint.
//

//! Independent C conformance harness for interpreter-authority semantics.

#include "malbolge_vm.h"

static MalbolgeMachine g_machine;
static uint8_t g_output[8];
static uint8_t g_shared_io[8];
typedef union TraceAliasStorage {
    MalbolgeTrace trace;
    uint8_t bytes[sizeof(MalbolgeTrace)];
} TraceAliasStorage;
typedef union RunAliasStorage {
    size_t steps;
    MalbolgeDiagnostic diagnostic;
} RunAliasStorage;
static TraceAliasStorage g_trace_alias;
static RunAliasStorage g_run_alias;

int malbolge_c_conformance(void);
static int expect_true(int condition);

static int test_state_validation_and_control_edges(void)
{
    MalbolgeTrace trace;
    int failures = 0;

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.registers.code_pointer = UINT16_MAX;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code == MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE);
    failures += expect_true(trace.diagnostic.position == 1U);
    failures += expect_true(trace.diagnostic.value == UINT16_MAX);
    failures += expect_true(g_machine.registers.code_pointer == UINT16_MAX);

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'b';
    g_machine.memory[1] = UINT16_MAX;
    g_machine.registers.data_pointer = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code == MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE);
    failures += expect_true(trace.diagnostic.position == 1U);
    failures += expect_true(trace.diagnostic.value == UINT16_MAX);
    failures += expect_true(g_machine.registers.code_pointer == 0U);
    failures += expect_true(g_machine.registers.data_pointer == 1U);
    failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'b');

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'(';
    g_machine.memory[1] = 5U;
    g_machine.registers.data_pointer = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_CONTINUED);
    failures += expect_true(g_machine.registers.code_pointer == 1U);
    failures += expect_true(g_machine.registers.data_pointer == 6U);
    failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'y');

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'D';
    g_machine.registers.accumulator = 7U;
    g_machine.registers.data_pointer = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_CONTINUED);
    failures += expect_true(g_machine.registers.accumulator == 7U);
    failures += expect_true(g_machine.registers.code_pointer == 1U);
    failures += expect_true(g_machine.registers.data_pointer == 2U);
    failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'!');

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'Q';
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_TERMINATED);
    failures += expect_true(g_machine.termination == MALBOLGE_TERMINATION_HALT);
    failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'Q');
    failures += expect_true(g_machine.registers.code_pointer == 0U);
    failures += expect_true(g_machine.registers.data_pointer == 0U);

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output, 0U);
    g_machine.memory[0] = (MalbolgeWord)'c';
    g_machine.registers.accumulator = 7U;
    g_machine.registers.data_pointer = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code == MALBOLGE_DIAGNOSTIC_OUTPUT_CAPACITY);
    failures += expect_true(trace.has_output_byte == 0U);
    failures += expect_true(g_machine.output_length == 0U);
    failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'c');
    failures += expect_true(g_machine.registers.code_pointer == 0U);
    failures += expect_true(g_machine.registers.data_pointer == 1U);
    return failures;
}
uint64_t malbolge_c_semantic_signature(void);
int main(void);


static const uint64_t EXPECTED_SEMANTIC_SIGNATURE =
    UINT64_C(0xA9DABD8FC51D13C9);
static const uint64_t FNV_OFFSET = UINT64_C(14695981039346656037);
static const uint64_t FNV_PRIME = UINT64_C(1099511628211);
static const uint8_t SIGNATURE_CONTINUED = UINT8_C(0xA2);
static const uint8_t SIGNATURE_TERMINATED = UINT8_C(0xA1);
static const uint8_t SIGNATURE_HALT = UINT8_C(0xB1);
static const uint8_t SIGNATURE_NON_GRAPHICAL = UINT8_C(0xB2);
static const uint8_t SIGNATURE_INVALID_ENCRYPTION = UINT8_C(0xC1);
static const uint32_t SIGNATURE_MULTIPLIER = UINT32_C(17);
static const uint32_t SIGNATURE_INCREMENT = UINT32_C(23);

static uint64_t hash_byte(uint64_t hash, uint8_t value)
{
    return (hash ^ (uint64_t)value) * FNV_PRIME;
}

static uint64_t hash_word(uint64_t hash, MalbolgeWord value)
{
    hash = hash_byte(hash, (uint8_t)value);
    return hash_byte(hash, (uint8_t)(value >> 8U));
}
static int expect_true(int condition)
{
    return condition != 0 ? 0 : 1;
}

static int test_word_primitives(void)
{
    int failures = 0;
    failures += expect_true(malbolge_rotate(1U) == 19683U);
    failures += expect_true(malbolge_rotate(3U) == 1U);
    failures += expect_true(
        malbolge_rotate((MalbolgeWord)MALBOLGE_MAX_WORD) ==
        (MalbolgeWord)MALBOLGE_MAX_WORD);
    failures += expect_true(malbolge_crazy(0U, 0U) == 29524U);
    failures += expect_true(
        malbolge_crazy((MalbolgeWord)MALBOLGE_MAX_WORD, 0U) ==
        (MalbolgeWord)MALBOLGE_MAX_WORD);
    failures += expect_true(
        malbolge_crazy(0U, (MalbolgeWord)MALBOLGE_MAX_WORD) == 0U);
    return failures;
}

static int test_public_argument_validation(void)
{
    static const uint8_t SOURCE[] = {'u', 'b', 'O'};
    MalbolgeDiagnostic result;
    MalbolgeTrace trace;
    size_t steps = 99U;
    int failures = 0;

    result = malbolge_machine_init(NULL, SOURCE, sizeof(SOURCE), NULL, 0U,
                                   NULL, 0U);
    failures += expect_true(
        result.code == MALBOLGE_DIAGNOSTIC_INVALID_ARGUMENT);
    result = malbolge_machine_init(&g_machine, NULL, 1U, NULL, 0U,
                                   g_output, sizeof(g_output));
    failures += expect_true(
        result.code == MALBOLGE_DIAGNOSTIC_INVALID_ARGUMENT);
    result = malbolge_machine_init(&g_machine, SOURCE, sizeof(SOURCE),
                                   NULL, 1U, g_output, sizeof(g_output));
    failures += expect_true(
        result.code == MALBOLGE_DIAGNOSTIC_INVALID_ARGUMENT);
    result = malbolge_machine_init(&g_machine, SOURCE, sizeof(SOURCE),
                                   NULL, 0U, NULL, 1U);
    failures += expect_true(
        result.code == MALBOLGE_DIAGNOSTIC_INVALID_ARGUMENT);

    failures += expect_true(
        malbolge_step(NULL, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(trace.outcome == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code == MALBOLGE_DIAGNOSTIC_INVALID_ARGUMENT);

    result = (MalbolgeDiagnostic){MALBOLGE_DIAGNOSTIC_NONE, 0U, 0U};
    failures += expect_true(
        malbolge_run(NULL, 1U, &steps, &result) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(steps == 0U);
    failures += expect_true(
        result.code == MALBOLGE_DIAGNOSTIC_INVALID_ARGUMENT);

    failures += expect_true(
        malbolge_step(NULL, NULL) == MALBOLGE_STEP_REJECTED);
    result = (MalbolgeDiagnostic){MALBOLGE_DIAGNOSTIC_NONE, 0U, 0U};
    failures += expect_true(
        malbolge_run(&g_machine, 1U, NULL, &result) ==
        MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        result.code == MALBOLGE_DIAGNOSTIC_INVALID_ARGUMENT);
    steps = 99U;
    failures += expect_true(
        malbolge_run(&g_machine, 1U, &steps, NULL) ==
        MALBOLGE_STEP_REJECTED);
    failures += expect_true(steps == 0U);

    malbolge_machine_init_state(&g_machine, 7U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.registers.accumulator = 11U;
    malbolge_machine_init_state(NULL, 0U, NULL, 0U, NULL, 0U);
    malbolge_machine_init_state(&g_machine, 0U, NULL, 1U, g_output,
                                sizeof(g_output));
    failures += expect_true(g_machine.registers.accumulator == 11U);
    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, NULL, 1U);
    failures += expect_true(g_machine.registers.accumulator == 11U);
    malbolge_machine_init_state(&g_machine, UINT16_MAX, NULL, 0U, g_output,
                                sizeof(g_output));
    failures += expect_true(g_machine.registers.accumulator == 11U);

    {
        uint8_t *machine_bytes = (uint8_t *)(void *)&g_machine;
        machine_bytes[0] = (uint8_t)'u';
        machine_bytes[1] = (uint8_t)'b';
        machine_bytes[2] = (uint8_t)'O';
        result = malbolge_machine_init(
            &g_machine, machine_bytes, 3U, NULL, 0U, g_output,
            sizeof(g_output));
        failures += expect_true(
            result.code == MALBOLGE_DIAGNOSTIC_INVALID_ARGUMENT);
        failures += expect_true(machine_bytes[0] == (uint8_t)'u');
        failures += expect_true(machine_bytes[1] == (uint8_t)'b');
        failures += expect_true(machine_bytes[2] == (uint8_t)'O');
        result = malbolge_machine_init(
            &g_machine, SOURCE, sizeof(SOURCE), machine_bytes, 1U, g_output,
            sizeof(g_output));
        failures += expect_true(
            result.code == MALBOLGE_DIAGNOSTIC_INVALID_ARGUMENT);
        result = malbolge_machine_init(
            &g_machine, SOURCE, sizeof(SOURCE), NULL, 0U, machine_bytes, 1U);
        failures += expect_true(
            result.code == MALBOLGE_DIAGNOSTIC_INVALID_ARGUMENT);
        result = malbolge_machine_init(
            &g_machine, machine_bytes + sizeof(g_machine) - 1U, 2U, NULL, 0U,
            g_output, sizeof(g_output));
        failures += expect_true(
            result.code == MALBOLGE_DIAGNOSTIC_INVALID_ARGUMENT);
    }
    malbolge_machine_init_state(&g_machine, 7U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.registers.accumulator = 11U;
    malbolge_machine_init_state(
        &g_machine, 0U, (const uint8_t *)(const void *)g_machine.memory, 1U,
        g_output, sizeof(g_output));
    failures += expect_true(g_machine.registers.accumulator == 11U);
    malbolge_machine_init_state(
        &g_machine, 0U, NULL, 0U, (uint8_t *)(void *)g_machine.memory, 1U);
    failures += expect_true(g_machine.registers.accumulator == 11U);
    result = malbolge_machine_init(
        &g_machine, SOURCE, sizeof(SOURCE), g_shared_io, sizeof(g_shared_io),
        g_shared_io, sizeof(g_shared_io));
    failures += expect_true(
        result.code == MALBOLGE_DIAGNOSTIC_INVALID_ARGUMENT);
    malbolge_machine_init_state(&g_machine, 7U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.registers.accumulator = 11U;
    malbolge_machine_init_state(
        &g_machine, 0U, g_shared_io, sizeof(g_shared_io), g_shared_io,
        sizeof(g_shared_io));
    failures += expect_true(g_machine.registers.accumulator == 11U);
    malbolge_machine_init_state(&g_machine, 0U, g_shared_io, 4U,
                                g_shared_io + 4U, 4U);
    failures += expect_true(g_machine.input == g_shared_io);
    failures += expect_true(g_machine.input_length == 4U);
    failures += expect_true(g_machine.output == g_shared_io + 4U);
    failures += expect_true(g_machine.output_capacity == 4U);
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_CONTINUED);
    return failures;
}

static int test_auxiliary_output_alias_validation(void)
{
    MalbolgeDiagnostic result;
    size_t steps;
    int failures = 0;

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'D';
    failures += expect_true(
        malbolge_step(
            &g_machine, (MalbolgeTrace *)(void *)&g_machine) ==
        MALBOLGE_STEP_REJECTED);
    failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'D');
    failures += expect_true(g_machine.registers.code_pointer == 0U);

    for (size_t index = 0U; index < sizeof(g_trace_alias.bytes); ++index)
        g_trace_alias.bytes[index] = UINT8_C(0x5A);
    malbolge_machine_init_state(
        &g_machine, 0U, NULL, 0U, g_trace_alias.bytes,
        sizeof(g_trace_alias.bytes));
    g_machine.memory[0] = (MalbolgeWord)'D';
    failures += expect_true(
        malbolge_step(&g_machine, &g_trace_alias.trace) ==
        MALBOLGE_STEP_REJECTED);
    failures += expect_true(g_trace_alias.bytes[0] == UINT8_C(0x5A));
    failures += expect_true(g_machine.registers.code_pointer == 0U);

    for (size_t index = 0U; index < sizeof(g_trace_alias.bytes); ++index)
        g_trace_alias.bytes[index] = UINT8_C(0xA5);
    malbolge_machine_init_state(
        &g_machine, 0U, g_trace_alias.bytes, sizeof(g_trace_alias.bytes),
        g_output, sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'D';
    failures += expect_true(
        malbolge_step(&g_machine, &g_trace_alias.trace) ==
        MALBOLGE_STEP_REJECTED);
    failures += expect_true(g_trace_alias.bytes[0] == UINT8_C(0xA5));
    failures += expect_true(g_machine.registers.code_pointer == 0U);

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'D';
    result = (MalbolgeDiagnostic){MALBOLGE_DIAGNOSTIC_OUTPUT_CAPACITY, 7U, 9U};
    failures += expect_true(
        malbolge_run(
            &g_machine, 1U, (size_t *)(void *)&g_machine, &result) ==
        MALBOLGE_STEP_REJECTED);
    failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'D');
    failures += expect_true(
        result.code == MALBOLGE_DIAGNOSTIC_OUTPUT_CAPACITY);

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'D';
    steps = 17U;
    failures += expect_true(
        malbolge_run(
            &g_machine, 1U, &steps,
            (MalbolgeDiagnostic *)(void *)&g_machine) ==
        MALBOLGE_STEP_REJECTED);
    failures += expect_true(steps == 17U);
    failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'D');

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'D';
    failures += expect_true(
        malbolge_run(&g_machine, 1U, (size_t *)(void *)&g_machine, NULL) ==
        MALBOLGE_STEP_REJECTED);
    failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'D');
    failures += expect_true(g_machine.registers.code_pointer == 0U);

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'D';
    failures += expect_true(
        malbolge_run(&g_machine, 1U, NULL,
                     (MalbolgeDiagnostic *)(void *)&g_machine) ==
        MALBOLGE_STEP_REJECTED);
    failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'D');
    failures += expect_true(g_machine.registers.code_pointer == 0U);

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_run_alias.diagnostic = (MalbolgeDiagnostic){
        MALBOLGE_DIAGNOSTIC_INVALID_SOURCE_BYTE, 11U, 13U};
    failures += expect_true(
        malbolge_run(&g_machine, 0U, &g_run_alias.steps,
                     &g_run_alias.diagnostic) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        g_run_alias.diagnostic.code == MALBOLGE_DIAGNOSTIC_INVALID_SOURCE_BYTE);
    failures += expect_true(g_run_alias.diagnostic.position == 11U);
    failures += expect_true(g_run_alias.diagnostic.value == 13U);

    g_run_alias.diagnostic = (MalbolgeDiagnostic){
        MALBOLGE_DIAGNOSTIC_SOURCE_TOO_LONG, 17U, 19U};
    failures += expect_true(
        malbolge_run(NULL, 0U, &g_run_alias.steps, &g_run_alias.diagnostic) ==
        MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        g_run_alias.diagnostic.code == MALBOLGE_DIAGNOSTIC_SOURCE_TOO_LONG);
    failures += expect_true(g_run_alias.diagnostic.position == 17U);
    failures += expect_true(g_run_alias.diagnostic.value == 19U);
    return failures;
}

static int test_invalid_stream_state_rejects_before_io(void)
{
    MalbolgeTrace trace;
    int failures = 0;

    malbolge_machine_init_state(&g_machine, 33U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.input_length = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code == MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE);
    failures += expect_true(trace.diagnostic.position == 3U);

    malbolge_machine_init_state(&g_machine, 33U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.input_cursor = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code == MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE);
    failures += expect_true(trace.diagnostic.position == 3U);

    malbolge_machine_init_state(&g_machine, 33U, NULL, 0U, NULL, 0U);
    g_machine.output_capacity = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code == MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE);
    failures += expect_true(trace.diagnostic.position == 4U);

    malbolge_machine_init_state(&g_machine, 33U, NULL, 0U, g_output, 0U);
    g_machine.output_length = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code == MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE);
    failures += expect_true(trace.diagnostic.position == 4U);

    malbolge_machine_init_state(&g_machine, 33U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.input = (const uint8_t *)(const void *)g_machine.memory;
    g_machine.input_length = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code == MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE);
    failures += expect_true(trace.diagnostic.position == 3U);

    malbolge_machine_init_state(&g_machine, 33U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.output = (uint8_t *)(void *)g_machine.memory;
    g_machine.output_capacity = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code == MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE);
    failures += expect_true(trace.diagnostic.position == 4U);

    malbolge_machine_init_state(&g_machine, 33U, g_shared_io,
                                sizeof(g_shared_io), g_output,
                                sizeof(g_output));
    g_machine.output = g_shared_io;
    g_machine.output_capacity = sizeof(g_shared_io);
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code == MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE);
    failures += expect_true(trace.diagnostic.position == 4U);

    malbolge_machine_init_state(&g_machine, 33U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.termination = (MalbolgeTermination)99;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code == MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE);
    failures += expect_true(trace.diagnostic.position == 5U);
    {
        size_t run_steps = 99U;
        MalbolgeDiagnostic run_result = {
            MALBOLGE_DIAGNOSTIC_NONE, 0U, 0U};
        failures += expect_true(
            malbolge_run(&g_machine, 1U, &run_steps, &run_result) ==
            MALBOLGE_STEP_REJECTED);
        failures += expect_true(run_steps == 0U);
        failures += expect_true(
            run_result.code == MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE);
    }

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = UINT16_MAX;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code == MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE);
    failures += expect_true(trace.diagnostic.position == 0U);
    failures += expect_true(trace.diagnostic.value == UINT16_MAX);
    return failures;
}

static int test_loader_boundaries(void)
{
    static const uint8_t ONE_WORD[] = {'D'};
    static const uint8_t INVALID_BYTE[] = {UINT8_C(128)};
    static const uint8_t INVALID_INSTRUCTION[] = {'!'};
    MalbolgeDiagnostic result;
    int failures = 0;

    malbolge_machine_init_state(&g_machine, 7U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.registers.accumulator = 11U;
    result = malbolge_machine_init(&g_machine, NULL, 0U, NULL, 0U,
                                   g_output, sizeof(g_output));
    failures += expect_true(
        result.code == MALBOLGE_DIAGNOSTIC_INSUFFICIENT_RECURRENCE_BASE);
    failures += expect_true(g_machine.registers.accumulator == 11U);
    failures += expect_true(g_machine.memory[0] == 7U);
    result = malbolge_machine_init(&g_machine, ONE_WORD, sizeof(ONE_WORD),
                                   NULL, 0U, g_output, sizeof(g_output));
    failures += expect_true(
        result.code == MALBOLGE_DIAGNOSTIC_INSUFFICIENT_RECURRENCE_BASE);
    failures += expect_true(g_machine.registers.accumulator == 11U);
    failures += expect_true(g_machine.memory[0] == 7U);
    result = malbolge_machine_init(&g_machine, INVALID_BYTE,
                                   sizeof(INVALID_BYTE), NULL, 0U,
                                   g_output, sizeof(g_output));
    failures += expect_true(
        result.code == MALBOLGE_DIAGNOSTIC_INVALID_SOURCE_BYTE);
    failures += expect_true(g_machine.registers.accumulator == 11U);
    failures += expect_true(g_machine.memory[0] == 7U);
    result = malbolge_machine_init(&g_machine, INVALID_INSTRUCTION,
                                   sizeof(INVALID_INSTRUCTION), NULL, 0U,
                                   g_output, sizeof(g_output));
    failures += expect_true(
        result.code == MALBOLGE_DIAGNOSTIC_INVALID_SOURCE_INSTRUCTION);
    failures += expect_true(g_machine.registers.accumulator == 11U);
    failures += expect_true(g_machine.memory[0] == 7U);
    return failures;
}

static int test_roundtrip_fixture(void)
{
    static const uint8_t SOURCE[] = {'u', 'b', 'O'};
    static const uint8_t INPUT[] = {UINT8_C(0x41)};
    MalbolgeDiagnostic result;
    MalbolgeStepOutcome outcome;
    size_t steps = 0U;
    int failures = 0;

    result = malbolge_machine_init(&g_machine, SOURCE, sizeof(SOURCE),
                                   INPUT, sizeof(INPUT), g_output,
                                   sizeof(g_output));
    failures += expect_true(result.code == MALBOLGE_DIAGNOSTIC_NONE);
    failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'u');
    failures += expect_true(g_machine.memory[1] == (MalbolgeWord)'b');
    failures += expect_true(g_machine.memory[2] == (MalbolgeWord)'O');
    outcome = malbolge_run(&g_machine, 16U, &steps, &result);
    failures += expect_true(outcome == MALBOLGE_STEP_TERMINATED);
    failures += expect_true(
        g_machine.termination == MALBOLGE_TERMINATION_HALT);
    failures += expect_true(g_machine.input_cursor == 1U);
    failures += expect_true(g_machine.output_length == 1U);
    failures += expect_true(g_output[0] == UINT8_C(0x41));
    failures += expect_true(steps == 3U);
    return failures;
}

static int test_non_graphical_non_progress(void)
{
    MalbolgeTrace trace;
    const MalbolgeRegisters before = {7U, 0U, 0U};
    int failures = 0;

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.registers = before;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_CONTINUED);
    failures += expect_true(
        g_machine.termination == MALBOLGE_TERMINATION_NONE);
    failures += expect_true(g_machine.registers.accumulator == 7U);
    failures += expect_true(g_machine.registers.code_pointer == 0U);
    failures += expect_true(g_machine.registers.data_pointer == 0U);
    return failures;
}

static int test_byte_io_edges(void)
{
    MalbolgeTrace trace;
    int failures = 0;

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'c';
    g_machine.registers.accumulator = (MalbolgeWord)MALBOLGE_MAX_WORD;
    g_machine.registers.data_pointer = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_CONTINUED);
    failures += expect_true(g_machine.output_length == 1U);
    failures += expect_true(g_output[0] == UINT8_C(0xA8));

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'u';
    g_machine.registers.data_pointer = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_CONTINUED);
    failures += expect_true(
        g_machine.registers.accumulator == (MalbolgeWord)MALBOLGE_MAX_WORD);
    failures += expect_true(g_machine.input_cursor == 0U);
    failures += expect_true(trace.input_was_eof != 0U);
    return failures;
}

static int test_jump_encryption_and_atomic_rejection(void)
{
    MalbolgeTrace trace;
    int failures = 0;

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'b';
    g_machine.memory[1] = 2U;
    g_machine.memory[2] = (MalbolgeWord)'D';
    g_machine.registers.accumulator = 7U;
    g_machine.registers.data_pointer = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_CONTINUED);
    failures += expect_true(g_machine.registers.code_pointer == 3U);
    failures += expect_true(g_machine.registers.data_pointer == 2U);
    failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'b');
    failures += expect_true(g_machine.memory[2] == (MalbolgeWord)'!');

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'b';
    g_machine.memory[1] = 2U;
    g_machine.registers.accumulator = 7U;
    g_machine.registers.data_pointer = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_REJECTED);
    failures += expect_true(
        trace.diagnostic.code ==
        MALBOLGE_DIAGNOSTIC_INVALID_ENCRYPTION_TARGET);
    failures += expect_true(trace.diagnostic.position == 2U);
    failures += expect_true(trace.diagnostic.value == 0U);
    failures += expect_true(g_machine.registers.accumulator == 7U);
    failures += expect_true(g_machine.registers.code_pointer == 0U);
    failures += expect_true(g_machine.registers.data_pointer == 1U);
    failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'b');
    failures += expect_true(g_machine.input_cursor == 0U);
    failures += expect_true(g_machine.output_length == 0U);

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'b';
    g_machine.memory[1] = 2U;
    g_machine.registers.accumulator = 7U;
    g_machine.registers.data_pointer = 1U;
    {
        size_t run_steps = 99U;
        MalbolgeDiagnostic run_result = {
            MALBOLGE_DIAGNOSTIC_NONE, 0U, 0U};
        failures += expect_true(
            malbolge_run(&g_machine, 1U, &run_steps, &run_result) ==
            MALBOLGE_STEP_REJECTED);
        failures += expect_true(run_steps == 0U);
        failures += expect_true(
            run_result.code ==
            MALBOLGE_DIAGNOSTIC_INVALID_ENCRYPTION_TARGET);
        failures += expect_true(g_machine.registers.accumulator == 7U);
        failures += expect_true(g_machine.registers.code_pointer == 0U);
        failures += expect_true(g_machine.registers.data_pointer == 1U);
        failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'b');
    }

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'D';
    g_machine.memory[1] = UINT16_MAX;
    {
        size_t run_steps = 99U;
        MalbolgeDiagnostic run_result = {
            MALBOLGE_DIAGNOSTIC_NONE, 0U, 0U};
        failures += expect_true(
            malbolge_run(&g_machine, 2U, &run_steps, &run_result) ==
            MALBOLGE_STEP_REJECTED);
        failures += expect_true(run_steps == 1U);
        failures += expect_true(
            run_result.code == MALBOLGE_DIAGNOSTIC_INVALID_MACHINE_STATE);
        failures += expect_true(run_result.position == 1U);
        failures += expect_true(run_result.value == UINT16_MAX);
        failures += expect_true(g_machine.registers.code_pointer == 1U);
        failures += expect_true(g_machine.registers.data_pointer == 1U);
        failures += expect_true(g_machine.memory[0] == (MalbolgeWord)'!');
        failures += expect_true(g_machine.memory[1] == UINT16_MAX);
    }
    return failures;
}

static int test_rotate_crazy_and_wrap(void)
{
    MalbolgeTrace trace;
    int failures = 0;

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'\'';
    g_machine.memory[1] = 1U;
    g_machine.registers.data_pointer = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_CONTINUED);
    failures += expect_true(g_machine.registers.accumulator == 19683U);
    failures += expect_true(g_machine.memory[1] == 19683U);

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'>';
    g_machine.memory[1] = 0U;
    g_machine.registers.data_pointer = 1U;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_CONTINUED);
    failures += expect_true(g_machine.registers.accumulator == 29524U);
    failures += expect_true(g_machine.memory[1] == 29524U);

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[MALBOLGE_MAX_WORD] = (MalbolgeWord)'4';
    g_machine.registers.accumulator = 7U;
    g_machine.registers.code_pointer = (MalbolgeWord)MALBOLGE_MAX_WORD;
    g_machine.registers.data_pointer = (MalbolgeWord)MALBOLGE_MAX_WORD;
    failures += expect_true(
        malbolge_step(&g_machine, &trace) == MALBOLGE_STEP_CONTINUED);
    failures += expect_true(g_machine.registers.code_pointer == 0U);
    failures += expect_true(g_machine.registers.data_pointer == 0U);
    failures += expect_true(
        g_machine.memory[MALBOLGE_MAX_WORD] == (MalbolgeWord)'H');
    return failures;
}


uint64_t malbolge_c_semantic_signature(void)
{
    static const uint8_t SOURCE[] = {'u', 'b', 'O'};
    static const uint8_t INPUT[] = {UINT8_C(0x41)};
    MalbolgeDiagnostic result;
    MalbolgeStepOutcome outcome;
    MalbolgeTrace trace;
    uint64_t hash = FNV_OFFSET;
    uint32_t raw_value = 0U;
    size_t memory_index = 0U;
    size_t steps = 0U;

    for (raw_value = 0U; raw_value <= (uint32_t)MALBOLGE_MAX_WORD;
         ++raw_value) {
        const MalbolgeWord value = (MalbolgeWord)raw_value;
        const uint32_t paired_raw =
            (raw_value * SIGNATURE_MULTIPLIER + SIGNATURE_INCREMENT) %
            (uint32_t)MALBOLGE_MEMORY_WORDS;
        const MalbolgeWord paired = (MalbolgeWord)paired_raw;
        hash = hash_word(hash, malbolge_rotate(value));
        hash = hash_word(hash, malbolge_crazy(value, paired));
    }

    result = malbolge_machine_init(&g_machine, SOURCE, sizeof(SOURCE),
                                   INPUT, sizeof(INPUT), g_output,
                                   sizeof(g_output));
    if (result.code != MALBOLGE_DIAGNOSTIC_NONE) {
        return 0U;
    }
    for (memory_index = 0U;
         memory_index < (size_t)MALBOLGE_MEMORY_WORDS;
         ++memory_index) {
        hash = hash_word(hash, g_machine.memory[memory_index]);
    }
    outcome = malbolge_run(&g_machine, 16U, &steps, &result);
    if (outcome != MALBOLGE_STEP_TERMINATED ||
        result.code != MALBOLGE_DIAGNOSTIC_NONE) {
        return 0U;
    }
    hash = hash_byte(hash, SIGNATURE_TERMINATED);
    hash = hash_byte(hash, SIGNATURE_HALT);
    hash = hash_word(hash, g_machine.registers.accumulator);
    hash = hash_word(hash, g_machine.registers.code_pointer);
    hash = hash_word(hash, g_machine.registers.data_pointer);
    hash = hash_word(hash, (MalbolgeWord)g_machine.input_cursor);
    hash = hash_byte(hash, (uint8_t)g_machine.output_length);
    hash = hash_byte(hash, g_output[0]);
    hash = hash_byte(hash, (uint8_t)steps);

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    g_machine.memory[0] = (MalbolgeWord)'b';
    g_machine.memory[1] = 2U;
    g_machine.registers.accumulator = 7U;
    g_machine.registers.data_pointer = 1U;
    outcome = malbolge_step(&g_machine, &trace);
    if (outcome != MALBOLGE_STEP_REJECTED ||
        trace.diagnostic.code !=
            MALBOLGE_DIAGNOSTIC_INVALID_ENCRYPTION_TARGET) {
        return 0U;
    }
    hash = hash_byte(hash, SIGNATURE_INVALID_ENCRYPTION);
    hash = hash_word(hash, (MalbolgeWord)trace.diagnostic.position);
    hash = hash_word(hash, trace.diagnostic.value);
    hash = hash_word(hash, g_machine.registers.accumulator);
    hash = hash_word(hash, g_machine.registers.code_pointer);
    hash = hash_word(hash, g_machine.registers.data_pointer);
    hash = hash_word(hash, g_machine.memory[0]);

    malbolge_machine_init_state(&g_machine, 0U, NULL, 0U, g_output,
                                sizeof(g_output));
    outcome = malbolge_step(&g_machine, &trace);
    if (outcome != MALBOLGE_STEP_CONTINUED ||
        g_machine.termination != MALBOLGE_TERMINATION_NONE) {
        return 0U;
    }
    hash = hash_byte(hash, SIGNATURE_CONTINUED);
    hash = hash_byte(hash, SIGNATURE_NON_GRAPHICAL);
    hash = hash_word(hash, g_machine.registers.accumulator);
    hash = hash_word(hash, g_machine.registers.code_pointer);
    hash = hash_word(hash, g_machine.registers.data_pointer);
    return hash;
}
int malbolge_c_conformance(void)
{
    int failures = 0;
    failures += expect_true(
        malbolge_c_semantic_signature() == EXPECTED_SEMANTIC_SIGNATURE);
    failures += test_word_primitives();
    failures += test_public_argument_validation();
    failures += test_auxiliary_output_alias_validation();
    failures += test_invalid_stream_state_rejects_before_io();
    failures += test_loader_boundaries();
    failures += test_roundtrip_fixture();
    failures += test_non_graphical_non_progress();
    failures += test_byte_io_edges();
    failures += test_jump_encryption_and_atomic_rejection();
    failures += test_rotate_crazy_and_wrap();
    failures += test_state_validation_and_control_edges();
    return failures;
}

int main(void)
{
    return malbolge_c_conformance();
}
