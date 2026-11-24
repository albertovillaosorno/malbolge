// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier: Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Two genuine guest inputs combined by a physical memory-read p and output.
// - Must-Not:
//   - Treat a 15-trit crazy fold as C integer arithmetic or source CFG linkage.
// - Allows:
//   - Inputs: source-loaded N15 and bounded byte/EOF guest streams.
//   - Outputs: exact physical input, store, reload, byte output, and halt.
//   - Side effects: isolated normative guest VM only.
// - Split-When:
//   - General source C23 arithmetic and CFG implement a reusable guest block.
// - Merge-When:
//   - Source-C stateful lowering verifies the same operation via typed IR.
// - Summary:
//   - A second input's p consumes the physical first input store then outputs.

//! Two independent guest inputs meet in a physical ternary operation and
//! output.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use std::collections::BTreeSet;
use std::iter::once;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, historical_profile,
};

const SOURCE: &[u8] = b"DCs%:?>=<;:9876543cs*/M:JJ";

#[expect(
    clippy::arithmetic_side_effects,
    clippy::as_conversions,
    clippy::integer_division_remainder_used,
    clippy::indexing_slicing,
    reason = "independent scalar 15-trit crazy oracle"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut result = 0;
    let mut place = 1;
    for _ in 0usize..15 {
        result +=
            TABLE[(data % 3) as usize][(accumulator % 3) as usize] * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    result
}

fn code_for(opcode: u8, address: u32) -> Option<u8> {
    (33u8..=126).find(|byte| {
        decode_profile_instruction(u32::from(*byte), address) == Some(opcode)
    })
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    clippy::integer_division_remainder_used,
    reason = "source, physical instruction trace, scalar oracle and negatives"
)]
fn two_real_inputs_are_folded_and_emitted_from_the_first_guest_store() {
    let profile = current_profile();
    let plan = layout::build_live_two_input_fold_source(profile)
        .expect("strict source-loaded two-input guest must exist");
    assert_eq!(
        layout::build_live_two_input_fold_source(historical_profile()),
        Err(layout::LiveInputEncodedStoreError::UnsupportedProfile),
    );
    assert_eq!(plan.source, SOURCE);
    assert_eq!(plan.source.len(), 26);
    assert_eq!(plan.initial_data_word, 7_174_453);
    assert_eq!(plan.data_address, 38);
    assert_eq!(plan.return_data_address, 53);
    assert_eq!(plan.first_input_code_address, 2);
    assert_eq!(plan.second_input_code_address, 18);
    assert_eq!(plan.fold_code_address, 20);
    assert_eq!(plan.output_code_address, 22);
    assert_eq!(plan.halt_code_address, 23);
    for (code, &byte) in plan.source.iter().enumerate() {
        let instruction = match code {
            2 | 18 => b'/',
            3 | 19 => b'j',
            4 | 20 => b'p',
            22 => b'<',
            23 => b'v',
            24 | 25 => continue,
            _ => b'o',
        };
        assert_eq!(
            decode_profile_instruction(
                u32::from(byte),
                u32::try_from(code).expect("small source index")
            ),
            Some(instruction),
        );
    }
    let base = ProfileMachine::from_source(profile, &plan.source, vec![])
        .expect("whole source loads through normative N15 rules");
    assert_eq!(
        base.memory_word(plan.data_address),
        Ok(plan.initial_data_word)
    );
    assert_eq!(base.memory_word(plan.return_data_address), Ok(37));

    // Validate the two scalar operands independently, including true EOF.
    // These checks do not stand in for the real guest traces below.
    let mut encoded = BTreeSet::new();
    let mut first_operand_outputs = BTreeSet::new();
    let mut second_operand_outputs = BTreeSet::new();
    for first in (0..=255u32).chain(once(profile.eof_word())) {
        let stored = scalar_crazy(plan.initial_data_word, first);
        assert!(encoded.insert(stored));
        let _first_added =
            first_operand_outputs.insert(scalar_crazy(stored, 128) % 256);
        let _second_added = second_operand_outputs.insert(
            scalar_crazy(scalar_crazy(plan.initial_data_word, 128), first)
                % 256,
        );
    }
    assert_eq!(encoded.len(), 257);
    assert!(first_operand_outputs.len() > 1);
    assert!(second_operand_outputs.len() > 1);

    for input in [
        vec![],
        vec![0],
        vec![255],
        vec![0, 0],
        vec![0, 255],
        vec![255, 0],
        vec![255, 255],
        vec![1, 2, 3],
        vec![2, 1],
        vec![0x80, 0x7f],
        vec![0x7f, 0x80],
        vec![0, 0x80],
        vec![0x80, 0],
        vec![0x80],
    ] {
        let mut vm = base
            .fork_with_input(input.clone())
            .expect("pristine source-loaded snapshot with fresh stdin");
        let mut trace = Vec::new();
        assert_eq!(
            vm.run_traced(24, &mut |step| trace.push(*step)),
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 24,
            }),
        );
        assert_eq!(trace.len(), 24);
        assert_eq!(vm.input_consumed(), input.len().min(2));
        let first = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let second = input
            .get(1)
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let stored = scalar_crazy(plan.initial_data_word, first);
        let combined = scalar_crazy(stored, second);
        let output = u8::try_from(combined % 256)
            .expect("scalar byte projection must fit");
        assert_eq!(vm.output(), [output]);
        assert_eq!(
            trace[2].input,
            Some(input.first().map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            },))
        );
        assert_eq!(trace[3].decoded, Some(b'j'));
        assert_eq!(trace[3].after.registers.data_pointer, plan.data_address);
        assert_eq!(trace[4].decoded, Some(b'p'));
        assert_eq!(
            trace[4]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.data_address, plan.initial_data_word)),
        );
        assert_eq!(trace[4].after.registers.accumulator, stored);
        assert_eq!(
            trace[18].input,
            Some(input.get(1).map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            },))
        );
        assert_eq!(trace[18].after.registers.accumulator, second);
        assert_eq!(trace[19].decoded, Some(b'j'));
        assert_eq!(
            trace[19]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.return_data_address, 37)),
        );
        assert_eq!(trace[19].after.registers.data_pointer, plan.data_address);
        assert_eq!(trace[20].decoded, Some(b'p'));
        assert_eq!(
            trace[20]
                .memory_reads
                .data
                .map(|read| (read.address, read.value)),
            Some((plan.data_address, stored)),
        );
        assert_eq!(trace[20].after.registers.accumulator, combined);
        assert_eq!(vm.memory_word(plan.data_address), Ok(combined));
        assert_eq!(trace[22].decoded, Some(b'<'));
        assert_eq!(trace[22].output, Some(output));
        assert_eq!(trace[22].before.registers.accumulator, combined);
        assert_eq!(trace[23].decoded, Some(b'v'));
        assert!(trace[23].memory_delta.encryption.is_none());
    }

    // Removing C20's arithmetic retains two inputs and the same output site,
    // but C22 now emits the second raw input instead of the folded result.
    let mut no_fold = plan.source.clone();
    no_fold[20] = code_for(b'o', 20).expect("source-admitted C20 no-op");
    let mut guest =
        ProfileMachine::from_source(profile, &no_fold, vec![0, 255])
            .expect("negative source must remain valid");
    assert_eq!(
        guest.run(24),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 24,
        })
    );
    assert_eq!(guest.output(), [255]);
    assert_eq!(
        guest.memory_word(plan.data_address),
        Ok(scalar_crazy(plan.initial_data_word, 0))
    );
    assert_ne!(guest.output(), &[u8::try_from(
        scalar_crazy(scalar_crazy(plan.initial_data_word, 0), 255) % 256
    )
    .expect("byte")]);

    // Removing C19's pointer return makes C20 read a *different*, untouched
    // loader word, never M38. The guest cannot borrow the first store as a
    // fake arithmetic dependency.
    let mut no_return = plan.source.clone();
    no_return[19] = code_for(b'o', 19).expect("source-admitted C19 no-op");
    let mut vm = ProfileMachine::from_source(profile, &no_return, vec![0, 255])
        .expect("alternate loadable source");
    let mut trace = Vec::new();
    assert_eq!(
        vm.run_traced(24, &mut |step| trace.push(*step)),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 24,
        }),
    );
    assert_ne!(
        trace[20].memory_reads.data.map(|read| read.address),
        Some(plan.data_address)
    );
}
