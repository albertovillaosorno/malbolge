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
//   - Source-bound proof regressions for lazy C integer predicates.
// - Must-Not:
//   - Claim these hand-built preorder nodes are pinned Clang artifacts.
// - Allows:
//   - Inputs: exact source spans and syntactically valid pure AST trees.
//   - Outputs: finite-byte predicate proofs and conservative refusals.
//   - Side effects: none.
// - Split-When:
//   - The pinned frontend supports an independent whole-C golden fixture.
// - Merge-When:
//   - Source-checked conditional proof gains a dedicated test module.
// - Summary:
//   - Prove only evaluated logical and conditional C operands need values.
// - Description:
//   - Authenticate every subtree, including the skipped expression.
// - Usage:
//   - cargo test -p malbolge-c-frontend-json-adapter --lib lazy_byte_predicate
// - Defaults:
//   - Reachable division by zero rejects the entire predicate.

use serde_json::json;

use super::Node;

// Keep the existing predicate-selection assertions independent of whether
// the production proof also retains its per-byte branch truth domain.
fn prove_total_byte_if_predicate(
    nodes: &[Node],
    body: &Node,
    previous: u32,
    conditional: &Node,
    local: Option<&super::LocalDeclaration<'_>>,
    source: Option<&[u8]>,
) -> Option<(usize, Option<bool>)> {
    super::prove_total_byte_if_predicate(
        nodes,
        body,
        previous,
        conditional,
        local,
        source,
    )
    .map(|(width, selected, _)| (width, selected))
}

fn node(
    id: u32,
    parent: u32,
    kind: &str,
    start: u32,
    end: u32,
    operation: Option<&str>,
    literal: Option<&str>,
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
        "constant_integer": literal
    }))
    .expect("test preorder node")
}

fn number(id: u32, parent: u32, start: u32, value: &str) -> Node {
    node(
        id,
        parent,
        "integer-literal",
        start,
        start + u32::try_from(value.len()).unwrap(),
        None,
        Some(value),
    )
}

fn logical_with_divisor(left: &str, operator: &str) -> (String, Vec<Node>) {
    let source = format!("{left} {operator} 1 / 0");
    let right_start = u32::try_from(left.len() + operator.len() + 2).unwrap();
    let end = u32::try_from(source.len()).unwrap();
    let nodes = vec![
        node(2, 1, "binary-expression", 0, end, Some(operator), None),
        number(3, 2, 0, left),
        node(4, 2, "binary-expression", right_start, end, Some("/"), None),
        number(5, 4, right_start, "1"),
        number(6, 4, end - 1, "0"),
    ];
    (source, nodes)
}

fn predicate(source: &str, nodes: &[Node]) -> Option<(usize, Option<bool>)> {
    let conditional = node(1, 0, "if-statement", 0, 0, None, None);
    let body = node(0, 0, "compound-statement", 0, 0, None, None);
    prove_total_byte_if_predicate(
        nodes,
        &body,
        0,
        &conditional,
        None,
        Some(source.as_bytes()),
    )
}

#[test]
fn lazy_logical_operators_admit_only_the_evaluated_side() {
    for (left, operator, selected) in [("1", "||", true), ("0", "&&", false)] {
        let (source, nodes) = logical_with_divisor(left, operator);
        assert_eq!(predicate(&source, &nodes), Some((5, Some(selected))));
        let forged_source = source.replace(" / ", " * ");
        assert_eq!(predicate(&forged_source, &nodes), None);
    }
}

#[test]
fn evaluated_invalid_logical_operands_still_refuse() {
    for (left, operator) in [("0", "||"), ("1", "&&")] {
        let (source, nodes) = logical_with_divisor(left, operator);
        assert_eq!(predicate(&source, &nodes), None);
    }
}

#[test]
fn ternary_selects_only_its_defined_pure_arm() {
    let source = "1 ? 7 : 1 / 0";
    let nodes = vec![
        node(2, 1, "conditional-expression", 0, 13, None, None),
        number(3, 2, 0, "1"),
        number(4, 2, 4, "7"),
        node(5, 2, "binary-expression", 8, 13, Some("/"), None),
        number(6, 5, 8, "1"),
        number(7, 5, 12, "0"),
    ];
    assert_eq!(predicate(source, &nodes), Some((6, Some(true))));
    assert_eq!(predicate("0 ? 7 : 1 / 0", &nodes), None);
}

fn live_local_cast(id: u32, parent: u32, start: u32) -> [Node; 2] {
    let end = start + 7;
    let cast = node(
        id,
        parent,
        "cast-expression",
        start,
        end,
        Some("lvalue-to-rvalue"),
        None,
    );
    let reference = serde_json::from_value(json!({
        "id": id + 1,
        "parent": id,
        "kind": "declaration-reference-expression",
        "type": "i32",
        "reference": "current@0",
        "span": {
            "begin": {"byte": start, "line": 1, "column": start + 1},
            "end": {"byte": end, "line": 1, "column": end + 1}
        }
    }))
    .expect("test live-byte reference");
    [cast, reference]
}

fn live_division_guard(
    outer_operator: &str,
    left_operator: &str,
) -> (String, Vec<Node>) {
    let source = format!(
        "current {left_operator} 0 {outer_operator} current / current == 1"
    );
    let division_start =
        u32::try_from(source.find("current / current").unwrap()).unwrap();
    let right_start = division_start;
    let left_end = u32::try_from(source.find(" 0 ").unwrap() + 2).unwrap();
    let division_end = division_start + 17;
    let denominator_start = division_start + 10;
    let source_end = u32::try_from(source.len()).unwrap();
    let mut nodes = vec![
        node(
            2,
            1,
            "binary-expression",
            0,
            source_end,
            Some(outer_operator),
            None,
        ),
        node(
            3,
            2,
            "binary-expression",
            0,
            left_end,
            Some(left_operator),
            None,
        ),
    ];
    nodes.extend(live_local_cast(4, 3, 0));
    nodes.push(number(6, 3, left_end - 1, "0"));
    nodes.push(node(
        7,
        2,
        "binary-expression",
        right_start,
        source_end,
        Some("=="),
        None,
    ));
    nodes.push(node(
        8,
        7,
        "binary-expression",
        division_start,
        division_end,
        Some("/"),
        None,
    ));
    nodes.extend(live_local_cast(9, 8, division_start));
    nodes.extend(live_local_cast(11, 8, denominator_start));
    nodes.push(number(13, 7, source_end - 1, "1"));
    (source, nodes)
}

#[test]
fn live_byte_short_circuit_proves_all_256_input_cases() {
    let input = node(100, 0, "call-expression", 0, 0, None, None);
    let local = super::LocalDeclaration {
        declaration_end: 0,
        input: &input,
        line: 1,
        name: "current",
        variable_reference: String::from("current@0"),
    };
    for (outer, left, expected) in
        [("||", "==", Some(true)), ("&&", "!=", None)]
    {
        let (source, nodes) = live_division_guard(outer, left);
        let conditional = node(1, 0, "if-statement", 0, 0, None, None);
        let body = node(0, 0, "compound-statement", 0, 0, None, None);
        let check = |source: &str, nodes: &[Node]| {
            prove_total_byte_if_predicate(
                nodes,
                &body,
                0,
                &conditional,
                Some(&local),
                Some(source.as_bytes()),
            )
        };
        assert_eq!(check(&source, &nodes), Some((12, expected)));
        assert_eq!(check(&source.replace(" / ", " * "), &nodes), None);
    }
}

#[test]
fn live_byte_reachable_zero_division_refuses() {
    let input = node(100, 0, "call-expression", 0, 0, None, None);
    let local = super::LocalDeclaration {
        declaration_end: 0,
        input: &input,
        line: 1,
        name: "current",
        variable_reference: String::from("current@0"),
    };
    let (source, nodes) = live_division_guard("&&", "==");
    let conditional = node(1, 0, "if-statement", 0, 0, None, None);
    let body = node(0, 0, "compound-statement", 0, 0, None, None);
    assert_eq!(
        prove_total_byte_if_predicate(
            &nodes,
            &body,
            0,
            &conditional,
            Some(&local),
            Some(source.as_bytes()),
        ),
        None
    );
}

fn live_ternary_guard(condition_operator: &str) -> (String, Vec<Node>) {
    let source =
        format!("current {condition_operator} 0 ? 1 : current / current");
    let condition_end = u32::try_from(source.find(" ? ").unwrap()).unwrap();
    let arm_start = condition_end + 3;
    let division_start =
        u32::try_from(source.find("current / current").unwrap()).unwrap();
    let division_end = u32::try_from(source.len()).unwrap();
    let mut nodes = vec![
        node(2, 1, "conditional-expression", 0, division_end, None, None),
        node(
            3,
            2,
            "binary-expression",
            0,
            condition_end,
            Some(condition_operator),
            None,
        ),
    ];
    nodes.extend(live_local_cast(4, 3, 0));
    nodes.push(number(6, 3, condition_end - 1, "0"));
    nodes.push(number(7, 2, arm_start, "1"));
    nodes.push(node(
        8,
        2,
        "binary-expression",
        division_start,
        division_end,
        Some("/"),
        None,
    ));
    nodes.extend(live_local_cast(9, 8, division_start));
    nodes.extend(live_local_cast(11, 8, division_start + 10));
    (source, nodes)
}

#[test]
fn live_ternary_skips_division_exactly_at_zero_byte() {
    let input = node(100, 0, "call-expression", 0, 0, None, None);
    let local = super::LocalDeclaration {
        declaration_end: 0,
        input: &input,
        line: 1,
        name: "current",
        variable_reference: String::from("current@0"),
    };
    let conditional = node(1, 0, "if-statement", 0, 0, None, None);
    let body = node(0, 0, "compound-statement", 0, 0, None, None);
    let check = |source: &str, nodes: &[Node]| {
        prove_total_byte_if_predicate(
            nodes,
            &body,
            0,
            &conditional,
            Some(&local),
            Some(source.as_bytes()),
        )
    };
    let (source, nodes) = live_ternary_guard("==");
    assert_eq!(check(&source, &nodes), Some((11, Some(true))));
    let (source, nodes) = live_ternary_guard("!=");
    assert_eq!(check(&source, &nodes), None);
    assert_eq!(check(&source.replace(" / ", " + "), &nodes), None);
}

#[test]
fn skipped_expression_still_requires_authentic_ast_and_pure_effects() {
    let (source, mut nodes) = logical_with_divisor("1", "||");
    nodes[2].kind = String::from("call-expression");
    nodes[2].reference = Some(String::from("external:putchar"));
    assert_eq!(predicate(&source, &nodes), None);

    let (source, mut nodes) = logical_with_divisor("1", "||");
    nodes[2].operation = Some(String::from("*"));
    assert_eq!(predicate(&source, &nodes), None);

    let (source, mut nodes) = logical_with_divisor("0", "&&");
    nodes[4].span.begin.column += 1;
    assert_eq!(predicate(&source, &nodes), None);
}

#[test]
fn live_skipped_divisor_must_refer_to_the_authenticated_local() {
    let input = node(100, 0, "call-expression", 0, 0, None, None);
    let local = super::LocalDeclaration {
        declaration_end: 0,
        input: &input,
        line: 1,
        name: "current",
        variable_reference: String::from("current@0"),
    };
    let (source, mut nodes) = live_division_guard("||", "==");
    nodes[10].reference = Some(String::from("foreign@0"));
    let conditional = node(1, 0, "if-statement", 0, 0, None, None);
    let body = node(0, 0, "compound-statement", 0, 0, None, None);
    assert_eq!(
        prove_total_byte_if_predicate(
            &nodes,
            &body,
            0,
            &conditional,
            Some(&local),
            Some(source.as_bytes()),
        ),
        None
    );
}
