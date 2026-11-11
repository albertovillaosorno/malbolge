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
//   - Bounded same-line C call/argument spacing in source-bound Clang JSON.
// - Must-Not:
//   - Trust folded expressions or substitute host output for guest effects.
// - Allows:
//   - Inputs: exact pinned Clang preorder with bounded source span gaps.
//   - Outputs: canonical typed source spans and independently rechecked bytes.
//   - Side effects: none beyond local VM execution.
// - Split-When:
//   - General C expression parsing supersedes bounded byte output.
// - Merge-When:
//   - The general C frontend supports source whitespace by lexical proof.
// - Summary:
//   - Ordinary source spacing does not change typed guest byte effects.
// - Description:
//   - Preserve positional and semantic rejection for forged source gaps.
// - Usage:
//   - cargo test -p malbolge-c-frontend-json-adapter --test normalized_output_whitespace
// - Defaults:
//   - Real Clang integration is independently tested by the Python suite.

//! Verify bounded spacing and independently re-admitted typed guest bytes.

use malbolge as _;
use malbolge_c_frontend_json_adapter::{
    CanonicalGuestProjection, FrontendGuestMode, canonical_guest_typed_ir, typed,
};
use serde as _;
use serde_json::{Value, json};

fn span(begin: u32, end: u32) -> Value {
    json!({
        "begin": {"byte":begin,"line":2,"column":begin.saturating_sub(18)},
        "end": {"byte":end,"line":2,"column":end.saturating_sub(18)}
    })
}

fn leaf((id, parent): (u32, u32), start: u32, end: u32, digits: &str) -> Value {
    json!({"id":id,"parent":parent,"kind":"integer-literal",
           "span":span(start,end),"type":"i32",
           "constant_integer":digits,"literal":digits})
}

#[expect(
    clippy::default_numeric_fallback,
    reason = "pinned Clang JSON fixture IDs are small untyped integers"
)]
fn normalized(call_end: u32, argument_nodes: Vec<Value>) -> Value {
    let body_end = call_end.saturating_add(3);
    let mut nodes = vec![
        json!({"id":1,"parent":0,"kind":"function-declaration",
               "span":span(19,body_end),"name":"emit","type":"fn()->void",
               "definition":"definition","inline_specified":false,
               "linkage":"external","storage_class":"none"}),
        json!({"id":2,"parent":1,"kind":"compound-statement",
               "span":span(35,body_end)}),
        json!({"id":3,"parent":2,"kind":"call-expression",
               "span":span(37,call_end),"type":"i32",
               "reference":"external:putchar"}),
        json!({"id":4,"parent":3,"kind":"cast-expression",
               "span":span(37,44),"type":"ptr(fn(i32)->i32)",
               "operation":"function-to-pointer"}),
        json!({"id":5,"parent":4,"kind":"declaration-reference-expression",
               "span":span(37,44),"type":"fn(i32)->i32",
               "reference":"external:putchar"}),
    ];
    nodes.extend(argument_nodes);
    json!({
        "schema_version":1,"artifact_id":"malbolge-c-frontend-v1",
        "clang":{"version":"22.1.8","target":"wasm32-unknown-unknown",
                 "language":"c23"},
        "profile":{"abi_id":"malbolge-c32-v1","target_profile":"malbolge-2026"},
        "source":{"id":"spacing.c","sha256":
            "a89c18405bc20022ede681f378721e9ba71298fd250b2841417bfe1a01a43009"},
        "nodes":nodes
    })
}

fn admitted(value: &Value) -> Result<CanonicalGuestProjection, String> {
    let encoded = serde_json::to_vec(value).map_err(|error| error.to_string())?;
    canonical_guest_typed_ir(&encoded).map_err(|error| format!("{error:?}"))
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::default_numeric_fallback,
    reason = "source fixtures encode pinned Clang IDs and the typed assertions own failures"
)]
fn spaced_source_preserves_guest_a_and_original_spans() -> Result<(), String> {
    let cases = [
        (normalized(48, vec![leaf((6, 3), 45, 47, "65")]), 45, 47),
        (normalized(49, vec![leaf((6, 3), 46, 48, "65")]), 46, 48),
        (normalized(51, vec![leaf((6, 3), 47, 49, "65")]), 47, 49),
        (
            normalized(
                54,
                vec![
                    json!({"id":6,"parent":3,"kind":"parenthesized-expression",
                           "span":span(46,52),"type":"i32","constant_integer":"65"}),
                    leaf((7, 6), 48, 50, "65"),
                ],
            ),
            48,
            50,
        ),
        (
            normalized(
                55,
                vec![
                    json!({"id":6,"parent":3,"kind":"unary-expression",
                           "span":span(46,53),"type":"i32","operation":"-",
                           "constant_integer":"-191"}),
                    json!({"id":7,"parent":6,"kind":"parenthesized-expression",
                           "span":span(48,53),"type":"i32","constant_integer":"191"}),
                    leaf((8, 7), 49, 52, "191"),
                ],
            ),
            46,
            53,
        ),
    ];
    for (source, source_begin, source_end) in cases {
        let (wire, mode) = admitted(&source)?;
        assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
        let module = typed::canonical_module(&wire).map_err(|error| format!("{error:?}"))?;
        let constant = module
            .functions()
            .first()
            .and_then(|function| function.blocks().first())
            .and_then(|block| block.instructions().first())
            .ok_or("missing source constant")?;
        assert_eq!(constant.span().begin().byte(), source_begin);
        assert_eq!(constant.span().end().byte(), source_end);
        assert!(matches!(
            constant.instruction(),
            typed::Instruction::ConstantInteger { constant, .. }
                if constant.bit_width() == 8 && constant.little_endian() == [65]
        ));
    }
    Ok(())
}

#[test]
#[expect(
    clippy::default_numeric_fallback,
    clippy::indexing_slicing,
    reason = "deliberate mutations of checked synthetic JSON AST fixtures"
)]
fn inconsistent_or_unbounded_source_gaps_fail_closed() {
    let base = normalized(51, vec![leaf((6, 3), 47, 49, "65")]);
    let mut cases = Vec::new();
    // The semantic preorder is necessary, but cannot justify arbitrary gaps.
    cases.push(normalized(70, vec![leaf((6, 3), 66, 68, "65")]));
    let mut wrong_column = base.clone();
    wrong_column["nodes"][5]["span"]["begin"]["column"] = json!(28);
    cases.push(wrong_column);
    let mut wrong_line = base.clone();
    wrong_line["nodes"][5]["span"]["begin"]["line"] = json!(3);
    cases.push(wrong_line);
    let mut forged_callee = base.clone();
    forged_callee["nodes"][4]["reference"] = json!("external:other");
    cases.push(forged_callee);
    let mut mismatched_value = base;
    mismatched_value["nodes"][5]["constant_integer"] = json!("66");
    cases.push(mismatched_value);
    let extra_operator = normalized(
        55,
        vec![
            json!({"id":6,"parent":3,"kind":"unary-expression",
                   "span":span(46,53),"type":"i32","operation":"*",
                   "constant_integer":"-191"}),
            json!({"id":7,"parent":6,"kind":"parenthesized-expression",
                   "span":span(48,53),"type":"i32","constant_integer":"191"}),
            leaf((8, 7), 49, 52, "191"),
        ],
    );
    cases.push(extra_operator);
    for source in cases {
        assert!(admitted(&source).is_err(), "accepted forged JSON {source}");
    }
}
