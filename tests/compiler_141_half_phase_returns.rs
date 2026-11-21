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

// A physical return alone does not supply the live-in state required for
// reusable code. The bounded test captures source-authenticated state.
#[derive(Clone, Debug, Eq, PartialEq)]
struct ReturnEntryState {
    accumulator: u32,
    code_pointer: u32,
    common_code_word: u32,
    data_pointer: u32,
    input_consumed: usize,
    output: Vec<u8>,
}

fn encode(operation: u8, position: usize) -> Result<u8, String> {
    let address = u32::try_from(position).map_err(|e| e.to_string())?;
    (33u8..=126)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), address)
                == Some(operation)
        })
        .ok_or_else(|| format!("no graphical {operation} at {position}"))
}

const fn half_turn(byte: u8) -> u8 {
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
    assert_eq!(
        decode_profile_instruction(105, 463),
        Some(b'i'),
        "source second-return operand must decode as a physical jump",
    );
    Ok((source, operations))
}

// A third traversal fetches C106..C280 after *two* prior encryptions.
// Keep both earlier traversals valid while selecting safe third-visit code.
fn safe_on_third_visit(operation: u8, position: usize) -> Result<bool, String> {
    let raw = encode(operation, position)?;
    let first = encrypt_profile_cell(u32::from(raw))
        .ok_or_else(|| format!("no first encryption at {position}"))?;
    let second = encrypt_profile_cell(first)
        .ok_or_else(|| format!("no second encryption at {position}"))?;
    Ok(!matches!(
        decode_profile_instruction(second, position as u32),
        Some(b'i' | b'j' | b'v' | b'p' | b'*') | None
    ))
}

fn three_return_source() -> Result<(Vec<u8>, Vec<u8>, usize), String> {
    let (mut source, mut operations) = candidate_source()?;
    let mut repairs = 0;
    for position in 106..281 {
        if safe_on_third_visit(operations[position], position)? {
            continue;
        }
        let replacement = [b'o', b'<', b'/']
            .into_iter()
            .find(|operation| {
                safe_on_second_visit(*operation, position).unwrap_or(false)
                    && safe_on_third_visit(*operation, position)
                        .unwrap_or(false)
            })
            .ok_or_else(|| {
                format!("no third-visit-safe source at {position}")
            })?;
        source[position] = encode(replacement, position)?;
        operations[position] = replacement;
        repairs += 1;
    }
    // The final two source characters are not executed. They seed the
    // 6-period loader recurrence: M639=119, so third `i` at C281 lands C120.
    source[562] = 41;
    source[563] = 118;
    for (position, &operation) in
        operations.iter().enumerate().take(281).skip(106)
    {
        assert!(
            safe_on_second_visit(operation, position)?,
            "third-return candidate has unsafe second visit at {position}",
        );
        assert!(
            safe_on_third_visit(operation, position)?,
            "third-return candidate has unsafe third visit at {position}",
        );
    }
    Ok((source, operations, repairs))
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
    assert_eq!(
        outcome,
        RunOutcome::BudgetExhausted { steps: STEPS },
        "two-return prefix must consume exactly the frozen step budget",
    );
    assert_eq!(traces.len(), STEPS, "trace must cover every step");
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
        assert_eq!(
            trace.before.registers.code_pointer, code as u32,
            "source-locked code path differs at step {step}",
        );
        assert_eq!(
            trace.before.registers.data_pointer, data as u32,
            "source-locked data path differs at step {step}",
        );
        let operation = expected_opcode(source, operations, step)?;
        assert_eq!(
            trace.decoded,
            Some(operation),
            "source-derived operation differs at step {step}",
        );
        match operation {
            b'/' => {
                if let Some(&byte) = input.get(consumed) {
                    accumulator = u32::from(byte);
                    consumed += 1;
                    assert_eq!(
                        trace.input,
                        Some(TraceInput::Byte(byte)),
                        "input byte differs at step {step}",
                    );
                } else {
                    accumulator = current_profile().eof_word();
                    assert_eq!(
                        trace.input,
                        Some(TraceInput::EndOfInput),
                        "EOF event differs at step {step}",
                    );
                }
                assert_eq!(
                    trace.after.registers.accumulator, accumulator,
                    "guest input accumulator differs at step {step}",
                );
            },
            b'<' => {
                let byte = (accumulator & 255) as u8;
                output.push(byte);
                assert_eq!(
                    trace.output,
                    Some(byte),
                    "guest output differs at step {step}",
                );
            },
            b'i' if step == ACTIVE - 1 => {
                assert_eq!(
                    trace.memory_reads.data.map(|read| read.value),
                    Some(99),
                    "first physical return must read loader word 99",
                );
                assert_eq!(
                    trace.after.registers.code_pointer, FIRST_RETURN,
                    "first physical return destination must be C100",
                );
                assert_eq!(
                    trace.memory_reads.encryption.map(|read| read.address),
                    Some(99),
                    "first physical return must read loader word 99",
                );
            },
            b'i' if step == STEPS - 2 => {
                assert_eq!(
                    trace.memory_reads.data.map(|read| read.value),
                    Some(105),
                    "second physical return must read loader word 105",
                );
                assert_eq!(
                    trace.after.registers.code_pointer, SECOND_RETURN,
                    "second physical return destination must be C106",
                );
                assert_eq!(
                    trace.memory_reads.encryption.map(|read| read.address),
                    Some(105),
                    "second physical return must read loader word 105",
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
    assert_eq!(
        machine.input_consumed(),
        consumed,
        "input consumption must match the source-locked trace oracle",
    );
    assert_eq!(
        machine.output(),
        output,
        "guest output must match the source-locked trace oracle",
    );
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

fn revisited_code_word(
    source: &[u8],
    position: usize,
    visits: usize,
) -> Result<u32, String> {
    let mut word = u32::from(source[position]);
    let encryptions = if position == 281 {
        0
    } else {
        visits
    };
    for _ in 0..encryptions {
        word = encrypt_profile_cell(word)
            .ok_or("missing independently expected encryption")?;
    }
    Ok(word)
}

fn expected_next_input(
    input: &[u8],
    consumed: &mut usize,
) -> (u32, TraceInput) {
    if let Some(&byte) = input.get(*consumed) {
        *consumed += 1;
        (u32::from(byte), TraceInput::Byte(byte))
    } else {
        (current_profile().eof_word(), TraceInput::EndOfInput)
    }
}

// Two earlier guest backedges are not evidence of a third. This checks
// the complete source-driven third traversal including code mutation,
// loader-seeded D639 and actual input/EOF effects on five finite streams.
#[test]
fn real_n15_guest_executes_third_return_after_safe_revisits()
-> Result<(), String> {
    const THREE_RETURNS: usize = 640;
    let (source, operations, repairs) = three_return_source()?;
    assert_eq!(source.len(), SOURCE);
    assert_eq!(repairs, 6, "six third-visit code hazards need repair");
    assert_eq!(
        (0..140)
            .filter(|&offset| {
                source[offset + HALF] == half_turn(source[offset])
            })
            .count(),
        133,
    );
    for input in [vec![], vec![0], vec![0x80], vec![0xff], vec![1, 2]] {
        let mut machine = ProfileMachine::from_source(
            current_profile(),
            &source,
            input.clone(),
        )
        .map_err(|error| error.to_string())?;
        assert_eq!(machine.memory_word(639), Ok(119));
        assert_eq!(machine.memory_word(463), Ok(105));
        let mut traces = Vec::new();
        let outcome = machine
            .run_traced(THREE_RETURNS, &mut |trace| traces.push(*trace))
            .map_err(|error| error.to_string())?;
        assert_eq!(outcome, RunOutcome::BudgetExhausted {
            steps: THREE_RETURNS,
        });
        assert_eq!(traces.len(), THREE_RETURNS);
        let mut consumed = 0;
        let mut accumulator = 0;
        let mut expected_output = Vec::new();
        let mut returns = Vec::new();
        for (step, trace) in traces.iter().enumerate() {
            let (position, visits) = if step < 282 {
                (step, 0)
            } else if step < 464 {
                (step - 282 + 100, 1)
            } else {
                (step - 464 + 106, 2)
            };
            assert_eq!(trace.before.registers.code_pointer, position as u32);
            assert_eq!(trace.before.registers.data_pointer, step as u32);
            let encoded = revisited_code_word(&source, position, visits)?;
            let opcode = decode_profile_instruction(encoded, position as u32)
                .ok_or("invalid independently expected opcode")?;
            assert_eq!(trace.decoded, Some(opcode));
            assert_eq!(
                trace
                    .memory_reads
                    .fetch
                    .map(|read| (read.address, read.value)),
                Some((position as u32, encoded)),
            );
            let encryption = trace
                .memory_delta
                .encryption
                .ok_or("missing physical source-code encryption")?;
            assert_eq!(
                encryption.after,
                encrypt_profile_cell(encryption.before)
                    .ok_or("unexpected non-graphical encryption source")?,
            );
            if position != 281 {
                assert_eq!(encryption.address, position as u32);
                assert_eq!(encryption.before, encoded);
            }
            if visits == 0 {
                assert_eq!(opcode, operations[position]);
            }
            match opcode {
                b'/' => {
                    let expected_input;
                    (accumulator, expected_input) =
                        expected_next_input(&input, &mut consumed);
                    assert_eq!(trace.input, Some(expected_input));
                    assert_eq!(trace.after.registers.accumulator, accumulator);
                },
                b'<' => {
                    let byte = (accumulator & 255) as u8;
                    expected_output.push(byte);
                    assert_eq!(trace.output, Some(byte));
                },
                b'i' => {
                    assert_eq!(position, 281);
                    let (data_word, landing) = match visits {
                        0 => (99, 100),
                        1 => (105, 106),
                        2 => (119, 120),
                        _ => return Err("unexpected fourth return".to_owned()),
                    };
                    assert_eq!(
                        trace.memory_reads.data.map(|read| read.value),
                        Some(data_word)
                    );
                    assert_eq!(trace.after.registers.code_pointer, landing);
                    assert_eq!(
                        trace.memory_reads.encryption.map(|read| read.address),
                        Some(data_word)
                    );
                    returns
                        .push((trace.before.registers.data_pointer, landing));
                },
                _ => assert!(!matches!(opcode, b'j' | b'v' | b'p' | b'*')),
            }
        }
        assert_eq!(returns, [(281, 100), (463, 106), (639, 120)]);
        assert_eq!(machine.input_consumed(), consumed);
        assert_eq!(machine.output(), expected_output);
    }
    Ok(())
}

#[test]
fn changed_loader_tail_changes_third_return_without_changing_first_two()
-> Result<(), String> {
    let (mut source, _, _) = three_return_source()?;
    source[563] = 99; // M639=99, so the third return would land C100.
    let mut machine =
        ProfileMachine::from_source(current_profile(), &source, vec![1, 2])
            .map_err(|error| error.to_string())?;
    assert_eq!(machine.memory_word(639), Ok(99));
    let mut backedges = Vec::new();
    let result = machine
        .run_traced(640, &mut |trace| {
            if trace.before.registers.code_pointer == 281 {
                backedges.push(trace.after.registers.code_pointer);
            }
        })
        .map_err(|error| error.to_string())?;
    assert_eq!(result, RunOutcome::BudgetExhausted { steps: 640 });
    assert_eq!(backedges, [100, 106, 100]);
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

// Observe real return boundaries, not host-restored snapshots or a
// synthetic preloaded pointer.

fn three_return_entry_states(
    source: &[u8],
    input: &[u8],
) -> Result<Vec<ReturnEntryState>, String> {
    let mut machine =
        ProfileMachine::from_source(current_profile(), source, input.to_vec())
            .map_err(|error| error.to_string())?;
    let mut boundaries = Vec::new();
    for _ in 0..640 {
        let mut return_trace = None;
        let outcome = machine
            .step_traced(&mut |trace| {
                if trace.before.registers.code_pointer == 281 {
                    return_trace = Some(*trace);
                }
            })
            .map_err(|error| error.to_string())?;
        assert_eq!(
            outcome,
            malbolge::StepOutcome::Continued,
            "physical return-boundary trace must remain executable",
        );
        if let Some(trace) = return_trace {
            assert_eq!(trace.decoded, Some(b'i'), "expected physical return");
            assert_eq!(
                trace.before.registers.code_pointer, 281,
                "return must execute from physical C281",
            );
            let registers = machine.registers();
            assert_eq!(
                trace.after.registers, registers,
                "trace must reflect committed guest registers",
            );
            boundaries.push(ReturnEntryState {
                accumulator: registers.accumulator,
                code_pointer: registers.code_pointer,
                // All three traversals already visited physical C120. It
                // cannot be treated as the same live code state on reentry.
                common_code_word: machine
                    .memory_word(120)
                    .map_err(|error| error.to_string())?,
                data_pointer: registers.data_pointer,
                input_consumed: machine.input_consumed(),
                output: machine.output().to_vec(),
            });
        }
    }
    Ok(boundaries)
}

#[test]
fn repeated_physical_returns_do_not_restore_a_guest_state_contract()
-> Result<(), String> {
    let (source, _, repairs) = three_return_source()?;
    assert_eq!(repairs, 6);
    let mut last_code = u32::from(source[120]);
    let mut independently_encrypted_code = Vec::new();
    for _ in 0..3 {
        last_code = encrypt_profile_cell(last_code)
            .ok_or("source code at C120 failed to encrypt")?;
        independently_encrypted_code.push(last_code);
    }
    assert_eq!(
        independently_encrypted_code.len(),
        3,
        "all three physical guest visits have an expected state",
    );
    for input in [vec![], vec![0], vec![0x80], vec![0xff], vec![1, 2]] {
        let states = three_return_entry_states(&source, &input)?;
        assert_eq!(states.len(), 3);
        for (index, state) in states.iter().enumerate() {
            assert_eq!(state.code_pointer, [100, 106, 120][index]);
            assert_eq!(state.data_pointer, [282, 464, 640][index]);
            assert_eq!(
                state.common_code_word,
                independently_encrypted_code[index]
            );
        }
        for pair in states.windows(2) {
            let [first, second] = pair else {
                return Err(
                    "expected exactly two adjacent boundaries".to_owned()
                );
            };
            assert_ne!(first.data_pointer, second.data_pointer);
            assert_ne!(first.common_code_word, second.common_code_word);
        }
    }
    Ok(())
}

#[test]
fn same_three_return_code_path_does_not_erase_binary_input_state()
-> Result<(), String> {
    let (source, _, _) = three_return_source()?;
    let eof = three_return_entry_states(&source, &[])?;
    let high_byte = three_return_entry_states(&source, &[0x80])?;
    assert_eq!(eof.len(), 3);
    assert_eq!(high_byte.len(), 3);
    for (empty, high) in eof.iter().zip(&high_byte) {
        // Same immutable source and real guest control path do not imply
        // interchangeable source-sensitive block contracts.
        assert_eq!(empty.code_pointer, high.code_pointer);
        assert_eq!(empty.data_pointer, high.data_pointer);
        assert_eq!(empty.common_code_word, high.common_code_word);
        assert_eq!(empty.input_consumed, 0);
        assert_eq!(high.input_consumed, 1);
        assert_ne!(empty.output, high.output);
    }
    Ok(())
}
