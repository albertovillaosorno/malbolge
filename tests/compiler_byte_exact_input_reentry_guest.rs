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
//   - Normative VM proof of data pointer reentry into exact raw-byte state.
// - Must-Not:
//   - Claim a dynamic code branch, signed C32 EOF or completed checksum.
// - Allows:
//   - Inputs: source-loaded current N15 and 257 raw input classes.
//   - Outputs: exact two-p write proof and two physical j operand reads.
//   - Side effects: isolated in-memory profile VMs only.
// - Split-When:
//   - Genuine source-linked dynamic C control consumes exact raw state.
// - Merge-When:
//   - General guest physical state reentry verification owns this proof.
// - Summary:
//   - Last j reads the input-overwritten cell, not virgin loader memory.
//
//! Real guest control of D from an exact raw-byte written word.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::iter::once;

use malbolge::{
    ProfileMachine, ProfileRegisters, ProfileStepTrace, RunOutcome,
    Termination, TraceInput, current_profile, decode_profile_instruction,
    historical_profile,
};

const GUEST_EOF: u32 = 14_348_906;
const IDENTITY_OPERAND: u32 = 7_174_453;
const LAST_STEP: usize = 25;

type GuestDataRead = (u32, u32, u32);

fn reached_reentry_read(step: &ProfileStepTrace) -> Option<GuestDataRead> {
    let code = step.before.registers.code_pointer;
    let destination = match code {
        22 => 78,
        23 => 73,
        _ => return None,
    };
    assert_eq!(step.decoded, Some(b'j'), "reached j");
    assert_eq!(step.before.registers.data_pointer, destination, "read D");
    let read = step.memory_reads.data;
    assert_eq!(
        read.map(|word| word.address),
        Some(destination),
        "j operand"
    );
    let word = read.map(|value| value.value);
    assert_eq!(
        step.after.registers.data_pointer,
        word.map_or(0, |value| value
            .saturating_add(1)
            .rem_euclid(GUEST_EOF.saturating_add(1))),
        "j new D"
    );
    word.map(|value| (code, destination, value))
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "fixed 27-cell physical source and loader addresses"
)]
fn reentry_source_refuses_wrong_profile_and_has_frozen_geometry()
-> Result<(), String> {
    assert_eq!(
        layout::build_byte_exact_input_reentry_source(historical_profile()),
        Err(layout::ByteExactInputStoreError::UnsupportedProfile),
    );
    let plan = layout::build_byte_exact_input_reentry_source(current_profile())
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.store.source.as_slice(), b"DCBA@?>=<;:98hx/v-210/po9%H");
    assert_eq!(plan.store.source.len(), 27);
    assert_eq!(
        (
            plan.store.input_code_address,
            plan.store.first_store_code_address,
            plan.store.exact_store_code_address
        ),
        (13, 15, 17)
    );
    assert_eq!(
        (plan.store.first_data_address, plan.store.exact_data_address),
        (121, 73)
    );
    assert_eq!(
        (
            plan.reset_code_address,
            plan.input_reentry_code_address,
            plan.reset_data_address,
            plan.reset_loader_word,
            plan.reset_padding
        ),
        (22, 23, 78, 72, 4)
    );
    let source_ops = b"ooooooooooooo/jpjpoooojjv";
    for (index, expected) in source_ops.iter().copied().enumerate() {
        let byte = plan
            .store
            .source
            .get(index)
            .ok_or_else(|| format!("missing physical source at {index}"))?;
        let address =
            u32::try_from(index).map_err(|error| error.to_string())?;
        assert_eq!(
            decode_profile_instruction(u32::from(*byte), address),
            Some(expected)
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "exhaust all raw input classes through normative guest j and p"
)]
fn exact_input_state_is_reentered_by_guest_for_all_257_classes()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_byte_exact_input_reentry_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let baseline =
        ProfileMachine::from_source(profile, &plan.store.source, vec![])
            .map_err(|error| error.to_string())?;
    assert_eq!(baseline.memory_word(121), Ok(IDENTITY_OPERAND));
    assert_eq!(baseline.memory_word(73), Ok(IDENTITY_OPERAND));
    assert_eq!(baseline.memory_word(78), Ok(72));
    let loaded = baseline.memory().to_vec();
    let inputs = once(Vec::new())
        .chain((u8::MIN..=u8::MAX).map(|byte| vec![byte]))
        .chain([vec![0u8, 255u8], vec![255u8, 0u8]]);
    let mut seen = 0u32;
    for input in inputs {
        let raw = input.first().copied().map_or(GUEST_EOF, u32::from);
        let mut guest = ProfileMachine::from_state(
            profile,
            loaded.clone(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut reads = Vec::new();
        let mut input_events = Vec::new();
        let mut store_events = Vec::new();
        let result = guest
            .run_traced(LAST_STEP, &mut |step| {
                if let Some(read) = reached_reentry_read(step) {
                    reads.push(read);
                }
                if let Some(read) = step.input {
                    input_events
                        .push((step.before.registers.code_pointer, read));
                }
                if matches!(step.before.registers.code_pointer, 15 | 17) {
                    assert_eq!(step.decoded, Some(b'p'), "guest p decoded");
                    store_events.push((
                        step.before.registers.data_pointer,
                        step.after.registers.accumulator,
                    ));
                }
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: LAST_STEP,
        });
        assert_eq!(input_events, vec![(
            13,
            input
                .first()
                .copied()
                .map_or(TraceInput::EndOfInput, TraceInput::Byte)
        )]);
        assert_eq!(reads, vec![(22, 78, 72), (23, 73, raw)]);
        assert_eq!(store_events.first().map(|event| event.0), Some(121));
        assert_eq!(store_events.get(1), Some(&(73, raw)));
        assert_eq!(guest.memory_word(73), Ok(raw));
        assert_eq!(
            guest.registers().data_pointer,
            raw.saturating_add(1).rem_euclid(profile.memory_words())
        );
        assert_eq!(guest.input_consumed(), input.len().min(1));
        assert!(guest.output().is_empty());
        seen = seen.saturating_add(1);
    }
    assert_eq!(seen, 259);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source p-to-o mutation demonstrates state-dependent j refusal"
)]
fn replacing_exact_store_with_noop_breaks_raw_input_reentry()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_byte_exact_input_reentry_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let mut source = plan.store.source;
    let no_op = (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), 17) == Some(b'o')
        })
        .ok_or_else(|| String::from("missing graphical inert replacement"))?;
    *source
        .get_mut(17)
        .ok_or_else(|| String::from("missing p cell"))? = no_op;
    let mut guest = ProfileMachine::from_source(profile, &source, vec![0])
        .map_err(|error| error.to_string())?;
    assert_eq!(
        guest.run(LAST_STEP).map_err(|error| error.to_string())?,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: LAST_STEP
        }
    );
    assert_eq!(guest.memory_word(73), Ok(IDENTITY_OPERAND));
    assert_eq!(
        guest.registers().data_pointer,
        IDENTITY_OPERAND.saturating_add(1)
    );
    assert_ne!(guest.registers().data_pointer, 1);
    Ok(())
}
