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
//   - Source-CFG reachability of authenticated physical input prefixes.
// - Must-Not:
//   - Treat branch reachability as a proof of source branch predicates.
// - Allows:
//   - Inputs: frozen source-C checksum and synthetic source-site orderings.
//   - Outputs: exact admission/refusal for feasible source CFG prefixes.
//   - Side effects: none.
// - Split-When:
//   - Complete guest control-flow translation verification is available.
// - Merge-When:
//   - Input reachability becomes part of full source-linked trace checking.
// - Summary:
//   - Forbids physical inputs in an impossible source CFG order.

//! Source path ordering is a necessary condition, not a guest branch proof.

use std::str;

use malbolge::TraceInput;

use super::super::typed_cfg_adapter::lower_canonical_dynamic_cfg;
use super::super::typed_cfg_adapter::ternary::{
    TernaryCfgBlock, TernaryCfgFunction, TernaryCfgScalarKind,
    TernaryCfgTerminator, TernaryI32Scalar, TernaryOperation,
    TernarySourcePosition, TernarySourceSpan,
};
use super::{
    GuestCodeInputSemantics, GuestPlacedOperand, SourceBranchLanding,
    SourceInputIoEvent, SourceInputPrefixProof, SourceInputSiteObservation,
    SourceInputTraceError, SourceOutputSiteObservation,
    source_path_matches_input_observables, source_path_matches_input_prefix,
    source_path_matches_input_trace, source_path_matches_input_walk,
    verify_source_branch_io_landing, verify_source_cfg_input_order,
};

const CHECKSUM_TYPED: &str =
    include_str!("typed-ir/golden/mutable-eof-checksum.hex");

// Real N15 binary-input + actual M73 store + addressed output guest.
const BYTE_INPUT_STORE_OUTPUT_PHYSICAL: &[u8] =
    b"DCBA@?>=<;:98hx/v-210/p-K+*)ji&%$#\"!~}|{zyxwvutsrqponmlkjihgs%H";

fn checksum_wire() -> Result<Vec<u8>, String> {
    let hex = CHECKSUM_TYPED
        .trim_end()
        .strip_prefix("malbolge-typed-ir-v1:")
        .ok_or_else(|| "frozen typed checksum fixture".to_owned())?;
    let (chunks, remainder) = hex.as_bytes().as_chunks::<2>();
    if !remainder.is_empty() {
        return Err("odd-length canonical hex fixture".to_owned());
    }
    chunks
        .iter()
        .map(|chunk| {
            let pair =
                str::from_utf8(chunk).map_err(|error| error.to_string())?;
            u8::from_str_radix(pair, 16).map_err(|error| error.to_string())
        })
        .collect()
}

fn observed(block: u32, ordinal: u32) -> SourceInputSiteObservation {
    SourceInputSiteObservation {
        block,
        code_address: if block == 0 {
            37
        } else {
            66
        },
        destination: GuestPlacedOperand {
            address: 200u32.saturating_add(block),
            type_kind: TernaryCfgScalarKind::I32,
            value: ordinal.saturating_add(1),
            words: 2,
        },
        function: 0,
        input: TraceInput::Byte(3),
        ordinal,
        raw_accumulator: 3,
        semantics: GuestCodeInputSemantics::SignedC23 {
            raw_eof_word: 14_348_906,
            c23_eof_cells: [4_644_102, 299],
        },
        trace_index: usize::try_from(block).unwrap_or_default(),
    }
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "explicit source CFG assertions"
)]
fn actual_checksum_cfg_requires_first_read_before_backedge_read()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let first = observed(0, 1);
    let loop_read = observed(5, 2);
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[first, loop_read]),
        Ok(())
    );
    assert_eq!(verify_source_cfg_input_order(&wire, &[first]), Ok(()));
    // First-read EOF must take the source exit, even though a purely
    // branch-insensitive reachability walk could reach the loop read.
    let first_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..first
    };
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[first_eof, loop_read]),
        Err(SourceInputTraceError::SourceInputUnreachable)
    );
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[loop_read]),
        Err(SourceInputTraceError::SourceInputUnreachable)
    );
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[loop_read, first]),
        Err(SourceInputTraceError::SourceInputUnreachable)
    );
    // A source loop may reach the same read site again. The separate physical
    // prefix verifier refuses repeated code-site execution until a real
    // runtime CFG and guest state linker can prove repeated guest effects.
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[first, loop_read, loop_read]),
        Ok(())
    );
    let second_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..loop_read
    };
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[first, second_eof, loop_read]),
        Err(SourceInputTraceError::SourceInputUnreachable)
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "complete source return and EOF input obligations"
)]
fn checksum_cfg_skipped_loop_input_requires_real_source_return()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let cfg = lower_canonical_dynamic_cfg(&wire)
        .map_err(|error| format!("{error:?}"))?;
    let function = cfg.functions.first().ok_or("missing source function")?;
    let first = observed(0, 1);
    let loop_read = observed(5, 2);
    let first_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..first
    };
    let loop_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..loop_read
    };
    for (sequence, possible) in [
        (vec![&first_eof], true),
        (vec![&first], false),
        (vec![&first, &loop_read], false),
        (vec![&first, &loop_eof], true),
        (vec![&first_eof, &loop_read], false),
        (vec![&loop_eof], false),
    ] {
        assert_eq!(
            source_path_matches_input_trace(function, &sequence, 128, true),
            Ok(possible),
            "source return after input sequence {sequence:?}",
        );
    }
    assert_eq!(
        source_path_matches_input_trace(function, &[&first_eof], 1, true),
        Err(SourceInputTraceError::SourceInputSearchLimit)
    );
    Ok(())
}

// The real checksum guards its first getchar in block 1. A high successful
// byte (including 255) is *not* signed C EOF. These are source-only
// branch expectations; the separate N15 test checks physical pointer arms.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "frozen 257-class C23 source branch evidence"
)]
fn checksum_source_first_eof_guard_is_exact_for_all_byte_classes()
-> Result<(), String> {
    use super::{SourceBranchLanding, verify_source_branch_landing};

    let wire = checksum_wire()?;
    let branch = SourceBranchLanding {
        after_inputs: 1,
        block: 1,
        false_landing: 126,
        function: 0,
        true_landing: 45,
    };
    let first_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..observed(0, 1)
    };
    assert_eq!(
        verify_source_branch_landing(&wire, &[first_eof], branch, 126),
        Ok(()),
    );
    assert_eq!(
        verify_source_branch_landing(&wire, &[first_eof], branch, 45),
        Err(SourceInputTraceError::SourceBranchMismatch),
    );
    let second_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..observed(5, 2)
    };
    for byte in u8::MIN..=u8::MAX {
        let first = SourceInputSiteObservation {
            input: TraceInput::Byte(byte),
            raw_accumulator: u32::from(byte),
            ..observed(0, 1)
        };
        assert_eq!(
            verify_source_branch_landing(
                &wire,
                &[first, second_eof],
                branch,
                45
            ),
            Ok(()),
            "source C23 successful byte {byte}",
        );
        assert_eq!(
            verify_source_branch_landing(
                &wire,
                &[first, second_eof],
                branch,
                126
            ),
            Err(SourceInputTraceError::SourceBranchMismatch),
            "source C23 successful byte {byte} incorrectly treated as EOF",
        );
    }
    assert_eq!(
        verify_source_branch_landing(
            &wire,
            &[first_eof],
            SourceBranchLanding { block: 0, ..branch },
            126,
        ),
        Err(SourceInputTraceError::InvalidBranchBinding),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "explicit source CFG refusals"
)]
fn source_cfg_path_cannot_skip_or_invent_source_input_sites()
-> Result<(), String> {
    let wire = checksum_wire()?;
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[observed(6, 0)]),
        Err(SourceInputTraceError::SourceInputUnreachable)
    );
    assert_eq!(
        verify_source_cfg_input_order(&wire, &[observed(0, 2)]),
        Err(SourceInputTraceError::SourceInputUnreachable)
    );
    let mut corrupted = wire;
    corrupted.push(0);
    assert_eq!(
        verify_source_cfg_input_order(&corrupted, &[observed(0, 1)]),
        Err(SourceInputTraceError::InvalidSourcePlacement)
    );
    Ok(())
}

fn dummy_span() -> TernarySourceSpan {
    TernarySourceSpan {
        begin: TernarySourcePosition {
            byte: 0,
            column: 1,
            line: 1,
        },
        end: TernarySourcePosition {
            byte: 1,
            column: 2,
            line: 1,
        },
    }
}

fn guarded_inequality_fixture() -> TernaryCfgFunction {
    let span = dummy_span();
    TernaryCfgFunction {
        blocks: vec![
            TernaryCfgBlock {
                id: 0,
                operations: vec![
                    TernaryOperation::GetcharI32 { result: 0, span },
                    TernaryOperation::MaterializeI32 {
                        result: 1,
                        scalar: TernaryI32Scalar::from_bits(u32::MAX),
                        span,
                    },
                    TernaryOperation::NotEqualI32 {
                        left: 0,
                        result: 2,
                        right: 1,
                        span,
                    },
                ],
                phis: Vec::new(),
                terminator: TernaryCfgTerminator::Branch {
                    condition: 2,
                    false_target: 1,
                    span,
                    true_target: 2,
                },
            },
            TernaryCfgBlock {
                id: 1,
                operations: vec![TernaryOperation::GetcharI32 {
                    result: 3,
                    span,
                }],
                phis: Vec::new(),
                terminator: TernaryCfgTerminator::Return(
                    TernaryOperation::ReturnVoid { span },
                ),
            },
            TernaryCfgBlock {
                id: 2,
                operations: vec![TernaryOperation::GetcharI32 {
                    result: 4,
                    span,
                }],
                phis: Vec::new(),
                terminator: TernaryCfgTerminator::Return(
                    TernaryOperation::ReturnVoid { span },
                ),
            },
        ],
        entry: 0,
        id: 0,
        name: "emit".to_owned(),
        span,
    }
}

// Per-block ordinals reset at legitimate source CFG loop backedges. A
// monotone-ordinal check over the whole trace would incorrectly reject them;
// the authenticated CFG walk must also reject skipped earlier reads.
#[test]
fn source_loop_restarts_same_block_input_ordinals_without_reordering() {
    let span = dummy_span();
    let function = TernaryCfgFunction {
        blocks: vec![TernaryCfgBlock {
            id: 0,
            operations: vec![
                TernaryOperation::GetcharI32 { result: 0, span },
                TernaryOperation::GetcharI32 { result: 1, span },
            ],
            phis: Vec::new(),
            terminator: TernaryCfgTerminator::Jump { target: 0, span },
        }],
        entry: 0,
        id: 0,
        name: "emit".to_owned(),
        span,
    };
    let first = observed(0, 0);
    let second = observed(0, 1);
    for (sequence, valid) in [
        (vec![&first, &second, &first, &second], true),
        (vec![&first, &second, &first], true),
        (vec![&first, &first], false),
        (vec![&second, &first], false),
        (vec![&first, &second, &second], false),
    ] {
        assert_eq!(
            source_path_matches_input_prefix(&function, &sequence, 128),
            Ok(valid),
            "unexpected same-block CFG read order {sequence:?}",
        );
    }
}

#[test]
fn source_known_inequality_discriminates_high_byte_and_true_eof() {
    let function = guarded_inequality_fixture();
    let first_high = SourceInputSiteObservation {
        input: TraceInput::Byte(255),
        raw_accumulator: 255,
        ..observed(0, 0)
    };
    let first_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..observed(0, 0)
    };
    let eof_arm = observed(1, 0);
    let byte_arm = observed(2, 0);
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_high, &byte_arm],
            16_384,
        ),
        Ok(true)
    );
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_high, &eof_arm],
            16_384,
        ),
        Ok(false)
    );
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_eof, &eof_arm],
            16_384,
        ),
        Ok(true)
    );
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_eof, &byte_arm],
            16_384,
        ),
        Ok(false)
    );
}

#[test]
fn source_branch_arm_requires_a_known_guard_and_the_exact_input_occurrence() {
    use super::{
        SourceBranchObligation, source_path_matches_input_walk_with_branch,
    };

    let known = guarded_inequality_fixture();
    let first = SourceInputSiteObservation {
        input: TraceInput::Byte(255),
        raw_accumulator: 255,
        ..observed(0, 0)
    };
    let second = observed(2, 0);
    let returns = [&first, &second];
    let proof =
        |function: &TernaryCfgFunction, block, after_inputs, true_arm| {
            source_path_matches_input_walk_with_branch(
                function,
                &returns,
                128,
                true,
                None,
                None,
                None,
                Some(SourceBranchObligation {
                    after_inputs,
                    io_before_transfer: None,
                    block,
                    expected_true: true_arm,
                }),
            )
        };
    assert_eq!(proof(&known, 0, 1, true), Ok(true));
    assert_eq!(proof(&known, 0, 1, false), Ok(false));
    assert_eq!(proof(&known, 0, 2, true), Ok(false));
    assert_eq!(proof(&known, 1, 1, true), Ok(false));
    // The source branch's input-dependent predicate is no longer defined:
    // matching one plausible CFG successor is not a proof of its truth.
    let mut unknown = known.clone();
    let _removed = unknown.blocks[0].operations.pop();
    assert_eq!(proof(&unknown, 0, 1, true), Ok(false));
}

// A source conditional may precede *all* input effects. A physical guest
// pointer can branch at I/O cut zero, then execute the selected source read;
// forcing after_inputs >= 1 incorrectly rules out that legal source order.
fn branch_before_first_read_wire(truth: bool) -> Result<Vec<u8>, String> {
    use super::super::typed_cfg_adapter::typed::{
        BasicBlock, BasicBlockSpec, BlockId, Function, FunctionId,
        FunctionSpec, Instruction, IntegerConstant, LocatedInstruction, Module,
        ModuleSpec, SourcePosition, SourceSpan, Terminator, TypeDef, TypeEntry,
        TypeId, ValueId, canonical_bytes, validate_module,
    };
    let span = SourceSpan::new(
        SourcePosition::new(0, 1, 1),
        SourcePosition::new(1, 1, 2),
    );
    let block = |id, instructions, terminator| {
        BasicBlock::new(BasicBlockSpec {
            id: BlockId::new(id),
            instructions,
            phis: Vec::new(),
            span,
            terminator,
            terminator_span: span,
        })
    };
    let module = Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version:
            super::super::typed_cfg_adapter::typed::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![
                block(
                    0,
                    vec![LocatedInstruction::new(
                        Instruction::ConstantInteger {
                            constant: IntegerConstant::new(1, vec![u8::from(
                                truth,
                            )]),
                            result: ValueId::new(0),
                            type_id: TypeId::new(0),
                        },
                        span,
                    )],
                    Terminator::Branch {
                        condition: ValueId::new(0),
                        false_target: BlockId::new(2),
                        true_target: BlockId::new(1),
                    },
                ),
                block(
                    1,
                    vec![LocatedInstruction::new(
                        Instruction::Getchar {
                            result: ValueId::new(1),
                            type_id: TypeId::new(1),
                        },
                        span,
                    )],
                    Terminator::Return { value: None },
                ),
                block(2, Vec::new(), Terminator::Return { value: None }),
            ],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("branch_before_first_read"),
            parameters: Vec::new(),
            signature: TypeId::new(2),
            span,
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/branch-before-first-read.c"),
        source_sha256: [0x61; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), TypeDef::Bool),
            TypeEntry::new(TypeId::new(1), TypeDef::I32),
            TypeEntry::new(
                TypeId::new(2),
                TypeDef::function(Vec::new(), None, false),
            ),
        ],
    });
    validate_module(&module).map_err(|error| format!("typed: {error:?}"))?;
    canonical_bytes(&module).map_err(|error| format!("canonical: {error:?}"))
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source branch before any input"
)]
fn first_source_branch_can_precede_every_guest_read() -> Result<(), String> {
    use super::{
        verify_source_branch_io_landing, verify_source_branch_landing,
    };

    let binding = SourceBranchLanding {
        after_inputs: 0,
        block: 0,
        false_landing: 126,
        function: 0,
        true_landing: 45,
    };
    let read = SourceInputSiteObservation {
        block: 1,
        ordinal: 0,
        ..observed(0, 0)
    };
    let true_wire = branch_before_first_read_wire(true)?;
    assert_eq!(
        verify_source_branch_landing(&true_wire, &[read], binding, 45),
        Ok(()),
    );
    assert_eq!(
        verify_source_branch_landing(&true_wire, &[read], binding, 126),
        Err(SourceInputTraceError::SourceBranchMismatch),
    );
    let proof = SourceInputPrefixProof {
        bytes_consumed: 1,
        guest_output: Vec::new(),
        io_events: vec![SourceInputIoEvent::Input { observation_index: 0 }],
        output_sites: Vec::new(),
        observations: vec![read],
        outcome: malbolge::RunOutcome::Terminated {
            reason: malbolge::Termination::HaltInstruction,
            steps: 1,
        },
    };
    assert_eq!(
        verify_source_branch_io_landing(&true_wire, &proof, binding, 45, 0),
        Ok(()),
    );
    assert_eq!(
        verify_source_branch_io_landing(&true_wire, &proof, binding, 45, 1),
        Err(SourceInputTraceError::SourceOutputNotProven),
    );
    let false_wire = branch_before_first_read_wire(false)?;
    assert_eq!(
        verify_source_branch_landing(&false_wire, &[], binding, 126),
        Ok(()),
    );
    assert_eq!(
        verify_source_branch_landing(&false_wire, &[], binding, 45),
        Err(SourceInputTraceError::SourceBranchMismatch),
    );
    Ok(())
}

// A source-computed unsigned product must drive both a byte effect and the
// branch direction on the *same* return path. Raw EOF is 0xffffffff as C23
// i32; its u32 product wraps, unlike a successful high byte (255).
#[test]
fn unsigned_guest_input_product_controls_source_output_and_branch() {
    use super::{
        SourceBranchObligation, source_path_matches_input_walk_with_branch,
    };

    let span = dummy_span();
    let mut source = guarded_inequality_fixture();
    source.blocks[0].operations = vec![
        TernaryOperation::GetcharI32 { result: 0, span },
        TernaryOperation::BitcastI32ToU32 {
            result: 10,
            value: 0,
            span,
        },
        TernaryOperation::MaterializeU32 {
            result: 11,
            scalar: TernaryI32Scalar::from_bits(3),
            span,
        },
        TernaryOperation::MultiplyU32 {
            left: 10,
            result: 12,
            right: 11,
            span,
        },
        TernaryOperation::MaterializeU32 {
            result: 13,
            scalar: TernaryI32Scalar::from_bits(600),
            span,
        },
        TernaryOperation::LessUnsignedU32 {
            left: 12,
            result: 2,
            right: 13,
            span,
        },
        TernaryOperation::TruncateU32ToU8 {
            result: 14,
            value: 12,
            span,
        },
        TernaryOperation::ByteOutput { value: 14, span },
    ];
    for first in std::iter::once(TraceInput::EndOfInput)
        .chain((u8::MIN..=u8::MAX).map(TraceInput::Byte))
    {
        let raw = match first {
            TraceInput::Byte(byte) => u32::from(byte),
            TraceInput::EndOfInput => u32::MAX,
        };
        let product = raw.wrapping_mul(3);
        let true_arm = product < 600;
        let observed_first = SourceInputSiteObservation {
            input: first,
            raw_accumulator: raw,
            ..observed(0, 0)
        };
        let observed_second = SourceInputSiteObservation {
            block: if true_arm {
                2
            } else {
                1
            },
            input: TraceInput::EndOfInput,
            raw_accumulator: 14_348_906,
            ordinal: 0,
            ..observed(0, 0)
        };
        let reads = [&observed_first, &observed_second];
        let byte = product as u8;
        let ordered = [
            SourceInputIoEvent::Input { observation_index: 0 },
            SourceInputIoEvent::Output(byte),
            SourceInputIoEvent::Input { observation_index: 1 },
        ];
        for (expected_arm, cut, events, expected_output, expected) in [
            (true_arm, 2, &ordered[..], byte, true),
            (!true_arm, 2, &ordered[..], byte, false),
            (true_arm, 1, &ordered[..], byte, false),
            (true_arm, 2, &ordered[..], byte ^ 1, false),
        ] {
            assert_eq!(
                source_path_matches_input_walk_with_branch(
                    &source,
                    &reads,
                    128,
                    true,
                    Some(&[expected_output]),
                    Some(events),
                    None,
                    Some(SourceBranchObligation {
                        after_inputs: 1,
                        io_before_transfer: Some(cut),
                        block: 0,
                        expected_true: expected_arm,
                    }),
                ),
                Ok(expected),
                "product {first:?}, arm={expected_arm}, cut={cut}",
            );
        }
    }
}

// C23 signed operations are defined only when their mathematical result
// fits i32. A source branch cannot be certified by host integer wraparound.
#[test]
fn signed_source_product_and_checked_overflow_affect_branch_proof() {
    use super::{
        SourceBranchObligation, source_path_matches_input_walk_with_branch,
    };

    let span = dummy_span();
    let mut source = guarded_inequality_fixture();
    source.blocks[0].operations = vec![
        TernaryOperation::GetcharI32 { result: 0, span },
        TernaryOperation::MaterializeI32 {
            result: 10,
            scalar: TernaryI32Scalar::from_bits(10),
            span,
        },
        TernaryOperation::MultiplyI32 {
            left: 0,
            result: 11,
            right: 10,
            span,
        },
        TernaryOperation::MaterializeI32 {
            result: 12,
            scalar: TernaryI32Scalar::from_bits(u32::MAX),
            span,
        },
        TernaryOperation::SubtractI32 {
            left: 11,
            result: 13,
            right: 12,
            span,
        },
        TernaryOperation::MaterializeI32 {
            result: 14,
            scalar: TernaryI32Scalar::from_bits(1000),
            span,
        },
        TernaryOperation::LessSignedI32 {
            left: 13,
            result: 2,
            right: 14,
            span,
        },
        TernaryOperation::TruncateI32ToU8 {
            result: 15,
            value: 13,
            span,
        },
        TernaryOperation::ByteOutput { value: 15, span },
    ];
    let check = |function: &TernaryCfgFunction, first, true_arm, byte| {
        let first_read = SourceInputSiteObservation {
            input: first,
            raw_accumulator: match first {
                TraceInput::Byte(byte) => u32::from(byte),
                TraceInput::EndOfInput => 14_348_906,
            },
            ..observed(0, 0)
        };
        let second_read = SourceInputSiteObservation {
            block: if true_arm {
                2
            } else {
                1
            },
            input: TraceInput::EndOfInput,
            raw_accumulator: 14_348_906,
            ..observed(0, 0)
        };
        source_path_matches_input_walk_with_branch(
            function,
            &[&first_read, &second_read],
            128,
            true,
            Some(&[byte]),
            Some(&[
                SourceInputIoEvent::Input { observation_index: 0 },
                SourceInputIoEvent::Output(byte),
                SourceInputIoEvent::Input { observation_index: 1 },
            ]),
            None,
            Some(SourceBranchObligation {
                after_inputs: 1,
                io_before_transfer: Some(2),
                block: 0,
                expected_true: true_arm,
            }),
        )
    };
    for first in std::iter::once(TraceInput::EndOfInput)
        .chain((u8::MIN..=u8::MAX).map(TraceInput::Byte))
    {
        let number = match first {
            TraceInput::Byte(byte) => i32::from(byte),
            TraceInput::EndOfInput => -1,
        };
        let result = number * 10 + 1;
        let truth = result < 1000;
        assert_eq!(
            check(&source, first, truth, result as u8),
            Ok(true),
            "signed product source control for {first:?}",
        );
        assert_eq!(
            check(&source, first, !truth, result as u8),
            Ok(false),
            "signed product wrong branch for {first:?}",
        );
    }

    // A signed multiplication or subtraction overflow cannot borrow
    // the wrapped physical byte or a made-up definite source branch.
    source.blocks[0].operations[1] = TernaryOperation::MaterializeI32 {
        result: 10,
        scalar: TernaryI32Scalar::from_bits(0x7fff_ffff),
        span,
    };
    for invalid in [1, 2] {
        assert_eq!(
            check(&source, TraceInput::Byte(invalid), false, 0),
            Ok(false),
            "signed source overflow for first byte {invalid}",
        );
    }

    // Replace the product with signed addition of INT_MAX. Only the
    // successful zero byte is defined; adding one would overflow C i32.
    source.blocks[0].operations = vec![
        TernaryOperation::GetcharI32 { result: 0, span },
        TernaryOperation::MaterializeI32 {
            result: 10,
            scalar: TernaryI32Scalar::from_bits(0x7fff_ffff),
            span,
        },
        TernaryOperation::AddI32 {
            left: 0,
            result: 11,
            right: 10,
            span,
        },
        TernaryOperation::MaterializeI32 {
            result: 12,
            scalar: TernaryI32Scalar::from_bits(0),
            span,
        },
        TernaryOperation::LessSignedI32 {
            left: 11,
            result: 2,
            right: 12,
            span,
        },
        TernaryOperation::TruncateI32ToU8 {
            result: 15,
            value: 11,
            span,
        },
        TernaryOperation::ByteOutput { value: 15, span },
    ];
    assert_eq!(check(&source, TraceInput::Byte(0), false, 255), Ok(true));
    assert_eq!(check(&source, TraceInput::Byte(1), false, 0), Ok(false));

    // INT_MIN minus EOF (-1) is representable; subtracting one
    // successful byte instead crosses the signed minimum boundary.
    source.blocks[0].operations[1] = TernaryOperation::MaterializeI32 {
        result: 10,
        scalar: TernaryI32Scalar::from_bits(i32::MIN as u32),
        span,
    };
    source.blocks[0].operations[2] = TernaryOperation::SubtractI32 {
        left: 10,
        result: 11,
        right: 0,
        span,
    };
    assert_eq!(check(&source, TraceInput::EndOfInput, true, 1), Ok(true));
    assert_eq!(check(&source, TraceInput::Byte(0), true, 0), Ok(true));
    assert_eq!(check(&source, TraceInput::Byte(1), true, 255), Ok(false));
}

// The physical branch must agree with the same source return that emits a
// shifted input byte. Unsigned C32 left shifts wrap; logical right shifts
// retain all 32 input bits, including true EOF as 0xffffffff.
#[test]
fn defined_unsigned_shifts_bind_source_output_and_branch() -> Result<(), String>
{
    use std::iter::once;

    use super::{
        SourceBranchObligation, source_path_matches_input_walk_with_branch,
    };

    let span = dummy_span();
    let mut source = guarded_inequality_fixture();
    source
        .blocks
        .first_mut()
        .ok_or("missing source block")?
        .operations = vec![
        TernaryOperation::GetcharI32 { result: 0, span },
        TernaryOperation::BitcastI32ToU32 {
            result: 10,
            value: 0,
            span,
        },
        TernaryOperation::MaterializeU32 {
            result: 11,
            scalar: TernaryI32Scalar::from_bits(3),
            span,
        },
        TernaryOperation::ShiftLeftU32 {
            left: 10,
            result: 12,
            right: 11,
            span,
        },
        TernaryOperation::ShiftRightLogicalU32 {
            left: 10,
            result: 13,
            right: 11,
            span,
        },
        TernaryOperation::XorU32 {
            left: 12,
            result: 14,
            right: 13,
            span,
        },
        TernaryOperation::MaterializeU32 {
            result: 15,
            scalar: TernaryI32Scalar::from_bits(16),
            span,
        },
        TernaryOperation::LessUnsignedU32 {
            left: 13,
            result: 2,
            right: 15,
            span,
        },
        TernaryOperation::TruncateU32ToU8 {
            result: 16,
            value: 14,
            span,
        },
        TernaryOperation::ByteOutput { value: 16, span },
    ];
    for input in once(TraceInput::EndOfInput)
        .chain((u8::MIN..=u8::MAX).map(TraceInput::Byte))
    {
        let raw = match input {
            TraceInput::Byte(byte) => u32::from(byte),
            TraceInput::EndOfInput => u32::MAX,
        };
        let shifted = raw.wrapping_shl(3u32) ^ raw.wrapping_shr(3u32);
        let expected = u8::try_from(shifted & 0xffu32)
            .map_err(|error| error.to_string())?;
        let true_arm = raw.wrapping_shr(3u32) < 16u32;
        let first = SourceInputSiteObservation {
            input,
            raw_accumulator: raw,
            ..observed(0, 0)
        };
        let second = SourceInputSiteObservation {
            block: if true_arm {
                2
            } else {
                1
            },
            input: TraceInput::EndOfInput,
            raw_accumulator: 14_348_906,
            ..observed(0, 0)
        };
        let observations = [&first, &second];
        let events = [
            SourceInputIoEvent::Input { observation_index: 0 },
            SourceInputIoEvent::Output(expected),
            SourceInputIoEvent::Input { observation_index: 1 },
        ];
        let check = |function: &TernaryCfgFunction, arm, cut, output| {
            source_path_matches_input_walk_with_branch(
                function,
                &observations,
                128,
                true,
                Some(&[output]),
                Some(&events),
                None,
                Some(SourceBranchObligation {
                    after_inputs: 1,
                    io_before_transfer: Some(cut),
                    block: 0,
                    expected_true: arm,
                }),
            )
        };
        assert_eq!(check(&source, true_arm, 2, expected), Ok(true));
        assert_eq!(check(&source, !true_arm, 2, expected), Ok(false));
        assert_eq!(check(&source, true_arm, 1, expected), Ok(false));
        assert_eq!(check(&source, true_arm, 2, expected ^ 1), Ok(false));
        *source
            .blocks
            .first_mut()
            .and_then(|block| block.operations.get_mut(2))
            .ok_or("missing shift count")? = TernaryOperation::MaterializeU32 {
            result: 11,
            scalar: TernaryI32Scalar::from_bits(32),
            span,
        };
        assert_eq!(
            check(&source, true_arm, 2, expected),
            Ok(false),
            "undefined unsigned shift count for {input:?}",
        );
        *source
            .blocks
            .first_mut()
            .and_then(|block| block.operations.get_mut(2))
            .ok_or("missing shift count")? = TernaryOperation::MaterializeU32 {
            result: 11,
            scalar: TernaryI32Scalar::from_bits(3),
            span,
        };
    }
    Ok(())
}

// Signed left shifts require nonnegative, representable results. Arithmetic
// right shift of a negative signed value is implementation-defined in C23,
// so this source proof does not select its value. Neither failure can pass
// by coincidentally matching a physical output byte or proposed branch arm.
#[test]
#[expect(
    clippy::too_many_lines,
    reason = "signed shift variants must share one input and branch oracle"
)]
fn signed_shifts_refuse_overflow_negative_values_and_invalid_counts()
-> Result<(), String> {
    use super::{
        SourceBranchObligation, source_path_matches_input_walk_with_branch,
    };
    let span = dummy_span();
    let mut source = guarded_inequality_fixture();
    source
        .blocks
        .first_mut()
        .ok_or("missing source block")?
        .operations = vec![
        TernaryOperation::GetcharI32 { result: 0, span },
        TernaryOperation::MaterializeI32 {
            result: 10,
            scalar: TernaryI32Scalar::from_bits(4),
            span,
        },
        TernaryOperation::ShiftLeftI32 {
            left: 0,
            result: 11,
            right: 10,
            span,
        },
        TernaryOperation::MaterializeI32 {
            result: 12,
            scalar: TernaryI32Scalar::from_bits(3),
            span,
        },
        TernaryOperation::ShiftRightArithmeticI32 {
            left: 11,
            result: 13,
            right: 12,
            span,
        },
        TernaryOperation::MaterializeI32 {
            result: 14,
            scalar: TernaryI32Scalar::from_bits(100),
            span,
        },
        TernaryOperation::LessSignedI32 {
            left: 13,
            result: 2,
            right: 14,
            span,
        },
        TernaryOperation::TruncateI32ToU8 {
            result: 15,
            value: 13,
            span,
        },
        TernaryOperation::ByteOutput { value: 15, span },
    ];
    let check = |function: &TernaryCfgFunction, input, true_arm, byte| {
        let first = SourceInputSiteObservation {
            input,
            raw_accumulator: match input {
                TraceInput::Byte(input_byte) => u32::from(input_byte),
                TraceInput::EndOfInput => 14_348_906,
            },
            ..observed(0, 0)
        };
        let second = SourceInputSiteObservation {
            block: if true_arm {
                2
            } else {
                1
            },
            input: TraceInput::EndOfInput,
            raw_accumulator: 14_348_906,
            ..observed(0, 0)
        };
        source_path_matches_input_walk_with_branch(
            function,
            &[&first, &second],
            128,
            true,
            Some(&[byte]),
            Some(&[
                SourceInputIoEvent::Input { observation_index: 0 },
                SourceInputIoEvent::Output(byte),
                SourceInputIoEvent::Input { observation_index: 1 },
            ]),
            None,
            Some(SourceBranchObligation {
                after_inputs: 1,
                io_before_transfer: Some(2),
                block: 0,
                expected_true: true_arm,
            }),
        )
    };
    for byte in u8::MIN..=u8::MAX {
        let expected = byte.wrapping_mul(2);
        let arm = u16::from(byte).saturating_mul(2u16) < 100u16;
        assert_eq!(
            check(&source, TraceInput::Byte(byte), arm, expected),
            Ok(true),
            "defined signed shift for {byte}",
        );
        assert_eq!(
            check(&source, TraceInput::Byte(byte), !arm, expected),
            Ok(false),
        );
    }
    assert_eq!(
        check(&source, TraceInput::EndOfInput, true, 254),
        Ok(false),
        "negative C signed left shift cannot select a return",
    );
    for invalid_count in [32u32, u32::MAX] {
        *source
            .blocks
            .first_mut()
            .and_then(|block| block.operations.get_mut(1))
            .ok_or("missing signed shift count")? =
            TernaryOperation::MaterializeI32 {
                result: 10,
                scalar: TernaryI32Scalar::from_bits(invalid_count),
                span,
            };
        assert_eq!(
            check(&source, TraceInput::Byte(1), true, 0),
            Ok(false),
            "invalid signed count {invalid_count}",
        );
    }
    *source
        .blocks
        .first_mut()
        .and_then(|block| block.operations.get_mut(1))
        .ok_or("missing signed shift count")? =
        TernaryOperation::MaterializeI32 {
            result: 10,
            scalar: TernaryI32Scalar::from_bits(31),
            span,
        };
    assert_eq!(check(&source, TraceInput::Byte(0), true, 0), Ok(true));
    assert_eq!(check(&source, TraceInput::Byte(1), true, 0), Ok(false));
    // The right shift must not silently adopt the host's arithmetic shift
    // when its signed left operand is negative.
    *source
        .blocks
        .first_mut()
        .and_then(|block| block.operations.get_mut(4))
        .ok_or("missing arithmetic shift")? =
        TernaryOperation::ShiftRightArithmeticI32 {
            left: 0,
            result: 13,
            right: 12,
            span,
        };
    assert_eq!(check(&source, TraceInput::EndOfInput, true, 255), Ok(false),);
    Ok(())
}

// Revisited source blocks must not keep a past defined shift result when a
// later input or shift count makes that very same SSA definition unknown.
// This is essential for the original checksum's backedge path accounting.
#[test]
fn undefined_shift_redefinition_removes_stale_source_scalar() {
    use std::collections::BTreeMap;

    use super::advance_known_source_scalar;

    let span = dummy_span();
    let mut known =
        BTreeMap::from([(1u32, 255u32), (2u32, 3u32), (3u32, 123u32)]);
    let unsigned = TernaryOperation::ShiftLeftU32 {
        left: 1,
        result: 3,
        right: 2,
        span,
    };
    assert!(advance_known_source_scalar(&unsigned, &mut known));
    assert_eq!(known.get(&3), Some(&2040));
    let _prior = known.insert(2, 32);
    assert!(!advance_known_source_scalar(&unsigned, &mut known));
    assert!(!known.contains_key(&3));
    let _prior = known.insert(2, 1);
    assert!(advance_known_source_scalar(&unsigned, &mut known));
    assert_eq!(known.get(&3), Some(&510));
    let _prior = known.remove(&1);
    assert!(advance_known_source_scalar(&unsigned, &mut known));
    assert!(!known.contains_key(&3));

    // The same invalidation is required for negative signed inputs even
    // when an earlier execution of the same result produced a known byte.
    let signed = TernaryOperation::ShiftRightArithmeticI32 {
        left: 1,
        result: 3,
        right: 2,
        span,
    };
    let _prior = known.insert(1, 255);
    let _prior = known.insert(2, 1);
    assert!(advance_known_source_scalar(&signed, &mut known));
    assert_eq!(known.get(&3), Some(&127));
    let _prior = known.insert(1, u32::MAX);
    assert!(advance_known_source_scalar(&signed, &mut known));
    assert!(!known.contains_key(&3));
    let _prior = known.insert(1, 255);
    let _prior = known.insert(2, u32::MAX);
    assert!(!advance_known_source_scalar(&signed, &mut known));
    assert!(!known.contains_key(&3));
}

// A complete source return with a dead arithmetic result must still honor
// C23 definedness before accepting its later observable output.
fn dead_result_source_path(
    operation: TernaryOperation,
    left: u32,
    right: u32,
) -> Result<bool, SourceInputTraceError> {
    let span = dummy_span();
    let function = TernaryCfgFunction {
        blocks: vec![TernaryCfgBlock {
            id: 0,
            operations: vec![
                TernaryOperation::GetcharI32 { result: 0, span },
                TernaryOperation::MaterializeI32 {
                    result: 1,
                    scalar: TernaryI32Scalar::from_bits(left),
                    span,
                },
                TernaryOperation::MaterializeI32 {
                    result: 2,
                    scalar: TernaryI32Scalar::from_bits(right),
                    span,
                },
                operation,
                TernaryOperation::MaterializeU32 {
                    result: 4,
                    scalar: TernaryI32Scalar::from_bits(65),
                    span,
                },
                TernaryOperation::TruncateU32ToU8 {
                    result: 5,
                    value: 4,
                    span,
                },
                TernaryOperation::ByteOutput { value: 5, span },
            ],
            phis: Vec::new(),
            terminator: TernaryCfgTerminator::Return(
                TernaryOperation::ReturnVoid { span },
            ),
        }],
        entry: 0,
        id: 0,
        name: "dead_result".to_owned(),
        span,
    };
    let input = observed(0, 0);
    source_path_matches_input_observables(&function, &[&input], b"A", 32)
}

// Unknown counts and implementation-defined signed right shifts remain possible
// source paths; known undefined left/right shifts must not certify a return.
#[test]
fn executed_undefined_shift_cannot_certify_unrelated_guest_output() {
    let span = dummy_span();
    for (operation, lhs, count, expected) in [
        (
            TernaryOperation::ShiftLeftU32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            1,
            31,
            true,
        ),
        (
            TernaryOperation::ShiftLeftU32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            1,
            32,
            false,
        ),
        (
            TernaryOperation::ShiftRightLogicalU32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            1,
            u32::MAX,
            false,
        ),
        (
            TernaryOperation::ShiftLeftI32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            u32::MAX,
            1,
            false,
        ),
        (
            TernaryOperation::ShiftLeftI32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            255,
            24,
            false,
        ),
        (
            TernaryOperation::ShiftRightArithmeticI32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            17,
            32,
            false,
        ),
        (
            TernaryOperation::ShiftRightArithmeticI32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            u32::MAX,
            1,
            true,
        ),
    ] {
        assert_eq!(
            dead_result_source_path(operation, lhs, count),
            Ok(expected),
            "dead shift {operation:?}, lhs={lhs}, count={count}"
        );
    }
}

// As with shifts, executing undefined arithmetic is not a valid C23
// return, even when subsequent guest I/O uses an independent constant.
#[test]
fn executed_undefined_arithmetic_cannot_certify_unrelated_output() {
    let span = dummy_span();
    for (operation, lhs, rhs, expected) in [
        (
            TernaryOperation::AddI32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            0x7fff_ffff,
            1,
            false,
        ),
        (
            TernaryOperation::AddI32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            10,
            1,
            true,
        ),
        (
            TernaryOperation::SubtractI32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            0x8000_0000,
            1,
            false,
        ),
        (
            TernaryOperation::MultiplyI32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            0x7fff_ffff,
            2,
            false,
        ),
        (
            TernaryOperation::DivideI32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            1,
            0,
            false,
        ),
        (
            TernaryOperation::DivideI32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            9,
            3,
            true,
        ),
        (
            TernaryOperation::DivideU32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            1,
            0,
            false,
        ),
        (
            TernaryOperation::RemainderI32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            0x8000_0000,
            u32::MAX,
            false,
        ),
        (
            TernaryOperation::RemainderU32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            1,
            0,
            false,
        ),
        (
            TernaryOperation::AddU32 {
                left: 1,
                result: 3,
                right: 2,
                span,
            },
            u32::MAX,
            1,
            true,
        ),
    ] {
        assert_eq!(
            dead_result_source_path(operation, lhs, rhs),
            Ok(expected),
            "dead arithmetic {operation:?}, lhs={lhs}, rhs={rhs}",
        );
    }
}

// A source EOF guard loops through the same read/shift SSA slots.
// Each iteration must use *that iteration's* input and preserve proposed
// input/output ordering; a stale shifted result cannot justify an output.
#[test]
#[expect(
    clippy::too_many_lines,
    reason = "three source CFG blocks and complete four-input I/O walk"
)]
fn source_known_unsigned_shift_loop_rederives_each_read_before_eof() {
    let span = dummy_span();
    let function = TernaryCfgFunction {
        blocks: vec![
            TernaryCfgBlock {
                id: 0,
                operations: vec![
                    TernaryOperation::GetcharI32 { result: 0, span },
                    TernaryOperation::MaterializeI32 {
                        result: 1,
                        scalar: TernaryI32Scalar::from_bits(u32::MAX),
                        span,
                    },
                    TernaryOperation::NotEqualI32 {
                        left: 0,
                        result: 2,
                        right: 1,
                        span,
                    },
                ],
                phis: Vec::new(),
                terminator: TernaryCfgTerminator::Branch {
                    condition: 2,
                    false_target: 2,
                    span,
                    true_target: 1,
                },
            },
            TernaryCfgBlock {
                id: 1,
                operations: vec![
                    TernaryOperation::BitcastI32ToU32 {
                        result: 3,
                        value: 0,
                        span,
                    },
                    TernaryOperation::MaterializeU32 {
                        result: 4,
                        scalar: TernaryI32Scalar::from_bits(3),
                        span,
                    },
                    TernaryOperation::ShiftRightLogicalU32 {
                        left: 3,
                        result: 5,
                        right: 4,
                        span,
                    },
                    TernaryOperation::ShiftLeftU32 {
                        left: 5,
                        result: 7,
                        right: 4,
                        span,
                    },
                    TernaryOperation::TruncateU32ToU8 {
                        result: 8,
                        value: 7,
                        span,
                    },
                    TernaryOperation::ByteOutput { value: 8, span },
                ],
                phis: Vec::new(),
                terminator: TernaryCfgTerminator::Jump { target: 0, span },
            },
            TernaryCfgBlock {
                id: 2,
                operations: Vec::new(),
                phis: Vec::new(),
                terminator: TernaryCfgTerminator::Return(
                    TernaryOperation::ReturnVoid { span },
                ),
            },
        ],
        entry: 0,
        id: 0,
        name: "shift_until_eof".to_owned(),
        span,
    };
    let inputs = [
        TraceInput::Byte(0),
        TraceInput::Byte(0x80),
        TraceInput::Byte(0xff),
        TraceInput::EndOfInput,
    ];
    let observations = inputs.map(|input| SourceInputSiteObservation {
        input,
        raw_accumulator: match input {
            TraceInput::Byte(byte) => u32::from(byte),
            TraceInput::EndOfInput => 14_348_906,
        },
        ..observed(0, 0)
    });
    let refs = observations.iter().collect::<Vec<_>>();
    let expected = [0u8, 0x80, 0xf8];
    let events = [
        SourceInputIoEvent::Input { observation_index: 0 },
        SourceInputIoEvent::Output(0),
        SourceInputIoEvent::Input { observation_index: 1 },
        SourceInputIoEvent::Output(0x80),
        SourceInputIoEvent::Input { observation_index: 2 },
        SourceInputIoEvent::Output(0xf8),
        SourceInputIoEvent::Input { observation_index: 3 },
    ];
    let check = |function: &TernaryCfgFunction, observed: &[_], output, io| {
        source_path_matches_input_walk(
            function,
            observed,
            4096,
            true,
            Some(output),
            Some(io),
            None,
        )
    };
    assert_eq!(check(&function, &refs, &expected, &events), Ok(true));
    assert_eq!(
        check(&function, &refs, &[0, 0x80, 0xff], &events),
        Ok(false)
    );
    assert_eq!(check(&function, &refs, &[0, 0, 0xf8], &events), Ok(false));
    let [
        first_read,
        _first_out,
        second_read,
        second_out,
        third_read,
        third_out,
        eof_read,
    ] = events;
    let wrong_order = [
        SourceInputIoEvent::Output(0),
        first_read,
        second_read,
        second_out,
        third_read,
        third_out,
        eof_read,
    ];
    assert_eq!(check(&function, &refs, &expected, &wrong_order), Ok(false));
    let truncated = refs.iter().take(3).copied().collect::<Vec<_>>();
    assert_eq!(check(&function, &truncated, &expected, &events), Ok(false));
    let [_first, second, third, eof] = &observations;
    let early_eof = [eof, second, third, eof];
    assert_eq!(check(&function, &early_eof, &expected, &events), Ok(false));
    let mut invalid = function;
    assert!(
        invalid
            .blocks
            .get_mut(1)
            .and_then(|block| block.operations.get_mut(1))
            .map(|operation| {
                *operation = TernaryOperation::MaterializeU32 {
                    result: 4,
                    scalar: TernaryI32Scalar::from_bits(32),
                    span,
                };
            })
            .is_some()
    );
    assert_eq!(check(&invalid, &refs, &expected, &events), Ok(false));
}

// Exact C32 division and remainder can jointly select one source branch
// and output. The 257 input classes include EOF rather than treating byte
// 255 as -1; zero divisors and signed MIN / -1 stay unprovable.
#[test]
fn defined_unsigned_quotient_remainder_preserve_source_branch_and_io() {
    use super::{
        SourceBranchObligation, source_path_matches_input_walk_with_branch,
    };
    let span = dummy_span();
    let mut source = guarded_inequality_fixture();
    source.blocks[0].operations = vec![
        TernaryOperation::GetcharI32 { result: 0, span },
        TernaryOperation::BitcastI32ToU32 {
            result: 10,
            value: 0,
            span,
        },
        TernaryOperation::MaterializeU32 {
            result: 11,
            scalar: TernaryI32Scalar::from_bits(3),
            span,
        },
        TernaryOperation::DivideU32 {
            left: 10,
            result: 12,
            right: 11,
            span,
        },
        TernaryOperation::RemainderU32 {
            left: 10,
            result: 13,
            right: 11,
            span,
        },
        TernaryOperation::AddU32 {
            left: 12,
            result: 14,
            right: 13,
            span,
        },
        TernaryOperation::MaterializeU32 {
            result: 15,
            scalar: TernaryI32Scalar::from_bits(80),
            span,
        },
        TernaryOperation::LessUnsignedU32 {
            left: 12,
            result: 2,
            right: 15,
            span,
        },
        TernaryOperation::TruncateU32ToU8 {
            result: 16,
            value: 14,
            span,
        },
        TernaryOperation::ByteOutput { value: 16, span },
    ];
    for input in std::iter::once(TraceInput::EndOfInput)
        .chain((u8::MIN..=u8::MAX).map(TraceInput::Byte))
    {
        let raw = match input {
            TraceInput::Byte(byte) => u32::from(byte),
            TraceInput::EndOfInput => u32::MAX,
        };
        let expected = (raw / 3 + raw % 3) as u8;
        let true_arm = raw / 3 < 80;
        let first = SourceInputSiteObservation {
            input,
            raw_accumulator: raw,
            ..observed(0, 0)
        };
        let second = SourceInputSiteObservation {
            block: if true_arm {
                2
            } else {
                1
            },
            input: TraceInput::EndOfInput,
            raw_accumulator: 14_348_906,
            ..observed(0, 0)
        };
        let reads = [&first, &second];
        let io = [
            SourceInputIoEvent::Input { observation_index: 0 },
            SourceInputIoEvent::Output(expected),
            SourceInputIoEvent::Input { observation_index: 1 },
        ];
        let check = |function: &TernaryCfgFunction, arm, cut, output| {
            source_path_matches_input_walk_with_branch(
                function,
                &reads,
                128,
                true,
                Some(&[output]),
                Some(&io),
                None,
                Some(SourceBranchObligation {
                    after_inputs: 1,
                    io_before_transfer: Some(cut),
                    block: 0,
                    expected_true: arm,
                }),
            )
        };
        assert_eq!(check(&source, true_arm, 2, expected), Ok(true));
        assert_eq!(check(&source, !true_arm, 2, expected), Ok(false));
        assert_eq!(check(&source, true_arm, 1, expected), Ok(false));
        assert_eq!(check(&source, true_arm, 2, expected ^ 1), Ok(false));
        source.blocks[0].operations[2] = TernaryOperation::MaterializeU32 {
            result: 11,
            scalar: TernaryI32Scalar::from_bits(0),
            span,
        };
        assert_eq!(check(&source, true_arm, 2, expected), Ok(false));
        source.blocks[0].operations[2] = TernaryOperation::MaterializeU32 {
            result: 11,
            scalar: TernaryI32Scalar::from_bits(3),
            span,
        };
    }
}

#[test]
fn signed_quotient_and_remainder_distinguish_eof_from_high_byte() {
    use super::{
        SourceBranchObligation, source_path_matches_input_walk_with_branch,
    };
    let span = dummy_span();
    let mut source = guarded_inequality_fixture();
    source.blocks[0].operations = vec![
        TernaryOperation::GetcharI32 { result: 0, span },
        TernaryOperation::MaterializeI32 {
            result: 10,
            scalar: TernaryI32Scalar::from_bits(3),
            span,
        },
        TernaryOperation::DivideI32 {
            left: 0,
            result: 11,
            right: 10,
            span,
        },
        TernaryOperation::RemainderI32 {
            left: 0,
            result: 12,
            right: 10,
            span,
        },
        TernaryOperation::MaterializeI32 {
            result: 13,
            scalar: TernaryI32Scalar::from_bits(0),
            span,
        },
        TernaryOperation::LessSignedI32 {
            left: 12,
            result: 2,
            right: 13,
            span,
        },
        TernaryOperation::BitcastI32ToU32 {
            result: 14,
            value: 12,
            span,
        },
        TernaryOperation::TruncateU32ToU8 {
            result: 15,
            value: 14,
            span,
        },
        TernaryOperation::ByteOutput { value: 15, span },
    ];
    let check = |function: &TernaryCfgFunction, first_input, true_arm, byte| {
        let first = SourceInputSiteObservation {
            input: first_input,
            raw_accumulator: match first_input {
                TraceInput::Byte(value) => u32::from(value),
                TraceInput::EndOfInput => 14_348_906,
            },
            ..observed(0, 0)
        };
        let second = SourceInputSiteObservation {
            block: if true_arm {
                2
            } else {
                1
            },
            input: TraceInput::EndOfInput,
            raw_accumulator: 14_348_906,
            ..observed(0, 0)
        };
        source_path_matches_input_walk_with_branch(
            function,
            &[&first, &second],
            128,
            true,
            Some(&[byte]),
            Some(&[
                SourceInputIoEvent::Input { observation_index: 0 },
                SourceInputIoEvent::Output(byte),
                SourceInputIoEvent::Input { observation_index: 1 },
            ]),
            None,
            Some(SourceBranchObligation {
                after_inputs: 1,
                io_before_transfer: Some(2),
                block: 0,
                expected_true: true_arm,
            }),
        )
    };
    for input in std::iter::once(TraceInput::EndOfInput)
        .chain((u8::MIN..=u8::MAX).map(TraceInput::Byte))
    {
        let signed = match input {
            TraceInput::Byte(byte) => i32::from(byte),
            TraceInput::EndOfInput => -1,
        };
        let result = (signed % 3) as u8;
        let arm = signed % 3 < 0;
        assert_eq!(check(&source, input, arm, result), Ok(true));
        assert_eq!(check(&source, input, !arm, result), Ok(false));
    }
    source.blocks[0].operations[1] = TernaryOperation::MaterializeI32 {
        result: 10,
        scalar: TernaryI32Scalar::from_bits(0),
        span,
    };
    assert_eq!(check(&source, TraceInput::Byte(1), false, 0), Ok(false),);
    // The first source input remains real and reaches both operations.
    // MIN divided by successful byte 1 is defined; EOF=-1 overflows,
    // while a successful NUL creates a zero divisor instead.
    source.blocks[0].operations = vec![
        TernaryOperation::GetcharI32 { result: 0, span },
        TernaryOperation::MaterializeI32 {
            result: 10,
            scalar: TernaryI32Scalar::from_bits(i32::MIN as u32),
            span,
        },
        TernaryOperation::DivideI32 {
            left: 10,
            result: 11,
            right: 0,
            span,
        },
        TernaryOperation::RemainderI32 {
            left: 10,
            result: 12,
            right: 0,
            span,
        },
        TernaryOperation::MaterializeI32 {
            result: 13,
            scalar: TernaryI32Scalar::from_bits(0),
            span,
        },
        TernaryOperation::LessSignedI32 {
            left: 12,
            result: 2,
            right: 13,
            span,
        },
        TernaryOperation::BitcastI32ToU32 {
            result: 14,
            value: 12,
            span,
        },
        TernaryOperation::TruncateU32ToU8 {
            result: 15,
            value: 14,
            span,
        },
        TernaryOperation::ByteOutput { value: 15, span },
    ];
    assert_eq!(check(&source, TraceInput::Byte(1), false, 0), Ok(true));
    assert_eq!(check(&source, TraceInput::Byte(0), false, 0), Ok(false));
    assert_eq!(check(&source, TraceInput::EndOfInput, false, 0), Ok(false));
}

// A valid source branch may follow an output effect. The full-I/O cut gate
// must admit that ordering while rejecting the same final bytes if the guest
// transfers before the source's preceding output has occurred.
#[test]
fn source_branch_io_cut_can_follow_output_on_one_known_path() {
    use super::{
        SourceBranchObligation, source_path_matches_input_walk_with_branch,
    };

    let span = dummy_span();
    let mut function = guarded_inequality_fixture();
    function.blocks[0].operations.extend([
        TernaryOperation::BitcastI32ToU32 {
            result: 5,
            value: 0,
            span,
        },
        TernaryOperation::TruncateU32ToU8 {
            result: 6,
            value: 5,
            span,
        },
        TernaryOperation::ByteOutput { value: 6, span },
    ]);
    let first = observed(0, 0);
    let second = observed(2, 0);
    let observations = [&first, &second];
    let correct = [
        SourceInputIoEvent::Input { observation_index: 0 },
        SourceInputIoEvent::Output(3),
        SourceInputIoEvent::Input { observation_index: 1 },
    ];
    let reordered = [correct[0], correct[2], correct[1]];
    for (cut, events, expected) in [
        (2, &correct[..], true),
        (0, &correct[..], false),
        (1, &correct[..], false),
        (3, &correct[..], false),
        (2, &reordered[..], false),
    ] {
        assert_eq!(
            source_path_matches_input_walk_with_branch(
                &function,
                &observations,
                128,
                true,
                Some(&[3]),
                Some(events),
                None,
                Some(SourceBranchObligation {
                    after_inputs: 1,
                    io_before_transfer: Some(cut),
                    block: 0,
                    expected_true: true,
                }),
            ),
            Ok(expected),
            "source output and physical branch cut {cut}; events {events:?}",
        );
    }
}

#[test]
fn source_guest_branch_chronology_uses_vm_trace_steps_not_code_addresses() {
    use super::super::indirect_source_suffix as suffix;

    // Reached C53 is at step 53, but reached C101 occurs on the
    // indirect-selected arm at trace step 171. A guest branch at step 114
    // is therefore after exactly one input, not two.
    assert_eq!(
        suffix::source_read_count_before_guest_transfer([53, 171], 114),
        1,
    );
    assert_eq!(
        suffix::source_read_count_before_guest_transfer([53, 101], 114),
        2,
    );
    assert_eq!(
        suffix::source_read_count_before_guest_transfer([53, 171], 172),
        2,
    );
    assert_eq!(
        suffix::source_read_count_before_guest_transfer([53, 114], 114),
        1,
    );
}

#[test]
fn exhausted_source_path_search_is_not_an_unreachable_path_proof() {
    let function = guarded_inequality_fixture();
    let first = observed(0, 0);
    let second = observed(2, 0);
    assert_eq!(
        source_path_matches_input_prefix(&function, &[&first, &second], 1),
        Err(SourceInputTraceError::SourceInputSearchLimit)
    );
    assert_eq!(
        source_path_matches_input_prefix(&function, &[&first, &second], 128),
        Ok(true)
    );
}

fn guarded_byte_cast_fixture() -> TernaryCfgFunction {
    let span = dummy_span();
    let mut function = guarded_inequality_fixture();
    let Some(block) = function.blocks.first_mut() else {
        return function;
    };
    block.operations = vec![
        TernaryOperation::GetcharI32 { result: 0, span },
        TernaryOperation::BitcastI32ToU32 {
            result: 1,
            value: 0,
            span,
        },
        TernaryOperation::TruncateU32ToU8 {
            result: 2,
            value: 1,
            span,
        },
        TernaryOperation::U8ToBool {
            result: 3,
            value: 2,
            span,
        },
    ];
    block.terminator = TernaryCfgTerminator::Branch {
        condition: 3,
        false_target: 1,
        true_target: 2,
        span,
    };
    function
}

#[test]
fn source_known_c23_casts_preserve_zero_and_truncate_eof() {
    let function = guarded_byte_cast_fixture();
    let first_zero = SourceInputSiteObservation {
        input: TraceInput::Byte(0),
        raw_accumulator: 0,
        ..observed(0, 0)
    };
    let first_high = SourceInputSiteObservation {
        input: TraceInput::Byte(255),
        raw_accumulator: 255,
        ..observed(0, 0)
    };
    let first_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..observed(0, 0)
    };
    let zero_arm = observed(1, 0);
    let nonzero_arm = observed(2, 0);
    for (first, expected_block) in
        [(first_zero, 1u32), (first_high, 2u32), (first_eof, 2u32)]
    {
        for (arm, block) in [(zero_arm, 1u32), (nonzero_arm, 2u32)] {
            assert_eq!(
                source_path_matches_input_prefix(
                    &function,
                    &[&first, &arm],
                    128,
                ),
                Ok(block == expected_block),
                "source input {first:?}, successor block {block}",
            );
        }
    }
}

#[test]
fn source_known_equality_selects_only_the_matching_input_arm() {
    let mut function = guarded_inequality_fixture();
    let span = dummy_span();
    if let Some(operation) = function
        .blocks
        .first_mut()
        .and_then(|block| block.operations.get_mut(2))
    {
        *operation = TernaryOperation::EqualI32 {
            left: 0,
            result: 2,
            right: 1,
            span,
        };
    }
    let first_byte = observed(0, 0);
    let first_eof = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..first_byte
    };
    let false_arm = observed(1, 0);
    let true_arm = observed(2, 0);
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_byte, &true_arm],
            128
        ),
        Ok(false),
    );
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_eof, &false_arm],
            128
        ),
        Ok(false),
    );
    assert_eq!(
        source_path_matches_input_prefix(
            &function,
            &[&first_eof, &true_arm],
            128
        ),
        Ok(true),
    );
}

fn guarded_threshold_fixture(unsigned: bool) -> TernaryCfgFunction {
    let span = dummy_span();
    let mut function = guarded_inequality_fixture();
    let Some(block) = function.blocks.first_mut() else {
        return function;
    };
    let initial_read = TernaryOperation::GetcharI32 { result: 0, span };
    let threshold = TernaryI32Scalar::from_bits(128);
    if unsigned {
        block.operations = vec![
            initial_read,
            TernaryOperation::BitcastI32ToU32 {
                value: 0,
                result: 5,
                span,
            },
            TernaryOperation::MaterializeU32 {
                result: 1,
                scalar: threshold,
                span,
            },
            TernaryOperation::LessUnsignedU32 {
                left: 5,
                right: 1,
                result: 2,
                span,
            },
        ];
    } else {
        block.operations = vec![
            initial_read,
            TernaryOperation::MaterializeI32 {
                result: 1,
                scalar: threshold,
                span,
            },
            TernaryOperation::LessSignedI32 {
                left: 0,
                right: 1,
                result: 2,
                span,
            },
        ];
    }
    function
}

#[test]
fn source_known_signed_and_unsigned_thresholds_separate_eof_from_bytes() {
    let signed = guarded_threshold_fixture(false);
    let unsigned = guarded_threshold_fixture(true);
    let first = observed(0, 0);
    let false_arm = observed(1, 0);
    let true_arm = observed(2, 0);
    for (input, signed_true, unsigned_true) in [
        (TraceInput::Byte(0), true, true),
        (TraceInput::Byte(127), true, true),
        (TraceInput::Byte(128), false, false),
        (TraceInput::Byte(255), false, false),
        (TraceInput::EndOfInput, true, false),
    ] {
        let current = SourceInputSiteObservation { input, ..first };
        for (function, expected) in
            [(&signed, signed_true), (&unsigned, unsigned_true)]
        {
            assert_eq!(
                source_path_matches_input_prefix(
                    function,
                    &[&current, &true_arm],
                    128,
                ),
                Ok(expected),
            );
            assert_eq!(
                source_path_matches_input_prefix(
                    function,
                    &[&current, &false_arm],
                    128,
                ),
                Ok(!expected),
            );
        }
    }
}

// This oracle walks the original normalized C CFG, not the guest VM. Every
// real source input (including true EOF) must reach exactly the one C output
// byte; arbitrary output guesses must not satisfy the authenticated path.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "independently computed checksum and source CFG output assertions"
)]
fn complete_checksum_source_paths_require_exact_output_bytes()
-> Result<(), String> {
    let cfg = lower_canonical_dynamic_cfg(&checksum_wire()?)
        .map_err(|error| format!("{error:?}"))?;
    let source = cfg.functions.first().ok_or("missing checksum function")?;
    for input in [vec![], vec![0], vec![0xff], vec![1, 0, 0x80, 0xfe], vec![
        5, 0, 0x81,
    ]] {
        let first = observed(0, 1);
        let next = observed(5, 2);
        let mut reads = Vec::new();
        for (index, byte) in input.iter().copied().enumerate() {
            let site = if index == 0 {
                first
            } else {
                next
            };
            reads.push(SourceInputSiteObservation {
                input: TraceInput::Byte(byte),
                raw_accumulator: u32::from(byte),
                ..site
            });
        }
        reads.push(SourceInputSiteObservation {
            input: TraceInput::EndOfInput,
            raw_accumulator: 14_348_906,
            ..if input.is_empty() {
                first
            } else {
                next
            }
        });
        let observations = reads.iter().collect::<Vec<_>>();
        let mut checksum = 0u8;
        for byte in &input {
            checksum = if byte & 1 == 0 {
                checksum.wrapping_add(*byte)
            } else {
                checksum ^ byte
            };
            checksum = checksum.wrapping_add(3);
        }
        assert_eq!(
            source_path_matches_input_observables(
                source,
                &observations,
                &[checksum],
                16_384,
            ),
            Ok(true),
            "source refused correct checksum for {input:?}"
        );
        assert_eq!(
            source_path_matches_input_observables(
                source,
                &observations,
                &[checksum ^ 1],
                16_384,
            ),
            Ok(false),
            "source admitted incorrect checksum for {input:?}"
        );
    }
    Ok(())
}

// The unchanged original C23 checksum gives a source-only positive control;
// none of these synthetic receipts pretends to be a normative guest VM run.
fn checksum_guard_binding() -> SourceBranchLanding {
    SourceBranchLanding {
        after_inputs: 1,
        block: 1,
        false_landing: 126,
        function: 0,
        true_landing: 45,
    }
}

fn synthetic_checksum_receipt(
    observations: Vec<SourceInputSiteObservation>,
    output: u8,
    output_sites: Vec<SourceOutputSiteObservation>,
) -> SourceInputPrefixProof {
    let input_events =
        observations.iter().enumerate().filter_map(|(index, _)| {
            u16::try_from(index).ok().map(|observation_index| {
                SourceInputIoEvent::Input { observation_index }
            })
        });
    SourceInputPrefixProof {
        bytes_consumed: observations
            .iter()
            .filter(|site| matches!(site.input, TraceInput::Byte(_)))
            .count(),
        guest_output: vec![output],
        io_events: input_events
            .chain(std::iter::once(SourceInputIoEvent::Output(output)))
            .collect(),
        output_sites,
        observations,
        outcome: malbolge::RunOutcome::Terminated {
            reason: malbolge::Termination::HaltInstruction,
            steps: 1,
        },
    }
}

fn checksum_source_output_identity(wire: &[u8]) -> Result<(u32, u32), String> {
    let cfg = lower_canonical_dynamic_cfg(wire)
        .map_err(|error| format!("{error:?}"))?;
    let function = cfg.functions.first().ok_or("missing checksum function")?;
    function
        .blocks
        .iter()
        .find_map(|block| {
            block
                .operations
                .iter()
                .position(|operation| {
                    matches!(operation, TernaryOperation::ByteOutput { .. })
                })
                .and_then(|source_ordinal| {
                    u32::try_from(source_ordinal)
                        .ok()
                        .map(|ordinal| (block.id, ordinal))
                })
        })
        .ok_or_else(|| "missing source checksum output".to_owned())
}

fn byte_then_eof_checksum_receipt(
    first: u8,
    output_identity: (u32, u32),
) -> SourceInputPrefixProof {
    let checksum = first.wrapping_add(3);
    synthetic_checksum_receipt(
        vec![
            SourceInputSiteObservation {
                input: TraceInput::Byte(first),
                raw_accumulator: u32::from(first),
                ..observed(0, 1)
            },
            SourceInputSiteObservation {
                input: TraceInput::EndOfInput,
                raw_accumulator: 14_348_906,
                ..observed(5, 2)
            },
        ],
        checksum,
        vec![SourceOutputSiteObservation {
            block: output_identity.0,
            byte: checksum,
            code_address: 128,
            function: 0,
            ordinal: output_identity.1,
            trace_index: 3,
        }],
    )
}

// Both the first EOF and the exact final output must agree on one return.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "complete source guard and I/O path obligations"
)]
fn checksum_first_eof_guard_and_output_share_a_source_return()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let proof = synthetic_checksum_receipt(
        vec![SourceInputSiteObservation {
            input: TraceInput::EndOfInput,
            raw_accumulator: 14_348_906,
            ..observed(0, 1)
        }],
        0,
        Vec::new(),
    );
    let branch = checksum_guard_binding();
    assert_eq!(
        verify_source_branch_io_landing(&wire, &proof, branch, 126, 1),
        Ok(()),
    );
    assert_eq!(
        verify_source_branch_io_landing(&wire, &proof, branch, 45, 1),
        Err(SourceInputTraceError::SourceOutputNotProven),
    );
    // Correct output bytes cannot certify a branch executed before its
    // source input, or after an early guest output. This check binds the
    // physical transfer to its exact cut in the complete I/O timeline.
    for wrong_cut in [0, 2, 3] {
        assert_eq!(
            verify_source_branch_io_landing(
                &wire, &proof, branch, 126, wrong_cut,
            ),
            Err(SourceInputTraceError::SourceOutputNotProven),
            "physical transfer after {wrong_cut} I/O events",
        );
    }
    let mut malformed = proof;
    malformed.io_events.reverse();
    assert_eq!(
        verify_source_branch_io_landing(&wire, &malformed, branch, 126, 1),
        Err(SourceInputTraceError::SourceOutputNotProven),
    );
    malformed.io_events = vec![
        SourceInputIoEvent::Input { observation_index: 0 },
        SourceInputIoEvent::Output(30),
    ];
    malformed.guest_output = vec![30];
    assert_eq!(
        verify_source_branch_io_landing(&wire, &malformed, branch, 126, 1),
        Err(SourceInputTraceError::SourceOutputNotProven),
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "known checksum and branch truth across byte/EOF paths"
)]
fn checksum_first_byte_guard_and_output_share_a_source_return()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let output_identity = checksum_source_output_identity(&wire)?;
    let branch = checksum_guard_binding();
    for first in [0u8, 1, 254, 255] {
        let proof = byte_then_eof_checksum_receipt(first, output_identity);
        assert_eq!(
            verify_source_branch_io_landing(&wire, &proof, branch, 45, 1),
            Ok(()),
            "first byte {first} followed by actual EOF",
        );
        assert_eq!(
            verify_source_branch_io_landing(&wire, &proof, branch, 126, 1),
            Err(SourceInputTraceError::SourceOutputNotProven),
            "a successful first byte cannot select the EOF arm",
        );
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source identity and exact physical I/O chronology"
)]
fn checksum_source_output_identity_and_eof_order_cannot_be_forged()
-> Result<(), String> {
    let wire = checksum_wire()?;
    let output_identity = checksum_source_output_identity(&wire)?;
    let branch = checksum_guard_binding();
    let mut proof = byte_then_eof_checksum_receipt(1, output_identity);
    let output_site = proof
        .output_sites
        .first_mut()
        .ok_or("missing synthetic source output site")?;
    output_site.ordinal = output_identity.1.saturating_add(1);
    assert_eq!(
        verify_source_branch_io_landing(&wire, &proof, branch, 45, 1),
        Err(SourceInputTraceError::SourceOutputNotProven),
        "the same byte from a different source output is not interchangeable",
    );
    proof
        .output_sites
        .first_mut()
        .ok_or("missing synthetic source output site")?
        .ordinal = output_identity.1;
    proof.io_events.swap(1, 2);
    assert_eq!(
        verify_source_branch_io_landing(&wire, &proof, branch, 45, 1),
        Err(SourceInputTraceError::SourceOutputNotProven),
        "the C checksum output must follow the final EOF read",
    );
    Ok(())
}

// Undefined C division must not be promoted into a known byte merely
// because a guest happened to emit a particular result.
#[test]
fn undefined_source_division_cannot_certify_guest_output() {
    let span = dummy_span();
    let function = TernaryCfgFunction {
        blocks: vec![TernaryCfgBlock {
            id: 0,
            operations: vec![
                TernaryOperation::GetcharI32 { result: 0, span },
                TernaryOperation::MaterializeU32 {
                    result: 1,
                    scalar: TernaryI32Scalar::from_bits(0),
                    span,
                },
                TernaryOperation::DivideU32 {
                    left: 0,
                    result: 2,
                    right: 1,
                    span,
                },
                TernaryOperation::TruncateU32ToU8 {
                    result: 3,
                    value: 2,
                    span,
                },
                TernaryOperation::ByteOutput { value: 3, span },
            ],
            phis: Vec::new(),
            terminator: TernaryCfgTerminator::Return(
                TernaryOperation::ReturnVoid { span },
            ),
        }],
        entry: 0,
        id: 0,
        name: "unknown_output".to_owned(),
        span,
    };
    let first = observed(0, 0);
    assert_eq!(
        source_path_matches_input_observables(&function, &[&first], &[0], 128),
        Ok(false),
    );
    // The physical input is still a valid prefix, but no complete C return
    // can pass through an executed, source-known division by zero.
    assert_eq!(
        source_path_matches_input_prefix(&function, &[&first], 128),
        Ok(true),
    );
    assert_eq!(
        source_path_matches_input_trace(&function, &[&first], 128, true),
        Ok(false),
    );
    let mut defined = function;
    defined.blocks[0].operations[1] = TernaryOperation::MaterializeU32 {
        result: 1,
        scalar: TernaryI32Scalar::from_bits(1),
        span,
    };
    assert_eq!(
        source_path_matches_input_observables(&defined, &[&first], &[3], 128),
        Ok(true),
    );
}

// Unsigned C32 additions wrap even when the guest must preserve two words.
// Reject a forged output and missing/extra outputs after a valid source return.
#[test]
fn known_source_unsigned_addition_preserves_full_width_wraparound() {
    let span = dummy_span();
    let function = TernaryCfgFunction {
        blocks: vec![TernaryCfgBlock {
            id: 0,
            operations: vec![
                TernaryOperation::MaterializeU32 {
                    result: 0,
                    scalar: TernaryI32Scalar::from_bits(u32::MAX),
                    span,
                },
                TernaryOperation::MaterializeU32 {
                    result: 1,
                    scalar: TernaryI32Scalar::from_bits(2),
                    span,
                },
                TernaryOperation::AddU32 {
                    left: 0,
                    result: 2,
                    right: 1,
                    span,
                },
                TernaryOperation::TruncateU32ToU8 {
                    result: 3,
                    value: 2,
                    span,
                },
                TernaryOperation::ByteOutput { value: 3, span },
            ],
            phis: Vec::new(),
            terminator: TernaryCfgTerminator::Return(
                TernaryOperation::ReturnVoid { span },
            ),
        }],
        entry: 0,
        id: 0,
        name: "unsigned_wrap".to_owned(),
        span,
    };
    assert_eq!(
        source_path_matches_input_observables(&function, &[], &[1], 128),
        Ok(true),
    );
    for wrong in [&[][..], &[0][..], &[1, 1][..], &[255][..]] {
        assert_eq!(
            source_path_matches_input_observables(&function, &[], wrong, 128),
            Ok(false),
        );
    }
}

// Matching the final bytes is not enough: the source checksum emits only
// after the exact final EOF input, not before a pending source read.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "original source CFG checks independently ordered physical I/O"
)]
fn checksum_source_io_requires_output_after_final_eof() -> Result<(), String> {
    let cfg = lower_canonical_dynamic_cfg(&checksum_wire()?)
        .map_err(|error| format!("{error:?}"))?;
    let source = cfg.functions.first().ok_or("missing source CFG")?;
    let first = SourceInputSiteObservation {
        input: TraceInput::Byte(1),
        raw_accumulator: 1,
        ..observed(0, 1)
    };
    let end = SourceInputSiteObservation {
        input: TraceInput::EndOfInput,
        raw_accumulator: 14_348_906,
        ..observed(5, 2)
    };
    let input_zero = SourceInputIoEvent::Input { observation_index: 0 };
    let input_one = SourceInputIoEvent::Input { observation_index: 1 };
    let output = SourceInputIoEvent::Output(4);
    let observed = [&first, &end];
    let good = [input_zero, input_one, output];
    let early = [input_zero, output, input_one];
    let reordered = [input_one, input_zero, output];
    for (events, valid) in [
        (&good[..], true),
        (&early[..], false),
        (&reordered[..], false),
    ] {
        assert_eq!(
            source_path_matches_input_walk(
                source,
                &observed,
                16_384,
                true,
                Some(&[4]),
                Some(events),
                None,
            ),
            Ok(valid),
            "I/O order {events:?}"
        );
    }
    Ok(())
}

// The same physical 132-cell byte/EOF branch can host two source-identified
// input effect sites even when their proposed code blocks reserve extra room
// for operand setup. This is input-only, not source-C state or CFG linkage.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "bounded source-locked and normative-guest input admission"
)]
fn physically_reached_input_effects_allow_expanded_code_block_anchors()
-> Result<(), String> {
    use malbolge::{RunOutcome, Termination, current_profile};

    use super::super::indirect_source_suffix::{
        SourceBoundIndirectGuestError as BoundError,
        SourceBoundIndirectGuestProbe, SourceInputPointerOrigin,
        SourceWrittenIndirectGuestError as PointerError,
        SourceWrittenIndirectGuestVerifier,
    };
    use super::super::signed_eof_branch_source as signed_source;
    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeEdgeKind, GuestCodeEdgePadPlacement,
        GuestCodeEffectAnchor, GuestCodeInputAnchor, GuestCodeOperationAnchor,
        GuestCodeProposals,
    };
    use super::{SourceBranchLanding, SourceInputProbe};

    let wire = checksum_wire()?;
    let physical = signed_source::build_guarded_signed_eof_second_read_source(
        current_profile(),
    )
    .map_err(|error| format!("{error:?}"))?;
    assert_eq!(physical.len(), 132);
    let blocks = [
        (0, 40, 66, 67),
        (1, 0, 1, 2),
        (2, 2, 5, 6),
        (3, 6, 10, 11),
        (4, 11, 15, 16),
        (5, 91, 104, 105),
        (6, 16, 18, 19),
    ]
    .map(|(block, start, control_start, end_exclusive)| {
        GuestCodeBlockPlacement {
            block,
            control_start,
            end_exclusive,
            function: 0,
            start,
        }
    });
    let pads = [
        (0, 1, 19, 28),
        (3, 5, 28, 33),
        (4, 5, 33, 38),
        (5, 1, 105, 114),
    ]
    .map(|(predecessor, successor, start, end_exclusive)| {
        GuestCodeEdgePadPlacement {
            end_exclusive,
            function: 0,
            kind: GuestCodeEdgeKind::Jump,
            predecessor,
            start,
            successor,
        }
    });
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &pads,
    };
    let read_sites = [
        GuestCodeInputAnchor {
            block: 0,
            code_address: 53,
            function: 0,
            ordinal: 1,
        },
        GuestCodeInputAnchor {
            block: 5,
            code_address: 101,
            function: 0,
            ordinal: 2,
        },
    ];
    let operation_anchors = [
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 53,
            function: 0,
            ordinal: 1,
        },
        GuestCodeOperationAnchor {
            block: 5,
            code_address: 101,
            function: 0,
            ordinal: 2,
        },
    ];
    // Independently bind the first real C23 getchar SSA operation to the
    // physical guest-written M143 pointer and reached C114 i branch.
    let pointer_verifier =
        SourceWrittenIndirectGuestVerifier::new(current_profile(), &physical)
            .map_err(|error| format!("physical guest source: {error:?}"))?;
    let first_getchar = [SourceInputPointerOrigin {
        block: 0,
        function: 0,
        ordinal: 1,
    }];
    let second_getchar = [SourceInputPointerOrigin {
        block: 5,
        function: 0,
        ordinal: 2,
    }];
    // The real first getchar guards a typed source branch. These two
    // physical destinations have independent runtime pointer provenance.
    let source_first_guard = SourceBranchLanding {
        after_inputs: 1,
        block: 1,
        false_landing: 126,
        function: 0,
        true_landing: 45,
    };
    for (input, expected, steps) in [
        (&[][..], vec![(53, TraceInput::EndOfInput)], 119),
        (
            &[0][..],
            vec![(53, TraceInput::Byte(0)), (101, TraceInput::EndOfInput)],
            175,
        ),
        (
            &[255][..],
            vec![(53, TraceInput::Byte(255)), (101, TraceInput::EndOfInput)],
            175,
        ),
        (
            &[0, 0][..],
            vec![(53, TraceInput::Byte(0)), (101, TraceInput::Byte(0))],
            175,
        ),
        (
            &[255, 0, 44][..],
            vec![(53, TraceInput::Byte(255)), (101, TraceInput::Byte(0))],
            175,
        ),
    ] {
        let proof = SourceInputProbe {
            anchors: &read_sites,
            canonical: &wire,
            frame_base: 256,
            input,
            physical_source: &physical,
            step_budget: 175,
        }
        .verify_with_operation_anchors(proposals, &operation_anchors)
        .map_err(|error| format!("source-bound guest: {error:?}"))?;
        assert_eq!(proof.outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps,
        });
        assert_eq!(
            proof
                .observations
                .iter()
                .map(|event| (event.code_address, event.input))
                .collect::<Vec<_>>(),
            expected
        );
        let source_input = SourceInputProbe {
            anchors: &read_sites,
            canonical: &wire,
            frame_base: 256,
            input,
            physical_source: &physical,
            step_budget: 175,
        };
        let requested = SourceBoundIndirectGuestProbe {
            allowed_landings: &[45, 126],
            indirect_code_cell: 114,
            operation_anchors: &operation_anchors,
            origins: &first_getchar,
            pointer_cell: 143,
            proposals,
            source_input,
        };
        let joined = pointer_verifier
            .verify_source_bound(&requested)
            .map_err(|error| format!("typed C input to guest i: {error:?}"))?;
        assert_eq!(joined.source_input(), &proof);
        assert_eq!(joined.guest_pointer().pointer_input_steps(), &[53]);
        assert_eq!(joined.guest_pointer().pointer_write_step(), 82);
        assert_eq!(joined.guest_pointer().transfer_step(), 114);
        assert_eq!(joined.guest_pointer().steps(), steps);
        // A source input prefix alone can accept a guest that halts before
        // the C EOF loop would consume the next byte. Require a separate
        // typed source-return-compatible path before treating reads as final.
        let source_return =
            pointer_verifier.verify_source_return_bound(&requested);
        if input.len() >= 2 {
            assert_eq!(
                source_return,
                Err(BoundError::SourceInput(
                    SourceInputTraceError::UnreachedSourceInput,
                )),
            );
        } else {
            assert_eq!(
                source_return.map_err(|error| format!("{error:?}"))?,
                joined,
            );
        }
        let source_branch = pointer_verifier
            .verify_source_return_branch_bound(&requested, source_first_guard);
        if input.len() >= 2 {
            assert_eq!(
                source_branch,
                Err(BoundError::SourceInput(
                    SourceInputTraceError::UnreachedSourceInput,
                )),
            );
        } else {
            assert_eq!(
                source_branch.map_err(|error| format!("{error:?}"))?,
                joined,
            );
            for (wrong, expected) in [
                (
                    SourceBranchLanding {
                        false_landing: 45,
                        true_landing: 126,
                        ..source_first_guard
                    },
                    SourceInputTraceError::SourceBranchMismatch,
                ),
                (
                    SourceBranchLanding {
                        after_inputs: 2,
                        ..source_first_guard
                    },
                    if input.is_empty() {
                        SourceInputTraceError::InvalidBranchBinding
                    } else {
                        SourceInputTraceError::SourceBranchMismatch
                    },
                ),
                (
                    SourceBranchLanding {
                        block: 5,
                        ..source_first_guard
                    },
                    SourceInputTraceError::InvalidBranchBinding,
                ),
                (
                    SourceBranchLanding {
                        false_landing: 45,
                        true_landing: 45,
                        ..source_first_guard
                    },
                    SourceInputTraceError::InvalidBranchBinding,
                ),
            ] {
                assert_eq!(
                    pointer_verifier
                        .verify_source_return_branch_bound(&requested, wrong),
                    Err(BoundError::SourceInput(expected)),
                    "forged typed branch {wrong:?}",
                );
            }
        }
        // Source branch sequencing is checked using actual transition
        // indexes, not the C101 code address. The second read executes at
        // trace step 171, *after* the C114 indirect transfer at step 114.
        // Both EOF and successful-byte cases respect first-guard ordering.
        assert_eq!(
            pointer_verifier
                .verify_source_return_branch_ordered(
                    &requested,
                    source_first_guard,
                )
                .map(|_proof| ()),
            if input.len() <= 1 {
                Ok(())
            } else {
                Err(BoundError::SourceInput(
                    SourceInputTraceError::UnreachedSourceInput,
                ))
            },
            "guest branch input chronology for {input:?}",
        );
        // The reached C114 guest branch, like the source first guard,
        // occurs after exactly one read and before any output. Source/guest
        // chronology is necessary, but the later class-marker bytes still
        // cannot satisfy the C checksum's complete I/O contract.
        let early_io = joined
            .guest_pointer()
            .trace()
            .iter()
            .take(joined.guest_pointer().transfer_step())
            .filter(|step| step.input.is_some() || step.output.is_some())
            .count();
        assert_eq!(early_io, 1, "real pre-transfer guest I/O cut");
        // A correct input-dependent arm does not justify the physical class
        // marker as the checksum's source ByteOutput. Require both effects
        // on a *single* source return path to expose that real C gap.
        assert_eq!(
            pointer_verifier
                .verify_source_return_branch_io_ordered(
                    &requested,
                    source_first_guard,
                )
                .map(|_proof| ()),
            if input.len() <= 1 {
                Err(BoundError::SourceInput(
                    SourceInputTraceError::SourceOutputNotProven,
                ))
            } else {
                Err(BoundError::SourceInput(
                    SourceInputTraceError::UnreachedSourceInput,
                ))
            },
            "class markers are not the C23 checksum for {input:?}",
        );
        if input.len() == 1 {
            assert_eq!(joined.source_input().observations[1].trace_index, 171);
        }
        // An input/branch proof cannot borrow an unplaced marker output
        // as a source-identical checksum effect. The new strict option
        // independently checks each reached guest output opcode address.
        assert_eq!(
            pointer_verifier
                .verify_source_return_branch_io_effect_anchored(
                    &requested,
                    source_first_guard,
                    &[],
                )
                .map(|_proof| ()),
            Err(BoundError::SourceInput(
                SourceInputTraceError::UnexpectedGuestOutput,
            )),
            "real N15 marker output has no source effect anchor for {input:?}",
        );
        if input.is_empty() {
            let (block, ordinal) = checksum_source_output_identity(&wire)?;
            // Naming the physical C128 marker as the checksum ByteOutput
            // cannot place it inside the source block's bounded interval.
            // A forged identity is refused before it can authenticate bytes.
            let forged = [GuestCodeEffectAnchor {
                block,
                code_address: 128,
                effect_index: 0,
                function: 0,
                ordinal,
            }];
            assert_eq!(
                pointer_verifier
                    .verify_source_return_branch_io_effect_anchored(
                        &requested,
                        source_first_guard,
                        &forged,
                    )
                    .map(|_proof| ()),
                Err(BoundError::SourceInput(
                    SourceInputTraceError::InvalidSourcePlacement,
                )),
                "the real C128 marker is outside its claimed source output",
            );
        }
        // The second C23 getchar is a real input on non-EOF paths, but
        // cannot be borrowed as an ancestor of this earlier pointer.
        for origins in [&[][..], &[first_getchar[0], first_getchar[0]][..]] {
            assert_eq!(
                pointer_verifier.verify_source_bound(
                    &SourceBoundIndirectGuestProbe { origins, ..requested }
                ),
                Err(BoundError::InvalidOriginSelection),
            );
        }
        assert_eq!(
            pointer_verifier.verify_source_bound(
                &SourceBoundIndirectGuestProbe {
                    origins: &second_getchar,
                    ..requested
                }
            ),
            if input.is_empty() {
                Err(BoundError::MissingSourceInputOrigin)
            } else {
                Err(BoundError::GuestPointer(
                    PointerError::MissingRequiredInputProvenance,
                ))
            },
        );
        if input == [0] {
            assert_eq!(
                pointer_verifier.verify_source_bound(
                    &SourceBoundIndirectGuestProbe {
                        allowed_landings: &[126],
                        ..requested
                    }
                ),
                Err(BoundError::GuestPointer(PointerError::UnexpectedLanding)),
            );
            // The actual byte arm C45 is allowed in isolation, but a
            // source-branch binding must reserve *both* stated physical
            // successors. A missing EOF-arm C126 cannot be tacitly accepted.
            let one_arm_only = SourceBoundIndirectGuestProbe {
                allowed_landings: &[45],
                ..requested
            };
            assert_eq!(
                pointer_verifier
                    .verify_source_return_bound(&one_arm_only)
                    .map_err(|error| format!("{error:?}"))?,
                joined,
            );
            assert_eq!(
                pointer_verifier.verify_source_return_branch_bound(
                    &one_arm_only,
                    source_first_guard,
                ),
                Err(BoundError::SourceInput(
                    SourceInputTraceError::InvalidBranchBinding,
                )),
            );
            let wrong_anchors = [
                GuestCodeOperationAnchor {
                    code_address: 52,
                    ..operation_anchors[0]
                },
                operation_anchors[1],
            ];
            assert_eq!(
                pointer_verifier.verify_source_bound(
                    &SourceBoundIndirectGuestProbe {
                        operation_anchors: &wrong_anchors,
                        ..requested
                    }
                ),
                Err(BoundError::SourceInput(
                    SourceInputTraceError::InvalidSourcePlacement,
                )),
            );
            let changed_source = &physical[1..];
            assert_eq!(
                pointer_verifier.verify_source_bound(
                    &SourceBoundIndirectGuestProbe {
                        source_input: SourceInputProbe {
                            physical_source: changed_source,
                            ..source_input
                        },
                        ..requested
                    }
                ),
                Err(BoundError::SourceMismatch),
            );
        }
    }
    // Reached signed reads alone do not implement the source checksum.
    // The unchanged physical helper emits a class marker, not the source
    // checksum byte, and one branch outputs before the final EOF read.
    for input in [&[][..], &[0][..], &[255][..]] {
        assert_eq!(
            SourceInputProbe {
                anchors: &read_sites,
                canonical: &wire,
                frame_base: 256,
                input,
                physical_source: &physical,
                step_budget: 175,
            }
            .verify_output_with_operation_anchors(
                proposals,
                &operation_anchors,
            ),
            Err(SourceInputTraceError::UnexpectedGuestOutput),
        );
    }
    assert_eq!(
        SourceInputProbe {
            anchors: &read_sites,
            canonical: &wire,
            frame_base: 256,
            input: &[255, 0, 44],
            physical_source: &physical,
            step_budget: 175,
        }
        .verify_output_with_operation_anchors(proposals, &operation_anchors),
        Err(SourceInputTraceError::UnexpectedGuestOutput),
        "unsourced guest output refuses before checking the missing loop input",
    );
    // The 132-cell guest reads real bytes, but it does not write the
    // source-C32 signed result into both authenticated SSA frame words.
    // Passing the input-placement and source-return gates is insufficient.
    for input in [&[][..], &[0][..], &[255][..]] {
        assert_eq!(
            SourceInputProbe {
                anchors: &read_sites,
                canonical: &wire,
                frame_base: 256,
                input,
                physical_source: &physical,
                step_budget: 175,
            }
            .verify_stored_with_operation_anchors(
                proposals,
                &operation_anchors,
            ),
            Err(SourceInputTraceError::MissingInputResultStore),
        );
    }
    let changed = [
        GuestCodeInputAnchor {
            code_address: 52,
            ..read_sites[0]
        },
        read_sites[1],
    ];
    assert_eq!(
        SourceInputProbe {
            anchors: &changed,
            canonical: &wire,
            frame_base: 256,
            input: &[0],
            physical_source: &physical,
            step_budget: 175,
        }
        .verify_with_operation_anchors(proposals, &operation_anchors),
        Err(SourceInputTraceError::InvalidSourcePlacement),
    );
    Ok(())
}

// One source-typed byte trace has two real inputs and one source-located
// output. This checks physical effect-site provenance, *not* the missing
// source SSA stores or a compiled C function.
fn two_input_byte_output_wire() -> Result<Vec<u8>, String> {
    use super::super::typed_cfg_adapter::typed::{
        BasicBlock, BasicBlockSpec, BlockId, Function, FunctionId,
        FunctionSpec, Instruction, LocatedInstruction, Module, ModuleSpec,
        SourcePosition, SourceSpan, Terminator, TypeDef, TypeEntry, TypeId,
        ValueId, canonical_bytes, validate_module,
    };
    let span = |start: u32, end: u32| {
        SourceSpan::new(
            SourcePosition::new(start, 1, start + 1),
            SourcePosition::new(end, 1, end + 1),
        )
    };
    let byte_type = TypeId::new(0);
    let module = Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version:
            super::super::typed_cfg_adapter::typed::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions: vec![
                    LocatedInstruction::new(
                        Instruction::ByteInput {
                            result: ValueId::new(0),
                            type_id: byte_type,
                        },
                        span(0, 1),
                    ),
                    LocatedInstruction::new(
                        Instruction::ByteInput {
                            result: ValueId::new(1),
                            type_id: byte_type,
                        },
                        span(1, 2),
                    ),
                    LocatedInstruction::new(
                        Instruction::ByteOutput { value: ValueId::new(1) },
                        span(2, 3),
                    ),
                ],
                phis: Vec::new(),
                span: span(0, 4),
                terminator: Terminator::Return { value: None },
                terminator_span: span(3, 4),
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("two_input_byte_output"),
            parameters: Vec::new(),
            signature: TypeId::new(1),
            span: span(0, 4),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/two-input-byte-output.c"),
        source_sha256: [0x45; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(byte_type, TypeDef::U8),
            TypeEntry::new(
                TypeId::new(1),
                TypeDef::function(Vec::new(), None, false),
            ),
        ],
    });
    validate_module(&module).map_err(|error| format!("typed: {error:?}"))?;
    canonical_bytes(&module).map_err(|error| format!("canonical: {error:?}"))
}

// One canonical typed U8 input optionally followed by its byte output.
// Its source-placed effects can be verified against genuine N15 operations
// rather than only necessary minimum code reservations.
fn single_byte_input_wire() -> Result<Vec<u8>, String> {
    single_byte_program_wire(false)
}

fn single_byte_input_output_wire() -> Result<Vec<u8>, String> {
    single_byte_program_wire(true)
}

fn single_byte_program_wire(with_output: bool) -> Result<Vec<u8>, String> {
    single_byte_program_with_outputs(usize::from(with_output))
}

fn single_byte_program_with_outputs(outputs: usize) -> Result<Vec<u8>, String> {
    single_byte_program_with_output_source(outputs, false)
}

fn single_byte_constant_output_wire() -> Result<Vec<u8>, String> {
    single_byte_program_with_output_source(1, true)
}

fn single_byte_program_with_output_source(
    outputs: usize,
    constant_output: bool,
) -> Result<Vec<u8>, String> {
    use super::super::typed_cfg_adapter::typed::{
        BasicBlock, BasicBlockSpec, BlockId, Function, FunctionId,
        FunctionSpec, Instruction, IntegerConstant, LocatedInstruction, Module,
        ModuleSpec, SourcePosition, SourceSpan, Terminator, TypeDef, TypeEntry,
        TypeId, ValueId, canonical_bytes, validate_module,
    };
    let span = SourceSpan::new(
        SourcePosition::new(0, 1, 1),
        SourcePosition::new(1, 1, 2),
    );
    let byte_type = TypeId::new(0);
    let mut instructions = vec![LocatedInstruction::new(
        Instruction::ByteInput {
            result: ValueId::new(0),
            type_id: byte_type,
        },
        span,
    )];
    if constant_output {
        instructions.push(LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(8, vec![37]),
                result: ValueId::new(1),
                type_id: byte_type,
            },
            span,
        ));
    }
    for _ in 0..outputs {
        instructions.push(LocatedInstruction::new(
            Instruction::ByteOutput {
                value: ValueId::new(u32::from(constant_output)),
            },
            span,
        ));
    }
    let module = Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version:
            super::super::typed_cfg_adapter::typed::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![BasicBlock::new(BasicBlockSpec {
                id: BlockId::new(0),
                instructions,
                phis: Vec::new(),
                span,
                terminator: Terminator::Return { value: None },
                terminator_span: span,
            })],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from(match (outputs, constant_output) {
                (1, true) => "single_byte_constant_output",
                (0, false) => "single_byte_input",
                (1, false) => "single_byte_input_output",
                _ => "single_byte_input_two_outputs",
            }),
            parameters: Vec::new(),
            signature: TypeId::new(1),
            span,
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from(match (outputs, constant_output) {
            (1, true) => "fixtures/single-byte-constant-output.c",
            (0, false) => "fixtures/single-byte-input.c",
            (1, false) => "fixtures/single-byte-input-output.c",
            _ => "fixtures/single-byte-input-two-outputs.c",
        }),
        source_sha256: match (outputs, constant_output) {
            (1, true) => [0x56; 32],
            (0, false) => [0x53; 32],
            (1, false) => [0x54; 32],
            _ => [0x55; 32],
        },
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(byte_type, TypeDef::U8),
            TypeEntry::new(
                TypeId::new(1),
                TypeDef::function(Vec::new(), None, false),
            ),
        ],
    });
    validate_module(&module).map_err(|error| format!("typed: {error:?}"))?;
    canonical_bytes(&module).map_err(|error| format!("canonical: {error:?}"))
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "identical output bytes must not erase source operation identity"
)]
fn identical_source_outputs_refuse_reversed_physical_effect_identity()
-> Result<(), String> {
    let wire = single_byte_program_with_outputs(2)?;
    let cfg = lower_canonical_dynamic_cfg(&wire)
        .map_err(|error| format!("typed CFG: {error:?}"))?;
    let function = cfg.functions.first().ok_or("missing source function")?;
    let observation = SourceInputSiteObservation {
        block: 0,
        code_address: 13,
        destination: GuestPlacedOperand {
            address: 73,
            type_kind: TernaryCfgScalarKind::U8,
            value: 0,
            words: 1,
        },
        function: 0,
        input: TraceInput::Byte(37),
        ordinal: 0,
        raw_accumulator: 37,
        semantics: GuestCodeInputSemantics::ByteU8,
        trace_index: 13,
    };
    let input = SourceInputIoEvent::Input { observation_index: 0 };
    let first = SourceOutputSiteObservation {
        block: 0,
        byte: 37,
        code_address: 24,
        function: 0,
        ordinal: 1,
        trace_index: 24,
    };
    let second = SourceOutputSiteObservation {
        block: 0,
        byte: 37,
        code_address: 26,
        function: 0,
        ordinal: 2,
        trace_index: 26,
    };
    assert_eq!(
        source_path_matches_input_walk(
            function,
            &[&observation],
            128,
            true,
            Some(&[37, 37]),
            Some(&[
                input,
                SourceInputIoEvent::Output(37),
                SourceInputIoEvent::Output(37)
            ]),
            Some(&[first, second]),
        ),
        Ok(true),
    );
    assert_eq!(
        source_path_matches_input_walk(
            function,
            &[&observation],
            128,
            true,
            Some(&[37, 37]),
            Some(&[
                input,
                SourceInputIoEvent::Output(37),
                SourceInputIoEvent::Output(37)
            ]),
            Some(&[second, first]),
        ),
        Ok(false),
        "two identical output bytes cannot swap source effect identities",
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source-placed two-output normative guest trace"
)]
fn actual_guest_two_identical_outputs_keep_distinct_source_effects()
-> Result<(), String> {
    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeInputAnchor,
        GuestCodeOperationAnchor, GuestCodeProposals,
    };
    use super::SourceInputProbe;

    let mut physical =
        b"DCBA@?>=<;:98hx/v-210/p-K+*)ji&%$#\"!~}|{zyxwvutsrqponmlkjihgs%H"
            .to_vec();
    let output_code = (33..=126u8)
        .find(|byte| {
            malbolge::decode_profile_instruction(u32::from(*byte), 26)
                == Some(b'<')
        })
        .ok_or("no graphical second output")?;
    *physical.get_mut(26).ok_or("missing second output cell")? = output_code;
    let wire = single_byte_program_with_outputs(2)?;
    let blocks = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 61,
        control_start: 60,
    }];
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &[],
    };
    let operations = [
        GuestCodeOperationAnchor {
            function: 0,
            block: 0,
            ordinal: 0,
            code_address: 13,
        },
        GuestCodeOperationAnchor {
            function: 0,
            block: 0,
            ordinal: 1,
            code_address: 24,
        },
        GuestCodeOperationAnchor {
            function: 0,
            block: 0,
            ordinal: 2,
            code_address: 26,
        },
    ];
    let inputs = [GuestCodeInputAnchor {
        function: 0,
        block: 0,
        ordinal: 0,
        code_address: 13,
    }];
    for stream in [&[0u8][..], &[37, 99][..], &[255][..]] {
        let probe = SourceInputProbe {
            anchors: &inputs,
            canonical: &wire,
            frame_base: 73,
            input: stream,
            physical_source: &physical,
            step_budget: 61,
        };
        let proof = probe
            .verify_output_with_operation_anchors(proposals, &operations)
            .map_err(|error| {
                format!("two-output guest {stream:?}: {error:?}")
            })?;
        assert_eq!(proof.bytes_consumed, 1);
        assert_eq!(proof.guest_output, [stream[0], stream[0]]);
        assert_eq!(proof.output_sites.len(), 2);
        assert_eq!(proof.output_sites[0].code_address, 24);
        assert_eq!(proof.output_sites[0].ordinal, 1);
        assert_eq!(proof.output_sites[1].code_address, 26);
        assert_eq!(proof.output_sites[1].ordinal, 2);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real byte-exact N15 guest and source-locked store-site refusals"
)]
fn actual_guest_byte_store_requires_its_source_effect_address()
-> Result<(), String> {
    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeEffectAnchor, GuestCodeInputAnchor,
        GuestCodeOperationAnchor, GuestCodeProposals,
    };
    use super::{SourceInputProbe, SourceInputTraceError};

    // Pinned source bytes are independently decoded and proven in the
    // byte-exact guest test; avoid regenerating the bounded search here.
    let physical = b"DCBA@?>n~5|3Ex6";
    assert_eq!(
        malbolge::decode_profile_instruction(u32::from(physical[7]), 7),
        Some(b'/'),
    );
    assert_eq!(
        malbolge::decode_profile_instruction(u32::from(physical[11]), 11),
        Some(b'p'),
    );
    let wire = single_byte_input_wire()?;
    let blocks = [GuestCodeBlockPlacement {
        block: 0,
        control_start: 12,
        end_exclusive: 13,
        function: 0,
        start: 0,
    }];
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &[],
    };
    let operations = [GuestCodeOperationAnchor {
        block: 0,
        code_address: 7,
        function: 0,
        ordinal: 0,
    }];
    let effects = [GuestCodeEffectAnchor {
        block: 0,
        code_address: 11,
        effect_index: 1,
        function: 0,
        ordinal: 0,
    }];
    let inputs = [GuestCodeInputAnchor {
        block: 0,
        code_address: 7,
        function: 0,
        ordinal: 0,
    }];
    for stream in [&[0][..], &[255, 99][..]] {
        let probe = SourceInputProbe {
            anchors: &inputs,
            canonical: &wire,
            frame_base: 55,
            input: stream,
            physical_source: physical,
            step_budget: 13,
        };
        let proof = probe
            .verify_stored_with_effect_anchors(proposals, &operations, &effects)
            .map_err(|error| format!("source store {stream:?}: {error:?}"))?;
        assert_eq!(proof.prefix.bytes_consumed, 1);
        assert!(proof.prefix.guest_output.is_empty());
        assert_eq!(proof.stores.len(), 1);
        assert_eq!(proof.stores[0].cells.len(), 1);
        assert_eq!(
            (
                proof.stores[0].cells[0].code_address,
                proof.stores[0].cells[0].address,
                proof.stores[0].cells[0].trace_index,
                proof.stores[0].cells[0].value,
            ),
            (11, 55, 11, u32::from(stream[0])),
        );
    }
    let probe = SourceInputProbe {
        anchors: &inputs,
        canonical: &wire,
        frame_base: 55,
        input: &[42, 99],
        physical_source: physical,
        step_budget: 13,
    };
    // Matching stored bytes, dependencies and return are insufficient
    // if the only source-identified store code site is C10, not C11.
    let wrong_site = [GuestCodeEffectAnchor {
        code_address: 10,
        ..effects[0]
    }];
    assert!(
        probe
            .verify_return_with_effect_anchors(
                proposals,
                &operations,
                &wrong_site,
            )
            .is_ok()
    );
    assert_eq!(
        probe.verify_stored_with_effect_anchors(
            proposals,
            &operations,
            &wrong_site,
        ),
        Err(SourceInputTraceError::UnexpectedGuestStoreSite),
    );
    // Without a sparse store anchor, an adjacent C8 proposal also
    // cannot authenticate the genuine C11 word write.
    assert_eq!(
        probe.verify_stored_with_effect_anchors(proposals, &operations, &[],),
        Err(SourceInputTraceError::UnexpectedGuestStoreSite),
    );
    let probe = SourceInputProbe {
        anchors: &inputs,
        canonical: &wire,
        frame_base: 55,
        input: &[],
        physical_source: physical,
        step_budget: 13,
    };
    assert_eq!(
        probe.verify_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        ),
        Err(SourceInputTraceError::SourceInputUnreachable),
        "unsigned-byte source paths cannot read true EOF",
    );
    Ok(())
}

// A matching physical byte is not a physical SSA operand. This guest stores
// the input in M73 and emits byte 37, but the authenticated source asks it to
// output a *different*, constant-37 SSA value at M74. Nothing wrote M74.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source operand not materialized in a real N15 guest"
)]
fn source_output_requires_a_prior_physical_write_to_its_own_ssa_cell()
-> Result<(), String> {
    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeEffectAnchor, GuestCodeInputAnchor,
        GuestCodeOperationAnchor, GuestCodeProposals,
    };
    use super::{SourceInputProbe, SourceInputTraceError};

    let wire = single_byte_constant_output_wire()?;
    let blocks = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 61,
        control_start: 60,
    }];
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &[],
    };
    let operations = [
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 13,
            function: 0,
            ordinal: 0,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 18,
            function: 0,
            ordinal: 1,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 24,
            function: 0,
            ordinal: 2,
        },
    ];
    let effects = [GuestCodeEffectAnchor {
        block: 0,
        code_address: 17,
        effect_index: 1,
        function: 0,
        ordinal: 0,
    }];
    let inputs = [GuestCodeInputAnchor {
        block: 0,
        code_address: 13,
        function: 0,
        ordinal: 0,
    }];
    let probe = SourceInputProbe {
        anchors: &inputs,
        canonical: &wire,
        frame_base: 73,
        input: &[37],
        physical_source: BYTE_INPUT_STORE_OUTPUT_PHYSICAL,
        step_budget: 61,
    };
    // A source-known constant of 37 makes the raw I/O path acceptable.
    let output = probe
        .verify_output_with_operation_anchors(proposals, &operations)
        .map_err(|error| format!("raw output gate: {error:?}"))?;
    assert_eq!(output.guest_output, [37]);
    assert_eq!(output.output_sites[0].ordinal, 2);
    // The store-only API intentionally does not promise source output
    // operand materialization; it authenticates the genuine input store.
    let stored = probe
        .verify_stored_with_effect_anchors(proposals, &operations, &effects)
        .map_err(|error| format!("store-only gate: {error:?}"))?;
    assert_eq!(stored.stores[0].cells[0].value, 37);
    assert_eq!(
        probe.verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        ),
        Err(SourceInputTraceError::SourceOutputNotProven),
        "the output operand M74 must be written before C24",
    );
    Ok(())
}

// A single independent real-stream witness keeps the new all-frame store
// path testable without rerunning the full multi-vector negative matrix.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "one real source I/O witness"
)]
fn source_combined_frame_write_gate_accepts_one_real_guest_stream()
-> Result<(), String> {
    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeEffectAnchor, GuestCodeInputAnchor,
        GuestCodeOperationAnchor, GuestCodeProposals,
    };
    use super::SourceInputProbe;

    let wire = single_byte_input_output_wire()?;
    let blocks = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 61,
        control_start: 60,
    }];
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &[],
    };
    let operations = [
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 13,
            function: 0,
            ordinal: 0,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 24,
            function: 0,
            ordinal: 1,
        },
    ];
    let effects = [GuestCodeEffectAnchor {
        block: 0,
        code_address: 17,
        effect_index: 1,
        function: 0,
        ordinal: 0,
    }];
    let inputs = [GuestCodeInputAnchor {
        block: 0,
        code_address: 13,
        function: 0,
        ordinal: 0,
    }];
    let probe = SourceInputProbe {
        anchors: &inputs,
        canonical: &wire,
        frame_base: 73,
        input: &[37],
        physical_source: BYTE_INPUT_STORE_OUTPUT_PHYSICAL,
        step_budget: 61,
    };
    let proof = probe
        .verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        )
        .map_err(|error| {
            format!("real source frame verification: {error:?}")
        })?;
    assert_eq!(proof.prefix.bytes_consumed, 1);
    assert_eq!(proof.prefix.guest_output, [37]);
    assert_eq!(proof.stores.len(), 1);
    assert_eq!(proof.frame_writes.len(), 1);
    let store = proof.frame_writes.first().ok_or("no physical store")?;
    assert_eq!(
        (store.code_address, store.address, store.value),
        (17, 73, 37)
    );
    Ok(())
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::panic_in_result_fn,
    clippy::too_many_lines,
    reason = "one physical guest and two negative placement cases"
)]
fn real_guest_byte_store_and_source_output_require_both_effect_sites()
-> Result<(), String> {
    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeEffectAnchor, GuestCodeInputAnchor,
        GuestCodeOperationAnchor, GuestCodeProposals,
    };
    use super::{SourceInputProbe, SourceInputTraceError};

    // Frozen source-loaded N15 guest derived from the independent
    // byte-exact two-read/reentry generator, with C25/C26 replaced by
    // graphical no-ops. These suppress the helper's extra read/output.
    // The original C13 input, C17 exact p store at M73 and C24 echo remain.
    let physical = BYTE_INPUT_STORE_OUTPUT_PHYSICAL;
    let wire = single_byte_input_output_wire()?;
    let blocks = [GuestCodeBlockPlacement {
        function: 0,
        block: 0,
        start: 0,
        end_exclusive: 61,
        control_start: 60,
    }];
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &[],
    };
    let operations = [
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 13,
            function: 0,
            ordinal: 0,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 24,
            function: 0,
            ordinal: 1,
        },
    ];
    let effects = [GuestCodeEffectAnchor {
        block: 0,
        code_address: 17,
        effect_index: 1,
        function: 0,
        ordinal: 0,
    }];
    let inputs = [GuestCodeInputAnchor {
        block: 0,
        code_address: 13,
        function: 0,
        ordinal: 0,
    }];
    for stream in [&[0u8][..], &[255, 19][..], &[73, 255][..]] {
        let probe = SourceInputProbe {
            anchors: &inputs,
            canonical: &wire,
            frame_base: 73,
            input: stream,
            physical_source: physical,
            step_budget: 61,
        };
        let proof = probe
            .verify_output_and_stored_with_effect_anchors(
                proposals,
                &operations,
                &effects,
            )
            .map_err(|error| format!("physical byte {stream:?}: {error:?}"))?;
        let first_byte = *stream.first().ok_or("missing first input byte")?;
        let cell = proof
            .stores
            .first()
            .and_then(|store| store.cells.first())
            .ok_or("missing verified guest result word")?;
        assert_eq!(proof.prefix.bytes_consumed, 1, "one physical read");
        assert_eq!(proof.prefix.guest_output, [first_byte], "guest echo");
        assert_eq!(cell.code_address, 17, "reached source store opcode");
        assert_eq!(cell.address, 73, "source result word");
        assert_eq!(cell.value, u32::from(first_byte), "guest input word");
        assert_eq!(proof.frame_writes, [*cell], "no extra frame writes");
    }
    let probe = SourceInputProbe {
        anchors: &inputs,
        canonical: &wire,
        frame_base: 73,
        input: &[37],
        physical_source: physical,
        step_budget: 61,
    };
    assert_eq!(
        probe.verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &[GuestCodeEffectAnchor {
                code_address: 16,
                ..effects[0]
            }],
        ),
        Err(SourceInputTraceError::UnexpectedGuestStoreSite),
    );
    // Source-compatible byte output and even genuine input-dependent
    // frame storage are insufficient if the reached < instruction has
    // moved away from the authenticated ByteOutput operation at C24.
    let mut shifted = physical.to_vec();
    for (address, opcode) in [(23usize, b'<'), (24, b'o')] {
        let encoded = (33..=126u8)
            .find(|byte| {
                malbolge::decode_profile_instruction(
                    u32::from(*byte),
                    u32::try_from(address).unwrap_or(u32::MAX),
                ) == Some(opcode)
            })
            .ok_or("graphical output shift missing")?;
        *shifted.get_mut(address).ok_or("output address absent")? = encoded;
    }
    let shifted_probe = SourceInputProbe {
        physical_source: &shifted,
        ..probe
    };
    let shifted_store = shifted_probe
        .verify_stored_with_effect_anchors(proposals, &operations, &effects)
        .map_err(|error| format!("shifted output kept store: {error:?}"))?;
    assert_eq!(
        shifted_store
            .stores
            .first()
            .and_then(|store| store.cells.first())
            .map(|cell| cell.value),
        Some(37),
        "wrong output site must not invalidate real input storage",
    );
    assert_eq!(
        shifted_probe.verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        ),
        Err(SourceInputTraceError::UnexpectedGuestOutput),
    );
    // A physically stored result cannot excuse an omitted source output.
    // C24 becomes an inert no-op; nothing else about the input or store
    // provenance changes.
    let mut silent = physical.to_vec();
    let no_output = (33..=126u8)
        .find(|byte| {
            malbolge::decode_profile_instruction(u32::from(*byte), 24)
                == Some(b'o')
        })
        .ok_or("graphical silent instruction missing")?;
    *silent.get_mut(24).ok_or("source output cell absent")? = no_output;
    let silent_probe = SourceInputProbe {
        physical_source: &silent,
        ..probe
    };
    assert_eq!(
        silent_probe.verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        ),
        Err(SourceInputTraceError::SourceOutputNotProven),
    );
    // An unsigned source input does not reinterpret a real guest EOF
    // sentinel as a successful byte even when the physical p path halts.
    let eof_probe = SourceInputProbe { input: &[], ..probe };
    assert_eq!(
        eof_probe.verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        ),
        Err(SourceInputTraceError::SourceInputUnreachable),
    );

    // After the authentic C17 store and C24 output, C29 has D=M73
    // again. Replacing its j with * performs a second *real* store
    // of zero to M73 on NUL. This idempotent mutation leaves the
    // source-compatible input, output, final memory and halt intact,
    // but it is not the source-anchored C17 store.
    let mut rogue = physical.to_vec();
    let extra_rotate = (33..=126u8)
        .find(|byte| {
            malbolge::decode_profile_instruction(u32::from(*byte), 29)
                == Some(b'*')
        })
        .ok_or("graphical rogue rotation missing")?;
    *rogue.get_mut(29).ok_or("rogue code cell absent")? = extra_rotate;
    let rogue_probe = SourceInputProbe {
        input: &[0],
        physical_source: &rogue,
        ..probe
    };
    assert!(
        rogue_probe
            .verify_output_with_operation_anchors(proposals, &operations)
            .is_ok(),
        "raw NUL output and source return still agree",
    );
    assert_eq!(
        rogue_probe.verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        ),
        Err(SourceInputTraceError::UnexpectedGuestStoreSite),
        "all frame mutations, not just the correct C17 store, need anchors",
    );
    let changed_probe = SourceInputProbe {
        input: &[37],
        ..rogue_probe
    };
    assert_eq!(
        changed_probe.verify_output_and_stored_with_effect_anchors(
            proposals,
            &operations,
            &effects,
        ),
        Err(SourceInputTraceError::InputResultMismatch),
        "non-idempotent late mutation also corrupts the live source result",
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source-locked sparse guest effect placement refusals"
)]
fn sparse_input_effect_anchors_allow_real_setup_gaps_but_not_reordering()
-> Result<(), String> {
    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeEffectAnchor,
        GuestCodeOperationAnchor, GuestCodeOperationEffect,
        GuestCodePlacementError, GuestCodeProposals,
        bind_source_locked_cfg_code_targets_with_effect_anchors,
    };

    let wire = two_input_byte_output_wire()?;
    let blocks = [GuestCodeBlockPlacement {
        block: 0,
        control_start: 15,
        end_exclusive: 16,
        function: 0,
        start: 0,
    }];
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &[],
    };
    let operations = [
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 0,
            function: 0,
            ordinal: 0,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 7,
            function: 0,
            ordinal: 1,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 14,
            function: 0,
            ordinal: 2,
        },
    ];
    let stores = [
        GuestCodeEffectAnchor {
            block: 0,
            code_address: 5,
            effect_index: 1,
            function: 0,
            ordinal: 0,
        },
        GuestCodeEffectAnchor {
            block: 0,
            code_address: 12,
            effect_index: 1,
            function: 0,
            ordinal: 1,
        },
    ];
    let bind = |effects: &[GuestCodeEffectAnchor]| {
        bind_source_locked_cfg_code_targets_with_effect_anchors(
            &wire,
            16,
            256,
            proposals,
            &operations,
            effects,
        )
    };
    let plan = bind(&stores).map_err(|error| format!("layout: {error:?}"))?;
    assert_eq!(
        plan.operation_effect_sites
            .iter()
            .map(|site| (site.code_address, site.ordinal, site.effect))
            .collect::<Vec<_>>(),
        vec![
            (0, 0, plan.operation_effect_sites[0].effect),
            (5, 0, plan.operation_effect_sites[1].effect),
            (7, 1, plan.operation_effect_sites[2].effect),
            (12, 1, plan.operation_effect_sites[3].effect),
            (14, 2, plan.operation_effect_sites[4].effect),
        ],
    );
    assert!(matches!(
        plan.operation_effect_sites[1].effect,
        GuestCodeOperationEffect::Store { .. }
    ));
    assert!(matches!(
        plan.operation_effect_sites[3].effect,
        GuestCodeOperationEffect::Store { .. }
    ));
    assert_eq!(
        plan.operation_sites
            .iter()
            .map(|site| (site.start, site.end_exclusive))
            .collect::<Vec<_>>(),
        [(0, 6), (7, 13), (14, 15)],
    );
    let refusal = Err(GuestCodePlacementError::InvalidCodePlacement);
    for invalid in [
        vec![stores[0], stores[0]],
        vec![GuestCodeEffectAnchor {
            code_address: 0,
            ..stores[0]
        }],
        vec![GuestCodeEffectAnchor {
            code_address: 7,
            ..stores[0]
        }],
        vec![GuestCodeEffectAnchor {
            code_address: 15,
            ..stores[1]
        }],
        vec![GuestCodeEffectAnchor {
            effect_index: 2,
            ..stores[0]
        }],
        vec![GuestCodeEffectAnchor { ordinal: 99, ..stores[0] }],
        vec![GuestCodeEffectAnchor { block: 99, ..stores[0] }],
        vec![GuestCodeEffectAnchor {
            function: 99,
            ..stores[0]
        }],
    ] {
        assert_eq!(bind(&invalid), refusal);
    }
    // The old operation-only entrypoint keeps its adjacent effect layout.
    let ordinary = super::super::typed_cfg_adapter::state_relocation::
        bind_source_locked_cfg_code_targets_with_operation_anchors(
            &wire, 16, 256, proposals, &operations,
        ).map_err(|error| format!("adjacent layout: {error:?}"))?;
    assert_eq!(
        ordinary
            .operation_effect_sites
            .iter()
            .map(|site| site.code_address)
            .collect::<Vec<_>>(),
        [0, 1, 7, 8, 14],
    );
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real guest input and output provenance at exact typed addresses"
)]
fn explicit_output_anchors_require_reached_guest_output_site()
-> Result<(), String> {
    use malbolge::{current_profile, decode_profile_instruction};

    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeInputAnchor,
        GuestCodeOperationAnchor, GuestCodeProposals,
    };
    use super::SourceInputProbe;

    let wire = two_input_byte_output_wire()?;
    let encoded = |operations: &[u8]| -> Result<Vec<u8>, String> {
        operations
            .iter()
            .enumerate()
            .map(|(address, &opcode)| {
                (33u8..=126)
                    .find(|&byte| {
                        decode_profile_instruction(
                            u32::from(byte),
                            address as u32,
                        ) == Some(opcode)
                    })
                    .ok_or_else(|| {
                        format!("no graphical opcode {opcode} at {address}")
                    })
            })
            .collect()
    };
    let correct = encoded(b"/o/o<v")?;
    let mislocated = encoded(b"/o/<ov")?;
    let blocks = [GuestCodeBlockPlacement {
        block: 0,
        control_start: 5,
        end_exclusive: 6,
        function: 0,
        start: 0,
    }];
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &[],
    };
    let operation_anchors = [
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 0,
            function: 0,
            ordinal: 0,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 2,
            function: 0,
            ordinal: 1,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 4,
            function: 0,
            ordinal: 2,
        },
    ];
    let inputs = [
        GuestCodeInputAnchor {
            block: 0,
            code_address: 0,
            function: 0,
            ordinal: 0,
        },
        GuestCodeInputAnchor {
            block: 0,
            code_address: 2,
            function: 0,
            ordinal: 1,
        },
    ];
    for stream in [&[0, 0xff][..], &[0xff, 0][..], &[23, 42, 99][..]] {
        let expected = stream[1];
        let probe = SourceInputProbe {
            anchors: &inputs,
            canonical: &wire,
            frame_base: 256,
            input: stream,
            physical_source: &correct,
            step_budget: 6,
        };
        let proof = probe
            .verify_output_with_operation_anchors(proposals, &operation_anchors)
            .map_err(|error| {
                format!("source-placed guest output: {error:?}")
            })?;
        assert_eq!(proof.guest_output, [expected]);
        assert_eq!(proof.bytes_consumed, 2);
        assert_eq!(proof.io_events, [
            SourceInputIoEvent::Input { observation_index: 0 },
            SourceInputIoEvent::Input { observation_index: 1 },
            SourceInputIoEvent::Output(expected),
        ]);
        assert_eq!(proof.output_sites, [SourceOutputSiteObservation {
            block: 0,
            byte: expected,
            code_address: 4,
            function: 0,
            ordinal: 2,
            trace_index: 4,
        }]);
        let shifted = SourceInputProbe {
            physical_source: &mislocated,
            ..probe
        };
        assert_eq!(
            shifted
                .verify_with_operation_anchors(proposals, &operation_anchors)
                .map_err(|error| format!("raw I/O compatibility: {error:?}"))?
                .guest_output,
            [expected],
            "raw byte parity does not authenticate output sites",
        );
        assert_eq!(
            shifted.verify_output_with_operation_anchors(
                proposals,
                &operation_anchors
            ),
            Err(SourceInputTraceError::UnexpectedGuestOutput),
        );
    }
    // An EOF cannot masquerade as a successful byte-typed source input.
    assert_eq!(
        SourceInputProbe {
            anchors: &inputs,
            canonical: &wire,
            frame_base: 256,
            input: &[23],
            physical_source: &correct,
            step_budget: 6,
        }
        .verify_output_with_operation_anchors(proposals, &operation_anchors),
        Err(SourceInputTraceError::SourceInputUnreachable),
    );
    assert_eq!(current_profile().input_instruction(), b'/');
    Ok(())
}

// The strict source CFG checker must compose the existing input-result
// verifier. A real `/` at its source site is not enough: unsigned byte input
// has no source path for EOF, and the reached guest must authenticate the
// actual SSA store rather than accepting arbitrary rotated/crazy state.
#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "one pinned physical N15 guest and source-typed input replay"
)]
fn complete_cfg_strict_mode_checks_source_input_result_materialization()
-> Result<(), String> {
    use super::super::source_phi_copy_trace::{
        SourcePhiCopyProbe, SourcePhiCopyTraceError,
    };
    use super::super::typed_cfg_adapter::state_relocation::{
        GuestCodeBlockPlacement, GuestCodeEffectAnchor,
        GuestCodeOperationAnchor, GuestCodeProposals,
    };

    let physical = b"DCBA@?>n~5|3Ex6";
    let wire = single_byte_input_wire()?;
    let blocks = [GuestCodeBlockPlacement {
        block: 0,
        control_start: 12,
        end_exclusive: 13,
        function: 0,
        start: 0,
    }];
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &[],
    };
    let operations = [GuestCodeOperationAnchor {
        block: 0,
        code_address: 7,
        function: 0,
        ordinal: 0,
    }];
    let effects = [GuestCodeEffectAnchor {
        block: 0,
        code_address: 11,
        effect_index: 1,
        function: 0,
        ordinal: 0,
    }];
    for stream in [&[0u8][..], &[255u8, 10][..]] {
        let probe = SourcePhiCopyProbe {
            canonical: &wire,
            effect_anchors: &effects,
            frame_base: 55,
            input: stream,
            operation_anchors: &operations,
            physical_source: physical,
            proposals,
            step_budget: 13,
        };
        assert_eq!(
            probe.verify_with_source_computations(&[]),
            Ok(super::super::source_phi_copy_trace::SourcePhiCopyProof {
                completed_pads: 0,
                copies: vec![],
            }),
            "guest must materialize an actual source byte from {stream:?}"
        );
    }
    let at_eof = SourcePhiCopyProbe {
        canonical: &wire,
        effect_anchors: &effects,
        frame_base: 55,
        input: &[],
        operation_anchors: &operations,
        physical_source: physical,
        proposals,
        step_budget: 13,
    };
    assert_eq!(
        at_eof.verify_with_source_computations(&[]),
        Err(SourcePhiCopyTraceError::InvalidSourceInputResult(
            SourceInputTraceError::SourceInputUnreachable,
        )),
        "source ByteInput cannot silently store the raw EOF sentinel"
    );
    Ok(())
}
