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
