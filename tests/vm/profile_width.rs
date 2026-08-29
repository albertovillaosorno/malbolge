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
    ProfileLoadError, ProfileMachine, ProfileMachineError,
    ProfileMachineIoState, ProfileMachineState, ProfileStepTrace,
    ProfileWidthProofKind, ProfileWidthVerificationError, RegionEffectProgram,
    RunOutcome, StepProgramProjectionError, TargetProfileRequirement,
    Termination, current_profile, decode_profile_instruction,
    historical_profile, profile_crazy, select_minimum_verified_profile_width,
    verify_initial_halt_profile_width, verify_input_output_halt_profile_width,
    verify_input_then_halt_profile_width, verify_jump_code_halt_profile_width,
    verify_jump_code_io_halt_profile_width,
    verify_jump_code_rotate_halt_profile_width,
    verify_jump_crazy_halt_profile_width,
    verify_jump_crazy_io_halt_profile_width,
    verify_jump_data_halt_profile_width,
    verify_jump_rotate_crazy_halt_profile_width,
    verify_jump_rotate_halt_profile_width,
    verify_jump_rotate_io_halt_profile_width,
    verify_minimum_initial_halt_profile_width,
    verify_minimum_input_output_halt_profile_width,
    verify_minimum_input_then_halt_profile_width,
    verify_minimum_jump_code_halt_profile_width,
    verify_minimum_jump_code_io_halt_profile_width,
    verify_minimum_jump_code_rotate_halt_profile_width,
    verify_minimum_jump_crazy_halt_profile_width,
    verify_minimum_jump_crazy_io_halt_profile_width,
    verify_minimum_jump_data_halt_profile_width,
    verify_minimum_jump_rotate_crazy_halt_profile_width,
    verify_minimum_jump_rotate_halt_profile_width,
    verify_minimum_jump_rotate_io_halt_profile_width,
    verify_minimum_noop_prefix_halt_profile_width,
    verify_minimum_repeated_jump_data_profile_width,
    verify_minimum_straight_line_io_profile_width,
    verify_noop_prefix_halt_profile_width,
    verify_repeated_jump_data_profile_width,
    verify_straight_line_io_profile_width,
};

use super::{TestResult, check_equal, normalize_result};

const CANONICAL_WORD_TRITS: u8 = 15;
const MINIMUM_WORD_TRITS: u8 = 10;
const MINIMUM_MEMORY_WORDS: u32 = 59_049;
const MINIMUM_MEMORY_WORDS_USIZE: usize = 59_049;
const QP: &[u8] = b"QP";
const JUMP_ROTATE_SAFE: &[u8] = b"(&O";
const JUMP_ROTATE_UNSAFE: &[u8] = b"(CB$M";
const JUMP_ROTATE_CRAZY_SAFE: &[u8] = b"(&<;:9K";
const JUMP_ROTATE_CRAZY_UNSAFE: &[u8] = b"(C%;M";
const JUMP_ROTATE_IO_SAFE: &[u8] = b"(CB$q^K";
const JUMP_ROTATE_IO_TWO_PAIRS: &[u8] = b"(CB$q^o\\I";
const JUMP_ROTATE_IO_FOUR_PAIRS: &[u8] = b"(CB$q^o\\mZkXE";
const JUMP_ROTATE_IO_UNSAFE: &[u8] = b"(&s`M";
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
fn input_output_halt_verifier_binds_nonempty_runtime_input() -> TestResult {
    let verified =
        normalize_result(verify_minimum_input_output_halt_profile_width(
            current_profile(),
            b"ubO",
        ))?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::InputOutputHaltProjection,
        "input-output proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "input-output minimum width",
    )?;
    for input in [vec![0xa5], vec![0x00, 0xff]] {
        let expected = input.first().copied().ok_or_else(|| {
            String::from("nonempty input fixture became empty")
        })?;
        let mut machine = normalize_result(
            ProfileMachine::from_verified_source(&verified, input),
        )?;
        check_equal(
            &normalize_result(machine.run(3))?,
            &RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 3,
            },
            "input-output halt outcome",
        )?;
        check_equal(
            &machine.output(),
            &vec![expected].as_slice(),
            "input-output emitted byte",
        )?;
        check_equal(
            &machine.input_consumed(),
            &1usize,
            "input-output consumed input",
        )?;
    }
    let empty = ProfileMachine::from_verified_source(&verified, Vec::new());
    if !matches!(empty, Err(ProfileMachineError::VerifiedInputRejected)) {
        return Err(String::from("input-output proof admitted EOF input"));
    }
    Ok(())
}

#[test]
fn input_output_halt_policy_survives_geometry_checkpoint_api() -> TestResult {
    let verified = normalize_result(verify_input_output_halt_profile_width(
        current_profile(),
        b"ubO",
        MINIMUM_WORD_TRITS,
    ))?;
    let machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        vec![0xa5],
    ))?;
    let snapshot = machine.snapshot_state();
    let empty_io = normalize_result(ProfileMachineIoState::new(
        Vec::new(),
        0,
        Vec::new(),
        None,
    ))?;
    let rebuilt = ProfileMachineState::new_with_geometry(
        verified.geometry(),
        snapshot.memory().to_vec(),
        snapshot.registers(),
        empty_io,
    );
    if matches!(rebuilt, Err(ProfileMachineError::VerifiedInputRejected)) {
        Ok(())
    } else {
        Err(String::from("checkpoint stripped verified input policy"))
    }
}

#[test]
fn input_output_halt_verifier_rejects_wrong_reached_sequence() -> TestResult {
    let observed = verify_input_output_halt_profile_width(
        current_profile(),
        b"uP",
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &observed,
        &Err(ProfileWidthVerificationError::InputOutputHaltInstruction {
            position: 1,
            decoded: b'v',
        }),
        "input-output sequence rejection",
    )
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
fn jump_crazy_halt_verifier_executes_guarded_projection_at_minimum_width()
-> TestResult {
    let verified = normalize_result(
        verify_minimum_jump_crazy_halt_profile_width(current_profile(), b"(=O"),
    )?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::JumpCrazyHaltProjection,
        "jump-crazy proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "jump-crazy minimum width",
    )?;
    let mut machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    check_equal(
        &normalize_result(machine.run(3))?,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 3,
        },
        "jump-crazy halt outcome",
    )
}

#[test]
fn jump_crazy_halt_verifier_tracks_multiple_projected_accumulators()
-> TestResult {
    let verified =
        normalize_result(verify_minimum_jump_crazy_halt_profile_width(
            current_profile(),
            b"(=<N",
        ))?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "multi-crazy minimum width",
    )?;
    let mut machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    check_equal(
        &normalize_result(machine.run(4))?,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 4,
        },
        "multi-crazy halt outcome",
    )
}

#[test]
fn jump_crazy_io_verifier_recovers_exact_byte_after_crazy_prefix() -> TestResult
{
    let cases = [
        (b"(=s`M".as_slice(), 5usize),
        (b"(=<r_L".as_slice(), 6usize),
    ];
    for (source, steps) in cases {
        let verified =
            normalize_result(verify_minimum_jump_crazy_io_halt_profile_width(
                current_profile(),
                source,
            ))?;
        check_equal(
            &verified.proof_kind(),
            &ProfileWidthProofKind::JumpCrazyIoHaltProjection,
            "jump-crazy I/O proof family",
        )?;
        let mut machine = normalize_result(
            ProfileMachine::from_verified_source(&verified, vec![0xa5]),
        )?;
        check_equal(
            &normalize_result(machine.run(steps))?,
            &RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps,
            },
            "jump-crazy I/O outcome",
        )?;
        check_equal(&machine.output(), &(&[0xa5][..]), "recovered output")?;
        if !matches!(
            ProfileMachine::from_verified_source(&verified, Vec::new()),
            Err(ProfileMachineError::VerifiedInputRejected)
        ) {
            return Err(String::from("jump-crazy I/O proof admitted EOF"));
        }
    }
    Ok(())
}

#[test]
fn jump_crazy_io_verifier_covers_every_reviewed_geometry() -> TestResult {
    for (word_trits, memory_words) in CHECKED_GEOMETRIES {
        let verified =
            normalize_result(verify_jump_crazy_io_halt_profile_width(
                current_profile(),
                b"(=s`M",
                word_trits,
            ))?;
        check_equal(&verified.word_trits(), &word_trits, "recovery width")?;
        check_equal(
            &verified.memory_words(),
            &memory_words,
            "recovery memory words",
        )?;
        check_equal(
            &verified.proof_kind(),
            &ProfileWidthProofKind::JumpCrazyIoHaltProjection,
            "recovery proof family",
        )?;
    }
    Ok(())
}

#[test]
fn jump_crazy_io_verifier_rejects_output_before_input_recovery() -> TestResult {
    let observed = verify_jump_crazy_io_halt_profile_width(
        current_profile(),
        b"(=O",
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &observed,
        &Err(ProfileWidthVerificationError::JumpCrazyHaltInstruction {
            position: 2,
            decoded: b'v',
        }),
        "missing input recovery rejection",
    )
}

#[test]
fn jump_crazy_halt_verifier_rejects_unguarded_crazy() -> TestResult {
    let observed = verify_jump_crazy_halt_profile_width(
        current_profile(),
        b">P",
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &observed,
        &Err(ProfileWidthVerificationError::JumpCrazyHaltInstruction {
            position: 0,
            decoded: b'p',
        }),
        "unguarded crazy rejection",
    )
}

#[test]
fn jump_data_halt_verifier_executes_exact_low_address_at_minimum_width()
-> TestResult {
    let verified = normalize_result(
        verify_minimum_jump_data_halt_profile_width(current_profile(), b"(P"),
    )?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::JumpDataHaltProjection,
        "jump-data proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "jump-data minimum width",
    )?;
    let mut machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    check_equal(
        &normalize_result(machine.run(2))?,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 2,
        },
        "jump-data halt outcome",
    )?;
    check_equal(
        &machine.registers().data_pointer,
        &41u32,
        "jump-data exact successor",
    )?;
    check_equal(
        &machine.registers().code_pointer,
        &1u32,
        "jump-data halt pointer",
    )
}

#[test]
fn jump_data_halt_verifier_rejects_wrong_reached_sequence() -> TestResult {
    let wrong_first = verify_jump_data_halt_profile_width(
        current_profile(),
        QP,
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &wrong_first,
        &Err(ProfileWidthVerificationError::JumpDataHaltInstruction {
            position: 0,
            decoded: b'v',
        }),
        "jump-data first instruction rejection",
    )?;
    let wrong_second = verify_jump_data_halt_profile_width(
        current_profile(),
        b"(=",
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &wrong_second,
        &Err(ProfileWidthVerificationError::JumpDataHaltInstruction {
            position: 1,
            decoded: b'p',
        }),
        "jump-data second instruction rejection",
    )
}

fn encoded_profile_instruction(decoded: u8, position: usize) -> TestResult<u8> {
    let pointer = u32::try_from(position)
        .map_err(|error| format!("profile instruction position: {error}"))?;
    (33u8..=126u8)
        .find(|cell| {
            decode_profile_instruction(u32::from(*cell), pointer)
                == Some(decoded)
        })
        .ok_or_else(|| format!("missing encoded {decoded} at {position}"))
}

fn admit_jump_code_every_reviewed_width(source: &[u8]) -> TestResult {
    for (word_trits, _memory_words) in CHECKED_GEOMETRIES {
        let _admitted = normalize_result(verify_jump_code_halt_profile_width(
            current_profile(),
            source,
            word_trits,
        ))?;
    }
    Ok(())
}

fn source_with_source_backed_jump_code_halt() -> TestResult<Vec<u8>> {
    let first = encoded_profile_instruction(b'i', 0)?;
    let encryption_target = usize::from(first);
    let halt_position = encryption_target.saturating_add(1);
    let mut source = Vec::with_capacity(halt_position.saturating_add(1));
    for position in 0..=halt_position {
        let decoded = if position == 0 {
            b'i'
        } else if position == halt_position {
            b'v'
        } else {
            b'o'
        };
        source.push(encoded_profile_instruction(decoded, position)?);
    }
    Ok(source)
}

fn source_with_two_source_backed_jump_codes() -> TestResult<Vec<u8>> {
    let first_target = encoded_profile_instruction(b'i', 0)?;
    let second_target = encoded_profile_instruction(b'j', 1)?;
    let second_jump = usize::from(first_target).saturating_add(1);
    let halt_position = usize::from(second_target).saturating_add(1);
    let source_len = second_jump.saturating_add(1);
    let mut source = Vec::with_capacity(source_len);
    for position in 0..source_len {
        source.push(encoded_profile_instruction(b'o', position)?);
    }
    let first = source
        .get_mut(0)
        .ok_or_else(|| String::from("missing first jump-code source cell"))?;
    *first = first_target;
    let second_data = source
        .get_mut(1)
        .ok_or_else(|| String::from("missing second jump-code data cell"))?;
    *second_data = second_target;
    let second_code = source
        .get_mut(second_jump)
        .ok_or_else(|| String::from("missing second jump-code instruction"))?;
    *second_code = encoded_profile_instruction(b'i', second_jump)?;
    let halt = source
        .get_mut(halt_position)
        .ok_or_else(|| String::from("missing repeated jump-code halt"))?;
    *halt = encoded_profile_instruction(b'v', halt_position)?;
    Ok(source)
}

fn source_with_shadow_dependent_jump_codes() -> TestResult<Vec<u8>> {
    let first_target = encoded_profile_instruction(b'i', 0)?;
    let mutated_target = encoded_profile_instruction(b'*', 1)?;
    let return_target = encoded_profile_instruction(b'*', 2)?;
    let halt_target = encoded_profile_instruction(b'v', 3)?;
    let second_jump = usize::from(first_target).saturating_add(1);
    let third_jump = usize::from(mutated_target).saturating_add(1);
    let mutated_jump = usize::from(return_target).saturating_add(1);
    let halt_position = usize::from(halt_target).saturating_add(1);
    let source_len = second_jump.saturating_add(1);
    let mut source = Vec::with_capacity(source_len);
    for position in 0..source_len {
        source.push(encoded_profile_instruction(b'o', position)?);
    }
    for (position, value) in [
        (0usize, first_target),
        (1usize, mutated_target),
        (2usize, return_target),
        (3usize, halt_target),
        (
            mutated_jump,
            encoded_profile_instruction(b'j', mutated_jump)?,
        ),
        (third_jump, encoded_profile_instruction(b'i', third_jump)?),
        (
            halt_position,
            encoded_profile_instruction(b'v', halt_position)?,
        ),
        (second_jump, encoded_profile_instruction(b'i', second_jump)?),
    ] {
        let cell = source.get_mut(position).ok_or_else(|| {
            format!("missing shadow jump-code cell {position}")
        })?;
        *cell = value;
    }
    Ok(source)
}

fn source_with_shadow_jump_code_io() -> TestResult<Vec<u8>> {
    let mut source = source_with_shadow_dependent_jump_codes()?;
    let profile = current_profile();
    for (position, decoded) in [
        (79usize, profile.input_instruction()),
        (80usize, profile.output_instruction()),
        (81usize, b'v'),
    ] {
        let cell = source
            .get_mut(position)
            .ok_or_else(|| format!("missing jump-code I/O cell {position}"))?;
        *cell = encoded_profile_instruction(decoded, position)?;
    }
    Ok(source)
}

fn source_with_shadow_jump_code_rotate(
    data_instruction: u8,
) -> TestResult<Vec<u8>> {
    let mut source = source_with_shadow_dependent_jump_codes()?;
    for (position, decoded) in
        [(4usize, data_instruction), (79usize, b'*'), (80usize, b'v')]
    {
        let cell = source.get_mut(position).ok_or_else(|| {
            format!("missing jump-code rotate cell {position}")
        })?;
        *cell = encoded_profile_instruction(decoded, position)?;
    }
    Ok(source)
}

fn source_with_two_shadow_jump_code_io_pairs() -> TestResult<Vec<u8>> {
    let mut source = source_with_shadow_jump_code_io()?;
    let profile = current_profile();
    for (position, decoded) in [
        (81usize, profile.input_instruction()),
        (82usize, profile.output_instruction()),
        (83usize, b'v'),
    ] {
        let cell = source
            .get_mut(position)
            .ok_or_else(|| format!("missing two-pair I/O cell {position}"))?;
        *cell = encoded_profile_instruction(decoded, position)?;
    }
    Ok(source)
}

#[test]
fn jump_code_halt_verifier_executes_exact_source_target_at_minimum_width()
-> TestResult {
    let source = source_with_source_backed_jump_code_halt()?;
    admit_jump_code_every_reviewed_width(&source)?;
    let verified = normalize_result(
        verify_minimum_jump_code_halt_profile_width(current_profile(), &source),
    )?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::JumpCodeHaltProjection,
        "jump-code proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "jump-code minimum width",
    )?;
    let mut narrow = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    let mut canonical = normalize_result(ProfileMachine::from_source(
        current_profile(),
        &source,
        Vec::new(),
    ))?;
    let narrow_outcome = normalize_result(narrow.run(2))?;
    let canonical_outcome = normalize_result(canonical.run(2))?;
    check_equal(
        &narrow_outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 2,
        },
        "jump-code narrow outcome",
    )?;
    check_equal(
        &canonical_outcome,
        &narrow_outcome,
        "jump-code canonical outcome",
    )?;
    check_equal(
        &narrow.registers().code_pointer,
        &99u32,
        "jump-code exact halt pointer",
    )?;
    check_complete_profile_projection(
        &narrow,
        &canonical,
        verified.memory_words(),
        "jump-code",
    )
}

#[test]
fn jump_code_verifier_executes_two_source_backed_jumps() -> TestResult {
    let source = source_with_two_source_backed_jump_codes()?;
    admit_jump_code_every_reviewed_width(&source)?;
    let verified = normalize_result(
        verify_minimum_jump_code_halt_profile_width(current_profile(), &source),
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "repeated jump-code minimum width",
    )?;
    let mut narrow = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    let mut canonical = normalize_result(ProfileMachine::from_source(
        current_profile(),
        &source,
        Vec::new(),
    ))?;
    let narrow_outcome = normalize_result(narrow.run(3))?;
    let canonical_outcome = normalize_result(canonical.run(3))?;
    check_equal(
        &narrow_outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 3,
        },
        "repeated jump-code narrow outcome",
    )?;
    check_equal(
        &canonical_outcome,
        &narrow_outcome,
        "repeated jump-code canonical outcome",
    )?;
    check_equal(
        &narrow.registers().code_pointer,
        &40u32,
        "repeated jump-code exact halt pointer",
    )?;
    check_equal(
        &narrow.registers().data_pointer,
        &2u32,
        "repeated jump-code exact data pointer",
    )?;
    check_complete_profile_projection(
        &narrow,
        &canonical,
        verified.memory_words(),
        "repeated jump-code",
    )
}

#[test]
fn jump_code_verifier_follows_exact_self_encryption_shadow() -> TestResult {
    let source = source_with_shadow_dependent_jump_codes()?;
    admit_jump_code_every_reviewed_width(&source)?;
    let verified = normalize_result(
        verify_minimum_jump_code_halt_profile_width(current_profile(), &source),
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "shadow jump-code minimum width",
    )?;
    let mut narrow = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    let mut canonical = normalize_result(ProfileMachine::from_source(
        current_profile(),
        &source,
        Vec::new(),
    ))?;
    let narrow_outcome = normalize_result(narrow.run(5))?;
    let canonical_outcome = normalize_result(canonical.run(5))?;
    check_equal(
        &narrow_outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 5,
        },
        "shadow jump-code narrow outcome",
    )?;
    check_equal(
        &canonical_outcome,
        &narrow_outcome,
        "shadow jump-code canonical outcome",
    )?;
    let mutated = normalize_result(narrow.memory_word(38))?;
    check_equal(
        &decode_profile_instruction(mutated, 38),
        &Some(b'i'),
        "shadow jump-code encrypted decode",
    )?;
    check_equal(
        &narrow.registers().code_pointer,
        &79u32,
        "shadow jump-code exact halt pointer",
    )?;
    check_equal(
        &narrow.registers().data_pointer,
        &4u32,
        "shadow jump-code exact data pointer",
    )?;
    check_complete_profile_projection(
        &narrow,
        &canonical,
        verified.memory_words(),
        "shadow jump-code",
    )
}

#[test]
fn jump_code_rotate_verifier_executes_exact_source_write() -> TestResult {
    let source = source_with_shadow_jump_code_rotate(b'j')?;
    for (word_trits, _memory_words) in CHECKED_GEOMETRIES {
        let _admitted =
            normalize_result(verify_jump_code_rotate_halt_profile_width(
                current_profile(),
                &source,
                word_trits,
            ))?;
    }
    let verified =
        normalize_result(verify_minimum_jump_code_rotate_halt_profile_width(
            current_profile(),
            &source,
        ))?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::JumpCodeRotateHaltProjection,
        "jump-code rotate proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "jump-code rotate minimum width",
    )?;
    check_jump_code_rotate_execution(&source, &verified)
}

fn check_jump_code_rotate_execution(
    source: &[u8],
    verified: &malbolge::VerifiedProfileExecutionGeometry,
) -> TestResult {
    let mut narrow = normalize_result(ProfileMachine::from_verified_source(
        verified,
        Vec::new(),
    ))?;
    let mut canonical = normalize_result(ProfileMachine::from_source(
        current_profile(),
        source,
        Vec::new(),
    ))?;
    let narrow_outcome = normalize_result(narrow.run(6))?;
    let canonical_outcome = normalize_result(canonical.run(6))?;
    check_equal(
        &narrow_outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 6,
        },
        "jump-code rotate narrow outcome",
    )?;
    check_equal(
        &canonical_outcome,
        &narrow_outcome,
        "jump-code rotate canonical outcome",
    )?;
    check_equal(
        &narrow.registers().accumulator,
        &12u32,
        "jump-code rotate accumulator",
    )?;
    check_equal(
        &normalize_result(narrow.memory_word(4))?,
        &12u32,
        "jump-code rotate source write",
    )?;
    check_complete_profile_projection(
        &narrow,
        &canonical,
        verified.memory_words(),
        "jump-code rotate",
    )
}

#[test]
fn jump_code_rotate_projection_miss_preserves_canonical_width() -> TestResult {
    let source = source_with_shadow_jump_code_rotate(b'i')?;
    check_equal(
        &verify_jump_code_rotate_halt_profile_width(
            current_profile(),
            &source,
            MINIMUM_WORD_TRITS,
        ),
        &Err(ProfileWidthVerificationError::JumpCodeRotateProjection),
        "jump-code rotate N10 projection rejection",
    )?;
    let minimum =
        normalize_result(verify_minimum_jump_code_rotate_halt_profile_width(
            current_profile(),
            &source,
        ))?;
    check_equal(
        &minimum.word_trits(),
        &CANONICAL_WORD_TRITS,
        "jump-code rotate only canonical width",
    )?;
    check_equal(
        &select_minimum_verified_profile_width(current_profile(), &source, &[]),
        &None,
        "jump-code rotate composite fallback",
    )?;
    let machine = normalize_result(ProfileMachine::from_adaptive_source(
        current_profile(),
        &source,
        Vec::new(),
    ))?;
    check_equal(
        &machine.geometry().word_trits(),
        &CANONICAL_WORD_TRITS,
        "jump-code rotate adaptive canonical width",
    )
}

#[test]
fn jump_code_io_verifier_recovers_exact_byte_after_shadow_chain() -> TestResult
{
    let source = source_with_shadow_jump_code_io()?;
    for (word_trits, _memory_words) in CHECKED_GEOMETRIES {
        let _admitted =
            normalize_result(verify_jump_code_io_halt_profile_width(
                current_profile(),
                &source,
                word_trits,
            ))?;
    }
    let verified =
        normalize_result(verify_minimum_jump_code_io_halt_profile_width(
            current_profile(),
            &source,
        ))?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::JumpCodeIoHaltProjection,
        "jump-code I/O proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "jump-code I/O minimum width",
    )?;
    check_jump_code_io_execution(&source, &verified, vec![0xa5], 7)
}

fn check_jump_code_io_execution(
    source: &[u8],
    verified: &malbolge::VerifiedProfileExecutionGeometry,
    input: Vec<u8>,
    step_count: usize,
) -> TestResult {
    let expected_output = input.clone();
    let mut narrow = normalize_result(ProfileMachine::from_verified_source(
        verified,
        input.clone(),
    ))?;
    let mut canonical = normalize_result(ProfileMachine::from_source(
        current_profile(),
        source,
        input,
    ))?;
    let narrow_outcome = normalize_result(narrow.run(step_count))?;
    let canonical_outcome = normalize_result(canonical.run(step_count))?;
    check_equal(
        &narrow_outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: step_count,
        },
        "jump-code I/O narrow outcome",
    )?;
    check_equal(
        &canonical_outcome,
        &narrow_outcome,
        "jump-code I/O canonical outcome",
    )?;
    if narrow.output() != expected_output.as_slice() {
        return Err(String::from("jump-code I/O output drifted"));
    }
    check_equal(
        &narrow.input_consumed(),
        &expected_output.len(),
        "jump-code I/O input cursor",
    )?;
    check_complete_profile_projection(
        &narrow,
        &canonical,
        verified.memory_words(),
        "jump-code I/O",
    )
}

#[test]
fn jump_code_io_policy_tracks_two_required_bytes_after_shadow_chain()
-> TestResult {
    let source = source_with_two_shadow_jump_code_io_pairs()?;
    let verified =
        normalize_result(verify_minimum_jump_code_io_halt_profile_width(
            current_profile(),
            &source,
        ))?;
    check_equal(
        &ProfileMachine::from_verified_source(&verified, vec![0xa5]).err(),
        &Some(ProfileMachineError::VerifiedInputRejected),
        "jump-code I/O one-byte rejection",
    )?;
    check_equal(
        &select_minimum_verified_profile_width(current_profile(), &source, &[
            0xa5,
        ]),
        &None,
        "jump-code I/O one-byte selector fallback",
    )?;
    let selected =
        select_minimum_verified_profile_width(current_profile(), &source, &[
            0xa5, 0x3c,
        ])
        .ok_or_else(|| {
            String::from("two-byte jump-code I/O was not selected")
        })?;
    check_equal(
        &selected.geometry(),
        &verified.geometry(),
        "two-byte jump-code I/O authority",
    )?;
    check_jump_code_io_execution(&source, &verified, vec![0xa5, 0x3c], 9)
}

#[test]
fn jump_code_io_policy_rejects_eof_and_preserves_canonical_fallback()
-> TestResult {
    let source = source_with_shadow_jump_code_io()?;
    let verified =
        normalize_result(verify_minimum_jump_code_io_halt_profile_width(
            current_profile(),
            &source,
        ))?;
    check_equal(
        &ProfileMachine::from_verified_source(&verified, Vec::new()).err(),
        &Some(ProfileMachineError::VerifiedInputRejected),
        "jump-code I/O empty-input rejection",
    )?;
    check_equal(
        &select_minimum_verified_profile_width(current_profile(), &source, &[]),
        &None,
        "jump-code I/O empty-input selector fallback",
    )?;
    let machine = normalize_result(ProfileMachine::from_adaptive_source(
        current_profile(),
        &source,
        Vec::new(),
    ))?;
    check_equal(
        &machine.geometry().word_trits(),
        &CANONICAL_WORD_TRITS,
        "jump-code I/O EOF canonical width",
    )
}

#[test]
fn jump_code_io_verifier_rejects_wrong_output_suffix() -> TestResult {
    let mut source = source_with_shadow_jump_code_io()?;
    let output = source
        .get_mut(80)
        .ok_or_else(|| String::from("missing jump-code output suffix"))?;
    *output = encoded_profile_instruction(b'v', 80)?;
    check_equal(
        &verify_jump_code_io_halt_profile_width(
            current_profile(),
            &source,
            MINIMUM_WORD_TRITS,
        ),
        &Err(ProfileWidthVerificationError::JumpCodeIoHaltInstruction {
            position: 80,
            decoded: b'v',
        }),
        "jump-code I/O suffix rejection",
    )
}

#[test]
fn jump_code_halt_verifier_rejects_second_target_outside_source() -> TestResult
{
    let mut source = source_with_two_source_backed_jump_codes()?;
    let outside_target = encoded_profile_instruction(b'/', 1)?;
    let second_data = source
        .get_mut(1)
        .ok_or_else(|| String::from("missing repeated jump-code data cell"))?;
    *second_data = outside_target;
    check_equal(
        &verify_jump_code_halt_profile_width(
            current_profile(),
            &source,
            MINIMUM_WORD_TRITS,
        ),
        &Err(ProfileWidthVerificationError::JumpCodeProjection),
        "repeated jump-code source-bound rejection",
    )?;
    check_equal(
        &select_minimum_verified_profile_width(current_profile(), &source, &[]),
        &None,
        "repeated jump-code composite fallback",
    )
}

#[test]
fn exact_recurrence_code_target_forces_next_width_divergence() -> TestResult {
    for (word_trits, modulus) in CHECKED_GEOMETRIES
        .into_iter()
        .filter(|(word_trits, _words)| *word_trits < CANONICAL_WORD_TRITS)
    {
        let high_trits = CANONICAL_WORD_TRITS.saturating_sub(word_trits);
        let high_domain = 3u32.pow(u32::from(high_trits));
        for high_data in 0u32..high_domain {
            let wide_data = high_data.saturating_mul(modulus);
            let wide_next = profile_crazy(wide_data, 0, CANONICAL_WORD_TRITS);
            if wide_next < modulus {
                return Err(format!(
                    "N{word_trits} recurrence successor stayed narrow"
                ));
            }
        }
    }
    Ok(())
}

#[test]
fn jump_code_halt_verifier_rejects_recurrence_encryption_target() -> TestResult
{
    let source = [
        encoded_profile_instruction(b'i', 0)?,
        encoded_profile_instruction(b'v', 1)?,
    ];
    check_equal(
        &verify_jump_code_halt_profile_width(
            current_profile(),
            &source,
            MINIMUM_WORD_TRITS,
        ),
        &Err(ProfileWidthVerificationError::JumpCodeProjection),
        "jump-code recurrence target rejection",
    )?;
    check_equal(
        &select_minimum_verified_profile_width(current_profile(), &source, &[]),
        &None,
        "jump-code composite fallback",
    )?;
    let machine = normalize_result(ProfileMachine::from_adaptive_source(
        current_profile(),
        &source,
        Vec::new(),
    ))?;
    check_equal(
        &machine.geometry().word_trits(),
        &CANONICAL_WORD_TRITS,
        "jump-code adaptive canonical geometry",
    )
}

fn check_complete_profile_projection(
    narrow: &ProfileMachine,
    canonical: &ProfileMachine,
    modulus: u32,
    label: &str,
) -> TestResult {
    let narrow_registers = narrow.registers();
    let canonical_registers = canonical.registers();
    for (name, narrow_value, canonical_value) in [
        (
            "accumulator",
            narrow_registers.accumulator,
            canonical_registers.accumulator,
        ),
        (
            "code",
            narrow_registers.code_pointer,
            canonical_registers.code_pointer,
        ),
        (
            "data",
            narrow_registers.data_pointer,
            canonical_registers.data_pointer,
        ),
    ] {
        if narrow_value != canonical_value.rem_euclid(modulus) {
            return Err(format!("{label} {name} projection differs"));
        }
    }
    for (address, (narrow_word, wide_word)) in
        narrow.memory().iter().zip(canonical.memory()).enumerate()
    {
        if *narrow_word != wide_word.rem_euclid(modulus) {
            return Err(format!(
                "{label} memory projection differs at {address}"
            ));
        }
    }
    Ok(())
}

#[test]
fn jump_rotate_crazy_tracks_projected_accumulator_chain() -> TestResult {
    for (word_trits, _memory_words) in CHECKED_GEOMETRIES {
        let _verified =
            normalize_result(verify_jump_rotate_crazy_halt_profile_width(
                current_profile(),
                JUMP_ROTATE_CRAZY_SAFE,
                word_trits,
            ))?;
    }
    let verified =
        normalize_result(verify_minimum_jump_rotate_crazy_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_CRAZY_SAFE,
        ))?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::JumpRotateCrazyHaltProjection,
        "jump-rotate-crazy proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "jump-rotate-crazy minimum width",
    )?;
    check_jump_rotate_crazy_execution(&verified)
}

fn check_jump_rotate_crazy_execution(
    verified: &malbolge::VerifiedProfileExecutionGeometry,
) -> TestResult {
    let mut narrow = normalize_result(ProfileMachine::from_verified_source(
        verified,
        Vec::new(),
    ))?;
    let mut canonical = normalize_result(ProfileMachine::from_source(
        current_profile(),
        JUMP_ROTATE_CRAZY_SAFE,
        Vec::new(),
    ))?;
    check_equal(
        &normalize_result(narrow.run(2))?,
        &RunOutcome::BudgetExhausted { steps: 2 },
        "jump-rotate-crazy narrow rotate prefix",
    )?;
    check_equal(
        &normalize_result(canonical.run(2))?,
        &RunOutcome::BudgetExhausted { steps: 2 },
        "jump-rotate-crazy canonical rotate prefix",
    )?;
    check_equal(
        &narrow.registers().accumulator,
        &29_529u32,
        "jump-rotate-crazy narrow rotated A",
    )?;
    check_equal(
        &canonical.registers().accumulator,
        &7_174_458u32,
        "jump-rotate-crazy canonical rotated A",
    )?;
    check_complete_profile_projection(
        &narrow,
        &canonical,
        verified.memory_words(),
        "jump-rotate-crazy rotate prefix",
    )?;
    check_jump_rotate_crazy_suffix(&mut narrow, &mut canonical, verified)
}

fn check_jump_rotate_crazy_writes(
    narrow: &ProfileMachine,
    canonical: &ProfileMachine,
) -> TestResult {
    for (address, narrow_word, wide_word) in [
        (42usize, 67u32, 67u32),
        (43, 29_538, 7_174_467),
        (44, 49, 49),
        (45, 29_538, 7_174_467),
    ] {
        check_equal(
            &narrow.memory().get(address).copied(),
            &Some(narrow_word),
            "jump-rotate-crazy narrow write",
        )?;
        check_equal(
            &canonical.memory().get(address).copied(),
            &Some(wide_word),
            "jump-rotate-crazy canonical write",
        )?;
    }
    Ok(())
}

fn check_jump_rotate_crazy_suffix(
    narrow: &mut ProfileMachine,
    canonical: &mut ProfileMachine,
    verified: &malbolge::VerifiedProfileExecutionGeometry,
) -> TestResult {
    check_equal(
        &normalize_result(narrow.run(4))?,
        &RunOutcome::BudgetExhausted { steps: 4 },
        "jump-rotate-crazy narrow crazy prefix",
    )?;
    check_equal(
        &normalize_result(canonical.run(4))?,
        &RunOutcome::BudgetExhausted { steps: 4 },
        "jump-rotate-crazy canonical crazy prefix",
    )?;
    check_equal(
        &narrow.registers().accumulator,
        &29_538u32,
        "jump-rotate-crazy narrow projected A",
    )?;
    check_equal(
        &canonical.registers().accumulator,
        &7_174_467u32,
        "jump-rotate-crazy canonical projected A",
    )?;
    check_jump_rotate_crazy_writes(narrow, canonical)?;
    check_complete_profile_projection(
        narrow,
        canonical,
        verified.memory_words(),
        "jump-rotate-crazy crazy prefix",
    )?;
    let narrow_outcome = normalize_result(narrow.run(1))?;
    let canonical_outcome = normalize_result(canonical.run(1))?;
    check_equal(
        &narrow_outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 1,
        },
        "jump-rotate-crazy narrow halt",
    )?;
    check_equal(
        &canonical_outcome,
        &narrow_outcome,
        "jump-rotate-crazy canonical halt",
    )?;
    check_complete_profile_projection(
        narrow,
        canonical,
        verified.memory_words(),
        "jump-rotate-crazy final",
    )
}

#[test]
fn jump_rotate_crazy_projection_miss_preserves_canonical_width() -> TestResult {
    check_equal(
        &verify_jump_rotate_crazy_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_CRAZY_UNSAFE,
            MINIMUM_WORD_TRITS,
        ),
        &Err(ProfileWidthVerificationError::JumpRotateProjection),
        "jump-rotate-crazy incompatible N10 projection",
    )?;
    let canonical =
        normalize_result(verify_minimum_jump_rotate_crazy_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_CRAZY_UNSAFE,
        ))?;
    check_equal(
        &canonical.word_trits(),
        &CANONICAL_WORD_TRITS,
        "jump-rotate-crazy canonical fallback",
    )?;
    check_equal(
        &select_minimum_verified_profile_width(
            current_profile(),
            JUMP_ROTATE_CRAZY_UNSAFE,
            &[],
        ),
        &None,
        "jump-rotate-crazy composite fallback",
    )
}

#[test]
fn jump_rotate_io_recovers_exact_byte_after_projected_rotate() -> TestResult {
    for (word_trits, _memory_words) in CHECKED_GEOMETRIES {
        let _verified =
            normalize_result(verify_jump_rotate_io_halt_profile_width(
                current_profile(),
                JUMP_ROTATE_IO_SAFE,
                word_trits,
            ))?;
    }
    let verified =
        normalize_result(verify_minimum_jump_rotate_io_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_IO_SAFE,
        ))?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::JumpRotateIoHaltProjection,
        "jump-rotate I/O proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "jump-rotate I/O minimum width",
    )?;
    check_jump_rotate_io_recovery(&verified)
}

fn projected_jump_rotate_io_machines(
    verified: &malbolge::VerifiedProfileExecutionGeometry,
) -> TestResult<(ProfileMachine, ProfileMachine)> {
    let input = vec![0xa5];
    let mut narrow = normalize_result(ProfileMachine::from_verified_source(
        verified,
        input.clone(),
    ))?;
    let mut canonical = normalize_result(ProfileMachine::from_source(
        current_profile(),
        JUMP_ROTATE_IO_SAFE,
        input,
    ))?;
    check_equal(
        &normalize_result(narrow.run(4))?,
        &RunOutcome::BudgetExhausted { steps: 4 },
        "jump-rotate I/O narrow projected prefix",
    )?;
    check_equal(
        &normalize_result(canonical.run(4))?,
        &RunOutcome::BudgetExhausted { steps: 4 },
        "jump-rotate I/O canonical projected prefix",
    )?;
    check_equal(
        &narrow.registers().accumulator,
        &29_517u32,
        "jump-rotate I/O narrow projected accumulator",
    )?;
    check_equal(
        &canonical.registers().accumulator,
        &7_174_446u32,
        "jump-rotate I/O canonical projected accumulator",
    )?;
    if narrow.registers().accumulator == canonical.registers().accumulator {
        return Err(String::from(
            "jump-rotate I/O prefix became numerically exact",
        ));
    }
    check_complete_profile_projection(
        &narrow,
        &canonical,
        verified.memory_words(),
        "jump-rotate I/O projected prefix",
    )?;
    Ok((narrow, canonical))
}

fn check_jump_rotate_io_recovery(
    verified: &malbolge::VerifiedProfileExecutionGeometry,
) -> TestResult {
    let (mut narrow, mut canonical) =
        projected_jump_rotate_io_machines(verified)?;
    let _narrow_input = normalize_result(narrow.run(1))?;
    let _canonical_input = normalize_result(canonical.run(1))?;
    check_equal(
        &narrow.registers().accumulator,
        &0xa5u32,
        "jump-rotate I/O recovered narrow accumulator",
    )?;
    check_equal(
        &canonical.registers().accumulator,
        &0xa5u32,
        "jump-rotate I/O recovered canonical accumulator",
    )?;
    let narrow_outcome = normalize_result(narrow.run(2))?;
    let canonical_outcome = normalize_result(canonical.run(2))?;
    check_equal(
        &narrow_outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 2,
        },
        "jump-rotate I/O narrow completion",
    )?;
    check_equal(
        &canonical_outcome,
        &narrow_outcome,
        "jump-rotate I/O canonical completion",
    )?;
    if narrow.output() != [0xa5] {
        return Err(String::from("jump-rotate I/O exact output drifted"));
    }
    check_complete_profile_projection(
        &narrow,
        &canonical,
        verified.memory_words(),
        "jump-rotate I/O final",
    )
}

#[test]
fn jump_rotate_io_policy_tracks_four_required_bytes() -> TestResult {
    for (word_trits, _memory_words) in CHECKED_GEOMETRIES {
        let _verified =
            normalize_result(verify_jump_rotate_io_halt_profile_width(
                current_profile(),
                JUMP_ROTATE_IO_FOUR_PAIRS,
                word_trits,
            ))?;
    }
    let verified =
        normalize_result(verify_minimum_jump_rotate_io_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_IO_FOUR_PAIRS,
        ))?;
    let one_pair =
        normalize_result(verify_minimum_jump_rotate_io_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_IO_SAFE,
        ))?;
    if verified.geometry() == one_pair.geometry() {
        return Err(String::from("rotate I/O input policies collapsed"));
    }
    check_equal(
        &ProfileMachine::from_verified_source(&verified, vec![
            0xa5, 0x3c, 0x7f,
        ])
        .err(),
        &Some(ProfileMachineError::VerifiedInputRejected),
        "four-pair rotate I/O short-input rejection",
    )?;
    check_equal(
        &select_minimum_verified_profile_width(
            current_profile(),
            JUMP_ROTATE_IO_FOUR_PAIRS,
            &[0xa5, 0x3c, 0x7f],
        ),
        &None,
        "four-pair rotate I/O short-input selector",
    )?;
    let input = vec![0xa5, 0x3c, 0x7f, 0x00];
    let selected = select_minimum_verified_profile_width(
        current_profile(),
        JUMP_ROTATE_IO_FOUR_PAIRS,
        &input,
    )
    .ok_or_else(|| String::from("four-pair rotate I/O was not selected"))?;
    check_equal(
        &selected.geometry(),
        &verified.geometry(),
        "four-pair rotate I/O authority",
    )?;
    check_four_pair_jump_rotate_io_execution(&verified, &input)
}

fn check_four_pair_jump_rotate_io_execution(
    verified: &malbolge::VerifiedProfileExecutionGeometry,
    input: &[u8],
) -> TestResult {
    let mut narrow = normalize_result(ProfileMachine::from_verified_source(
        verified,
        input.to_owned(),
    ))?;
    let mut canonical = normalize_result(ProfileMachine::from_source(
        current_profile(),
        JUMP_ROTATE_IO_FOUR_PAIRS,
        input.to_owned(),
    ))?;
    let narrow_outcome = normalize_result(narrow.run(13))?;
    let canonical_outcome = normalize_result(canonical.run(13))?;
    check_equal(
        &narrow_outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 13,
        },
        "four-pair rotate I/O narrow outcome",
    )?;
    check_equal(
        &canonical_outcome,
        &narrow_outcome,
        "four-pair rotate I/O canonical outcome",
    )?;
    if narrow.output() != input || narrow.input_consumed() != 4 {
        return Err(String::from("four-pair rotate I/O exact I/O drifted"));
    }
    check_complete_profile_projection(
        &narrow,
        &canonical,
        verified.memory_words(),
        "four-pair rotate I/O final",
    )
}

#[test]
fn jump_rotate_io_source_length_rechecks_rotate_projection() -> TestResult {
    check_equal(
        &verify_jump_rotate_io_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_IO_TWO_PAIRS,
            MINIMUM_WORD_TRITS,
        ),
        &Err(ProfileWidthVerificationError::JumpRotateProjection),
        "two-pair rotate I/O N10 projection rejection",
    )?;
    let minimum =
        normalize_result(verify_minimum_jump_rotate_io_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_IO_TWO_PAIRS,
        ))?;
    check_equal(
        &minimum.word_trits(),
        &CANONICAL_WORD_TRITS,
        "two-pair rotate I/O canonical minimum",
    )?;
    check_equal(
        &select_minimum_verified_profile_width(
            current_profile(),
            JUMP_ROTATE_IO_TWO_PAIRS,
            &[0xa5, 0x3c],
        ),
        &None,
        "two-pair rotate I/O composite fallback",
    )
}

#[test]
fn jump_rotate_io_rejects_eof_and_incompatible_projection() -> TestResult {
    let verified =
        normalize_result(verify_minimum_jump_rotate_io_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_IO_SAFE,
        ))?;
    check_equal(
        &ProfileMachine::from_verified_source(&verified, Vec::new()).err(),
        &Some(ProfileMachineError::VerifiedInputRejected),
        "jump-rotate I/O EOF token rejection",
    )?;
    check_equal(
        &select_minimum_verified_profile_width(
            current_profile(),
            JUMP_ROTATE_IO_SAFE,
            &[],
        ),
        &None,
        "jump-rotate I/O EOF selector fallback",
    )?;
    check_equal(
        &verify_jump_rotate_io_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_IO_UNSAFE,
            MINIMUM_WORD_TRITS,
        ),
        &Err(ProfileWidthVerificationError::JumpRotateProjection),
        "jump-rotate I/O incompatible N10 projection",
    )?;
    let minimum =
        normalize_result(verify_minimum_jump_rotate_io_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_IO_UNSAFE,
        ))?;
    check_equal(
        &minimum.word_trits(),
        &CANONICAL_WORD_TRITS,
        "jump-rotate I/O incompatible canonical width",
    )?;
    check_equal(
        &select_minimum_verified_profile_width(
            current_profile(),
            JUMP_ROTATE_IO_UNSAFE,
            &[0xa5],
        ),
        &None,
        "jump-rotate I/O incompatible composite fallback",
    )
}

#[test]
fn jump_rotate_halt_verifier_executes_projected_write_at_minimum_width()
-> TestResult {
    for (word_trits, _memory_words) in CHECKED_GEOMETRIES {
        let _admitted =
            normalize_result(verify_jump_rotate_halt_profile_width(
                current_profile(),
                JUMP_ROTATE_SAFE,
                word_trits,
            ))?;
    }
    let verified =
        normalize_result(verify_minimum_jump_rotate_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_SAFE,
        ))?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::JumpRotateHaltProjection,
        "jump-rotate proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "jump-rotate minimum width",
    )?;
    let mut narrow = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    let mut canonical = normalize_result(ProfileMachine::from_source(
        current_profile(),
        JUMP_ROTATE_SAFE,
        Vec::new(),
    ))?;
    let narrow_outcome = normalize_result(narrow.run(3))?;
    let canonical_outcome = normalize_result(canonical.run(3))?;
    check_equal(
        &narrow_outcome,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 3,
        },
        "jump-rotate narrow outcome",
    )?;
    check_equal(
        &canonical_outcome,
        &narrow_outcome,
        "jump-rotate canonical outcome",
    )?;
    check_complete_profile_projection(
        &narrow,
        &canonical,
        verified.memory_words(),
        "jump-rotate",
    )
}

#[test]
fn jump_rotate_halt_verifier_rejects_incompatible_rotate_projection()
-> TestResult {
    check_equal(
        &verify_jump_rotate_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_UNSAFE,
            MINIMUM_WORD_TRITS,
        ),
        &Err(ProfileWidthVerificationError::JumpRotateProjection),
        "jump-rotate incompatible N10 rejection",
    )?;
    let canonical =
        normalize_result(verify_minimum_jump_rotate_halt_profile_width(
            current_profile(),
            JUMP_ROTATE_UNSAFE,
        ))?;
    check_equal(
        &canonical.word_trits(),
        &CANONICAL_WORD_TRITS,
        "jump-rotate incompatible minimum fallback",
    )?;
    check_equal(
        &select_minimum_verified_profile_width(
            current_profile(),
            JUMP_ROTATE_UNSAFE,
            &[],
        ),
        &None,
        "jump-rotate composite canonical fallback",
    )?;
    let machine = normalize_result(ProfileMachine::from_adaptive_source(
        current_profile(),
        JUMP_ROTATE_UNSAFE,
        Vec::new(),
    ))?;
    check_equal(
        &machine.geometry().word_trits(),
        &CANONICAL_WORD_TRITS,
        "jump-rotate adaptive canonical geometry",
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
fn repeated_jump_verifier_recomputes_exact_recurrence_reads() -> TestResult {
    let verified =
        normalize_result(verify_minimum_repeated_jump_data_profile_width(
            current_profile(),
            b"('&N",
        ))?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::RepeatedJumpDataProjection,
        "repeated-jump proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "repeated-jump minimum width",
    )?;
    let mut machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        Vec::new(),
    ))?;
    check_equal(
        &normalize_result(machine.run(4))?,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 4,
        },
        "repeated-jump outcome",
    )
}

#[test]
fn repeated_jump_verifier_rejects_nonjump_prefix() -> TestResult {
    let observed = verify_repeated_jump_data_profile_width(
        current_profile(),
        b"(P",
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &observed,
        &Err(ProfileWidthVerificationError::RepeatedJumpMissingHalt),
        "repeated-jump minimum prefix rejection",
    )?;
    let projected_only = verify_repeated_jump_data_profile_width(
        current_profile(),
        b"('O",
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &projected_only,
        &Err(ProfileWidthVerificationError::RepeatedJumpMemoryMismatch {
            address: 41,
        }),
        "repeated-jump projected-only rejection",
    )?;
    let projected_d_crazy = verify_repeated_jump_data_profile_width(
        current_profile(),
        b"('<AM",
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &projected_d_crazy,
        &Err(ProfileWidthVerificationError::RepeatedJumpMemoryMismatch {
            address: 41,
        }),
        "projected-D crazy authority rejection",
    )
}

#[test]
fn straight_line_io_verifier_binds_exact_required_input_prefix() -> TestResult {
    let verified =
        normalize_result(verify_minimum_straight_line_io_profile_width(
            current_profile(),
            b"uCar_L",
        ))?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::StraightLineIoProjection,
        "straight-line proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "straight-line minimum width",
    )?;
    let mut machine = normalize_result(ProfileMachine::from_verified_source(
        &verified,
        vec![0xa5, 0x3c],
    ))?;
    check_equal(
        &normalize_result(machine.run(6))?,
        &RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 6,
        },
        "straight-line outcome",
    )?;
    check_equal(
        &machine.output(),
        &vec![0xa5, 0x3c].as_slice(),
        "straight-line output",
    )?;
    check_equal(
        &machine.input_consumed(),
        &2usize,
        "straight-line consumed input",
    )?;
    let short = ProfileMachine::from_verified_source(&verified, vec![0xa5]);
    if matches!(short, Err(ProfileMachineError::VerifiedInputRejected)) {
        Ok(())
    } else {
        Err(String::from("straight-line proof admitted short input"))
    }
}

#[test]
fn straight_line_io_verifier_rejects_unsupported_or_unterminated_prefix()
-> TestResult {
    let unsupported = verify_straight_line_io_profile_width(
        current_profile(),
        b"(P",
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &unsupported,
        &Err(ProfileWidthVerificationError::StraightLineInstruction {
            position: 0,
            decoded: b'j',
        }),
        "straight-line unsupported opcode",
    )?;
    let unterminated = verify_straight_line_io_profile_width(
        current_profile(),
        b"uC",
        MINIMUM_WORD_TRITS,
    );
    check_equal(
        &unterminated,
        &Err(ProfileWidthVerificationError::StraightLineMissingHalt),
        "straight-line missing halt",
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
fn adaptive_selector_respects_input_policy_and_canonical_width() -> TestResult {
    let initial =
        select_minimum_verified_profile_width(current_profile(), QP, &[])
            .ok_or_else(|| {
                String::from("initial-halt adaptive proof missing")
            })?;
    check_equal(
        &initial.word_trits(),
        &MINIMUM_WORD_TRITS,
        "initial-halt adaptive width",
    )?;

    let available =
        select_minimum_verified_profile_width(current_profile(), b"ubO\n", &[
            0xa5,
        ])
        .ok_or_else(|| String::from("byte-I/O adaptive proof missing"))?;
    check_equal(
        &available.word_trits(),
        &MINIMUM_WORD_TRITS,
        "byte-I/O adaptive width",
    )?;
    check_equal(
        &select_minimum_verified_profile_width(current_profile(), b"ubO\n", &[
        ]),
        &None,
        "EOF-visible adaptive rejection",
    )?;
    check_equal(
        &select_minimum_verified_profile_width(historical_profile(), QP, &[]),
        &None,
        "canonical-width adaptive rejection",
    )
}

#[test]
fn adaptive_source_constructor_falls_back_for_eof_visible_io() -> TestResult {
    let initial = normalize_result(ProfileMachine::from_adaptive_source(
        current_profile(),
        QP,
        Vec::new(),
    ))?;
    check_equal(
        &initial.geometry().word_trits(),
        &MINIMUM_WORD_TRITS,
        "adaptive initial-halt machine width",
    )?;

    let mut eof = normalize_result(ProfileMachine::from_adaptive_source(
        current_profile(),
        b"ubO\n",
        Vec::new(),
    ))?;
    check_equal(
        &eof.geometry().word_trits(),
        &CANONICAL_WORD_TRITS,
        "adaptive EOF canonical fallback width",
    )?;
    let _eof_outcome = normalize_result(eof.run(3))?;
    check_equal(eof.output(), &[0x6a], "adaptive EOF canonical output")?;

    let mut byte = normalize_result(ProfileMachine::from_adaptive_source(
        current_profile(),
        b"ubO\n",
        vec![0xa5],
    ))?;
    check_equal(
        &byte.geometry().word_trits(),
        &MINIMUM_WORD_TRITS,
        "adaptive byte-I/O machine width",
    )?;
    let _byte_outcome = normalize_result(byte.run(3))?;
    check_equal(byte.output(), &[0xa5], "adaptive byte-I/O output")
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
