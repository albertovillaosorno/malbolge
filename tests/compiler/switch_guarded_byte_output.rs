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
//   - Authenticated C switch case/default byte-domain identity.
// - Must-Not:
//   - Execute host-computed branches or trust forged Clang case metadata.
// - Allows:
//   - Inputs: pinned C23 source and its normalized Clang proof.
//   - Outputs: four real typed reads and four byte-identical guest writes.
//   - Side effects: none.
// - Split-When:
//   - General guest C switch execution supersedes this finite proof.
// - Merge-When:
//   - Source-proven byte guard tests cover the same conditional topology.
// - Summary:
//   - Refuse changed case labels, hidden effects and output divergence.

use super::super::{FrontendJsonError, canonical_guest_typed_ir_with_source};

const SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/unsigned_switch_guarded_live_input.c");
const JSON: &[u8] =
    include_bytes!("c-frontend/golden/unsigned_switch_guarded_live_input.json");

#[test]
fn source_proven_switch_preserves_four_real_guest_bytes() {
    // Successful-byte identities do not implement signed C23 EOF output.
    assert!(matches!(
        canonical_guest_typed_ir_with_source(JSON, Some(SOURCE)),
        Err(FrontendJsonError::Unsupported)
    ));
}

#[test]
fn switch_requires_original_source_and_complete_clang_evidence() {
    let mut changed_source = SOURCE.to_vec();
    let needle = b"current | 1";
    let index = changed_source
        .windows(needle.len())
        .position(|part| part == needle)
        .unwrap();
    changed_source[index + needle.len() - 1] = 50;
    assert!(matches!(
        canonical_guest_typed_ir_with_source(JSON, Some(&changed_source)),
        Err(FrontendJsonError::Unsupported)
    ));
    assert!(matches!(
        canonical_guest_typed_ir_with_source(JSON, None),
        Err(FrontendJsonError::Unsupported)
    ));
    for (kind, key, value) in [
        ("case-statement", "parent", serde_json::json!(2)),
        (
            "constant-expression",
            "constant_integer",
            serde_json::json!("1"),
        ),
        (
            "default-statement",
            "kind",
            serde_json::json!("break-statement"),
        ),
        (
            "break-statement",
            "kind",
            serde_json::json!("return-statement"),
        ),
    ] {
        let mut parsed: serde_json::Value =
            serde_json::from_slice(JSON).unwrap();
        let node = parsed["nodes"]
            .as_array_mut()
            .unwrap()
            .iter_mut()
            .find(|node| node["kind"] == kind)
            .unwrap();
        node[key] = value;
        assert!(
            matches!(
                canonical_guest_typed_ir_with_source(
                    &serde_json::to_vec(&parsed).unwrap(),
                    Some(SOURCE)
                ),
                Err(FrontendJsonError::Unsupported)
            ),
            "accepted forged {kind} {key}"
        );
    }
}
