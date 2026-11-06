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
//   - Pinned Clang local-initializer source-use and SSA admission regression.
// - Must-Not:
//   - Infer guest behavior from host output or overlook mutations/aliasing.
// - Allows:
//   - Inputs: native frontend golden and deliberately changed node records.
//   - Outputs: canonical MCTI, precise guest mode, or explicit rejection.
//   - Side effects: none.
// - Split-When:
//   - General local-state tests cover this source-backed projection.
// - Merge-When:
//   - Full C compiler SSA lowering owns the local-reference matrix.
// - Summary:
//   - Proves a referenced local is not merely an ignored declaration.
// - Description:
//   - Real VM execution is separately verified by the Python process test.
// - Usage:
//   - cargo test -p malbolge-c-frontend-json-adapter --test
//     normalized_local_output
// - Defaults:
//   - Extra source effects and unsupported state cannot publish MCTI.

//! Independently re-admit the exact pinned Clang automatic-local AST shape.

use malbolge as _;
use malbolge_c_frontend_json_adapter::{
    FrontendGuestMode, FrontendJsonError, canonical_guest_typed_ir, typed,
};
use serde as _;
use serde_json::{Value, json};

const PINNED: &[u8] = include_bytes!(
    "../../../../tests/compiler/c-frontend/golden/local_initialized_output.json"
);

#[expect(clippy::expect_used, reason = "fixed Clang JSON fixture")]
fn source() -> Value {
    serde_json::from_slice(PINNED).expect("pinned frontend JSON")
}

#[expect(clippy::expect_used, reason = "test-only JSON serialization")]
fn serialize(value: &Value) -> Vec<u8> {
    serde_json::to_vec(value).expect("synthetic Clang JSON")
}

#[test]
#[expect(clippy::panic_in_result_fn, reason = "exact source SSA test")]
fn automatic_local_is_source_bound_and_typed() -> Result<(), String> {
    let (wire, mode) = canonical_guest_typed_ir(PINNED)
        .map_err(|error| format!("local lowering: {error:?}"))?;
    assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
    let module = typed::canonical_module(&wire)
        .map_err(|error| format!("typed admission: {error:?}"))?;
    assert_eq!(module.source_id(), "tests/local-initialized-output-v1");
    assert_eq!(module.functions().len(), 1);
    let instructions = module.functions()[0].blocks()[0].instructions();
    let [initialized, output] = instructions else {
        return Err(String::from("expected local definition and byte output"));
    };
    assert!(matches!(
        initialized.instruction(),
        typed::Instruction::ConstantInteger {
            constant,
            result,
            type_id,
        } if constant.bit_width() == 8
            && constant.little_endian() == [65]
            && result.value() == 0
            && type_id.value() == 0
    ));
    assert!(matches!(
        output.instruction(),
        typed::Instruction::ByteOutput { value } if value.value() == 0
    ));
    assert_eq!(initialized.span().begin().line(), 35);
    assert_eq!(output.span().begin().line(), 36);
    assert!(matches!(
        module.functions()[0].blocks()[0].terminator(),
        typed::Terminator::Return { value: None }
    ));
    assert_eq!(typed::canonical_bytes(&module), Ok(wire));
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    reason = "fixed closed Clang nodes"
)]
fn zero_initializer_remains_a_guest_zero_output() {
    let mut input = source();
    input["nodes"][4]["constant_integer"] = json!("0");
    input["nodes"][4]["literal"] = json!("0");
    let (wire, mode) = canonical_guest_typed_ir(&serialize(&input)).unwrap();
    assert_eq!(mode, FrontendGuestMode::InitialZeroOutput);
    let module = typed::canonical_module(&wire).unwrap();
    assert!(matches!(
        module.functions()[0].blocks()[0].instructions()[0].instruction(),
        typed::Instruction::ConstantInteger { constant, .. }
            if constant.little_endian() == [0]
    ));
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::too_many_lines,
    reason = "source-backed unsupported C and metadata mutation matrix"
)]
fn changed_local_or_undeclared_effects_fail_closed() {
    let original = source();
    for (index, key, value) in [
        (3, "storage_duration", json!("static")),
        (3, "storage_duration", json!("thread")),
        (3, "type", json!("i32")),
        (3, "reference", json!("other@1152")),
        (3, "reference", Value::Null),
        (3, "name", json!("other")),
        (4, "constant_integer", json!("256")),
        (4, "literal", json!("77")),
        (4, "constant_integer", json!("4294967295")),
        (4, "constant_integer", json!("-1")),
        (5, "reference", json!("external:puts")),
        (5, "definition", json!("definition")),
        (8, "operation", json!("lvalue-to-rvalue")),
        (9, "operation", json!("integral-cast")),
        (10, "reference", json!("other@1152")),
        (10, "reference", json!("value@999")),
        (10, "type", json!("i32")),
    ] {
        let mut altered = original.clone();
        altered["nodes"][index][key] = value;
        assert_eq!(
            canonical_guest_typed_ir(&serialize(&altered)),
            Err(FrontendJsonError::Unsupported),
            "changed node {index} / {key} was silently lowered",
        );
    }
    for kind in ["binary-expression", "for-statement", "if-statement"] {
        let mut changed = original.clone();
        changed["nodes"][2]["kind"] = json!(kind);
        assert_eq!(
            canonical_guest_typed_ir(&serialize(&changed)),
            Err(FrontendJsonError::Unsupported),
            "unexpectedly admitted {kind}",
        );
    }
    let mut extra = original.clone();
    extra["nodes"].as_array_mut().unwrap().push(json!({
        "id":12,"parent":2,"kind":"binary-expression",
        "span":original["nodes"][5]["span"],
        "operation":"="
    }));
    assert_eq!(
        canonical_guest_typed_ir(&serialize(&extra)),
        Err(FrontendJsonError::Unsupported)
    );
}
