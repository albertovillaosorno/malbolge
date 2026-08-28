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
//   - Product-side trusted initial-halt adaptive-width verification evidence.
// - Must-Not:
//   - Treat research certificates as authority or execute derived geometry.
// - Allows:
//   - Inputs: canonical profiles, exact source bytes, and candidate widths.
//   - Outputs: exact verified-geometry and fail-closed rejection assertions.
//   - Side effects: test-process allocation only.
// - Split-When:
//   - Split when another product proof family gains independent fixtures.
// - Merge-When:
//   - Merge when adaptive width becomes ordinary profile admission evidence.
// - Summary:
//   - Verifies trusted initial-halt geometry admission and source binding.
// - Description:
//   - Covers the QP positive fixture plus width, source, and theorem failures.
// - Usage:
//   - Composed by `tests/vm.rs` under the normal Cargo integration test target.
// - Defaults:
//   - Any unproved or out-of-range case retains no verified geometry.
//

//! Trusted product-side initial-halt adaptive-width verification fixtures.

use malbolge::{
    ProfileLoadError, ProfileMachine, ProfileStepTrace, ProfileWidthProofKind,
    ProfileWidthVerificationError, RegionEffectProgram, RunOutcome,
    StepProgramProjectionError, TargetProfileRequirement, Termination,
    current_profile, decode_profile_instruction, historical_profile,
    verify_initial_halt_profile_width, verify_input_then_halt_profile_width,
    verify_minimum_initial_halt_profile_width,
    verify_minimum_input_then_halt_profile_width,
    verify_minimum_noop_prefix_halt_profile_width,
    verify_noop_prefix_halt_profile_width,
};

use super::{TestResult, check_equal, normalize_result};

const CANONICAL_WORD_TRITS: u8 = 14;
const MINIMUM_WORD_TRITS: u8 = 10;
const MINIMUM_MEMORY_WORDS: u32 = 59_049;
const MINIMUM_MEMORY_WORDS_USIZE: usize = 59_049;
const QP: &[u8] = b"QP";
const CHECKED_GEOMETRIES: [(u8, u32); 5] = [
    (10, 59_049),
    (11, 177_147),
    (12, 531_441),
    (13, 1_594_323),
    (14, 4_782_969),
];

#[test]
fn initial_halt_verifier_binds_profile_source_and_geometry() -> TestResult {
    let current = current_profile();
    let verified = normalize_result(verify_initial_halt_profile_width(
        current,
        QP,
        MINIMUM_WORD_TRITS,
    ))?;
    check_equal(&verified.profile(), &current, "canonical profile binding")?;
    check_equal(&verified.source(), &QP, "exact source binding")?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::InitialHalt,
        "proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "derived word width",
    )?;
    check_equal(
        &verified.memory_words(),
        &MINIMUM_MEMORY_WORDS,
        "derived memory words",
    )?;
    check_equal(
        &verified.word_modulus(),
        &MINIMUM_MEMORY_WORDS,
        "derived modulus",
    )?;
    check_equal(
        &verified.eof_word(),
        &(MINIMUM_MEMORY_WORDS - 1),
        "derived EOF",
    )
}

#[test]
fn derived_width_never_reclassifies_canonical_profile_identity() -> TestResult {
    let current = current_profile();
    let verified = normalize_result(verify_initial_halt_profile_width(
        current,
        QP,
        MINIMUM_WORD_TRITS,
    ))?;
    let requirement =
        TargetProfileRequirement::from_descriptor(verified.profile());
    check_equal(&verified.profile(), &current, "canonical descriptor")?;
    if verified.profile() == historical_profile() {
        return Err(String::from("derived width became historical profile"));
    }
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "derived execution width",
    )?;
    check_equal(
        &requirement.word_trits,
        &CANONICAL_WORD_TRITS,
        "canonical requirement width",
    )
}

#[test]
fn minimum_initial_halt_selector_chooses_narrowest_source_capacity()
-> TestResult {
    let source =
        source_with_initial_halt(MINIMUM_MEMORY_WORDS_USIZE.saturating_add(1))?;
    let verified = normalize_result(
        verify_minimum_initial_halt_profile_width(current_profile(), &source),
    )?;
    check_equal(&verified.word_trits(), &11u8, "minimum admitted width")?;
    check_equal(&verified.memory_words(), &177_147u32, "minimum memory")
}

#[test]
fn minimum_selector_does_not_hide_wider_source_rejection() -> TestResult {
    let invalid_position = MINIMUM_MEMORY_WORDS_USIZE;
    let mut source =
        source_with_initial_halt(invalid_position.saturating_add(1))?;
    let invalid_byte = invalid_instruction_byte(invalid_position)?;
    let slot = source
        .get_mut(invalid_position)
        .ok_or_else(|| String::from("missing adversarial source slot"))?;
    *slot = invalid_byte;
    let Err(error) =
        verify_minimum_initial_halt_profile_width(current_profile(), &source)
    else {
        return Err(String::from("wider invalid source was accepted"));
    };
    check_equal(
        &error,
        &ProfileWidthVerificationError::Source(
            ProfileLoadError::InvalidInstruction {
                position: MINIMUM_MEMORY_WORDS,
                byte: invalid_byte,
            },
        ),
        "wider source validation rejection",
    )
}

#[test]
fn initial_halt_verifier_covers_every_reviewed_geometry() -> TestResult {
    for (word_trits, memory_words) in CHECKED_GEOMETRIES {
        let verified = normalize_result(verify_initial_halt_profile_width(
            current_profile(),
            QP,
            word_trits,
        ))?;
        check_equal(&verified.word_trits(), &word_trits, "checked width")?;
        check_equal(
            &verified.memory_words(),
            &memory_words,
            "checked memory words",
        )?;
        check_equal(
            &verified.profile(),
            &current_profile(),
            "canonical profile identity",
        )?;
    }
    Ok(())
}

#[test]
fn verified_geometry_exposes_copyable_profile_bound_execution_token()
-> TestResult {
    let current = current_profile();
    let verified = normalize_result(verify_initial_halt_profile_width(
        current,
        QP,
        MINIMUM_WORD_TRITS,
    ))?;
    let geometry = verified.geometry();
    let copied = geometry;
    check_equal(&copied.profile(), &current, "token profile binding")?;
    check_equal(
        &copied.word_trits(),
        &MINIMUM_WORD_TRITS,
        "token word width",
    )?;
    check_equal(
        &copied.memory_words(),
        &MINIMUM_MEMORY_WORDS,
        "token memory words",
    )?;
    check_equal(&copied.eof_word(), &(MINIMUM_MEMORY_WORDS - 1), "token EOF")
}

#[test]
fn input_then_halt_verifier_executes_byte_and_eof_at_minimum_width()
-> TestResult {
    let verified = normalize_result(
        verify_minimum_input_then_halt_profile_width(current_profile(), b"uP"),
    )?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::InputThenHaltProjection,
        "input-halt proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "input-halt minimum width",
    )?;
    let cases = [
        (vec![0xa5], 0xa5u32, 1usize),
        (Vec::new(), verified.eof_word(), 0usize),
    ];
    for (input, accumulator, consumed) in cases {
        let mut machine = normalize_result(
            ProfileMachine::from_verified_source(&verified, input),
        )?;
        check_equal(
            &normalize_result(machine.run(2))?,
            &RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 2,
            },
            "input-halt outcome",
        )?;
        check_equal(
            &machine.registers().accumulator,
            &accumulator,
            "input-halt accumulator",
        )?;
        check_equal(
            &machine.input_consumed(),
            &consumed,
            "input-halt consumed input",
        )?;
        let expected_output: &[u8] = &[];
        check_equal(&machine.output(), &expected_output, "input-halt output")?;
        check_equal(
            &machine.geometry(),
            &verified.geometry(),
            "input-halt geometry",
        )?;
    }
    Ok(())
}

#[test]
fn input_then_halt_verifier_rejects_wrong_reached_sequence() -> TestResult {
    let wrong_first = verify_input_then_halt_profile_width(
        current_profile(),
        b"DP",
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &wrong_first,
        &Err(ProfileWidthVerificationError::InputThenHaltInstruction {
            position: 0,
            decoded: b'o',
        }),
        "input-halt first instruction rejection",
    )?;
    let wrong_second = verify_input_then_halt_profile_width(
        current_profile(),
        b"ub",
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &wrong_second,
        &Err(ProfileWidthVerificationError::InputThenHaltInstruction {
            position: 1,
            decoded: b'<',
        }),
        "input-halt second instruction rejection",
    )
}

#[test]
fn noop_prefix_halt_verifier_executes_dp_at_minimum_width() -> TestResult {
    let verified = normalize_result(
        verify_minimum_noop_prefix_halt_profile_width(current_profile(), b"DP"),
    )?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::NoopPrefixHalt,
        "no-op proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "no-op minimum width",
    )?;
    let mut machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    check_equal(
        &machine.memory().len(),
        &MINIMUM_MEMORY_WORDS_USIZE,
        "no-op derived memory length",
    )?;
    check_equal(
        &normalize_result(machine.run(2))?,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 2,
        },
        "no-op derived halt outcome",
    )
}

#[test]
fn noop_prefix_halt_verifier_rejects_empty_prefix_and_missing_halt()
-> TestResult {
    let empty_prefix = verify_noop_prefix_halt_profile_width(
        current_profile(),
        QP,
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &empty_prefix,
        &Err(ProfileWidthVerificationError::NoopPrefixInstruction {
            position: 0,
            decoded: b'v',
        }),
        "empty no-op prefix rejection",
    )?;
    let missing_halt = verify_noop_prefix_halt_profile_width(
        current_profile(),
        b"DC",
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &missing_halt,
        &Err(ProfileWidthVerificationError::NoopPrefixMissingHalt),
        "missing no-op prefix halt rejection",
    )
}

#[test]
fn derived_trace_cannot_claim_canonical_portable_ir_geometry() -> TestResult {
    let verified = normalize_result(
        verify_minimum_initial_halt_profile_width(current_profile(), QP),
    )?;
    let mut machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    let mut trace_record = None;
    let _outcome = normalize_result(machine.step_traced(
        &mut |trace: &ProfileStepTrace| {
            trace_record = Some(*trace);
        },
    ))?;
    let trace =
        trace_record.ok_or_else(|| String::from("derived trace missing"))?;
    check_equal(&trace.geometry, &verified.geometry(), "trace geometry")?;
    check_equal(
        &RegionEffectProgram::from_profile_step_trace(&trace),
        &Err(StepProgramProjectionError::ExecutionGeometry),
        "derived portable IR rejection",
    )
}

#[test]
fn verified_initial_halt_executes_only_derived_memory_geometry() -> TestResult {
    let current = current_profile();
    let verified = normalize_result(
        verify_minimum_initial_halt_profile_width(current, QP),
    )?;
    let mut machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    check_equal(&machine.profile(), &current, "machine canonical profile")?;
    check_equal(
        &machine.geometry(),
        &verified.geometry(),
        "machine verified geometry",
    )?;
    check_equal(
        &machine.memory().len(),
        &MINIMUM_MEMORY_WORDS_USIZE,
        "derived resident memory length",
    )?;
    let outcome = normalize_result(machine.run(1))?;
    check_equal(
        &outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 1,
        },
        "derived initial halt outcome",
    )?;
    let checkpoint = machine.snapshot_state();
    check_equal(
        &checkpoint.geometry(),
        &verified.geometry(),
        "checkpoint verified geometry",
    )?;
    let restored = ProfileMachine::from_snapshot(checkpoint);
    check_equal(
        &restored.geometry(),
        &verified.geometry(),
        "restored verified geometry",
    )?;
    check_equal(
        &restored.memory().len(),
        &MINIMUM_MEMORY_WORDS_USIZE,
        "restored derived memory length",
    )
}

#[test]
fn initial_halt_verifier_preserves_raw_source_identity() -> TestResult {
    let source = b" \tQP\n";
    let verified = normalize_result(verify_initial_halt_profile_width(
        current_profile(),
        source,
        MINIMUM_WORD_TRITS,
    ))?;
    check_equal(&verified.source(), &source.as_slice(), "raw source bytes")
}

#[test]
fn initial_halt_verifier_rejects_unreviewed_widths() -> TestResult {
    for requested in [MINIMUM_WORD_TRITS - 1, CANONICAL_WORD_TRITS + 1] {
        let Err(error) =
            verify_initial_halt_profile_width(current_profile(), QP, requested)
        else {
            return Err(format!("unreviewed width {requested} was accepted"));
        };
        check_equal(
            &error,
            &ProfileWidthVerificationError::WidthOutOfRange {
                profile_word_trits: CANONICAL_WORD_TRITS,
                requested,
            },
            "width rejection",
        )?;
    }
    Ok(())
}

#[test]
fn initial_halt_verifier_reuses_exact_profile_source_admission() -> TestResult {
    let invalid = [0x01, b'P'];
    let Err(error) = verify_initial_halt_profile_width(
        current_profile(),
        &invalid,
        MINIMUM_WORD_TRITS,
    ) else {
        return Err(String::from("invalid source byte was accepted"));
    };
    check_equal(
        &error,
        &ProfileWidthVerificationError::Source(
            ProfileLoadError::InvalidSourceByte { offset: 0, byte: 0x01 },
        ),
        "source admission rejection",
    )
}

#[test]
fn initial_halt_verifier_rejects_other_valid_source_families() -> TestResult {
    let Err(error) = verify_initial_halt_profile_width(
        current_profile(),
        b"DP",
        MINIMUM_WORD_TRITS,
    ) else {
        return Err(String::from("non-initial-halt source was accepted"));
    };
    check_equal(
        &error,
        &ProfileWidthVerificationError::InitialInstructionNotHalt {
            decoded: b'o',
        },
        "proof-family rejection",
    )
}

#[test]
fn derived_capacity_precedes_later_source_validation() -> TestResult {
    let oversized = vec![b'Q'; MINIMUM_MEMORY_WORDS_USIZE.saturating_add(1)];
    let Err(error) = verify_initial_halt_profile_width(
        current_profile(),
        &oversized,
        MINIMUM_WORD_TRITS,
    ) else {
        return Err(String::from("source beyond derived memory was accepted"));
    };
    check_equal(
        &error,
        &ProfileWidthVerificationError::Source(ProfileLoadError::SourceTooLong),
        "derived capacity rejection",
    )
}

fn source_with_initial_halt(word_count: usize) -> TestResult<Vec<u8>> {
    let mut source = Vec::with_capacity(word_count);
    for position in 0..word_count {
        let code_pointer = u32::try_from(position).map_err(|error| {
            format!("test code pointer conversion: {error}")
        })?;
        let decoded = if position == 0 {
            b'v'
        } else {
            b'o'
        };
        let byte = (33u8..=126u8)
            .find(|cell| {
                decode_profile_instruction(u32::from(*cell), code_pointer)
                    == Some(decoded)
            })
            .ok_or_else(|| {
                format!("missing encoded opcode at position {position}")
            })?;
        source.push(byte);
    }
    Ok(source)
}

fn invalid_instruction_byte(position: usize) -> TestResult<u8> {
    let code_pointer = u32::try_from(position)
        .map_err(|error| format!("invalid-byte pointer conversion: {error}"))?;
    (33u8..=126u8)
        .find(|cell| {
            let decoded =
                decode_profile_instruction(u32::from(*cell), code_pointer);
            !matches!(
                decoded,
                Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
            )
        })
        .ok_or_else(|| format!("missing invalid instruction at {position}"))
}
