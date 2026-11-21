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
//   - Independent full-byte physical VM proof of two-stage input identity.
// - Must-Not:
//   - Claim signed C32 EOF normalization, arithmetic or an executable C loop.
// - Allows:
//   - Inputs: real graphical N15 source, 256 byte values and true EOF.
//   - Outputs: two exact guest data-write traces and lossless raw state.
//   - Side effects: in-memory bounded guest VMs only.
// - Split-When:
//   - A source-linked C23 input state verifier covers this whole contract.
// - Merge-When:
//   - Executable guest input lowering consumes this canonical raw state.
// - Summary:
//   - Two source-loaded p writes physically recover the raw input word.
//
//! A physically executed byte-exact input store, not a C23 checksum.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::iter::once;

use malbolge::{
    ProfileMachine, ProfileRegisters, ProfileStepTrace, RunOutcome,
    Termination, TraceInput, current_profile, decode_profile_instruction,
    historical_profile,
};

const ONE_TRIT_WORD: u32 = 7_174_453;
const RAW_EOF: u32 = 14_348_906;
type ObservedDataWrite = (u32, u32, u32);

// Independent scalar truth table: crazy(one,x) swaps 0 and 1, fixes 2.
#[test]
fn two_ones_crazy_steps_are_a_full_width_involution() {
    let first = [1u32, 0u32, 2u32];
    // Every digit maps back to itself under two such crazy operations.
    assert_eq!(
        first.map(|digit| match digit {
            0 => 1u32,
            1 => 0u32,
            2 => 2u32,
            _ => 3u32,
        }),
        [0u32, 1, 2]
    );
    let mut word: u32 = ONE_TRIT_WORD;
    let mut trits = Vec::new();
    for _ in 0u32..15u32 {
        trits.push(word.rem_euclid(3));
        word = word.div_euclid(3);
    }
    assert_eq!(trits, vec![1; 15]);
    assert_eq!(word, 0);
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "fixed graphical-source and exact phase assertions"
)]
fn source_refuses_noncurrent_profile_and_records_disjoint_exact_sites()
-> Result<(), String> {
    assert_eq!(
        layout::build_byte_exact_input_store_source(historical_profile()),
        Err(layout::ByteExactInputStoreError::UnsupportedProfile),
    );
    let plan = layout::build_byte_exact_input_store_source(current_profile())
        .map_err(|error| format!("{error:?}"))?;
    assert_eq!(plan.source.len(), 15);
    assert_eq!(plan.source.as_slice(), b"DCBA@?>n~5|3Ex6");
    assert_eq!(plan.source.get(13..), Some(b"x6".as_slice()));
    assert_eq!(
        (
            plan.input_code_address,
            plan.first_store_code_address,
            plan.exact_store_code_address
        ),
        (7, 9, 11)
    );
    assert_eq!(
        (plan.first_data_address, plan.exact_data_address),
        (127, 55)
    );
    assert_eq!(
        (plan.first_initial_word, plan.exact_initial_word),
        (ONE_TRIT_WORD, ONE_TRIT_WORD)
    );
    for (address, &byte) in plan.source.iter().take(13).enumerate() {
        let expected = match address {
            0..=6 => b'o',
            7 => b'/',
            8 | 10 => b'j',
            9 | 11 => b'p',
            12 => b'v',
            _ => return Err(format!("unexpected code address {address}")),
        };
        assert_eq!(
            decode_profile_instruction(
                u32::from(byte),
                u32::try_from(address).map_err(|error| error.to_string())?,
            ),
            Some(expected)
        );
    }
    Ok(())
}
// A reached p can be idempotent, so data read and A prove the physical
// attempted write even when the VM records no changed-cell delta.
fn observed_physical_store(
    step: &ProfileStepTrace,
) -> Option<ObservedDataWrite> {
    let address = step.before.registers.code_pointer;
    let target = match address {
        9 => 127,
        11 => 55,
        _ => return None,
    };
    assert_eq!(step.decoded, Some(b'p'), "reached physical store");
    assert_eq!(
        step.before.registers.data_pointer, target,
        "guest D address"
    );
    let read = step.memory_reads.data;
    assert_eq!(read.map(|value| value.address), Some(target), "p operand");
    let result = step.after.registers.accumulator;
    if let Some(delta) = step.memory_delta.data {
        assert_eq!(delta.address, target, "p data delta address");
        assert_eq!(
            Some(delta.before),
            read.map(|value| value.value),
            "p prior value"
        );
        assert_eq!(delta.after, result, "p changed value");
    } else {
        assert_eq!(
            read.map(|value| value.value),
            Some(result),
            "idempotent p value"
        );
    }
    Some((address, target, result))
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "257 independently executed guest traces at two physical writes"
)]
fn every_byte_and_true_eof_reaches_the_exact_second_physical_store()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_byte_exact_input_store_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let baseline =
        ProfileMachine::from_source(profile, &plan.source, Vec::new())
            .map_err(|error| error.to_string())?;
    assert_eq!(
        baseline.memory_word(plan.first_data_address),
        Ok(ONE_TRIT_WORD)
    );
    assert_eq!(
        baseline.memory_word(plan.exact_data_address),
        Ok(ONE_TRIT_WORD)
    );
    assert_eq!(baseline.memory_word(128), Ok(54));
    let original = baseline.memory().to_vec();

    // All 256 values, true EOF, and two unread-suffix controls. No input is
    // synthesized from C or substituted for actual VM `/` execution.
    let cases = once(Vec::new())
        .chain((u8::MIN..=u8::MAX).map(|byte| vec![byte]))
        .chain([vec![0u8, 255, 1], vec![255u8, 0, 1]]);
    let mut checked: u32 = 0;
    for input in cases {
        let input_word = input.first().copied().map_or(RAW_EOF, u32::from);
        let mut vm = ProfileMachine::from_state(
            profile,
            original.clone(),
            input.clone(),
            ProfileRegisters::default(),
        )
        .map_err(|error| error.to_string())?;
        let mut visited = Vec::new();
        let mut inputs = Vec::new();
        let mut writes = Vec::new();
        let result = vm
            .run_traced(13, &mut |step| {
                let address = step.before.registers.code_pointer;
                visited.push(address);
                if let Some(read) = step.input {
                    inputs.push((address, read));
                }
                if let Some(write) = observed_physical_store(step) {
                    writes.push(write);
                }
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(result, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 13
        });
        assert_eq!(visited, (0..13).collect::<Vec<_>>());
        assert_eq!(inputs, vec![(
            7,
            input
                .first()
                .copied()
                .map_or(TraceInput::EndOfInput, TraceInput::Byte)
        )]);
        assert_eq!(writes.len(), 2);
        assert_eq!(writes.get(1), Some(&(11, 55, input_word)));
        assert_eq!(vm.memory_word(55), Ok(input_word));
        assert_eq!(
            vm.memory_word(127),
            Ok(writes
                .first()
                .ok_or_else(|| String::from("missing first p"))?
                .2)
        );
        assert_eq!(vm.input_consumed(), input.len().min(1));
        assert!(vm.output().is_empty());
        checked += 1;
    }
    assert_eq!(checked, 259);
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "negative p mutation checks exact guest effects"
)]
fn removing_second_crazy_does_not_materialize_the_input_word()
-> Result<(), String> {
    let profile = current_profile();
    let plan = layout::build_byte_exact_input_store_source(profile)
        .map_err(|error| format!("{error:?}"))?;
    let mut changed = plan.source;
    let inert = (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), 11) == Some(b'o')
        })
        .ok_or_else(|| String::from("missing inert graphical byte"))?;
    *changed
        .get_mut(11)
        .ok_or_else(|| String::from("missing p site"))? = inert;
    let mut vm = ProfileMachine::from_source(profile, &changed, vec![0])
        .map_err(|error| error.to_string())?;
    assert_eq!(
        vm.run(13).map_err(|error| error.to_string())?,
        RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 13
        }
    );
    assert_eq!(vm.memory_word(55), Ok(ONE_TRIT_WORD));
    assert_ne!(vm.memory_word(55), Ok(0));
    assert_eq!(vm.input_consumed(), 1);
    Ok(())
}
