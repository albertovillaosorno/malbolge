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
//   - Bounded N15 tests for complementary 141-cell opcode phases and two
//     physical guest code-pointer returns using precomputed source operands.
// - Must-Not:
//   - Claim a permanent loop, mutable-C lowering or state-independent blocks.
// - Allows:
//   - Inputs: two active 141-cell blocks, loader-valid unexecuted source tail,
//     finite binary/EOF streams, and exact normative VM trace data.
//   - Outputs: verified finite return targets and fail-closed source changes.
//   - Side effects: bounded in-memory guest execution only.
// - Split-When:
//   - A generalized block linker admits source-authenticated return contracts.
// - Merge-When:
//   - P4 proof-producing block composition subsumes finite phase experiments.
// - Summary:
//   - A 141-cell opcode half-turn is not a full semantic-state cycle.

//! Research witness for two 141-cell opcode-phase complements, with real
//! source-driven backedges. The final return is intentionally not treated as
//! proof of a stable/infinite machine cycle or a C-to-Malbolge compiler.

// The exact 94/141/282-cell fixture deliberately uses literal indices,
// assertion-driven checks, and bounded arithmetic. These exemptions belong
// only to this test crate; they do not change product compiler policy.
#![expect(
    clippy::indexing_slicing,
    clippy::as_conversions,
    clippy::cast_possible_truncation,
    clippy::arithmetic_side_effects,
    clippy::integer_division_remainder_used,
    clippy::default_numeric_fallback,
    clippy::byte_char_slices,
    clippy::min_ident_chars,
    clippy::type_complexity,
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    reason = "finite position-indexed N15 executable research assertions"
)]

use malbolge::{
    ProfileMachine, ProfileStepTrace, RunOutcome, TraceInput, current_profile,
    decode_profile_instruction, encrypt_profile_cell,
};

const HALF: usize = 141;
const ACTIVE: usize = HALF * 2;
const SOURCE: usize = ACTIVE * 2;
const STEPS: usize = 465;
const FIRST_RETURN: u32 = 100;
const SECOND_RETURN: u32 = 106;

fn encode(operation: u8, position: usize) -> Result<u8, String> {
    let address = u32::try_from(position).map_err(|e| e.to_string())?;
    (33u8..=126)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), address)
                == Some(operation)
        })
        .ok_or_else(|| format!("no graphical {operation} at {position}"))
}

fn half_turn(byte: u8) -> u8 {
    33 + ((byte - 33 + 47) % 94)
}

fn second_decode(operation: u8, position: usize) -> Result<u8, String> {
    let raw = encode(operation, position)?;
    let encrypted = encrypt_profile_cell(u32::from(raw))
        .ok_or_else(|| format!("no encryption at {position}"))?;
    decode_profile_instruction(
        encrypted,
        u32::try_from(position).map_err(|e| e.to_string())?,
    )
    .ok_or_else(|| format!("no revisited decode at {position}"))
}

fn safe_on_second_visit(
    operation: u8,
    position: usize,
) -> Result<bool, String> {
    Ok(!matches!(
        second_decode(operation, position)?,
        b'i' | b'j' | b'v' | b'p' | b'*'
    ))
}

// The optional tail is source code only for initial loader admission; it is
// never fetched in the 465-step witness. M[463] is a *real* graphical byte,
// not a host-provided pointer override or a fake guest trace.
fn candidate_source() -> Result<(Vec<u8>, Vec<u8>), String> {
    let mut operations = vec![b'o'; ACTIVE];
    operations[40] = b'/';
    operations[41] = b'<';
    for offset in 0..140 {
        let second = offset + HALF;
        if matches!(offset, 40 | 41) {
            operations[second] = operations[offset];
            continue;
        }
        let mut paired = None;
        for operation in [b'o', b'<', b'/'] {
            if safe_on_second_visit(operation, second)?
                && (offset < 100 || safe_on_second_visit(operation, offset)?)
            {
                paired = Some(operation);
                break;
            }
        }
        if let Some(operation) = paired {
            operations[offset] = operation;
            operations[second] = operation;
        } else {
            operations[offset] = [b'o', b'<', b'/']
                .into_iter()
                .find(|&operation| {
                    offset < 100
                        || safe_on_second_visit(operation, offset)
                            .is_ok_and(|safe| safe)
                })
                .ok_or_else(|| format!("no safe first half at {offset}"))?;
            operations[second] = [b'o', b'<', b'/']
                .into_iter()
                .find(|&operation| {
                    safe_on_second_visit(operation, second)
                        .is_ok_and(|safe| safe)
                })
                .ok_or_else(|| format!("no safe second half at {second}"))?;
        }
    }
    operations[281] = b'i';
    for (position, operation) in
        operations.iter().enumerate().take(281).skip(100)
    {
        assert!(
            safe_on_second_visit(*operation, position)?,
            "second visit would take an unplanned effect at {position}"
        );
    }
    let mut source = (0..SOURCE)
        .map(|position| {
            let operation = operations.get(position).copied().unwrap_or(b'o');
            encode(operation, position)
        })
        .collect::<Result<Vec<_>, String>>()?;
    source[463] = 105;
    assert_eq!(decode_profile_instruction(105, 463), Some(b'i'));
    Ok((source, operations))
}

#[test]
fn all_opcode_half_turn_phases_are_exact_but_not_identical_source_bytes()
-> Result<(), String> {
    for byte in 33u8..=126 {
        assert_eq!(half_turn(half_turn(byte)), byte);
    }
    for phase in 0..94 {
        for opcode in b"ji*p</vo" {
            let original = encode(*opcode, phase)?;
            let shifted = half_turn(original);
            assert_ne!(original, shifted);
            assert_eq!(
                decode_profile_instruction(
                    u32::from(shifted),
                    (phase + HALF) as u32
                ),
                Some(*opcode)
            );
            assert_eq!(
                decode_profile_instruction(
                    u32::from(original),
                    (phase + ACTIVE) as u32
                ),
                Some(*opcode)
            );
        }
    }
    Ok(())
}

fn expected_opcode(
    source: &[u8],
    operations: &[u8],
    step: usize,
) -> Result<u8, String> {
    if step < ACTIVE {
        return operations
            .get(step)
            .copied()
            .ok_or_else(|| format!("missing first-pass step {step}"));
    }
    let position = if step < STEPS - 1 {
        step - ACTIVE + 100
    } else {
        SECOND_RETURN as usize
    };
    if position == 281 {
        return Ok(b'i');
    }
    let mut word = u32::from(
        *source
            .get(position)
            .ok_or_else(|| format!("missing source byte at {position}"))?,
    );
    // At the 465th step, C106 is fetched for a third time. Earlier ordinary
    // execution encrypted it twice; the C281 code jumps encrypt C99 and C105.
    let visits = if step == STEPS - 1 {
        2
    } else {
        1
    };
    for _ in 0..visits {
        word = encrypt_profile_cell(word)
            .ok_or_else(|| format!("missing XLAT2 at {position}"))?;
    }
    decode_profile_instruction(word, position as u32)
        .ok_or_else(|| format!("missing decoded instruction at {position}"))
}

// The oracle uses the frozen source encoding and the independently expected
// physical path, not the VM's reported input/output values, to predict bytes.
fn assert_one_input(
    source: &[u8],
    operations: &[u8],
    input: &[u8],
) -> Result<(), String> {
    let mut machine =
        ProfileMachine::from_source(current_profile(), source, input.to_vec())
            .map_err(|error| error.to_string())?;
    let mut traces: Vec<ProfileStepTrace> = Vec::new();
    let outcome = machine
        .run_traced(STEPS, &mut |trace| traces.push(*trace))
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::BudgetExhausted { steps: STEPS });
    assert_eq!(traces.len(), STEPS);
    let mut accumulator = 0u32;
    let mut consumed = 0usize;
    let mut output = Vec::new();
    for (step, trace) in traces.iter().enumerate() {
        let code = if step < ACTIVE {
            step
        } else if step < STEPS - 1 {
            step - ACTIVE + 100
        } else {
            SECOND_RETURN as usize
        };
        let data = step;
        assert_eq!(trace.before.registers.code_pointer, code as u32);
        assert_eq!(trace.before.registers.data_pointer, data as u32);
        let operation = expected_opcode(source, operations, step)?;
        assert_eq!(trace.decoded, Some(operation));
        match operation {
            b'/' => {
                if let Some(&byte) = input.get(consumed) {
                    accumulator = u32::from(byte);
                    consumed += 1;
                    assert_eq!(trace.input, Some(TraceInput::Byte(byte)));
                } else {
                    accumulator = current_profile().eof_word();
                    assert_eq!(trace.input, Some(TraceInput::EndOfInput));
                }
                assert_eq!(trace.after.registers.accumulator, accumulator);
            },
            b'<' => {
                let byte = (accumulator & 255) as u8;
                output.push(byte);
                assert_eq!(trace.output, Some(byte));
            },
            b'i' if step == ACTIVE - 1 => {
                assert_eq!(
                    trace.memory_reads.data.map(|read| read.value),
                    Some(99)
                );
                assert_eq!(trace.after.registers.code_pointer, FIRST_RETURN);
                assert_eq!(
                    trace.memory_reads.encryption.map(|read| read.address),
                    Some(99)
                );
            },
            b'i' if step == STEPS - 2 => {
                assert_eq!(
                    trace.memory_reads.data.map(|read| read.value),
                    Some(105)
                );
                assert_eq!(trace.after.registers.code_pointer, SECOND_RETURN);
                assert_eq!(
                    trace.memory_reads.encryption.map(|read| read.address),
                    Some(105)
                );
            },
            _ => {
                assert!(
                    !matches!(operation, b'i' | b'j' | b'p' | b'*' | b'v'),
                    "unplanned control/data write at step {step}"
                );
            },
        }
    }
    assert_eq!(machine.input_consumed(), consumed);
    assert_eq!(machine.output(), output);
    Ok(())
}

#[test]
fn real_n15_guest_executes_two_source_driven_backward_returns()
-> Result<(), String> {
    let (source, operations) = candidate_source()?;
    let matched = (0..140)
        .filter(|&offset| source[offset + HALF] == half_turn(source[offset]))
        .count();
    assert_eq!(matched, 139);
    for input in [vec![], vec![0], vec![0x80], vec![0xff], vec![1, 2]] {
        assert_one_input(&source, &operations, &input)?;
    }
    Ok(())
}

#[test]
fn altered_rear_source_operand_does_not_prove_the_same_return()
-> Result<(), String> {
    let (mut source, operations) = candidate_source()?;
    source[463] = 106; // Loader-valid at C463, but returns C107, not C106.
    assert_eq!(decode_profile_instruction(106, 463), Some(b'<'));
    let mut machine =
        ProfileMachine::from_source(current_profile(), &source, vec![1, 2])
            .map_err(|error| error.to_string())?;
    let mut backedges = Vec::new();
    let outcome = machine
        .run_traced(STEPS - 1, &mut |trace| {
            if trace.before.registers.code_pointer == 281 {
                backedges.push((
                    trace.memory_reads.data.map(|read| read.value),
                    trace.after.registers.code_pointer,
                ));
            }
        })
        .map_err(|error| error.to_string())?;
    assert_eq!(outcome, RunOutcome::BudgetExhausted { steps: STEPS - 1 });
    assert_eq!(backedges, [(Some(99), FIRST_RETURN), (Some(106), 107)]);
    assert_ne!(backedges[1].1, SECOND_RETURN);
    assert_eq!(operations[281], b'i');
    Ok(())
}
