// File:
//   - decompiler.rs
// Path:
//   - tests/decompiler.rs
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
//   - Determinism, profile binding, source validation, and C-rendering
//     fixtures.
// - Must-Not:
//   - Depend on historical third-party program bytes.
// - Allows:
//   - Inputs: project-owned synthetic Malbolge fixtures and canonical profiles.
//   - Outputs: assertions over generated C source.
//   - Side effects: test-process allocation only.
// - Split-When:
//   - Split when executable C differential tests need independent toolchain
//     setup.
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
// Related documents:
// - tools/decompile/README.md
//
// Large file:
//   - false

//! Product Malbolge decompiler conformance.

#[path = "../tools/decompile/render.rs"]
pub mod decompiler;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, current_profile,
    historical_profile,
};

const OUTPUT_SOURCE: &[u8] = b"ctO";

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
    {
        Ok(())
    } else {
        Err(String::from("historical C geometry is missing"))
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
fn initial_listing_uses_normative_translation_table() -> Result<(), String> {
    let rendered = decompiler::render_c(historical_profile(), OUTPUT_SOURCE)
        .map_err(|error| error.to_string())?;
    for expected in [
        "0:  99 -> <  input byte into A",
        "1: 116 -> /  output low byte of A",
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
