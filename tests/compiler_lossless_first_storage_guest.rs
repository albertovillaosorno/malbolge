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
//   - Exact physical byte-plus-EOF storage retained across a second input.
// - Must-Not:
//   - Claim C23 local decoding, checksum arithmetic or dynamic EOF loop.
// - Allows:
//   - Inputs: a fixed nine-rotation loader and two signed guest reads.
//   - Outputs: independent 257-class oracle and normative memory/IO traces.
//   - Side effects: isolated in-memory guest machines only.
// - Split-When:
//   - General C32 storage and guest linker replaces the fixed input primitive.
// - Merge-When:
//   - Source-authenticated checksum lowering consumes a saved signed word.
// - Summary:
//   - The second input cannot destroy a byte-and-EOF-injective first word.

//! Positive retained guest storage, not yet a C32 source local or checksum.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;
use std::iter::once;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, historical_profile,
};

const MODULUS: u32 = 14_348_907;
const INITIAL: u32 = 7_174_457;
const ROTATED: u32 = 7_177_369;
const FIRST_TARGET: u32 = 95;
const STEPS: usize = 54;

// The physical proof uses a separately transcribed truth table, not VM crazy.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent 15-trit oracle with finite constant operands"
)]
fn independent_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const DIGITS: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut word = 0;
    let mut place = 1;
    for _ in 0..15 {
        let row = usize::try_from(data % 3).unwrap_or_default();
        let column = usize::try_from(accumulator % 3).unwrap_or_default();
        word += DIGITS[row][column] * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    word
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::integer_division,
    reason = "exact single-trit right rotation of one N15 guest word"
)]
fn rotate(value: u32) -> u32 {
    value / 3 + value % 3 * (MODULUS / 3)
}

#[test]
fn rotated_seed_is_injective_for_every_byte_and_signed_eof() {
    let seed = (0..9).fold(INITIAL, |word, _| rotate(word));
    assert_eq!(seed, ROTATED);
    let mut low_trits = seed;
    for _ in 0..6 {
        assert_eq!(low_trits % 3, 1);
        low_trits /= 3;
    }
    let words = (u8::MIN..=u8::MAX)
        .map(|byte| independent_crazy(seed, u32::from(byte)))
        .collect::<BTreeSet<_>>();
    assert_eq!(words.len(), 256);
    let eof = independent_crazy(seed, MODULUS - 1);
    assert!(!words.contains(&eof));
}

#[test]
fn source_rejects_other_profiles_and_invalid_pointer_seed() {
    assert_eq!(
        layout::build_seeded_preserved_first_input_source(
            historical_profile(),
            *b",H",
        ),
        Err(layout::RepeatedLoaderRotationError::UnsupportedProfile),
    );
    assert_eq!(
        layout::build_seeded_preserved_first_input_source(
            current_profile(),
            *b"Iy",
        ),
        Err(layout::RepeatedLoaderRotationError::InvalidResetSeed {
            tail: *b"Iy",
        }),
    );
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "bounded all-byte real VM state and second-read proof"
)]
fn first_word_survives_second_real_input_without_aliases() -> Result<(), String>
{
    let profile = current_profile();
    let source =
        layout::build_seeded_preserved_first_input_source(profile, *b",H")
            .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(FIRST_TARGET), Ok(INITIAL));
    let mut observed = BTreeSet::new();
    // Exhaust first byte/EOF and cross-check the second read at EOF.
    // Extra pairs prove second bytes 0, 31, 128 and 255 cannot rewrite M95.
    let cases = once(Vec::new())
        .chain((u8::MIN..=u8::MAX).map(|byte| vec![byte]))
        .chain([0u8, 31, 128, 255].into_iter().flat_map(|first| {
            [0u8, 31, 128, 255]
                .into_iter()
                .map(move |second| vec![first, second])
        }))
        .chain(once(vec![255, 31, 0, 128]));
    let mut checked = 0usize;
    for input in cases {
        let first = input
            .first()
            .copied()
            .map_or_else(|| profile.eof_word(), u32::from);
        let saved = independent_crazy(ROTATED, first);
        let expected_second = input.get(1).copied().unwrap_or(106);
        let second_word = input
            .get(1)
            .copied()
            .map_or_else(|| profile.eof_word(), u32::from);
        let mut machine = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut actual_first_write = None;
        let mut inputs = Vec::new();
        let mut output_events = Vec::new();
        let result = machine
            .run_traced(STEPS, &mut |trace| {
                let address = trace.before.registers.code_pointer;
                if let Some(read) = trace.input {
                    inputs.push((address, read));
                }
                if address == 43 {
                    assert_eq!(trace.decoded, Some(b'p'));
                    assert_eq!(
                        trace.before.registers.data_pointer,
                        FIRST_TARGET
                    );
                    actual_first_write =
                        Some(trace.after.registers.accumulator);
                }
                if address == 47 {
                    assert_eq!(
                        trace.decoded,
                        Some(profile.input_instruction())
                    );
                    assert_eq!(trace.after.registers.accumulator, second_word,);
                }
                if address == 51 {
                    assert_eq!(trace.decoded, Some(b'o'));
                    assert_eq!(
                        trace.before.registers.data_pointer,
                        FIRST_TARGET
                    );
                    assert_eq!(
                        trace.after.registers.accumulator,
                        input
                            .get(1)
                            .copied()
                            .map_or_else(|| profile.eof_word(), u32::from)
                    );
                }
                if let Some(byte) = trace.output {
                    output_events.push((address, byte));
                }
                let overwrote = trace
                    .memory_delta
                    .data
                    .is_some_and(|delta| delta.address == FIRST_TARGET);
                assert!(
                    !(address > 43 && overwrote),
                    "M95 overwritten at C{address}"
                );
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: STEPS,
        });
        assert_eq!(actual_first_write, Some(saved));
        assert_eq!(machine.memory_word(FIRST_TARGET), Ok(saved));
        assert_eq!(inputs, [
            (
                39,
                input
                    .first()
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
            (
                47,
                input
                    .get(1)
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
        ]);
        assert_eq!(output_events, [(52, expected_second)]);
        assert_eq!(machine.output(), &[expected_second]);
        assert_eq!(machine.input_consumed(), input.len().min(2));
        if input.len() <= 1 {
            assert!(observed.insert(saved), "distinct signed input aliases");
        }
        checked += 1;
    }
    assert_eq!(checked, 274);
    assert_eq!(observed.len(), 257);
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    reason = "physical two-read delayed-first-output control vectors"
)]
fn first_word_is_reloaded_after_second_read_and_output() -> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_seeded_delayed_first_output_source(profile, *b",H")
            .map_err(|error| format!("{error:?}"))?;
    let loaded = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    let streams: &[&[u8]] = &[
        &[],
        &[0],
        &[1],
        &[31],
        &[128],
        &[242],
        &[255],
        &[0, 0],
        &[0, 255],
        &[1, 31],
        &[31, 1],
        &[128, 255],
        &[242, 128],
        &[255, 0],
        &[255, 31, 0, 128],
    ];
    for &stream in streams {
        let first = stream
            .first()
            .copied()
            .map_or_else(|| profile.eof_word(), u32::from);
        let second = stream
            .get(1)
            .copied()
            .map_or_else(|| profile.eof_word(), u32::from);
        let saved = independent_crazy(ROTATED, first);
        let reloaded = rotate(saved);
        let derived_first =
            u8::try_from(reloaded % 256).map_err(|error| error.to_string())?;
        let second_low =
            u8::try_from(second % 256).map_err(|error| error.to_string())?;
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            stream.to_vec(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut read_sites = Vec::new();
        let mut outputs = Vec::new();
        let mut saved_before_reload = None;
        let outcome = vm
            .run_traced(58, &mut |trace| {
                let code = trace.before.registers.code_pointer;
                if let Some(read) = trace.input {
                    read_sites.push((code, read));
                }
                if code == 43 {
                    assert_eq!(trace.decoded, Some(b'p'));
                    assert_eq!(trace.after.registers.accumulator, saved);
                }
                if code == 55 {
                    assert_eq!(trace.decoded, Some(b'*'));
                    assert_eq!(
                        trace.before.registers.data_pointer,
                        FIRST_TARGET
                    );
                    assert_eq!(
                        trace.memory_reads.data.map(|read| read.value),
                        Some(saved)
                    );
                    assert_eq!(trace.after.registers.accumulator, reloaded);
                    saved_before_reload = Some(saved);
                }
                if let Some(byte) = trace.output {
                    outputs.push((code, byte));
                }
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 58,
        });
        assert_eq!(saved_before_reload, Some(saved));
        assert_eq!(vm.memory_word(FIRST_TARGET), Ok(reloaded));
        assert_eq!(read_sites, [
            (
                39,
                stream
                    .first()
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
            (
                47,
                stream
                    .get(1)
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
        ]);
        assert_eq!(outputs, [(51, second_low), (56, derived_first)]);
        assert_eq!(vm.output(), &[second_low, derived_first]);
        assert_eq!(vm.input_consumed(), stream.len().min(2));
    }
    Ok(())
}
