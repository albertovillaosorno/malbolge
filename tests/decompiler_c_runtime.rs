// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Executable C differential evidence for decompiler runtime semantics.
// - Must-Not:
//   - Treat host C execution as normative Malbolge authority.
// - Allows:
//   - Inputs: synthetic source and pinned Clang on Linux.
//   - Outputs: exact byte I/O and atomic output-capacity assertions.
//   - Side effects: temporary C compilation and test-local cleanup.
// - Split-When:
//   - More target platforms require independently reviewed build policy.
// - Merge-When:
//   - Executable C differential coverage becomes part of another test surface.
// - Summary:
//   - Executes generated semantic C and compares it to the normative VM.
// - Description:
//   - Covers binary/EOF I/O, halt, refusal, arithmetic, and jumps.
// - Usage:
//   - Collected by Cargo tests on Linux using the repository-pinned Clang.
// - Defaults:
//   - Missing tools or mismatched semantics fail explicitly.
//
//! Pinned-Linux C execution evidence for the generated decompiler source.

#![cfg(target_os = "linux")]

use std::env::temp_dir;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, id};
use std::time::{SystemTime, UNIX_EPOCH};

use malbolge::{
    ProfileDescriptor, ProfileMachine, ProfileMachineError, RunOutcome,
    Termination, current_profile, decode_profile_instruction,
    historical_profile, target_profile,
};

const SOURCE: &[u8] = b"ubO";
const ARITHMETIC_SOURCE: &[u8] = b"(&<N";
const INVALID_JUMP_SOURCE: &[u8] = b"bP";
const INVALID_ROTATE_SOURCE: &[u8] = b"'C";
const INVALID_CRAZY_SOURCE: &[u8] = b">C";
const JUMP_SOURCE: &[u8] = &[
    98, 67, 66, 65, 64, 63, 62, 61, 60, 59, 58, 57, 56, 55, 54, 53, 52,
    51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35,
    34, 33, 126, 125, 124, 123, 122, 121, 120, 119, 118, 117, 116, 115, 114, 113, 112,
    111, 110, 109, 108, 107, 106, 105, 104, 103, 102, 101, 100, 99, 98, 97, 96, 95,
    94, 93, 92, 91, 90, 89, 88, 87, 86, 85, 84, 83, 82, 81, 80, 79, 78,
    77, 76, 75, 74, 73, 72, 71, 70, 69, 68, 67, 66, 65, 64, 112, 93, 74,
];
const HARNESS: &str = "
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int run_case(const uint8_t *input, size_t input_len, uint8_t expected)
{
    uint32_t *memory = calloc(MB_MEMORY_WORDS, sizeof(*memory));
    uint8_t output[1] = {0};
    struct mb_result result;
    int status;
    if (memory == NULL) { return 20; }
    status = malbolge_decompiled_run(memory, MB_MEMORY_WORDS,
        input, input_len, output, 1, 8, &result);
    free(memory);
    if (status != MB_STATUS_HALT || result.status != MB_STATUS_HALT
        || result.steps != 3 || result.output_len != 1
        || result.input_consumed != input_len || output[0] != expected) {
        return 21;
    }
    return fwrite(output, 1, 1, stdout) == 1 ? 0 : 22;
}

static int check_atomic_exhaustion(void)
{
    uint8_t input[] = {0x41};
    uint32_t *one = calloc(MB_MEMORY_WORDS, sizeof(*one));
    uint32_t *blocked = calloc(MB_MEMORY_WORDS, sizeof(*blocked));
    struct mb_result first;
    struct mb_result refused;
    int first_status;
    int refused_status;
    int same;
    if (one == NULL || blocked == NULL) {
        free(one);
        free(blocked);
        return 23;
    }
    first_status = malbolge_decompiled_run(one, MB_MEMORY_WORDS,
        input, 1, NULL, 0, 1, &first);
    refused_status = malbolge_decompiled_run(blocked, MB_MEMORY_WORDS,
        input, 1, NULL, 0, 8, &refused);
    same = memcmp(one, blocked, MB_MEMORY_WORDS * sizeof(*one)) == 0;
    free(one);
    free(blocked);
    if (first_status != MB_STATUS_BUDGET_EXHAUSTED
        || refused_status != MB_STATUS_OUTPUT_EXHAUSTED
        || refused.status != MB_STATUS_OUTPUT_EXHAUSTED
        || first.steps != 1 || refused.steps != 1
        || first.input_consumed != 1 || refused.input_consumed != 1
        || first.output_len != 0 || refused.output_len != 0
        || first.accumulator != refused.accumulator
        || first.code_pointer != refused.code_pointer
        || first.data_pointer != refused.data_pointer || !same) {
        return 24;
    }
    return 0;
}

int main(void)
{
    const uint8_t zero[] = {0x00};
    const uint8_t letter[] = {0x41};
    const uint8_t high[] = {0xff};
    int status = run_case(zero, 1, 0x00);
    if (status != 0) { return status; }
    status = run_case(letter, 1, 0x41);
    if (status != 0) { return status; }
    status = run_case(high, 1, 0xff);
    if (status != 0) { return status; }
    status = run_case(NULL, 0, EXPECTED_EOF_BYTE);
    if (status != 0) { return status; }
    return check_atomic_exhaustion();
}
";

const MEMORY_HARNESS: &str = "
#include <stdio.h>
#include <stdlib.h>

#ifndef EXPECTED_OUTPUT_LEN
#define EXPECTED_OUTPUT_LEN 0
#endif
#ifndef EXPECTED_OUTPUT_BYTE
#define EXPECTED_OUTPUT_BYTE 0
#endif
#ifndef EXPECTED_STEPS
#define EXPECTED_STEPS 4
#endif
#ifndef EXPECTED_STATUS
#define EXPECTED_STATUS MB_STATUS_HALT
#endif
#ifndef STEP_BUDGET
#define STEP_BUDGET 4
#endif

int main(void)
{
    uint32_t *memory = calloc(MB_MEMORY_WORDS, sizeof(*memory));
    struct mb_result result;
    uint8_t output[1] = {0};
    size_t index;
    int status;
    if (memory == NULL) { return 30; }
    status = malbolge_decompiled_run(memory, MB_MEMORY_WORDS,
        NULL, 0, output, EXPECTED_OUTPUT_LEN, STEP_BUDGET, &result);
    if (status != EXPECTED_STATUS || result.status != EXPECTED_STATUS
        || result.steps != EXPECTED_STEPS || result.output_len != EXPECTED_OUTPUT_LEN
        || result.input_consumed != 0
        || (EXPECTED_OUTPUT_LEN != 0 && output[0] != EXPECTED_OUTPUT_BYTE)) {
        free(memory);
        return 31;
    }
    for (index = 0; index < MB_MEMORY_WORDS + 3; ++index) {
        uint32_t value = index < MB_MEMORY_WORDS ? memory[index]
            : index == MB_MEMORY_WORDS ? result.accumulator
            : index == MB_MEMORY_WORDS + 1 ? result.code_pointer
            : result.data_pointer;
        uint8_t bytes[4] = {
            (uint8_t)value, (uint8_t)(value >> 8),
            (uint8_t)(value >> 16), (uint8_t)(value >> 24)
        };
        if (fwrite(bytes, 1, 4, stdout) != 4) {
            free(memory);
            return 32;
        }
    }
    free(memory);
    return 0;
}
";

#[derive(Clone, Copy)]
enum ExpectedVmOutcome {
    BudgetExhausted,
    Halt,
    InvalidEncryption,
    InvalidWriteEncryption,
    NonGraphical,
}

#[derive(Clone, Copy)]
struct GeneratedVmCase<'case> {
    expected_outcome: ExpectedVmOutcome,
    expected_output: &'case [u8],
    expected_steps: usize,
    harness: &'case str,
    profile: &'static ProfileDescriptor,
    source: &'case [u8],
}

fn temporary_directory() -> Result<PathBuf, String> {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| error.to_string())?
        .as_nanos();
    let directory = temp_dir().join(format!("malbolge-c-runtime-{}-{nonce}", id()));
    fs::create_dir_all(&directory).map_err(|error| error.to_string())?;
    Ok(directory)
}

fn generated_c_stdout(source: &Path, profile: &str) -> Result<Vec<u8>, String> {
    let rendered = Command::new(env!("CARGO_BIN_EXE_malbolge_decompile"))
        .args(["--profile", profile, "--representation", "c"])
        .arg(source)
        .output()
        .map_err(|error| format!("launch decompiler: {error}"))?;
    if !rendered.status.success() || !rendered.stderr.is_empty() {
        return Err(format!("decompiler C render failed: {rendered:?}"));
    }
    Ok(rendered.stdout)
}

fn compile_generated_program(
    directory: &Path,
    source_bytes: &[u8],
    profile: &str,
    harness: &str,
) -> Result<PathBuf, String> {
    let source = directory.join("program.malbolge");
    fs::write(&source, source_bytes).map_err(|error| error.to_string())?;
    let mut c_source = generated_c_stdout(&source, profile)?;
    c_source.extend_from_slice(harness.as_bytes());
    let c_path = directory.join("generated.c");
    fs::write(&c_path, c_source).map_err(|error| error.to_string())?;
    let executable = directory.join("generated-runner");
    let clang = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join(".dependencies/llvm/22.1.8/bin/clang");
    let compiled = Command::new(&clang)
        .args(["-std=c23", "-Wall", "-Wextra", "-Werror"])
        .arg(&c_path)
        .arg("-o")
        .arg(&executable)
        .output()
        .map_err(|error| format!("launch pinned Clang: {error}"))?;
    if !compiled.status.success() {
        return Err(format!(
            "generated C rejected by Clang: {}",
            String::from_utf8_lossy(&compiled.stderr),
        ));
    }
    Ok(executable)
}

fn binary_io_source(profile: &ProfileDescriptor) -> Result<[u8; 3], String> {
    let mut source = [0u8; 3];
    for (index, (cell, opcode)) in source.iter_mut().zip([
        profile.input_instruction(),
        profile.output_instruction(),
        b'v',
    ]).enumerate() {
        let position = u32::try_from(index).map_err(|error| error.to_string())?;
        *cell = (33u8..=126)
            .find(|byte| {
                decode_profile_instruction(u32::from(*byte), position) == Some(opcode)
            })
            .ok_or_else(|| format!("no source byte for opcode {opcode} at {index}"))?;
    }
    Ok(source)
}

fn verify_generated_binary_io_against_vm(
    profile: &'static ProfileDescriptor,
    source: &[u8],
) -> Result<(), String> {
    let directory = temporary_directory()?;
    let result = (|| {
        let harness = format!(
            "#define EXPECTED_EOF_BYTE {}\n{HARNESS}",
            profile.eof_word().to_le_bytes()[0],
        );
        let executable = compile_generated_program(
            &directory, source, profile.id(), &harness,
        )?;
        let executed = Command::new(&executable)
            .output()
            .map_err(|error| format!("execute generated C: {error}"))?;
        let mut expected_output = Vec::new();
        for input in [vec![0], vec![0x41], vec![0xff], vec![]] {
            let mut machine = ProfileMachine::from_source(
                profile, source, input,
            )
            .map_err(|error| error.to_string())?;
            let outcome = machine.run(8).map_err(|error| error.to_string())?;
            if outcome != (RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 3,
            }) {
                return Err(format!("unexpected normative VM result: {outcome:?}"));
            }
            expected_output.extend_from_slice(machine.output());
        }
        if !executed.status.success()
            || !executed.stderr.is_empty()
            || executed.stdout != expected_output
        {
            return Err(format!(
                "generated C differs from normative VM: {executed:?}, \
                 expected={expected_output:?}",
            ));
        }
        Ok(())
    })();
    let cleanup = fs::remove_dir_all(&directory)
        .map_err(|error| format!("clean generated C fixtures: {error}"));
    result?;
    cleanup
}

#[test]
fn generated_c_matches_historical_vm_and_rejects_output_atomically()
-> Result<(), String> {
    verify_generated_binary_io_against_vm(historical_profile(), SOURCE)
}

#[test]
fn generated_c_matches_current_vm_and_rejects_output_atomically()
-> Result<(), String> {
    // Exercise all three non-EOF byte values and the 15-trit EOF sentinel,
    // alongside the same output-capacity rollback guard as the 1998 profile.
    verify_generated_binary_io_against_vm(current_profile(), SOURCE)
}

#[test]
fn generated_c_versioned_profiles_preserve_binary_io_and_output_refusal()
-> Result<(), String> {
    // Frozen identities include swapped I/O instruction assignments and
    // distinct 10- and 14-trit geometries; derive source from each descriptor.
    for id in ["malbolge-2026.1", "malbolge-2026.2", "malbolge-2026.3"] {
        let profile = target_profile(id)
            .ok_or_else(|| format!("missing immutable profile {id}"))?;
        let source = binary_io_source(profile)?;
        verify_generated_binary_io_against_vm(profile, &source)?;
    }
    Ok(())
}

fn vm_snapshot_bytes(machine: &ProfileMachine) -> Vec<u8> {
    let mut expected = Vec::with_capacity(
        machine.memory().len().saturating_add(3).saturating_mul(4),
    );
    for word in machine.memory().iter().copied().chain([
        machine.registers().accumulator,
        machine.registers().code_pointer,
        machine.registers().data_pointer,
    ]) {
        expected.extend_from_slice(&word.to_le_bytes());
    }
    expected
}

fn require_vm_outcome(
    machine: &ProfileMachine,
    observed: Result<RunOutcome, ProfileMachineError>,
    expected: ExpectedVmOutcome,
    expected_steps: usize,
) -> Result<(), String> {
    match (observed, expected) {
        (
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps,
            }),
            ExpectedVmOutcome::Halt,
        ) if steps == expected_steps => {},
        (
            Ok(RunOutcome::Terminated {
                reason: Termination::NonGraphicalCell,
                steps,
            }),
            ExpectedVmOutcome::NonGraphical,
        ) if steps == expected_steps => {},
        (
            Ok(RunOutcome::BudgetExhausted { steps }),
            ExpectedVmOutcome::BudgetExhausted,
        ) if steps == expected_steps => {},
        (
            Err(ProfileMachineError::InvalidEncryptionTarget {
                pointer: 98, value,
            }),
            ExpectedVmOutcome::InvalidEncryption,
        ) if expected_steps == 0
            && machine.memory().get(98).copied() == Some(value)
            && !(33..=126).contains(&value) => {},
        (
            Err(ProfileMachineError::InvalidEncryptionTarget {
                pointer: 0, value,
            }),
            ExpectedVmOutcome::InvalidWriteEncryption,
        ) if expected_steps == 0
            && machine.memory().first().is_some_and(|raw| *raw != value)
            && !(33..=126).contains(&value) => {},
        (unexpected, _) => {
            return Err(format!("unexpected normative outcome: {unexpected:?}"));
        },
    }
    Ok(())
}

fn verify_generated_state_against_vm(case: GeneratedVmCase<'_>)
-> Result<(), String> {
    let GeneratedVmCase {
        profile, source, harness, expected_outcome, expected_output,
        expected_steps,
    } = case;
    let directory = temporary_directory()?;
    let result = (|| {
        let executable = compile_generated_program(
            &directory, source, profile.id(), harness,
        )?;
        let executed = Command::new(&executable)
            .output()
            .map_err(|error| format!("execute generated C: {error}"))?;
        let mut machine = ProfileMachine::from_source(
            profile, source, Vec::new(),
        )
        .map_err(|error| error.to_string())?;
        let before = (expected_steps == 0).then(|| vm_snapshot_bytes(&machine));
        let outcome = machine.run(expected_steps.max(1));
        require_vm_outcome(&machine, outcome, expected_outcome, expected_steps)?;
        let expected = vm_snapshot_bytes(&machine);
        if before.is_some_and(|snapshot| snapshot != expected) {
            return Err(String::from("normative VM committed a rejected step"));
        }
        if machine.output() != expected_output {
            return Err(format!("unexpected normative output: {:?}", machine.output()));
        }
        if !executed.status.success()
            || !executed.stderr.is_empty()
            || executed.stdout != expected
        {
            return Err(format!(
                "generated C state differs from normative VM: status={} stderr={} actual-bytes={} expected-bytes={}",
                executed.status,
                String::from_utf8_lossy(&executed.stderr),
                executed.stdout.len(), expected.len(),
            ));
        }
        Ok(())
    })();
    let cleanup = fs::remove_dir_all(&directory)
        .map_err(|error| format!("clean generated C fixtures: {error}"));
    result?;
    cleanup
}

#[test]
fn generated_c_arithmetic_memory_and_registers_match_normative_vm()
-> Result<(), String> {
    verify_generated_state_against_vm(GeneratedVmCase {
        expected_outcome: ExpectedVmOutcome::Halt,
        expected_output: &[],
        expected_steps: 4,
        harness: MEMORY_HARNESS,
        profile: historical_profile(),
        source: ARITHMETIC_SOURCE,
    })
}

#[test]
fn generated_c_post_jump_encryption_matches_normative_vm()
-> Result<(), String> {
    let harness = format!(
        "#define EXPECTED_OUTPUT_LEN 1\n#define EXPECTED_OUTPUT_BYTE 0xa8\n{MEMORY_HARNESS}"
    );
    verify_generated_state_against_vm(GeneratedVmCase {
        expected_outcome: ExpectedVmOutcome::Halt,
        expected_output: &[0xa8],
        expected_steps: 4,
        harness: &harness,
        profile: historical_profile(),
        source: JUMP_SOURCE,
    })
}

#[test]
fn generated_c_current_profile_eof_state_matches_normative_vm()
-> Result<(), String> {
    // The 15-trit current profile has a different memory geometry and EOF
    // sentinel from the historical source-compatible machine.
    let profile = current_profile();
    let expected_byte = profile.eof_word().to_le_bytes()[0];
    let harness = format!(
        "#define EXPECTED_OUTPUT_LEN 1\n\
         #define EXPECTED_OUTPUT_BYTE {expected_byte}\n\
         #define EXPECTED_STEPS 3\n\
         #define STEP_BUDGET 3\n{MEMORY_HARNESS}",
    );
    verify_generated_state_against_vm(GeneratedVmCase {
        expected_outcome: ExpectedVmOutcome::Halt,
        expected_output: &[expected_byte],
        expected_steps: 3,
        harness: &harness,
        profile,
        source: SOURCE,
    })
}

#[test]
fn generated_c_invalid_jump_encryption_is_atomic_for_both_profiles()
-> Result<(), String> {
    // `b` decodes to an indirect jump from D=0 to C=98. The generated
    // recurrence gives non-graphical memory[98], so neither backend may
    // encrypt the target or commit the attempted jump.
    let harness = format!(
        "#define EXPECTED_STATUS MB_STATUS_INVALID_ENCRYPTION\n\
         #define EXPECTED_STEPS 0\n\
         #define STEP_BUDGET 1\n{MEMORY_HARNESS}",
    );
    for profile in [historical_profile(), current_profile()] {
        verify_generated_state_against_vm(GeneratedVmCase {
            expected_outcome: ExpectedVmOutcome::InvalidEncryption,
            expected_output: &[],
            expected_steps: 0,
            harness: &harness,
            profile,
            source: INVALID_JUMP_SOURCE,
        })?;
    }
    Ok(())
}

// The first `b` jumps indirectly from C=0 to the source cell at C=98.
// Each later raw byte is a valid initial no-op, so admission succeeds; the
// first generated cell past the 99-byte source is non-graphical at C=99.
fn source_with_non_graphical_jump_successor() -> Result<Vec<u8>, String> {
    let mut source = vec![b'b'];
    for position in 1..=98u32 {
        let raw = (33u8..=126).find(|byte| {
            decode_profile_instruction(u32::from(*byte), position) == Some(b'o')
        })
        .ok_or_else(|| format!("no valid no-op source byte at {position}"))?;
        source.push(raw);
    }
    Ok(source)
}

#[test]
fn generated_c_non_graphical_successor_obeys_selected_profile()
-> Result<(), String> {
    let source = source_with_non_graphical_jump_successor()?;
    for (profile, c_status, expected_outcome) in [
        (historical_profile(), "MB_STATUS_BUDGET_EXHAUSTED", ExpectedVmOutcome::BudgetExhausted),
        (current_profile(), "MB_STATUS_NON_GRAPHICAL", ExpectedVmOutcome::NonGraphical),
    ] {
        let harness = format!(
            "#define EXPECTED_STATUS {c_status}\n\
             #define EXPECTED_STEPS 2\n\
             #define STEP_BUDGET 2\n{MEMORY_HARNESS}",
        );
        verify_generated_state_against_vm(GeneratedVmCase {
            expected_outcome,
            expected_output: &[],
            expected_steps: 2,
            harness: &harness,
            profile,
            source: &source,
        })?;
    }
    Ok(())
}

#[test]
fn generated_c_invalid_code_cell_writes_are_atomic_for_both_profiles()
-> Result<(), String> {
    // The first cell decodes respectively to rotate and crazy. Both would
    // rewrite their own C=0 code cell with a non-graphical value. Neither
    // the value nor the new accumulator may commit on failed encryption.
    let harness = format!(
        "#define EXPECTED_STATUS MB_STATUS_INVALID_ENCRYPTION\n\
         #define EXPECTED_STEPS 0\n\
         #define STEP_BUDGET 1\n{MEMORY_HARNESS}",
    );
    for source in [INVALID_ROTATE_SOURCE, INVALID_CRAZY_SOURCE] {
        for profile in [historical_profile(), current_profile()] {
            verify_generated_state_against_vm(GeneratedVmCase {
                expected_outcome: ExpectedVmOutcome::InvalidWriteEncryption,
                expected_output: &[],
                expected_steps: 0,
                harness: &harness,
                profile,
                source,
            })?;
        }
    }
    Ok(())
}

#[test]
fn generated_c_current_profile_arithmetic_matches_normative_vm()
-> Result<(), String> {
    verify_generated_state_against_vm(GeneratedVmCase {
        expected_outcome: ExpectedVmOutcome::Halt,
        expected_output: &[],
        expected_steps: 4,
        harness: MEMORY_HARNESS,
        profile: current_profile(),
        source: ARITHMETIC_SOURCE,
    })
}

#[test]
fn generated_c_current_profile_post_jump_encryption_matches_normative_vm()
-> Result<(), String> {
    let profile = current_profile();
    let expected_byte = profile.eof_word().to_le_bytes()[0];
    let harness = format!(
        "#define EXPECTED_OUTPUT_LEN 1\n\
         #define EXPECTED_OUTPUT_BYTE {expected_byte}\n{MEMORY_HARNESS}",
    );
    verify_generated_state_against_vm(GeneratedVmCase {
        expected_outcome: ExpectedVmOutcome::Halt,
        expected_output: &[expected_byte],
        expected_steps: 4,
        harness: &harness,
        profile,
        source: JUMP_SOURCE,
    })
}
