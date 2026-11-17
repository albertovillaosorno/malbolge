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
