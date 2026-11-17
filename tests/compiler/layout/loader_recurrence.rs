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
//   - Exhaustive six-phase loader recurrence and independent VM checks.
// - Must-Not:
//   - Treat mathematical operands as a runnable C EOF compiler.
// - Allows:
//   - Inputs: printable source suffixes and canonical target profiles.
//   - Outputs: scalar recurrence and actual guest memory agreement.
//   - Side effects: bounded normative VM replays only.
// - Split-When:
//   - General guest-memory initialization supersedes loader-tail selection.
// - Merge-When:
//   - Expanded-memory control planning receives a complete proof engine.
// - Summary:
//   - Guards the six-phase shortcut used by forward jumps and relocations.

use super::*;

// Independent scalar ternary operation: no production crazy helper or
// recurrence period reduction is used for these twelve reference words.
#[expect(
    clippy::integer_division_remainder_used,
    reason = "independent base-three scalar reference"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32, trits: u8) -> u32 {
    let mut result = 0u32;
    let mut place = 1u32;
    for _ in 0..trits {
        let (data_trit, accumulator_trit) = (data % 3, accumulator % 3);
        let trit: u32 = match (data_trit, accumulator_trit) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        result = result.saturating_add(trit.saturating_mul(place));
        data /= 3;
        accumulator /= 3;
        place = place.saturating_mul(3);
    }
    result
}

fn reference_loader_words(seed: [u8; 2], trits: u8) -> [u32; 12] {
    let (mut previous, mut latest) = (u32::from(seed[0]), u32::from(seed[1]));
    let mut words = [0u32; 12];
    for word in &mut words {
        let next = scalar_crazy(previous, latest, trits);
        *word = next;
        previous = latest;
        latest = next;
    }
    words
}

#[expect(
    clippy::integer_division_remainder_used,
    reason = "loader control words have a proven six-phase recurrence"
)]
fn verify_seed_phase(
    profile: &malbolge::ProfileDescriptor,
    seed: [u8; 2],
    memory_words: usize,
) -> Result<(), String> {
    let expected = reference_loader_words(seed, profile.word_trits());
    if expected.get(..6) != expected.get(6..) {
        return Err(format!(
            "scalar recurrence period exceeds six for {seed:?}"
        ));
    }
    for (offset, &word) in expected.iter().enumerate() {
        let actual = layout::unwritten_loader_word(
            &seed,
            offset.saturating_add(2),
            profile,
        )
        .map_err(|error| format!("loader proof: {error:?}"))?;
        if actual != word {
            return Err(format!("near loader mismatch at {offset}, {seed:?}"));
        }
    }
    for offset in [23, 100, 1_024, memory_words.saturating_sub(3)] {
        let word = expected.get(offset % 6).ok_or("missing scalar phase")?;
        let actual = layout::unwritten_loader_word(
            &seed,
            offset.saturating_add(2),
            profile,
        )
        .map_err(|error| format!("far loader proof: {error:?}"))?;
        if actual != *word {
            return Err(format!("far loader mismatch at {offset}, {seed:?}"));
        }
    }
    Ok(())
}

#[test]
fn every_printable_loader_seed_obeys_exact_six_phase_recurrence()
-> Result<(), String> {
    // Exhaustive over all 94^2 graphical tails, even when the tail does not
    // decode as a loadable source at one particular physical position.
    for profile in [current_profile(), historical_profile()] {
        let memory_words = usize::try_from(profile.memory_words())
            .map_err(|error| error.to_string())?;
        for first in 33..=126u8 {
            for second in 33..=126u8 {
                verify_seed_phase(profile, [first, second], memory_words)?;
            }
        }
        if layout::unwritten_loader_word(b"Iy", 1, profile)
            != Err(LinearLayoutError::UnsafeDataPlacement)
            || layout::unwritten_loader_word(b"Iy", memory_words, profile)
                != Err(LinearLayoutError::UnsafeDataPlacement)
        {
            return Err(String::from("out-of-bounds loader operand admitted"));
        }
    }
    Ok(())
}

fn loadable_seed(
    profile: &malbolge::ProfileDescriptor,
    position: u32,
) -> Result<u8, String> {
    (33..=126u8)
        .find(|&byte| {
            let operation =
                decode_profile_instruction(u32::from(byte), position);
            matches!(operation, Some(b'j' | b'i' | b'*' | b'p' | b'v' | b'o'))
                || operation == Some(profile.input_instruction())
                || operation == Some(profile.output_instruction())
        })
        .ok_or_else(|| format!("no source-loadable graphical phase {position}"))
}

#[expect(
    clippy::integer_division_remainder_used,
    reason = "loader phase is exactly offset modulo six"
)]
fn check_source_loaded_guest(
    profile: &'static malbolge::ProfileDescriptor,
    length: usize,
) -> Result<(), String> {
    let mut operations = vec![LinearOpcode::NoOperation; length];
    *operations
        .get_mut(length.saturating_sub(3))
        .ok_or("missing halt cell")? = LinearOpcode::Halt;
    for position in [length.saturating_sub(2), length.saturating_sub(1)] {
        let address =
            u32::try_from(position).map_err(|error| error.to_string())?;
        *operations.get_mut(position).ok_or("missing seed cell")? =
            LinearOpcode::SkippedDataByte {
                byte: u32::from(loadable_seed(profile, address)?),
            };
    }
    let layout = encode_linear_layout(profile, &operations)
        .map_err(|error| format!("source-tail layout: {error:?}"))?;
    let source = layout.source();
    let [.., first, second] = source else {
        return Err(String::from("missing two-byte loader seed"));
    };
    let independent =
        reference_loader_words([*first, *second], profile.word_trits());
    let mut vm = ProfileMachine::from_source(profile, source, vec![])
        .map_err(|error| format!("guest loader: {error:?}"))?;
    let last_offset = usize::try_from(profile.memory_words())
        .map_err(|error| error.to_string())?
        .saturating_sub(length)
        .saturating_sub(1);
    for offset in [0, 1, 2, 5, 6, 7, 23, 100, 1_024, last_offset] {
        let address = length.saturating_add(offset);
        let expected = layout::unwritten_loader_word(source, address, profile)
            .map_err(|error| format!("control-word proof: {error:?}"))?;
        let scalar =
            independent.get(offset % 6).ok_or("missing scalar phase")?;
        let actual = vm
            .memory_word(
                u32::try_from(address).map_err(|error| error.to_string())?,
            )
            .map_err(|error| format!("guest memory: {error:?}"))?;
        if expected != *scalar || actual != *scalar {
            return Err(format!(
                "VM/control mismatch at {address}, length={length}, profile={}",
                profile.id()
            ));
        }
    }
    if vm.run(length)
        != Ok(RunOutcome::Terminated {
            reason: malbolge::Termination::HaltInstruction,
            steps: length.saturating_sub(2),
        })
    {
        return Err(String::from("source-loaded guest did not halt"));
    }
    Ok(())
}

#[test]
fn source_loaded_guest_memory_matches_far_recurrence_words()
-> Result<(), String> {
    for profile in [current_profile(), historical_profile()] {
        for length in [91usize, 118] {
            check_source_loaded_guest(profile, length)?;
        }
    }
    Ok(())
}
