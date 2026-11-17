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
//   - Source-position feasibility of the simple C23 EOF rotation reset.
// - Must-Not:
//   - Claim that nine guest writes or dynamic C EOF conversion are implemented.
// - Allows:
//   - Inputs: the complete phase-compatible 122-address loader-tail class.
//   - Outputs: positional refusals and a traced N15 relocation trap.
//   - Side effects: isolated, bounded normative VM execution.
// - Split-When:
//   - More general guest pointer synthesis escapes this finite geometry.
// - Merge-When:
//   - The backend emits a fully verified live signed EOF conversion.
// - Summary:
//   - An algebraic self-reset at D=122 cannot use an admitted two-cell tail.
// - Description:
//   - Checks all shorter seed lengths and an independent actual j-chain.
// - Usage:
//   - `cargo test --test malbolge_layout eof_reset_geometry_tests`.
// - Defaults:
//   - Current N15 profile, exact two-p nine-rotate loader-tail plan.

//! Source validity rules out a seemingly cheap nine-rotation guest loop.
//!
//! The two conversion operands are a rotated loader word and its untouched
//! adjacent word 121. Placing the first at D=122 makes `j` on the second
//! reset D to 122 after every `*`. However the position-sensitive source
//! decoder rejects every phase-compatible terminal seed below D=122.
//! A real guest using the accepted 91-cell seed demonstrates that an
//! untouched-loader-only j-chain instead becomes trapped at D=158.

use malbolge::{
    ProfileMachine, RunOutcome, Termination, current_profile,
    decode_profile_instruction, profile_rotate,
};

use super::layout;

const FIRST_OPERAND: u32 = 7_138_732;
const SECOND_OPERAND: u32 = 121;
const FIRST_DATA_ADDRESS: u32 = 122;
const ROTATIONS: u8 = 9;
const VALID_TAIL_FIRST: &[u8; 4] = b"HIKL";

#[test]
fn every_phase_compatible_short_reset_seed_is_unloadable() {
    let profile = current_profile();
    let mut checked = 0usize;
    for source_length in (4usize..=118).step_by(6) {
        // These are exactly the source lengths with phase-four D=122.
        // The four source-tail candidates were enumerated independently
        // over all 94*94 seeds and 15 rotations for 257 possible inputs.
        for &first in VALID_TAIL_FIRST {
            let decoded_first = decode_profile_instruction(
                u32::from(first),
                u32::try_from(source_length - 2).unwrap_or(u32::MAX),
            );
            let decoded_second = decode_profile_instruction(
                u32::from(b'y'),
                u32::try_from(source_length - 1).unwrap_or(u32::MAX),
            );
            assert!(
                !matches!(
                    decoded_first,
                    Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                ) || !matches!(
                    decoded_second,
                    Some(b'j' | b'i' | b'*' | b'p' | b'<' | b'/' | b'v' | b'o')
                ),
                "source length {source_length} unexpectedly accepts {first}y"
            );
            checked += 1;
        }
        assert_eq!(
            layout::select_rotated_loader_seed(
                profile,
                source_length,
                FIRST_DATA_ADDRESS,
                ROTATIONS,
                [FIRST_OPERAND, SECOND_OPERAND],
            ),
            Err(layout::LoaderSeedSelectionError::NoLoadableSeed),
            "source length {source_length} unexpectedly places reset pair"
        );
    }
    assert_eq!(checked, 80);
    // The accepted length-91 seed places the same pair at D=95 instead:
    // after a rotate its adjacent j operand 121 jumps to D=122, not 95.
    assert_eq!(
        layout::select_rotated_loader_seed(profile, 91, 95, ROTATIONS, [
            FIRST_OPERAND,
            SECOND_OPERAND
        ]),
        Ok(*b"Iy"),
    );
}

fn source_with_untouched_loader_relocations() -> Result<Vec<u8>, String> {
    let mut source = Vec::with_capacity(91);
    for position in 0..89u32 {
        let decoded = match position {
            40 | 42 | 43 | 44 => b'j',
            41 => b'*',
            88 => b'v',
            _ => b'o',
        };
        let cell = (33..=126u8)
            .find(|cell| {
                decode_profile_instruction(u32::from(*cell), position)
                    == Some(decoded)
            })
            .ok_or_else(|| format!("cannot encode {decoded} at {position}"))?;
        source.push(cell);
    }
    source.extend_from_slice(b"Iy");
    Ok(source)
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    reason = "exact guest transition and pointer witnesses need assertions"
)]
fn real_guest_untouched_loader_j_chain_cannot_reenter_rotated_operand()
-> Result<(), String> {
    let profile = current_profile();
    let source = source_with_untouched_loader_relocations()?;
    let mut vm = ProfileMachine::from_source(profile, &source, Vec::new())
        .map_err(|error| error.to_string())?;
    assert_eq!(vm.memory_word(95), Ok(7_174_404));
    assert_eq!(vm.memory_word(96), Ok(SECOND_OPERAND));
    assert_eq!(vm.memory_word(122), Ok(157));
    assert_eq!(vm.memory_word(158), Ok(157));
    let mut traces = Vec::new();
    let run = vm
        .run_traced(89, &mut |trace| traces.push(*trace))
        .map_err(|error| error.to_string())?;
    assert_eq!(run, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 89,
    });
    assert_eq!(traces.len(), 89);
    for (step, address, expected_data) in [
        (40usize, 40u32, 40u32),
        (41, 41, 95),
        (42, 42, 96),
        (43, 43, 122),
        (44, 44, 158),
        (45, 45, 158),
    ] {
        let trace = traces.get(step).ok_or("missing guest transition")?;
        assert_eq!(trace.before.registers.code_pointer, address);
        assert_eq!(trace.before.registers.data_pointer, expected_data);
    }
    assert_eq!(traces.get(41).map(|trace| trace.decoded), Some(Some(b'*')));
    assert!(
        traces
            .get(42..45)
            .ok_or("missing reset relocation steps")?
            .iter()
            .all(|trace| trace.decoded == Some(b'j'))
    );
    assert_eq!(
        vm.memory_word(95),
        Ok(profile_rotate(7_174_404, profile.word_modulus())),
    );
    assert_ne!(vm.memory_word(95), Ok(FIRST_OPERAND));
    assert_eq!(vm.memory_word(96), Ok(SECOND_OPERAND));
    assert_eq!(vm.input_consumed(), 0);
    assert!(vm.output().is_empty());
    Ok(())
}
