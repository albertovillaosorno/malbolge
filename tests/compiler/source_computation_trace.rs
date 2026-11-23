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
//   - Actual N15 word-store and typed-computation result counterexamples.
// - Must-Not:
//   - Treat a seeded guest state as emitted source-C arithmetic.
// - Allows:
//   - Inputs: finite real VM instructions and independent source obligations.
//   - Outputs: exact positive/negative verifier outcomes.
//   - Side effects: isolated normative VM execution only.
// - Split-When:
//   - End-to-end source-C arithmetic guest parity supersedes these probes.
// - Merge-When:
//   - Full source-C physical CFG regressions use the same strict checker.
// - Summary:
//   - Numeric coincidence must not authorize a wrong source-computed word.

use super::*;

fn graphical(position: usize, opcode: u8) -> Result<u8, String> {
    (33..=126)
        .find(|byte| {
            malbolge::decode_profile_instruction(
                u32::from(*byte),
                u32::try_from(position).unwrap_or(u32::MAX),
            ) == Some(opcode)
        })
        .ok_or_else(|| format!("no graphical {opcode} at {position}"))
}

// These are genuine N15 guest stores, not synthetic trace structs. Source
// C0-C2 rotates M70/M71/M72 and C3 halts. Seeding 3,6,9 makes the *actual*
// three stored values 1,2,3; seeding M72=6 changes only the result to 2.
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "fixed real four-step guest witness and exact terminal assertion"
)]
fn traced_three_stores_with_seeds(
    seeds: [u32; 3],
) -> Result<Vec<ProfileStepTrace>, String> {
    let mut source = (0..59)
        .map(|at| graphical(at, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (at, opcode) in [(0, b'*'), (1, b'*'), (2, b'*'), (3, b'v')] {
        source[at] = graphical(at, opcode)?;
    }
    let profile = malbolge::current_profile();
    let loaded =
        malbolge::ProfileMachine::from_source(profile, &source, Vec::new())
            .map_err(|error| format!("source load: {error:?}"))?;
    let mut memory = loaded.memory().to_vec();
    for (offset, value) in seeds.into_iter().enumerate() {
        memory[70usize.saturating_add(offset)] = value;
    }
    let registers = malbolge::ProfileRegisters {
        accumulator: profile.eof_word(),
        code_pointer: 0,
        data_pointer: 70,
    };
    let mut machine = malbolge::ProfileMachine::from_state(
        profile,
        memory,
        Vec::new(),
        registers,
    )
    .map_err(|error| format!("state load: {error:?}"))?;
    let mut steps = Vec::new();
    let outcome = machine
        .run_traced(4, &mut |step| steps.push(*step))
        .map_err(|error| format!("guest run: {error:?}"))?;
    assert_eq!(outcome, malbolge::RunOutcome::Terminated {
        reason: malbolge::Termination::HaltInstruction,
        steps: 4,
    });
    Ok(steps)
}

fn traced_three_stores(
    result_seed: u32,
) -> Result<Vec<ProfileStepTrace>, String> {
    traced_three_stores_with_seeds([3, 6, result_seed])
}

fn operand(address: u32, value: u32) -> GuestPlacedOperand {
    GuestPlacedOperand {
        address,
        type_kind: TernaryCfgScalarKind::U8,
        value,
        words: 1,
    }
}

fn computation(operation: BinaryOp) -> GuestCodeComputation {
    GuestCodeComputation::Binary {
        operation,
        left: operand(70, 0),
        right: operand(71, 1),
        result: operand(72, 2),
    }
}

fn operations(
    computation: GuestCodeComputation,
) -> [GuestCodeOperationSite; 1] {
    [GuestCodeOperationSite {
        block: 0,
        computation: Some(computation),
        start: 2,
        end_exclusive: 3,
        function: 0,
        ordinal: 2,
    }]
}

fn effects() -> [GuestCodeOperationEffectSite; 3] {
    [70u32, 71, 72].map(|destination| GuestCodeOperationEffectSite {
        block: 0,
        code_address: destination.saturating_sub(70),
        effect: GuestCodeOperationEffect::Store {
            destination,
            literal: None,
        },
        function: 0,
        ordinal: destination.saturating_sub(70),
    })
}

fn frames() -> [GuestFramePlacement; 1] {
    [GuestFramePlacement {
        base: 70,
        end_exclusive: 73,
        source_cells: 59,
    }]
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "one real guest control and strict numerical failure matrix"
)]
fn real_guest_computed_result_requires_correct_typed_operation()
-> Result<(), String> {
    let correct = traced_three_stores(9)?;
    let incorrect = traced_three_stores(6)?;
    let witness = operations(computation(BinaryOp::Xor));
    let placed = effects();
    let frame = frames();
    assert_eq!(
        verify_source_computation_values(
            &witness,
            &placed,
            &[],
            &frame,
            &correct
        ),
        Ok(())
    );
    assert_eq!(
        verify_source_computation_values(
            &witness,
            &placed,
            &[],
            &frame,
            &incorrect
        ),
        Err(SourcePhiCopyTraceError::InvalidComputationValue)
    );
    assert_eq!(
        verify_source_computation_values(
            &operations(computation(BinaryOp::And)),
            &placed,
            &[],
            &frame,
            &correct,
        ),
        Err(SourcePhiCopyTraceError::InvalidComputationValue)
    );
    let unmaterialized = GuestCodeComputation::Binary {
        operation: BinaryOp::Xor,
        left: operand(73, 3),
        right: operand(71, 1),
        result: operand(72, 2),
    };
    assert_eq!(
        verify_source_computation_values(
            &operations(unmaterialized),
            &placed,
            &[],
            &frame,
            &correct,
        ),
        Err(SourcePhiCopyTraceError::MissingComputationOperand)
    );
    assert_eq!(
        verify_source_computation_values(
            &operations(computation(BinaryOp::DivideUnsigned)),
            &placed,
            &[],
            &frame,
            &correct,
        ),
        Err(SourcePhiCopyTraceError::UnsupportedComputation)
    );
    Ok(())
}

// C1 and C2 perform two physical writes of one C32 SSA result. Matching the
// low word is insufficient: a second genuine guest rotation at the high-word
// site must preserve the complete source-typed zero extension.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "two real guest executions check both C32 result words"
)]
fn real_guest_two_word_computation_rejects_wrong_high_result_word()
-> Result<(), String> {
    let valid = traced_three_stores_with_seeds([6, 6, 0])?;
    let high_corrupted = traced_three_stores_with_seeds([6, 6, 3])?;
    let source = operand(70, 0);
    let result = GuestPlacedOperand {
        address: 71,
        type_kind: TernaryCfgScalarKind::U32,
        value: 1,
        words: 2,
    };
    let sites = [GuestCodeOperationSite {
        block: 0,
        computation: Some(GuestCodeComputation::Cast {
            operation: CastOp::ZeroExtend,
            source,
            result,
        }),
        start: 1,
        end_exclusive: 3,
        function: 0,
        ordinal: 1,
    }];
    let effects = [
        GuestCodeOperationEffectSite {
            block: 0,
            code_address: 0,
            effect: GuestCodeOperationEffect::Store {
                destination: 70,
                literal: None,
            },
            function: 0,
            ordinal: 0,
        },
        GuestCodeOperationEffectSite {
            block: 0,
            code_address: 1,
            effect: GuestCodeOperationEffect::Store {
                destination: 71,
                literal: None,
            },
            function: 0,
            ordinal: 1,
        },
        GuestCodeOperationEffectSite {
            block: 0,
            code_address: 2,
            effect: GuestCodeOperationEffect::Store {
                destination: 72,
                literal: None,
            },
            function: 0,
            ordinal: 1,
        },
    ];
    let frame = frames();
    assert_eq!(
        verify_source_computation_values(&sites, &effects, &[], &frame, &valid),
        Ok(()),
    );
    assert_eq!(
        verify_source_computation_values(
            &sites,
            &effects,
            &[],
            &frame,
            &high_corrupted,
        ),
        Err(SourcePhiCopyTraceError::InvalidComputationValue),
    );
    Ok(())
}

#[test]
fn typed_c32_checksum_operations_preserve_full_width() {
    let i32_operand = |address, value| GuestPlacedOperand {
        address,
        type_kind: TernaryCfgScalarKind::U32,
        value,
        words: 2,
    };
    let mut journal = BTreeMap::new();
    for (offset, word) in encode_i32_cells(0xffff_fffe).into_iter().enumerate()
    {
        _ = journal.insert(
            70u32.saturating_add(u32::try_from(offset).unwrap_or(u32::MAX)),
            word,
        );
    }
    for (offset, word) in encode_i32_cells(4).into_iter().enumerate() {
        _ = journal.insert(
            72u32.saturating_add(u32::try_from(offset).unwrap_or(u32::MAX)),
            word,
        );
    }
    let arithmetic = GuestCodeComputation::Binary {
        operation: BinaryOp::Add,
        left: i32_operand(70, 0),
        right: i32_operand(72, 1),
        result: i32_operand(74, 2),
    };
    assert_eq!(evaluate(arithmetic, &journal), Ok(2));
    let compare = GuestCodeComputation::Compare {
        operation: CompareOp::NotEqual,
        left: i32_operand(70, 0),
        right: i32_operand(72, 1),
        result: GuestPlacedOperand {
            address: 76,
            type_kind: TernaryCfgScalarKind::Bool,
            value: 3,
            words: 1,
        },
    };
    assert_eq!(evaluate(compare, &journal), Ok(1));
    let cast = GuestCodeComputation::Cast {
        operation: CastOp::Truncate,
        source: i32_operand(70, 0),
        result: operand(77, 4),
    };
    assert_eq!(evaluate(cast, &journal), Ok(254));
}
