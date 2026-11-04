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
//   - Bounded Clang source-bound parenthesis chains around putchar constants.
// - Must-Not:
//   - Infer arithmetic, decode source token spellings, or bypass guest verification.
// - Allows:
//   - Inputs: exact pinned Clang nested-argument semantic preorders.
//   - Outputs: typed source spans, normative guest bytes or strict rejection.
//   - Side effects: none beyond isolated in-process guest VM execution.
// - Split-When:
//   - General C expression lowering replaces source-bound argument admission.
// - Merge-When:
//   - One source-to-guest integration suite owns these exact wrapper cases.
// - Summary:
//   - Parenthesized C literals retain their signed-byte effects in guest code.
// - Description:
//   - Exact ancestor, constant, type, token and delimiter spans are required.
// - Usage:
//   - cargo test -p malbolge-c-frontend-json-adapter --test normalized_parenthesized_output
// - Defaults:
//   - Native Clang is independently exercised by the corresponding Python test.

//! Strict parenthesized Clang argument projections with real Malbolge execution.

#[path = "../../typed-echo-adapter/composition/lib.rs"]
pub mod adapter;

use malbolge::{ProfileMachine, RunOutcome, target_profile};
use malbolge_c_frontend_json_adapter::{FrontendGuestMode, canonical_guest_typed_ir, typed};
use serde as _;
use serde_json::{Value, json};

fn span(begin: u32, end: u32) -> Value {
    json!({"begin":{"byte":begin,"line":2,"column":begin.saturating_sub(18)},
           "end":{"byte":end,"line":2,"column":end.saturating_sub(18)}})
}

// Generated positions and semantic node relationships match pinned Clang's
// `putchar(((65)))`, `putchar((+65))`, `putchar((-191))`, `putchar((65u))`.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing,
    reason = "synthetic checked source offsets and direct adversarial mutations"
)]
fn input(parentheses: u32, sign: Option<&str>, digits: &str, suffix: &str) -> Value {
    let unsigned = suffix == "u";
    let evaluated = if sign == Some("-") && digits != "0" {
        format!("-{digits}")
    } else {
        digits.to_string()
    };
    let value_type = if unsigned { "u32" } else { "i32" };
    let leaf_start = 45 + parentheses + u32::from(sign.is_some());
    let leaf_end = leaf_start + u32::try_from(digits.len() + suffix.len()).unwrap_or_default();
    let arg_end = leaf_end + parentheses;
    let call_end = arg_end + 1;
    let body_end = call_end + 3;
    let mut nodes = vec![
        json!({"id":1,"parent":0,"kind":"function-declaration","span":span(19,body_end),
               "name":"emit","type":"fn()->void","definition":"definition",
               "inline_specified":false,"linkage":"external","storage_class":"none"}),
        json!({"id":2,"parent":1,"kind":"compound-statement","span":span(35,body_end)}),
        json!({"id":3,"parent":2,"kind":"call-expression","span":span(37,call_end),
               "type":"i32","reference":"external:putchar"}),
        json!({"id":4,"parent":3,"kind":"cast-expression","span":span(37,44),
               "type":"ptr(fn(i32)->i32)","operation":"function-to-pointer"}),
        json!({"id":5,"parent":4,"kind":"declaration-reference-expression",
               "span":span(37,44),"type":"fn(i32)->i32","reference":"external:putchar"}),
    ];
    let mut parent = 3;
    let mut id = 6;
    if unsigned {
        nodes.push(json!({"id":id,"parent":parent,"kind":"cast-expression",
                          "span":span(45,arg_end),"type":"i32",
                          "operation":"integral-cast","constant_integer":evaluated}));
        parent = id;
        id += 1;
    }
    for index in 0..parentheses {
        nodes.push(
            json!({"id":id,"parent":parent,"kind":"parenthesized-expression",
                          "span":span(45+index,arg_end-index),"type":value_type,
                          "constant_integer":evaluated}),
        );
        parent = id;
        id += 1;
    }
    if let Some(operation) = sign {
        nodes.push(json!({"id":id,"parent":parent,"kind":"unary-expression",
                          "span":span(leaf_start-1,leaf_end),"type":"i32",
                          "operation":operation,"constant_integer":evaluated}));
        parent = id;
        id += 1;
    }
    nodes.push(json!({"id":id,"parent":parent,"kind":"integer-literal",
                      "span":span(leaf_start,leaf_end),"type":value_type,
                      "constant_integer":digits,"literal":digits}));
    json!({
        "schema_version":1,"artifact_id":"malbolge-c-frontend-v1",
        "clang":{"version":"22.1.8","target":"wasm32-unknown-unknown","language":"c23"},
        "profile":{"abi_id":"malbolge-c32-v1","target_profile":"malbolge-2026"},
        "source":{"id":"parentheses.c","sha256":
            "a89c18405bc20022ede681f378721e9ba71298fd250b2841417bfe1a01a43009"},
        "nodes":nodes
    })
}

// Move the one source sign before the parentheses without modifying the
// literal leaf offsets. This models pinned Clang for `-(191)` and `+((65))`.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing,
    reason = "bounded synthetic normalized nodes"
)]
fn outer_sign_input(parentheses: u32, sign: &str, digits: &str) -> Value {
    let mut source = input(parentheses, Some(sign), digits, "");
    source["nodes"][5]["kind"] = json!("unary-expression");
    source["nodes"][5]["operation"] = json!(sign);
    let argument_end = 46 + parentheses * 2 + u32::try_from(digits.len()).unwrap_or_default();
    for index in 1..=parentheses {
        let begin = 45 + index;
        let end = argument_end - index + 1;
        let node = &mut source["nodes"][5 + usize::try_from(index).unwrap_or_default()];
        node["kind"] = json!("parenthesized-expression");
        drop(
            node.as_object_mut()
                .and_then(|fields| fields.remove("operation")),
        );
        node["constant_integer"] = json!(digits);
        node["span"]["begin"]["byte"] = json!(begin);
        node["span"]["begin"]["column"] = json!(begin - 18);
        node["span"]["end"]["byte"] = json!(end);
        node["span"]["end"]["column"] = json!(end - 18);
    }
    source
}

fn encode(source: &Value) -> Result<Vec<u8>, String> {
    serde_json::to_vec(source).map_err(|error| error.to_string())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "a mismatched C source or guest output must fail the test"
)]
fn nested_source_constants_execute_as_single_guest_a() -> Result<(), String> {
    let profile = target_profile("malbolge-2026").ok_or("missing current profile")?;
    for (parens, sign, digits, suffix) in [
        (3, None, "65", ""),
        (1, Some("+"), "65", ""),
        (2, Some("-"), "191", ""),
        (2, None, "65", "u"),
        (3, Some("+"), "65", ""),
    ] {
        let source = input(parens, sign, digits, suffix);
        let (wire, mode) = canonical_guest_typed_ir(&encode(&source)?)
            .map_err(|error| format!("{source} rejected: {error:?}"))?;
        assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
        let module = typed::canonical_module(&wire)
            .map_err(|error| format!("canonical typed IR: {error:?}"))?;
        let instructions = module
            .functions()
            .first()
            .and_then(|function| function.blocks().first())
            .ok_or("missing compiled function block")?
            .instructions();
        assert!(matches!(
            instructions.first().map(typed::LocatedInstruction::instruction),
            Some(typed::Instruction::ConstantInteger { constant, .. })
                if constant.bit_width() == 8 && constant.little_endian() == [65]
        ));
        let source_constant = instructions.first().ok_or("missing source constant")?;
        assert_eq!(source_constant.span().begin().byte(), 45 + parens);
        assert_eq!(
            source_constant.span().end().byte(),
            45 + parens
                + u32::from(sign.is_some())
                + u32::try_from(digits.len() + suffix.len()).unwrap_or_default()
        );
        let compiled = adapter::compile_canonical_typed_rotated_byte_literal(&wire, profile)
            .map_err(|error| format!("guest compilation: {error:?}"))?;
        let mut vm = ProfileMachine::from_source(profile, compiled.layout().source(), Vec::new())
            .map_err(|error| format!("load guest: {error:?}"))?;
        assert!(matches!(
            vm.run(compiled.layout().executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), &[65]);
    }
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "a changed guest effect or provenance must fail this regression"
)]
fn outer_signed_parentheses_execute_with_proven_source_span() -> Result<(), String> {
    let profile = target_profile("malbolge-2026").ok_or("missing current profile")?;
    for (parentheses, sign, digits) in [(1, "-", "191"), (2, "+", "65")] {
        let source = outer_sign_input(parentheses, sign, digits);
        let (wire, mode) = canonical_guest_typed_ir(&encode(&source)?)
            .map_err(|error| format!("{source} rejected: {error:?}"))?;
        assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
        let module = typed::canonical_module(&wire)
            .map_err(|error| format!("canonical typed IR: {error:?}"))?;
        let constant = module
            .functions()
            .first()
            .and_then(|function| function.blocks().first())
            .and_then(|block| block.instructions().first())
            .ok_or("missing guest constant")?;
        assert!(matches!(
            constant.instruction(),
            typed::Instruction::ConstantInteger { constant, .. }
                if constant.bit_width() == 8 && constant.little_endian() == [65]
        ));
        assert_eq!(constant.span().begin().byte(), 45);
        assert_eq!(
            constant.span().end().byte(),
            45 + 1
                + parentheses.saturating_mul(2)
                + u32::try_from(digits.len()).unwrap_or_default()
        );
        let guest = adapter::compile_canonical_typed_rotated_byte_literal(&wire, profile)
            .map_err(|error| format!("guest compilation: {error:?}"))?;
        let mut vm = ProfileMachine::from_source(profile, guest.layout().source(), Vec::new())
            .map_err(|error| format!("guest load: {error:?}"))?;
        assert!(matches!(
            vm.run(guest.layout().executed_code_positions().len()),
            Ok(RunOutcome::Terminated { .. })
        ));
        assert_eq!(vm.output(), b"A");
    }
    Ok(())
}

#[test]
fn forged_or_unbounded_wrapper_nodes_reject() -> Result<(), String> {
    let valid = input(2, Some("-"), "191", "");
    let mut invalid = valid.clone();
    invalid["nodes"][5]["constant_integer"] = json!("191");
    assert!(canonical_guest_typed_ir(&encode(&invalid)?).is_err());
    let mut invalid = valid.clone();
    invalid["nodes"][6]["parent"] = json!(3);
    assert!(canonical_guest_typed_ir(&encode(&invalid)?).is_err());
    let mut invalid = valid.clone();
    invalid["nodes"][6]["span"]["end"]["byte"] = json!(51);
    assert!(canonical_guest_typed_ir(&encode(&invalid)?).is_err());
    let mut invalid = valid.clone();
    invalid["nodes"][7]["operation"] = json!("~");
    assert!(canonical_guest_typed_ir(&encode(&invalid)?).is_err());
    let outer = outer_sign_input(1, "-", "191");
    let mut wrong_inner_value = outer.clone();
    wrong_inner_value["nodes"][6]["constant_integer"] = json!("-191");
    assert!(canonical_guest_typed_ir(&encode(&wrong_inner_value)?).is_err());
    let mut wrong_outer_sign = outer.clone();
    wrong_outer_sign["nodes"][5]["operation"] = json!("~");
    assert!(canonical_guest_typed_ir(&encode(&wrong_outer_sign)?).is_err());
    let mut wrong_paren_span = outer;
    wrong_paren_span["nodes"][6]["span"]["begin"]["byte"] = json!(45);
    assert!(canonical_guest_typed_ir(&encode(&wrong_paren_span)?).is_err());
    let too_deep = input(4, None, "65", "");
    assert!(canonical_guest_typed_ir(&encode(&too_deep)?).is_err());
    let mut invalid = input(2, None, "65", "u");
    invalid["nodes"][5]["operation"] = json!("floating-cast");
    assert!(canonical_guest_typed_ir(&encode(&invalid)?).is_err());
    Ok(())
}
