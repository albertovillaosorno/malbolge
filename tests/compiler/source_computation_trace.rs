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
        Err(SourcePhiCopyTraceError::InvalidComputationValue)
    );
    assert_eq!(
        verify_source_computation_values(
            &operations(computation(BinaryOp::DivideFloat)),
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

// C1's real indirect transfer skips the low C32 result store at C2 but
// reaches the high-word site C3 with the expected zero. The numeric checker
// must not certify the complete result solely from that last site.
#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "five-cell physical jump with a skipped source store"
)]
fn real_guest_skipped_low_word_store_cannot_certify_a_c32_result()
-> Result<(), String> {
    let mut source = (0..59)
        .map(|at| graphical(at, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (at, opcode) in [(0, b'*'), (1, b'i'), (2, b'*'), (3, b'*'), (4, b'v')]
    {
        source[at] = graphical(at, opcode)?;
    }
    let profile = malbolge::current_profile();
    let loaded =
        malbolge::ProfileMachine::from_source(profile, &source, Vec::new())
            .map_err(|error| format!("source load: {error:?}"))?;
    let mut memory = loaded.memory().to_vec();
    // C0 rotates M70=3 to 1. C1 i reads M71=2 and jumps to C3,
    // bypassing the promised M71 low-word result at C2. C3 rotates
    // M72=0 to the numerically correct high word 0 and C4 halts.
    memory[70] = 3;
    memory[71] = 2;
    memory[72] = 0;
    let mut machine = malbolge::ProfileMachine::from_state(
        profile,
        memory,
        Vec::new(),
        malbolge::ProfileRegisters {
            accumulator: profile.eof_word(),
            code_pointer: 0,
            data_pointer: 70,
        },
    )
    .map_err(|error| format!("state load: {error:?}"))?;
    let mut steps = Vec::new();
    let outcome = machine
        .run_traced(5, &mut |step| steps.push(*step))
        .map_err(|error| format!("guest run: {error:?}"))?;
    assert_eq!(outcome, malbolge::RunOutcome::Terminated {
        reason: malbolge::Termination::HaltInstruction,
        steps: 4,
    });
    assert_eq!(
        steps
            .iter()
            .map(|step| step.before.registers.code_pointer)
            .collect::<Vec<_>>(),
        [0, 1, 3, 4],
    );
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
            source: operand(70, 0),
            result,
        }),
        start: 2,
        end_exclusive: 4,
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
            code_address: 2,
            effect: GuestCodeOperationEffect::Store {
                destination: 71,
                literal: None,
            },
            function: 0,
            ordinal: 1,
        },
        GuestCodeOperationEffectSite {
            block: 0,
            code_address: 3,
            effect: GuestCodeOperationEffect::Store {
                destination: 72,
                literal: None,
            },
            function: 0,
            ordinal: 1,
        },
    ];
    assert_eq!(
        verify_source_computation_values(
            &sites,
            &effects,
            &[],
            &frames(),
            &steps
        ),
        Err(SourcePhiCopyTraceError::MissingBlockEffect),
    );
    Ok(())
}

// The full source-typed result need not be stored low word first. A real
// N15 j sets D to a higher frame address for C2's high-word *, then a
// second j retargets C4's low-word *. This is *not* C computation causality;
// it isolates exact physical two-word result checking under address reorder.
#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "a six-step physical N15 data-pointer reversal"
)]
fn real_guest_high_word_before_low_word_authenticates_c32_result()
-> Result<(), String> {
    let mut source = (0..59)
        .map(|at| graphical(at, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (at, opcode) in [
        (0, b'*'),
        (1, b'j'),
        (2, b'*'),
        (3, b'j'),
        (4, b'*'),
        (5, b'v'),
    ] {
        source[at] = graphical(at, opcode)?;
    }
    let profile = malbolge::current_profile();
    let loaded =
        malbolge::ProfileMachine::from_source(profile, &source, Vec::new())
            .map_err(|error| format!("source load: {error:?}"))?;
    let trace = |high_seed: u32| -> Result<Vec<ProfileStepTrace>, String> {
        let mut memory = loaded.memory().to_vec();
        memory[70] = 3; // C0 * materializes U8 1.
        memory[71] = 100; // C1 j selects D=101 after increment.
        memory[101] = high_seed; // C2 * writes high word first.
        memory[102] = 99; // C3 j selects D=100 after increment.
        memory[100] = 3; // C4 * writes low word 1.
        let mut machine = malbolge::ProfileMachine::from_state(
            profile,
            memory,
            Vec::new(),
            malbolge::ProfileRegisters {
                accumulator: profile.eof_word(),
                code_pointer: 0,
                data_pointer: 70,
            },
        )
        .map_err(|error| format!("seeded guest: {error:?}"))?;
        let mut steps = Vec::new();
        let outcome = machine
            .run_traced(6, &mut |step| steps.push(*step))
            .map_err(|error| format!("guest run: {error:?}"))?;
        assert_eq!(outcome, malbolge::RunOutcome::Terminated {
            reason: malbolge::Termination::HaltInstruction,
            steps: 6,
        });
        assert_eq!(
            steps
                .iter()
                .map(|step| step.before.registers.code_pointer)
                .collect::<Vec<_>>(),
            [0, 1, 2, 3, 4, 5],
        );
        assert_eq!(
            steps
                .iter()
                .map(|step| step.before.registers.data_pointer)
                .collect::<Vec<_>>(),
            [70, 71, 101, 102, 100, 101],
        );
        Ok(steps)
    };
    let valid = trace(0)?;
    let high_corrupted = trace(3)?;
    let result = GuestPlacedOperand {
        address: 100,
        type_kind: TernaryCfgScalarKind::U32,
        value: 1,
        words: 2,
    };
    let sites = [GuestCodeOperationSite {
        block: 0,
        computation: Some(GuestCodeComputation::Cast {
            operation: CastOp::ZeroExtend,
            source: operand(70, 0),
            result,
        }),
        start: 2,
        end_exclusive: 5,
        function: 0,
        ordinal: 1,
    }];
    let effects = [(0u32, 70u32, 0u32), (2, 101, 1), (4, 100, 1)].map(
        |(code_address, destination, ordinal)| GuestCodeOperationEffectSite {
            block: 0,
            code_address,
            effect: GuestCodeOperationEffect::Store {
                destination,
                literal: None,
            },
            function: 0,
            ordinal,
        },
    );
    let frames = [GuestFramePlacement {
        base: 70,
        end_exclusive: 103,
        source_cells: 59,
    }];
    assert_eq!(
        verify_source_computation_values(
            &sites,
            &effects,
            &[],
            &frames,
            &valid
        ),
        Ok(()),
    );
    assert_eq!(
        verify_source_computation_values(
            &sites,
            &effects,
            &[],
            &frames,
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

// The typed cast opcode is part of the source-C contract. A numerically
// matching guest store cannot authorize a forged cast: C truth conversion
// tests nonzero, and sign extension depends on the *source* signedness.
#[test]
fn typed_casts_refuse_invalid_signedness_and_bool_truncation() {
    use TernaryCfgScalarKind::{Bool, I8, I16, U8, U16};
    let input = |operation, source_type, result_type, value| {
        let source = GuestPlacedOperand {
            address: 70,
            type_kind: source_type,
            value: 0,
            words: 1,
        };
        let result = GuestPlacedOperand {
            address: 72,
            type_kind: result_type,
            value: 1,
            words: 1,
        };
        let mut written = BTreeMap::new();
        let _old = written.insert(70, value);
        evaluate(
            GuestCodeComputation::Cast {
                operation,
                source,
                result,
            },
            &written,
        )
    };
    let invalid = Err(SourcePhiCopyTraceError::UnsupportedComputation);
    let checks = [
        (CastOp::SignExtend, U8, I16, 128, invalid),
        (CastOp::ZeroExtend, I8, U16, 128, invalid),
        // A matching low word cannot change the destination type category.
        (CastOp::SignExtend, I8, U16, 1, invalid),
        (CastOp::ZeroExtend, U8, I16, 1, invalid),
        (CastOp::ZeroExtend, Bool, U16, 1, invalid),
        (CastOp::Truncate, U8, Bool, 2, invalid),
        (CastOp::BoolToSigned, Bool, U16, 1, invalid),
        (CastOp::IntegerToBool, Bool, Bool, 1, invalid),
        (CastOp::IntegerBitcast, Bool, Bool, 1, invalid),
        (CastOp::Truncate, U8, U8, 2, invalid),
        (CastOp::SignExtend, I8, I8, 128, invalid),
        (CastOp::ZeroExtend, U8, U8, 128, invalid),
        (CastOp::SignExtend, I8, I16, 128, Ok(0xff80)),
        (CastOp::ZeroExtend, U8, U16, 128, Ok(128)),
        (CastOp::Truncate, U16, U8, 0x102, Ok(2)),
        (CastOp::IntegerToBool, U8, Bool, 2, Ok(1)),
        (CastOp::BoolToSigned, Bool, I16, 1, Ok(1)),
        (CastOp::IntegerBitcast, U8, I8, 255, Ok(255)),
    ];
    for (operation, source, result, value, expected) in checks {
        assert_eq!(input(operation, source, result, value), expected);
    }
}

// These casts are numerically identical on source value one, so the
// physically rotated guest result alone cannot authenticate the typed opcode.
// The source IR admits sign-extension only to signed destinations and
// zero-extension only between non-Boolean unsigned integer types.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "one real guest validates the destination-category cast gate"
)]
fn real_guest_cast_extension_requires_correct_destination_category()
-> Result<(), String> {
    let trace = traced_three_stores_with_seeds([3, 3, 3])?;
    let typed = |address, type_kind| GuestPlacedOperand {
        address,
        type_kind,
        value: address.saturating_sub(70),
        words: 1,
    };
    let check = |operation, source_kind, destination_kind| {
        let sites = operations(GuestCodeComputation::Cast {
            operation,
            source: typed(71, source_kind),
            result: typed(72, destination_kind),
        });
        verify_source_computation_values(
            &sites,
            &effects(),
            &[],
            &frames(),
            &trace,
        )
    };
    use TernaryCfgScalarKind::{Bool, I8, I16, U8, U16};
    let unsupported = Err(SourcePhiCopyTraceError::UnsupportedComputation);
    assert_eq!(check(CastOp::SignExtend, I8, U16), unsupported);
    assert_eq!(check(CastOp::ZeroExtend, U8, I16), unsupported);
    assert_eq!(check(CastOp::ZeroExtend, Bool, U16), unsupported);
    assert_eq!(check(CastOp::SignExtend, I8, I16), Ok(()));
    assert_eq!(check(CastOp::ZeroExtend, U8, U16), Ok(()));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "strict assertions over a normative four-step N15 guest trace"
)]
fn real_guest_zero_result_cannot_authenticate_bool_truncate_of_two()
-> Result<(), String> {
    // The real N15 guest stores 1, 2, 0 in M70..M72. Truncating the
    // signed/unsigned byte 2 to a one-bit Boolean would falsely accept its
    // zero result; C23 (bool)2 is 1, so only IntegerToBool is meaningful.
    let steps = traced_three_stores_with_seeds([3, 6, 0])?;
    let source = operand(71, 0);
    let result = GuestPlacedOperand {
        address: 72,
        type_kind: TernaryCfgScalarKind::Bool,
        value: 1,
        words: 1,
    };
    let truncate = operations(GuestCodeComputation::Cast {
        operation: CastOp::Truncate,
        source,
        result,
    });
    assert_eq!(
        verify_source_computation_values(
            &truncate,
            &effects(),
            &[],
            &frames(),
            &steps
        ),
        Err(SourcePhiCopyTraceError::UnsupportedComputation)
    );
    Ok(())
}

// Equality is bitwise regardless of signedness; ordering is not. A forged
// typed comparison must not reinterpret a U8 0xff as negative, or a signed
// I8 -1 as unsigned 255, to justify an otherwise coincident guest store.
#[test]
fn typed_comparisons_require_consistent_ordering_signedness() {
    use TernaryCfgScalarKind::{Bool, I8, U8};
    let compare = |operation, kind, left, right| {
        let source = |address| GuestPlacedOperand {
            address,
            type_kind: kind,
            value: address.saturating_sub(70),
            words: 1,
        };
        let result = GuestPlacedOperand {
            address: 72,
            type_kind: Bool,
            value: 2,
            words: 1,
        };
        let written = BTreeMap::from([(70, left), (71, right)]);
        evaluate(
            GuestCodeComputation::Compare {
                operation,
                left: source(70),
                right: source(71),
                result,
            },
            &written,
        )
    };
    let unsupported = Err(SourcePhiCopyTraceError::UnsupportedComputation);
    let checks = [
        (CompareOp::LessSigned, U8, 255, 1, unsupported),
        (CompareOp::LessSignedEqual, U8, 255, 1, unsupported),
        (CompareOp::LessUnsigned, I8, 255, 1, unsupported),
        (CompareOp::LessUnsignedEqual, I8, 255, 1, unsupported),
        (CompareOp::LessSigned, Bool, 1, 0, unsupported),
        (CompareOp::LessSignedEqual, Bool, 1, 0, unsupported),
        (CompareOp::LessUnsigned, U8, 255, 1, Ok(0)),
        (CompareOp::LessUnsignedEqual, U8, 1, 255, Ok(1)),
        (CompareOp::LessSigned, I8, 255, 1, Ok(1)),
        (CompareOp::LessSignedEqual, I8, 255, 255, Ok(1)),
        (CompareOp::LessUnsigned, Bool, 0, 1, unsupported),
        (CompareOp::Equal, Bool, 1, 1, unsupported),
        (CompareOp::NotEqual, Bool, 1, 0, unsupported),
        (CompareOp::Equal, I8, 255, 255, Ok(1)),
        (CompareOp::NotEqual, U8, 255, 1, Ok(1)),
    ];
    for (operation, kind, lhs, rhs, expected) in checks {
        assert_eq!(compare(operation, kind, lhs, rhs), expected);
    }
}

// A real equal-byte comparison can be numerically correct while its
// direct Boolean operand kind violates the typed IR promotion boundary.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "one authentic N15 trace distinguishes promoted comparisons"
)]
fn real_guest_bool_comparison_requires_promoted_integer_operands()
-> Result<(), String> {
    let trace = traced_three_stores_with_seeds([3, 3, 3])?;
    let typed = |address, kind| GuestPlacedOperand {
        address,
        type_kind: kind,
        value: address.saturating_sub(70),
        words: 1,
    };
    let check = |kind| {
        let sites = operations(GuestCodeComputation::Compare {
            operation: CompareOp::Equal,
            left: typed(70, kind),
            right: typed(71, kind),
            result: typed(72, TernaryCfgScalarKind::Bool),
        });
        verify_source_computation_values(
            &sites,
            &effects(),
            &[],
            &frames(),
            &trace,
        )
    };
    assert_eq!(
        check(TernaryCfgScalarKind::Bool),
        Err(SourcePhiCopyTraceError::UnsupportedComputation)
    );
    assert_eq!(check(TernaryCfgScalarKind::U8), Ok(()));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "strict assertions over a normative four-step N15 guest trace"
)]
fn real_guest_signed_and_unsigned_ordering_use_source_width()
-> Result<(), String> {
    // Four physical stores are NOT fabricated: the VM rotates 765 ->
    // 255, 3 -> 1, and 0/3 -> 0/1, then genuinely halts at C3.
    // U8 255 < 1 is false; I8 -1 < 1 is true. A forged ordering opcode
    // must not justify the opposite observed guest Boolean result.
    let actual_true = traced_three_stores_with_seeds([765, 3, 3])?;
    let actual_false = traced_three_stores_with_seeds([765, 3, 0])?;
    for (steps, expected) in [(&actual_true, 1), (&actual_false, 0)] {
        assert_eq!(
            steps
                .iter()
                .take(3)
                .map(|step| step.after.registers.accumulator)
                .collect::<Vec<_>>(),
            vec![255, 1, expected]
        );
    }
    let compare = |operation, kind| {
        let source = |address| GuestPlacedOperand {
            address,
            type_kind: kind,
            value: address.saturating_sub(70),
            words: 1,
        };
        operations(GuestCodeComputation::Compare {
            operation,
            left: source(70),
            right: source(71),
            result: GuestPlacedOperand {
                address: 72,
                type_kind: TernaryCfgScalarKind::Bool,
                value: 2,
                words: 1,
            },
        })
    };
    let check = |operation, kind, steps: &[ProfileStepTrace]| {
        verify_source_computation_values(
            &compare(operation, kind),
            &effects(),
            &[],
            &frames(),
            steps,
        )
    };
    let invalid = Err(SourcePhiCopyTraceError::UnsupportedComputation);
    assert_eq!(
        check(
            CompareOp::LessSigned,
            TernaryCfgScalarKind::U8,
            &actual_true
        ),
        invalid
    );
    assert_eq!(
        check(
            CompareOp::LessUnsigned,
            TernaryCfgScalarKind::U8,
            &actual_false
        ),
        Ok(())
    );
    assert_eq!(
        check(
            CompareOp::LessUnsigned,
            TernaryCfgScalarKind::I8,
            &actual_false
        ),
        invalid
    );
    assert_eq!(
        check(
            CompareOp::LessSigned,
            TernaryCfgScalarKind::I8,
            &actual_true
        ),
        Ok(())
    );
    Ok(())
}

// Boolean C operands undergo integer promotion for arithmetic and bitwise
// operations. Typed IR cannot claim a direct one-bit opcode as source C:
// (bool)(true + true) is 1, not a one-bit wrapped result of zero.
#[test]
fn typed_boolean_arithmetic_requires_explicit_integer_promotion() {
    let value = |operation| {
        let operand = |address| GuestPlacedOperand {
            address,
            type_kind: TernaryCfgScalarKind::Bool,
            value: address.saturating_sub(70),
            words: 1,
        };
        evaluate(
            GuestCodeComputation::Binary {
                operation,
                left: operand(70),
                right: operand(71),
                result: operand(72),
            },
            &BTreeMap::from([(70, 1), (71, 1)]),
        )
    };
    for operation in [BinaryOp::Add, BinaryOp::Subtract, BinaryOp::Multiply] {
        assert_eq!(
            value(operation),
            Err(SourcePhiCopyTraceError::UnsupportedComputation)
        );
    }
    for operation in [BinaryOp::And, BinaryOp::Or, BinaryOp::Xor] {
        assert_eq!(
            value(operation),
            Err(SourcePhiCopyTraceError::UnsupportedComputation)
        );
    }
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "strict assertions over a normative four-step N15 guest trace"
)]
fn real_guest_one_bit_wrapped_add_is_not_c_boolean_add() -> Result<(), String> {
    let trace = traced_three_stores_with_seeds([3, 3, 0])?;
    assert_eq!(
        trace
            .iter()
            .take(3)
            .map(|step| step.after.registers.accumulator)
            .collect::<Vec<_>>(),
        vec![1, 1, 0]
    );
    let bool_operand = |address| GuestPlacedOperand {
        address,
        type_kind: TernaryCfgScalarKind::Bool,
        value: address.saturating_sub(70),
        words: 1,
    };
    let check = |operation| {
        let computation = GuestCodeComputation::Binary {
            operation,
            left: bool_operand(70),
            right: bool_operand(71),
            result: bool_operand(72),
        };
        verify_source_computation_values(
            &operations(computation),
            &effects(),
            &[],
            &frames(),
            &trace,
        )
    };
    assert_eq!(
        check(BinaryOp::Add),
        Err(SourcePhiCopyTraceError::UnsupportedComputation)
    );
    assert_eq!(
        check(BinaryOp::Xor),
        Err(SourcePhiCopyTraceError::UnsupportedComputation)
    );
    Ok(())
}

// A C32 SSA result needs two physical N15 frame words even when its
// current value happens to fit in one. Conversely, a byte or Boolean result
// cannot authorize an invented high word. Operand widths are independently
// checked by read_scalar; result widths must obey the same invariant.
#[test]
fn typed_results_require_canonical_guest_word_count() {
    use TernaryCfgScalarKind::{Bool, U8, U32};
    let word = |kind, words, part: u32| {
        expected_word(
            if kind == U32 {
                0x1234_5678
            } else {
                0x78
            },
            GuestPlacedOperand {
                address: 72,
                type_kind: kind,
                value: 0,
                words,
            },
            72 + part,
        )
    };
    let invalid = Err(SourcePhiCopyTraceError::InvalidSourcePlacement);
    assert_eq!(word(U8, 2, 0), invalid);
    assert_eq!(word(Bool, 2, 0), invalid);
    assert_eq!(word(U32, 1, 0), invalid);
    assert_eq!(word(U32, 3, 0), invalid);
    assert_eq!(word(U8, 1, 1), invalid);
    assert_eq!(word(U8, 1, 0), Ok(0x78));
    let full = encode_i32_cells(0x1234_5678);
    assert_eq!(word(U32, 2, 0), Ok(full[0]));
    assert_eq!(word(U32, 2, 1), Ok(full[1]));
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "strict assertions over a normative four-step N15 guest trace"
)]
fn real_guest_byte_result_cannot_claim_two_c32_words() -> Result<(), String> {
    // These three stores are genuine N15 rotations with values 1, 2, 3.
    // A forged U8 result placement requiring two words previously passed
    // numerical XOR even though only M72 was written; no high word exists.
    let steps = traced_three_stores(9)?;
    let forged = operations(GuestCodeComputation::Binary {
        operation: BinaryOp::Xor,
        left: operand(70, 0),
        right: operand(71, 1),
        result: GuestPlacedOperand {
            address: 72,
            type_kind: TernaryCfgScalarKind::U8,
            value: 2,
            words: 2,
        },
    });
    assert_eq!(
        verify_source_computation_values(
            &forged,
            &effects(),
            &[],
            &frames(),
            &steps,
        ),
        Err(SourcePhiCopyTraceError::InvalidSourcePlacement)
    );
    Ok(())
}

// C23 signed arithmetic overflow is undefined source behavior, even when
// the guest physically writes the corresponding low-width wrapped bits.
// These are real four-step N15 guest executions, not fabricated VM traces.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "one bounded real guest signed/unsigned overflow matrix"
)]
fn real_guest_signed_overflow_must_not_pass_numeric_result_check()
-> Result<(), String> {
    let typed = |address, type_kind| GuestPlacedOperand {
        address,
        type_kind,
        value: address.saturating_sub(70),
        words: 1,
    };
    let computation = |operation, type_kind| GuestCodeComputation::Binary {
        operation,
        left: typed(70, type_kind),
        right: typed(71, type_kind),
        result: typed(72, type_kind),
    };
    let placed = effects();
    let frame = frames();
    let signed_kind = TernaryCfgScalarKind::I8;
    // * rotates 3*x into x for all these small N15 words.
    // 127 + 1 -> 128: the physical low-byte result matches modulo 256,
    // but evaluating this as a signed i8 computation would be undefined.
    let add_overflow = traced_three_stores_with_seeds([381, 3, 384])?;
    assert_eq!(
        verify_source_computation_values(
            &operations(computation(BinaryOp::Add, signed_kind)),
            &placed,
            &[],
            &frame,
            &add_overflow,
        ),
        Err(SourcePhiCopyTraceError::InvalidComputationValue)
    );
    let defined_add = traced_three_stores_with_seeds([378, 3, 381])?;
    assert_eq!(
        verify_source_computation_values(
            &operations(computation(BinaryOp::Add, signed_kind)),
            &placed,
            &[],
            &frame,
            &defined_add,
        ),
        Ok(())
    );
    let sub_overflow = traced_three_stores_with_seeds([384, 3, 381])?;
    assert_eq!(
        verify_source_computation_values(
            &operations(computation(BinaryOp::Subtract, signed_kind)),
            &placed,
            &[],
            &frame,
            &sub_overflow,
        ),
        Err(SourcePhiCopyTraceError::InvalidComputationValue)
    );
    let mul_overflow = traced_three_stores_with_seeds([384, 6, 0])?;
    assert_eq!(
        verify_source_computation_values(
            &operations(computation(BinaryOp::Multiply, signed_kind)),
            &placed,
            &[],
            &frame,
            &mul_overflow,
        ),
        Err(SourcePhiCopyTraceError::InvalidComputationValue)
    );
    // Unsigned arithmetic is defined modulo 2^8: 255 + 1 -> 0.
    let unsigned_wrap = traced_three_stores_with_seeds([765, 3, 0])?;
    assert_eq!(
        verify_source_computation_values(
            &operations(computation(BinaryOp::Add, TernaryCfgScalarKind::U8,)),
            &placed,
            &[],
            &frame,
            &unsigned_wrap,
        ),
        Ok(())
    );
    Ok(())
}

// The physical overflow witness above tests signed i8; this deterministic
// full-width matrix verifies the same bounded interpreter at both C32 cells.
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_lines,
    reason = "one full-width signed/unsigned boundary matrix"
)]
fn checked_signed_arithmetic_preserves_c32_and_i16_boundaries() {
    let computed = |kind, operation, lhs, rhs| {
        let mut journal = BTreeMap::new();
        let width = scalar_bits(kind);
        let words = if width == 32 {
            2
        } else {
            1
        };
        let placed = |address, value| GuestPlacedOperand {
            address,
            type_kind: kind,
            value,
            words,
        };
        let src = if words == 2 {
            [encode_i32_cells(lhs), encode_i32_cells(rhs)]
        } else {
            [[lhs, 0], [rhs, 0]]
        };
        for (index, cells) in src.into_iter().enumerate() {
            let address = 70u32.saturating_add(
                u32::try_from(index)
                    .unwrap_or(u32::MAX)
                    .saturating_mul(words),
            );
            for (offset, word) in cells
                .into_iter()
                .take(usize::try_from(words).unwrap_or(usize::MAX))
                .enumerate()
            {
                _ = journal.insert(
                    address.saturating_add(
                        u32::try_from(offset).unwrap_or(u32::MAX),
                    ),
                    word,
                );
            }
        }
        evaluate(
            GuestCodeComputation::Binary {
                operation,
                left: placed(70, 0),
                right: placed(70u32.saturating_add(words), 1),
                result: placed(
                    70u32.saturating_add(words.saturating_mul(2)),
                    2,
                ),
            },
            &journal,
        )
    };
    let invalid = Err(SourcePhiCopyTraceError::InvalidComputationValue);
    assert_eq!(
        computed(TernaryCfgScalarKind::I32, BinaryOp::Add, 0x7fff_ffff, 1),
        invalid
    );
    assert_eq!(
        computed(
            TernaryCfgScalarKind::I32,
            BinaryOp::Subtract,
            0x8000_0000,
            1
        ),
        invalid
    );
    assert_eq!(
        computed(
            TernaryCfgScalarKind::I32,
            BinaryOp::Multiply,
            0x4000_0000,
            2
        ),
        invalid
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::I32, BinaryOp::Add, 0xffff_fffe, 1),
        Ok(0xffff_ffff)
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::U32, BinaryOp::Add, 0xffff_ffff, 1),
        Ok(0)
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::I16, BinaryOp::Add, 0x7fff, 1),
        invalid
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::I16, BinaryOp::Subtract, 0x8000, 1),
        invalid
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::U32, BinaryOp::DivideUnsigned, 9, 2),
        Ok(4)
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::U32, BinaryOp::RemainderUnsigned, 9, 2),
        Ok(1)
    );
    assert_eq!(
        computed(
            TernaryCfgScalarKind::I32,
            BinaryOp::DivideSigned,
            0xffff_fff9,
            3
        ),
        Ok(0xffff_fffe)
    );
    assert_eq!(
        computed(
            TernaryCfgScalarKind::I32,
            BinaryOp::RemainderSigned,
            0xffff_fff9,
            3
        ),
        Ok(0xffff_ffff)
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::U32, BinaryOp::DivideUnsigned, 9, 0),
        invalid
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::I32, BinaryOp::DivideSigned, 9, 0),
        invalid
    );
    assert_eq!(
        computed(
            TernaryCfgScalarKind::I32,
            BinaryOp::RemainderSigned,
            0x8000_0000,
            0xffff_ffff
        ),
        invalid
    );
    assert_eq!(
        computed(
            TernaryCfgScalarKind::I32,
            BinaryOp::DivideSigned,
            0x8000_0000,
            0xffff_ffff
        ),
        invalid
    );
    // A source C32 shift keeps all 32 result bits across two N15 words.
    assert_eq!(
        computed(TernaryCfgScalarKind::U32, BinaryOp::ShiftLeft, 1, 31),
        Ok(0x8000_0000)
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::I32, BinaryOp::ShiftLeft, 1, 31),
        invalid
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::I32, BinaryOp::ShiftLeft, 7, 3),
        Ok(56)
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::U32, BinaryOp::ShiftLeft, 1, 32),
        invalid
    );
    assert_eq!(
        computed(
            TernaryCfgScalarKind::I32,
            BinaryOp::ShiftLeft,
            1,
            0xffff_ffff
        ),
        invalid
    );
    assert_eq!(
        computed(
            TernaryCfgScalarKind::U32,
            BinaryOp::ShiftRightLogical,
            0xffff_ffff,
            31
        ),
        Ok(1)
    );
    assert_eq!(
        computed(
            TernaryCfgScalarKind::I32,
            BinaryOp::ShiftRightArithmetic,
            0xffff_fffd,
            1
        ),
        Ok(0xffff_fffe)
    );
    assert_eq!(
        computed(
            TernaryCfgScalarKind::I32,
            BinaryOp::ShiftRightLogical,
            0xffff_fffd,
            1
        ),
        Err(SourcePhiCopyTraceError::UnsupportedComputation)
    );
    assert_eq!(
        computed(
            TernaryCfgScalarKind::U32,
            BinaryOp::ShiftRightArithmetic,
            0xffff_fffd,
            1
        ),
        Err(SourcePhiCopyTraceError::UnsupportedComputation)
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::U16, BinaryOp::ShiftLeft, 1, 15),
        Ok(0x8000)
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::I16, BinaryOp::ShiftLeft, 1, 15),
        invalid
    );
    assert_eq!(
        computed(
            TernaryCfgScalarKind::I16,
            BinaryOp::ShiftRightArithmetic,
            0x8000,
            15
        ),
        Ok(0xffff)
    );
    assert_eq!(
        computed(
            TernaryCfgScalarKind::U16,
            BinaryOp::ShiftRightLogical,
            0x8000,
            16
        ),
        invalid
    );
    assert_eq!(
        computed(TernaryCfgScalarKind::Bool, BinaryOp::ShiftLeft, 1, 0),
        Err(SourcePhiCopyTraceError::UnsupportedComputation)
    );
}

// Distinguish actual source-defined integer division from a numeric guest
// coincidence, and preserve the explicit C23 trap/undefined boundaries.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "one bounded real VM division/remainder witness family"
)]
fn real_guest_division_and_remainder_require_defined_c23_results()
-> Result<(), String> {
    let result = |operation, kind, seeds| -> Result<_, String> {
        let steps = traced_three_stores_with_seeds(seeds)?;
        let input = |address| GuestPlacedOperand {
            address,
            type_kind: kind,
            value: address.saturating_sub(70),
            words: 1,
        };
        let sites = operations(GuestCodeComputation::Binary {
            operation,
            left: input(70),
            right: input(71),
            result: input(72),
        });
        Ok(verify_source_computation_values(
            &sites,
            &effects(),
            &[],
            &frames(),
            &steps,
        ))
    };
    assert_eq!(
        result(BinaryOp::DivideUnsigned, TernaryCfgScalarKind::U8, [
            18, 6, 9
        ])?,
        Ok(())
    );
    assert_eq!(
        result(BinaryOp::RemainderUnsigned, TernaryCfgScalarKind::U8, [
            21, 9, 3
        ])?,
        Ok(())
    );
    assert_eq!(
        result(BinaryOp::DivideSigned, TernaryCfgScalarKind::I8, [
            747, 9, 762
        ])?,
        Ok(())
    );
    assert_eq!(
        result(BinaryOp::RemainderSigned, TernaryCfgScalarKind::I8, [
            747, 9, 765
        ])?,
        Ok(())
    );
    assert_eq!(
        result(BinaryOp::RemainderSigned, TernaryCfgScalarKind::I8, [
            747, 9, 762
        ])?,
        Err(SourcePhiCopyTraceError::InvalidComputationValue)
    );
    let undefined = Err(SourcePhiCopyTraceError::InvalidComputationValue);
    assert_eq!(
        result(BinaryOp::DivideUnsigned, TernaryCfgScalarKind::U8, [
            18, 0, 0
        ])?,
        undefined
    );
    assert_eq!(
        result(BinaryOp::DivideSigned, TernaryCfgScalarKind::I8, [
            384, 765, 384
        ])?,
        undefined
    );
    Ok(())
}

// Real guest p writes form the typed left/right/result word journal. The
// verifier must check shift count bounds and distinguish arithmetic from
// logical right shift before a linker can rely on these typed results.
#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    reason = "one bounded real VM bit-shift witness family"
)]
fn real_guest_shift_results_obey_width_signedness_and_count()
-> Result<(), String> {
    let positive = traced_three_stores_with_seeds([6, 3, 12])?;
    let wrapping = traced_three_stores_with_seeds([384, 3, 0])?;
    let negative = traced_three_stores_with_seeds([747, 3, 756])?;
    let bad_count = traced_three_stores_with_seeds([6, 24, 0])?;
    let logical = traced_three_stores_with_seeds([765, 3, 381])?;
    let check = |steps: &[ProfileStepTrace], operation, kind| {
        let operand = |address| GuestPlacedOperand {
            address,
            type_kind: kind,
            value: address.saturating_sub(70),
            words: 1,
        };
        let sites = operations(GuestCodeComputation::Binary {
            operation,
            left: operand(70),
            right: operand(71),
            result: operand(72),
        });
        verify_source_computation_values(
            &sites,
            &effects(),
            &[],
            &frames(),
            steps,
        )
    };
    let unsigned = TernaryCfgScalarKind::U8;
    let signed = TernaryCfgScalarKind::I8;
    let invalid = Err(SourcePhiCopyTraceError::InvalidComputationValue);
    assert_eq!(check(&positive, BinaryOp::ShiftLeft, unsigned), Ok(()));
    assert_eq!(check(&positive, BinaryOp::ShiftLeft, signed), Ok(()));
    assert_eq!(check(&wrapping, BinaryOp::ShiftLeft, unsigned), Ok(()));
    assert_eq!(check(&wrapping, BinaryOp::ShiftLeft, signed), invalid);
    assert_eq!(check(&negative, BinaryOp::ShiftLeft, signed), invalid);
    assert_eq!(
        check(&negative, BinaryOp::ShiftRightArithmetic, signed),
        Ok(())
    );
    assert_eq!(
        check(&negative, BinaryOp::ShiftRightLogical, unsigned),
        invalid
    );
    assert_eq!(check(&bad_count, BinaryOp::ShiftLeft, unsigned), invalid);
    assert_eq!(
        check(&bad_count, BinaryOp::ShiftRightLogical, unsigned),
        invalid
    );
    assert_eq!(
        check(&logical, BinaryOp::ShiftRightLogical, unsigned),
        Ok(())
    );
    assert_eq!(
        check(&logical, BinaryOp::ShiftRightArithmetic, signed),
        invalid
    );
    Ok(())
}

// Every C32 operand and result cell is genuinely rotated into place by a
// reached guest *, with no preconstructed VM trace. A differing *high* result
// word must not authorize a correct-looking low-word unsigned shift.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "one canonical 32-bit two-word N15 guest shift witness"
)]
fn real_guest_c32_shift_requires_both_result_words() -> Result<(), String> {
    fn traced_words(values: [u32; 3]) -> Result<Vec<ProfileStepTrace>, String> {
        const TOP_TRIT: u32 = 4_782_969;
        let mut source = (0..59)
            .map(|at| graphical(at, b'o'))
            .collect::<Result<Vec<_>, _>>()?;
        for (at, opcode) in (0..6).map(|at| (at, b'*')).chain([(6, b'v')]) {
            *source.get_mut(at).ok_or("missing source code cell")? =
                graphical(at, opcode)?;
        }
        let profile = malbolge::current_profile();
        let loaded =
            malbolge::ProfileMachine::from_source(profile, &source, Vec::new())
                .map_err(|error| format!("source load: {error:?}"))?;
        let mut memory = loaded.memory().to_vec();
        for (index, word) in
            values.into_iter().flat_map(encode_i32_cells).enumerate()
        {
            // Inverse of a one-trit right rotate, valid for every N15 word.
            let low = word.checked_rem(TOP_TRIT).ok_or("trit remainder")?;
            let high = word.checked_div(TOP_TRIT).ok_or("trit quotient")?;
            let seed = low
                .checked_mul(3)
                .and_then(|part| part.checked_add(high))
                .ok_or("trit rotation inverse overflow")?;
            *memory.get_mut(70 + index).ok_or("missing data word")? = seed;
        }
        let mut machine = malbolge::ProfileMachine::from_state(
            profile,
            memory,
            Vec::new(),
            malbolge::ProfileRegisters {
                accumulator: profile.eof_word(),
                code_pointer: 0,
                data_pointer: 70,
            },
        )
        .map_err(|error| format!("state load: {error:?}"))?;
        let mut steps = Vec::new();
        let outcome = machine
            .run_traced(7, &mut |step| steps.push(*step))
            .map_err(|error| format!("guest run: {error:?}"))?;
        assert_eq!(outcome, malbolge::RunOutcome::Terminated {
            reason: malbolge::Termination::HaltInstruction,
            steps: 7,
        });
        Ok(steps)
    }
    let correct = traced_words([1, 31, 0x8000_0000])?;
    let wrong_high = traced_words([1, 31, 0x8000_0000 + 14_348_907])?;
    let operand = |address, type_kind| GuestPlacedOperand {
        address,
        type_kind,
        value: address.saturating_sub(70).wrapping_shr(1),
        words: 2,
    };
    let computation = |type_kind| GuestCodeComputation::Binary {
        operation: BinaryOp::ShiftLeft,
        left: operand(70, type_kind),
        right: operand(72, type_kind),
        result: operand(74, type_kind),
    };
    let effects = (0..6)
        .map(|index| GuestCodeOperationEffectSite {
            block: 0,
            code_address: index,
            effect: GuestCodeOperationEffect::Store {
                destination: 70 + index,
                literal: None,
            },
            function: 0,
            ordinal: if index < 4 {
                index.wrapping_shr(1)
            } else {
                2
            },
        })
        .collect::<Vec<_>>();
    let frame = [GuestFramePlacement {
        base: 70,
        end_exclusive: 76,
        source_cells: 59,
    }];
    let verify = |steps: &[ProfileStepTrace], kind| {
        let operation = [GuestCodeOperationSite {
            block: 0,
            computation: Some(computation(kind)),
            start: 4,
            end_exclusive: 6,
            function: 0,
            ordinal: 2,
        }];
        verify_source_computation_values(
            &operation,
            &effects,
            &[],
            &frame,
            steps,
        )
    };
    assert_eq!(verify(&correct, TernaryCfgScalarKind::U32), Ok(()));
    assert_eq!(
        verify(&wrong_high, TernaryCfgScalarKind::U32),
        Err(SourcePhiCopyTraceError::InvalidComputationValue)
    );
    assert_eq!(
        verify(&correct, TernaryCfgScalarKind::I32),
        Err(SourcePhiCopyTraceError::InvalidComputationValue)
    );
    Ok(())
}
