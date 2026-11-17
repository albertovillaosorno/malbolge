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
//   - Finite lower bound for source-tail-assisted C23 signed EOF conversion.
// - Must-Not:
//   - Treat a planned rotation as a guest write or claim general C support.
// - Allows:
//   - Inputs: 94 squared graphical tails, six loader phases, 0..14 rotations.
//   - Outputs: complete 257-value byte proof and a real N15 loader witness.
//   - Side effects: bounded, isolated profiled VM execution.
// - Split-When:
//   - A general guest arithmetic synthesizer makes this finite class obsolete.
// - Merge-When:
//   - The compiler emits and verifies all required operand preparations.
// - Summary:
//   - Nine rotations are necessary in the tested adjacent two-crazy class.

//! An exhaustive pre-layout bound plus one genuine guest write, not P2
//! acceptance.

use malbolge::{
    ProfileMachine, RunOutcome, Termination, current_profile,
    decode_profile_instruction, profile_rotate,
};

const WORD_MODULUS: u32 = 14_348_907;
const TAIL_PAIRS: usize = 94 * 94;
const LOADER_PHASES: usize = 6;
const ROTATIONS: usize = 15;

const EXPECTED_HITS: [Candidate; 4] = [
    Candidate {
        first_tail: b'H',
        phase: 6,
        rotations: 9,
        second_tail: b'y',
    },
    Candidate {
        first_tail: b'I',
        phase: 6,
        rotations: 9,
        second_tail: b'y',
    },
    Candidate {
        first_tail: b'K',
        phase: 6,
        rotations: 9,
        second_tail: b'y',
    },
    Candidate {
        first_tail: b'L',
        phase: 6,
        rotations: 9,
        second_tail: b'y',
    },
];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Candidate {
    first_tail: u8,
    phase: u8,
    rotations: u8,
    second_tail: u8,
}

// Keep an independent digit oracle, rather than accepting the VM's crazy
// helper as both candidate generator and proof of C23 observable behavior.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "15 bounded base-three digit steps form the independent oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut value = 0u32;
    let mut place = 1u32;
    for _ in 0u8..15 {
        let trit = match (data % 3, accumulator % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        value += place * trit;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    value
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "one mathematical 15-trit rotation of an in-range word"
)]
const fn scalar_rotate(word: u32) -> u32 {
    word / 3 + word % 3 * (WORD_MODULUS / 3)
}

#[expect(
    clippy::integer_division_remainder_used,
    reason = "the guest output instruction reduces its accumulator modulo 256"
)]
fn outputs_expected_byte(first: u32, second: u32, input: u32) -> bool {
    let expected = if input == WORD_MODULUS - 1 {
        255
    } else {
        input % 256
    };
    scalar_crazy(second, scalar_crazy(first, input)) % 256 == expected
}

fn collect_rotated_candidates(
    first_tail: u8,
    second_tail: u8,
    candidates: &mut Vec<Candidate>,
) -> usize {
    let mut two_back = u32::from(first_tail);
    let mut one_back = u32::from(second_tail);
    let mut visited = 0usize;
    // Two trailing seed words determine all six recurrent loader phases.
    for phase in 2u8..8 {
        let first_operand = scalar_crazy(two_back, one_back);
        let second_operand = scalar_crazy(one_back, first_operand);
        let mut rotated = first_operand;
        for rotations in 0u8..15 {
            visited = visited.saturating_add(1);
            // Four necessary cases prune; all survivors face 257 outcomes.
            if [0, 1, 255, WORD_MODULUS - 1].into_iter().all(|input| {
                outputs_expected_byte(rotated, second_operand, input)
            }) && (0..=255).all(|input| {
                outputs_expected_byte(rotated, second_operand, input)
            }) {
                candidates.push(Candidate {
                    first_tail,
                    phase,
                    rotations,
                    second_tail,
                });
            }
            rotated = scalar_rotate(rotated);
        }
        two_back = one_back;
        one_back = first_operand;
    }
    visited
}

#[test]
fn finite_loader_seed_class_requires_exactly_nine_rotations() {
    let profile = current_profile();
    assert_eq!(profile.word_modulus(), WORD_MODULUS);
    assert_eq!(profile.eof_word(), WORD_MODULUS - 1);
    let mut candidates = Vec::new();
    let mut visited = 0usize;
    for first_tail in 33..=126u8 {
        for second_tail in 33..=126u8 {
            visited = visited.saturating_add(collect_rotated_candidates(
                first_tail,
                second_tail,
                &mut candidates,
            ));
        }
    }
    assert_eq!(visited, TAIL_PAIRS * LOADER_PHASES * ROTATIONS);
    assert_eq!(candidates, EXPECTED_HITS);
}

fn witness_prefix() -> Result<Vec<u8>, String> {
    let mut source = Vec::with_capacity(91);
    for position in 0..89 {
        let decoded = match position {
            40 => b'j',
            41 => b'*',
            88 => b'v',
            _ => b'o',
        };
        let graphical = (33..=126u8)
            .find(|cell| {
                decode_profile_instruction(u32::from(*cell), position)
                    == Some(decoded)
            })
            .ok_or_else(|| format!("no graphical opcode at C={position}"))?;
        source.push(graphical);
    }
    Ok(source)
}

fn verify_seed_position_admission(prefix: &[u8]) -> Result<(), String> {
    let profile = current_profile();
    for candidate in EXPECTED_HITS {
        let mut source = prefix.to_vec();
        source
            .extend_from_slice(&[candidate.first_tail, candidate.second_tail]);
        // These are the four complete algebraic winners. Only 'Iy' is
        // graphical and decodes to a *loadable* opcode at both real addresses.
        let loadable =
            ProfileMachine::from_source(profile, &source, Vec::new()).is_ok();
        if loadable != (candidate.first_tail == b'I') {
            return Err(format!("incorrect loadability for {candidate:?}"));
        }
    }
    Ok(())
}

fn expanded_operand_pair(vm: &ProfileMachine) -> Result<[u32; 2], String> {
    let first = vm.memory_word(95).map_err(|error| error.to_string())?;
    let second = vm.memory_word(96).map_err(|error| error.to_string())?;
    Ok([first, second])
}

#[expect(
    clippy::panic_in_result_fn,
    reason = "one normative guest trace has an exact decoded instruction"
)]
fn verify_rotation_trace(
    traces: &[malbolge::ProfileStepTrace],
) -> Result<(), String> {
    let rotation = traces.get(41).ok_or("missing guest rotation trace")?;
    assert_eq!(rotation.decoded, Some(b'*'), "expected a real guest rotate");
    assert_eq!(
        rotation.memory_reads.data.map(|read| read.address),
        Some(95),
        "guest rotation must read the loader-expanded operand"
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "the complete VM regression uses assertions and typed setup errors"
)]
fn physically_decodable_seed_replays_a_single_real_guest_rotation()
-> Result<(), String> {
    let profile = current_profile();
    let mut source = witness_prefix()?;
    verify_seed_position_admission(&source)?;
    source.extend_from_slice(b"Iy");
    assert_eq!(source.len(), 91);
    let mut vm = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    let [first, adjacent] = expanded_operand_pair(&vm)?;
    assert_eq!((first, adjacent), (7_174_404, 121));
    let mut traces = Vec::new();
    let outcome = vm
        .run_traced(89, &mut |trace| traces.push(*trace))
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 89,
    });
    assert_eq!(traces.len(), 89);
    verify_rotation_trace(&traces)?;
    assert_eq!(vm.memory_word(95), Ok(profile_rotate(first, WORD_MODULUS)));
    assert_eq!(vm.memory_word(96), Ok(adjacent));
    // Remaining eight writes and live input-to-output are not synthesized.
    assert_ne!(vm.memory_word(95), Ok(7_138_732));
    assert_eq!(vm.input_consumed(), 0);
    Ok(())
}
