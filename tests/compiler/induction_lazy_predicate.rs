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

use super::{
    Node, StaticInduction, prove_induction_predicate, prove_static_predicate,
};

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

fn prefix_guard(grouped: bool) -> (String, Vec<Node>) {
    let source = if grouped {
        "if ((i))"
    } else {
        "if (!i)"
    };
    let kind = if grouped {
        "parenthesized-expression"
    } else {
        "unary-expression"
    };
    let end = if grouped {
        7
    } else {
        6
    };
    let operation = if grouped {
        None
    } else {
        Some("!")
    };
    let nodes = vec![
        node(2, 1, kind, 4, end, operation, None, None),
        counter_cast(3, 2, 5),
        counter_reference(4, 3, 5),
    ];
    (String::from(source), nodes)
}

#[test]
fn induction_prefix_proofs_bind_source_punctuation() {
    let (not_source, not_nodes) = prefix_guard(false);
    assert_eq!(guard(&not_source, &not_nodes, 0), Some((3, true)));
    assert_eq!(guard(&not_source, &not_nodes, 1), Some((3, false)));
    // A valid same-width C unary plus cannot inherit the Clang ! decision.
    assert_eq!(guard(&not_source.replace('!', "+"), &not_nodes, 0), None);
    let (group_source, group_nodes) = prefix_guard(true);
    assert_eq!(guard(&group_source, &group_nodes, 0), Some((3, false)));
    assert_eq!(guard(&group_source, &group_nodes, 1), Some((3, true)));
    assert_eq!(
        guard(&group_source.replace("((", "(["), &group_nodes, 1),
        None
    );
    assert_eq!(
        guard(&group_source.replace("))", "])"), &group_nodes, 1),
        None
    );
}

#[test]
fn induction_constant_subtrees_must_match_original_source_bytes() {
    let integer = vec![literal(2, 1, 4, "1")];
    assert_eq!(guard("if (1)", &integer, 0), Some((1, true)));
    assert_eq!(guard("if (0)", &integer, 0), None);

    let mut comparison_node =
        node(2, 1, "binary-expression", 4, 10, Some("=="), None, None);
    comparison_node.constant_integer = Some(String::from("1"));
    let comparison_tree = vec![
        comparison_node,
        literal(3, 2, 4, "1"),
        literal(4, 2, 9, "1"),
    ];
    assert_eq!(guard("if (1 == 1)", &comparison_tree, 0), Some((3, true)));
    assert_eq!(guard("if (1 != 1)", &comparison_tree, 0), None);
    assert_eq!(guard("if (0 == 1)", &comparison_tree, 0), None);
}

#[test]
fn induction_nested_static_subtrees_reject_source_forgery() {
    let mut not_node =
        node(2, 1, "unary-expression", 4, 6, Some("!"), None, None);
    not_node.constant_integer = Some(String::from("0"));
    let not_tree = vec![not_node, literal(3, 2, 5, "1")];
    assert_eq!(guard("if (!1)", &not_tree, 0), Some((2, false)));
    assert_eq!(guard("if (+1)", &not_tree, 0), None);

    let mut outer_node =
        node(2, 1, "binary-expression", 4, 15, Some("=="), None, None);
    outer_node.constant_integer = Some(String::from("1"));
    let mut nested_node =
        node(3, 2, "binary-expression", 4, 10, Some("=="), None, None);
    nested_node.constant_integer = Some(String::from("1"));
    let nested_tree = vec![
        outer_node,
        nested_node,
        literal(4, 3, 4, "1"),
        literal(5, 3, 9, "1"),
        literal(6, 2, 14, "1"),
    ];
    assert_eq!(guard("if (1 == 1 == 1)", &nested_tree, 0), Some((5, true)));
    assert_eq!(guard("if (1 == 1 == 0)", &nested_tree, 0), None);
    assert_eq!(guard("if (1 != 1 == 1)", &nested_tree, 0), None);
    assert_eq!(guard("if (1 == 1 && 1)", &nested_tree, 0), None);
}

#[test]
fn source_backed_static_if_must_not_fall_back_to_unchecked_ast() {
    let conditional = node(1, 0, "if-statement", 0, 6, None, None, None);
    let integer = vec![literal(2, 1, 4, "1")];
    for (source, expected) in [("if (1)", Some((1, true))), ("if (0)", None)] {
        assert_eq!(
            prove_static_predicate(
                &integer,
                &conditional,
                Some(StaticInduction {
                    reference: "i@0",
                    name: "i",
                    source: Some(source.as_bytes()),
                    value: 0,
                }),
            ),
            expected,
        );
    }
}

#[test]
fn source_backed_static_logical_keeps_a_proven_constant_fallback() {
    let conditional = node(1, 0, "if-statement", 0, 11, None, None, None);
    let mut logical =
        node(2, 1, "binary-expression", 4, 10, Some("&&"), None, None);
    logical.constant_integer = Some(String::from("1"));
    let nodes = vec![logical, literal(3, 2, 4, "1"), literal(4, 2, 9, "1")];
    for (source, expected) in [
        ("if (1 && 1)", Some((3, true))),
        ("if (1 || 1)", None),
        ("if (1 && 0)", None),
    ] {
        assert_eq!(
            prove_static_predicate(
                &nodes,
                &conditional,
                Some(StaticInduction {
                    reference: "i@0",
                    name: "i",
                    source: Some(source.as_bytes()),
                    value: 0,
                }),
            ),
            expected,
        );
    }
}

// Division by zero is undefined only when this pure C operand executes.
// All of the node, token, and loop-local bindings still need authentication.
fn zero_divisor_logical_guard(
    lhs: &str,
    operator: &str,
) -> (String, Vec<Node>) {
    let source = format!("if ({lhs} {operator} i / 0)");
    let right_start = 4 + lhs.len() + operator.len() + 2;
    let end = source.len() - 1;
    (source, vec![
        node(
            2,
            1,
            "binary-expression",
            4,
            end,
            Some(operator),
            None,
            None,
        ),
        literal(3, 2, 4, lhs),
        node(
            4,
            2,
            "binary-expression",
            right_start,
            end,
            Some("/"),
            None,
            None,
        ),
        counter_cast(5, 4, right_start),
        counter_reference(6, 5, right_start),
        literal(7, 4, right_start + 4, "0"),
    ])
}

#[test]
fn unexecuted_zero_division_is_pure_and_does_not_need_a_value() {
    for (lhs, operator, expected) in [("1", "||", true), ("0", "&&", false)] {
        let (source, nodes) = zero_divisor_logical_guard(lhs, operator);
        for counter in [0, 1, -1, i32::MAX] {
            assert_eq!(guard(&source, &nodes, counter), Some((6, expected)));
        }
        assert_eq!(guard(&source.replace(" / ", " + "), &nodes, 0), None);
        assert_eq!(guard(&source.replace("i /", "j /"), &nodes, 0), None);
        let (_, mut forged) = zero_divisor_logical_guard(lhs, operator);
        forged[4].reference = Some(String::from("foreign@0"));
        assert_eq!(guard(&source, &forged, 0), None);
    }
}

#[test]
fn executed_zero_division_still_refuses_before_selecting_guest_effects() {
    for (lhs, operator) in [("0", "||"), ("1", "&&")] {
        let (source, nodes) = zero_divisor_logical_guard(lhs, operator);
        for counter in [0, 1, -1] {
            assert_eq!(guard(&source, &nodes, counter), None);
        }
    }
}

fn zero_divisor_ternary_guard(skip_true: bool) -> (String, Vec<Node>) {
    let source = if skip_true {
        String::from("if (0 ? i / 0 : 1)")
    } else {
        String::from("if (1 ? 1 : i / 0)")
    };
    let end = source.len() - 1;
    let division_start = source.find("i / 0").unwrap();
    let division_id = if skip_true {
        4
    } else {
        5
    };
    let mut nodes = vec![
        node(2, 1, "conditional-expression", 4, end, None, None, None),
        literal(
            3,
            2,
            4,
            if skip_true {
                "0"
            } else {
                "1"
            },
        ),
    ];
    if !skip_true {
        nodes.push(literal(4, 2, 8, "1"));
    }
    nodes.extend([
        node(
            division_id,
            2,
            "binary-expression",
            division_start,
            division_start + 5,
            Some("/"),
            None,
            None,
        ),
        counter_cast(division_id + 1, division_id, division_start),
        counter_reference(division_id + 2, division_id + 1, division_start),
        literal(division_id + 3, division_id, division_start + 4, "0"),
    ]);
    if skip_true {
        nodes.push(literal(8, 2, source.find(": 1").unwrap() + 2, "1"));
    }
    (source, nodes)
}

#[test]
fn unselected_ternary_arm_allows_pure_undefined_division() {
    for skip_true in [true, false] {
        let (source, nodes) = zero_divisor_ternary_guard(skip_true);
        assert_eq!(guard(&source, &nodes, 0), Some((7, true)));
        assert_eq!(guard(&source, &nodes, i32::MIN), Some((7, true)));
        assert_eq!(guard(&source.replace(" / ", " * "), &nodes, 1), None);
        let (_, mut forged) = zero_divisor_ternary_guard(skip_true);
        let reference_index = if skip_true {
            4
        } else {
            5
        };
        forged[reference_index].reference = Some(String::from("foreign@0"));
        assert_eq!(guard(&source, &forged, 1), None);
    }
}

#[test]
fn skipped_comparison_with_zero_divisor_does_not_require_a_value() {
    let source = "if (1 || i / 0 == 1)";
    let nodes = vec![
        node(2, 1, "binary-expression", 4, 19, Some("||"), None, None),
        literal(3, 2, 4, "1"),
        node(4, 2, "binary-expression", 9, 19, Some("=="), None, None),
        node(5, 4, "binary-expression", 9, 14, Some("/"), None, None),
        counter_cast(6, 5, 9),
        counter_reference(7, 6, 9),
        literal(8, 5, 13, "0"),
        literal(9, 4, 18, "1"),
    ];
    assert_eq!(guard(source, &nodes, 0), Some((8, true)));
    assert_eq!(guard(&source.replace(" || ", " && "), &nodes, 0), None);
    assert_eq!(guard(&source.replace(" == ", " != "), &nodes, 0), None);
}
