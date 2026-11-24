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
//   - Delayed physical output of a third genuine input through mutable code.
// - Must-Not:
//   - Claim C23 signed EOF, mutable checksum linkage or a reusable loop.
// - Allows:
//   - Inputs: one graphical source and bounded binary/EOF guest streams.
//   - Outputs: exact N15 input read, code reuse, byte output and guest halt.
//   - Side effects: isolated normative VM execution only.
// - Split-When:
//   - Full source-C CFG linkage verifies reusable input/output blocks.
// - Merge-When:
//   - Source-C byte-stream lowering consumes the real delayed output path.
// - Summary:
//   - A third guest input passes through eight backedges to one real output.

//! One actual guest byte output after reentry, with independent code oracle.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
    decode_profile_instruction, encrypt_profile_cell,
};

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::as_conversions,
    clippy::indexing_slicing,
    reason = "independent exact 15-trit scalar computation, not VM arithmetic"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    const TABLE: [[u32; 3]; 3] = [[1, 0, 0], [1, 0, 2], [2, 2, 1]];
    let mut output = 0;
    let mut scale = 1;
    for _ in 0u32..15u32 {
        output +=
            TABLE[(data % 3) as usize][(accumulator % 3) as usize] * scale;
        data /= 3;
        accumulator /= 3;
        scale *= 3;
    }
    output
}

#[test]
#[expect(
    clippy::expect_used,
    clippy::indexing_slicing,
    clippy::integer_division_remainder_used,
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "bounded 115-step independent VM trace, XLAT2 and scalar input"
)]
fn delayed_third_input_physically_outputs_after_eight_true_backedges() {
    const READ_STEPS: [usize; 5] = [37, 43, 73, 96, 103];
    const OUTPUT_STEP: usize = 92;
    let profile = current_profile();
    let plan = layout::build_long_source_delayed_input_echo_source(profile)
        .expect("one exact reentrant N15 echo source");
    let baseline = layout::build_long_source_finite_input_loop_source(profile)
        .expect("source-matched non-output baseline");
    assert_eq!(plan.source.len(), 261);
    assert_eq!(plan.output_code_address, 67);
    assert_eq!(plan.repeated_input_code_address, 66);
    assert_eq!(plan.first_data_address, baseline.first_data_address);
    assert_eq!(plan.initial_data_word, baseline.initial_data_word);
    assert_eq!(plan.source[67], 95);
    for (index, (&edited, &original)) in
        plan.source.iter().zip(&baseline.source).enumerate()
    {
        if index == 67 {
            assert_ne!(edited, original);
        } else {
            assert_eq!(edited, original, "source must differ only at C67");
        }
    }
    let loaded = ProfileMachine::from_source(profile, &plan.source, Vec::new())
        .expect("the source must load through normative N15 rules");
    for input in [
        vec![],
        vec![0],
        vec![255, 0],
        vec![0, 1, 255, 3, 4, 5, 6],
        vec![255, 0, 128, 7, 9],
        vec![1, 2, 0, 128, 255],
    ] {
        let mut vm = loaded
            .fork_with_input(input.clone())
            .expect("independent unread stdin on a pristine guest");
        let mut steps = Vec::new();
        let outcome = vm.run_traced(115, &mut |step| steps.push(*step));
        assert_eq!(
            outcome,
            Ok(RunOutcome::Terminated {
                reason: Termination::HaltInstruction,
                steps: 115,
            })
        );
        assert_eq!(steps.len(), 115);
        assert_eq!(vm.input_consumed(), input.len().min(5));
        let raw_third = input
            .get(2)
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        let expected_byte = u8::try_from(raw_third % 256)
            .expect("input or EOF byte projection");
        assert_eq!(vm.output(), [expected_byte]);
        assert_eq!(steps[OUTPUT_STEP].output, Some(expected_byte));
        assert_eq!(steps[OUTPUT_STEP].before.registers.accumulator, raw_third);
        assert_eq!(steps[OUTPUT_STEP].before.registers.code_pointer, 67);
        assert_eq!(steps[OUTPUT_STEP].decoded, Some(b'<'));
        assert_eq!(steps[73].before.registers.code_pointer, 66);
        assert_eq!(
            steps[73].input,
            Some(input.get(2).map_or(TraceInput::EndOfInput, |byte| {
                TraceInput::Byte(*byte)
            }))
        );
        assert_eq!(steps[114].before.registers.code_pointer, 65);
        assert_eq!(steps[114].decoded, Some(b'v'));
        assert!(steps[114].memory_delta.encryption.is_none());

        let read_indices = steps
            .iter()
            .enumerate()
            .filter_map(|(index, step)| step.input.map(|_| index))
            .collect::<Vec<_>>();
        assert_eq!(read_indices, READ_STEPS);
        for (ordinal, index) in READ_STEPS.iter().copied().enumerate() {
            assert_eq!(
                steps[index].input,
                Some(
                    input.get(ordinal).map_or(TraceInput::EndOfInput, |byte| {
                        TraceInput::Byte(*byte)
                    })
                )
            );
        }
        // The original second C67 `p` store no longer occurs. Only the
        // initial C38 store retains its first raw input word.
        let first_raw = input
            .first()
            .map_or_else(|| profile.eof_word(), |byte| u32::from(*byte));
        assert_eq!(
            vm.memory_word(plan.first_data_address),
            Ok(scalar_crazy(plan.initial_data_word, first_raw))
        );
        assert_eq!(
            vm.memory_word(baseline.second_data_address),
            Ok(baseline.initial_data_word)
        );

        // Independently enumerate each fetched C67 XLAT2 value. Only visit
        // nine is output, with all earlier/later visits semantically inert.
        let mut code = u32::from(plan.source[67]);
        for visit in 0..12usize {
            let index = 44 + 6 * visit;
            let trace = &steps[index];
            assert_eq!(trace.before.registers.code_pointer, 67);
            assert_eq!(trace.fetched_cell, Some(code));
            assert_eq!(trace.decoded, decode_profile_instruction(code, 67));
            assert_eq!(trace.output, (visit == 8).then_some(expected_byte));
            assert!(trace.memory_delta.data.is_none());
            code =
                encrypt_profile_cell(code).expect("graphical C67 code cycle");
        }
        for visit in 0..12usize {
            let step = &steps[45 + 6 * visit];
            assert_eq!(step.before.registers.code_pointer, 68);
            assert_eq!(step.decoded, Some(b'i'));
            assert_eq!(step.after.registers.code_pointer, 63);
            assert_eq!(step.memory_reads.data.map(|word| word.value), Some(62));
            assert_eq!(
                step.memory_delta.encryption.map(|write| write.address),
                Some(62)
            );
        }
    }
}

#[test]
#[expect(
    clippy::expect_used,
    reason = "verified original source is the negative output control"
)]
fn unmodified_finite_backedge_guest_does_not_output() {
    let profile = current_profile();
    let baseline = layout::build_long_source_finite_input_loop_source(profile)
        .expect("original canonical guest");
    let mut vm = ProfileMachine::from_source(profile, &baseline.source, vec![
        0, 1, 255, 3, 4,
    ])
    .expect("original source loads");
    assert_eq!(
        vm.run(115),
        Ok(RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 115,
        })
    );
    assert_eq!(vm.output(), []);
    assert_eq!(vm.input_consumed(), 5);
}
