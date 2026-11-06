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

//! Re-admit pinned Clang local initialization and ordered assignment ASTs.

use malbolge as _;
use malbolge_c_frontend_json_adapter::{
    FrontendGuestMode, FrontendJsonError, canonical_guest_typed_ir, typed,
};
use serde as _;
use serde_json::{Value, json};

const PINNED: &[u8] = include_bytes!(
    "../../../../tests/compiler/c-frontend/golden/local_initialized_output.json"
);
const REASSIGNED: &[u8] = include_bytes!(
    "../../../../tests/compiler/c-frontend/golden/local_reassigned_output.json"
);
const ARITHMETIC: &[u8] = include_bytes!(
    "../../../../tests/compiler/c-frontend/golden/local_arithmetic_output.json"
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
    clippy::panic_in_result_fn,
    reason = "source-bound assignment proof"
)]
fn ordered_dead_stores_leave_the_last_clang_definition() -> Result<(), String> {
    let (wire, mode) = canonical_guest_typed_ir(REASSIGNED)
        .map_err(|error| format!("assignment lowering: {error:?}"))?;
    assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
    let module = typed::canonical_module(&wire)
        .map_err(|error| format!("typed admission: {error:?}"))?;
    assert_eq!(module.source_id(), "tests/local-reassigned-output-v1");
    let [constant, output] = module.functions()[0].blocks()[0].instructions()
    else {
        return Err(String::from("expected live SSA value and guest output"));
    };
    assert!(matches!(
        constant.instruction(),
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
    assert_eq!(constant.span().begin().line(), 37);
    assert_eq!(output.span().begin().line(), 38);
    assert_eq!(typed::canonical_bytes(&module), Ok(wire));
    Ok(())
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "source-bound arithmetic proof"
)]
fn prior_local_value_drives_checked_arithmetic() -> Result<(), String> {
    let (wire, mode) = canonical_guest_typed_ir(ARITHMETIC)
        .map_err(|error| format!("arithmetic lowering: {error:?}"))?;
    assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
    let module = typed::canonical_module(&wire)
        .map_err(|error| format!("typed admission: {error:?}"))?;
    assert_eq!(module.source_id(), "tests/local-arithmetic-output-v1");
    let [constant, output] = module.functions()[0].blocks()[0].instructions()
    else {
        return Err(String::from(
            "expected source-derived SSA byte and output",
        ));
    };
    assert!(matches!(
        constant.instruction(),
        typed::Instruction::ConstantInteger { constant, .. }
            if constant.bit_width() == 8 && constant.little_endian() == [65]
    ));
    assert!(matches!(
        output.instruction(),
        typed::Instruction::ByteOutput { value } if value.value() == 0
    ));
    assert_eq!(constant.span().begin().line(), 38);
    assert_eq!(output.span().begin().line(), 39);
    assert_eq!(typed::canonical_bytes(&module), Ok(wire));
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    reason = "pinned arithmetic AST indices"
)]
fn arithmetic_mutations_reject_foreign_reads_and_unsupported_effects() {
    let original: Value = serde_json::from_slice(ARITHMETIC).unwrap();
    for (index, key, value) in [
        (7, "operation", json!("*")),
        (7, "type", json!("i32")),
        (8, "operation", json!("integral-cast")),
        (8, "parent", json!(6)),
        (9, "reference", json!("other@1175")),
        (9, "type", json!("i32")),
        (10, "constant_integer", json!("256")),
        (10, "literal", json!("7")),
        (13, "operation", json!("&")),
        (15, "reference", json!("other@1175")),
        (19, "operation", json!("*")),
        (21, "reference", json!("other@1175")),
        (22, "constant_integer", json!("-6")),
    ] {
        let mut changed = original.clone();
        changed["nodes"][index][key] = value;
        assert_eq!(
            canonical_guest_typed_ir(&serialize(&changed)),
            Err(FrontendJsonError::Unsupported),
            "arithmetic node {index} / {key} must not be silently ignored"
        );
    }
    // The admitted machine-byte domain excludes C arithmetic that grows
    // beyond 255 or would wrap an unsigned subtraction.
    let mut overflow = original.clone();
    overflow["nodes"][4]["constant_integer"] = json!("250");
    overflow["nodes"][4]["literal"] = json!("250");
    assert_eq!(
        canonical_guest_typed_ir(&serialize(&overflow)),
        Err(FrontendJsonError::Unsupported)
    );
    let mut underflow = original.clone();
    underflow["nodes"][22]["constant_integer"] = json!("72");
    underflow["nodes"][22]["literal"] = json!("72");
    assert_eq!(
        canonical_guest_typed_ir(&serialize(&underflow)),
        Err(FrontendJsonError::Unsupported)
    );
    // A valid arithmetic operand changes the computed SSA value.
    let mut changed = original;
    changed["nodes"][10]["constant_integer"] = json!("9");
    changed["nodes"][10]["literal"] = json!("9");
    let (wire, _) = canonical_guest_typed_ir(&serialize(&changed)).unwrap();
    let module = typed::canonical_module(&wire).unwrap();
    assert!(matches!(
        module.functions()[0].blocks()[0].instructions()[0].instruction(),
        typed::Instruction::ConstantInteger { constant, .. }
            if constant.little_endian() == [64]
    ));
}

#[test]
#[expect(
    clippy::indexing_slicing,
    reason = "exact source-backed node identities"
)]
fn reassignment_mutations_are_not_discarded_or_forged() {
    let original: Value = serde_json::from_slice(REASSIGNED).unwrap();
    for (index, key, value) in [
        (5, "operation", json!("+=")),
        (5, "type", json!("i32")),
        (5, "reference", json!("value@1184")),
        (5, "parent", json!(4)),
        (6, "reference", json!("other@1152")),
        (6, "type", json!("i32")),
        (7, "constant_integer", json!("256")),
        (7, "literal", json!("77")),
        (8, "operation", json!("-")),
        (9, "reference", json!("other@1152")),
        (10, "constant_integer", json!("-1")),
        (10, "name", json!("unexpected")),
        (16, "reference", json!("wrong@1152")),
    ] {
        let mut changed = original.clone();
        changed["nodes"][index][key] = value;
        assert_eq!(
            canonical_guest_typed_ir(&serialize(&changed)),
            Err(FrontendJsonError::Unsupported),
            "assignment node {index} / {key} silently lost its effect"
        );
    }
    let mut extra = original.clone();
    extra["nodes"].as_array_mut().unwrap().push(json!({
        "id":18,"parent":2,"kind":"if-statement",
        "span":original["nodes"][11]["span"]
    }));
    assert_eq!(
        canonical_guest_typed_ir(&serialize(&extra)),
        Err(FrontendJsonError::Unsupported)
    );
    // Replacing the final write changes the live value, not the initializer.
    let mut changed = original;
    changed["nodes"][10]["constant_integer"] = json!("0");
    changed["nodes"][10]["literal"] = json!("0");
    let (wire, mode) = canonical_guest_typed_ir(&serialize(&changed)).unwrap();
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

const MULTI_LOCAL: &[u8] = include_bytes!(
    "../../../../tests/compiler/c-frontend/golden/local_multi_output.json"
);

#[test]
fn multiple_local_definitions_drive_guest_byte() {
    let (wire, mode) = canonical_guest_typed_ir(MULTI_LOCAL).unwrap();
    assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
    let module = typed::canonical_module(&wire).unwrap();
    assert_eq!(module.source_id(), "tests/local-multi-output-v1");
    let [constant, output] = module.functions()[0].blocks()[0].instructions()
    else {
        panic!("expected one folded byte and guest output");
    };
    assert!(matches!(
        constant.instruction(),
        typed::Instruction::ConstantInteger { constant, .. }
            if constant.bit_width() == 8 && constant.little_endian() == [65]
    ));
    assert!(matches!(
        output.instruction(),
        typed::Instruction::ByteOutput { value } if value.value() == 0
    ));
    assert_eq!(constant.span().begin().line(), 39);
    assert_eq!(typed::canonical_bytes(&module), Ok(wire));
}

#[test]
fn multi_local_foreign_symbols_and_extra_effects_fail_closed() {
    let original: Value = serde_json::from_slice(MULTI_LOCAL).unwrap();
    for (index, key, value) in [
        (12, "reference", json!("b@999")),
        (14, "reference", json!("a@999")),
        (13, "operation", json!("integral-cast")),
        (10, "operation", json!("*")),
        (9, "storage_duration", json!("static")),
        (22, "reference", json!("a@999")),
        (27, "reference", json!("external:puts")),
    ] {
        let mut changed = original.clone();
        changed["nodes"][index][key] = value;
        assert_eq!(
            canonical_guest_typed_ir(&serialize(&changed)),
            Err(FrontendJsonError::Unsupported),
            "admitted mutation of node {index} field {key}",
        );
    }
    let mut changed = original;
    changed["nodes"][15]["kind"] = json!("if-statement");
    assert_eq!(
        canonical_guest_typed_ir(&serialize(&changed)),
        Err(FrontendJsonError::Unsupported),
    );
}

const CONDITIONAL: &[u8] = include_bytes!(
    "../../../../tests/compiler/c-frontend/golden/local_conditional_output.json"
);
const CONDITIONAL_ELSE: &[u8] = include_bytes!(concat!(
    "../../../../tests/compiler/c-frontend/golden/",
    "local_conditional_else_output.json"
));

#[test]
fn exact_conditional_branches_select_source_bound_ssa_values() {
    for (source, id, definition_line) in [
        (CONDITIONAL, "tests/local-conditional-output-v1", 39),
        (
            CONDITIONAL_ELSE,
            "tests/local-conditional-else-output-v1",
            41,
        ),
    ] {
        let (wire, mode) = canonical_guest_typed_ir(source).unwrap();
        assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
        let module = typed::canonical_module(&wire).unwrap();
        assert_eq!(module.source_id(), id);
        let [constant, output] =
            module.functions()[0].blocks()[0].instructions()
        else {
            panic!("expected one selected byte and its output");
        };
        assert!(matches!(
            constant.instruction(),
            typed::Instruction::ConstantInteger { constant, .. }
                if constant.bit_width() == 8 && constant.little_endian() == [65]
        ));
        assert!(matches!(
            output.instruction(),
            typed::Instruction::ByteOutput { value } if value.value() == 0
        ));
        assert_eq!(constant.span().begin().line(), definition_line);
        assert_eq!(typed::canonical_bytes(&module), Ok(wire));
    }
}

#[test]
fn conditional_foreign_reads_metadata_and_unproven_branches_reject() {
    let original: Value = serde_json::from_slice(CONDITIONAL).unwrap();
    for (index, key, value) in [
        (15, "kind", json!("for-statement")),
        (16, "operation", json!("!=")),
        (17, "type", json!("i32")),
        (18, "operation", json!("|")),
        (20, "reference", json!("a@999")),
        (22, "type", json!("i32")),
        (23, "reference", json!("result@1194")),
        (24, "parent", json!(2)),
        (26, "operation", json!("*")),
        (30, "kind", json!("call-expression")),
        (33, "operation", json!("*")),
        (36, "reference", json!("result@999")),
    ] {
        let mut altered = original.clone();
        altered["nodes"][index][key] = value;
        assert_eq!(
            canonical_guest_typed_ir(&serialize(&altered)),
            Err(FrontendJsonError::Unsupported),
            "admitted condition mutation at node {index} / {key}",
        );
    }
    let mut changed = original;
    let _removed = changed["nodes"].as_array_mut().unwrap().remove(30);
    assert_eq!(
        canonical_guest_typed_ir(&serialize(&changed)),
        Err(FrontendJsonError::Unsupported)
    );
}

const EXPRESSION_OUTPUT: &[u8] = include_bytes!(
    "../../../../tests/compiler/c-frontend/golden/local_expression_output.json"
);

#[test]
fn conditional_expression_argument_preserves_live_source_and_byte() {
    let (wire, mode) = canonical_guest_typed_ir(EXPRESSION_OUTPUT).unwrap();
    assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
    let module = typed::canonical_module(&wire).unwrap();
    assert_eq!(module.source_id(), "tests/local-expression-output-v1");
    let [constant, output] = module.functions()[0].blocks()[0].instructions()
    else {
        panic!("expected one expression result and guest output");
    };
    assert!(matches!(
        constant.instruction(),
        typed::Instruction::ConstantInteger { constant, .. }
            if constant.bit_width() == 8 && constant.little_endian() == [65]
    ));
    assert_eq!(constant.span().begin().line(), 43);
    assert!(matches!(
        output.instruction(),
        typed::Instruction::ByteOutput { value } if value.value() == 0
    ));
    assert_eq!(typed::canonical_bytes(&module), Ok(wire));
}

#[test]
fn expression_argument_mutations_fail_closed() {
    let original: Value = serde_json::from_slice(EXPRESSION_OUTPUT).unwrap();
    for (index, key, value) in [
        (40, "operation", json!("lvalue-to-rvalue")),
        (41, "parent", json!(38)),
        (41, "type", json!("i32")),
        (42, "operation", json!("+=")),
        (42, "type", json!("i32")),
        (43, "operation", json!("integral-cast")),
        (44, "reference", json!("other@1208")),
        (45, "constant_integer", json!("256")),
        (45, "literal", json!("77")),
    ] {
        let mut changed = original.clone();
        changed["nodes"][index][key] = value;
        assert_eq!(
            canonical_guest_typed_ir(&serialize(&changed)),
            Err(FrontendJsonError::Unsupported),
            "expression argument node {index} / {key} was unchecked"
        );
    }
    let mut extra = original;
    let call_span = extra["nodes"][37]["span"].clone();
    extra["nodes"].as_array_mut().unwrap().push(json!({
        "id":47,"parent":2,"kind":"call-expression",
        "span":call_span,
        "reference":"external:putchar","type":"i32"
    }));
    assert_eq!(
        canonical_guest_typed_ir(&serialize(&extra)),
        Err(FrontendJsonError::Unsupported)
    );
}

const MASKED_SUM: &[u8] = include_bytes!(
    "../../../../tests/compiler/c-frontend/golden/local_masked_sum_output.json"
);

#[test]
fn masked_wide_unsigned_sum_preserves_source_and_guest_byte() {
    let (wire, mode) = canonical_guest_typed_ir(MASKED_SUM).unwrap();
    assert_eq!(mode, FrontendGuestMode::SeededByteLiteral);
    let module = typed::canonical_module(&wire).unwrap();
    assert_eq!(module.source_id(), "tests/local-masked-sum-output-v1");
    let [constant, output] = module.functions()[0].blocks()[0].instructions()
    else {
        panic!("expected masked sum result and guest output");
    };
    assert!(matches!(
        constant.instruction(),
        typed::Instruction::ConstantInteger { constant, .. }
            if constant.bit_width() == 8 && constant.little_endian() == [65]
    ));
    assert_eq!(constant.span().begin().line(), 41);
    assert!(matches!(
        output.instruction(),
        typed::Instruction::ByteOutput { value } if value.value() == 0
    ));
    assert_eq!(typed::canonical_bytes(&module), Ok(wire));
}

#[test]
fn masked_sum_operator_and_parenthesis_mutations_reject() {
    let original: Value = serde_json::from_slice(MASKED_SUM).unwrap();
    for (index, key, value) in [
        (10, "operation", json!("+")),
        (11, "parent", json!(10)),
        (11, "type", json!("i32")),
        (12, "operation", json!("*")),
        (12, "parent", json!(10)),
        (17, "constant_integer", json!("256")),
        (19, "operation", json!("!=")),
    ] {
        let mut changed = original.clone();
        changed["nodes"][index][key] = value;
        assert_eq!(
            canonical_guest_typed_ir(&serialize(&changed)),
            Err(FrontendJsonError::Unsupported),
            "changed node {} field {key}",
            index + 1,
        );
    }
}
