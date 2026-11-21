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
//   - Normative signed-byte conversion followed by real guest state folding.
// - Must-Not:
//   - Treat an encoded M96 word as signed C32 or an EOF checksum compiler.
// - Allows:
//   - Inputs: all 256 signed byte classes plus true EOF, and unread suffix.
//   - Outputs: real input, both conversion writes, final fold and exact output.
//   - Side effects: isolated 82-step profile VM executions only.
// - Split-When:
//   - A general physical typed-C32 arithmetic linker replaces this probe.
// - Merge-When:
//   - Whole source-C checksum is independently VM-verified.
// - Summary:
//   - Distinguishes full converted state from lossy post-output folding.

//! A reached third physical crazy write after correct signed C23 byte output.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;

use malbolge::{
    ProfileMachine, ProfileRegisters, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, historical_profile,
};

const ROTATED: u32 = 7_138_732;
const NEXT_SEED: u32 = 121;
const FOLD_SEED: u32 = 157;
const UNTOUCHED_POINTER: u32 = 7_174_404;

// Independent trit table, not the production profile crazy primitive.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "independent fixed-width 15-trit arithmetic oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut place = 1;
    for _ in 0..15 {
        result +=
            TABLE[(data % 3) as usize][(accumulator % 3) as usize] * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "exact guest effect and 257-class state parity assertions"
)]
fn signed_c23_conversion_preserves_state_through_post_output_guest_fold()
-> Result<(), String> {
    let profile = current_profile();
    let source =
        layout::build_c23_signed_output_with_post_conversion_fold_source(
            profile,
        )
        .map_err(|error| format!("{error:?}"))?;
    let original = layout::build_c23_nine_rotated_signed_output_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(source.len(), 91);
    assert_eq!(&source[89..], b"Iy");
    assert_eq!(source[81], 94);
    assert_eq!(layout::admit_c23_probe_graphical_source(&source), Ok(()));
    assert_eq!(
        layout::build_c23_signed_output_with_post_conversion_fold_source(
            historical_profile(),
        ),
        Err(layout::C23OperandProbeSourceError::UnsupportedProfile)
    );
    assert_eq!(
        source
            .iter()
            .zip(&original)
            .enumerate()
            .filter(|(_, (after, before))| after != before)
            .map(|(index, _)| index)
            .collect::<Vec<_>>(),
        vec![80]
    );
    assert_eq!(
        decode_profile_instruction(u32::from(source[80]), 80),
        Some(b'p')
    );

    let loaded = ProfileMachine::from_source(profile, &source, vec![])
        .map_err(|error| error.to_string())?;
    assert_eq!(loaded.memory_word(96), Ok(NEXT_SEED));
    assert_eq!(loaded.memory_word(98), Ok(FOLD_SEED));
    assert_eq!(loaded.memory_word(97), Ok(UNTOUCHED_POINTER));
    let mut all_converted = BTreeSet::new();
    let mut all_folded = BTreeSet::new();
    let all_inputs = (0u8..=255).map(Some).chain(std::iter::once(None));
    for second in all_inputs {
        let raw = second.map_or(profile.eof_word(), u32::from);
        let converted = scalar_crazy(NEXT_SEED, scalar_crazy(ROTATED, raw));
        assert_eq!(converted % 256, u32::from(second.unwrap_or(255)));
        _ = all_converted.insert(converted);
        _ = all_folded.insert(scalar_crazy(FOLD_SEED, converted));
    }
    // Byte 0xff and true EOF emit the same low byte, but require different
    // persistent guest state; a byte-only approximation loses source meaning.
    let high = scalar_crazy(NEXT_SEED, scalar_crazy(ROTATED, 255));
    let eof =
        scalar_crazy(NEXT_SEED, scalar_crazy(ROTATED, profile.eof_word()));
    assert_eq!((high % 256, eof % 256), (255, 255));
    assert_ne!(high, eof);
    let eof_folded = scalar_crazy(FOLD_SEED, eof);
    assert_eq!(eof_folded, 7_112_573);
    assert!((0..=255).all(|byte| {
        let converted = scalar_crazy(NEXT_SEED, scalar_crazy(ROTATED, byte));
        scalar_crazy(FOLD_SEED, converted) != eof_folded
    }));
    // Pin independent algebra for all 257 classes; run a finite set of
    // distinct input/EOF cases on the costly 14M-word normative guest VM.
    for second in [
        None,
        Some(0),
        Some(1),
        Some(2),
        Some(0x7f),
        Some(0x80),
        Some(0xfe),
        Some(0xff),
    ] {
        let mut input = vec![0x5a];
        if let Some(byte) = second {
            input.extend_from_slice(&[byte, 0x39]);
        }
        let raw = second.map_or(profile.eof_word(), u32::from);
        let after_first = scalar_crazy(ROTATED, raw);
        let converted = scalar_crazy(NEXT_SEED, after_first);
        let folded = scalar_crazy(FOLD_SEED, converted);
        let expected = second.unwrap_or(0xff);
        let mut vm = ProfileMachine::from_state(
            profile,
            loaded.memory().to_vec(),
            input,
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace = Vec::new();
        let outcome = vm
            .run_traced(82, &mut |step| trace.push(*step))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 82,
        });
        assert_eq!(trace.len(), 82);
        assert_eq!(trace[37].input, Some(TraceInput::Byte(0x5a)));
        assert_eq!(
            trace[66].input,
            Some(second.map_or(TraceInput::EndOfInput, TraceInput::Byte))
        );
        for (position, address, before, after) in [
            (77, 95, ROTATED, after_first),
            (78, 96, NEXT_SEED, converted),
            (80, 98, FOLD_SEED, folded),
        ] {
            let step = &trace[position];
            assert_eq!(step.decoded, Some(b'p'));
            assert_eq!(step.before.registers.data_pointer, address);
            assert_eq!(
                step.memory_reads
                    .data
                    .map(|read| (read.address, read.value)),
                Some((address, before))
            );
            assert_eq!(step.after.registers.accumulator, after);
            assert_eq!(
                step.memory_delta.data.map(|delta| {
                    (delta.address, delta.before, delta.after)
                }),
                (before != after).then_some((address, before, after))
            );
            assert_eq!(vm.memory_word(address), Ok(after));
        }
        assert_eq!(trace[79].output, Some(expected));
        assert_eq!(trace[80].before.registers.accumulator, converted);
        assert_eq!(trace[81].decoded, Some(b'v'));
        assert_eq!(vm.output(), &[expected]);
        assert_eq!(vm.memory_word(97), Ok(UNTOUCHED_POINTER));
        assert_eq!(vm.input_consumed(), 1 + usize::from(second.is_some()));
    }
    // The converted physical word in M96 retains byte-plus-EOF state, but
    // the new M98 crazy fold cannot replace signed C23 scalar storage.
    assert_eq!(all_converted.len(), 257);
    assert_eq!(all_folded.len(), 118);
    Ok(())
}
