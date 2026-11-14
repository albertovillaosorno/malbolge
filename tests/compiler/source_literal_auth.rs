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
//   - Source-bound normalized C integer token admission regressions.
// - Must-Not:
//   - Accept a normalized integer value detached from original C bytes.
// - Allows:
//   - Inputs: pinned Clang golden and original C plus controlled forgeries.
//   - Outputs: typed admission or explicit refusal before guest publication.
//   - Side effects: none.
// - Split-When:
//   - Generic Clang source provenance verifier owns lexical token proofs.
// - Merge-When:
//   - Source-to-typed compiler verification subsumes this guard.
// - Summary:
//   - Reject forged literals even when the artifact is otherwise well formed.

use serde_json::{Value, json};

use super::{FrontendJsonError, canonical_guest_typed_ir_with_source};

const NORMALIZED: &[u8] =
    include_bytes!("c-frontend/golden/source_literal_auth_current.json");
const SOURCE: &[u8] =
    include_bytes!("c-frontend/accepted/local_multi_output.c");

#[test]
fn source_bound_multi_local_literals_refuse_forged_values() {
    assert!(
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(SOURCE)).is_ok()
    );
    let original: Value = serde_json::from_slice(NORMALIZED).unwrap();
    let first = original["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .position(|node| {
            node["kind"] == "integer-literal" && node["literal"] == "60"
        })
        .unwrap();
    let mut forged = original;
    forged["nodes"][first]["literal"] = json!("61");
    forged["nodes"][first]["constant_integer"] = json!("61");
    let changed = serde_json::to_vec(&forged).unwrap();
    assert!(matches!(
        canonical_guest_typed_ir_with_source(&changed, Some(SOURCE)),
        Err(FrontendJsonError::Unsupported)
    ));
}

#[test]
fn source_bound_binary_operator_refuses_same_width_forgery() {
    let original: Value = serde_json::from_slice(NORMALIZED).unwrap();
    let first = original["nodes"]
        .as_array()
        .unwrap()
        .iter()
        .position(|node| {
            node["kind"] == "binary-expression" && node["operation"] == "+"
        })
        .unwrap();
    let mut forged = original;
    forged["nodes"][first]["operation"] = json!("-");
    let changed = serde_json::to_vec(&forged).unwrap();
    assert!(matches!(
        canonical_guest_typed_ir_with_source(&changed, Some(SOURCE)),
        Err(FrontendJsonError::Unsupported)
    ));
}

#[test]
fn c23_integer_spelling_is_checked_across_radices_and_suffixes() {
    use super::source_integer_token_value;

    for (token, value) in [
        ("60U", 60),
        ("074u", 60),
        ("0x3cUL", 60),
        ("0X3Cllu", 60),
        ("0b111100U", 60),
        ("0B111'100U", 60),
        ("4'294'967'295ULL", 4_294_967_295),
        ("0", 0),
    ] {
        assert_eq!(source_integer_token_value(token.as_bytes()), Some(value));
    }
    for token in [
        "",
        "0x",
        "0b",
        "08",
        "0b2",
        "0x1'",
        "0x''f",
        "60UU",
        "60ULLU",
        "18446744073709551616U",
        "getchar()",
        "-1",
    ] {
        assert_eq!(
            source_integer_token_value(token.as_bytes()),
            None,
            "{token}"
        );
    }
}

#[test]
fn source_bound_literal_requires_same_original_source_bytes() {
    let mut source = SOURCE.to_vec();
    let site = source
        .windows(3)
        .position(|window| window == b"60U")
        .unwrap();
    source[site + 1] = b'1';
    assert!(matches!(
        canonical_guest_typed_ir_with_source(NORMALIZED, Some(&source)),
        Err(FrontendJsonError::Unsupported)
    ));
}
