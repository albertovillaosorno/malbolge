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
//   - Real input-indexed guest code transfer after a two-p raw-byte store.
// - Must-Not:
//   - Claim a C parity branch, signed C32 state, checksum or reusable loop.
// - Allows:
//   - Inputs: one source-loaded 27-cell N15 guest, binary bytes and EOF.
//   - Outputs: bounded physical i/j/p and code/data-alias trace evidence.
//   - Side effects: isolated normative in-memory profile VMs only.
// - Split-When:
//   - A source-linked conditional/loop compiler owns the same guest effects.
// - Merge-When:
//   - A generic physical data-dependent code emitter subsumes the witness.
// - Summary:
//   - Two input values select different real opcodes at overwritten C73.

//! Source-loaded input-driven instruction dispatch, not source-C control flow.

#[path = "../src/compiler/malbolge-layout/composition/lib.rs"]
pub mod layout;

use malbolge::{
    ProfileMachine, ProfileMemoryRead, ProfileStepTrace, RunOutcome,
    StepOutcome, Termination, current_profile, decode_profile_instruction,
    encrypt_profile_cell,
};

// This is the checked 27-cell exact-input store/reentry with only the reached
// C24 halt re-encoded as a code jump. C25/C26 still fix the virgin loader.
const SOURCE: &[u8; 27] = b"DCBA@?>=<;:98hx/v-210/poJ%H";
const RAW_ONE_TRITS: u32 = 7_174_453;
const RAW_EOF: u32 = 14_348_906;
const DISPATCH_STEPS: usize = 26;

type GuestRun = (ProfileMachine, Vec<ProfileStepTrace>, RunOutcome);

fn physical_guest(input: Vec<u8>, steps: usize) -> Result<GuestRun, String> {
    let mut guest =
        ProfileMachine::from_source(current_profile(), SOURCE, input)
            .map_err(|error| error.to_string())?;
    let mut events = Vec::new();
    let outcome = guest
        .run_traced(steps, &mut |trace| events.push(*trace))
        .map_err(|error| format!("actual source guest rejected: {error}"))?;
    Ok((guest, events, outcome))
}

fn indexed_jump_source() -> Result<Vec<u8>, String> {
    let mut source =
        layout::build_byte_exact_input_reentry_source(current_profile())
            .map_err(|error| format!("{error:?}"))?
            .store
            .source;
    let opcode = (33u8..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), 24) == Some(b'i')
        })
        .ok_or("no graphical i at C24")?;
    *source.get_mut(24).ok_or("missing C24")? = opcode;
    Ok(source)
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "loaded source geometry is a test oracle, not compiler lowering"
)]
fn dispatched_source_is_one_checked_code_cell_from_exact_input_reentry()
-> Result<(), String> {
    assert_eq!(indexed_jump_source()?, SOURCE);
    assert_eq!(SOURCE.len(), 27);
    assert_eq!(SOURCE.get(24), Some(&b'J'));
    assert_eq!(decode_profile_instruction(u32::from(b'J'), 24), Some(b'i'));
    let baseline =
        ProfileMachine::from_source(current_profile(), SOURCE, vec![])
            .map_err(|error| error.to_string())?;
    assert_eq!(baseline.memory_word(72), Ok(72));
    assert_eq!(baseline.memory_word(73), Ok(RAW_ONE_TRITS));
    assert_eq!(baseline.memory_word(121), Ok(RAW_ONE_TRITS));
    assert_eq!(baseline.memory_word(85), Ok(7_174_453));
    Ok(())
}

// The second reached p overwrites *future executable code* at M73 with
// the exact raw input. C24 i then jumps via a separate input-indexed operand
// at M62 or M84, and C73 executes different instructions from that write.
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    clippy::panic_in_result_fn,
    reason = "two independently source-loaded 26-step mutable-code VM paths"
)]
fn exact_input_write_selects_real_j_versus_p_at_same_code_address()
-> Result<(), String> {
    for (byte, target, opcode) in [(61u8, 63u32, b'j'), (83u8, 85u32, b'p')] {
        let (machine, trace, outcome) =
            physical_guest(vec![byte], DISPATCH_STEPS)?;
        assert_eq!(outcome, RunOutcome::BudgetExhausted {
            steps: DISPATCH_STEPS
        });
        assert_eq!(trace.len(), DISPATCH_STEPS);
        assert_eq!(
            trace
                .iter()
                .take(25)
                .map(|event| event.before.registers.code_pointer)
                .collect::<Vec<_>>(),
            (0..25u32).collect::<Vec<_>>()
        );
        let input = trace.get(13).ok_or("input site not reached")?;
        assert_eq!(input.decoded, Some(b'/'));
        assert_eq!(input.input, Some(malbolge::TraceInput::Byte(byte)));
        let stored = trace.get(17).ok_or("second p not reached")?;
        assert_eq!(stored.decoded, Some(b'p'));
        assert_eq!(
            stored.memory_reads.data,
            Some(ProfileMemoryRead {
                address: 73,
                value: RAW_ONE_TRITS,
            })
        );
        assert_eq!(stored.after.registers.accumulator, u32::from(byte));
        assert_eq!(
            stored
                .memory_delta
                .data
                .map(|write| (write.address, write.after)),
            Some((73, u32::from(byte)))
        );
        for (site, address, read) in [(22, 78, 72), (23, 73, u32::from(byte))] {
            let step = trace.get(site).ok_or("missing pointer reentry")?;
            assert_eq!(step.decoded, Some(b'j'));
            assert_eq!(
                step.memory_reads.data,
                Some(ProfileMemoryRead { address, value: read })
            );
        }
        let jump = trace.get(24).ok_or("code jump not reached")?;
        assert_eq!(jump.decoded, Some(b'i'));
        assert_eq!(
            jump.memory_reads.data,
            Some(ProfileMemoryRead {
                address: u32::from(byte) + 1,
                value: 72,
            })
        );
        assert_eq!(jump.before.registers.code_pointer, 24);
        assert_eq!(jump.after.registers.code_pointer, 73);
        assert_eq!(
            jump.memory_delta.encryption.map(|write| (
                write.address,
                write.before,
                write.after
            )),
            Some((72, 72, encrypt_profile_cell(72).ok_or("bad XLAT2")?))
        );
        let dispatched = trace.get(25).ok_or("dynamic code not reached")?;
        assert_eq!(dispatched.before.registers.code_pointer, 73);
        assert_eq!(dispatched.before.registers.data_pointer, target);
        assert_eq!(dispatched.fetched_cell, Some(u32::from(byte)));
        assert_eq!(dispatched.decoded, Some(opcode));
        assert_eq!(dispatched.result, Ok(StepOutcome::Continued));
        assert_eq!(
            dispatched.memory_reads.data.map(|read| read.address),
            Some(target)
        );
        assert_eq!(machine.input_consumed(), 1);
        assert!(machine.output().is_empty());
        assert_eq!(machine.registers().code_pointer, 74);
        if byte == 61 {
            assert_eq!(
                dispatched.memory_reads.data.map(|read| read.value),
                Some(7_174_489)
            );
            assert_eq!(machine.registers().data_pointer, 7_174_490);
            assert_eq!(machine.registers().accumulator, 61);
            assert!(dispatched.memory_delta.data.is_none());
        } else {
            assert_eq!(
                dispatched.memory_reads.data.map(|read| read.value),
                Some(7_174_453)
            );
            assert_eq!(
                dispatched
                    .memory_delta
                    .data
                    .map(|write| (write.address, write.after)),
                Some((85, 7_174_373))
            );
            assert_eq!(machine.memory_word(85), Ok(7_174_373));
            assert_eq!(machine.registers().accumulator, 7_174_373);
            assert_eq!(machine.registers().data_pointer, 86);
        }
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "mutant source proves physical code/data alias necessity"
)]
fn missing_second_store_blocks_dynamic_code() -> Result<(), String> {
    let mut source = SOURCE.to_vec();
    let nop = (33u8..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), 17) == Some(b'o')
        })
        .ok_or("no graphical nop at C17")?;
    *source.get_mut(17).ok_or("missing store")? = nop;
    let mut targets = Vec::new();
    for byte in [61u8, 83u8] {
        let mut machine =
            ProfileMachine::from_source(current_profile(), &source, vec![byte])
                .map_err(|error| error.to_string())?;
        let prefix = machine.run(24).map_err(|error| error.to_string())?;
        assert_eq!(prefix, RunOutcome::BudgetExhausted { steps: 24 });
        assert_eq!(machine.memory_word(73), Ok(RAW_ONE_TRITS));
        assert_eq!(machine.registers().data_pointer, RAW_ONE_TRITS + 1);
        let result = machine.step();
        targets.push((machine.registers().code_pointer, result));
        assert_eq!(machine.registers().code_pointer, 73);
        let mut dispatch = Vec::new();
        assert_eq!(
            machine.step_traced(&mut |step| dispatch.push(*step)),
            Ok(StepOutcome::Terminated(Termination::NonGraphicalCell))
        );
        let fetched = dispatch.first().ok_or("missing C73 mutant fetch")?;
        assert_eq!(fetched.fetched_cell, Some(RAW_ONE_TRITS));
        assert_eq!(fetched.decoded, None);
    }
    assert_eq!(targets.first(), targets.get(1));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "bounded negative classes must not be claimed as C control"
)]
fn eof_and_unsupported_bytes_do_not_form_a_total_dynamic_branch()
-> Result<(), String> {
    for input in [vec![], vec![0]] {
        let expected_raw = input.first().copied().map_or(RAW_EOF, u32::from);
        let mut machine =
            ProfileMachine::from_source(current_profile(), SOURCE, input)
                .map_err(|error| error.to_string())?;
        assert_eq!(
            machine.run(24),
            Ok(RunOutcome::BudgetExhausted { steps: 24 })
        );
        assert_eq!(machine.memory_word(73), Ok(expected_raw));
        assert!(machine.step().is_err(), "no legal jump encryption");
        assert_eq!(machine.registers().code_pointer, 24);
    }
    let (machine, trace, outcome) =
        physical_guest(vec![35, 255], DISPATCH_STEPS)?;
    assert_eq!(outcome, RunOutcome::BudgetExhausted {
        steps: DISPATCH_STEPS
    });
    assert_eq!(trace.get(25).and_then(|event| event.decoded), Some(b'Y'));
    assert_eq!(trace.get(25).and_then(|event| event.fetched_cell), Some(35));
    assert_eq!(machine.input_consumed(), 1);
    assert!(machine.output().is_empty());
    let (jump_machine, jump_trace, jump_outcome) =
        physical_guest(vec![119], 25)?;
    assert_eq!(jump_outcome, RunOutcome::BudgetExhausted { steps: 25 });
    assert_eq!(
        jump_trace
            .last()
            .map(|event| event.after.registers.code_pointer),
        Some(73)
    );
    assert_eq!(jump_machine.memory_word(73), Ok(119));
    Ok(())
}

// Independent 15-trit crazy table. No VM loader or compiler helper is invoked
// in the census below; the real VM separately witnesses representative paths.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    reason = "15 fixed trits and independently enumerated crazy truth table"
)]
fn scalar_crazy(mut data: u32, mut accumulator: u32) -> u32 {
    let mut value = 0u32;
    let mut place = 1u32;
    for _ in 0usize..15usize {
        let digit = match (data % 3, accumulator % 3) {
            (0 | 1, 0) | (2, 2) => 1,
            (1, 2) | (2, 0 | 1) => 2,
            _ => 0,
        };
        value += digit * place;
        data /= 3;
        accumulator /= 3;
        place *= 3;
    }
    value
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "finite static closure of the input-driven jump address grammar"
)]
fn all_high_byte_destinations_are_bounded_and_none_can_output()
-> Result<(), String> {
    let mut loader = SOURCE
        .iter()
        .map(|byte| u32::from(*byte))
        .collect::<Vec<_>>();
    while loader.len() <= 256 {
        let previous = loader
            .get(loader.len().saturating_sub(2))
            .copied()
            .ok_or("no previous loader word")?;
        let latest = loader.last().copied().ok_or("no last loader word")?;
        loader.push(scalar_crazy(previous, latest));
    }
    for (address, expected) in [
        (37, RAW_ONE_TRITS),
        (62, 72),
        (73, RAW_ONE_TRITS),
        (78, 72),
        (84, 72),
        (121, RAW_ONE_TRITS),
    ] {
        assert_eq!(loader.get(address), Some(&expected), "loader M{address}");
    }

    let mut refused_jump = 0u32;
    let mut non_graphical_fetch = 0u32;
    let mut code_at_73 = 0u32;
    let mut inert_at_73 = 0u32;
    let mut jump_at_73 = 0u32;
    let mut crazy_at_73 = 0u32;
    let mut jump_code_at_73 = 0u32;
    let mut code_at_37 = 0u32;
    for byte in 26u8..=255u8 {
        let raw = u32::from(byte);
        let pointer = usize::from(byte) + 1;
        // C17 p overwrites C73 with exact raw input. C15 p overwrites M121
        // with one crazy transform. All other 27..=256 words are virgin.
        let operand = match pointer {
            73 => raw,
            121 => scalar_crazy(RAW_ONE_TRITS, raw),
            _ => loader.get(pointer).copied().ok_or("missing operand")?,
        };
        if !(33..=126).contains(&operand) {
            refused_jump += 1;
            continue;
        }
        let next_code = operand + 1;
        assert!(matches!(next_code, 37 | 73));
        if next_code == 37 {
            code_at_37 += 1;
            // Loader M37 is non-graphical, so the next fetch terminates.
            assert_eq!(loader.get(37), Some(&RAW_ONE_TRITS));
            non_graphical_fetch += 1;
            continue;
        }
        let fetched = raw;
        if !(33..=126).contains(&fetched) {
            non_graphical_fetch += 1;
            continue;
        }
        code_at_73 += 1;
        let opcode = decode_profile_instruction(fetched, 73)
            .ok_or("graphical C73 failed to decode")?;
        match opcode {
            b'j' => jump_at_73 += 1,
            b'p' => crazy_at_73 += 1,
            b'i' => jump_code_at_73 += 1,
            _ => {
                assert!(!matches!(opcode, b'/' | b'<' | b'v' | b'*'));
                inert_at_73 += 1;
            },
        }
    }
    assert_eq!(
        (
            refused_jump,
            code_at_37,
            code_at_73,
            non_graphical_fetch,
            inert_at_73,
            jump_at_73,
            crazy_at_73,
            jump_code_at_73,
        ),
        (114, 39, 32, 84, 29, 1, 1, 1)
    );
    // No byte >= 26 can reach an output or input opcode in one dispatch.
    // The lower 26 bytes and EOF need separate instruction-version tracing.
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "representative real guest terminations anchor static census"
)]
fn both_non_graphical_dispatch_destination_classes_terminate()
-> Result<(), String> {
    // Byte 27 selects virgin M37. Byte 29 jumps into overwritten M73,
    // whose actual raw value 29 cannot be decoded as an instruction.
    for (byte, next_code, fetched) in
        [(27u8, 37u32, RAW_ONE_TRITS), (29u8, 73u32, 29u32)]
    {
        let (guest, traces, outcome) =
            physical_guest(vec![byte, 255], DISPATCH_STEPS)?;
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::NonGraphicalCell,
            steps: DISPATCH_STEPS,
        });
        let jump = traces.get(24).ok_or("missing physical i")?;
        assert_eq!(jump.decoded, Some(b'i'));
        assert_eq!(jump.after.registers.code_pointer, next_code);
        let refused = traces.get(25).ok_or("missing reached bad fetch")?;
        assert_eq!(refused.before.registers.code_pointer, next_code);
        assert_eq!(refused.fetched_cell, Some(fetched));
        assert_eq!(refused.decoded, None);
        assert_eq!(
            refused.result,
            Ok(StepOutcome::Terminated(Termination::NonGraphicalCell))
        );
        assert_eq!(guest.input_consumed(), 1);
        assert!(guest.output().is_empty());
    }
    Ok(())
}
