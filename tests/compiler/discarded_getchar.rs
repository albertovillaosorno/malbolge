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
//   - Pinned Clang signed-getchar source admission and EOF-unsafe output
//     refusal.
// - Must-Not:
//   - Treat signed EOF as an unconditional successful u8 byte.
// - Allows:
//   - Inputs: frozen C23 sources and pinned normalized frontend JSON.
//   - Outputs: canonical signed MCTI effects or deterministic Unsupported.
//   - Side effects: none.
// - Split-When:
//   - Source-authenticated signed-EOF output becomes independently executable.
// - Merge-When:
//   - The source byte-effect tests own every signed input/output projection.
// - Summary:
//   - Getchar discarded results preserve i32, while direct output refuses EOF.

use super::super::typed::{Instruction, TypeDef, canonical_module};
use super::super::{
    FrontendGuestMode, FrontendJsonError, canonical_guest_typed_ir_with_source,
    source_byte_echo as echo,
};

const SINGLE_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/discarded_getchar_one.c");
const SINGLE_JSON: &[u8] =
    include_bytes!("c-frontend/golden/discarded_getchar_one.json");
const DOUBLE_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/discarded_getchar_two.c");
const DOUBLE_JSON: &[u8] =
    include_bytes!("c-frontend/golden/discarded_getchar_two.json");
const DIRECT_OUTPUT_SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/direct_getchar_putchar_eof.c");
const DIRECT_OUTPUT_JSON: &[u8] =
    include_bytes!("c-frontend/golden/direct_getchar_putchar_eof.json");

#[test]
fn discarded_getchar_is_signed_and_tracks_each_source_read() {
    for (source, json, count) in [
        (SINGLE_SOURCE, SINGLE_JSON, 1),
        (DOUBLE_SOURCE, DOUBLE_JSON, 2),
    ] {
        let (canonical, mode) =
            canonical_guest_typed_ir_with_source(json, Some(source))
                .expect("source-proven discarded reads are executable at EOF");
        assert_eq!(mode, FrontendGuestMode::DiscardedGetchar);
        let module = canonical_module(&canonical).unwrap();
        let instructions = module.functions()[0].blocks()[0].instructions();
        assert_eq!(instructions.len(), count);
        for (index, instruction) in instructions.iter().enumerate() {
            let Instruction::Getchar { result, type_id } =
                instruction.instruction()
            else {
                panic!(
                    "a discarded i32 getchar must not become a u8 byte input"
                );
            };
            assert_eq!(result.value(), index as u32);
            assert!(module.types().iter().any(|entry| {
                entry.id() == *type_id && *entry.definition() == TypeDef::I32
            }));
            assert_eq!(instruction.span().begin().line(), 2);
        }
    }
}

#[test]
fn signed_getchar_source_rejects_stale_or_forged_frontend_evidence() {
    let mut changed_source = SINGLE_SOURCE.to_vec();
    let needle = b"getchar();";
    let index = changed_source
        .windows(needle.len())
        .position(|window| window == needle)
        .unwrap();
    changed_source[index] = b'G';
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            SINGLE_JSON,
            Some(&changed_source)
        ),
        Err(FrontendJsonError::Unsupported)
    ));
    let mut forged: serde_json::Value =
        serde_json::from_slice(SINGLE_JSON).unwrap();
    forged["nodes"][2]["reference"] = serde_json::json!("external:putchar");
    assert!(matches!(
        canonical_guest_typed_ir_with_source(
            &serde_json::to_vec(&forged).unwrap(),
            Some(SINGLE_SOURCE)
        ),
        Err(FrontendJsonError::Unsupported)
    ));
}

#[test]
fn standalone_put_get_refuses_without_signed_eof_to_byte_conversion() {
    for source in [None, Some(DIRECT_OUTPUT_SOURCE)] {
        assert_eq!(
            canonical_guest_typed_ir_with_source(DIRECT_OUTPUT_JSON, source),
            Err(FrontendJsonError::Unsupported)
        );
    }
}

#[test]
fn signed_direct_eof_output_in_every_loop_kind_requires_its_own_conversion() {
    use super::super::source_byte_echo::is_unchecked_direct_loop_eof_echo;

    // Wrap the existing source-normalized direct output in a synthetic loop
    // ancestor. This is a refusal-only structural test, never a source proof:
    // the real frontend separately authenticates all Clang/source topology.
    for kind in ["for-statement", "while-statement", "do-statement"] {
        let mut value: serde_json::Value =
            serde_json::from_slice(DIRECT_OUTPUT_JSON).unwrap();
        let nodes = value["nodes"].as_array_mut().unwrap();
        let mut wrapper = nodes[2].clone();
        wrapper["id"] = serde_json::json!(9);
        wrapper["parent"] = serde_json::json!(2);
        wrapper["kind"] = serde_json::json!(kind);
        wrapper["reference"] = serde_json::Value::Null;
        nodes[2]["parent"] = serde_json::json!(9);
        nodes.insert(2, wrapper);
        let encoded = serde_json::to_vec(&value).unwrap();
        assert!(
            is_unchecked_direct_loop_eof_echo(&encoded),
            "signed getchar nested in {kind} escaped the EOF guard"
        );
        assert_eq!(
            canonical_guest_typed_ir_with_source(
                &encoded,
                Some(DIRECT_OUTPUT_SOURCE)
            ),
            Err(FrontendJsonError::Unsupported),
        );
    }
    // The loop guard does not itself claim that a standalone signed input
    // can safely become a successful-u8 output. That refusal is separate.
    assert!(!is_unchecked_direct_loop_eof_echo(DIRECT_OUTPUT_JSON));
}

#[test]
fn signed_local_output_in_each_loop_kind_refuses_byte_only_projection() {
    // A genuine pinned-Clang C for-loop gives us the i32 declaration,
    // getchar initializer, nested if and all local-reference parent edges.
    // Swapping only its loop node kind tests this *refusal* on both other
    // source-control kinds without manufacturing an admissible Clang proof.
    const LOOP_JSON: &[u8] = include_bytes!(
        "c-frontend/golden/unsigned_conditional_live_input.json"
    );
    for kind in ["for-statement", "while-statement", "do-statement"] {
        let mut value: serde_json::Value =
            serde_json::from_slice(LOOP_JSON).unwrap();
        let node = value["nodes"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|node| node["kind"] == "for-statement")
            .unwrap();
        node["kind"] = serde_json::json!(kind);
        let encoded = serde_json::to_vec(&value).unwrap();
        assert!(
            echo::is_unchecked_counter_loop_signed_eof_output(&encoded),
            "i32 local getchar output escaped its {kind} EOF guard"
        );
    }
    let mut altered: serde_json::Value =
        serde_json::from_slice(LOOP_JSON).unwrap();
    let local = altered["nodes"]
        .as_array_mut()
        .unwrap()
        .iter_mut()
        .find(|node| {
            node["kind"] == "variable-declaration"
                && node["reference"]
                    .as_str()
                    .is_some_and(|r| r.starts_with("current@"))
        })
        .unwrap();
    local["type"] = serde_json::json!("u8");
    assert!(!echo::is_unchecked_counter_loop_signed_eof_output(
        &serde_json::to_vec(&altered).unwrap()
    ));
}
