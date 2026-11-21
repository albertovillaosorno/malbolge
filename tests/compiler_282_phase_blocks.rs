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
//   - Finite physical phase-aligned N15 input/fold/output blocks.
// - Must-Not:
//   - Infer a source-C compiler, phase-equivalent machine state, or a loop.
// - Allows:
//   - Inputs: two 282-cell blocks and five pinned byte/EOF streams.
//   - Outputs: normative guest effects, exact boundary state and refusals.
//   - Side effects: isolated bounded in-memory N15 VM execution only.
// - Split-When:
//   - A source-linked physical block compiler owns full state contracts.
// - Merge-When:
//   - General linker translation verification proves block relocation.
// - Summary:
//   - Separates matched decoder phase from executable block composition.

//! A bounded 282-address phase-alignment experiment, not C translation.
//! The guest actually executes two input/crazy/output operations on distinct
//! physical code/data cells. Continuation is linear; a separate `j` candidate
//! probes the effect of resetting D at the first block's exit.

use malbolge::{
    ProfileMachine, ProfileStepTrace, RunOutcome, Termination, TraceInput,
    current_profile, decode_profile_instruction, encrypt_profile_cell,
};

const BLOCK: usize = 282;
const SOURCE_CELLS: usize = BLOCK * 2;
const RESET_OFFSET: usize = 200;
const READ_OFFSET: usize = 205;
const FOLD_OFFSET: usize = 206;
const EMIT_OFFSET: usize = 207;
const MAX_STEPS: usize = 4096;

fn at<T>(items: &[T], index: usize) -> Result<&T, String> {
    items
        .get(index)
        .ok_or_else(|| format!("missing index {index}"))
}

fn byte_at(items: &[u8], index: usize) -> Result<u32, String> {
    Ok(u32::from(*at(items, index)?))
}

fn low_byte(word: u32) -> Result<u8, String> {
    u8::try_from(word & 0xff).map_err(|error| error.to_string())
}

fn n15_raw(selected: Option<u8>) -> u32 {
    selected.map_or_else(|| current_profile().eof_word(), u32::from)
}

fn physical_source(first_boundary: u8) -> Result<Vec<u8>, String> {
    let mut source = Vec::with_capacity(SOURCE_CELLS);
    for address in 0..SOURCE_CELLS {
        let address_word =
            u32::try_from(address).map_err(|error| error.to_string())?;
        let decoded = match address {
            200 | 482 => b'j',
            205 | 487 => b'/',
            206 | 488 => b'p',
            207 | 489 => b'<',
            281 => first_boundary,
            563 => b'v',
            _ => b'o',
        };
        let cell = (33u8..=126).find(|byte| {
            decode_profile_instruction(u32::from(*byte), address_word)
                == Some(decoded)
        });
        source.push(
            cell.ok_or_else(|| format!("no graphical {decoded} at {address}"))?,
        );
    }
    Ok(source)
}

#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "fifteen trits, bounded independent scalar oracle"
)]
fn ternary_crazy(mut left: u32, mut right: u32) -> u32 {
    let mut place = 1u32;
    let mut output = 0u32;
    for _ in 0u8..15 {
        let digit = match (left % 3, right % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        output += digit * place;
        place *= 3;
        left /= 3;
        right /= 3;
    }
    output
}

// Require the full loader source to be executed in order, rather than
// accepting a shortened path which happens to emit two matching bytes.
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    reason = "full code trace test assertions"
)]
fn assert_code_encryption(
    source: &[u8],
    traces: &[ProfileStepTrace],
) -> Result<(), String> {
    assert_eq!(source.len(), SOURCE_CELLS);
    assert_eq!(traces.len(), SOURCE_CELLS);
    let mut writes = 0usize;
    for (index, (source_byte, step)) in source.iter().zip(traces).enumerate() {
        let code = u32::try_from(index).map_err(|error| error.to_string())?;
        let cell = u32::from(*source_byte);
        assert_eq!(step.before.registers.code_pointer, code);
        assert_eq!(step.fetched_cell, Some(cell));
        assert_eq!(step.decoded, decode_profile_instruction(cell, code));
        assert!(step.result.is_ok(), "failed guest step {index}");
        if step.memory_delta.data.is_some() {
            writes = writes.saturating_add(1);
        }
        if index == SOURCE_CELLS - 1 {
            assert_eq!(step.decoded, Some(b'v'));
            assert_eq!(step.memory_delta.encryption, None);
            continue;
        }
        assert_eq!(
            step.memory_reads
                .encryption
                .map(|item| (item.address, item.value)),
            Some((code, cell)),
        );
        let encrypted = encrypt_profile_cell(cell)
            .ok_or("source code encryption refused")?;
        assert_eq!(
            step.memory_delta
                .encryption
                .map(|delta| { (delta.address, delta.before, delta.after) }),
            (encrypted != cell).then_some((code, cell, encrypted)),
        );
    }
    assert_eq!(writes, 2);
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "five frozen streams need full physical trace checks"
)]
fn two_282_cell_envelopes_execute_distinct_guest_input_folds()
-> Result<(), String> {
    let profile = current_profile();
    let source = physical_source(b'o')?;
    assert_eq!(source.len(), SOURCE_CELLS);
    assert_eq!(
        source.get(0..BLOCK - 1),
        source.get(BLOCK..SOURCE_CELLS - 1)
    );
    for input in [vec![], vec![0], vec![0x80], vec![0xff], vec![1, 2]] {
        let mut vm =
            ProfileMachine::from_source(profile, &source, input.clone())
                .map_err(|error| error.to_string())?;
        let first_reset_word = u32::from(*at(&source, RESET_OFFSET)?);
        let second_reset_address = u32::try_from(BLOCK)
            .map_err(|error| error.to_string())?
            + first_reset_word;
        let second_reset_word = encrypt_profile_cell(byte_at(
            &source,
            usize::try_from(second_reset_address)
                .map_err(|error| error.to_string())?,
        )?)
        .ok_or("invalid second reset seed")?;
        let reset_words = [first_reset_word, second_reset_word];
        let data_addresses = reset_words.map(|word| word + 6);
        assert!(
            data_addresses
                .iter()
                .all(|address| (33..200).contains(address))
        );
        assert_ne!(data_addresses[0], data_addresses[1]);
        let seeds = data_addresses
            .map(|address| {
                let index = usize::try_from(address)
                    .map_err(|error| error.to_string())?;
                let cell = byte_at(&source, index)?;
                encrypt_profile_cell(cell)
                    .ok_or_else(|| "non-graphical seed".to_owned())
            })
            .into_iter()
            .collect::<Result<Vec<_>, _>>()?;
        for address in data_addresses {
            assert_eq!(
                vm.memory_word(address),
                Ok(byte_at(
                    &source,
                    usize::try_from(address)
                        .map_err(|error| error.to_string())?
                )?)
            );
        }
        let mut traces = Vec::new();
        let outcome = vm
            .run_traced(MAX_STEPS, &mut |trace| traces.push(*trace))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: SOURCE_CELLS,
        });
        assert_code_encryption(&source, &traces)?;
        let mut oracle_bytes = Vec::new();
        for block_index in 0..2 {
            let base = block_index * BLOCK;
            let selected = input.get(block_index).copied();
            let raw = n15_raw(selected);
            let reset = at(&traces, base + RESET_OFFSET)?;
            let read_step = at(&traces, base + READ_OFFSET)?;
            assert_eq!(reset.decoded, Some(b'j'));
            assert_eq!(
                reset.memory_reads.data.map(|item| item.value),
                Some(*at(&reset_words, block_index)?)
            );
            assert_eq!(
                reset.after.registers.data_pointer,
                *at(&reset_words, block_index)? + 1
            );
            let fold = at(&traces, base + FOLD_OFFSET)?;
            let emit = at(&traces, base + EMIT_OFFSET)?;
            assert_eq!(read_step.decoded, Some(b'/'));
            assert_eq!(
                read_step.input,
                Some(
                    selected.map_or(TraceInput::EndOfInput, TraceInput::Byte,)
                )
            );
            assert_eq!(read_step.after.registers.accumulator, raw);
            assert_eq!(fold.decoded, Some(b'p'));
            assert_eq!(
                fold.before.registers.data_pointer,
                *at(&data_addresses, block_index)?
            );
            assert_eq!(
                fold.memory_reads.data.map(|item| item.value),
                Some(*at(&seeds, block_index)?)
            );
            let expected_word = ternary_crazy(*at(&seeds, block_index)?, raw);
            assert_eq!(
                fold.memory_delta.data.map(|write| write.after),
                Some(expected_word)
            );
            assert_eq!(fold.after.registers.accumulator, expected_word);
            assert_eq!(emit.decoded, Some(b'<'));
            assert_eq!(emit.output, Some(low_byte(expected_word)?));
            oracle_bytes.push(low_byte(expected_word)?);
        }
        // The first block physically continues through its 282nd cell.
        assert_eq!(at(&traces, BLOCK - 1)?.decoded, Some(b'o'));
        assert_eq!(
            at(&traces, BLOCK - 1)?.after.registers.code_pointer,
            u32::try_from(BLOCK).map_err(|error| error.to_string())?
        );
        assert_eq!(
            at(&traces, BLOCK)?.before.registers.code_pointer,
            u32::try_from(BLOCK).map_err(|error| error.to_string())?
        );
        assert_eq!(at(&traces, SOURCE_CELLS - 1)?.decoded, Some(b'v'));
        assert_eq!(vm.output(), oracle_bytes);
        for (index, address) in data_addresses.iter().enumerate() {
            let raw = n15_raw(input.get(index).copied());
            assert_eq!(
                vm.memory_word(*address),
                Ok(ternary_crazy(*at(&seeds, index)?, raw))
            );
        }
        assert_eq!(vm.input_consumed(), input.len().min(2));
    }
    Ok(())
}

// An explicit `j` at the first exit changes D before the second block.
// Both instances still execute, but positional phase matching does not
// preserve the incoming data state or the second fold's output.
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "five bounded boundary-jump paths require full trace"
)]
fn explicit_boundary_data_restart_changes_the_second_block_state()
-> Result<(), String> {
    let profile = current_profile();
    let source = physical_source(b'j')?;
    assert_eq!(source.len(), SOURCE_CELLS);
    assert_eq!(source.get(..BLOCK - 1), source.get(BLOCK..SOURCE_CELLS - 1));
    let first_reset_word = u32::from(*at(&source, RESET_OFFSET)?);
    let first_data_address = first_reset_word + 6;
    let exit_data_address = first_reset_word
        + u32::try_from(BLOCK - RESET_OFFSET - 1)
            .map_err(|error| error.to_string())?;
    let exit_word = encrypt_profile_cell(u32::from(*at(
        &source,
        usize::try_from(exit_data_address)
            .map_err(|error| error.to_string())?,
    )?))
    .ok_or("unavailable independently computed exit jump word")?;
    let second_reset_address = exit_word
        + u32::try_from(RESET_OFFSET).map_err(|error| error.to_string())?
        + 1;
    let second_reset_word = encrypt_profile_cell(byte_at(
        &source,
        usize::try_from(second_reset_address)
            .map_err(|error| error.to_string())?,
    )?)
    .ok_or("unavailable independently computed second reset word")?;
    let second_data_address = second_reset_word + 6;
    assert_eq!(
        [
            first_data_address,
            exit_data_address,
            second_reset_address,
            second_data_address
        ],
        [128, 203, 246, 95]
    );
    assert_ne!(second_data_address, first_reset_word + 5);
    let destinations = [first_data_address, second_data_address];
    let seeds = destinations
        .map(|address| {
            let index =
                usize::try_from(address).map_err(|error| error.to_string())?;
            let cell = byte_at(&source, index)?;
            encrypt_profile_cell(cell)
                .ok_or_else(|| "non-graphical seed".to_owned())
        })
        .into_iter()
        .collect::<Result<Vec<_>, _>>()?;
    for input in [vec![], vec![0], vec![0x80], vec![0xff], vec![1, 2]] {
        let mut vm =
            ProfileMachine::from_source(profile, &source, input.clone())
                .map_err(|error| error.to_string())?;
        let mut traces = Vec::new();
        let outcome = vm
            .run_traced(MAX_STEPS, &mut |trace| traces.push(*trace))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: SOURCE_CELLS,
        });
        assert_code_encryption(&source, &traces)?;
        let exit = at(&traces, BLOCK - 1)?;
        assert_eq!(exit.decoded, Some(b'j'));
        assert_eq!(exit.before.registers.data_pointer, exit_data_address);
        assert_eq!(
            exit.memory_reads.data.map(|item| item.value),
            Some(exit_word)
        );
        assert_eq!(exit.after.registers.data_pointer, exit_word + 1);
        assert_eq!(
            exit.after.registers.code_pointer,
            u32::try_from(BLOCK).map_err(|error| error.to_string())?
        );
        assert_eq!(
            at(&traces, BLOCK)?.before.registers.code_pointer,
            u32::try_from(BLOCK).map_err(|error| error.to_string())?
        );
        let resets = [first_reset_word, second_reset_word];
        let mut expected_output = Vec::new();
        for index in 0..2 {
            let base = index * BLOCK;
            let selected = input.get(index).copied();
            let raw = n15_raw(selected);
            let reset = at(&traces, base + RESET_OFFSET)?;
            let read_step = at(&traces, base + READ_OFFSET)?;
            let fold = at(&traces, base + FOLD_OFFSET)?;
            let output = at(&traces, base + EMIT_OFFSET)?;
            assert_eq!(reset.decoded, Some(b'j'));
            assert_eq!(
                reset.memory_reads.data.map(|item| item.value),
                Some(*at(&resets, index)?)
            );
            assert_eq!(
                reset.after.registers.data_pointer,
                *at(&resets, index)? + 1
            );
            assert_eq!(
                read_step.input,
                Some(
                    selected.map_or(TraceInput::EndOfInput, TraceInput::Byte,)
                )
            );
            assert_eq!(read_step.after.registers.accumulator, raw);
            assert_eq!(
                fold.before.registers.data_pointer,
                *at(&destinations, index)?
            );
            assert_eq!(
                fold.memory_reads.data.map(|item| item.value),
                Some(*at(&seeds, index)?)
            );
            let expected = ternary_crazy(*at(&seeds, index)?, raw);
            assert_eq!(
                fold.memory_delta.data.map(|write| write.after),
                Some(expected)
            );
            assert_eq!(fold.after.registers.accumulator, expected);
            assert_eq!(output.output, Some(low_byte(expected)?));
            assert_eq!(
                vm.memory_word(*at(&destinations, index)?),
                Ok(expected)
            );
            expected_output.push(low_byte(expected)?);
        }
        assert_eq!(vm.output(), expected_output);
        assert_eq!(vm.input_consumed(), input.len().min(2));
        if input == [1, 2] {
            // Replacing the first exit's `o` by `j` changes only one
            // physical code cell but alters the later data state/output.
            let unreset_second = low_byte(ternary_crazy(
                encrypt_profile_cell(u32::from(*at(&source, 127)?))
                    .ok_or("seed")?,
                2,
            ))?;
            assert_ne!(*at(&expected_output, 1)?, unreset_second);
        }
    }
    Ok(())
}
