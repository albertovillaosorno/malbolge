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
    assert_eq!(addressed.edge_pads, pads);
    assert_eq!(addressed.relocated.operation_blocks.len(), 7);
    assert_eq!(addressed.control_edges.len(), 8);
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
        commits,
        condition,
        control_address,
        entry_address,
        function,
        kind,
        predecessor,
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
        assert_eq!(
            snapshots.as_slice(),
            phi.map_or(&[][..], |edge| &edge.snapshots)
        );
        assert_eq!(
            commits.as_slice(),
            phi.map_or(&[][..], |edge| &edge.commits)
        );
    }
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
fn source_checksum_code_entry_bindings_fail_closed_on_invalid_code_layout() {
    use super::typed_cfg_adapter::state_relocation::{
        GuestCodePlacementError, GuestCodeProposals,
        bind_source_locked_cfg_code_targets,
    };

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
    // A proposed control sequence may start at any cell *inside* its block;
    // the last cell is a fixture choice, not an artificial linker rule.
    let mut control_at_block_start = proposed.clone();
    control_at_block_start[2].control_start = proposed[2].start;
    assert!(check(&control_at_block_start).is_ok());
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
    // Every phi snapshot and commit must reserve a distinct destination
    // instruction slot, even before target code has been synthesized.
    let mut too_short_for_phi = pads.clone();
    too_short_for_phi[0].end_exclusive = too_short_for_phi[0].start + 7;
    assert_eq!(check(&too_short_for_phi), refusal);
    let mut exact_phi_capacity = pads.clone();
    exact_phi_capacity[0].end_exclusive = exact_phi_capacity[0].start + 8;
    assert!(check(&exact_phi_capacity).is_ok());
    let mut short_backedge = pads.clone();
    short_backedge[3].end_exclusive = short_backedge[3].start + 7;
    assert_eq!(check(&short_backedge), refusal);
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
    use super::typed_cfg_adapter::state_relocation::relocate_source_locked_cfg;
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
