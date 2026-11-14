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
//   - Source-backed finite induction short-circuit proof regressions.
// - Must-Not:
//   - Claim synthetic preorder nodes replace pinned frontend guest evidence.
// - Allows:
//   - Inputs: authenticated pure C expression trees and loop counter values.
//   - Outputs: source-time branch decisions or conservative refusals.
//   - Side effects: none.
// - Split-When:
//   - General dynamic C expression evaluation replaces static proof.
// - Merge-When:
//   - Normalized loop regression tests own the same lazy proof contract.
// - Summary:
//   - Unselected pure induction operands need no defined runtime value.
// - Description:
//   - Require source and node identity even for an overflowing skipped arm.
// - Usage:
//   - cargo test -p malbolge-c-frontend-json-adapter --lib induction_lazy
// - Defaults:
//   - Selected signed overflow rejects source-time branch projection.

use serde_json::json;

use super::{Node, StaticInduction, prove_induction_predicate};

fn node(
    id: u32,
    parent: u32,
    kind: &str,
    start: usize,
    end: usize,
    operation: Option<&str>,
    literal: Option<&str>,
    reference: Option<&str>,
) -> Node {
    serde_json::from_value(json!({
        "id": id,
        "parent": parent,
        "kind": kind,
        "type": "i32",
        "span": {
            "begin": {"byte": start, "line": 1, "column": start + 1},
            "end": {"byte": end, "line": 1, "column": end + 1}
        },
        "operation": operation,
        "literal": literal,
        "constant_integer": literal,
        "reference": reference
    }))
    .expect("synthetic source-proven Clang preorder node")
}

fn literal(id: u32, parent: u32, start: usize, spelling: &str) -> Node {
    node(
        id,
        parent,
        "integer-literal",
        start,
        start + spelling.len(),
        None,
        Some(spelling),
        None,
    )
}

fn counter_cast(id: u32, parent: u32, start: usize) -> Node {
    node(
        id,
        parent,
        "cast-expression",
        start,
        start + 1,
        Some("lvalue-to-rvalue"),
        None,
        None,
    )
}

fn counter_reference(id: u32, parent: u32, start: usize) -> Node {
    node(
        id,
        parent,
        "declaration-reference-expression",
        start,
        start + 1,
        None,
        None,
        Some("i@0"),
    )
}

fn guard(source: &str, nodes: &[Node], counter: i32) -> Option<(usize, bool)> {
    let if_node = node(1, 0, "if-statement", 0, source.len(), None, None, None);
    prove_induction_predicate(nodes, &if_node, StaticInduction {
        reference: "i@0",
        name: "i",
        source: Some(source.as_bytes()),
        value: counter,
    })
}

fn logical_guard(lhs: &str, op: &str) -> (String, Vec<Node>) {
    let source = format!("if (i {lhs} 0 {op} i + 2147483647 == 2147483647)");
    let left_start = 4;
    let left_end = source.find(&format!(" {op} ")).unwrap();
    let right_start = left_end + op.len() + 2;
    let arithmetic_end = right_start + "i + 2147483647".len();
    let right_end = source.len() - 1;
    let nodes = vec![
        node(
            2,
            1,
            "binary-expression",
            4,
            right_end,
            Some(op),
            None,
            None,
        ),
        node(
            3,
            2,
            "binary-expression",
            left_start,
            left_end,
            Some(lhs),
            None,
            None,
        ),
        counter_cast(4, 3, left_start),
        counter_reference(5, 4, left_start),
        literal(6, 3, left_end - 1, "0"),
        node(
            7,
            2,
            "binary-expression",
            right_start,
            right_end,
            Some("=="),
            None,
            None,
        ),
        node(
            8,
            7,
            "binary-expression",
            right_start,
            arithmetic_end,
            Some("+"),
            None,
            None,
        ),
        counter_cast(9, 8, right_start),
        counter_reference(10, 9, right_start),
        literal(11, 8, right_start + 4, "2147483647"),
        literal(12, 7, arithmetic_end + 4, "2147483647"),
    ];
    (source, nodes)
}

#[test]
fn induction_logical_skips_overflow_only_on_unselected_path() {
    // In the valid C loop i=0,1 the RHS is defined only for i=0.
    // Each path selects it exactly when arithmetic is defined.
    for (lhs, op, second_trip) in [("!=", "||", true), ("==", "&&", false)] {
        let (source, nodes) = logical_guard(lhs, op);
        assert_eq!(guard(&source, &nodes, 0), Some((11, true)));
        assert_eq!(guard(&source, &nodes, 1), Some((11, second_trip)));
    }
}

#[test]
fn induction_logical_rejects_executed_overflow_and_source_forgery() {
    for (lhs, op) in [("==", "||"), ("!=", "&&")] {
        let (source, nodes) = logical_guard(lhs, op);
        assert_eq!(guard(&source, &nodes, 1), None);
    }
    let (source, mut nodes) = logical_guard("!=", "||");
    assert_eq!(guard(&source.replace(" + ", " - "), &nodes, 1), None);
    assert_eq!(guard(&source.replace(" || ", " && "), &nodes, 1), None);
    nodes[9].reference = Some(String::from("foreign@0"));
    assert_eq!(guard(&source, &nodes, 1), None);
}

fn ternary_guard(lhs: &str) -> (String, Vec<Node>) {
    let source = format!("if (i {lhs} 0 ? 1 : i + 2147483647 == 2147483647)");
    let condition_end = source.find(" ? ").unwrap();
    let true_start = condition_end + 3;
    let false_start = source.find("i + 2147483647").unwrap();
    let arithmetic_end = false_start + "i + 2147483647".len();
    let end = source.len() - 1;
    let nodes = vec![
        node(2, 1, "conditional-expression", 4, end, None, None, None),
        node(
            3,
            2,
            "binary-expression",
            4,
            condition_end,
            Some(lhs),
            None,
            None,
        ),
        counter_cast(4, 3, 4),
        counter_reference(5, 4, 4),
        literal(6, 3, condition_end - 1, "0"),
        literal(7, 2, true_start, "1"),
        node(
            8,
            2,
            "binary-expression",
            false_start,
            end,
            Some("=="),
            None,
            None,
        ),
        node(
            9,
            8,
            "binary-expression",
            false_start,
            arithmetic_end,
            Some("+"),
            None,
            None,
        ),
        counter_cast(10, 9, false_start),
        counter_reference(11, 10, false_start),
        literal(12, 9, false_start + 4, "2147483647"),
        literal(13, 8, arithmetic_end + 4, "2147483647"),
    ];
    (source, nodes)
}

#[test]
fn induction_ternary_authenticates_both_arms_but_selects_one_value() {
    let (source, nodes) = ternary_guard("!=");
    assert_eq!(guard(&source, &nodes, 0), Some((12, true)));
    assert_eq!(guard(&source, &nodes, 1), Some((12, true)));
    assert_eq!(guard(&source.replace(" ? ", " + "), &nodes, 1), None);
    assert_eq!(guard(&source.replace(" : ", " + "), &nodes, 1), None);
    let (source, nodes) = ternary_guard("==");
    assert_eq!(guard(&source, &nodes, 1), None);
}

fn ternary_true_arm_guard(lhs: &str) -> (String, Vec<Node>) {
    let source = format!("if (i {lhs} 0 ? i + 2147483647 == 2147483647 : 1)");
    let condition_end = source.find(" ? ").unwrap();
    let true_start = condition_end + 3;
    let arithmetic_end = true_start + "i + 2147483647".len();
    let true_end = source.find(" : ").unwrap();
    let false_start = true_end + 3;
    let end = source.len() - 1;
    let nodes = vec![
        node(2, 1, "conditional-expression", 4, end, None, None, None),
        node(
            3,
            2,
            "binary-expression",
            4,
            condition_end,
            Some(lhs),
            None,
            None,
        ),
        counter_cast(4, 3, 4),
        counter_reference(5, 4, 4),
        literal(6, 3, condition_end - 1, "0"),
        node(
            7,
            2,
            "binary-expression",
            true_start,
            true_end,
            Some("=="),
            None,
            None,
        ),
        node(
            8,
            7,
            "binary-expression",
            true_start,
            arithmetic_end,
            Some("+"),
            None,
            None,
        ),
        counter_cast(9, 8, true_start),
        counter_reference(10, 9, true_start),
        literal(11, 8, true_start + 4, "2147483647"),
        literal(12, 7, arithmetic_end + 4, "2147483647"),
        literal(13, 2, false_start, "1"),
    ];
    (source, nodes)
}

#[test]
fn induction_ternary_can_skip_overflow_in_first_arm_too() {
    let (source, nodes) = ternary_true_arm_guard("==");
    assert_eq!(guard(&source, &nodes, 0), Some((12, true)));
    assert_eq!(guard(&source, &nodes, 1), Some((12, true)));
    let (source, nodes) = ternary_true_arm_guard("!=");
    assert_eq!(guard(&source, &nodes, 1), None);
}
