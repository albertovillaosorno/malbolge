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
//   - Source-typed full-width input-store expectations and refusal cases.
// - Must-Not:
//   - Treat synthetic stores as physical guest execution.
// - Allows:
//   - Inputs: source-authenticated input types and fixed observed inputs.
//   - Outputs: canonical C23 scalar cell values and precise errors.
//   - Side effects: none.
// - Split-When:
//   - A full guest state/dataflow verifier subsumes this focused contract.
// - Merge-When:
//   - Physical input-result operation admission owns both real and typed data.
// - Summary:
//   - Pinned EOF full-width store must not be confused with one raw guest word.

//! Full-width typed input-store obligations, separate from physical tests.

use super::super::typed_cfg_adapter::state_relocation::GuestPlacedOperand;
use super::super::typed_cfg_adapter::ternary::TernaryCfgScalarKind;
use super::*;

fn input_observation(
    input: TraceInput,
    semantics: GuestCodeInputSemantics,
    words: u32,
) -> SourceInputSiteObservation {
    SourceInputSiteObservation {
        block: 0,
        code_address: 53,
        destination: GuestPlacedOperand {
            address: 256,
            type_kind: if words == 1 {
                TernaryCfgScalarKind::U8
            } else {
                TernaryCfgScalarKind::I32
            },
            value: 2,
            words,
        },
        function: 0,
        input,
        ordinal: 0,
        raw_accumulator: match input {
            TraceInput::Byte(byte) => u32::from(byte),
            TraceInput::EndOfInput => current_profile().eof_word(),
        },
        semantics,
        trace_index: 53,
    }
}

fn signed_c23() -> GuestCodeInputSemantics {
    GuestCodeInputSemantics::SignedC23 {
        raw_eof_word: current_profile().eof_word(),
        c23_eof_cells: encode_i32_cells(u32::MAX),
    }
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source type assertions"
)]
fn signed_input_requires_two_real_stores_even_for_zero_and_ff()
-> Result<(), SourceInputTraceError> {
    for (input, expected) in [
        (TraceInput::Byte(0), vec![0, 0]),
        (TraceInput::Byte(0xff), vec![255, 0]),
        (TraceInput::EndOfInput, vec![4_644_102, 299]),
    ] {
        let pending = pending_store(input_observation(input, signed_c23(), 2))?;
        assert_eq!(pending.expected, expected);
        assert_eq!(pending.writes, vec![None, None]);
        assert!(pending.completed.is_none());
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source input width assertions"
)]
fn byte_result_refuses_eof_or_width() -> Result<(), SourceInputTraceError> {
    assert_eq!(
        pending_store(input_observation(
            TraceInput::EndOfInput,
            GuestCodeInputSemantics::ByteU8,
            1,
        ))
        .err(),
        Some(SourceInputTraceError::InputResultMismatch),
    );
    assert_eq!(
        pending_store(input_observation(
            TraceInput::Byte(0xff),
            GuestCodeInputSemantics::ByteU8,
            2,
        ))
        .err(),
        Some(SourceInputTraceError::InputResultMismatch),
    );
    assert_eq!(
        pending_store(input_observation(TraceInput::Byte(0), signed_c23(), 1))
            .err(),
        Some(SourceInputTraceError::InputResultMismatch),
    );
    let byte = pending_store(input_observation(
        TraceInput::Byte(0xff),
        GuestCodeInputSemantics::ByteU8,
        1,
    ))?;
    assert_eq!(byte.expected, [255]);
    assert_eq!(byte.writes, [None]);
    Ok(())
}

// These state-accounting unit tests do not claim guest execution. The public
// verifier obtains every word from the actual normative VM, not this helper.
fn synthetic_tracker(
    input: SourceInputSiteObservation,
) -> Result<StoreTracker, SourceInputTraceError> {
    let pending = pending_store(input)?;
    let words = pending
        .expected
        .iter()
        .enumerate()
        .map(|(index, _value)| {
            let offset = u32::try_from(index)
                .map_err(|_error| SourceInputTraceError::InputResultMismatch)?;
            let address = 256u32
                .checked_add(offset)
                .ok_or(SourceInputTraceError::InputResultMismatch)?;
            Ok((address, 0))
        })
        .collect::<Result<_, _>>()?;
    Ok(StoreTracker {
        error: None,
        influence: GuestInfluence::default(),
        next_input: 1,
        pending: vec![pending],
        trace_index: 54,
        words,
    })
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "strict physical store tests"
)]
fn physical_store_accounting_refuses_loader_values_and_partial_c32_writes()
-> Result<(), SourceInputTraceError> {
    let input = input_observation(TraceInput::Byte(0), signed_c23(), 2);
    let mut partial = synthetic_tracker(input)?;
    // Even if the loader state happened to be zero, no write occurred there.
    partial.observe_data_write(256, 54, &BTreeSet::from([0]));
    assert_eq!(
        partial
            .pending
            .first()
            .and_then(|store| store.completed.as_ref()),
        None
    );
    assert_eq!(
        partial.complete().err(),
        Some(SourceInputTraceError::MissingInputResultStore),
    );

    let mut complete = synthetic_tracker(input)?;
    complete.observe_data_write(257, 54, &BTreeSet::from([0]));
    complete.observe_data_write(256, 55, &BTreeSet::from([0]));
    let stores = complete.complete()?;
    assert_eq!(stores.len(), 1);
    assert_eq!(
        stores.first().map(|store| store
            .cells
            .iter()
            .map(|cell| cell.address)
            .collect::<Vec<_>>()),
        Some(vec![256, 257]),
    );
    assert_eq!(
        stores.first().map(|store| store
            .cells
            .iter()
            .map(|cell| cell.trace_index)
            .collect::<Vec<_>>()),
        Some(vec![55, 54]),
    );
    Ok(())
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "full-width EOF tests")]
fn physical_store_accounting_rejects_wrong_eof_high_word_until_corrected()
-> Result<(), SourceInputTraceError> {
    let input = input_observation(TraceInput::EndOfInput, signed_c23(), 2);
    let mut corrected = synthetic_tracker(input)?;
    let _previous_low = corrected.words.insert(256, 4_644_102);
    corrected.observe_data_write(256, 54, &BTreeSet::from([0]));
    let _previous_high = corrected.words.insert(257, 298);
    corrected.observe_data_write(257, 55, &BTreeSet::from([0]));
    assert_eq!(
        corrected
            .pending
            .first()
            .map(|store| store.completed.as_ref()),
        Some(None),
    );
    assert_eq!(
        corrected
            .pending
            .first()
            .map(|store| store.writes.as_slice()),
        Some([Some(54), Some(55)].as_slice()),
    );
    let _previous_corrected_high = corrected.words.insert(257, 299);
    corrected.observe_data_write(257, 56, &BTreeSet::from([0]));
    let stores = corrected.complete()?;
    let result = stores.first();
    assert_eq!(result.map(|store| store.cells.len()), Some(2));
    assert_eq!(
        result.map(|store| store
            .cells
            .iter()
            .map(|cell| cell.value)
            .collect::<Vec<_>>()),
        Some(vec![4_644_102, 299]),
    );
    assert_eq!(
        result.map(|store| store
            .cells
            .iter()
            .map(|cell| cell.trace_index)
            .collect::<Vec<_>>()),
        Some(vec![54, 56]),
    );

    let mut wrong = synthetic_tracker(input)?;
    let _wrong_low = wrong.words.insert(256, 4_644_102);
    wrong.observe_data_write(256, 54, &BTreeSet::from([0]));
    let _wrong_high = wrong.words.insert(257, 298);
    wrong.observe_data_write(257, 55, &BTreeSet::from([0]));
    assert_eq!(
        wrong.complete().err(),
        Some(SourceInputTraceError::InputResultMismatch),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source input dependency must be demonstrated independently"
)]
fn matching_constant_writes_are_not_input_stores()
-> Result<(), SourceInputTraceError> {
    let input = input_observation(TraceInput::Byte(0), signed_c23(), 2);
    let mut unrelated = synthetic_tracker(input)?;
    unrelated.observe_data_write(256, 54, &BTreeSet::new());
    unrelated.observe_data_write(257, 55, &BTreeSet::new());
    assert_eq!(
        unrelated.complete().err(),
        Some(SourceInputTraceError::InputResultUnrelatedToInput)
    );

    // C23's successful-byte high word may correctly be fixed zero. At
    // least one constituent write must nevertheless depend on *this* read.
    let mut mixed = synthetic_tracker(input)?;
    mixed.observe_data_write(256, 54, &BTreeSet::from([0]));
    mixed.observe_data_write(257, 55, &BTreeSet::new());
    assert_eq!(mixed.complete()?.len(), 1);

    let mut wrong_read = synthetic_tracker(input)?;
    wrong_read.observe_data_write(256, 54, &BTreeSet::from([1]));
    wrong_read.observe_data_write(257, 55, &BTreeSet::from([1]));
    assert_eq!(
        wrong_read.complete().err(),
        Some(SourceInputTraceError::InputResultUnrelatedToInput),
        "a different physical getchar cannot authenticate this SSA store"
    );
    Ok(())
}

fn source_cell(position: usize, opcode: u8) -> Result<u8, String> {
    (33..=126u8)
        .find(|byte| {
            malbolge::decode_profile_instruction(
                u32::from(*byte),
                u32::try_from(position).unwrap_or(u32::MAX),
            ) == Some(opcode)
        })
        .ok_or_else(|| format!("missing graphical {opcode} at {position}"))
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    reason = "bounded original N15 guest instructions and dependency effects"
)]
fn real_guest_input_dependence_survives_crazy_but_not_fresh_rotate()
-> Result<(), String> {
    let profile = current_profile();
    for (first, second, dependent) in [
        (b'p', b'p', [true, true]),
        (b'p', b'*', [true, false]),
        (b'*', b'p', [false, false]),
    ] {
        let mut source = Vec::new();
        for opcode in [b'/', b'j', first, second, b'v'] {
            source.push(source_cell(source.len(), opcode)?);
        }
        let tail = (33..=126u8)
            .find(|byte| {
                malbolge::decode_profile_instruction(u32::from(*byte), 5)
                    .is_some_and(|op| b"ji*pv/o<".contains(&op))
            })
            .ok_or("missing valid graphical loader tail")?;
        source.push(tail);
        let data_base = u32::from(source[1]) + 1;
        assert!(
            data_base
                >= u32::try_from(source.len())
                    .map_err(|error| error.to_string())?
        );
        let loaded = ProfileMachine::from_source(profile, &source, vec![])
            .map_err(|error| error.to_string())?;
        for input in [vec![], vec![2], vec![255]] {
            let mut vm = ProfileMachine::from_state(
                profile,
                loaded.memory().to_vec(),
                input.clone(),
                malbolge::ProfileRegisters::default(),
            )
            .map_err(|error| error.to_string())?;
            let mut trace = Vec::new();
            let outcome = vm
                .run_traced(5, &mut |step| trace.push(*step))
                .map_err(|error| error.to_string())?;
            assert_eq!(outcome, malbolge::RunOutcome::Terminated {
                reason: malbolge::Termination::HaltInstruction,
                steps: 5,
            });
            let mut influence = GuestInfluence::default();
            let mut data_influences = Vec::new();
            for step in &trace {
                let effect = influence.step(step, step.input.map(|_v| 0));
                if matches!(step.decoded, Some(b'p' | b'*')) {
                    data_influences.push(effect.contains(&0));
                    assert!(step.memory_reads.data.is_some());
                }
            }
            assert_eq!(data_influences, dependent);
            assert_eq!(trace[0].decoded, Some(b'/'));
            assert_eq!(trace[1].decoded, Some(b'j'));
            assert_eq!(trace[4].decoded, Some(b'v'));
            assert_eq!(vm.input_consumed(), usize::from(!input.is_empty()));
            assert!(vm.output().is_empty());
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "physical two-input state chain from the canonical guest loader"
)]
fn real_guest_second_input_depends_on_both_reads() -> Result<(), String> {
    let profile = current_profile();
    let source = super::super::build_seeded_two_input_state_update_source(
        profile, *b",H",
    )
    .map_err(|error| format!("{error:?}"))?;
    let mut vm =
        ProfileMachine::from_source(profile, &source, vec![0x02, 0xff])
            .map_err(|error| error.to_string())?;
    let mut influence = GuestInfluence::default();
    let mut read_count = 0usize;
    let mut data_events = Vec::new();
    let mut actual_reads = Vec::new();
    let outcome = vm
        .run_traced(54, &mut |step| {
            let id = step.input.map(|read| {
                actual_reads.push(read);
                let index = read_count;
                read_count = read_count.saturating_add(1);
                index
            });
            let dependencies = influence.step(step, id);
            if step.decoded == Some(b'p') {
                data_events.push((
                    step.before.registers.code_pointer,
                    step.before.registers.data_pointer,
                    dependencies,
                ));
            }
        })
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, malbolge::RunOutcome::Terminated {
        reason: malbolge::Termination::HaltInstruction,
        steps: 54,
    });
    assert_eq!(actual_reads, [TraceInput::Byte(2), TraceInput::Byte(255)]);
    assert_eq!(data_events, [
        (43, 95, BTreeSet::from([0])),
        (51, 95, BTreeSet::from([0, 1])),
    ]);
    assert_eq!(vm.input_consumed(), 2);
    Ok(())
}
