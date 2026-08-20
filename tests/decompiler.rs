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
//   - Determinism, profile binding, source validation, and C-rendering
//   - fixtures.
// - Must-Not:
//   - Depend on historical third-party program bytes.
// - Allows:
//   - Inputs: project-owned synthetic Malbolge fixtures and canonical profiles.
//   - Outputs: assertions over generated C source.
//   - Side effects: test-process allocation only.
// - Split-When:
//   - Split when executable C differential tests need independent toolchain
//   - setup.
// - Merge-When:
//   - Merge when decompiler verification gains a unified product test suite.
// - Summary:
//   - Proves the general C renderer is deterministic and profile-explicit.
// - Description:
//   - Uses only project-owned tiny sources already present in VM conformance.
// - Usage:
//   - Auto-discovered by Cargo test.
// - Defaults:
//   - No museum specimen is embedded in tests.
//

//! Product Malbolge decompiler conformance.

#[path = "../src/tooling/decompiler/domain/analysis.rs"]
pub mod analysis;
#[path = "../src/tooling/decompiler/application/render.rs"]
pub mod decompiler;

use std::process::Command;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, current_profile,
    historical_profile,
};

const ANALYSIS_SOURCE: &[u8] = b"b&&;@L";
const OUTPUT_SOURCE: &[u8] = b"ubO";

type DuplicateCliCase = (&'static [&'static str], &'static str);

#[test]
fn cli_rejects_duplicate_semantic_options() -> Result<(), String> {
    let cases: [DuplicateCliCase; 3] = [
        (&["--profile", "a", "--profile", "b"], "duplicate --profile"),
        (
            &["--representation", "c", "--representation", "c"],
            "duplicate --representation",
        ),
        (&["--output", "a", "-o", "b"], "duplicate --output"),
    ];
    for (arguments, expected) in cases {
        let output = Command::new(env!("CARGO_BIN_EXE_malbolge_decompile"))
            .args(arguments)
            .output()
            .map_err(|error| format!("run decompiler CLI: {error}"))?;
        if output.status.success() {
            return Err(format!(
                "duplicate CLI option unexpectedly succeeded: {arguments:?}"
            ));
        }
        let stderr = String::from_utf8_lossy(&output.stderr);
        if !stderr.contains(expected) {
            return Err(format!(
                "duplicate CLI diagnostic missing {expected:?}: {stderr}"
            ));
        }
    }
    Ok(())
}

#[test]
fn cli_help_is_exclusive() -> Result<(), String> {
    let help = Command::new(env!("CARGO_BIN_EXE_malbolge_decompile"))
        .arg("--help")
        .output()
        .map_err(|error| format!("run decompiler help: {error}"))?;
    if !help.status.success()
        || !String::from_utf8_lossy(&help.stdout).contains("usage:")
    {
        return Err(String::from("standalone help did not succeed"));
    }
    for arguments in [["--help", "--unknown"], ["--profile", "--help"], [
        "-h",
        "input.malbolge",
    ]] {
        let output = Command::new(env!("CARGO_BIN_EXE_malbolge_decompile"))
            .args(arguments)
            .output()
            .map_err(|error| format!("run combined help: {error}"))?;
        let stderr = String::from_utf8_lossy(&output.stderr);
        if output.status.success()
            || !stderr.contains("--help cannot be combined")
        {
            return Err(format!(
                "combined help did not fail closed: {arguments:?}: {stderr}"
            ));
        }
    }
    Ok(())
}

#[test]
fn c_render_is_deterministic_and_profile_bound() -> Result<(), String> {
    let first = decompiler::render_c(current_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    let second = decompiler::render_c(current_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    if first != second {
        return Err(String::from("decompiler output is not deterministic"));
    }
    if !first.contains(current_profile().fingerprint())
        || !first.contains("#define MB_WORD_TRITS UINT32_C(14)")
        || !first.contains("#define MB_INPUT_INSTRUCTION UINT32_C(47)")
        || !first.contains("#define MB_OUTPUT_INSTRUCTION UINT32_C(60)")
        || !first.contains("#define MB_NON_GRAPHICAL_NO_PROGRESS 0")
        || !first.contains("uint32_t *memory")
        || first.contains("malloc(")
    {
        return Err(String::from("current-profile C metadata is incomplete"));
    }
    Ok(())
}

#[test]
fn c_render_distinguishes_historical_geometry() -> Result<(), String> {
    let current = decompiler::render_c(current_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    let historical = decompiler::render_c(historical_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    if current == historical {
        return Err(String::from("profile change did not change generated C"));
    }
    if historical.contains("#define MB_WORD_TRITS UINT32_C(10)")
        && historical.contains("#define MB_MEMORY_WORDS UINT32_C(59049)")
        && historical.contains("#define MB_INPUT_INSTRUCTION UINT32_C(47)")
        && historical.contains("#define MB_OUTPUT_INSTRUCTION UINT32_C(60)")
        && historical.contains("#define MB_NON_GRAPHICAL_NO_PROGRESS 1")
    {
        Ok(())
    } else {
        Err(String::from("historical C geometry is missing"))
    }
}

#[test]
fn c_render_ignores_vertical_tab_source_whitespace() -> Result<(), String> {
    let plain = decompiler::render_c(historical_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    let spaced =
        decompiler::render_c(historical_profile(), &[b'u', 0x0b, b'b', b'O'])
            .map_err(|error| error.to_string())?;
    if plain == spaced {
        Ok(())
    } else {
        Err(String::from("vertical tab changed generated C"))
    }
}

#[test]
fn c_render_rejects_invalid_source() {
    let observed = decompiler::render_c(historical_profile(), b"not malbolge");
    assert!(observed.is_err(), "invalid source unexpectedly decompiled");
}

#[test]
fn c_render_contains_atomic_post_jump_encryption_logic() -> Result<(), String> {
    let rendered = decompiler::render_c(historical_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    let jump = rendered
        .find("next_code_pointer = memory[data_pointer];")
        .ok_or_else(|| String::from("jump lowering missing"))?;
    let target = rendered
        .find("encryption_target = writes_memory")
        .ok_or_else(|| String::from("encryption target lowering missing"))?;
    let commit = rendered
        .find("memory[next_code_pointer] = encrypted;")
        .ok_or_else(|| String::from("encryption commit missing"))?;
    if jump < target && target < commit {
        Ok(())
    } else {
        Err(String::from("post-jump encryption ordering is wrong"))
    }
}

#[test]
fn c_render_checks_output_capacity_at_emission() -> Result<(), String> {
    let rendered = decompiler::render_c(current_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    if rendered.contains("output_capacity < step_budget")
        || rendered.contains("step_budget != 0 && output == NULL")
    {
        return Err(String::from(
            "generated C retains budget-sized output precondition",
        ));
    }
    let capacity = rendered
        .find("if (emits_output && output_len >= output_capacity)")
        .ok_or_else(|| String::from("dynamic output capacity check missing"))?;
    let commit = rendered
        .find("memory[next_code_pointer] = encrypted;")
        .ok_or_else(|| String::from("encryption commit missing"))?;
    if rendered.contains("MB_STATUS_OUTPUT_EXHAUSTED = 5")
        && rendered.contains("output_capacity != 0 && output == NULL")
        && capacity < commit
    {
        Ok(())
    } else {
        Err(String::from(
            "output capacity rejection is not explicit and atomic",
        ))
    }
}

#[test]
fn initial_listing_uses_normative_translation_table() -> Result<(), String> {
    let rendered = decompiler::render_c(historical_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    for expected in [
        "0: 117 -> /  input byte into A",
        "1:  98 -> <  output low byte of A",
        "2:  79 -> v  halt",
    ] {
        if !rendered.contains(expected) {
            return Err(format!(
                "missing translated listing entry: {expected}"
            ));
        }
    }
    Ok(())
}

#[test]
fn synthetic_roundtrip_fixture_matches_normative_vm() -> Result<(), String> {
    let mut machine =
        ProfileMachine::from_source(historical_profile(), OUTPUT_SOURCE, vec![
            0x41,
        ])
        .map_err(|error| error.to_string())?;
    let outcome = machine.run(8).map_err(|error| error.to_string())?;
    if outcome
        != (RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 3,
        })
        || machine.output() != b"A"
        || machine.input_consumed() != 1
    {
        return Err(String::from("synthetic roundtrip VM baseline changed"));
    }
    Ok(())
}

#[test]
fn analysis_report_classifies_initial_state_without_guessing()
-> Result<(), String> {
    let rendered =
        decompiler::render_analysis(historical_profile(), ANALYSIS_SOURCE)
            .map_err(|error| error.to_string())?;
    for expected in [
        "profile_id=malbolge-1998",
        "indirect-targets=unresolved",
        concat!(
            "cell position=0 raw=98 decoded=i ",
            "control=indirect-code-pointer-from-data data=read-data-cell ",
            "accumulator=none post_step_encryption=yes"
        ),
        concat!(
            "cell position=1 raw=38 decoded=* control=sequential ",
            "data=read-write-data-cell accumulator=write ",
            "post_step_encryption=yes"
        ),
        concat!(
            "cell position=5 raw=76 decoded=v control=halt data=none ",
            "accumulator=none post_step_encryption=no"
        ),
    ] {
        if !rendered.contains(expected) {
            return Err(format!("analysis report missing: {expected}"));
        }
    }
    Ok(())
}

#[test]
fn cli_emits_analysis_representation() -> Result<(), String> {
    let source = concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/tests/compatibility/specification/interpreter-io-roundtrip.malbolge"
    );
    let output = Command::new(env!("CARGO_BIN_EXE_malbolge_decompile"))
        .args([
            "--profile",
            "malbolge-1998",
            "--representation",
            "analysis",
            source,
        ])
        .output()
        .map_err(|error| format!("run analysis CLI: {error}"))?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    if !output.status.success()
        || !stdout.contains("Malbolge initial-state analysis")
        || !stdout.contains("profile_id=malbolge-1998")
        || !stdout.contains("decoded=/")
        || !stdout.contains("decoded=<")
        || !stdout.contains("decoded=v")
    {
        return Err(format!(
            "analysis CLI did not emit expected report: {stdout}"
        ));
    }
    Ok(())
}
