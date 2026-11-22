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
//   - Source-loaded indexed loader reads after an exact input-state write.
// - Must-Not:
//   - Claim a C23 odd/even branch, a signed EOF loop or checksum lowering.
// - Allows:
//   - Inputs: 128 high bytes, two aliases, true EOF, immutable loader and two
//     live writes.
//   - Outputs: exact j trace and finite parity/address-alias boundaries.
//   - Side effects: isolated in-memory N15 execution only.
// - Split-When:
//   - An executable source-linked arithmetic/control linker uses this ROM.
// - Merge-When:
//   - A verified general dynamic guest table-indexing implementation exists.
// - Summary:
//   - The six-phase loader distinguishes high-byte parity, unless aliased.

//! Guest-loaded data-indexed ROM evidence, not a dynamic C arithmetic linker.

use malbolge::{
    ProfileMachine, ProfileMemoryRead, ProfileRegisters, ProfileStepTrace,
    RunOutcome, TraceInput, current_profile, decode_profile_instruction,
};

// The checked two-p byte-exact reentry fixture, with only its C24 halt
// encoded as j. C25/C26 are the same non-executed loader tail as before.
const SOURCE: &[u8; 27] = b"DCBA@?>=<;:98hx/v-210/pon%H";
const GUEST_EOF: u32 = 14_348_906;
const ONE_TRITS: u32 = 7_174_453;
const GUEST_STEPS: usize = 25;
const SIX_PHASE_ROM: [u32; 6] = [7_174_489, 36, 7_174_489, 72, 7_174_453, 72];

// Deliberately separate from the normative VM's precomputed crazy table.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "small independent base-three recurrence witness"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut result = 0;
    let mut place = 1;
    for _ in 0u8..15u8 {
        let (left, right) = (data % 3, accumulator % 3);
        let digit = match (left, right) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        result += digit * place;
        place *= 3;
        data /= 3;
        accumulator /= 3;
    }
    result
}

#[test]
#[expect(
    clippy::integer_division_remainder_used,
    reason = "six-cycle indexing is the independently checked theorem"
)]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    reason = "two independent recurrence cycles and source-loaded VM checks"
)]
fn original_graphical_loader_has_the_exact_six_phase_rom() -> Result<(), String>
{
    let mut older = u32::from(SOURCE[25]);
    let mut previous = u32::from(SOURCE[26]);
    assert_eq!((older, previous), (37, 72));
    for expected in SIX_PHASE_ROM {
        let next = scalar_crazy(older, previous);
        assert_eq!(next, expected);
        older = previous;
        previous = next;
    }
    // The generated sequence is six-periodic after the first recurrence;
    // the initial graphical tail itself is not required to be periodic.
    for expected in SIX_PHASE_ROM {
        let next = scalar_crazy(older, previous);
        assert_eq!(next, expected);
        older = previous;
        previous = next;
    }
    assert_eq!(
        decode_profile_instruction(u32::from(SOURCE[24]), 24),
        Some(b'j')
    );
    let guest = ProfileMachine::from_source(current_profile(), SOURCE, vec![])
        .map_err(|error| error.to_string())?;
    for address in 27u32..=256u32 {
        let offset = usize::try_from((address - 27) % 6)
            .map_err(|error| error.to_string())?;
        let expected =
            SIX_PHASE_ROM.get(offset).copied().ok_or("missing phase")?;
        assert_eq!(guest.memory_word(address), Ok(expected));
    }
    assert_eq!(guest.memory_word(73), Ok(ONE_TRITS));
    assert_eq!(guest.memory_word(121), Ok(ONE_TRITS));
    assert_eq!(guest.memory_word(78), Ok(72));
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "131 exact guest input/ROM probes and live write conflicts"
)]
fn real_guest_high_byte_parity_addresses_and_alias_exceptions()
-> Result<(), String> {
    let profile = current_profile();
    let baseline = ProfileMachine::from_source(profile, SOURCE, vec![])
        .map_err(|error| error.to_string())?;
    let virgin = baseline.memory().to_vec();
    let mut cases = vec![vec![], vec![72], vec![120]];
    cases.extend((128u8..=u8::MAX).map(|byte| vec![byte]));
    let mut high_bytes: usize = 0;
    for input in cases {
        let raw = input.first().copied().map_or(GUEST_EOF, u32::from);
        let mut guest = ProfileMachine::from_state(
            profile,
            virgin.clone(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut trace: Vec<ProfileStepTrace> = Vec::new();
        assert_eq!(
            guest
                .run_traced(GUEST_STEPS, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?,
            RunOutcome::BudgetExhausted { steps: GUEST_STEPS }
        );
        assert_eq!(trace.len(), GUEST_STEPS);
        let read = trace.get(13).ok_or("missing physical input")?;
        assert_eq!(read.decoded, Some(b'/'));
        assert_eq!(
            read.input,
            Some(
                input
                    .first()
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte,)
            )
        );
        let first_store = trace.get(15).ok_or("missing first physical p")?;
        assert_eq!(first_store.decoded, Some(b'p'));
        assert_eq!(
            first_store.memory_reads.data,
            Some(ProfileMemoryRead {
                address: 121,
                value: ONE_TRITS,
            })
        );
        let first_result = scalar_crazy(ONE_TRITS, raw);
        assert_eq!(first_store.after.registers.accumulator, first_result);
        assert_eq!(guest.memory_word(121), Ok(first_result));
        let store = trace.get(17).ok_or("missing physical exact p")?;
        assert_eq!(store.decoded, Some(b'p'));
        assert_eq!(store.before.registers.data_pointer, 73);
        assert_eq!(store.after.registers.accumulator, raw);
        assert_eq!(guest.memory_word(73), Ok(raw));
        let reentry = trace.get(23).ok_or("missing input-dependent j")?;
        assert_eq!(reentry.decoded, Some(b'j'));
        assert_eq!(
            reentry.memory_reads.data,
            Some(ProfileMemoryRead { address: 73, value: raw })
        );
        let expected_index = (raw + 1) % profile.memory_words();
        let probe = trace.get(24).ok_or("missing ROM probe")?;
        assert_eq!(probe.decoded, Some(b'j'));
        assert_eq!(probe.before.registers.data_pointer, expected_index);
        let observed =
            probe.memory_reads.data.ok_or("missing j operand read")?;
        assert_eq!(observed.address, expected_index);
        assert_eq!(
            probe.after.registers.data_pointer,
            (observed.value + 1) % profile.memory_words()
        );
        assert_eq!(guest.input_consumed(), input.len());
        assert_eq!(guest.output(), &[]);
        if let Some(byte) = input.first().copied() {
            if byte >= 128 {
                high_bytes = high_bytes.saturating_add(1);
                // At M129..M256 the source has no code/data write aliases.
                let recurrence_index = usize::from(byte - 26) % 6;
                let expected = SIX_PHASE_ROM
                    .get(recurrence_index)
                    .copied()
                    .ok_or("missing high-byte recurrence")?;
                assert_eq!(observed.value, expected);
                assert_eq!(observed.value > 1_000_000, byte % 2 == 0);
            }
            if byte == 72 {
                // M73 is the actual input store, NOT the virgin ROM value.
                assert_eq!(observed.value, 72);
                assert_ne!(Some(observed.value), virgin.get(73).copied());
            }
            if byte == 120 {
                // M121 is the first p store; it is also indexed by byte 120.
                assert_ne!(Some(observed.value), virgin.get(121).copied());
                assert_eq!(
                    observed.value,
                    guest.memory_word(121).map_err(|error| error.to_string())?
                );
            }
        }
    }
    assert_eq!(high_bytes, 128);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::integer_division_remainder_used,
    reason = "one mutation shows reached j and exact modulo-six routing"
)]
fn replacing_indexed_j_with_inert_code_removes_parity_routing()
-> Result<(), String> {
    let mut source = *SOURCE;
    source[24] = (33u8..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), 24) == Some(b'o')
        })
        .ok_or("no graphical inert code cell")?;
    for byte in [128u8, 129] {
        let mut guest =
            ProfileMachine::from_source(current_profile(), &source, vec![byte])
                .map_err(|error| error.to_string())?;
        assert_eq!(
            guest.run(GUEST_STEPS).map_err(|error| error.to_string())?,
            RunOutcome::BudgetExhausted { steps: GUEST_STEPS }
        );
        assert_eq!(guest.registers().data_pointer, u32::from(byte) + 2);
        let ring_index = usize::from(byte - 26) % 6;
        assert_ne!(
            guest.registers().data_pointer,
            SIX_PHASE_ROM
                .get(ring_index)
                .copied()
                .ok_or("missing ring phase")?
                + 1
        );
    }
    Ok(())
}
