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
//   - A fixed physical N15 four-read, one-output same-site reentry witness.
// - Must-Not:
//   - Claim an EOF-terminated C23 loop, C32 state or checksum compilation.
// - Allows:
//   - Inputs: one 120-cell SHA-frozen graphical source and six byte streams.
//   - Outputs: exact source-loaded 83-step code, IO and data-write evidence.
//   - Side effects: bounded normative VM execution only.
// - Split-When:
//   - A reusable guest loop linker derives source C state and EOF control.
// - Merge-When:
//   - Verified general guest control can emit the same real code lifecycle.
// - Summary:
//   - Four physical reads reuse C47 through alternating XLAT2 input phases.

//! A genuinely revisited input code site, not a C23 EOF-terminated program.
//! The guest loops C44..C49 after two earlier data-dependent backedges.
//! Its third input feeds a reached output; the fourth input is also physical.
//! Halt/EOF policy and C32 frame translation are deliberately absent.

use malbolge::{
    ProfileMachine, ProfileStepTrace, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, encrypt_profile_cell,
};

const SOURCE: &[u8; 120] =
    include_bytes!("compiler/fixtures/same-site-four-read.malbolge");
const STEPS: usize = 83;
const INPUT_SITE: u32 = 47;
const INPUT_STEPS: [usize; 4] = [47, 56, 68, 80];
const ENTRY_STEPS: [usize; 7] = [47, 50, 56, 62, 68, 74, 80];

type GuestCapture = (ProfileMachine, Vec<ProfileStepTrace>, RunOutcome);

fn expected_code_path() -> Vec<u32> {
    let mut result = (0..50u32).collect::<Vec<_>>();
    result.extend([47, 48, 49, 73, 74, 75, 47, 48, 49]);
    for _ in 0u8..4u8 {
        result.extend(44..50);
    }
    result
}

fn capture(
    source: &[u8],
    input: Vec<u8>,
    limit: usize,
) -> Result<GuestCapture, String> {
    let mut machine =
        ProfileMachine::from_source(current_profile(), source, input)
            .map_err(|error| format!("profile source rejected: {error}"))?;
    let mut traces = Vec::new();
    let result = machine
        .run_traced(limit, &mut |step| traces.push(*step))
        .map_err(|error| format!("guest transition rejected: {error}"))?;
    Ok((machine, traces, result))
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "four distinct real input effects checked on six frozen streams"
)]
fn four_reads_and_one_data_dependent_output() -> Result<(), String> {
    assert_eq!(SOURCE.len(), 120);
    for (position, &byte) in SOURCE.iter().enumerate() {
        let address =
            u32::try_from(position).map_err(|error| error.to_string())?;
        assert!(
            matches!(
                decode_profile_instruction(u32::from(byte), address),
                Some(b'o' | b'i' | b'j' | b'p' | b'*' | b'/' | b'<' | b'v')
            ),
            "non-graphical source at C{position}"
        );
    }
    assert_eq!(SOURCE.get(113), Some(&43));
    assert_eq!(SOURCE.get(119), Some(&43));
    assert_eq!(SOURCE.get(47), Some(&70));
    assert_eq!(expected_code_path().len(), STEPS);
    let first = u32::from(SOURCE[47]);
    let after_one = encrypt_profile_cell(first).ok_or("missing XLAT2 first")?;
    let after_two =
        encrypt_profile_cell(after_one).ok_or("missing XLAT2 second")?;
    assert_eq!((first, after_one, after_two), (70, 74, 70));

    for input in [
        vec![],
        vec![0x00],
        vec![0xff],
        vec![0x01, 0x02, 0x03, 0x04, 0x05],
        vec![0x80, 0x00, 0x00, 0xff],
        vec![0x01, 0x02, 0xff, 0x00],
    ] {
        let third = input.get(2).copied().unwrap_or(106);
        let (machine, traces, outcome) = capture(SOURCE, input.clone(), STEPS)?;
        assert_eq!(outcome, RunOutcome::BudgetExhausted { steps: STEPS });
        assert_eq!(traces.len(), STEPS);
        assert_eq!(
            traces
                .iter()
                .map(|step| step.before.registers.code_pointer)
                .collect::<Vec<_>>(),
            expected_code_path(),
        );
        let actual_input_steps = traces
            .iter()
            .enumerate()
            .filter_map(|(index, trace)| trace.input.map(|read| (index, read)))
            .collect::<Vec<_>>();
        let expected_inputs = INPUT_STEPS
            .iter()
            .enumerate()
            .map(|(ordinal, &step)| {
                (
                    step,
                    input
                        .get(ordinal)
                        .copied()
                        .map_or(TraceInput::EndOfInput, TraceInput::Byte),
                )
            })
            .collect::<Vec<_>>();
        assert_eq!(actual_input_steps, expected_inputs);
        assert_eq!(machine.input_consumed(), input.len().min(4));
        assert_eq!(machine.output(), [third]);
        assert_eq!(
            traces.get(73).ok_or("missing third-byte output")?.decoded,
            Some(b'<'),
        );
        assert_eq!(traces.get(73).and_then(|step| step.output), Some(third));
        for (ordinal, &index) in ENTRY_STEPS.iter().enumerate() {
            let visit = traces.get(index).ok_or("missing C47 revisit")?;
            assert_eq!(visit.before.registers.code_pointer, INPUT_SITE);
            assert_eq!(
                visit.fetched_cell,
                Some(if ordinal & 1 == 0 {
                    70
                } else {
                    74
                })
            );
            assert_eq!(
                visit.decoded,
                Some(if ordinal & 1 == 0 {
                    b'/'
                } else {
                    b'P'
                })
            );
            let encrypted = visit
                .memory_delta
                .encryption
                .ok_or("every non-halt C47 visit encrypts its code")?;
            assert_eq!(encrypted.address, INPUT_SITE);
            assert_eq!(
                encrypted.after,
                if ordinal & 1 == 0 {
                    74
                } else {
                    70
                }
            );
        }
        for (index, destination) in [
            (49, 47),
            (52, 73),
            (58, 44),
            (64, 44),
            (70, 44),
            (76, 44),
            (82, 44),
        ] {
            let jump = traces.get(index).ok_or("missing actual return")?;
            assert_eq!(jump.decoded, Some(b'i'));
            assert_eq!(jump.after.registers.code_pointer, destination);
            assert_eq!(
                jump.memory_reads.data.map(|read| read.value),
                Some(destination - 1),
            );
        }
        let physical_store = traces.get(60).ok_or("missing reached write")?;
        assert_eq!(physical_store.decoded, Some(b'p'));
        assert_eq!(
            physical_store.memory_delta.data.map(|write| write.address),
            Some(115),
        );
        assert_eq!(machine.memory_word(119), Ok(43));
        assert_eq!(machine.memory_word(125), Ok(43));
        assert_eq!(machine.memory_word(131), Ok(43));
        assert_eq!(machine.memory_word(137), Ok(43));
        assert_eq!(machine.memory_word(INPUT_SITE), Ok(74));
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "negative source mutation compares actual executed input count"
)]
fn source_loaded_exit_pointer_mutation_removes_the_third_read()
-> Result<(), String> {
    let mut source = SOURCE.to_vec();
    // The original two-read source carried M113=115 and halted at C116.
    // A different legal source byte redirects the same reached C49 'i'.
    *source.get_mut(113).ok_or("missing jump source operand")? = 115;
    assert_eq!(decode_profile_instruction(115, 113), Some(b'j'));
    let (machine, traces, outcome) =
        capture(&source, vec![0x01, 0x02, 0x03, 0x04], STEPS)?;
    assert_eq!(outcome, RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps: 60,
    });
    assert_eq!(traces.iter().filter(|step| step.input.is_some()).count(), 2);
    assert_eq!(machine.input_consumed(), 2);
    assert_eq!(machine.output(), []);
    Ok(())
}
