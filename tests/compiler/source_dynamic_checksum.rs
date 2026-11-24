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
//   - Full source-authenticated EOF checksum's first dynamic typed-CFG witness.
// - Must-Not:
//   - Mistake typed CFG admission for verified guest program execution.
// - Allows:
//   - Inputs: pinned Clang JSON, original C and controlled forged nodes.
//   - Outputs: exact signed input, CFG, mutable-state and refusal assertions.
//   - Side effects: none.
// - Split-When:
//   - General C CFG translation validation subsumes the source witness.
// - Merge-When:
//   - The P2 complete mutable-checksum guest test can assert every stage.
// - Summary:
//   - Checks dynamic C meaning survives real typed SSA without guest output.
// - Description:
//   - Source and normalized AST must remain bound at every compiler stage.
// - Usage:
//   - Included by the JSON frontend's Rust unit test composition.
// - Defaults:
//   - Unlinked dynamic CFG never counts as published guest code.

//! Source-locked checksum CFG, staged guest state and refusal regression.

use serde_json::{Value, json};

use super::typed::{
    BinaryOp, CompareOp, Instruction, Terminator, canonical_module,
};
use super::typed_cfg_adapter::state_operations::{
    GuestOperationBinding, GuestOperationBlock,
};
use super::typed_cfg_adapter::state_relocation::{
    GuestPlacedBlock, GuestPlacedInstruction, GuestPlacedPhiEdge,
    GuestRelocatedCfgPlan,
};
use super::typed_cfg_adapter::state_storage::GuestCellEdge;
use super::{
    FrontendGuestMode, FrontendJsonError, canonical_guest_typed_ir_with_source,
};

const NORMALIZED: &[u8] =
    include_bytes!("c-frontend/golden/mutable_eof_checksum_current.json");
const SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/mutable_eof_checksum.c");

#[test]
fn frozen_eof_checksum_reaches_genuine_dynamic_typed_cfg() {
    let (wire, mode) =
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(SOURCE)).expect(
            "whole checksum should pass the normalized-to-typed boundary",
        );
    assert_eq!(mode, FrontendGuestMode::DynamicEofChecksum);
    let module = canonical_module(&wire).expect("typed checksum must re-admit");
    let [function] = module.functions() else {
        panic!("checksum must contain exactly one function");
    };
    let blocks = function.blocks();
    assert_eq!(blocks.len(), 7);
    assert!(matches!(blocks[0].terminator(), Terminator::Jump { .. }));
    assert_eq!(blocks[1].phis().len(), 2);
    assert!(matches!(blocks[1].terminator(), Terminator::Branch { .. }));
    assert!(matches!(blocks[2].terminator(), Terminator::Branch { .. }));
    assert_eq!(blocks[5].phis().len(), 1);
    let mut reads = 0;
    let mut writes = 0;
    let mut xors = 0;
    let mut adds = 0;
    let mut bitands = 0;
    let mut neq = 0;
    for block in blocks {
        for located in block.instructions() {
            match located.instruction() {
                Instruction::Getchar { .. } => reads += 1,
                Instruction::ByteOutput { .. } => writes += 1,
                Instruction::Binary {
                    operation: BinaryOp::Xor, ..
                } => xors += 1,
                Instruction::Binary {
                    operation: BinaryOp::Add, ..
                } => adds += 1,
                Instruction::Binary {
                    operation: BinaryOp::And, ..
                } => bitands += 1,
                Instruction::Compare {
                    operation: CompareOp::NotEqual,
                    ..
                } => neq += 1,
                _ => {},
            }
        }
    }
    assert_eq!(
        (reads, writes, xors, adds, bitands, neq),
        (2, 1, 1, 2, 2, 2)
    );
    // Both loop-carried values originate at entry or from the *same* backedge.
    for phi in blocks[1].phis() {
        assert_eq!(phi.incoming().len(), 2);
        assert_eq!(phi.incoming()[0].block().value(), 0);
        assert_eq!(phi.incoming()[1].block().value(), 5);
    }
}

#[test]
fn original_checksum_crosses_canonical_typed_to_symbolic_cfg_composition() {
    use super::typed_cfg_adapter::ternary::{
        TernaryCfgTerminator, TernaryOperation,
    };
    use super::typed_cfg_adapter::{
        TypedCfgAdapterError, lower_canonical_dynamic_cfg,
    };

    let (wire, mode) =
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(SOURCE))
            .expect("original C23 checksum must reach canonical typed IR");
    assert_eq!(mode, FrontendGuestMode::DynamicEofChecksum);
    let plan = lower_canonical_dynamic_cfg(&wire)
        .expect("validated source-backed canonical IR must lower directly");
    let [function] = plan.functions.as_slice() else {
        panic!("one source-authenticated checksum function");
    };
    assert_eq!(
        plan.source_sha256,
        *canonical_module(&wire).unwrap().source_sha256()
    );
    assert_eq!(plan.target_profile, "malbolge-2026");
    assert_eq!(function.blocks.len(), 7);
    assert_eq!(function.blocks[1].phis.len(), 2);
    assert_eq!(function.blocks[5].phis.len(), 1);
    assert!(matches!(
        function.blocks[5].terminator,
        TernaryCfgTerminator::Jump { target: 1, .. },
    ));
    let operations = function
        .blocks
        .iter()
        .flat_map(|block| &block.operations)
        .collect::<Vec<_>>();
    assert_eq!(
        operations
            .iter()
            .filter(|operation| matches!(
                operation,
                TernaryOperation::GetcharI32 { .. }
            ))
            .count(),
        2
    );
    assert_eq!(
        operations
            .iter()
            .filter(|operation| matches!(
                operation,
                TernaryOperation::ByteOutput { .. }
            ))
            .count(),
        1
    );
    assert_eq!(lower_canonical_dynamic_cfg(&wire), Ok(plan));

    let mut forged = wire.clone();
    forged[0] ^= 0xff;
    assert!(matches!(
        lower_canonical_dynamic_cfg(&forged),
        Err(TypedCfgAdapterError::InvalidTypedIr(_)),
    ));
    // An original-source mutation cannot borrow the canonical witness as
    // an authorization token for a different C translation unit.
    let mut changed = SOURCE.to_vec();
    let index = changed.windows(4).position(|word| word == b"255U").unwrap();
    changed[index] = b'1';
    assert_eq!(
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(&changed)),
        Err(FrontendJsonError::Unsupported),
    );
}

#[test]
fn original_checksum_phi_edges_are_unselected_parallel_guest_transfers() {
    use super::typed_cfg_adapter::prepare_canonical_dynamic_cfg;

    let (wire, mode) =
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(SOURCE))
            .expect("whole-source authenticated checksum");
    assert_eq!(mode, FrontendGuestMode::DynamicEofChecksum);
    let prelink = prepare_canonical_dynamic_cfg(&wire)
        .expect("all checksum phi edges must be independently validated");
    let edges = &prelink.phi_edges;
    let summary = edges
        .iter()
        .map(|edge| (edge.predecessor, edge.successor, edge.simultaneous.len()))
        .collect::<Vec<_>>();
    assert_eq!(summary, vec![(0, 1, 2), (3, 5, 1), (4, 5, 1), (5, 1, 2),]);
    assert_eq!(
        edges
            .iter()
            .map(|edge| edge.simultaneous.len())
            .sum::<usize>(),
        6
    );
    for edge in edges {
        assert_eq!(edge.function, 0);
        let destination = &prelink.cfg.functions[0].blocks
            [usize::try_from(edge.successor).unwrap()];
        assert_eq!(destination.id, edge.successor);
        assert_eq!(edge.simultaneous.len(), destination.phis.len());
        for (move_op, phi) in edge.simultaneous.iter().zip(&destination.phis) {
            assert_eq!(move_op.result, phi.result);
            assert_eq!(move_op.type_kind, phi.type_kind);
            assert_eq!(
                phi.incoming
                    .iter()
                    .find(|(predecessor, _)| *predecessor == edge.predecessor)
                    .map(|(_, value)| *value),
                Some(move_op.source)
            );
        }
    }
    assert_eq!(prepare_canonical_dynamic_cfg(&wire), Ok(prelink));
}

#[test]
fn original_c23_checksum_reproduces_frozen_dynamic_typed_wire() {
    // This fixture must be regenerated only from the source-checked pinned
    // Clang tree, never from a hand-authored approximation of the checksum.
    const FROZEN: &str =
        include_str!("typed-ir/golden/mutable-eof-checksum.hex");
    let (wire, mode) =
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(SOURCE))
            .expect("source-checked original checksum must reach typed IR");
    assert_eq!(mode, FrontendGuestMode::DynamicEofChecksum);
    let expected = FROZEN
        .trim_end_matches('\n')
        .strip_prefix("malbolge-typed-ir-v1:")
        .expect("frozen typed wire must declare its version");
    let actual = wire
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();
    assert_eq!(actual, expected, "source-bound typed wire snapshot drift");
}

#[test]
fn normalized_checksum_without_the_original_source_fails_closed() {
    assert_eq!(
        canonical_guest_typed_ir_with_source(NORMALIZED, None),
        Err(FrontendJsonError::Unsupported),
    );
    let mut changed = SOURCE.to_vec();
    let site = changed.windows(4).position(|s| s == b"255U").unwrap();
    changed[site] = b'1';
    assert_eq!(
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(&changed)),
        Err(FrontendJsonError::Unsupported),
    );
}

#[test]
fn forged_dynamic_checksum_nodes_refuse_before_backend() {
    let original: Value = serde_json::from_slice(NORMALIZED).unwrap();
    let edits: &[(usize, &str, Value)] = &[
        (11, "operation", json!("==")),
        (15, "operation", json!("+")),
        (21, "operation", json!("|")),
        (27, "operation", json!("+=")),
        (33, "operation", json!("^=")),
        (42, "operation", json!("-")),
        (49, "reference", json!("external:putchar")),
        (50, "operation", json!("lvalue-to-rvalue")),
        (52, "reference", json!("external:getchar")),
        (56, "type", json!("i32")),
        (3, "storage_duration", json!("static")),
        (17, "inline_specified", json!(true)),
    ];
    for (index, field, value) in edits {
        let mut forged = original.clone();
        forged["nodes"][*index][*field] = value.clone();
        let payload = serde_json::to_vec(&forged).unwrap();
        assert_eq!(
            canonical_guest_typed_ir_with_source(&payload, Some(SOURCE)),
            Err(FrontendJsonError::Unsupported),
            "forged node {} field {field} crossed typed admission",
            index + 1,
        );
    }
}

// This small test-only interpreter consumes the *admitted typed instructions*,
// not a second hardcoded checksum implementation. It cannot emit Malbolge or
// serve as evidence of actual guest execution. The independent source oracle
// below checks its observable EOF, mutable-state, and branch semantics.
fn execute_typed_checksum(wire: &[u8], stdin: &[u8]) -> (Vec<u8>, usize) {
    use std::collections::BTreeMap;

    use super::typed::{CastOp, ValueId};

    let module = canonical_module(wire).expect("admitted typed IR");
    let [function] = module.functions() else {
        panic!("one function")
    };
    let mut values = BTreeMap::<u32, u32>::new();
    let mut current_block = function.entry().value();
    let mut previous_block = None;
    let mut input_cursor = 0_usize;
    let mut output = Vec::new();
    let mut steps = 0_usize;
    let read = |values: &BTreeMap<u32, u32>, operand: &ValueId| -> u32 {
        values[&operand.value()]
    };
    loop {
        steps += 1;
        assert!(steps <= 100_000, "typed CFG step budget exhausted");
        let block = &function.blocks()[current_block as usize];
        // A phi edge takes its predecessor's value, *before* any result of
        // another phi in the same block overwrites a loop-carried location.
        let mut merges = Vec::new();
        for phi in block.phis() {
            let edge = phi
                .incoming()
                .iter()
                .find(|edge| Some(edge.block().value()) == previous_block)
                .expect("must take a reachable incoming edge");
            merges.push((phi.result().value(), read(&values, &edge.value())));
        }
        for (id, value) in merges {
            _ = values.insert(id, value);
        }
        for located in block.instructions() {
            match located.instruction() {
                Instruction::ConstantInteger { constant, result, .. } => {
                    let bits = constant
                        .little_endian()
                        .iter()
                        .enumerate()
                        .fold(0_u32, |acc, (byte, value)| {
                            acc | (u32::from(*value) << (byte * 8))
                        });
                    _ = values.insert(result.value(), bits);
                },
                Instruction::Getchar { result, .. } => {
                    let value = stdin
                        .get(input_cursor)
                        .map_or(u32::MAX, |b| u32::from(*b));
                    if input_cursor < stdin.len() {
                        input_cursor += 1;
                    }
                    _ = values.insert(result.value(), value);
                },
                Instruction::Binary {
                    left,
                    right,
                    result,
                    operation,
                    ..
                } => {
                    let a = read(&values, left);
                    let b = read(&values, right);
                    let computed = match operation {
                        BinaryOp::Add => a.wrapping_add(b),
                        BinaryOp::Xor => a ^ b,
                        BinaryOp::And => a & b,
                        other => panic!("unexpected arithmetic {other:?}"),
                    };
                    _ = values.insert(result.value(), computed);
                },
                Instruction::Compare {
                    left,
                    right,
                    result,
                    operation,
                    ..
                } => {
                    let computed = match operation {
                        CompareOp::NotEqual => u32::from(
                            read(&values, left) != read(&values, right),
                        ),
                        other => panic!("unexpected predicate {other:?}"),
                    };
                    _ = values.insert(result.value(), computed);
                },
                Instruction::Cast {
                    value, result, operation, ..
                } => {
                    let computed = match operation {
                        CastOp::IntegerBitcast => read(&values, value),
                        CastOp::Truncate => read(&values, value) & 255,
                        other => panic!("unexpected cast {other:?}"),
                    };
                    _ = values.insert(result.value(), computed);
                },
                Instruction::ByteOutput { value } => {
                    output.push(
                        u8::try_from(read(&values, value))
                            .expect("byte output"),
                    );
                },
                other => panic!("unexpected typed instruction {other:?}"),
            }
        }
        let next_block = match block.terminator() {
            Terminator::Jump { target } => target.value(),
            Terminator::Branch {
                condition,
                true_target,
                false_target,
            } => {
                if read(&values, condition) != 0 {
                    true_target.value()
                } else {
                    false_target.value()
                }
            },
            Terminator::Return { value: None } => {
                return (output, input_cursor);
            },
            other => panic!("unexpected terminator {other:?}"),
        };
        previous_block = Some(current_block);
        current_block = next_block;
    }
}

fn independent_c23_checksum(input: &[u8]) -> u8 {
    let mut checksum = 0_u32;
    for &byte in input {
        if byte & 1 != 0 {
            checksum ^= u32::from(byte);
        } else {
            checksum = checksum.wrapping_add(u32::from(byte));
        }
        checksum = checksum.wrapping_add(3) & 255;
    }
    checksum as u8
}

#[test]
fn source_checksum_typed_cfg_matches_five_c23_eof_binary_controls() {
    let (wire, mode) =
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(SOURCE))
            .expect("whole checksum typed projection");
    assert_eq!(mode, FrontendGuestMode::DynamicEofChecksum);
    let inputs: &[(&str, &[u8])] = &[
        ("empty", b""),
        ("nul", b"\0"),
        ("high", b"\xff"),
        ("mixed", b"\x01\x00\x80\xfe"),
        ("truncated", b"\x05\x00\x81"),
    ];
    for (name, input) in inputs {
        let (output, reads) = execute_typed_checksum(&wire, input);
        assert_eq!(output, [independent_c23_checksum(input)], "{name}");
        assert_eq!(reads, input.len(), "{name}: consumes through EOF");
    }
}

#[test]
fn original_checksum_state_frame_preserves_signed_eof_and_parallel_loop_phi() {
    use super::typed_cfg_adapter::prepare_canonical_dynamic_cfg;
    use super::typed_cfg_adapter::state_storage::{
        decode_i32_cells, encode_i32_cells,
    };

    let (wire, mode) =
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(SOURCE)).unwrap();
    assert_eq!(mode, FrontendGuestMode::DynamicEofChecksum);
    let prelink = prepare_canonical_dynamic_cfg(&wire).unwrap();
    let frame = &prelink.state_frames[0];
    assert_eq!(frame.values.len(), 21);
    assert_eq!(frame.scratch_offset, 39);
    assert_eq!(frame.scratch_words, 4);
    assert_eq!(frame.total_words, 43);
    assert_eq!(prelink.cell_edges.len(), 4);
    assert_eq!(frame.function, 0);
    assert!(frame.values.iter().any(|value| value.words == 2));
    assert!(frame.scratch_words >= 2);
    assert!(frame.total_words > frame.scratch_offset);
    for value in &frame.values {
        assert!(
            value.offset.checked_add(value.words).unwrap()
                <= frame.scratch_offset
        );
    }
    for bits in [0, 1, 255, 256, 0x8000_0000, 0xffff_ffff] {
        let cells = encode_i32_cells(bits);
        assert!(cells.iter().all(|value| *value < 14_348_907));
        assert_eq!(decode_i32_cells(cells), Some(bits));
    }
    assert_eq!(decode_i32_cells([0, 14_348_906]), None);
    let backedge = prelink
        .cell_edges
        .iter()
        .find(|edge| {
            edge.function == 0 && edge.predecessor == 5 && edge.successor == 1
        })
        .unwrap();
    // All sources are copied into a disjoint scratch region before the first
    // destination is overwritten, even when SSA values depend on each other.
    assert_eq!(backedge.snapshots.len(), 4);
    assert_eq!(backedge.commits.len(), 4);
    assert!(backedge.snapshots.iter().all(|item| {
        item.source < frame.scratch_offset
            && item.destination >= frame.scratch_offset
    }));
    assert!(backedge.commits.iter().all(|item| {
        item.source >= frame.scratch_offset
            && item.destination < frame.scratch_offset
    }));
    assert_eq!(prepare_canonical_dynamic_cfg(&wire), Ok(prelink));
}

#[test]
fn parallel_cell_copies_preserve_cross_swaps_without_host_branching() {
    use super::typed_cfg_adapter::state_storage::{
        GuestStateFrame, GuestStorageValue, plan_cell_edge,
    };
    use super::typed_cfg_adapter::ternary::TernaryCfgScalarKind;
    use super::typed_cfg_adapter::{PhiEdgeMove, PhiEdgeTransfers};

    let frame = GuestStateFrame {
        function: 0,
        values: vec![
            GuestStorageValue {
                value: 0,
                offset: 0,
                words: 2,
                type_kind: TernaryCfgScalarKind::I32,
            },
            GuestStorageValue {
                value: 1,
                offset: 2,
                words: 2,
                type_kind: TernaryCfgScalarKind::I32,
            },
        ],
        scratch_offset: 4,
        scratch_words: 4,
        total_words: 8,
    };
    let edge = PhiEdgeTransfers {
        function: 0,
        predecessor: 1,
        successor: 0,
        simultaneous: vec![
            PhiEdgeMove {
                result: 0,
                source: 1,
                type_kind: TernaryCfgScalarKind::I32,
            },
            PhiEdgeMove {
                result: 1,
                source: 0,
                type_kind: TernaryCfgScalarKind::I32,
            },
        ],
    };
    let scheduled = plan_cell_edge(&frame, &edge).unwrap();
    let mut bank = vec![12, 13, 21, 22, 0, 0, 0, 0];
    for copy in scheduled.snapshots.iter().chain(&scheduled.commits) {
        bank[copy.destination as usize] = bank[copy.source as usize];
    }
    assert_eq!(bank[..4], [21, 22, 12, 13]);
    assert_eq!(bank[4..], [21, 22, 12, 13]);
}

#[test]
fn guest_cell_copy_planner_rejects_forged_slots_and_phi_sources() {
    use super::typed_cfg_adapter::state_storage::{
        GuestStateFrame, GuestStorageValue, plan_cell_edge,
    };
    use super::typed_cfg_adapter::ternary::TernaryCfgScalarKind;
    use super::typed_cfg_adapter::{
        PhiEdgeMove, PhiEdgeTransfers, TypedCfgAdapterError,
    };

    let frame = GuestStateFrame {
        function: 3,
        values: vec![
            GuestStorageValue {
                value: 8,
                offset: 0,
                words: 2,
                type_kind: TernaryCfgScalarKind::I32,
            },
            GuestStorageValue {
                value: 9,
                offset: 2,
                words: 2,
                type_kind: TernaryCfgScalarKind::I32,
            },
        ],
        scratch_offset: 4,
        scratch_words: 2,
        total_words: 6,
    };
    let edge = PhiEdgeTransfers {
        function: 3,
        predecessor: 0,
        successor: 1,
        simultaneous: vec![PhiEdgeMove {
            result: 9,
            source: 8,
            type_kind: TernaryCfgScalarKind::I32,
        }],
    };
    assert!(plan_cell_edge(&frame, &edge).is_ok());
    let rejected = Err(TypedCfgAdapterError::GuestStateAllocation);
    let mut forged = edge.clone();
    forged.function = 4;
    assert_eq!(plan_cell_edge(&frame, &forged), rejected);
    forged = edge.clone();
    forged.simultaneous[0].source = 99;
    assert_eq!(plan_cell_edge(&frame, &forged), rejected);
    forged = edge.clone();
    forged.simultaneous[0].type_kind = TernaryCfgScalarKind::U32;
    assert_eq!(plan_cell_edge(&frame, &forged), rejected);
    forged = edge.clone();
    forged.simultaneous.push(forged.simultaneous[0]);
    assert_eq!(plan_cell_edge(&frame, &forged), rejected);
    let mut forged_frame = frame.clone();
    forged_frame.values[1].offset = 1;
    assert_eq!(plan_cell_edge(&forged_frame, &edge), rejected);
    forged_frame = frame.clone();
    forged_frame.values[1].value = 8;
    assert_eq!(plan_cell_edge(&forged_frame, &edge), rejected);
    forged_frame = frame.clone();
    forged_frame.total_words = 5;
    assert_eq!(plan_cell_edge(&forged_frame, &edge), rejected);
    forged_frame = frame.clone();
    forged_frame.scratch_words = 1;
    forged_frame.total_words = 5;
    assert_eq!(plan_cell_edge(&forged_frame, &edge), rejected);
}

#[test]
fn frame_placement_proves_no_source_overlap_and_no_memory_wrap() {
    use super::typed_cfg_adapter::state_storage::{
        CURRENT_WORD_COUNT, placed_cell, validate_frame_placement,
    };
    use super::typed_cfg_adapter::{
        TypedCfgAdapterError, prepare_canonical_dynamic_cfg,
    };

    let (wire, _) =
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(SOURCE)).unwrap();
    let plan = prepare_canonical_dynamic_cfg(&wire).unwrap();
    let frame = &plan.state_frames[0];
    let placement = validate_frame_placement(frame, 200, 200).unwrap();
    assert_eq!(placement.base, 200);
    assert_eq!(placement.end_exclusive, 243);
    assert_eq!(placed_cell(placement, frame, 0), Ok(200));
    assert_eq!(placed_cell(placement, frame, 42), Ok(242));
    let rejected = Err(TypedCfgAdapterError::GuestStateAllocation);
    assert_eq!(placed_cell(placement, frame, 43), rejected);
    assert_eq!(
        validate_frame_placement(frame, 200, 199).err(),
        rejected.err()
    );
    assert_eq!(
        validate_frame_placement(frame, 1, 200).err(),
        rejected.err()
    );
    assert_eq!(
        validate_frame_placement(frame, 200, CURRENT_WORD_COUNT - 42).err(),
        rejected.err()
    );
    let last =
        validate_frame_placement(frame, 200, CURRENT_WORD_COUNT - 43).unwrap();
    assert_eq!(last.end_exclusive, CURRENT_WORD_COUNT);
    assert_eq!(placed_cell(last, frame, 42), Ok(CURRENT_WORD_COUNT - 1));
    let mut forged = last;
    forged.end_exclusive -= 1;
    assert_eq!(placed_cell(forged, frame, 1), rejected);
}

#[test]
fn c32_guest_cell_encoding_roundtrips_all_signed_input_classes() {
    use super::typed_cfg_adapter::state_storage::{
        CURRENT_WORD_COUNT, decode_i32_cells, encode_i32_cells,
    };

    let all_inputs = (0_u32..=255).chain(std::iter::once(u32::MAX));
    for bits in all_inputs {
        let encoded = encode_i32_cells(bits);
        assert!(encoded.iter().all(|cell| *cell < CURRENT_WORD_COUNT));
        assert_eq!(decode_i32_cells(encoded), Some(bits));
    }
    // A deterministic full-word set probes the entire 32-bit range, not only
    // inputs that happen to fit in the first 15-trit cell.
    let mut bits = 0x6d_2b_79_f5_u32;
    for _ in 0..4096 {
        bits = bits.wrapping_mul(1_664_525).wrapping_add(1_013_904_223);
        assert_eq!(decode_i32_cells(encode_i32_cells(bits)), Some(bits));
    }
    assert_eq!(decode_i32_cells([CURRENT_WORD_COUNT, 0]), None);
    assert_eq!(decode_i32_cells([0, CURRENT_WORD_COUNT]), None);
}

#[test]
fn all_source_checksum_phi_edges_copy_original_predecessor_values() {
    use super::typed_cfg_adapter::prepare_canonical_dynamic_cfg;

    let (wire, _) =
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(SOURCE)).unwrap();
    let plan = prepare_canonical_dynamic_cfg(&wire).unwrap();
    let frame = &plan.state_frames[0];
    let mut initial = vec![0_u32; frame.total_words as usize];
    for slot in &frame.values {
        for digit in 0..slot.words {
            initial[(slot.offset + digit) as usize] =
                slot.value.wrapping_mul(1_001).wrapping_add(digit);
        }
    }
    for cell_edge in &plan.cell_edges {
        let incoming = plan
            .phi_edges
            .iter()
            .find(|edge| {
                edge.function == cell_edge.function
                    && edge.predecessor == cell_edge.predecessor
                    && edge.successor == cell_edge.successor
            })
            .unwrap();
        let mut observed = initial.clone();
        for op in cell_edge.snapshots.iter().chain(&cell_edge.commits) {
            observed[op.destination as usize] = observed[op.source as usize];
        }
        let mut expected = initial.clone();
        for assignment in &incoming.simultaneous {
            let from = frame
                .values
                .iter()
                .find(|slot| slot.value == assignment.source)
                .unwrap();
            let to = frame
                .values
                .iter()
                .find(|slot| slot.value == assignment.result)
                .unwrap();
            assert_eq!(from.words, to.words);
            for digit in 0..from.words {
                expected[(to.offset + digit) as usize] =
                    initial[(from.offset + digit) as usize];
            }
        }
        let live = frame.scratch_offset as usize;
        assert_eq!(
            &observed[..live],
            &expected[..live],
            "incorrect staged phi transfer for {} -> {}",
            cell_edge.predecessor,
            cell_edge.successor
        );
    }
}

#[test]
fn original_checksum_binds_all_dynamic_operations_to_disjoint_guest_cells() {
    use super::typed_cfg_adapter::prepare_canonical_dynamic_cfg;
    use super::typed_cfg_adapter::typed::{Instruction, canonical_module};

    let (wire, mode) =
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(SOURCE))
            .expect("frozen checksum source contract");
    assert_eq!(mode, FrontendGuestMode::DynamicEofChecksum);
    let typed =
        canonical_module(&wire).expect("frozen checksum source contract");
    let plan = prepare_canonical_dynamic_cfg(&wire)
        .expect("frozen checksum source contract");
    assert_eq!(plan.operation_blocks.len(), 7);
    let frame = plan.state_frames.first().expect("one state frame");
    let mut observed = 0usize;
    let mut input_count = 0usize;
    let mut output_count = 0usize;
    let mut branching = 0usize;
    for (bound, original) in plan
        .operation_blocks
        .iter()
        .zip(typed.functions().first().expect("one function").blocks())
    {
        assert_eq!(bound.function, 0);
        assert_eq!(bound.block, original.id().value());
        assert_eq!(bound.instructions.len(), original.instructions().len());
        for (binding, located) in
            bound.instructions.iter().zip(original.instructions())
        {
            assert_eq!(&binding.instruction, located.instruction());
            assert_eq!(binding.span, located.span());
            observed += 1;
            for slot in binding.reads.iter().chain(binding.write.as_ref()) {
                assert!(
                    slot.offset
                        .checked_add(slot.words)
                        .is_some_and(|end| end <= frame.scratch_offset)
                );
                assert_eq!(
                    frame.values.iter().find(|saved| saved.value == slot.value),
                    Some(slot),
                );
            }
            if matches!(binding.instruction, Instruction::Getchar { .. }) {
                input_count += 1;
                let dest =
                    binding.write.expect("frozen checksum source contract");
                assert_eq!(
                    dest.words, 2,
                    "signed EOF must retain its high cell"
                );
                assert!(binding.reads.is_empty());
            }
            if matches!(binding.instruction, Instruction::ByteOutput { .. }) {
                output_count += 1;
                assert_eq!(binding.reads.len(), 1);
                assert!(binding.write.is_none());
            }
            if matches!(binding.instruction, Instruction::Binary { .. }) {
                assert_eq!(binding.reads.len(), 2);
                assert!(binding.write.is_some());
            }
        }
        assert_eq!(&bound.control.terminator, original.terminator());
        if let Some(condition) = bound.control.condition {
            branching += 1;
            assert_eq!(condition.words, 1);
            assert!(frame.values.contains(&condition));
        }
        if let Some(returned) = bound.control.return_value {
            assert!(frame.values.contains(&returned));
        }
    }
    assert_eq!(observed, 19);
    assert_eq!(input_count, 2);
    assert_eq!(output_count, 1);
    assert_eq!(branching, 2);
    assert_eq!(prepare_canonical_dynamic_cfg(&wire), Ok(plan));
}

#[test]
fn checksum_literal_cell_bindings_keep_exact_c32_bits_and_source_order() {
    use super::typed_cfg_adapter::prepare_canonical_dynamic_cfg;
    use super::typed_cfg_adapter::state_storage::decode_i32_cells;
    use super::typed_cfg_adapter::typed::{Instruction, canonical_module};

    let (wire, _) =
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(SOURCE))
            .expect("frozen checksum source contract");
    let original =
        canonical_module(&wire).expect("frozen checksum source contract");
    let plan = prepare_canonical_dynamic_cfg(&wire)
        .expect("frozen checksum source contract");
    let mut constant_count = 0usize;
    for (bound, typed) in plan
        .operation_blocks
        .iter()
        .zip(original.functions().first().expect("one function").blocks())
    {
        for (binding, located) in
            bound.instructions.iter().zip(typed.instructions())
        {
            let mut expected_reads = Vec::new();
            let expected_write = match located.instruction() {
                Instruction::Binary { left, right, result, .. }
                | Instruction::Compare { left, right, result, .. } => {
                    expected_reads.extend([left.value(), right.value()]);
                    Some(result.value())
                },
                Instruction::Cast { value, result, .. } => {
                    expected_reads.push(value.value());
                    Some(result.value())
                },
                Instruction::ConstantInteger { result, .. }
                | Instruction::ByteInput { result, .. }
                | Instruction::Getchar { result, .. } => Some(result.value()),
                Instruction::ByteOutput { value } => {
                    expected_reads.push(value.value());
                    None
                },
                Instruction::AddressOffset { .. }
                | Instruction::AutomaticAllocate { .. }
                | Instruction::Call { .. }
                | Instruction::FunctionAddress { .. }
                | Instruction::Load { .. }
                | Instruction::Store { .. } => None,
            };
            assert_eq!(
                binding
                    .reads
                    .iter()
                    .map(|slot| slot.value)
                    .collect::<Vec<_>>(),
                expected_reads
            );
            assert_eq!(binding.write.map(|slot| slot.value), expected_write);
            if let Instruction::ConstantInteger { constant, .. } =
                located.instruction()
            {
                constant_count += 1;
                let slot =
                    binding.write.expect("frozen checksum source contract");
                assert_eq!(
                    binding.constant_cells.len(),
                    usize::try_from(slot.words).expect("N15 slot width")
                );
                let mut observed = [0u32; 2];
                for (offset, cell) in binding.constant_cells.iter().enumerate()
                {
                    assert_eq!(
                        Some(cell.destination),
                        u32::try_from(offset)
                            .ok()
                            .and_then(|index| slot.offset.checked_add(index))
                    );
                    assert!(cell.word < 14_348_907);
                    *observed.get_mut(offset).expect("literal cell extent") =
                        cell.word;
                }
                let expected = constant
                    .little_endian()
                    .iter()
                    .enumerate()
                    .fold(0u32, |acc, (index, byte)| {
                        acc | (u32::from(*byte) << (index * 8))
                    });
                let reconstructed = if slot.words == 2 {
                    decode_i32_cells(observed)
                        .expect("frozen checksum source contract")
                } else {
                    *observed.first().expect("one literal word")
                };
                assert_eq!(reconstructed, expected);
            } else {
                assert!(binding.constant_cells.is_empty());
            }
        }
    }
    assert!(constant_count >= 3);
}

#[test]
fn runtime_operand_binder_rejects_forged_frame_identity_and_cell_geometry() {
    use super::typed_cfg_adapter::state_operations::bind_function_operations;
    use super::typed_cfg_adapter::ternary::TernaryCfgScalarKind;
    use super::typed_cfg_adapter::typed::canonical_module;
    use super::typed_cfg_adapter::{
        TypedCfgAdapterError, prepare_canonical_dynamic_cfg,
    };

    let (wire, _) =
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(SOURCE))
            .expect("frozen checksum source contract");
    let original =
        canonical_module(&wire).expect("frozen checksum source contract");
    let function = original.functions().first().expect("one function");
    let plan = prepare_canonical_dynamic_cfg(&wire)
        .expect("frozen checksum source contract");
    let frame = plan.state_frames.first().expect("one state frame");
    assert_eq!(
        bind_function_operations(&original, function, frame),
        Ok(plan.operation_blocks.clone())
    );
    let refused = Err(TypedCfgAdapterError::GuestStateAllocation);
    let mut forged = frame.clone();
    forged.function += 1;
    assert_eq!(
        bind_function_operations(&original, function, &forged),
        refused
    );
    forged = frame.clone();
    forged.values.first_mut().expect("one slot").value = 998;
    assert_eq!(
        bind_function_operations(&original, function, &forged),
        refused
    );
    forged = frame.clone();
    forged.values.first_mut().expect("one slot").offset += 1;
    assert_eq!(
        bind_function_operations(&original, function, &forged),
        refused
    );
    forged = frame.clone();
    forged.values.first_mut().expect("one slot").type_kind =
        TernaryCfgScalarKind::Bool;
    assert_eq!(
        bind_function_operations(&original, function, &forged),
        refused
    );
    forged = frame.clone();
    forged.values.first_mut().expect("one slot").words += 1;
    assert_eq!(
        bind_function_operations(&original, function, &forged),
        refused
    );
    forged = frame.clone();
    _ = forged.values.pop();
    assert_eq!(
        bind_function_operations(&original, function, &forged),
        refused
    );
}

fn source_locked_checksum_wire() -> Result<Vec<u8>, String> {
    canonical_guest_typed_ir_with_source(NORMALIZED, Some(SOURCE))
        .map(|(wire, _)| wire)
        .map_err(|error| format!("frozen checksum source rejected: {error:?}"))
}

fn relocated_checksum_address(offset: u32) -> u32 {
    let address = 4096u32.checked_add(offset);
    assert!(address.is_some(), "checksum data address must fit in N15");
    address.unwrap_or_default()
}

fn assert_placed_checksum_operand(
    placed: &super::typed_cfg_adapter::state_relocation::GuestPlacedOperand,
    original: &super::typed_cfg_adapter::state_storage::GuestStorageValue,
) {
    assert_eq!(placed.address, relocated_checksum_address(original.offset));
    assert_eq!(placed.value, original.value);
    assert_eq!(placed.words, original.words);
    assert_eq!(placed.type_kind, original.type_kind);
    let cells = (0..original.words)
        .map(|word| placed.cell_address(word))
        .collect::<Vec<_>>();
    assert_eq!(
        cells,
        (0..original.words)
            .map(|word| Some(relocated_checksum_address(
                original.offset + word
            )))
            .collect::<Vec<_>>()
    );
    assert_eq!(placed.cell_address(original.words), None);
    assert!(placed.address >= 4096);
    assert!(placed.address + placed.words <= 4139);
}

fn assert_placed_checksum_instruction(
    placed: &GuestPlacedInstruction,
    original: &GuestOperationBinding,
) {
    assert_eq!(placed.instruction, original.instruction);
    assert_eq!(placed.span, original.span);
    assert_eq!(placed.reads.len(), original.reads.len());
    for (linked, slot) in placed.reads.iter().zip(&original.reads) {
        assert_placed_checksum_operand(linked, slot);
    }
    match (&placed.write, &original.write) {
        (Some(linked), Some(slot)) => {
            assert_placed_checksum_operand(linked, slot)
        },
        (None, None) => {},
        _ => panic!("placed write lost exact source SSA slot"),
    }
    assert_eq!(placed.constant_cells.len(), original.constant_cells.len());
    for (word, cell) in
        placed.constant_cells.iter().zip(&original.constant_cells)
    {
        assert_eq!(
            (word.address, word.word),
            (relocated_checksum_address(cell.destination), cell.word)
        );
    }
}

fn assert_placed_checksum_block(
    placed: &GuestPlacedBlock,
    original: &GuestOperationBlock,
) {
    assert_eq!(
        (placed.function, placed.block),
        (original.function, original.block)
    );
    assert_eq!(placed.instructions.len(), original.instructions.len());
    for (linked, bound) in
        placed.instructions.iter().zip(&original.instructions)
    {
        assert_placed_checksum_instruction(linked, bound);
    }
    match (&placed.condition, &original.control.condition) {
        (Some(linked), Some(slot)) => {
            assert_placed_checksum_operand(linked, slot)
        },
        (None, None) => {},
        _ => panic!("placed branch lost its exact Boolean scalar"),
    }
    match (&placed.return_value, &original.control.return_value) {
        (Some(linked), Some(slot)) => {
            assert_placed_checksum_operand(linked, slot)
        },
        (None, None) => {},
        _ => panic!("placed return lost its exact scalar"),
    }
}

fn assert_placed_checksum_edge(
    placed: &GuestPlacedPhiEdge,
    original: &GuestCellEdge,
) {
    assert_eq!(
        (placed.function, placed.predecessor, placed.successor),
        (original.function, original.predecessor, original.successor)
    );
    assert_eq!(placed.snapshots.len(), original.snapshots.len());
    assert_eq!(placed.commits.len(), original.commits.len());
    for (linked, source) in placed.snapshots.iter().zip(&original.snapshots) {
        assert_eq!(
            (linked.source, linked.destination),
            (
                relocated_checksum_address(source.source),
                relocated_checksum_address(source.destination)
            )
        );
    }
    for (linked, source) in placed.commits.iter().zip(&original.commits) {
        assert_eq!(
            (linked.source, linked.destination),
            (
                relocated_checksum_address(source.source),
                relocated_checksum_address(source.destination)
            )
        );
    }
}

fn assert_source_checksum_relocation(
    relocated: &GuestRelocatedCfgPlan,
    original: &super::typed_cfg_adapter::PrelinkCfgPlan,
    wire: &[u8],
) {
    use super::typed_cfg_adapter::state_relocation::relocate_source_locked_cfg;

    assert_eq!(&relocated.prelink, original);
    assert_eq!(relocated.state_placements.len(), 1);
    assert_eq!(
        relocated
            .state_placements
            .first()
            .map(|place| (place.base, place.end_exclusive)),
        Some((4096, 4139))
    );
    assert_eq!(relocated.operation_blocks.len(), 7);
    assert_eq!(relocated.phi_edges.len(), 4);
    for (placed, bound) in relocated
        .operation_blocks
        .iter()
        .zip(&relocated.prelink.operation_blocks)
    {
        assert_placed_checksum_block(placed, bound);
    }
    for (placed, bound) in relocated
        .phi_edges
        .iter()
        .zip(&relocated.prelink.cell_edges)
    {
        assert_placed_checksum_edge(placed, bound);
    }
    assert_eq!(
        relocate_source_locked_cfg(wire, 2048, 4096),
        Ok(relocated.clone())
    );
}

fn prove_source_checksum_relocation() -> Result<(), String> {
    use super::typed_cfg_adapter::prepare_canonical_dynamic_cfg;
    use super::typed_cfg_adapter::state_relocation::relocate_source_locked_cfg;

    let wire = source_locked_checksum_wire()?;
    let original = prepare_canonical_dynamic_cfg(&wire).map_err(|error| {
        format!("canonical checksum prelink rejected: {error:?}")
    })?;
    let relocated =
        relocate_source_locked_cfg(&wire, 2048, 4096).map_err(|error| {
            format!("source-locked relocation rejected: {error:?}")
        })?;
    assert_source_checksum_relocation(&relocated, &original, &wire);
    Ok(())
}

#[test]
fn source_checksum_control_edges_bind_their_own_phi_copies() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestPlacedControl, GuestPlacedControlEdge, relocate_source_locked_cfg,
    };
    use super::typed_cfg_adapter::typed::Terminator as CfgTerminator;

    let wire =
        source_locked_checksum_wire().expect("pinned source-backed wire");
    let relocated = relocate_source_locked_cfg(&wire, 2048, 4096)
        .expect("source-locked checksum placement");
    let expected_edge = |function, predecessor, successor| {
        let phi = relocated.phi_edges.iter().find(|edge| {
            (edge.function, edge.predecessor, edge.successor)
                == (function, predecessor, successor)
        });
        GuestPlacedControlEdge {
            successor,
            snapshots: phi.map_or_else(Vec::new, |edge| edge.snapshots.clone()),
            commits: phi.map_or_else(Vec::new, |edge| edge.commits.clone()),
        }
    };
    let mut branches = 0;
    let mut jumps = 0;
    let mut returns = 0;
    for (block, original) in relocated
        .operation_blocks
        .iter()
        .zip(&relocated.prelink.operation_blocks)
    {
        match (&block.control, &original.control.terminator) {
            (
                GuestPlacedControl::Jump { edge },
                CfgTerminator::Jump { target },
            ) => {
                jumps += 1;
                assert_eq!(
                    *edge,
                    expected_edge(block.function, block.block, target.value())
                );
            },
            (
                GuestPlacedControl::Branch { when_false, when_true },
                CfgTerminator::Branch {
                    false_target,
                    true_target,
                    ..
                },
            ) => {
                branches += 1;
                assert_eq!(
                    *when_false,
                    expected_edge(
                        block.function,
                        block.block,
                        false_target.value()
                    )
                );
                assert_eq!(
                    *when_true,
                    expected_edge(
                        block.function,
                        block.block,
                        true_target.value()
                    )
                );
            },
            (GuestPlacedControl::Return, CfgTerminator::Return { .. }) => {
                returns += 1;
            },
            _ => panic!("physical data plan lost canonical CFG control"),
        }
    }
    assert_eq!((branches, jumps, returns), (2, 4, 1));
    // The actual checksum backedge takes snapshots *before* committing the
    // two carried C32 values. No host-side input selected that edge.
    let backedge = &relocated.operation_blocks[5];
    let GuestPlacedControl::Jump { edge } = &backedge.control else {
        panic!("checksum block 5 must jump back to block 1");
    };
    assert_eq!(edge.successor, 1);
    assert_eq!(edge.snapshots.len(), 4);
    assert_eq!(edge.commits.len(), 4);
    assert!(edge.snapshots.iter().all(|copy| {
        (4096..4139).contains(&copy.source)
            && (4096..4139).contains(&copy.destination)
    }));
}

// These are proposed *code* intervals for the original seven C23 blocks.
// No bytes or Malbolge instruction placement are produced by this test.
fn checksum_proposed_code_blocks()
-> Vec<super::typed_cfg_adapter::state_relocation::GuestCodeBlockPlacement> {
    use super::typed_cfg_adapter::state_relocation::GuestCodeBlockPlacement;

    [
        (64, 80),
        (80, 100),
        (104, 116),
        (128, 144),
        (144, 152),
        (160, 200),
        (224, 240),
    ]
    .into_iter()
    .enumerate()
    .map(|(block, (start, end_exclusive))| GuestCodeBlockPlacement {
        block: u32::try_from(block).expect("seven source blocks"),
        end_exclusive,
        function: 0,
        start,
        control_start: end_exclusive - 1,
    })
    .collect()
}

// Edge-local phi copies must run before entering a shared successor. These
// unverified intervals reserve separate predecessor-specific landing pads.
fn checksum_proposed_phi_edge_pads()
-> Vec<super::typed_cfg_adapter::state_relocation::GuestCodeEdgePadPlacement> {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeEdgeKind, GuestCodeEdgePadPlacement,
    };

    [
        (0, 1, 256, 280),
        (3, 5, 288, 304),
        (4, 5, 312, 328),
        (5, 1, 336, 376),
    ]
    .into_iter()
    .map(|(predecessor, successor, start, end_exclusive)| {
        GuestCodeEdgePadPlacement {
            end_exclusive,
            function: 0,
            kind: GuestCodeEdgeKind::Jump,
            predecessor,
            start,
            successor,
        }
    })
    .collect()
}

#[test]
fn source_checksum_proposed_code_entries_bind_all_unselected_control_edges() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeControlEdge, GuestCodeEdgeKind, GuestCodeProposals,
        bind_source_locked_cfg_code_targets,
    };
    use super::typed_cfg_adapter::typed::Instruction as PlacedInstruction;

    let wire =
        source_locked_checksum_wire().expect("original C23 typed source");
    let proposed = checksum_proposed_code_blocks();
    let pads = checksum_proposed_phi_edge_pads();
    let mut reordered = proposed.clone();
    reordered.reverse();
    let mut reversed_pads = pads.clone();
    reversed_pads.reverse();
    let addressed = bind_source_locked_cfg_code_targets(
        &wire,
        2048,
        4096,
        GuestCodeProposals {
            code_blocks: &reordered,
            edge_pads: &reversed_pads,
        },
    )
    .expect("distinct source-contained blocks and phi landing pads");
    assert_eq!(addressed.code_blocks, proposed);
    // Every authenticated typed operation must acquire a distinct minimum
    // code reservation before its block's unverified control sequence.
    // This is an address obligation, not a claim about encoded opcodes.
    let mut all_operation_sites = 0usize;
    for (block, proposed_block) in
        addressed.relocated.operation_blocks.iter().zip(&proposed)
    {
        let sites = addressed
            .operation_sites
            .iter()
            .filter(|site| {
                (site.function, site.block) == (block.function, block.block)
            })
            .collect::<Vec<_>>();
        assert_eq!(sites.len(), block.instructions.len());
        let mut next = proposed_block.start;
        for (ordinal, (site, operation)) in
            sites.iter().zip(&block.instructions).enumerate()
        {
            assert_eq!(site.ordinal, u32::try_from(ordinal).unwrap());
            assert_eq!(site.start, next);
            let writes = operation.write.map_or(0, |slot| slot.words);
            let input = u32::from(matches!(
                operation.instruction,
                PlacedInstruction::Getchar { .. }
                    | PlacedInstruction::ByteInput { .. }
            ));
            let required = (writes + input)
                .max(u32::try_from(operation.constant_cells.len()).unwrap())
                .max(1);
            assert_eq!(site.end_exclusive - site.start, required);
            assert!(site.end_exclusive <= proposed_block.control_start);
            next = site.end_exclusive;
        }
        all_operation_sites += sites.len();
    }
    assert_eq!(all_operation_sites, 19);
    // Every minimum reservation must bind its independent physical effects,
    // including the real input opcode before both signed C32 stores.
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeInputSemantics, GuestCodeOperationEffect,
    };
    let mut inputs = Vec::new();
    let mut outputs = Vec::new();
    let mut stores = 0usize;
    let mut literal_stores = 0usize;
    let mut compute_sites = 0usize;
    for site in &addressed.operation_sites {
        let original = &addressed.relocated.operation_blocks
            [usize::try_from(site.block).unwrap()]
        .instructions[usize::try_from(site.ordinal).unwrap()];
        let effects = addressed
            .operation_effect_sites
            .iter()
            .filter(|effect| {
                (effect.function, effect.block, effect.ordinal)
                    == (site.function, site.block, site.ordinal)
            })
            .collect::<Vec<_>>();
        assert_eq!(effects.len(), (site.end_exclusive - site.start) as usize);
        for (index, effect) in effects.iter().enumerate() {
            assert_eq!(effect.code_address, site.start + index as u32);
            match effect.effect {
                GuestCodeOperationEffect::Input { destination, semantics } => {
                    assert!(matches!(
                        original.instruction,
                        PlacedInstruction::Getchar { .. }
                    ));
                    assert_eq!(original.write, Some(destination));
                    assert_eq!(destination.words, 2, "C23 int is full-width");
                    assert_eq!(
                        semantics,
                        GuestCodeInputSemantics::SignedC23 {
                            raw_eof_word: 14_348_906,
                            c23_eof_cells: [4_644_102, 299],
                        },
                        "raw N15 EOF is not the C23 minus-one value"
                    );
                    assert_eq!(index, 0, "the signed read precedes all stores");
                    assert_eq!(
                        effects.len(),
                        3,
                        "one input and two C32 writes"
                    );
                    inputs.push((
                        effect.block,
                        effect.ordinal,
                        effect.code_address,
                    ));
                },
                GuestCodeOperationEffect::Output { source } => {
                    assert!(matches!(
                        original.instruction,
                        PlacedInstruction::ByteOutput { .. }
                    ));
                    assert_eq!(original.reads.as_slice(), &[source]);
                    outputs.push((effect.block, source.address));
                },
                GuestCodeOperationEffect::Store { destination, literal } => {
                    let slot = original
                        .write
                        .expect("store must have SSA destination");
                    assert!(
                        (slot.address..slot.address + slot.words)
                            .contains(&destination)
                    );
                    assert_eq!(
                        literal,
                        original
                            .constant_cells
                            .iter()
                            .find(|word| word.address == destination)
                            .map(|word| word.word)
                    );
                    literal_stores += usize::from(literal.is_some());
                    stores += 1;
                },
                GuestCodeOperationEffect::Compute => {
                    assert!(original.write.is_none());
                    assert!(!matches!(
                        original.instruction,
                        PlacedInstruction::ByteOutput { .. }
                    ));
                    compute_sites += 1;
                },
            }
        }
    }
    assert_eq!(inputs.len(), 2, "both signed getchar effects are distinct");
    assert_ne!(inputs[0].2, inputs[1].2);
    assert_eq!(outputs.len(), 1, "one guest byte output is retained");
    assert!(stores > 2, "full-width scalar results have separate stores");
    assert!(
        literal_stores > 0,
        "literal words remain source-authenticated"
    );
    assert_eq!(
        addressed.operation_effect_sites.len(),
        inputs.len() + outputs.len() + stores + compute_sites
    );
    assert_eq!(addressed.edge_pads, pads);
    assert_eq!(addressed.relocated.operation_blocks.len(), 7);
    assert_eq!(addressed.control_edges.len(), 8);
    // Four distinct predecessor-owned phi pads must leave through their
    // individually reserved final code cells; no branch arm inherits a
    // synthetic pad exit when it has no phi transfers.
    let mut pad_exit_sites = addressed
        .control_edges
        .iter()
        .filter_map(|edge| {
            edge.pad_exit_address
                .map(|exit| (edge.predecessor, edge.successor, exit))
        })
        .collect::<Vec<_>>();
    pad_exit_sites.sort_unstable();
    assert_eq!(pad_exit_sites, [
        (0, 1, 279),
        (3, 5, 303),
        (4, 5, 327),
        (5, 1, 375),
    ]);
    assert_eq!(
        addressed
            .control_edges
            .iter()
            .filter(|edge| edge.pad_exit_address.is_none())
            .count(),
        4,
    );
    assert_eq!(addressed.function_entries, vec![
        super::typed_cfg_adapter::state_relocation::GuestCodeFunctionEntry {
            function: 0,
            block: 0,
            address: 64,
        }
    ]);
    assert_eq!(addressed.return_sites, vec![
        super::typed_cfg_adapter::state_relocation::GuestCodeReturnSite {
            function: 0,
            block: 6,
            address: 239,
            value: None,
        }
    ]);
    let mut targets = addressed
        .control_edges
        .iter()
        .map(|edge| (edge.predecessor, edge.successor, edge.target_address))
        .collect::<Vec<_>>();
    targets.sort_unstable();
    assert_eq!(targets, [
        (0, 1, 80),
        (1, 2, 104),
        (1, 6, 224),
        (2, 3, 128),
        (2, 4, 144),
        (3, 5, 160),
        (4, 5, 160),
        (5, 1, 80),
    ]);
    let original_edges = &addressed.relocated.phi_edges;
    for GuestCodeControlEdge {
        commit_sites,
        commits,
        condition,
        control_address,
        entry_address,
        function,
        kind,
        pad_exit_address,
        predecessor,
        snapshot_sites,
        snapshots,
        successor,
        target_address,
    } in &addressed.control_edges
    {
        assert_eq!(*function, 0);
        let predecessor_block = &addressed.relocated.operation_blocks
            [usize::try_from(*predecessor).expect("canonical predecessor")];
        assert_eq!(*condition, predecessor_block.condition);
        assert_eq!(
            *control_address,
            proposed
                [usize::try_from(*predecessor).expect("canonical predecessor")]
            .control_start
        );
        assert_eq!(*kind, match *predecessor {
            1 | 2 if *successor == 2 || *successor == 3 => {
                GuestCodeEdgeKind::WhenTrue
            },
            1 | 2 => GuestCodeEdgeKind::WhenFalse,
            _ => GuestCodeEdgeKind::Jump,
        },);
        assert_eq!(
            proposed
                .iter()
                .find(|block| {
                    block.function == *function && block.block == *successor
                })
                .map(|block| block.start),
            Some(*target_address)
        );
        let phi = original_edges.iter().find(|edge| {
            (edge.function, edge.predecessor, edge.successor)
                == (*function, *predecessor, *successor)
        });
        assert_eq!(
            *entry_address,
            pads.iter()
                .find(|pad| {
                    pad.function == *function
                        && pad.predecessor == *predecessor
                        && pad.successor == *successor
                        && pad.kind == *kind
                })
                .map_or(*target_address, |pad| pad.start),
        );
        let pad = pads.iter().find(|pad| {
            pad.function == *function
                && pad.predecessor == *predecessor
                && pad.successor == *successor
                && pad.kind == *kind
        });
        assert_eq!(
            *pad_exit_address,
            pad.map(|pad| pad.end_exclusive - 1),
            "only phi-bearing edges reserve post-copy jump cells"
        );
        assert_eq!(
            snapshots.as_slice(),
            phi.map_or(&[][..], |edge| &edge.snapshots)
        );
        assert_eq!(
            commits.as_slice(),
            phi.map_or(&[][..], |edge| &edge.commits)
        );
        // The same source-owned edge binds ordered write-obligation cells,
        // rather than only reserving an anonymous phi-pad interval.
        assert_eq!(
            snapshot_sites
                .iter()
                .map(|site| site.copy)
                .collect::<Vec<_>>(),
            *snapshots,
        );
        assert_eq!(
            commit_sites
                .iter()
                .map(|site| site.copy)
                .collect::<Vec<_>>(),
            *commits,
        );
        if let Some(pad) = pad {
            let expected = (pad.end_exclusive
                - 1
                - u32::try_from(snapshots.len() + commits.len()).unwrap()
                ..pad.end_exclusive - 1)
                .collect::<Vec<_>>();
            let actual = snapshot_sites
                .iter()
                .chain(commit_sites)
                .map(|site| site.code_address)
                .collect::<Vec<_>>();
            assert_eq!(
                actual, expected,
                "phi sites on {predecessor}->{successor}"
            );
            assert_eq!(
                actual.last().and_then(|cell| cell.checked_add(1)),
                *pad_exit_address,
                "the final phi commit precedes the successor transfer",
            );
        } else {
            assert!(snapshot_sites.is_empty());
            assert!(commit_sites.is_empty());
        }
    }
    // The original four source-locked phi edges have distinct contiguous
    // copy suffixes, with no speculative filler between their final commit
    // and the required successor transfer at the pad end.
    let mut bound_copy_suffixes = addressed
        .control_edges
        .iter()
        .filter_map(|edge| {
            Some((
                edge.predecessor,
                edge.successor,
                edge.snapshot_sites.first()?.code_address,
                edge.commit_sites.first()?.code_address,
                edge.pad_exit_address?,
            ))
        })
        .collect::<Vec<_>>();
    bound_copy_suffixes.sort_unstable();
    assert_eq!(bound_copy_suffixes, [
        (0, 1, 271, 275, 279),
        (3, 5, 299, 301, 303),
        (4, 5, 323, 325, 327),
        (5, 1, 367, 371, 375),
    ]);
    let backedge = addressed.control_edges.last().expect("canonical backedge");
    assert_eq!((backedge.predecessor, backedge.successor), (5, 1));
    assert_eq!(backedge.snapshots.len(), 4);
    assert_eq!(backedge.commits.len(), 4);
    assert_eq!((backedge.entry_address, backedge.target_address), (336, 80));
    assert_eq!(
        bind_source_locked_cfg_code_targets(
            &wire,
            2048,
            4096,
            GuestCodeProposals {
                code_blocks: &proposed,
                edge_pads: &pads,
            }
        ),
        Ok(addressed)
    );
}

#[test]
fn original_checksum_has_source_locked_minimum_code_and_phi_pad_plan() {
    use super::typed_cfg_adapter::TypedCfgAdapterError;
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodePlacementError, plan_source_locked_cfg_minimum_code_targets,
        source_locked_cfg_minimum_code_cells,
    };

    let wire = source_locked_checksum_wire().expect("original C23 source");
    assert_eq!(source_locked_cfg_minimum_code_cells(&wire), Ok(71));
    // Exactly 43 minimum block cells and 28 predecessor-specific phi-pad
    // cells are required. This is a *code capacity* lower bound, not an
    // executable source or evidence that 71 graphical bytes implement C.
    let planned =
        plan_source_locked_cfg_minimum_code_targets(&wire, 91, 128, 0)
            .expect("source-derived original checksum code reservations");
    assert_eq!(
        planned
            .code_blocks
            .iter()
            .map(|block| (
                block.start,
                block.control_start,
                block.end_exclusive,
            ))
            .collect::<Vec<_>>(),
        [
            (0, 15, 16),
            (16, 17, 18),
            (18, 21, 22),
            (22, 26, 27),
            (27, 31, 32),
            (32, 39, 40),
            (40, 42, 43),
        ]
    );
    assert_eq!(
        planned
            .edge_pads
            .iter()
            .map(|pad| (
                pad.predecessor,
                pad.successor,
                pad.start,
                pad.end_exclusive,
            ))
            .collect::<Vec<_>>(),
        [
            (0, 1, 43, 52),
            (3, 5, 52, 57),
            (4, 5, 57, 62),
            (5, 1, 62, 71),
        ]
    );
    assert_eq!(planned.operation_sites.len(), 19);
    assert_eq!(planned.operation_effect_sites.len(), 36);
    assert_eq!(planned.control_edges.len(), 8);
    assert_eq!(planned.return_sites.len(), 1);
    assert_eq!(planned.relocated.state_placements[0].base, 128);
    assert_eq!(planned.relocated.state_placements[0].end_exclusive, 171);
    assert_eq!(planned.function_entries[0].address, 0);
    assert_eq!(
        plan_source_locked_cfg_minimum_code_targets(&wire, 91, 128, 0),
        Ok(planned.clone()),
        "canonical source input must yield identical code obligations"
    );
    let shifted =
        plan_source_locked_cfg_minimum_code_targets(&wire, 100, 128, 12)
            .expect("source-relative code placement can relocate");
    assert_eq!(shifted.code_blocks[0].start, 12);
    assert_eq!(
        shifted.edge_pads.last().map(|pad| pad.end_exclusive),
        Some(83)
    );
    assert_eq!(shifted.relocated.state_placements[0].base, 128);
    let refused = Err(GuestCodePlacementError::InvalidCodePlacement);
    assert_eq!(
        plan_source_locked_cfg_minimum_code_targets(&wire, 70, 128, 0),
        refused,
        "one cell short of the true lower bound must refuse"
    );
    assert_eq!(
        plan_source_locked_cfg_minimum_code_targets(&wire, 91, 128, 21),
        refused,
        "proposed source too small for shifted placement"
    );
    assert_eq!(
        plan_source_locked_cfg_minimum_code_targets(&wire, 91, 128, u32::MAX),
        refused,
        "offset arithmetic cannot wrap"
    );
    assert_eq!(
        plan_source_locked_cfg_minimum_code_targets(&wire, 91, 90, 0),
        Err(GuestCodePlacementError::TypedCfg(
            TypedCfgAdapterError::GuestStateAllocation,
        )),
        "typed C-state frame may not alias source bytes"
    );
    let mut corrupted = wire;
    corrupted.push(0);
    assert!(matches!(
        source_locked_cfg_minimum_code_cells(&corrupted),
        Err(GuestCodePlacementError::TypedCfg(_)),
    ));
    assert!(matches!(
        plan_source_locked_cfg_minimum_code_targets(&corrupted, 91, 128, 0),
        Err(GuestCodePlacementError::TypedCfg(_)),
    ));
}

// Two actual byte inputs in the same C basic block require distinct physical
// source sites, but only one reservation for their shared instruction span.
fn same_block_two_input_wire() -> Vec<u8> {
    use super::typed::{
        BasicBlock, BasicBlockSpec, BlockId, Function, FunctionId,
        FunctionSpec, LocatedInstruction, Module, ModuleSpec, SourcePosition,
        SourceSpan, TypeDef, TypeEntry, TypeId, ValueId, canonical_bytes,
        validate_module,
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
        format_version: super::typed::TYPED_IR_VERSION,
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
            name: String::from("two_source_inputs"),
            parameters: Vec::new(),
            signature: TypeId::new(1),
            span: span(0, 4),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/two-source-inputs.c"),
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
    validate_module(&module).expect("valid source-typed two-input block");
    canonical_bytes(&module).expect("canonical two-input block")
}

#[test]
fn source_input_anchors_share_a_real_basic_block_without_aliasing() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeInputAnchor, GuestCodeOperationEffect,
        GuestCodePlacementError, plan_source_locked_cfg_with_input_anchors,
        source_locked_cfg_minimum_code_cells,
    };

    let wire = same_block_two_input_wire();
    let first = GuestCodeInputAnchor {
        block: 0,
        code_address: 37,
        function: 0,
        ordinal: 0,
    };
    let second = GuestCodeInputAnchor {
        block: 0,
        code_address: 39,
        function: 0,
        ordinal: 1,
    };
    assert_eq!(source_locked_cfg_minimum_code_cells(&wire), Ok(6));
    let expected =
        plan_source_locked_cfg_with_input_anchors(&wire, 91, 128, &[
            first, second,
        ])
        .expect("same source block should have two different reads");
    assert_eq!(expected.code_blocks.len(), 1);
    assert_eq!(expected.code_blocks[0].start, 37);
    assert_eq!(expected.code_blocks[0].end_exclusive, 43);
    assert_eq!(
        expected
            .operation_effect_sites
            .iter()
            .filter_map(|site| {
                matches!(site.effect, GuestCodeOperationEffect::Input { .. })
                    .then_some((site.ordinal, site.code_address))
            })
            .collect::<Vec<_>>(),
        [(0, 37), (1, 39)]
    );
    assert_eq!(
        plan_source_locked_cfg_with_input_anchors(&wire, 91, 128, &[
            second, first
        ],),
        Ok(expected.clone())
    );

    let gapped = GuestCodeInputAnchor {
        code_address: 40,
        ..second
    };
    let with_setup =
        plan_source_locked_cfg_with_input_anchors(&wire, 91, 128, &[
            first, gapped,
        ])
        .expect("source-typed input sites may have a real guest setup gap");
    assert_eq!(with_setup.code_blocks[0].start, 37);
    assert_eq!(with_setup.code_blocks[0].end_exclusive, 44);
    assert_eq!(
        with_setup
            .operation_effect_sites
            .iter()
            .filter_map(|site| {
                matches!(site.effect, GuestCodeOperationEffect::Input { .. })
                    .then_some(site.code_address)
            })
            .collect::<Vec<_>>(),
        [37, 40],
    );
    let refusal = Err(GuestCodePlacementError::InvalidCodePlacement);
    for anchors in [
        vec![first, first],
        vec![first, GuestCodeInputAnchor {
            code_address: 38,
            ..second
        }],
        vec![first, GuestCodeInputAnchor {
            code_address: 37,
            ..second
        }],
        vec![first, GuestCodeInputAnchor { ordinal: 2, ..second }],
    ] {
        let actual =
            plan_source_locked_cfg_with_input_anchors(&wire, 91, 128, &anchors);
        assert_eq!(actual, refusal);
    }
    assert!(
        plan_source_locked_cfg_with_input_anchors(&wire, 42, 128, &[
            first, second
        ],)
        .is_err()
    );
}

// This is actual source-backed Clang C, not a synthetic typed fixture. The
// two discarded signed getchar calls share one C basic block. The real guest
// performs both / instructions, but it does not implement the two required
// C32 result writes, so this remains input-site *prefix* evidence only.
#[test]
fn original_same_block_c23_getchar_sites_match_two_real_guest_reads() {
    use malbolge::{
        ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
        decode_profile_instruction,
    };

    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeInputAnchor, GuestCodeInputSemantics,
        GuestCodeOperationEffect, plan_source_locked_cfg_with_input_anchors,
    };

    let original =
        include_bytes!("c-frontend/accepted/discarded_getchar_two.c");
    let normalized =
        include_bytes!("c-frontend/golden/discarded_getchar_two.json");
    let (wire, mode) =
        canonical_guest_typed_ir_with_source(normalized, Some(original))
            .expect("original two-read C must reenter compiler");
    assert_eq!(mode, FrontendGuestMode::DiscardedGetchar);
    let anchors = [
        GuestCodeInputAnchor {
            function: 0,
            block: 0,
            ordinal: 0,
            code_address: 0,
        },
        GuestCodeInputAnchor {
            function: 0,
            block: 0,
            ordinal: 1,
            code_address: 3,
        },
    ];
    let plan =
        plan_source_locked_cfg_with_input_anchors(&wire, 7, 128, &anchors)
            .expect("two signed source reads in the same block");
    assert_eq!(plan.code_blocks.len(), 1);
    assert_eq!(
        (plan.code_blocks[0].start, plan.code_blocks[0].end_exclusive),
        (0, 7)
    );
    let source_sites = plan
        .operation_effect_sites
        .iter()
        .filter_map(|site| {
            if let GuestCodeOperationEffect::Input { destination, semantics } =
                site.effect
            {
                assert_eq!(destination.words, 2);
                assert!(matches!(
                    semantics,
                    GuestCodeInputSemantics::SignedC23 { .. }
                ));
                Some((site.ordinal, site.code_address, destination.address))
            } else {
                None
            }
        })
        .collect::<Vec<_>>();
    assert_eq!(source_sites.len(), 2);
    assert_eq!((source_sites[0].0, source_sites[0].1), (0, 0));
    assert_eq!((source_sites[1].0, source_sites[1].1), (1, 3));
    assert_ne!(source_sites[0].2, source_sites[1].2);

    let physical = b"/oo/oov"
        .iter()
        .enumerate()
        .map(|(address, opcode)| {
            (33u8..=126)
                .find(|byte| {
                    decode_profile_instruction(u32::from(*byte), address as u32)
                        == Some(*opcode)
                })
                .expect("every physical opcode must be graphical")
        })
        .collect::<Vec<_>>();
    for input in [Vec::new(), vec![0], vec![0xff], vec![0x80, 1], vec![
        0x01, 0x02, 0x03,
    ]] {
        let mut guest = ProfileMachine::from_source(
            current_profile(),
            &physical,
            input.clone(),
        )
        .expect("printable, valid N15 source");
        let mut reached = Vec::new();
        let outcome = guest
            .run_traced(7, &mut |step| {
                if let Some(event) = step.input {
                    reached.push((
                        step.before.registers.code_pointer,
                        event,
                        step.after.registers.accumulator,
                    ));
                }
            })
            .expect("seven physically valid instructions");
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 7,
        });
        assert!(guest.output().is_empty());
        assert_eq!(guest.input_consumed(), input.len().min(2));
        assert_eq!(reached, [
            (
                0,
                input
                    .first()
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte),
                input
                    .first()
                    .copied()
                    .map_or(current_profile().eof_word(), u32::from)
            ),
            (
                3,
                input
                    .get(1)
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte),
                input
                    .get(1)
                    .copied()
                    .map_or(current_profile().eof_word(), u32::from)
            ),
        ]);
    }
}

// The original source-locked two-getchar C23 shape has one basic block.
// A source-loaded N15 guest may reserve an inert cell for future pointer
// preparation between the two real reads. Physical read sites must remain
// fixed, even though neither result has yet been written to its signed two-cell
// frame.
#[test]
fn original_two_getchars_accept_a_real_guest_setup_gap() {
    use malbolge::{
        ProfileMachine, RunOutcome, Termination, TraceInput, current_profile,
        decode_profile_instruction,
    };

    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeInputAnchor, GuestCodeOperationEffect,
        GuestCodePlacementError, plan_source_locked_cfg_with_input_anchors,
    };

    let original =
        include_bytes!("c-frontend/accepted/discarded_getchar_two.c");
    let normalized =
        include_bytes!("c-frontend/golden/discarded_getchar_two.json");
    let (wire, mode) =
        canonical_guest_typed_ir_with_source(normalized, Some(original))
            .expect("pinned two-read C23 source");
    assert_eq!(mode, FrontendGuestMode::DiscardedGetchar);
    let first = GuestCodeInputAnchor {
        block: 0,
        code_address: 0,
        function: 0,
        ordinal: 0,
    };
    let second = GuestCodeInputAnchor {
        code_address: 4,
        ordinal: 1,
        ..first
    };
    let plan = plan_source_locked_cfg_with_input_anchors(&wire, 8, 128, &[
        second, first,
    ])
    .expect("physical guest setup gap must not shift authenticated reads");
    assert_eq!(plan.code_blocks.len(), 1);
    assert_eq!(
        (
            plan.code_blocks[0].start,
            plan.code_blocks[0].control_start,
            plan.code_blocks[0].end_exclusive,
        ),
        (0, 7, 8)
    );
    assert_eq!(
        plan.operation_effect_sites
            .iter()
            .filter_map(|site| {
                matches!(site.effect, GuestCodeOperationEffect::Input { .. })
                    .then_some((site.ordinal, site.code_address))
            })
            .collect::<Vec<_>>(),
        [(0, 0), (1, 4)],
    );
    assert_eq!(
        plan_source_locked_cfg_with_input_anchors(&wire, 8, 128, &[
            first,
            GuestCodeInputAnchor {
                code_address: 2,
                ..second
            },
        ]),
        Err(GuestCodePlacementError::InvalidCodePlacement),
    );
    let physical = b"/ooo/oov"
        .iter()
        .enumerate()
        .map(|(position, opcode)| {
            (33u8..=126)
                .find(|byte| {
                    decode_profile_instruction(
                        u32::from(*byte),
                        u32::try_from(position).unwrap_or(u32::MAX),
                    ) == Some(*opcode)
                })
                .expect("source-loadable N15 instruction")
        })
        .collect::<Vec<_>>();
    for input in [&[][..], &[0][..], &[255, 128][..], &[3, 0, 44][..]] {
        let mut vm = ProfileMachine::from_source(
            current_profile(),
            &physical,
            input.to_vec(),
        )
        .expect("source-loaded two-read guest");
        let mut reads = Vec::new();
        let outcome = vm
            .run_traced(8, &mut |step| {
                if let Some(value) = step.input {
                    reads.push((step.before.registers.code_pointer, value));
                }
            })
            .expect("bounded normative N15 VM");
        assert_eq!(outcome, RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps: 8,
        });
        assert_eq!(reads, [
            (
                0,
                input
                    .first()
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
            (
                4,
                input
                    .get(1)
                    .copied()
                    .map_or(TraceInput::EndOfInput, TraceInput::Byte)
            ),
        ]);
        assert_eq!(vm.input_consumed(), input.len().min(2));
        assert!(vm.output().is_empty());
    }
}

// Source-locked C23 input operations owe *three* distinct effects each:
// real '/', a low-word store and a high-word store. These positions are
// unverified code reservations, not claims of executable signed conversion.
#[test]
fn original_c23_two_reads_reserve_sparse_signed_word_effects() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeEffectAnchor, GuestCodeInputAnchor, GuestCodeOperationEffect,
        GuestCodePlacementError,
        plan_source_locked_cfg_with_input_and_effect_anchors,
    };

    let original =
        include_bytes!("c-frontend/accepted/discarded_getchar_two.c");
    let normalized =
        include_bytes!("c-frontend/golden/discarded_getchar_two.json");
    let (wire, mode) =
        canonical_guest_typed_ir_with_source(normalized, Some(original))
            .expect("authentic original two-getchar C23 source");
    assert_eq!(mode, FrontendGuestMode::DiscardedGetchar);
    let inputs = [
        GuestCodeInputAnchor {
            block: 0,
            code_address: 0,
            function: 0,
            ordinal: 0,
        },
        GuestCodeInputAnchor {
            block: 0,
            code_address: 20,
            function: 0,
            ordinal: 1,
        },
    ];
    let sites = [
        GuestCodeEffectAnchor {
            block: 0,
            code_address: 7,
            effect_index: 1,
            function: 0,
            ordinal: 0,
        },
        GuestCodeEffectAnchor {
            block: 0,
            code_address: 9,
            effect_index: 2,
            function: 0,
            ordinal: 0,
        },
        GuestCodeEffectAnchor {
            block: 0,
            code_address: 27,
            effect_index: 1,
            function: 0,
            ordinal: 1,
        },
        GuestCodeEffectAnchor {
            block: 0,
            code_address: 29,
            effect_index: 2,
            function: 0,
            ordinal: 1,
        },
    ];
    let plan = plan_source_locked_cfg_with_input_and_effect_anchors(
        &wire, 36, 128, &inputs, &sites,
    )
    .expect("original C23 read and distinct signed result word sites");
    assert_eq!(plan.code_blocks.len(), 1);
    assert_eq!(
        (
            plan.code_blocks[0].start,
            plan.code_blocks[0].control_start,
            plan.code_blocks[0].end_exclusive
        ),
        (0, 30, 31),
    );
    assert_eq!(
        plan.operation_effect_sites
            .iter()
            .map(|site| site.code_address)
            .collect::<Vec<_>>(),
        [0, 7, 9, 20, 27, 29],
    );
    assert_eq!(
        plan.operation_effect_sites
            .iter()
            .filter(|site| matches!(
                site.effect,
                GuestCodeOperationEffect::Input { .. }
            ))
            .count(),
        2,
    );
    assert_eq!(
        plan.operation_effect_sites
            .iter()
            .filter_map(|site| match site.effect {
                GuestCodeOperationEffect::Store {
                    destination,
                    literal: None,
                } => Some(destination),
                _ => None,
            })
            .collect::<Vec<_>>(),
        [128, 129, 130, 131],
    );
    assert_eq!(
        plan_source_locked_cfg_with_input_and_effect_anchors(
            &wire, 30, 128, &inputs, &sites,
        ),
        Err(GuestCodePlacementError::InvalidCodePlacement),
    );
    let mut forged = sites;
    forged[1].code_address = 6;
    assert_eq!(
        plan_source_locked_cfg_with_input_and_effect_anchors(
            &wire, 36, 128, &inputs, &forged,
        ),
        Err(GuestCodePlacementError::InvalidCodePlacement),
    );
    forged = sites;
    forged[1].effect_index = 3;
    assert_eq!(
        plan_source_locked_cfg_with_input_and_effect_anchors(
            &wire, 36, 128, &inputs, &forged,
        ),
        Err(GuestCodePlacementError::InvalidCodePlacement),
    );
    forged = sites;
    forged[0].effect_index = 0;
    assert_eq!(
        plan_source_locked_cfg_with_input_and_effect_anchors(
            &wire, 36, 128, &inputs, &forged,
        ),
        Err(GuestCodePlacementError::InvalidCodePlacement),
        "effect-index zero cannot relocate the authenticated read",
    );
    let mut repeated = sites.to_vec();
    repeated.push(sites[0]);
    assert_eq!(
        plan_source_locked_cfg_with_input_and_effect_anchors(
            &wire, 36, 128, &inputs, &repeated,
        ),
        Err(GuestCodePlacementError::InvalidCodePlacement),
        "one source-word effect may have only one physical site",
    );
    assert_eq!(
        plan_source_locked_cfg_with_input_and_effect_anchors(
            &wire,
            36,
            128,
            &[],
            &sites,
        ),
        Err(GuestCodePlacementError::InvalidCodePlacement),
    );
}

// Pin both source-C23 signed input results in the actual mutable checksum
// graph. This is still an unlinked proposal: the guest has to *execute*
// all four stores and the phi/control graph before publication.
#[test]
fn original_checksum_sparse_c23_effects_keep_phi_pads_disjoint() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeEffectAnchor, GuestCodeInputAnchor, GuestCodeOperationEffect,
        plan_source_locked_cfg_with_input_and_effect_anchors,
    };

    let wire = source_locked_checksum_wire().expect("original C23 checksum");
    let inputs = [
        GuestCodeInputAnchor {
            block: 0,
            code_address: 37,
            function: 0,
            ordinal: 1,
        },
        GuestCodeInputAnchor {
            block: 5,
            code_address: 66,
            function: 0,
            ordinal: 2,
        },
    ];
    let effects = [
        GuestCodeEffectAnchor {
            block: 0,
            code_address: 40,
            effect_index: 1,
            function: 0,
            ordinal: 1,
        },
        GuestCodeEffectAnchor {
            block: 0,
            code_address: 42,
            effect_index: 2,
            function: 0,
            ordinal: 1,
        },
        GuestCodeEffectAnchor {
            block: 5,
            code_address: 69,
            effect_index: 1,
            function: 0,
            ordinal: 2,
        },
        GuestCodeEffectAnchor {
            block: 5,
            code_address: 71,
            effect_index: 2,
            function: 0,
            ordinal: 2,
        },
    ];
    let plan = plan_source_locked_cfg_with_input_and_effect_anchors(
        &wire, 91, 128, &inputs, &effects,
    )
    .expect("seven-block C23 read/store effect reservations with phi pads");
    assert_eq!(plan.code_blocks.len(), 7);
    assert_eq!(plan.edge_pads.len(), 4);
    assert_eq!(
        plan.operation_effect_sites
            .iter()
            .filter_map(|site| {
                (matches!(site.effect, GuestCodeOperationEffect::Input { .. })
                    || matches!(
                        site.effect,
                        GuestCodeOperationEffect::Store { .. }
                    ) && [40, 42, 69, 71].contains(&site.code_address))
                .then_some((site.block, site.code_address))
            })
            .collect::<Vec<_>>(),
        [(0, 37), (0, 40), (0, 42), (5, 66), (5, 69), (5, 71)],
    );
    let reservations = plan
        .code_blocks
        .iter()
        .map(|block| (block.start, block.end_exclusive))
        .chain(
            plan.edge_pads
                .iter()
                .map(|pad| (pad.start, pad.end_exclusive)),
        )
        .collect::<Vec<_>>();
    for (index, &(start, end)) in reservations.iter().enumerate() {
        assert!(start < end && end <= 91, "bounded guest code interval");
        for &(other_start, other_end) in reservations.iter().skip(index + 1) {
            assert!(
                end <= other_start || other_end <= start,
                "source frame, code and phi pads must never alias"
            );
        }
    }
}

// Source-authenticated operations before the first real signed input, and in
// unrelated blocks, need independently anchored code positions. These are
// unverified layout proposals, not executable C or guest opcodes.
#[test]
fn original_checksum_anchors_non_input_operations_around_signed_reads() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeEffectAnchor, GuestCodeOperationAnchor,
        GuestCodePlacementError,
        plan_source_locked_cfg_with_operation_and_effect_anchors,
    };

    let wire = source_locked_checksum_wire().expect("original C23 checksum");
    let operations = [
        GuestCodeOperationAnchor {
            function: 0,
            block: 0,
            ordinal: 0,
            code_address: 0,
        },
        GuestCodeOperationAnchor {
            function: 0,
            block: 0,
            ordinal: 1,
            code_address: 37,
        },
        GuestCodeOperationAnchor {
            function: 0,
            block: 5,
            ordinal: 2,
            code_address: 66,
        },
        GuestCodeOperationAnchor {
            function: 0,
            block: 3,
            ordinal: 0,
            code_address: 180,
        },
    ];
    let effects = [
        GuestCodeEffectAnchor {
            function: 0,
            block: 0,
            ordinal: 1,
            effect_index: 1,
            code_address: 40,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 0,
            ordinal: 1,
            effect_index: 2,
            code_address: 42,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 5,
            ordinal: 2,
            effect_index: 1,
            code_address: 69,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 5,
            ordinal: 2,
            effect_index: 2,
            code_address: 71,
        },
    ];
    let plan = plan_source_locked_cfg_with_operation_and_effect_anchors(
        &wire,
        256,
        512,
        &operations,
        &effects,
    )
    .expect("literal, arithmetic, two reads and four stores reserve code");
    assert_eq!(plan.code_blocks.len(), 7);
    assert_eq!(plan.edge_pads.len(), 4);
    for anchor in operations {
        assert_eq!(
            plan.operation_sites
                .iter()
                .find(|site| {
                    (site.function, site.block, site.ordinal)
                        == (anchor.function, anchor.block, anchor.ordinal)
                })
                .map(|site| site.start),
            Some(anchor.code_address),
        );
    }
    assert!(matches!(
        plan.relocated.operation_blocks[0].instructions[0].instruction,
        super::typed_cfg_adapter::typed::Instruction::ConstantInteger { .. }
    ));
    assert!(
        plan.operation_sites.iter().any(|site| {
            site.block == 3 && site.ordinal == 0 && site.computation.is_some()
        }),
        "source block three must retain its typed arithmetic/cast"
    );
    assert_eq!(plan.function_entries[0].address, 0);
    assert_eq!(plan.relocated.state_placements[0].base, 512);
    for effect in effects {
        assert!(plan.operation_effect_sites.iter().any(|site| {
            (site.function, site.block, site.ordinal, site.code_address)
                == (
                    effect.function,
                    effect.block,
                    effect.ordinal,
                    effect.code_address,
                )
        }));
    }
    let invalid = Err(GuestCodePlacementError::InvalidCodePlacement);
    let mut forged = operations;
    forged[0].code_address = 38;
    assert_eq!(
        plan_source_locked_cfg_with_operation_and_effect_anchors(
            &wire, 256, 512, &forged, &effects,
        ),
        invalid,
        "the first source literal cannot execute after the read",
    );
    forged = operations;
    forged[3].code_address = 40;
    assert_eq!(
        plan_source_locked_cfg_with_operation_and_effect_anchors(
            &wire, 256, 512, &forged, &effects,
        ),
        invalid,
        "different source blocks cannot share a code reservation",
    );
    forged = operations;
    forged[3].ordinal = 99;
    assert_eq!(
        plan_source_locked_cfg_with_operation_and_effect_anchors(
            &wire, 256, 512, &forged, &effects,
        ),
        invalid,
    );
    let mut duplicated = operations.to_vec();
    duplicated.push(operations[0]);
    assert_eq!(
        plan_source_locked_cfg_with_operation_and_effect_anchors(
            &wire,
            256,
            512,
            &duplicated,
            &effects,
        ),
        invalid,
    );
}

// The checked source CFG also needs space for a physical control suffix
// after each block's data effects, including blocks with no input anchor.
// The proposed sites are not yet verified Malbolge branch instructions.
#[test]
fn original_checksum_pins_sparse_control_sites_after_data_effects() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeControlAnchor, GuestCodeEffectAnchor,
        GuestCodeOperationAnchor, GuestCodePlacementError,
        plan_source_locked_cfg_with_operation_effect_and_control_anchors,
    };

    let wire = source_locked_checksum_wire().expect("original C23 checksum");
    let operations = [
        GuestCodeOperationAnchor {
            function: 0,
            block: 0,
            ordinal: 1,
            code_address: 37,
        },
        GuestCodeOperationAnchor {
            function: 0,
            block: 5,
            ordinal: 2,
            code_address: 66,
        },
        GuestCodeOperationAnchor {
            function: 0,
            block: 3,
            ordinal: 0,
            code_address: 180,
        },
    ];
    let effects = [
        GuestCodeEffectAnchor {
            function: 0,
            block: 0,
            ordinal: 1,
            effect_index: 1,
            code_address: 40,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 0,
            ordinal: 1,
            effect_index: 2,
            code_address: 42,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 5,
            ordinal: 2,
            effect_index: 1,
            code_address: 69,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 5,
            ordinal: 2,
            effect_index: 2,
            code_address: 71,
        },
    ];
    let controls = [
        GuestCodeControlAnchor {
            function: 0,
            block: 0,
            code_address: 60,
        },
        GuestCodeControlAnchor {
            function: 0,
            block: 5,
            code_address: 75,
        },
        GuestCodeControlAnchor {
            function: 0,
            block: 3,
            code_address: 201,
        },
        GuestCodeControlAnchor {
            function: 0,
            block: 6,
            code_address: 224,
        },
    ];
    let bind = |controls: &[GuestCodeControlAnchor]| {
        plan_source_locked_cfg_with_operation_effect_and_control_anchors(
            &wire,
            256,
            512,
            &operations,
            &effects,
            controls,
        )
    };
    let plan =
        bind(&controls).expect("source operations and control suffixes fit");
    for anchor in controls {
        assert_eq!(
            plan.code_blocks
                .iter()
                .find(|block| {
                    (block.function, block.block)
                        == (anchor.function, anchor.block)
                })
                .map(|block| block.control_start),
            Some(anchor.code_address),
        );
    }
    assert_eq!(plan.function_entries[0].block, 0);
    assert_eq!(plan.return_sites[0].address, 224);
    assert_eq!(plan.control_edges.len(), 8);
    assert_eq!(plan.edge_pads.len(), 4);
    let invalid = Err(GuestCodePlacementError::InvalidCodePlacement);
    let mut forged = controls;
    forged[1].code_address = 70;
    assert_eq!(
        bind(&forged),
        invalid,
        "control cannot precede a signed word store"
    );
    forged = controls;
    forged[0].code_address = 67;
    assert_eq!(
        bind(&forged),
        invalid,
        "overlapping source CFG blocks refuse"
    );
    forged = controls;
    forged[3].block = 99;
    assert_eq!(bind(&forged), invalid, "foreign CFG control site refuses");
    let mut duplicate = controls.to_vec();
    duplicate.push(controls[0]);
    assert_eq!(bind(&duplicate), invalid);
    assert_eq!(
        plan_source_locked_cfg_with_operation_effect_and_control_anchors(
            &wire,
            224,
            512,
            &operations,
            &effects,
            &controls,
        ),
        invalid,
        "guest control address must fit within the graphical source",
    );
}

// An automatic source-locked layout must not silently move a witnessed
// snapshot/commit sequence after placing unrelated source blocks first.
// The code locations are proposals, not executed guest phi writes.
#[test]
fn original_checksum_auto_reserves_sparse_backedge_phi_copy_sites() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeEdgeKind, GuestCodePhiCopyAnchor, GuestCodePlacementError,
        plan_source_locked_cfg_with_operation_effect_control_and_phi_anchors,
    };

    let wire = source_locked_checksum_wire().expect("original C23 checksum");
    let positions = [90, 97, 105, 114, 123, 131, 140, 150];
    let phi = positions
        .into_iter()
        .enumerate()
        .map(|(copy_index, code_address)| GuestCodePhiCopyAnchor {
            code_address,
            copy_index: u32::try_from(copy_index).expect("eight phi copies"),
            function: 0,
            kind: GuestCodeEdgeKind::Jump,
            predecessor: 5,
            successor: 1,
        })
        .collect::<Vec<_>>();
    let bind = |phi: &[GuestCodePhiCopyAnchor]| {
        plan_source_locked_cfg_with_operation_effect_control_and_phi_anchors(
            &wire,
            256,
            512,
            &[],
            &[],
            &[],
            phi,
        )
    };
    let plan =
        bind(&phi).expect("source-locked sparse backedge pad reservation");
    let pad = plan
        .edge_pads
        .iter()
        .find(|pad| (pad.function, pad.predecessor, pad.successor) == (0, 5, 1))
        .expect("source checksum backedge pad");
    assert_eq!((pad.start, pad.end_exclusive), (90, 152));
    let edge = plan
        .control_edges
        .iter()
        .find(|edge| {
            (edge.function, edge.predecessor, edge.successor) == (0, 5, 1)
        })
        .expect("source checksum backedge");
    assert_eq!(
        edge.snapshot_sites
            .iter()
            .chain(&edge.commit_sites)
            .map(|site| site.code_address)
            .collect::<Vec<_>>(),
        positions,
    );
    assert_eq!(edge.pad_exit_address, Some(151));
    assert_eq!(plan.code_blocks.len(), 7);
    assert_eq!(plan.edge_pads.len(), 4);
    let mut intervals = plan
        .code_blocks
        .iter()
        .map(|block| (block.start, block.end_exclusive))
        .chain(
            plan.edge_pads
                .iter()
                .map(|pad| (pad.start, pad.end_exclusive)),
        )
        .collect::<Vec<_>>();
    intervals.sort_unstable();
    for pair in intervals.windows(2) {
        assert!(
            pair[0].1 <= pair[1].0,
            "unanchored source blocks must not hide the pinned phi pad"
        );
    }
    let refused = Err(GuestCodePlacementError::InvalidCodePlacement);
    let mut invalid = phi.clone();
    assert!(invalid.pop().is_some());
    assert_eq!(bind(&invalid), refused, "incomplete copies must refuse");
    invalid = phi.clone();
    invalid.push(phi[0]);
    assert_eq!(bind(&invalid), refused, "duplicate copies must refuse");
    for bad in [
        GuestCodePhiCopyAnchor { copy_index: 9, ..phi[0] },
        GuestCodePhiCopyAnchor { predecessor: 4, ..phi[0] },
        GuestCodePhiCopyAnchor {
            kind: GuestCodeEdgeKind::WhenTrue,
            ..phi[0]
        },
        GuestCodePhiCopyAnchor { function: 5, ..phi[0] },
        GuestCodePhiCopyAnchor {
            code_address: 151,
            ..phi[0]
        },
        GuestCodePhiCopyAnchor {
            code_address: 255,
            ..phi[0]
        },
    ] {
        let mut changed = phi.clone();
        changed[0] = bad;
        assert_eq!(bind(&changed), refused, "forged source phi {bad:?}");
    }
    let mut shuffled = phi.clone();
    shuffled.reverse();
    assert_eq!(bind(&shuffled), Ok(plan));
}

// Exact source read/store, return and phi-pad reservations must compose:
// reserving one independently observed edge can never alias an input block.
#[test]
fn original_checksum_auto_phi_pad_composes_with_signed_input_and_control_sites()
{
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeControlAnchor, GuestCodeEdgeKind, GuestCodeEffectAnchor,
        GuestCodeOperationAnchor, GuestCodePhiCopyAnchor,
        GuestCodePlacementError,
        plan_source_locked_cfg_with_operation_effect_control_and_phi_anchors,
    };

    let wire = source_locked_checksum_wire()
        .expect("source-authenticated C23 EOF loop");
    let operations = [
        GuestCodeOperationAnchor {
            function: 0,
            block: 0,
            ordinal: 1,
            code_address: 37,
        },
        GuestCodeOperationAnchor {
            function: 0,
            block: 5,
            ordinal: 2,
            code_address: 66,
        },
        GuestCodeOperationAnchor {
            function: 0,
            block: 3,
            ordinal: 0,
            code_address: 180,
        },
    ];
    let effects = [
        GuestCodeEffectAnchor {
            function: 0,
            block: 0,
            ordinal: 1,
            effect_index: 1,
            code_address: 40,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 0,
            ordinal: 1,
            effect_index: 2,
            code_address: 42,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 5,
            ordinal: 2,
            effect_index: 1,
            code_address: 69,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 5,
            ordinal: 2,
            effect_index: 2,
            code_address: 71,
        },
    ];
    let controls = [
        GuestCodeControlAnchor {
            function: 0,
            block: 0,
            code_address: 60,
        },
        GuestCodeControlAnchor {
            function: 0,
            block: 5,
            code_address: 75,
        },
        GuestCodeControlAnchor {
            function: 0,
            block: 3,
            code_address: 201,
        },
        GuestCodeControlAnchor {
            function: 0,
            block: 6,
            code_address: 224,
        },
    ];
    let addresses = [90, 97, 105, 114, 123, 131, 140, 150];
    let phi = addresses
        .into_iter()
        .enumerate()
        .map(|(copy_index, code_address)| GuestCodePhiCopyAnchor {
            code_address,
            copy_index: u32::try_from(copy_index)
                .expect("backedge phi copy ordinal"),
            function: 0,
            kind: GuestCodeEdgeKind::Jump,
            predecessor: 5,
            successor: 1,
        })
        .collect::<Vec<_>>();
    let plan =
        plan_source_locked_cfg_with_operation_effect_control_and_phi_anchors(
            &wire,
            256,
            512,
            &operations,
            &effects,
            &controls,
            &phi,
        )
        .expect(
            "all source-locked site classes fit one deterministic geometry",
        );
    assert_eq!(plan.code_blocks.len(), 7);
    assert_eq!(plan.edge_pads.len(), 4);
    assert_eq!(plan.return_sites[0].address, 224);
    assert_eq!(
        plan.operation_effect_sites
            .iter()
            .filter(|effect| {
                [37, 40, 42, 66, 69, 71].contains(&effect.code_address)
            })
            .count(),
        6,
    );
    let backedge = plan
        .control_edges
        .iter()
        .find(|edge| {
            (edge.function, edge.predecessor, edge.successor) == (0, 5, 1)
        })
        .expect("source backedge");
    assert_eq!(backedge.entry_address, 90);
    assert_eq!(backedge.pad_exit_address, Some(151));
    assert_eq!(
        backedge
            .snapshot_sites
            .iter()
            .chain(&backedge.commit_sites)
            .map(|copy| copy.code_address)
            .collect::<Vec<_>>(),
        addresses,
    );
    let mut conflicting = operations;
    conflicting[2].code_address = 120;
    assert_eq!(
        plan_source_locked_cfg_with_operation_effect_control_and_phi_anchors(
            &wire,
            256,
            512,
            &conflicting,
            &effects,
            &controls,
            &phi,
        ),
        Err(GuestCodePlacementError::InvalidCodePlacement),
        "source block cannot run in the reserved backedge phi pad",
    );
}

// Two independently pinned incoming phi edges for the same loop header
// must keep their own snapshot/commit code pads and predecessor identity.
#[test]
fn original_checksum_auto_phi_pads_keep_both_header_predecessors_disjoint() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeEdgeKind, GuestCodePhiCopyAnchor, GuestCodePhiEntryAnchor,
        GuestCodePhiExitAnchor, GuestCodePlacementError,
        plan_source_locked_cfg_with_operation_effect_control_and_phi_anchors,
        plan_source_locked_cfg_with_phi_boundary_anchors,
        plan_source_locked_cfg_with_phi_exit_anchors,
    };
    let wire =
        source_locked_checksum_wire().expect("C23 loop backedge and entry");
    let entry = [88, 89, 91, 93, 95, 97, 99, 101];
    let backedge = [120, 127, 135, 144, 153, 161, 170, 181];
    let anchors = [(0, entry), (5, backedge)]
        .into_iter()
        .flat_map(|(predecessor, addresses)| {
            addresses.into_iter().enumerate().map(
                move |(index, code_address)| GuestCodePhiCopyAnchor {
                    code_address,
                    copy_index: u32::try_from(index)
                        .expect("eight source copies"),
                    function: 0,
                    kind: GuestCodeEdgeKind::Jump,
                    predecessor,
                    successor: 1,
                },
            )
        })
        .collect::<Vec<_>>();
    let bind = |anchors: &[GuestCodePhiCopyAnchor]| {
        plan_source_locked_cfg_with_operation_effect_control_and_phi_anchors(
            &wire,
            256,
            512,
            &[],
            &[],
            &[],
            anchors,
        )
    };
    let plan = bind(&anchors).expect("both incoming edges have separate pads");
    for (predecessor, addresses) in [(0, entry), (5, backedge)] {
        let edge = plan
            .control_edges
            .iter()
            .find(|edge| {
                (edge.function, edge.predecessor, edge.successor)
                    == (0, predecessor, 1)
            })
            .expect("source predecessor-specific loop phi edge");
        assert_eq!(edge.entry_address, addresses[0]);
        assert_eq!(edge.pad_exit_address, Some(addresses[7] + 1));
        assert_eq!(edge.snapshot_sites.len(), 4);
        assert_eq!(edge.commit_sites.len(), 4);
        assert_eq!(
            edge.snapshot_sites
                .iter()
                .chain(&edge.commit_sites)
                .map(|site| site.code_address)
                .collect::<Vec<_>>(),
            addresses,
        );
    }
    assert_eq!(plan.edge_pads.len(), 4);
    let refused = Err(GuestCodePlacementError::InvalidCodePlacement);
    let mut overlapping = anchors.clone();
    for anchor in overlapping
        .iter_mut()
        .filter(|anchor| anchor.predecessor == 5)
    {
        anchor.code_address -= 35;
    }
    assert_eq!(
        bind(&overlapping),
        refused,
        "distinct phi edges may not alias"
    );
    let mut foreign = anchors.clone();
    foreign[0].predecessor = 3;
    assert_eq!(bind(&foreign), refused, "source copy identities stay bound");
    let mut shuffled = anchors.clone();
    shuffled.reverse();
    assert_eq!(bind(&shuffled), Ok(plan));

    // Each predecessor may need its *own* post-commit pointer setup, and
    // neither exit may consume code reserved for the other phi landing pad.
    let exits = [
        GuestCodePhiExitAnchor {
            code_address: 109,
            function: 0,
            kind: GuestCodeEdgeKind::Jump,
            predecessor: 0,
            successor: 1,
        },
        GuestCodePhiExitAnchor {
            code_address: 199,
            function: 0,
            kind: GuestCodeEdgeKind::Jump,
            predecessor: 5,
            successor: 1,
        },
    ];
    let with_exits = |exits: &[GuestCodePhiExitAnchor]| {
        plan_source_locked_cfg_with_phi_exit_anchors(
            &wire,
            256,
            512,
            &[],
            &[],
            &[],
            &anchors,
            exits,
        )
    };
    let padded = with_exits(&exits)
        .expect("each source predecessor has an independent exit and setup");
    for (predecessor, first, exit) in [(0, 88, 109), (5, 120, 199)] {
        let edge = padded
            .control_edges
            .iter()
            .find(|edge| {
                (edge.function, edge.predecessor, edge.successor)
                    == (0, predecessor, 1)
            })
            .expect("source locked predecessor");
        assert_eq!(
            (edge.entry_address, edge.pad_exit_address),
            (first, Some(exit))
        );
    }
    let mut reordered = exits;
    reordered.reverse();
    assert_eq!(with_exits(&reordered), Ok(padded));
    // Both distinct loop-header phi predecessors may reserve setup before
    // *their own* first copy, without relocating one another's word sites.
    let entries = [
        GuestCodePhiEntryAnchor {
            code_address: 80,
            function: 0,
            kind: GuestCodeEdgeKind::Jump,
            predecessor: 0,
            successor: 1,
        },
        GuestCodePhiEntryAnchor {
            code_address: 112,
            function: 0,
            kind: GuestCodeEdgeKind::Jump,
            predecessor: 5,
            successor: 1,
        },
    ];
    let with_boundaries = |entries: &[GuestCodePhiEntryAnchor]| {
        plan_source_locked_cfg_with_phi_boundary_anchors(
            &wire,
            256,
            512,
            &[],
            &[],
            &[],
            &anchors,
            entries,
            &exits,
        )
    };
    let with_entries = with_boundaries(&entries)
        .expect("both original checksum predecessors keep private setup");
    for (predecessor, start, first, exit) in
        [(0, 80, 88, 109), (5, 112, 120, 199)]
    {
        let edge = with_entries
            .control_edges
            .iter()
            .find(|edge| {
                (edge.function, edge.predecessor, edge.successor)
                    == (0, predecessor, 1)
            })
            .expect("source predecessor edge");
        assert_eq!(
            (edge.entry_address, edge.pad_exit_address),
            (start, Some(exit))
        );
        assert_eq!(edge.snapshot_sites[0].code_address, first);
    }
    let mut entry_order = entries;
    entry_order.reverse();
    assert_eq!(with_boundaries(&entry_order), Ok(with_entries));
    assert_eq!(
        with_boundaries(&[entries[0], GuestCodePhiEntryAnchor {
            code_address: 105,
            ..entries[1]
        },]),
        refused,
        "one predecessor setup cannot overlap the other pad"
    );
    assert_eq!(
        with_boundaries(&[
            GuestCodePhiEntryAnchor {
                predecessor: 5,
                ..entries[0]
            },
            entries[1],
        ]),
        refused,
        "predecessor identity cannot be borrowed"
    );
    assert_eq!(
        with_exits(&[
            GuestCodePhiExitAnchor {
                code_address: 125,
                ..exits[0]
            },
            exits[1],
        ]),
        refused,
        "one predecessor cannot occupy the next phi pad"
    );
}

#[test]
fn source_checksum_input_anchors_reserve_disjoint_unselected_phi_paths() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeInputAnchor, GuestCodeOperationEffect,
        GuestCodePlacementError, plan_source_locked_cfg_with_input_anchors,
    };

    let wire = source_locked_checksum_wire().expect("original C23 source");
    // The independent physical converter executes signed '/' at C37 and
    // C66. These are *candidate coordinates*, not a claim that its bytes
    // implement the source-C checksum or its parallel phi transfers.
    let first = GuestCodeInputAnchor {
        function: 0,
        block: 0,
        ordinal: 1,
        code_address: 37,
    };
    let second = GuestCodeInputAnchor {
        function: 0,
        block: 5,
        ordinal: 2,
        code_address: 66,
    };
    let proposed =
        plan_source_locked_cfg_with_input_anchors(&wire, 91, 128, &[
            first, second,
        ])
        .expect("source-backed non-overlapping physical input coordinates");
    assert_eq!(
        proposed
            .code_blocks
            .iter()
            .map(|block| (block.block, block.start, block.end_exclusive,))
            .collect::<Vec<_>>(),
        [
            (0, 35, 51),
            (1, 0, 2),
            (2, 2, 6),
            (3, 6, 11),
            (4, 11, 16),
            (5, 62, 70),
            (6, 16, 19)
        ],
    );
    assert_eq!(
        proposed
            .edge_pads
            .iter()
            .map(|pad| (
                pad.predecessor,
                pad.successor,
                pad.start,
                pad.end_exclusive,
            ))
            .collect::<Vec<_>>(),
        [
            (0, 1, 19, 28),
            (3, 5, 28, 33),
            (4, 5, 51, 56),
            (5, 1, 70, 79)
        ],
    );
    let inputs = proposed
        .operation_effect_sites
        .iter()
        .filter_map(|site| {
            matches!(site.effect, GuestCodeOperationEffect::Input { .. })
                .then_some((site.block, site.ordinal, site.code_address))
        })
        .collect::<Vec<_>>();
    assert_eq!(inputs, [(0, 1, 37), (5, 2, 66)]);
    assert_eq!(proposed.function_entries[0].address, 35);
    assert_eq!(
        plan_source_locked_cfg_with_input_anchors(&wire, 91, 128, &[
            second, first
        ],),
        Ok(proposed),
        "candidate anchors are source identities, not argument order",
    );
    let refuses = Err(GuestCodePlacementError::InvalidCodePlacement);
    assert_eq!(
        plan_source_locked_cfg_with_input_anchors(&wire, 91, 128, &[
            first, first
        ],),
        refuses,
        "duplicate physical input anchors must refuse",
    );
    assert_eq!(
        plan_source_locked_cfg_with_input_anchors(&wire, 91, 128, &[
            GuestCodeInputAnchor { ordinal: 0, ..first }
        ],),
        refuses,
        "constants are not signed guest input effects",
    );
    assert_eq!(
        plan_source_locked_cfg_with_input_anchors(&wire, 91, 128, &[
            GuestCodeInputAnchor { code_address: 1, ..first }
        ],),
        refuses,
        "anchor address cannot precede the required entry prefix",
    );
    assert_eq!(
        plan_source_locked_cfg_with_input_anchors(&wire, 70, 128, &[
            first, second
        ],),
        refuses,
        "71 minimum code cells cannot fit into a 70-cell source",
    );
    assert_eq!(
        plan_source_locked_cfg_with_input_anchors(&wire, 91, 128, &[
            first,
            GuestCodeInputAnchor {
                code_address: 37,
                ..second
            }
        ],),
        refuses,
        "two pinned source blocks cannot overlap the same guest code",
    );
    assert_eq!(
        plan_source_locked_cfg_with_input_anchors(&wire, 91, 128, &[
            GuestCodeInputAnchor { block: 99, ..first }
        ],),
        refuses,
        "input anchors cannot invent an unseen source block",
    );
    assert_eq!(
        plan_source_locked_cfg_with_input_anchors(&wire, 91, 128, &[]),
        super::typed_cfg_adapter::state_relocation::
            plan_source_locked_cfg_minimum_code_targets(&wire, 91, 128, 0),
        "unconstrained first-fit must recover the source-ordered plan",
    );
    let mut forged = wire;
    forged.push(0);
    assert!(matches!(
        plan_source_locked_cfg_with_input_anchors(&forged, 91, 128, &[
            first, second
        ],),
        Err(GuestCodePlacementError::TypedCfg(_)),
    ));
}

#[test]
fn source_checksum_effect_anchors_allow_checked_runtime_setup_gaps() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeOperationAnchor, GuestCodeOperationEffect,
        GuestCodePlacementError, GuestCodeProposals,
        bind_source_locked_cfg_code_targets,
        bind_source_locked_cfg_code_targets_with_operation_anchors,
    };

    let wire = source_locked_checksum_wire().expect("original C23 source");
    let mut blocks = checksum_proposed_code_blocks();
    let starts = [64, 120, 140, 160, 184, 208, 252];
    let ends = [112, 132, 156, 180, 204, 248, 268];
    for (index, block) in blocks.iter_mut().enumerate() {
        block.start = starts[index];
        block.end_exclusive = ends[index];
        block.control_start = ends[index] - 1;
    }
    let mut pads = checksum_proposed_phi_edge_pads();
    for (pad, (start, end_exclusive)) in
        pads.iter_mut()
            .zip([(300, 324), (328, 344), (348, 364), (368, 408)])
    {
        pad.start = start;
        pad.end_exclusive = end_exclusive;
    }
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &pads,
    };
    let first = GuestCodeOperationAnchor {
        block: 0,
        code_address: 83,
        function: 0,
        ordinal: 1,
    };
    let second = GuestCodeOperationAnchor {
        block: 5,
        code_address: 226,
        function: 0,
        ordinal: 2,
    };
    let middle = GuestCodeOperationAnchor {
        block: 2,
        code_address: 147,
        function: 0,
        ordinal: 0,
    };
    let anchors = [first, second, middle];
    let anchored = bind_source_locked_cfg_code_targets_with_operation_anchors(
        &wire, 512, 4096, proposals, &anchors,
    )
    .expect("source-authenticated effects may follow unverified setup space");
    let previous =
        bind_source_locked_cfg_code_targets(&wire, 512, 4096, proposals)
            .expect(
                "original minimum effects still fit inside expanded blocks",
            );
    assert_eq!(anchored.relocated, previous.relocated);
    assert_eq!(anchored.control_edges, previous.control_edges);
    assert_eq!(anchored.code_blocks, previous.code_blocks);
    assert_eq!(anchored.edge_pads, previous.edge_pads);
    assert_eq!(anchored.operation_sites.len(), 19);
    assert_ne!(anchored.operation_sites, previous.operation_sites);
    for anchor in anchors {
        let site = anchored.operation_sites.iter().find(|site| {
            (site.function, site.block, site.ordinal)
                == (anchor.function, anchor.block, anchor.ordinal)
        });
        assert_eq!(site.map(|site| site.start), Some(anchor.code_address));
    }
    let input_sites = anchored
        .operation_effect_sites
        .iter()
        .filter_map(|site| {
            matches!(site.effect, GuestCodeOperationEffect::Input { .. })
                .then_some((site.block, site.ordinal, site.code_address))
        })
        .collect::<Vec<_>>();
    assert_eq!(input_sites, [(0, 1, 83), (5, 2, 226)]);
    assert_eq!(
        bind_source_locked_cfg_code_targets_with_operation_anchors(
            &wire,
            512,
            4096,
            proposals,
            &[middle, first, second],
        ),
        Ok(anchored.clone()),
        "anchors must be identified by source operation, not input order",
    );
    let refuses = Err(GuestCodePlacementError::InvalidCodePlacement);
    for forged in [
        vec![first, first],
        vec![GuestCodeOperationAnchor { ordinal: 99, ..first }],
        vec![GuestCodeOperationAnchor { block: 99, ..first }],
        vec![GuestCodeOperationAnchor { function: 1, ..first }],
        vec![GuestCodeOperationAnchor {
            code_address: 64,
            ..first
        }],
        vec![GuestCodeOperationAnchor {
            code_address: 111,
            ..first
        }],
        vec![first, GuestCodeOperationAnchor {
            block: 0,
            ordinal: 0,
            code_address: 84,
            ..first
        }],
        vec![GuestCodeOperationAnchor {
            code_address: u32::MAX,
            ..second
        }],
    ] {
        assert_eq!(
            bind_source_locked_cfg_code_targets_with_operation_anchors(
                &wire, 512, 4096, proposals, &forged,
            ),
            refuses,
            "unmapped, overlapping or out-of-order effect anchors refuse",
        );
    }
}

#[test]
fn source_checksum_code_entry_bindings_fail_closed_on_invalid_code_layout() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodePlacementError, GuestCodeProposals,
        bind_source_locked_cfg_code_targets,
    };
    use super::typed_cfg_adapter::typed::Instruction as GuestTypedInstruction;

    let wire =
        source_locked_checksum_wire().expect("original C23 typed source");
    let proposed = checksum_proposed_code_blocks();
    let pads = checksum_proposed_phi_edge_pads();
    let refusal = Err(GuestCodePlacementError::InvalidCodePlacement);
    let check = |blocks: &[_]| {
        bind_source_locked_cfg_code_targets(
            &wire,
            2048,
            4096,
            GuestCodeProposals {
                code_blocks: blocks,
                edge_pads: &pads,
            },
        )
    };
    let mut missing = proposed.clone();
    assert!(missing.pop().is_some());
    assert_eq!(check(&missing), refusal);
    let mut duplicate = proposed.clone();
    duplicate.push(proposed[0]);
    assert_eq!(check(&duplicate), refusal);
    let mut foreign_block = proposed.clone();
    foreign_block[0].block = 100;
    assert_eq!(check(&foreign_block), refusal);
    let mut foreign_function = proposed.clone();
    foreign_function[0].function = 1;
    assert_eq!(check(&foreign_function), refusal);
    let mut empty = proposed.clone();
    empty[0].end_exclusive = empty[0].start;
    assert_eq!(check(&empty), refusal);
    let mut reversed = proposed.clone();
    reversed[0].end_exclusive = reversed[0].start - 1;
    assert_eq!(check(&reversed), refusal);
    // The source's block 2 computes a live condition before branching.
    // A proposed terminator at its entry leaves no real instruction cell
    // to realize even the first typed operation: this must fail closed.
    let mut control_at_block_start = proposed.clone();
    control_at_block_start[2].control_start = proposed[2].start;
    assert_eq!(check(&control_at_block_start), refusal);
    // Each original typed operation requires its own instruction cell, and
    // multiword constants require a separate cell per mandatory write.
    // Preserve the final cell for a real terminator, not a host branch.
    let plan = super::typed_cfg_adapter::prepare_canonical_dynamic_cfg(&wire)
        .expect("original checksum must have verified typed operations");
    for operation_block in &plan.operation_blocks {
        let id = usize::try_from(operation_block.block).unwrap();
        let minimum = operation_block
            .instructions
            .iter()
            .map(|instruction| {
                let writes = instruction.write.map_or(0, |slot| slot.words);
                let input = u32::from(matches!(
                    instruction.instruction,
                    GuestTypedInstruction::Getchar { .. }
                        | GuestTypedInstruction::ByteInput { .. }
                ));
                usize::try_from(writes + input)
                    .unwrap()
                    .max(instruction.constant_cells.len())
                    .max(1)
            })
            .sum::<usize>();
        assert_eq!(minimum, [15, 1, 3, 4, 4, 7, 2][id]);
        if minimum == 0 {
            continue;
        }
        let mut one_cell_short = proposed.clone();
        one_cell_short[id].control_start =
            one_cell_short[id].start + u32::try_from(minimum - 1).unwrap();
        assert_eq!(check(&one_cell_short), refusal, "block {id}");
        let mut exact = proposed.clone();
        exact[id].control_start =
            exact[id].start + u32::try_from(minimum).unwrap();
        assert!(check(&exact).is_ok(), "block {id}");
    }
    let mut control_before_block = proposed.clone();
    control_before_block[2].control_start = proposed[2].start - 1;
    assert_eq!(check(&control_before_block), refusal);
    let mut control_after_block = proposed.clone();
    control_after_block[2].control_start = proposed[2].end_exclusive;
    assert_eq!(check(&control_after_block), refusal);
    let mut collision = proposed.clone();
    collision[1].start = collision[0].start;
    assert_eq!(check(&collision), refusal);
    let mut partial_overlap = proposed.clone();
    partial_overlap[1].start = proposed[0].end_exclusive - 1;
    assert_eq!(check(&partial_overlap), refusal);
    let mut out_of_source = proposed.clone();
    out_of_source[6].end_exclusive = 2049;
    assert_eq!(check(&out_of_source), refusal);
    let mut at_source_end = proposed.clone();
    at_source_end[6].start = 2048;
    at_source_end[6].end_exclusive = 2049;
    assert_eq!(check(&at_source_end), refusal);
    // Code/data reservations are independently validated against the *same*
    // proposed source length: moving the frame into any code cell refuses.
    assert_eq!(
        bind_source_locked_cfg_code_targets(
            &wire, 2048, 2047, GuestCodeProposals {
            code_blocks: &proposed,
            edge_pads: &pads,
        },
        ),
        Err(GuestCodePlacementError::TypedCfg(
            super::typed_cfg_adapter::TypedCfgAdapterError::GuestStateAllocation
        ))
    );
    let mut forged_wire = wire;
    forged_wire.push(0);
    assert!(matches!(
        bind_source_locked_cfg_code_targets(
            &forged_wire,
            2048,
            4096,
            GuestCodeProposals {
                code_blocks: &proposed,
                edge_pads: &pads,
            },
        ),
        Err(GuestCodePlacementError::TypedCfg(_))
    ));
}

#[test]
fn source_checksum_phi_edge_pads_reject_missing_forged_or_aliasing_entries() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeEdgeKind, GuestCodePlacementError, GuestCodeProposals,
        bind_source_locked_cfg_code_targets,
    };

    let wire = source_locked_checksum_wire().expect("original checksum source");
    let blocks = checksum_proposed_code_blocks();
    let pads = checksum_proposed_phi_edge_pads();
    let refusal = Err(GuestCodePlacementError::InvalidCodePlacement);
    let check = |candidate: &[_]| {
        bind_source_locked_cfg_code_targets(
            &wire,
            2048,
            4096,
            GuestCodeProposals {
                code_blocks: &blocks,
                edge_pads: candidate,
            },
        )
    };
    assert_eq!(check(&[]), refusal);
    let mut missing = pads.clone();
    assert!(missing.pop().is_some());
    assert_eq!(check(&missing), refusal);
    let mut duplicate = pads.clone();
    duplicate.push(pads[0]);
    assert_eq!(check(&duplicate), refusal);
    let mut foreign = pads.clone();
    foreign[0].predecessor = 2;
    assert_eq!(check(&foreign), refusal);
    let mut wrong_function = pads.clone();
    wrong_function[0].function = 100;
    assert_eq!(check(&wrong_function), refusal);
    let mut wrong_successor = pads.clone();
    wrong_successor[0].successor = 2;
    assert_eq!(check(&wrong_successor), refusal);
    let mut wrong_arm = pads.clone();
    wrong_arm[0].kind = GuestCodeEdgeKind::WhenTrue;
    assert_eq!(check(&wrong_arm), refusal);
    let mut no_writes = pads.clone();
    no_writes[0].predecessor = 1;
    no_writes[0].successor = 2;
    no_writes[0].kind = GuestCodeEdgeKind::WhenTrue;
    assert_eq!(check(&no_writes), refusal);
    // An extra pad on a phi-free branch is not justified by the CFG.
    let mut extra_pad = pads.clone();
    let mut spurious = pads[0];
    spurious.predecessor = 1;
    spurious.successor = 2;
    spurious.kind = GuestCodeEdgeKind::WhenTrue;
    spurious.start = 400;
    spurious.end_exclusive = 416;
    extra_pad.push(spurious);
    assert_eq!(check(&extra_pad), refusal);
    // Eight guest-memory writes require eight distinct pad cells, then at
    // least one more executable control transfer to enter the destination.
    // This applies to the source's initial phi edge and its real loop backedge.
    let mut missing_exit = pads.clone();
    missing_exit[0].end_exclusive = missing_exit[0].start + 8;
    assert_eq!(check(&missing_exit), refusal);
    let mut exact_pad_capacity = pads.clone();
    exact_pad_capacity[0].end_exclusive = exact_pad_capacity[0].start + 9;
    assert!(check(&exact_pad_capacity).is_ok());
    let mut short_backedge = pads.clone();
    short_backedge[3].end_exclusive = short_backedge[3].start + 8;
    assert_eq!(check(&short_backedge), refusal);
    let mut exact_backedge = pads.clone();
    exact_backedge[3].end_exclusive = exact_backedge[3].start + 9;
    assert!(check(&exact_backedge).is_ok());
    // Touching code and pad intervals do not overlap.
    let mut touching = pads.clone();
    touching[0].start = 240;
    touching[0].end_exclusive = 256;
    assert!(check(&touching).is_ok());
    let mut zero = pads.clone();
    zero[0].end_exclusive = zero[0].start;
    assert_eq!(check(&zero), refusal);
    let mut reversed = pads.clone();
    reversed[0].end_exclusive = reversed[0].start - 1;
    assert_eq!(check(&reversed), refusal);
    let mut overlapping_pad = pads.clone();
    overlapping_pad[1].start = pads[0].end_exclusive - 1;
    assert_eq!(check(&overlapping_pad), refusal);
    let mut overlapping_block = pads.clone();
    overlapping_block[1].start = blocks[3].start;
    assert_eq!(check(&overlapping_block), refusal);
    let mut outside = pads.clone();
    outside[3].end_exclusive = 2049;
    assert_eq!(check(&outside), refusal);
    let mut end_boundary = pads.clone();
    end_boundary[3].start = 2048;
    end_boundary[3].end_exclusive = 2049;
    assert_eq!(check(&end_boundary), refusal);
}

#[test]
fn source_checksum_relocates_operation_control_and_phi_cells() {
    assert_eq!(prove_source_checksum_relocation(), Ok(()));
}

fn assert_checksum_relocation_refusals(wire: &[u8]) {
    use super::typed_cfg_adapter::TypedCfgAdapterError;
    use super::typed_cfg_adapter::state_relocation::relocate_source_locked_cfg;
    use super::typed_cfg_adapter::state_storage::CURRENT_WORD_COUNT;

    let refusal = Err(TypedCfgAdapterError::GuestStateAllocation);
    assert_eq!(relocate_source_locked_cfg(wire, 2048, 2047), refusal);
    assert_eq!(relocate_source_locked_cfg(wire, 0, 4096), refusal);
    assert_eq!(relocate_source_locked_cfg(wire, 1, 4096), refusal);
    assert_eq!(
        relocate_source_locked_cfg(wire, CURRENT_WORD_COUNT, 4096),
        refusal
    );
    assert_eq!(
        relocate_source_locked_cfg(wire, 2048, CURRENT_WORD_COUNT - 42),
        refusal
    );
}

fn prove_checksum_relocation_limits() -> Result<(), String> {
    use super::typed_cfg_adapter::state_relocation::relocate_source_locked_cfg;
    use super::typed_cfg_adapter::state_storage::CURRENT_WORD_COUNT;

    let mut wire = source_locked_checksum_wire()?;
    assert_checksum_relocation_refusals(&wire);
    let last = relocate_source_locked_cfg(&wire, 2048, CURRENT_WORD_COUNT - 43)
        .map_err(|error| {
            format!("last valid checksum relocation refused: {error:?}")
        })?;
    assert_last_checksum_relocation_address(&last);
    wire.push(0);
    assert_corrupted_checksum_refusal(&wire);
    Ok(())
}

fn assert_last_checksum_relocation_address(placed: &GuestRelocatedCfgPlan) {
    use super::typed_cfg_adapter::state_storage::CURRENT_WORD_COUNT;
    assert_eq!(
        placed
            .state_placements
            .first()
            .map(|place| place.end_exclusive),
        Some(CURRENT_WORD_COUNT)
    );
}

fn assert_corrupted_checksum_refusal(wire: &[u8]) {
    use super::typed_cfg_adapter::state_relocation::relocate_source_locked_cfg;
    assert!(relocate_source_locked_cfg(wire, 2048, 4096).is_err());
}

#[test]
fn source_checksum_relocation_refuses_code_collision_and_memory_wrap() {
    assert_eq!(prove_checksum_relocation_limits(), Ok(()));
}

// A narrow local can cross a real CFG merge without widening its original
// C type or claiming that a physical guest branch has been linked.
fn narrow_join_typed_module(
    kind: super::typed::TypeDef,
    width: u16,
    alternatives: [u16; 2],
) -> super::typed::Module {
    use super::typed::{
        BasicBlock, BasicBlockSpec, BlockId, Function, FunctionId,
        FunctionSpec, IntegerConstant, LocatedInstruction, Module, ModuleSpec,
        Phi, PhiIncoming, SourcePosition, SourceSpan, TypeDef, TypeEntry,
        TypeId, ValueId,
    };

    let span = |start: u32, end: u32| {
        SourceSpan::new(
            SourcePosition::new(start, 1, start + 1),
            SourcePosition::new(end, 1, end + 1),
        )
    };
    let literal = |result: u32, value: u16, at: u32| {
        LocatedInstruction::new(
            Instruction::ConstantInteger {
                constant: IntegerConstant::new(
                    width,
                    value.to_le_bytes()[..usize::from(width / 8)].to_vec(),
                ),
                result: ValueId::new(result),
                type_id: TypeId::new(1),
            },
            span(at, at + 1),
        )
    };
    let block = |id, instructions, phis, terminator| {
        BasicBlock::new(BasicBlockSpec {
            id: BlockId::new(id),
            instructions,
            phis,
            span: span(id * 2, id * 2 + 2),
            terminator,
            terminator_span: span(id * 2 + 1, id * 2 + 2),
        })
    };
    Module::new(ModuleSpec {
        abi_id: String::from("malbolge-c32-v1"),
        format_version: super::typed::TYPED_IR_VERSION,
        functions: vec![Function::new(FunctionSpec {
            blocks: vec![
                block(
                    0,
                    vec![LocatedInstruction::new(
                        Instruction::ConstantInteger {
                            constant: IntegerConstant::new(1, vec![1]),
                            result: ValueId::new(0),
                            type_id: TypeId::new(0),
                        },
                        span(0, 1),
                    )],
                    Vec::new(),
                    Terminator::Branch {
                        condition: ValueId::new(0),
                        false_target: BlockId::new(2),
                        true_target: BlockId::new(1),
                    },
                ),
                block(
                    1,
                    vec![literal(1, alternatives[0], 2)],
                    Vec::new(),
                    Terminator::Jump { target: BlockId::new(3) },
                ),
                block(
                    2,
                    vec![literal(2, alternatives[1], 4)],
                    Vec::new(),
                    Terminator::Jump { target: BlockId::new(3) },
                ),
                block(
                    3,
                    Vec::new(),
                    vec![Phi::new(
                        ValueId::new(3),
                        TypeId::new(1),
                        vec![
                            PhiIncoming::new(BlockId::new(1), ValueId::new(1)),
                            PhiIncoming::new(BlockId::new(2), ValueId::new(2)),
                        ],
                        span(6, 7),
                    )],
                    Terminator::Return {
                        value: Some(ValueId::new(3)),
                    },
                ),
            ],
            entry: BlockId::new(0),
            id: FunctionId::new(0),
            name: String::from("narrow_join"),
            parameters: Vec::new(),
            signature: TypeId::new(2),
            span: span(0, 8),
        })],
        globals: Vec::new(),
        proof_obligations: Vec::new(),
        source_id: String::from("fixtures/narrow-join.c"),
        source_sha256: [0x53; 32],
        target_profile: String::from("malbolge-2026"),
        types: vec![
            TypeEntry::new(TypeId::new(0), TypeDef::Bool),
            TypeEntry::new(TypeId::new(1), kind),
            TypeEntry::new(
                TypeId::new(2),
                TypeDef::function(Vec::new(), Some(TypeId::new(1)), false),
            ),
        ],
    })
}

#[test]
fn narrow_signed_and_unsigned_phi_joins_preserve_guest_storage_widths() {
    use super::typed::{TypeDef, canonical_bytes, validate_module};
    use super::typed_cfg_adapter::prepare_canonical_dynamic_cfg;
    use super::typed_cfg_adapter::state_relocation::{
        plan_source_locked_cfg_minimum_code_targets,
        relocate_source_locked_cfg, source_locked_cfg_minimum_code_cells,
    };
    use super::typed_cfg_adapter::ternary::TernaryCfgScalarKind;

    for (kind, width, alternatives, target) in [
        (TypeDef::I8, 8, [0x80, 0x7f], TernaryCfgScalarKind::I8),
        (
            TypeDef::I16,
            16,
            [0x8000, 0x7fff],
            TernaryCfgScalarKind::I16,
        ),
        (TypeDef::U16, 16, [0xffff, 0x100], TernaryCfgScalarKind::U16),
    ] {
        let module = narrow_join_typed_module(kind, width, alternatives);
        validate_module(&module).expect("valid narrow typed CFG");
        let wire = canonical_bytes(&module).expect("canonical typed CFG");
        assert_eq!(canonical_module(&wire), Ok(module));
        // Narrow scalar source branches need seven minimum block cells and
        // two three-cell phi pads. Do not widen them to C32 reservations.
        assert_eq!(source_locked_cfg_minimum_code_cells(&wire), Ok(13));
        let compact =
            plan_source_locked_cfg_minimum_code_targets(&wire, 20, 64, 0)
                .expect("narrow source-linked minimum physical obligations");
        assert_eq!(compact.operation_effect_sites.len(), 3);
        assert_eq!(compact.code_blocks.len(), 4);
        assert_eq!(compact.edge_pads.len(), 2);
        assert_eq!(compact.edge_pads[0].start, 7);
        assert_eq!(compact.edge_pads[1].end_exclusive, 13);
        assert!(
            compact
                .edge_pads
                .iter()
                .all(|pad| { pad.end_exclusive - pad.start == 3 })
        );
        let prepared = prepare_canonical_dynamic_cfg(&wire)
            .expect("narrow phi must preserve original width");
        let [frame] = prepared.state_frames.as_slice() else {
            panic!("one source CFG frame");
        };
        assert_eq!(frame.values.len(), 4);
        assert_eq!(frame.values[3].type_kind, target);
        assert!(frame.values.iter().all(|slot| slot.words == 1));
        assert_eq!(
            (frame.scratch_offset, frame.scratch_words, frame.total_words),
            (4, 1, 5)
        );
        assert_eq!(prepared.phi_edges.len(), 2);
        assert_eq!(prepared.cell_edges.len(), 2);
        for edge in &prepared.cell_edges {
            assert_eq!(edge.snapshots.len(), 1);
            assert_eq!(edge.commits.len(), 1);
            assert_eq!(edge.commits[0].destination, 3);
        }
        let literal_words = prepared
            .operation_blocks
            .iter()
            .flat_map(|block| &block.instructions)
            .flat_map(|instruction| &instruction.constant_cells)
            .map(|cell| cell.word)
            .collect::<Vec<_>>();
        assert_eq!(literal_words, vec![
            1,
            u32::from(alternatives[0]),
            u32::from(alternatives[1])
        ]);
        assert_eq!(prepare_canonical_dynamic_cfg(&wire), Ok(prepared));
        // These are exact data obligations, never guest instructions.
        let relocated = relocate_source_locked_cfg(&wire, 91, 128)
            .expect("narrow phi can be placed beyond the guest source");
        assert_eq!(relocated.state_placements.len(), 1);
        assert_eq!(relocated.state_placements[0].base, 128);
        assert_eq!(relocated.state_placements[0].end_exclusive, 133);
        assert_eq!(relocated.phi_edges.len(), 2);
        for edge in &relocated.phi_edges {
            assert_eq!(edge.snapshots.len(), 1);
            assert_eq!(edge.commits.len(), 1);
            assert_eq!(edge.snapshots[0].destination, 132);
            assert_eq!(edge.commits[0].source, 132);
            assert_eq!(edge.commits[0].destination, 131);
        }
        let physical_literals = relocated
            .operation_blocks
            .iter()
            .flat_map(|block| &block.instructions)
            .flat_map(|instruction| &instruction.constant_cells)
            .map(|cell| (cell.address, cell.word))
            .collect::<Vec<_>>();
        assert_eq!(physical_literals, vec![
            (128, 1),
            (129, u32::from(alternatives[0])),
            (130, u32::from(alternatives[1])),
        ]);
        // Signed and unsigned narrow values are one *typed* guest word,
        // while the Boolean condition stays separate from the phi result.
        let [entry, first, second, joined] =
            relocated.operation_blocks.as_slice()
        else {
            panic!("narrow diamond has four placed blocks");
        };
        let boolean = entry.condition.expect("actual Boolean branch");
        assert_eq!(
            (boolean.address, boolean.words, boolean.value),
            (128, 1, 0)
        );
        assert_eq!(boolean.type_kind, TernaryCfgScalarKind::Bool);
        assert_eq!(boolean.cell_address(1), None);
        for (block, address, value) in [(first, 129, 1), (second, 130, 2)] {
            let literal = &block.instructions[0];
            let slot = literal.write.expect("one narrow literal");
            assert_eq!(
                (slot.address, slot.words, slot.value),
                (address, 1, value)
            );
            assert_eq!(slot.type_kind, target);
            assert_eq!(slot.cell_address(0), Some(address));
            assert_eq!(slot.cell_address(1), None);
        }
        let result = joined.return_value.expect("narrow phi return");
        assert_eq!((result.address, result.words, result.value), (131, 1, 3));
        assert_eq!(result.type_kind, target);
        assert_eq!(relocate_source_locked_cfg(&wire, 91, 128), Ok(relocated));
    }
}

#[test]
fn narrow_phi_rejects_invalid_constant_width_and_storage_overlap() {
    use super::typed::{TypeDef, canonical_bytes, validate_module};
    use super::typed_cfg_adapter::TypedCfgAdapterError;
    use super::typed_cfg_adapter::state_relocation::relocate_source_locked_cfg;

    for (kind, wrong_width) in
        [(TypeDef::I8, 16), (TypeDef::I16, 8), (TypeDef::U16, 8)]
    {
        let mismatched = narrow_join_typed_module(kind, wrong_width, [1, 2]);
        assert!(validate_module(&mismatched).is_err());
        assert!(canonical_bytes(&mismatched).is_err());
    }
    let valid = narrow_join_typed_module(TypeDef::I16, 16, [0x8000, 0x7fff]);
    let wire =
        canonical_bytes(&valid).expect("valid source-based typed witness");
    let rejected = Err(TypedCfgAdapterError::GuestStateAllocation);
    assert_eq!(relocate_source_locked_cfg(&wire, 91, 90), rejected);
    let touching = relocate_source_locked_cfg(&wire, 91, 91)
        .expect("a frame may begin immediately after the full source");
    assert_eq!(touching.state_placements[0].end_exclusive, 96);
    assert_eq!(
        relocate_source_locked_cfg(&wire, 91, 92)
            .expect("adjacent non-overlapping data placement")
            .state_placements[0]
            .base,
        92,
    );
}

#[test]
fn source_checksum_code_sites_bind_real_arithmetic_operands() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeComputation, GuestCodeProposals,
        bind_source_locked_cfg_code_targets,
    };
    use super::typed_cfg_adapter::typed::Instruction as PlacedInstruction;

    let wire = source_locked_checksum_wire().expect("original C23 source");
    let blocks = checksum_proposed_code_blocks();
    let pads = checksum_proposed_phi_edge_pads();
    let plan = bind_source_locked_cfg_code_targets(
        &wire,
        2048,
        4096,
        GuestCodeProposals {
            code_blocks: &blocks,
            edge_pads: &pads,
        },
    )
    .expect("source-authenticated operation and code placements");
    let mut arithmetic = 0usize;
    let mut comparisons = 0usize;
    let mut conversions = 0usize;
    for block in &plan.relocated.operation_blocks {
        for (ordinal, original) in block.instructions.iter().enumerate() {
            let site = plan
                .operation_sites
                .iter()
                .find(|site| {
                    (site.function, site.block, site.ordinal)
                        == (
                            block.function,
                            block.block,
                            u32::try_from(ordinal).unwrap(),
                        )
                })
                .expect("source operation has code site");
            match (&original.instruction, site.computation) {
                (
                    PlacedInstruction::Binary {
                        left, operation, right, ..
                    },
                    Some(GuestCodeComputation::Binary {
                        operation: bound_operation,
                        left: bound_left,
                        right: bound_right,
                        result,
                    }),
                ) => {
                    assert_eq!(*operation, bound_operation);
                    assert_eq!(original.reads, vec![bound_left, bound_right]);
                    assert_eq!(original.write, Some(result));
                    assert_eq!(
                        (left.value(), right.value()),
                        (bound_left.value, bound_right.value)
                    );
                    arithmetic += 1;
                },
                (
                    PlacedInstruction::Compare {
                        left, operation, right, ..
                    },
                    Some(GuestCodeComputation::Compare {
                        operation: bound_operation,
                        left: bound_left,
                        right: bound_right,
                        result,
                    }),
                ) => {
                    assert_eq!(*operation, bound_operation);
                    assert_eq!(original.reads, vec![bound_left, bound_right]);
                    assert_eq!(original.write, Some(result));
                    assert_eq!(
                        (left.value(), right.value()),
                        (bound_left.value, bound_right.value)
                    );
                    assert_eq!(result.words, 1);
                    comparisons += 1;
                },
                (
                    PlacedInstruction::Cast { operation, value, .. },
                    Some(GuestCodeComputation::Cast {
                        operation: bound_operation,
                        source,
                        result,
                    }),
                ) => {
                    assert_eq!(*operation, bound_operation);
                    assert_eq!(original.reads, vec![source]);
                    assert_eq!(original.write, Some(result));
                    assert_eq!(value.value(), source.value);
                    conversions += 1;
                },
                (
                    PlacedInstruction::Binary { .. }
                    | PlacedInstruction::Compare { .. }
                    | PlacedInstruction::Cast { .. },
                    _,
                ) => {
                    panic!("guest computation lost source operands");
                },
                (_, None) => {},
                (_, Some(_)) => panic!("unrelated operation has computation"),
            }
        }
    }
    assert_eq!(arithmetic, 5, "xor/add/and all require guest computation");
    assert_eq!(comparisons, 2, "both C23 guards require guest comparison");
    assert!(conversions > 0, "source casts cannot be pre-evaluated");
}

#[test]
fn source_checksum_sparse_phi_copy_anchors_preserve_exact_two_phase_edges() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeEdgeKind, GuestCodePhiCopyAnchor, GuestCodePhiCopyPlacement,
        GuestCodePlacementError, GuestCodeProposals,
        bind_source_locked_cfg_code_targets_with_phi_copy_anchors,
    };

    let wire = source_locked_checksum_wire().expect("pinned C23 checksum");
    let blocks = checksum_proposed_code_blocks();
    let pads = checksum_proposed_phi_edge_pads();
    let proposals = GuestCodeProposals {
        code_blocks: &blocks,
        edge_pads: &pads,
    };
    let locations = [338, 341, 344, 349, 354, 359, 363, 371];
    let anchors = locations
        .into_iter()
        .enumerate()
        .map(|(copy_index, code_address)| GuestCodePhiCopyAnchor {
            code_address,
            copy_index: u32::try_from(copy_index).expect("eight copies"),
            function: 0,
            kind: GuestCodeEdgeKind::Jump,
            predecessor: 5,
            successor: 1,
        })
        .collect::<Vec<_>>();
    let bind = |candidate: &[_]| {
        bind_source_locked_cfg_code_targets_with_phi_copy_anchors(
            GuestCodePhiCopyPlacement {
                canonical: &wire,
                source_cells: 2048,
                frame_base: 4096,
                proposals,
                operation_anchors: &[],
                effect_anchors: &[],
                phi_anchors: candidate,
            },
        )
    };
    let sparse = bind(&anchors).expect("sparse phi sites preserve typed edge");
    let original = bind(&[]).expect("old compact site defaults");
    assert_eq!(sparse.relocated, original.relocated);
    assert_eq!(sparse.code_blocks, original.code_blocks);
    assert_eq!(
        sparse.operation_effect_sites,
        original.operation_effect_sites
    );
    assert_eq!(sparse.control_edges.len(), original.control_edges.len());
    for (before, after) in
        original.control_edges.iter().zip(&sparse.control_edges)
    {
        assert_eq!(before.snapshots, after.snapshots);
        assert_eq!(before.commits, after.commits);
        assert_eq!(before.entry_address, after.entry_address);
        assert_eq!(before.pad_exit_address, after.pad_exit_address);
        if before.predecessor != 5 {
            assert_eq!(before, after);
        }
    }
    let changed = sparse
        .control_edges
        .iter()
        .find(|edge| (edge.predecessor, edge.successor) == (5, 1))
        .expect("source backedge");
    assert_eq!(
        changed
            .snapshot_sites
            .iter()
            .chain(&changed.commit_sites)
            .map(|site| site.code_address)
            .collect::<Vec<_>>(),
        locations
    );
    assert_eq!(changed.pad_exit_address, Some(375));
    let mut shuffled = anchors.clone();
    shuffled.reverse();
    assert_eq!(bind(&shuffled), Ok(sparse));

    let refuses = Err(GuestCodePlacementError::InvalidCodePlacement);
    let mut incomplete = anchors.clone();
    assert!(incomplete.pop().is_some());
    assert_eq!(bind(&incomplete), refuses);
    let mut duplicate = anchors.clone();
    duplicate.push(anchors[0]);
    assert_eq!(bind(&duplicate), refuses);
    for forged in [
        GuestCodePhiCopyAnchor {
            copy_index: 8,
            ..anchors[0]
        },
        GuestCodePhiCopyAnchor {
            function: 1,
            ..anchors[0]
        },
        GuestCodePhiCopyAnchor {
            predecessor: 4,
            ..anchors[0]
        },
        GuestCodePhiCopyAnchor {
            successor: 5,
            ..anchors[0]
        },
        GuestCodePhiCopyAnchor {
            kind: GuestCodeEdgeKind::WhenTrue,
            ..anchors[0]
        },
        GuestCodePhiCopyAnchor {
            code_address: 335,
            ..anchors[0]
        },
        GuestCodePhiCopyAnchor {
            code_address: 375,
            ..anchors[0]
        },
        GuestCodePhiCopyAnchor {
            code_address: 271,
            ..anchors[0]
        },
    ] {
        let mut changed = anchors.clone();
        changed[0] = forged;
        assert_eq!(bind(&changed), refuses, "forged anchor: {forged:?}");
    }
    let mut alias = anchors.clone();
    alias[1].code_address = alias[0].code_address;
    assert_eq!(bind(&alias), refuses);
    let mut reverse = anchors.clone();
    reverse[1].code_address = 337;
    assert_eq!(bind(&reverse), refuses);
}

// A physical trace can reveal the first signed result-store positions before
// its earlier input opcode has been linked. General source-CFG placement must
// honor those complete, source-typed effects without inventing an input site.
// The narrower input-only planner still demands the explicit input anchor.
#[test]
fn original_checksum_auto_places_signed_stores_without_input_op_anchors() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeEffectAnchor, GuestCodeOperationEffect,
        GuestCodePlacementError,
        plan_source_locked_cfg_with_operation_and_effect_anchors,
    };

    let wire = source_locked_checksum_wire().expect("original C23 checksum");
    let effects = [
        GuestCodeEffectAnchor {
            function: 0,
            block: 0,
            ordinal: 1,
            effect_index: 1,
            code_address: 40,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 0,
            ordinal: 1,
            effect_index: 2,
            code_address: 42,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 5,
            ordinal: 2,
            effect_index: 1,
            code_address: 69,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 5,
            ordinal: 2,
            effect_index: 2,
            code_address: 71,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 3,
            ordinal: 0,
            effect_index: 0,
            code_address: 180,
        },
        GuestCodeEffectAnchor {
            function: 0,
            block: 3,
            ordinal: 0,
            effect_index: 1,
            code_address: 190,
        },
    ];
    let plan = plan_source_locked_cfg_with_operation_and_effect_anchors(
        &wire,
        256,
        512,
        &[],
        &effects,
    )
    .expect("typed stores alone should reserve earlier source read effects");
    assert_eq!(plan.code_blocks.len(), 7);
    assert_eq!(plan.edge_pads.len(), 4);
    for anchor in effects {
        assert!(plan.operation_effect_sites.iter().any(|site| {
            (site.function, site.block, site.ordinal, site.code_address)
                == (
                    anchor.function,
                    anchor.block,
                    anchor.ordinal,
                    anchor.code_address,
                )
                && matches!(site.effect, GuestCodeOperationEffect::Store { .. })
        }));
    }
    let first = plan
        .operation_effect_sites
        .iter()
        .find(|site| {
            site.block == 0
                && site.ordinal == 1
                && matches!(site.effect, GuestCodeOperationEffect::Input { .. })
        })
        .expect("unanchored earlier signed input effect");
    assert!(first.code_address < 40);
    assert_eq!(plan.function_entries[0].address, plan.code_blocks[0].start);

    let arithmetic = plan.operation_sites.iter().find(|site| {
        site.block == 3 && site.ordinal == 0 && site.computation.is_some()
    });
    assert_eq!(arithmetic.map(|site| site.start), Some(180));

    let invalid = Err(GuestCodePlacementError::InvalidCodePlacement);
    let mut unknown = effects;
    unknown[0].effect_index = 3;
    assert_eq!(
        plan_source_locked_cfg_with_operation_and_effect_anchors(
            &wire,
            256,
            512,
            &[],
            &unknown,
        ),
        invalid,
        "a source read has exactly three effects",
    );
    unknown = effects;
    unknown[1].code_address = 39;
    assert_eq!(
        plan_source_locked_cfg_with_operation_and_effect_anchors(
            &wire,
            256,
            512,
            &[],
            &unknown,
        ),
        invalid,
        "signed store effects retain physical source order",
    );
}

// A reached source phi pad may require real pointer-setup instructions after
// its final p/* memory copy and before its successor i. Pinning the transfer
// site must not force that setup interval into another source block or pad.
// All sites remain code reservations, never executable C23 guest claims.
#[test]
fn original_checksum_phi_exit_anchor_reserves_post_commit_guest_setup() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeEdgeKind, GuestCodeOperationAnchor, GuestCodePhiCopyAnchor,
        GuestCodePhiExitAnchor, GuestCodePlacementError,
        plan_source_locked_cfg_with_operation_effect_control_and_phi_anchors,
        plan_source_locked_cfg_with_phi_exit_anchors,
    };

    let wire =
        source_locked_checksum_wire().expect("original C23 EOF checksum");
    let positions = [90, 97, 105, 114, 123, 131, 140, 150];
    let copies = positions
        .into_iter()
        .enumerate()
        .map(|(copy_index, code_address)| GuestCodePhiCopyAnchor {
            code_address,
            copy_index: u32::try_from(copy_index)
                .expect("eight backedge copies"),
            function: 0,
            kind: GuestCodeEdgeKind::Jump,
            predecessor: 5,
            successor: 1,
        })
        .collect::<Vec<_>>();
    let exits = [GuestCodePhiExitAnchor {
        code_address: 170,
        function: 0,
        kind: GuestCodeEdgeKind::Jump,
        predecessor: 5,
        successor: 1,
    }];
    let bind = |operation: &[GuestCodeOperationAnchor],
                exits: &[GuestCodePhiExitAnchor]| {
        plan_source_locked_cfg_with_phi_exit_anchors(
            &wire,
            256,
            512,
            operation,
            &[],
            &[],
            &copies,
            exits,
        )
    };
    let placed = bind(&[], &exits)
        .expect("source-authenticated post-commit setup and exit fit");
    let pad = placed
        .edge_pads
        .iter()
        .find(|pad| (pad.function, pad.predecessor, pad.successor) == (0, 5, 1))
        .expect("one original checksum backedge pad");
    assert_eq!((pad.start, pad.end_exclusive), (90, 171));
    let edge = placed
        .control_edges
        .iter()
        .find(|edge| {
            (edge.function, edge.predecessor, edge.successor) == (0, 5, 1)
        })
        .expect("source C23 backedge");
    assert_eq!(edge.pad_exit_address, Some(170));
    assert_eq!(
        edge.snapshot_sites
            .iter()
            .chain(&edge.commit_sites)
            .map(|copy| copy.code_address)
            .collect::<Vec<_>>(),
        positions
    );
    assert_eq!(placed.code_blocks.len(), 7);
    assert_eq!(placed.edge_pads.len(), 4);

    let compact =
        plan_source_locked_cfg_with_operation_effect_control_and_phi_anchors(
            &wire,
            256,
            512,
            &[],
            &[],
            &[],
            &copies,
        )
        .expect("existing compact source-backedge API still works");
    assert_eq!(
        compact
            .control_edges
            .iter()
            .find(|edge| {
                (edge.function, edge.predecessor, edge.successor) == (0, 5, 1)
            })
            .and_then(|edge| edge.pad_exit_address),
        Some(151)
    );
    let refusal = Err(GuestCodePlacementError::InvalidCodePlacement);
    for wrong in [
        GuestCodePhiExitAnchor {
            code_address: 150,
            ..exits[0]
        },
        GuestCodePhiExitAnchor {
            code_address: 149,
            ..exits[0]
        },
        GuestCodePhiExitAnchor {
            code_address: 256,
            ..exits[0]
        },
        GuestCodePhiExitAnchor {
            predecessor: 4,
            ..exits[0]
        },
        GuestCodePhiExitAnchor {
            kind: GuestCodeEdgeKind::WhenTrue,
            ..exits[0]
        },
        GuestCodePhiExitAnchor { successor: 2, ..exits[0] },
    ] {
        assert_eq!(bind(&[], &[wrong]), refusal, "invalid exit: {wrong:?}");
    }
    assert_eq!(bind(&[], &[exits[0], exits[0]]), refusal);
    assert_eq!(
        plan_source_locked_cfg_with_phi_exit_anchors(
            &wire,
            256,
            512,
            &[],
            &[],
            &[],
            &[],
            &exits,
        ),
        refusal,
        "exit-only pad without all anchored copy sites must refuse",
    );
    let block = [GuestCodeOperationAnchor {
        function: 0,
        block: 3,
        ordinal: 0,
        code_address: 180,
    }];
    assert_eq!(
        bind(&block, &[GuestCodePhiExitAnchor {
            code_address: 190,
            ..exits[0]
        }]),
        refusal,
        "guest setup may not overlap another source block"
    );
}

// Before a phi snapshot can physically execute p/*, its predecessor-owned pad
// may need guest pointer setup. The predecessor must land at the setup entry,
// not skip directly to the first copy. These are address obligations only.
#[test]
fn original_checksum_phi_entry_anchor_reserves_pre_snapshot_guest_setup() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeEdgeKind, GuestCodeOperationAnchor, GuestCodePhiCopyAnchor,
        GuestCodePhiEntryAnchor, GuestCodePhiExitAnchor,
        GuestCodePlacementError,
        plan_source_locked_cfg_with_phi_boundary_anchors,
        plan_source_locked_cfg_with_phi_exit_anchors,
    };

    let wire =
        source_locked_checksum_wire().expect("original C23 EOF checksum");
    let positions = [90, 97, 105, 114, 123, 131, 140, 150];
    let copies = positions
        .into_iter()
        .enumerate()
        .map(|(copy_index, code_address)| GuestCodePhiCopyAnchor {
            code_address,
            copy_index: u32::try_from(copy_index)
                .expect("eight backedge writes"),
            function: 0,
            kind: GuestCodeEdgeKind::Jump,
            predecessor: 5,
            successor: 1,
        })
        .collect::<Vec<_>>();
    let entry = GuestCodePhiEntryAnchor {
        code_address: 80,
        function: 0,
        kind: GuestCodeEdgeKind::Jump,
        predecessor: 5,
        successor: 1,
    };
    let exit = GuestCodePhiExitAnchor {
        code_address: 170,
        function: 0,
        kind: GuestCodeEdgeKind::Jump,
        predecessor: 5,
        successor: 1,
    };
    let bind = |operations: &[GuestCodeOperationAnchor],
                copies: &[GuestCodePhiCopyAnchor],
                entries: &[GuestCodePhiEntryAnchor],
                exits: &[GuestCodePhiExitAnchor]| {
        plan_source_locked_cfg_with_phi_boundary_anchors(
            &wire,
            256,
            512,
            operations,
            &[],
            &[],
            copies,
            entries,
            exits,
        )
    };
    let plan = bind(&[], &copies, &[entry], &[exit])
        .expect("the source-owned pad retains pointer setup at both ends");
    let pad = plan
        .edge_pads
        .iter()
        .find(|pad| (pad.function, pad.predecessor, pad.successor) == (0, 5, 1))
        .expect("checked loop backedge pad");
    assert_eq!((pad.start, pad.end_exclusive), (80, 171));
    let edge = plan
        .control_edges
        .iter()
        .find(|edge| {
            (edge.function, edge.predecessor, edge.successor) == (0, 5, 1)
        })
        .expect("checked source control edge");
    assert_eq!((edge.entry_address, edge.pad_exit_address), (80, Some(170)));
    assert_eq!(
        edge.snapshot_sites
            .iter()
            .chain(&edge.commit_sites)
            .map(|copy| copy.code_address)
            .collect::<Vec<_>>(),
        positions,
    );
    assert_eq!(plan.code_blocks.len(), 7);
    assert_eq!(plan.edge_pads.len(), 4);
    let entry_only = bind(&[], &copies, &[entry], &[])
        .expect("an explicit entry also permits the ordinary compact exit");
    let compact_pad = entry_only
        .edge_pads
        .iter()
        .find(|pad| (pad.function, pad.predecessor, pad.successor) == (0, 5, 1))
        .expect("same source backedge without an exit override");
    assert_eq!((compact_pad.start, compact_pad.end_exclusive), (80, 152));
    let compact_edge = entry_only
        .control_edges
        .iter()
        .find(|edge| {
            (edge.function, edge.predecessor, edge.successor) == (0, 5, 1)
        })
        .expect("same source control edge without an exit override");
    assert_eq!(
        (compact_edge.entry_address, compact_edge.pad_exit_address),
        (80, Some(151))
    );
    assert_eq!(
        compact_edge
            .snapshot_sites
            .iter()
            .chain(&compact_edge.commit_sites)
            .map(|copy| copy.code_address)
            .collect::<Vec<_>>(),
        positions,
    );
    assert_eq!(
        bind(&[], &copies, &[], &[exit])
            .expect("old exit-only boundary remains supported")
            .edge_pads,
        plan_source_locked_cfg_with_phi_exit_anchors(
            &wire,
            256,
            512,
            &[],
            &[],
            &[],
            &copies,
            &[exit],
        )
        .expect("legacy exit-only API remains supported")
        .edge_pads,
    );
    assert_eq!(
        bind(
            &[],
            &copies,
            &[GuestCodePhiEntryAnchor {
                code_address: 90,
                ..entry
            }],
            &[exit]
        )
        .map(|plan| plan.edge_pads),
        plan_source_locked_cfg_with_phi_exit_anchors(
            &wire,
            256,
            512,
            &[],
            &[],
            &[],
            &copies,
            &[exit],
        )
        .map(|plan| plan.edge_pads),
        "an entry exactly at the first copy preserves old reservations",
    );
    let refusal = Err(GuestCodePlacementError::InvalidCodePlacement);
    for wrong in [
        GuestCodePhiEntryAnchor {
            code_address: 91,
            ..entry
        },
        GuestCodePhiEntryAnchor {
            code_address: 171,
            ..entry
        },
        GuestCodePhiEntryAnchor {
            code_address: 256,
            ..entry
        },
        GuestCodePhiEntryAnchor { predecessor: 4, ..entry },
        GuestCodePhiEntryAnchor {
            kind: GuestCodeEdgeKind::WhenFalse,
            ..entry
        },
        GuestCodePhiEntryAnchor { successor: 2, ..entry },
    ] {
        assert_eq!(bind(&[], &copies, &[wrong], &[exit]), refusal);
    }
    assert_eq!(bind(&[], &copies, &[entry, entry], &[exit]), refusal);
    assert_eq!(bind(&[], &[], &[entry], &[exit]), refusal);
    let occupied = [GuestCodeOperationAnchor {
        function: 0,
        block: 3,
        ordinal: 0,
        code_address: 83,
    }];
    assert_eq!(bind(&occupied, &copies, &[entry], &[exit]), refusal);
}

// Real Malbolge execution starts at C0. Sparse input/effect anchors alone
// must not silently move the canonical C function entry to a later cell.
// This remains a code reservation, never evidence of a reached C23 loop.
#[test]
fn original_checksum_can_pin_function_entry_before_sparse_input_setup() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodeControlAnchor, GuestCodeEdgeKind, GuestCodeEffectAnchor,
        GuestCodeFunctionEntryAnchor, GuestCodeFunctionEntryPlacement,
        GuestCodeOperationAnchor, GuestCodePhiCopyAnchor,
        GuestCodePhiEntryAnchor, GuestCodePhiExitAnchor,
        GuestCodePlacementError,
        plan_source_locked_cfg_with_function_entry_anchors,
        plan_source_locked_cfg_with_operation_effect_control_and_phi_anchors,
    };

    let wire = source_locked_checksum_wire().expect("unchanged C23 checksum");
    let operations = [
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 34,
            function: 0,
            ordinal: 0,
        },
        GuestCodeOperationAnchor {
            block: 0,
            code_address: 37,
            function: 0,
            ordinal: 1,
        },
        GuestCodeOperationAnchor {
            block: 5,
            code_address: 66,
            function: 0,
            ordinal: 2,
        },
    ];
    let effects = [
        GuestCodeEffectAnchor {
            block: 0,
            code_address: 40,
            effect_index: 1,
            function: 0,
            ordinal: 1,
        },
        GuestCodeEffectAnchor {
            block: 0,
            code_address: 42,
            effect_index: 2,
            function: 0,
            ordinal: 1,
        },
        GuestCodeEffectAnchor {
            block: 5,
            code_address: 69,
            effect_index: 1,
            function: 0,
            ordinal: 2,
        },
        GuestCodeEffectAnchor {
            block: 5,
            code_address: 71,
            effect_index: 2,
            function: 0,
            ordinal: 2,
        },
    ];
    let controls = [
        GuestCodeControlAnchor {
            block: 0,
            code_address: 60,
            function: 0,
        },
        GuestCodeControlAnchor {
            block: 5,
            code_address: 75,
            function: 0,
        },
    ];
    let entry = GuestCodeFunctionEntryAnchor {
        block: 0,
        code_address: 0,
        function: 0,
    };
    let bind = |entries: &[GuestCodeFunctionEntryAnchor]| {
        plan_source_locked_cfg_with_function_entry_anchors(
            GuestCodeFunctionEntryPlacement {
                canonical: &wire,
                source_cells: 256,
                frame_base: 512,
                operation_anchors: &operations,
                effect_anchors: &effects,
                control_anchors: &controls,
                phi_anchors: &[],
                phi_entries: &[],
                phi_exits: &[],
                function_entries: entries,
            },
        )
    };
    let unpinned =
        plan_source_locked_cfg_with_operation_effect_control_and_phi_anchors(
            &wire,
            256,
            512,
            &operations,
            &effects,
            &controls,
            &[],
        )
        .expect("existing sparse sites preserve their legacy start");
    assert_ne!(unpinned.function_entries[0].address, 0);

    let plan = bind(&[entry]).expect("real C0 source entry precedes C37 input");
    assert_eq!(plan.function_entries[0].address, 0);
    let first = &plan.code_blocks[0];
    assert_eq!((first.start, first.control_start), (0, 60));
    assert!(plan.operation_effect_sites.iter().any(|effect| {
        (effect.block, effect.ordinal, effect.code_address) == (0, 0, 34)
    }));
    assert_eq!(plan.operation_effect_sites
        .iter()
        .filter(|site| [37, 40, 42, 66, 69, 71].contains(&site.code_address))
        .count(), 6);
    assert_eq!(plan.edge_pads.len(), 4);
    assert_eq!(plan.control_edges.len(), 8);
    // The C0 function entry also composes with an independently placed,
    // predecessor-owned loop backedge. No fake source branch is selected.
    let positions = [90, 97, 105, 114, 123, 131, 140, 150];
    let phi = positions
        .into_iter()
        .enumerate()
        .map(|(copy_index, code_address)| GuestCodePhiCopyAnchor {
            code_address,
            copy_index: u32::try_from(copy_index).expect("eight copies"),
            function: 0,
            kind: GuestCodeEdgeKind::Jump,
            predecessor: 5,
            successor: 1,
        })
        .collect::<Vec<_>>();
    let phi_entry = GuestCodePhiEntryAnchor {
        code_address: 80,
        function: 0,
        kind: GuestCodeEdgeKind::Jump,
        predecessor: 5,
        successor: 1,
    };
    let phi_exit = GuestCodePhiExitAnchor {
        code_address: 170,
        function: 0,
        kind: GuestCodeEdgeKind::Jump,
        predecessor: 5,
        successor: 1,
    };
    let complete = plan_source_locked_cfg_with_function_entry_anchors(
        GuestCodeFunctionEntryPlacement {
            canonical: &wire,
            source_cells: 256,
            frame_base: 512,
            operation_anchors: &operations,
            effect_anchors: &effects,
            control_anchors: &controls,
            phi_anchors: &phi,
            phi_entries: &[phi_entry],
            phi_exits: &[phi_exit],
            function_entries: &[entry],
        },
    )
    .expect("entry, reads, stores and loop backedge fit disjoint code");
    assert_eq!(complete.function_entries[0].address, 0);
    let backedge = complete
        .control_edges
        .iter()
        .find(|edge| {
            (edge.function, edge.predecessor, edge.successor) == (0, 5, 1)
        })
        .expect("canonical checksum loop header");
    assert_eq!(
        (backedge.entry_address, backedge.pad_exit_address),
        (80, Some(170))
    );
    assert_eq!(
        backedge
            .snapshot_sites
            .iter()
            .chain(&backedge.commit_sites)
            .map(|site| site.code_address)
            .collect::<Vec<_>>(),
        positions,
    );
    assert_eq!(complete.edge_pads.len(), 4);
    assert_eq!(complete.control_edges.len(), 8);
    let mut intervals = complete
        .code_blocks
        .iter()
        .map(|block| (block.start, block.end_exclusive))
        .chain(
            complete
                .edge_pads
                .iter()
                .map(|pad| (pad.start, pad.end_exclusive)),
        )
        .collect::<Vec<_>>();
    intervals.sort_unstable();
    assert!(intervals.windows(2).all(|pair| pair[0].1 <= pair[1].0));
    assert_eq!(bind(&[]), Ok(unpinned));
    let rejected = Err(GuestCodePlacementError::InvalidCodePlacement);
    assert_eq!(bind(&[entry, entry]), rejected);
    for bad in [
        GuestCodeFunctionEntryAnchor { block: 5, ..entry },
        GuestCodeFunctionEntryAnchor { function: 3, ..entry },
        GuestCodeFunctionEntryAnchor {
            code_address: 38,
            ..entry
        },
        GuestCodeFunctionEntryAnchor {
            code_address: 256,
            ..entry
        },
    ] {
        assert_eq!(bind(&[bad]), rejected, "invalid function entry {bad:?}");
    }
    let mut reversed = [entry, entry];
    reversed[1].function = 17;
    assert_eq!(bind(&reversed), rejected);
}
