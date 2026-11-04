// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Exactly one explicit C void cast discarding a putchar call result.
// - Must-Not:
//   - Drop a second side effect, nested discard or fabricated AST ancestry.
// - Allows:
//   - Inputs: pinned-Clang to-void cast wrapping one direct putchar call.
//   - Outputs: checked u8 output effect and canonical source-proven typed IR.
//   - Side effects: none.
// - Split-When:
//   - General C statement expression lowering handles discarded results.
// - Merge-When:
//   - Source-to-guest C integration owns this pinned normalized shape.
// - Summary:
//   - Explicitly ignored putchar return values preserve guest byte output.
// - Description:
//   - Forbid forged cast metadata, expression replacement or source offsets.
// - Usage:
//   - cargo test -p malbolge-c-frontend-json-adapter --test normalized_void_cast_output
// - Defaults:
//   - Pinned Clang and real guest VM are checked by native Python integration.

//! Pinned Clang's explicit to-void output cast is effect-preserving.

use malbolge as _;
use malbolge_c_frontend_json_adapter::{
    CanonicalGuestProjection, FrontendGuestMode, canonical_guest_typed_ir, typed,
};
use serde as _;
use serde_json::{Value, json};

fn span(begin: u32, end: u32) -> Value {
    json!({
        "begin":{"byte":begin,"line":2,"column":begin.saturating_sub(18)},
        "end":{"byte":end,"line":2,"column":end.saturating_sub(18)}
    })
}

fn input(gap: u32) -> Value {
    let call_begin = 43u32.saturating_add(gap);
    let call_end = 54u32.saturating_add(gap);
    let callee_end = 50u32.saturating_add(gap);
    let leaf_begin = 51u32.saturating_add(gap);
    let leaf_end = 53u32.saturating_add(gap);
    let body_end = 57u32.saturating_add(gap);
    json!({
        "schema_version":1,"artifact_id":"malbolge-c-frontend-v1",
        "clang":{"version":"22.1.8","target":"wasm32-unknown-unknown","language":"c23"},
        "profile":{"abi_id":"malbolge-c32-v1","target_profile":"malbolge-2026"},
        "source":{"id":"void-cast.c","sha256":
            "a89c18405bc20022ede681f378721e9ba71298fd250b2841417bfe1a01a43009"},
        "nodes":[
            {"id":1,"parent":0,"kind":"function-declaration",
             "span":span(19,body_end),"name":"emit","type":"fn()->void",
             "definition":"definition","inline_specified":false,"linkage":"external",
             "storage_class":"none"},
            {"id":2,"parent":1,"kind":"compound-statement","span":span(35,body_end)},
            {"id":3,"parent":2,"kind":"cast-expression","span":span(37,call_end),
             "type":"void","operation":"to-void"},
            {"id":4,"parent":3,"kind":"call-expression","span":span(call_begin,call_end),
             "type":"i32","reference":"external:putchar"},
            {"id":5,"parent":4,"kind":"cast-expression","span":span(call_begin,callee_end),
             "type":"ptr(fn(i32)->i32)","operation":"function-to-pointer"},
            {"id":6,"parent":5,"kind":"declaration-reference-expression",
             "span":span(call_begin,callee_end),"type":"fn(i32)->i32",
             "reference":"external:putchar"},
            {"id":7,"parent":4,"kind":"integer-literal","span":span(leaf_begin,leaf_end),
             "type":"i32","literal":"65","constant_integer":"65"}
        ]
    })
}

fn admitted(value: &Value) -> Result<CanonicalGuestProjection, String> {
    let bytes = serde_json::to_vec(value).map_err(|error| error.to_string())?;
    canonical_guest_typed_ir(&bytes).map_err(|error| format!("{error:?}"))
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    clippy::cognitive_complexity,
    reason = "source constant and byte-effect witnesses must be independently asserted"
)]
fn explicit_discard_preserves_actual_call_and_constant_spans() -> Result<(), String> {
    for gap in [0u32, 1, 3, 16] {
        let (bytes, mode) = admitted(&input(gap))?;
        assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
        let module = typed::canonical_module(&bytes).map_err(|error| format!("{error:?}"))?;
        let instructions = module
            .functions()
            .first()
            .and_then(|function| function.blocks().first())
            .map(typed::BasicBlock::instructions)
            .ok_or("missing typed effects")?;
        let constant = instructions.first().ok_or("missing literal")?;
        let output = instructions.get(1).ok_or("missing output")?;
        assert_eq!(constant.span().begin().byte(), 51u32.saturating_add(gap));
        assert_eq!(constant.span().end().byte(), 53u32.saturating_add(gap));
        assert_eq!(output.span().begin().byte(), 43u32.saturating_add(gap));
        assert_eq!(output.span().end().byte(), 54u32.saturating_add(gap));
        assert!(matches!(
            constant.instruction(),
            typed::Instruction::ConstantInteger { constant, .. }
                if constant.bit_width() == 8 && constant.little_endian() == [65]
        ));
        assert!(matches!(
            output.instruction(),
            typed::Instruction::ByteOutput { .. }
        ));
    }
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::default_numeric_fallback,
    reason = "deliberate corruption of fixed-size synthetic Clang nodes"
)]
fn forged_discard_ancestry_and_metadata_fail_closed() {
    let mut cases = Vec::new();
    let base = input(0);
    let mut wrong_parent = base.clone();
    wrong_parent["nodes"][3]["parent"] = json!(2);
    cases.push(wrong_parent);
    let mut wrong_operation = base.clone();
    wrong_operation["nodes"][2]["operation"] = json!("other-cast");
    cases.push(wrong_operation);
    let mut wrong_type = base.clone();
    wrong_type["nodes"][2]["type"] = json!("i32");
    cases.push(wrong_type);
    let mut extra_metadata = base.clone();
    extra_metadata["nodes"][2]["literal"] = json!("65");
    cases.push(extra_metadata);
    let mut wrong_end = base.clone();
    wrong_end["nodes"][2]["span"]["end"]["byte"] = json!(55);
    cases.push(wrong_end);
    cases.push(input(17));
    let mut wrong_column = input(0);
    wrong_column["nodes"][3]["span"]["begin"]["column"] = json!(26);
    cases.push(wrong_column);
    let mut wrong_callee = base;
    wrong_callee["nodes"][5]["reference"] = json!("external:getchar");
    cases.push(wrong_callee);
    for source in cases {
        assert!(
            admitted(&source).is_err(),
            "accepted forged discard {source}"
        );
    }
}
