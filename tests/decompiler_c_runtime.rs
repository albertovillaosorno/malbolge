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
//   - Covers binary/EOF I/O, halt, atomic refusal, and arithmetic state.
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

use malbolge::{ProfileMachine, RunOutcome, Termination, historical_profile};

const SOURCE: &[u8] = b"ubO";
const ARITHMETIC_SOURCE: &[u8] = b"(&<N";
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
    status = run_case(NULL, 0, 0xa8);
    if (status != 0) { return status; }
    return check_atomic_exhaustion();
}
";

const MEMORY_HARNESS: &str = "
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    uint32_t *memory = calloc(MB_MEMORY_WORDS, sizeof(*memory));
    struct mb_result result;
    size_t index;
    int status;
    if (memory == NULL) { return 30; }
    status = malbolge_decompiled_run(memory, MB_MEMORY_WORDS,
        NULL, 0, NULL, 0, 4, &result);
    if (status != MB_STATUS_HALT || result.status != MB_STATUS_HALT
        || result.steps != 4 || result.output_len != 0
        || result.input_consumed != 0) {
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

fn temporary_directory() -> Result<PathBuf, String> {
    let nonce = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map_err(|error| error.to_string())?
        .as_nanos();
    let directory = temp_dir().join(format!("malbolge-c-runtime-{}-{nonce}", id()));
    fs::create_dir_all(&directory).map_err(|error| error.to_string())?;
    Ok(directory)
}

fn generated_c_stdout(source: &Path) -> Result<Vec<u8>, String> {
    let rendered = Command::new(env!("CARGO_BIN_EXE_malbolge_decompile"))
        .args(["--profile", "malbolge-1998", "--representation", "c"])
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
    harness: &str,
) -> Result<PathBuf, String> {
    let source = directory.join("program.malbolge");
    fs::write(&source, source_bytes).map_err(|error| error.to_string())?;
    let mut c_source = generated_c_stdout(&source)?;
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

#[test]
fn generated_c_matches_historical_vm_and_rejects_output_atomically()
-> Result<(), String> {
    let directory = temporary_directory()?;
    let result = (|| {
        let executable = compile_generated_program(&directory, SOURCE, HARNESS)?;
        let executed = Command::new(&executable)
            .output()
            .map_err(|error| format!("execute generated C: {error}"))?;
        let mut expected_output = Vec::new();
        for input in [vec![0], vec![0x41], vec![0xff], vec![]] {
            let mut machine = ProfileMachine::from_source(
                historical_profile(), SOURCE, input,
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
fn generated_c_arithmetic_memory_and_registers_match_normative_vm()
-> Result<(), String> {
    let directory = temporary_directory()?;
    let result = (|| {
        let executable = compile_generated_program(
            &directory, ARITHMETIC_SOURCE, MEMORY_HARNESS,
        )?;
        let executed = Command::new(&executable)
            .output()
            .map_err(|error| format!("execute generated arithmetic C: {error}"))?;
        let mut machine = ProfileMachine::from_source(
            historical_profile(), ARITHMETIC_SOURCE, Vec::new(),
        )
        .map_err(|error| error.to_string())?;
        let outcome = machine.run(4).map_err(|error| error.to_string())?;
        if outcome != (RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 4,
        }) {
            return Err(format!("arithmetic VM did not halt: {outcome:?}"));
        }
        let mut expected = Vec::with_capacity((machine.memory().len() + 3) * 4);
        for word in machine.memory().iter().copied().chain([
            machine.registers().accumulator,
            machine.registers().code_pointer,
            machine.registers().data_pointer,
        ]) {
            expected.extend_from_slice(&word.to_le_bytes());
        }
        if !executed.status.success()
            || !executed.stderr.is_empty()
            || executed.stdout != expected
        {
            return Err(format!(
                "generated C state differs from normative VM: status={}                  stderr={} actual-bytes={} expected-bytes={}",
                executed.status,
                String::from_utf8_lossy(&executed.stderr),
                executed.stdout.len(), expected.len(),
            ));
        }
        Ok(())
    })();
    let cleanup = fs::remove_dir_all(&directory)
        .map_err(|error| format!("clean arithmetic C fixtures: {error}"));
    result?;
    cleanup
}
