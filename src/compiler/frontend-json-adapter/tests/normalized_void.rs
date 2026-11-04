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
//   - Normalized JSON to typed wire and real two-step guest VM regressions.
// - Must-Not:
//   - Substitute host output or assume arbitrary C compilation is supported.
// - Allows:
//   - Inputs: synthetic exact Clang JSON nodes for one C void return.
//   - Outputs: admission/refusal and guest execution evidence.
//   - Side effects: isolated test execution only.
// - Split-When:
//   - Another frontend semantic family needs independent evidence.
// - Merge-When:
//   - Actual Clang generated void-return fixtures replace these boundaries.
// - Summary:
//   - Proves source-shaped JSON can reach canonical MCTI and guest VM.
// - Description:
//   - Refuses dropped/duplicated node meaning and source/profile drift.
// - Usage:
//   - `cargo test -p malbolge-c-frontend-json-adapter --test normalized_void`.
// - Defaults:
//   - The native pinned Clang binary is not needed by this test.
//

//! Real-VM and canonical-IR evidence for the normalized void JSON adapter.

#[path = "../../typed-echo-adapter/composition/lib.rs"]
pub mod adapter;

use adapter::compile_canonical_typed_empty_void;
use malbolge::{ProfileMachine, RunOutcome, target_profile};
use malbolge_c_frontend_json_adapter::{
    FrontendJsonError, canonical_void_typed_ir, decode_void_frontend_json, typed,
};
use serde as _;
use serde_json::{Value, json};

fn input() -> Value {
    json!({
        "schema_version": 1,
        "artifact_id": "malbolge-c-frontend-v1",
        "clang": {"version":"22.1.8", "target":"wasm32-unknown-unknown", "language":"c23"},
        "profile": {"abi_id":"malbolge-c32-v1", "target_profile":"malbolge-2026"},
        "source": {"id":"fixtures/void-return.c", "sha256":
            "d374bb94b03d6902deb8b5cb25cf2913d63e215d1a3ead8f758b4a514c24c584"},
        "nodes": [
            {"id":1, "parent":0, "kind":"function-declaration",
             "span": span(0,27), "name":"noop", "type":"fn()->void",
             "definition":"definition", "inline_specified":false,
             "linkage":"external", "storage_class":"none"},
            {"id":2, "parent":1, "kind":"compound-statement", "span":span(16,27)},
            {"id":3, "parent":2, "kind":"return-statement", "span":span(18,25)}
        ]
    })
}

fn span(begin: u32, end: u32) -> Value {
    json!({"begin":{"byte":begin,"line":1,"column":begin.saturating_add(1)},
           "end":{"byte":end,"line":1,"column":end.saturating_add(1)}})
}

#[expect(
    clippy::expect_used,
    reason = "test-only JSON Value serialization is infallible"
)]
fn bytes(source: &Value) -> Vec<u8> {
    serde_json::to_vec(source).expect("test JSON serializes")
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real guest and source assertions"
)]
fn normalized_clang_void_json_reaches_canonical_typed_ir_and_real_guest() -> Result<(), String> {
    let input = input();
    let projection = decode_void_frontend_json(&bytes(&input))
        .map_err(|error| format!("normalized JSON projection: {error:?}"))?;
    assert_eq!(projection.source_id(), "fixtures/void-return.c");
    assert!(
        projection
            .void_function()
            .is_some_and(typed::FrontendReturnVoidFunction::explicit_return)
    );
    let typed_wire = canonical_void_typed_ir(&bytes(&input))
        .map_err(|error| format!("canonical MCTI: {error:?}"))?;
    let decoded = typed::canonical_module(&typed_wire)
        .map_err(|error| format!("decode canonical MCTI: {error:?}"))?;
    assert_eq!(decoded.source_sha256(), projection.source_sha256());
    assert_eq!(
        decoded.functions().first().map(typed::Function::name),
        Some("noop")
    );
    let profile = target_profile("malbolge-2026").ok_or("missing current target profile")?;
    let compiled = compile_canonical_typed_empty_void(&typed_wire, profile)
        .map_err(|error| format!("compile canonical MCTI to VM: {error:?}"))?;
    let mut vm = ProfileMachine::from_source(profile, compiled.layout().source(), Vec::new())
        .map_err(|error| format!("load emitted guest: {error:?}"))?;
    assert!(matches!(
        vm.run(2),
        Ok(RunOutcome::Terminated { steps: 2, .. })
    ));
    assert!(vm.output().is_empty());
    Ok(())
}

#[test]
#[expect(
    clippy::indexing_slicing,
    clippy::shadow_unrelated,
    clippy::default_numeric_fallback,
    clippy::expect_used,
    clippy::too_many_lines,
    reason = "adversarial test JSON mutations target fixed fixture node paths"
)]
fn normalized_clang_json_rejects_effects_schema_drift_and_duplicate_fields() {
    let base = input();
    let mut cases = Vec::new();
    let mut changed = base.clone();
    changed["nodes"][1]["kind"] = json!("call-expression");
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][2]["parent"] = json!(1);
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][0]["type"] = json!("fn()->i32");
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][0]["inline_specified"] = json!(true);
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][0]["id"] = json!(12);
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][1]["id"] = json!(12);
    cases.push(changed);
    let mut changed = base.clone();
    changed["source"]["sha256"] =
        json!("AB74bb94b03d6902deb8b5cb25cf2913d63e215d1a3ead8f758b4a514c24c584");
    cases.push(changed);
    let mut changed = base.clone();
    changed["source"]["sha256"] =
        json!("zz74bb94b03d6902deb8b5cb25cf2913d63e215d1a3ead8f758b4a514c24c584");
    cases.push(changed);
    let mut changed = base.clone();
    changed["source"]["id"] = json!("../outside.c");
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][2]["type"] = json!("void");
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][2]["span"]["end"]["byte"] = json!(29);
    cases.push(changed);
    let mut changed = base.clone();
    changed["profile"]["target_profile"] = json!("malbolge-1998");
    cases.push(changed);
    let mut changed = base.clone();
    changed["clang"]["version"] = json!("23.1.2");
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][0]["extra"] = json!("ignored-by-wrong-parser");
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"][2]["span"] = changed["nodes"][1]["span"].clone();
    cases.push(changed);
    let mut changed = base.clone();
    changed["nodes"]
        .as_array_mut()
        .expect("nodes are array")
        .push(json!({
            "id":4, "parent":2, "kind":"call-expression", "span":span(18,25)
        }));
    cases.push(changed);
    for (index, candidate) in cases.iter().enumerate() {
        assert!(
            canonical_void_typed_ir(&bytes(candidate)).is_err(),
            "forged case {index}"
        );
    }
    let raw = bytes(&base);
    let original = String::from_utf8(raw).expect("compact JSON is UTF-8");
    let duplicated = original.replacen(
        "\"schema_version\":1",
        "\"schema_version\":1,\"schema_version\":1",
        1,
    );
    assert_ne!(duplicated, original);
    assert_eq!(
        canonical_void_typed_ir(duplicated.as_bytes()),
        Err(FrontendJsonError::Malformed)
    );
    assert_eq!(
        canonical_void_typed_ir(&vec![b' '; 1_048_577]),
        Err(FrontendJsonError::Malformed)
    );
}

#[test]
#[expect(
    clippy::cognitive_complexity,
    clippy::default_numeric_fallback,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    clippy::shadow_unrelated,
    clippy::too_many_lines,
    reason = "source-shaped JSON and real guest checks share one complete C fixture"
)]
fn empty_c_void_body_reaches_verified_implicit_guest_halt() -> Result<(), String> {
    let source = b"void noop(void) {}";
    let mut artifact = input();
    artifact["source"]["id"] = json!("fixtures/void-fallthrough.c");
    artifact["source"]["sha256"] =
        json!("13ef0aee923d209381921481fc34e0ac1fa6240b29d0d43e7056f4ecfc00fbcf");
    artifact["nodes"] = json!([
        {"id":1, "parent":0, "kind":"function-declaration",
         "span":span(0,18), "name":"noop", "type":"fn()->void",
         "definition":"definition", "inline_specified":false,
         "linkage":"external", "storage_class":"none"},
        {"id":2, "parent":1, "kind":"compound-statement", "span":span(16,18)}
    ]);
    let normalized = bytes(&artifact);
    let projected = decode_void_frontend_json(&normalized)
        .map_err(|error| format!("empty C body rejected: {error:?}"))?;
    let function = projected.void_function().ok_or("missing void function")?;
    assert!(
        !function.explicit_return(),
        "empty body is a fallthrough, not return;"
    );
    assert_eq!(function.return_span(), function.body_span());
    let typed_wire = canonical_void_typed_ir(&normalized)
        .map_err(|error| format!("empty C body canonical IR: {error:?}"))?;
    let decoded = typed::canonical_module(&typed_wire)
        .map_err(|error| format!("decode empty C body: {error:?}"))?;
    let [function] = decoded.functions() else {
        return Err(String::from("missing guest function"));
    };
    let [block] = function.blocks() else {
        return Err(String::from("missing guest return block"));
    };
    assert!(matches!(
        block.terminator(),
        typed::Terminator::Return { value: None }
    ));
    assert_eq!(block.terminator_span().begin().byte(), 16);
    assert_eq!(block.terminator_span().end().byte(), 18);
    let profile = target_profile("malbolge-2026").ok_or("missing current profile")?;
    let guest = compile_canonical_typed_empty_void(&typed_wire, profile)
        .map_err(|error| format!("compile empty C guest: {error:?}"))?;
    let mut vm = ProfileMachine::from_source(profile, guest.layout().source(), Vec::new())
        .map_err(|error| format!("load empty C guest: {error:?}"))?;
    assert!(matches!(
        vm.run(2),
        Ok(RunOutcome::Terminated { steps: 2, .. })
    ));
    assert!(vm.output().is_empty());
    assert_eq!(source.len(), 18);

    let mut unsupported = artifact.clone();
    unsupported["nodes"][1]["kind"] = json!("return-statement");
    assert_eq!(
        canonical_void_typed_ir(&bytes(&unsupported)),
        Err(FrontendJsonError::Unsupported)
    );
    let mut invalid_location = artifact;
    invalid_location["nodes"][1]["span"] = span(18, 20);
    assert_eq!(
        canonical_void_typed_ir(&bytes(&invalid_location)),
        Err(FrontendJsonError::InvalidTypedIr)
    );
    Ok(())
}

#[expect(
    clippy::default_numeric_fallback,
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "fixed normalized Clang JSON fixture fields"
)]
fn null_statement_input(explicit_return: bool) -> Value {
    let mut artifact = input();
    let (end, digest) = if explicit_return {
        (
            29,
            "da0b6e6b01ebc4961392983157795f7bd56fedcb93689e4e8af1e8ad575bff7e",
        )
    } else {
        (
            21,
            "1d54ba3f70dcaeb691fa09cf124b000137304e061b14365760b0ff7c55bbd096",
        )
    };
    artifact["source"]["id"] = json!("fixtures/void-null.c");
    artifact["source"]["sha256"] = json!(digest);
    artifact["nodes"] = json!([
        {"id":1, "parent":0, "kind":"function-declaration", "span":span(0,end),
         "name":"noop", "type":"fn()->void", "definition":"definition",
         "inline_specified":false, "linkage":"external", "storage_class":"none"},
        {"id":2, "parent":1, "kind":"compound-statement", "span":span(16,end)},
        {"id":3, "parent":2, "kind":"null-statement", "span":span(17,18)},
        {"id":4, "parent":2, "kind":"null-statement", "span":span(19,20)}
    ]);
    if explicit_return {
        artifact["nodes"]
            .as_array_mut()
            .expect("known array")
            .push(json!({"id":5, "parent":2, "kind":"return-statement",
                         "span":span(21,28)}));
    }
    artifact
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "fully specified source-shaped JSON and independently executed guest"
)]
fn source_null_statements_preserve_void_return_and_execute_under_real_vm() -> Result<(), String> {
    for explicit in [false, true] {
        let source = if explicit {
            b"void noop(void) {; ; return;}\n".as_slice()
        } else {
            b"void noop(void) {; ;}\n".as_slice()
        };
        assert_eq!(source.len(), if explicit { 30 } else { 22 });
        let artifact = null_statement_input(explicit);
        let projected = decode_void_frontend_json(&bytes(&artifact))
            .map_err(|error| format!("null-statement C projection: {error:?}"))?;
        assert_eq!(
            projected
                .void_function()
                .map(typed::FrontendReturnVoidFunction::explicit_return),
            Some(explicit)
        );
        let wire = canonical_void_typed_ir(&bytes(&artifact))
            .map_err(|error| format!("null-statement typed IR: {error:?}"))?;
        let decoded = typed::canonical_module(&wire)
            .map_err(|error| format!("re-admit null-statement MCTI: {error:?}"))?;
        assert_eq!(decoded.source_sha256(), projected.source_sha256());
        let profile = target_profile("malbolge-2026").ok_or("current profile missing")?;
        let generated = compile_canonical_typed_empty_void(&wire, profile)
            .map_err(|error| format!("null-statement guest lowering: {error:?}"))?;
        let mut machine =
            ProfileMachine::from_source(profile, generated.layout().source(), Vec::new())
                .map_err(|error| format!("null-statement VM load: {error:?}"))?;
        assert!(matches!(
            machine.run(2),
            Ok(RunOutcome::Terminated { steps: 2, .. })
        ));
        assert!(machine.output().is_empty());
    }
    Ok(())
}

#[test]
#[expect(
    clippy::default_numeric_fallback,
    clippy::expect_used,
    clippy::indexing_slicing,
    reason = "fixed JSON mutation slots must fail closed"
)]
fn void_null_statement_admission_rejects_effects_and_false_source_order() {
    let base = null_statement_input(true);
    let mut cases = Vec::new();
    for (index, field, replacement) in [
        (2, "kind", json!("call-expression")),
        (2, "parent", json!(1)),
        (2, "id", json!(4)),
        (2, "span", span(16, 18)),
        (2, "span", span(17, 19)),
        (2, "span", span(29, 30)),
        (3, "span", span(16, 17)),
        (3, "span", span(17, 18)),
        (4, "parent", json!(1)),
        (4, "id", json!(7)),
        (4, "span", span(19, 22)),
    ] {
        let mut candidate = base.clone();
        candidate["nodes"][index][field] = replacement;
        cases.push(candidate);
    }
    {
        let mut altered = base.clone();
        altered["nodes"][3]["reference"] = json!("external:putchar");
        cases.push(altered);
    }
    {
        let mut altered = base.clone();
        altered["nodes"]
            .as_array_mut()
            .expect("known nodes")
            .swap(3, 4);
        cases.push(altered);
    }
    let mut altered = base;
    altered["nodes"]
        .as_array_mut()
        .expect("known nodes")
        .swap(2, 4);
    cases.push(altered);
    for (index, candidate) in cases.iter().enumerate() {
        assert!(
            canonical_void_typed_ir(&bytes(candidate)).is_err(),
            "modified null statement {index} unexpectedly admitted"
        );
    }
}

#[expect(
    clippy::default_numeric_fallback,
    clippy::indexing_slicing,
    reason = "source-shaped nested Clang AST with fixed positions and identities"
)]
fn nested_null_input(explicit_return: bool) -> Value {
    let mut artifact = input();
    let (end, digest, nodes) = if explicit_return {
        (
            33,
            "cc96b32238d65b5ad66aa28117c8ca466f8f4be8c4f8a65e4374068bc5b7c71d",
            json!([
                {"id":1,"parent":0,"kind":"function-declaration","span":span(0,33),
                 "name":"noop","type":"fn()->void","definition":"definition",
                 "inline_specified":false,"linkage":"external","storage_class":"none"},
                {"id":2,"parent":1,"kind":"compound-statement","span":span(16,33)},
                {"id":3,"parent":2,"kind":"null-statement","span":span(17,18)},
                {"id":4,"parent":2,"kind":"compound-statement","span":span(19,32)},
                {"id":5,"parent":4,"kind":"null-statement","span":span(21,22)},
                {"id":6,"parent":4,"kind":"return-statement","span":span(23,30)}
            ]),
        )
    } else {
        (
            25,
            "9cf8980576e0b85e6c8800f77226e7a1ed89c0690a23e4d4ec5f9eab9465be2b",
            json!([
                {"id":1,"parent":0,"kind":"function-declaration","span":span(0,25),
                 "name":"noop","type":"fn()->void","definition":"definition",
                 "inline_specified":false,"linkage":"external","storage_class":"none"},
                {"id":2,"parent":1,"kind":"compound-statement","span":span(16,25)},
                {"id":3,"parent":2,"kind":"compound-statement","span":span(17,24)},
                {"id":4,"parent":3,"kind":"null-statement","span":span(18,19)},
                {"id":5,"parent":3,"kind":"compound-statement","span":span(20,23)},
                {"id":6,"parent":5,"kind":"null-statement","span":span(21,22)}
            ]),
        )
    };
    artifact["source"]["id"] = json!("fixtures/nested-void.c");
    artifact["source"]["sha256"] = json!(digest);
    artifact["nodes"] = nodes;
    assert_eq!(
        artifact["nodes"][0]["span"]["end"]["byte"],
        json!(end),
        "nested function span must cover the source ending brace"
    );
    artifact
}

#[test]
#[expect(
    clippy::panic_in_result_fn,
    reason = "real guest VM execution is part of source-node admission"
)]
fn nested_effect_free_compound_scopes_reach_canonical_guest() -> Result<(), String> {
    for explicit in [false, true] {
        let artifact = nested_null_input(explicit);
        let projected = decode_void_frontend_json(&bytes(&artifact))
            .map_err(|error| format!("nested C projection: {error:?}"))?;
        assert_eq!(
            projected
                .void_function()
                .map(typed::FrontendReturnVoidFunction::explicit_return),
            Some(explicit)
        );
        let wire = canonical_void_typed_ir(&bytes(&artifact))
            .map_err(|error| format!("nested C canonical typed IR: {error:?}"))?;
        let admitted = typed::canonical_module(&wire)
            .map_err(|error| format!("nested C MCTI re-admission: {error:?}"))?;
        assert_eq!(admitted.source_sha256(), projected.source_sha256());
        let profile = target_profile("malbolge-2026").ok_or("current profile missing")?;
        let generated = compile_canonical_typed_empty_void(&wire, profile)
            .map_err(|error| format!("nested C compiled guest: {error:?}"))?;
        let mut vm = ProfileMachine::from_source(profile, generated.layout().source(), Vec::new())
            .map_err(|error| format!("nested guest VM load: {error:?}"))?;
        assert!(matches!(
            vm.run(2),
            Ok(RunOutcome::Terminated { steps: 2, .. })
        ));
        assert!(vm.output().is_empty());
    }
    Ok(())
}

#[test]
#[expect(
    clippy::default_numeric_fallback,
    clippy::indexing_slicing,
    clippy::expect_used,
    reason = "adversarial nested C AST mutation probes source and side-effect gates"
)]
fn nested_compound_rejects_forged_parent_overlap_and_effects() {
    let base = nested_null_input(true);
    let mut cases = Vec::new();
    for (index, field, value) in [
        (3, "kind", json!("call-expression")),
        (3, "parent", json!(1)),
        (3, "parent", json!(3)),
        (3, "span", span(18, 20)),
        (3, "span", span(19, 33)),
        (4, "parent", json!(2)),
        (4, "span", span(20, 22)),
        (5, "parent", json!(2)),
        (5, "span", span(31, 34)),
        (5, "span", span(20, 29)),
        (5, "id", json!(7)),
    ] {
        let mut candidate = base.clone();
        candidate["nodes"][index][field] = value;
        cases.push(candidate);
    }
    let mut with_effect = base.clone();
    with_effect["nodes"][3]["type"] = json!("void");
    cases.push(with_effect);
    let mut with_reordered = base;
    with_reordered["nodes"]
        .as_array_mut()
        .expect("nodes")
        .swap(3, 4);
    cases.push(with_reordered);
    for (index, candidate) in cases.iter().enumerate() {
        assert!(
            canonical_void_typed_ir(&bytes(candidate)).is_err(),
            "nested forged candidate {index} admitted"
        );
    }
}

#[test]
#[expect(
    clippy::default_numeric_fallback,
    clippy::indexing_slicing,
    clippy::panic_in_result_fn,
    reason = "explicit scope-sibling preorder requires true pop-to-ancestor verification"
)]
fn empty_and_sibling_compounds_preserve_fallthrough_in_guest() -> Result<(), String> {
    let mut artifact = input();
    artifact["source"]["id"] = json!("fixtures/sibling-void.c");
    artifact["source"]["sha256"] =
        json!("689f6dfb89a7605a895f00d61be658ce3011f660e744abe04168bdca371ad67d");
    artifact["nodes"] = json!([
        {"id":1,"parent":0,"kind":"function-declaration","span":span(0,25),
         "name":"noop","type":"fn()->void","definition":"definition",
         "inline_specified":false,"linkage":"external","storage_class":"none"},
        {"id":2,"parent":1,"kind":"compound-statement","span":span(16,25)},
        {"id":3,"parent":2,"kind":"compound-statement","span":span(17,19)},
        {"id":4,"parent":2,"kind":"compound-statement","span":span(20,23)},
        {"id":5,"parent":4,"kind":"null-statement","span":span(21,22)},
        {"id":6,"parent":2,"kind":"null-statement","span":span(23,24)}
    ]);
    let wire = canonical_void_typed_ir(&bytes(&artifact))
        .map_err(|error| format!("nested sibling admission: {error:?}"))?;
    let decoded = typed::canonical_module(&wire)
        .map_err(|error| format!("nested sibling canonical admission: {error:?}"))?;
    assert_eq!(decoded.source_id(), "fixtures/sibling-void.c");
    let profile = target_profile("malbolge-2026").ok_or("missing profile")?;
    let generated = compile_canonical_typed_empty_void(&wire, profile)
        .map_err(|error| format!("sibling guest compilation: {error:?}"))?;
    let mut vm = ProfileMachine::from_source(profile, generated.layout().source(), Vec::new())
        .map_err(|error| format!("sibling VM load: {error:?}"))?;
    assert!(matches!(
        vm.run(2),
        Ok(RunOutcome::Terminated { steps: 2, .. })
    ));
    assert!(vm.output().is_empty());

    let mut overlap = artifact.clone();
    overlap["nodes"][3]["span"] = span(18, 23);
    assert_eq!(
        canonical_void_typed_ir(&bytes(&overlap)),
        Err(FrontendJsonError::Unsupported)
    );
    let mut wrong_parent = artifact;
    wrong_parent["nodes"][5]["parent"] = json!(4);
    assert_eq!(
        canonical_void_typed_ir(&bytes(&wrong_parent)),
        Err(FrontendJsonError::Unsupported)
    );
    Ok(())
}
