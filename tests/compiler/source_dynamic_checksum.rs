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
