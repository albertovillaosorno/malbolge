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
//   - Closed normalized Clang-JSON to typed void/literal-output adapter.
// - Must-Not:
//   - Parse C, reinterpret calls, silently drop effects, or bypass typed
//     admission.
// - Allows:
//   - Inputs: bounded version-one normalized frontend JSON bytes.
//   - Outputs: canonical MCTI for no-effect void or witnessed literal output.
//   - Side effects: none.
// - Split-When:
//   - General C byte-I/O gains independently modeled effect semantics.
// - Merge-When:
//   - Native frontend composition owns equivalent validated JSON decoding.
// - Summary:
//   - Connects exact C semantics to tested typed void and literal-output slices.
// - Description:
//   - Unknown nodes, additional effects, identity/profile drift all fail closed.
// - Usage:
//   - `canonical_guest_typed_ir(json)` yields MCTI and verified effect mode.
// - Defaults:
//   - Does not infer missing Clang metadata or source identity.
//

//! Closed, dependency-isolated adapter from normalized C frontend JSON to MCTI.
//! This is an artifact boundary, not a native C frontend or executable entry ABI.

#[path = "../../typed-ir/composition/lib.rs"]
pub mod typed;

#[cfg(test)]
use malbolge as _;
use serde::Deserialize;
use std::iter::once;
use std::str;
use typed::{
    BasicBlock, BasicBlockSpec, FrontendArtifact, FrontendArtifactSpec,
    FrontendFallthroughVoidFunctionSpec, FrontendPosition, FrontendReturnVoidFunction,
    FrontendReturnVoidFunctionSpec, FrontendSpan, Function, FunctionSpec, Instruction,
    IntegerConstant, LocatedInstruction, Module, ModuleSpec, TypeId, ValueId, canonical_bytes,
    canonical_module, lower_frontend_artifact,
};

const EXPECTED_ABI: &str = "malbolge-c32-v1";
const EXPECTED_ARTIFACT: &str = "malbolge-c-frontend-v1";
const EXPECTED_PROFILE: &str = "malbolge-2026";
const MAX_FRONTEND_JSON_BYTES: usize = 1_048_576;
const MAX_EFFECT_FREE_BODY_NODES: usize = 4_094;
const MAX_COMPOUND_DEPTH: usize = 64;
const DISTINCT_ELEVEN_BYTES: &[u8; 11] = b"P\x1d\x1a6\x05\xb4\xba\xb3\x84\xcf\x9e";
const DISTINCT_TWELVE_BYTES: &[u8; 12] = b"Q748\xfb\xce\x9f\x98\xb8\xb4\x83\xcd";
const DISTINCT_THIRTEEN_BYTES: &[u8; 13] = b"BC0\x16T\x09\xbf\xc6\xc8\x87\xe3\xab\xa4";
const DISTINCT_FOURTEEN_BYTES: &[u8; 14] = b"YE,HS\x17LO=@[1\x194";
const DISTINCT_FIFTEEN_BYTES: &[u8; 15] = b"Q.\x198>\x89\xd2\xad\xa3\xb7\xc8\x88\x08\xd5\xc6";
const DISTINCT_SIXTEEN_BYTES: &[u8; 16] = b"?I6\x13Z\x0a\xba\xb3\xc3\x86\xcc\xaa\x01\x07\xd5\xc5";
const DISTINCT_SEVENTEEN_BYTES: &[u8; 17] = b"Y?,HP\x1b\x182\x15MK;B\x0fD0\x17";
const DISTINCT_EIGHTEEN_BYTES: &[u8; 18] =
    b"\x54\x22\x19\x3e\x38\x03\x09\xdd\x87\xd1\xa5\x99\xbf\x08\xc7\xc6\xc2\x91";
const DISTINCT_NINETEEN_BYTES: &[u8; 19] = b"S!\x1a<8\x03\x17U\x0eI+\x10F\x16@L:\x19X";
const DISTINCT_TWENTY_BYTES: &[u8; 20] =
    b"\x3e\x14\x35\x12\x3f\x0a\xa4\x9c\xad\xa3\x1a\xa8\xa2\x95\xab\x9f\x98\x1d\xac\xae";
const DISTINCT_TWENTY_ONE_BYTES: &[u8; 21] =
    b"\x41\x0e\x3b\x0f\x3f\x0a\x40\x8e\x26\x92\x27\x96\x22\x97\x8d\x15\x31\x18\x35\x1a\x2f";
const DISTINCT_TWENTY_TWO_BYTES: &[u8; 22] =
    b"\x39\x16\x37\x05\x41\x0c\x30\x8e\x24\x9f\x1b\xa0\x23\x97\x15\x28\x27\x29\x14\x32\x1e\x1f";
const DISTINCT_TWENTY_THREE_BYTES: &[u8; 23] =
    b"\x42\x0e\x2f\x17\x39\x04\x8e\x24\x9f\x1b\xa0\x23\x97\x15\x28\x27\x29\x14\x32\x1e\x8b\x26\x92";
const DISTINCT_TWENTY_FOUR_BYTES: &[u8; 24] =
    b"\x3e\x0b\x2c\x12\x36\x01\x3d\x95\x0f\x9d\x17\x8b\x21\x93\x92\x20\x94\x0e\x9b\x18\x8a\x1c\x2f\x23";
const DISTINCT_TWENTY_FIVE_BYTES: &[u8; 25] =
    b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e";
const DISTINCT_TWENTY_SIX_BYTES: &[u8; 26] =
    b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95";
const DISTINCT_TWENTY_SEVEN_BYTES: &[u8; 27] =
    b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95\x2d";
const DISTINCT_TWENTY_EIGHT_BYTES: &[u8; 28] =
    b"\x51\x3e\x35\x38\x54\x1f\x4e\x33\x3d\x39\x05\x53\x23\x1b\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95\x2d\xab";
const DISTINCT_TWENTY_NINE_BYTES: &[u8; 29] =
    b"\x87\xb7\xbc\xb1\x8a\xce\x9f\x9c\xb5\x2c\xcb\x12\xc6\x2e\xaf\xb4\xf8\xca\x0e\x95\x2d\xab\x33\x3d\x39\x05\x53\x23\x1b";
const DISTINCT_THIRTY_BYTES: &[u8; 30] =
    b"\x39\xa8\x07\xda\x99\xdd\xa3\xcf\xa7\xd9\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5";
const DISTINCT_THIRTY_ONE_BYTES: &[u8; 31] = b"\x3f\x0b\x92\x21\x94\x0e\x9d\x1c\x34\x27\x2b\x25\x35\x1d\x33\x11\xa8\xa2\x95\xab\x9f\x98\x14\xac\xae\xa4\x9b\xa5\xad\xa3\x9c";
const DISTINCT_THIRTY_TWO_BYTES: &[u8; 32] = b"\x41\x17\x32\x18\x50\x23\x5c\x27\x4b\x34\x4f\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae";
const DISTINCT_THIRTY_THREE_BYTES: &[u8; 33] = b"\x39\x19\x34\x08\x41\x0c\x5c\x32\x4d\x33\x5a\x25\x5b\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5";
const DISTINCT_THIRTY_FOUR_BYTES: &[u8; 34] = b"\x3f\x11\x2c\x14\x39\x04\xa8\x50\x36\x3d\x42\x44\x2f\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae\x09\xd4\xac\xe1\x9e\xe2\xab";
const DISTINCT_THIRTY_FIVE_BYTES: &[u8; 35] = b"\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae";
const DISTINCT_THIRTY_SIX_BYTES: &[u8; 36] = b"\x39\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x4b\x34\x4f\x23\x5c\x93\xe0\x9f\xe4\xaa\xd5\xae\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad";
const DISTINCT_THIRTY_SEVEN_BYTES: &[u8; 37] = b"\x3f\x11\x2c\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x4b\x34\x4f\x23\x5c\x93\xe0\x9f\xe4\xaa\xd5\xae\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2";
const DISTINCT_THIRTY_EIGHT_BYTES: &[u8; 38] = b"\x41\x17\x32\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae";
const DISTINCT_THIRTY_NINE_BYTES: &[u8; 39] = b"\x5c\x32\x26\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93";
const DISTINCT_FORTY_BYTES: &[u8; 40] = b"\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa";
const DISTINCT_FORTY_ONE_BYTES: &[u8; 41] = b"\x5a\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa";
const DISTINCT_FORTY_TWO_BYTES: &[u8; 42] = b"\xa8\x07\xbb\x02\xb6\x0c\xb1\x30\x0d\x3c\x11\x2c\x14\x39\xa6\x46\x42\x44\x2f\x50\x36\x09\xd4\xac\xe1\x9e\xe2\xab\x0b\xd6\x9c\xe3\xa0\xd2\xad\x93\xe0\x9f\xe4\xaa\xd5\xae";
const DISTINCT_FORTY_THREE_BYTES: &[u8; 43] = b"\x51\x2e\x4f\x1d\x1a\x2f\x1b\x1c\x24\x26\x11\xa7\x05\xb8\xfc\xb6\x40\x2d\x49\x34\x38\x3e\x92\xe4\xa4\xe2\xae\xda\xac\x08\xd5\xab\xdd\xa2\xde\xaa\x0b\xd9\x9c\xe3\xa3\xd2\xad";
const DISTINCT_FORTY_FOUR_BYTES: &[u8; 44] = b"\x5a\x26\x47\x0b\x3e\x09\x2d\x13\x34\xa5\x06\xaf\xf3\xa8\x2f\x11\x41\x0f\x30\x19\x37\x08\x4d\x32\x4e\x1f\x57\x29\x44\x0a\xd4\x99\xdd\xa0\xcc\xaa\xd3\x07\xd5\x91\xde\xa1\xdc\xab";
const DISTINCT_FORTY_FIVE_BYTES: &[u8; 45] = b"\x51\x3e\x35\x38\x54\x1f\x4e\x87\xd1\xa5\x99\x09\x08\xc7\xc6\xc2\x91\xe1\xa7\xac\x98\xdb\x9b\xa0\xb7\xbf\x7c\xb5\x2c\xcb\x12\xb4\xf8\xca\x0e\x95\x2d\xab\x33\x3d\x39\x05\x53\x23\x1b";
const MAX_LITERAL_OUTPUT_CALLS: usize = 45;
const MAX_OUTPUT_PARENTHESES: usize = 3;
const MAX_OUTPUT_ARGUMENT_WRAPPERS: usize = MAX_OUTPUT_PARENTHESES + 1;
// Bound extra same-line source bytes between AST-delimited C tokens.
const MAX_OUTPUT_INLINE_PADDING: u32 = 16;
const MAX_INERT_OUTPUT_STATEMENTS: usize = 128;
const MAX_NESTED_OUTPUT_SCOPES: usize = 128;

/// Which independently checked guest effect trace can realize this C source.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FrontendGuestMode {
    /// Exactly two VM-witnessed distinct nonzero printable bytes.
    DistinctLiteralPair,
    /// Exactly three independently VM-witnessed different bytes.
    DistinctLiteralTriple,
    /// Exactly four independently VM-witnessed printable bytes.
    DistinctLiteralQuad,
    /// Five distinct source-proven bytes, including one escape byte.
    DistinctLiteralQuint,
    /// Six VM-computed distinct binary bytes.
    DistinctLiteralSix,
    /// Seven independent guest-computed binary bytes.
    DistinctLiteralSeven,
    /// Eight separate guest arithmetic outputs, including zero-control bytes.
    DistinctLiteralEight,
    /// Nine independent guest-computed binary bytes.
    DistinctLiteralNine,
    /// Ten independent guest-computed binary bytes.
    DistinctLiteralTen,
    /// Eleven independent guest-computed binary bytes.
    DistinctLiteralEleven,
    /// Twelve independent guest-computed binary bytes.
    DistinctLiteralTwelve,
    /// Thirteen independent guest-computed binary bytes.
    DistinctLiteralThirteen,
    /// Fourteen independent guest-computed binary bytes.
    DistinctLiteralFourteen,
    /// Fifteen independent guest-computed binary bytes.
    DistinctLiteralFifteen,
    /// Sixteen independent guest-computed binary bytes.
    DistinctLiteralSixteen,
    /// Seventeen independent guest-computed binary bytes.
    DistinctLiteralSeventeen,
    /// Eighteen independent guest-computed binary bytes.
    DistinctLiteralEighteen,
    /// Nineteen independent guest-computed binary bytes.
    DistinctLiteralNineteen,
    /// Twenty independent guest-computed binary bytes.
    DistinctLiteralTwenty,
    /// Twenty-one independent guest-computed binary bytes.
    DistinctLiteralTwentyOne,
    /// Twenty-two independently guest-computed bytes.
    DistinctLiteralTwentyTwo,
    /// Twenty-three independently guest-computed bytes.
    DistinctLiteralTwentyThree,
    /// Twenty-four independently guest-computed bytes.
    DistinctLiteralTwentyFour,
    /// Twenty-five independently guest-computed bytes.
    DistinctLiteralTwentyFive,
    /// Twenty-six independently guest-computed bytes.
    DistinctLiteralTwentySix,
    /// Twenty-seven independently guest-computed bytes.
    DistinctLiteralTwentySeven,
    /// Twenty-eight independently guest-computed bytes.
    DistinctLiteralTwentyEight,
    /// Twenty-nine independently guest-computed bytes.
    DistinctLiteralTwentyNine,
    /// Thirty independently guest-computed bytes.
    DistinctLiteralThirty,
    /// Thirty-one independently guest-computed bytes.
    DistinctLiteralThirtyOne,
    /// Thirty-two independently guest-computed bytes.
    DistinctLiteralThirtyTwo,
    /// Thirty-three independently guest-computed bytes.
    DistinctLiteralThirtyThree,
    /// Thirty-four independently guest-computed bytes.
    DistinctLiteralThirtyFour,
    /// Thirty-five independently guest-computed bytes.
    DistinctLiteralThirtyFive,
    /// Thirty-six independently guest-computed bytes.
    DistinctLiteralThirtySix,
    /// Thirty-seven independently guest-computed bytes.
    DistinctLiteralThirtySeven,
    /// Thirty-eight independently guest-computed bytes.
    DistinctLiteralThirtyEight,
    /// Thirty-nine independently guest-computed bytes.
    DistinctLiteralThirtyNine,
    /// Forty independently guest-computed bytes.
    DistinctLiteralForty,
    /// Forty-one independently guest-computed bytes.
    DistinctLiteralFortyOne,
    /// Forty-two independently guest-computed bytes.
    DistinctLiteralFortyTwo,
    /// Forty-three independently guest-computed bytes.
    DistinctLiteralFortyThree,
    /// Forty-four independently guest-computed bytes.
    DistinctLiteralFortyFour,
    /// Forty-five independently guest-computed bytes.
    DistinctLiteralFortyFive,
    /// No byte effects, then a guest halt.
    EmptyVoid,
    /// Emit a literal zero byte, then a guest halt.
    InitialZeroOutput,
    /// Emit an independently witnessed nonzero byte using guest rotation.
    SeededByteLiteral,
    /// Exactly two different outputs: initial zero then a VM-witnessed byte.
    ZeroThenLiteral,
}

/// Canonical typed-IR bytes paired with their independently checked guest mode.
pub type CanonicalGuestProjection = (Vec<u8>, FrontendGuestMode);
type LiteralOutputProjection = (Vec<u8>, FrontendGuestMode);

/// A rejected normalized frontend artifact or typed-IR projection.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FrontendJsonError {
    /// The canonical typed-IR compiler rejected this semantic projection.
    InvalidTypedIr,
    /// JSON is malformed, has duplicate/unknown keys or exceeds the bound.
    Malformed,
    /// Metadata or semantic nodes are outside the admitted void-return slice.
    Unsupported,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Clang {
    language: String,
    target: String,
    version: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Target {
    abi_id: String,
    target_profile: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Source {
    id: String,
    sha256: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Position {
    byte: u32,
    column: u32,
    line: u32,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Span {
    begin: Position,
    end: Position,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Node {
    constant_integer: Option<String>,
    definition: Option<String>,
    id: u32,
    inline_specified: Option<bool>,
    kind: String,
    linkage: Option<String>,
    literal: Option<String>,
    name: Option<String>,
    operation: Option<String>,
    parent: u32,
    reference: Option<String>,
    span: Span,
    storage_class: Option<String>,
    #[serde(rename = "type")]
    type_name: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Artifact {
    clang: Clang,
    #[serde(rename = "artifact_id")]
    identity: String,
    nodes: Vec<Node>,
    profile: Target,
    schema_version: u16,
    source: Source,
}

struct LiteralOutputNodes<'node> {
    body: &'node Node,
    byte: u8,
    calls: Vec<(&'node Node, &'node Node)>,
    function: &'node Node,
    mixed_byte: Option<u8>,
    third_byte: Option<u8>,
    fourth_byte: Option<u8>,
    fifth_byte: Option<u8>,
    sixth_byte: Option<u8>,
    seventh_byte: Option<u8>,
    eighth_byte: Option<u8>,
    ninth_byte: Option<u8>,
    tenth_byte: Option<u8>,
    eleventh_byte: Option<u8>,
    twelfth_byte: Option<u8>,
    thirteenth_byte: Option<u8>,
    fourteenth_byte: Option<u8>,
    fifteenth_byte: Option<u8>,
    sixteenth_byte: Option<u8>,
    seventeenth_byte: Option<u8>,
    eighteenth_byte: Option<u8>,
    nineteenth_byte: Option<u8>,
    twentieth_byte: Option<u8>,
    twenty_first_byte: Option<u8>,
    twenty_second_byte: Option<u8>,
    twenty_third_byte: Option<u8>,
    twenty_fourth_byte: Option<u8>,
    twenty_fifth_byte: Option<u8>,
    twenty_sixth_byte: Option<u8>,
    twenty_seventh_byte: Option<u8>,
    twenty_eighth_byte: Option<u8>,
    twenty_ninth_byte: Option<u8>,
    thirtieth_byte: Option<u8>,
    thirty_first_byte: Option<u8>,
    thirty_second_byte: Option<u8>,
    thirty_third_byte: Option<u8>,
    thirty_fourth_byte: Option<u8>,
    thirty_fifth_byte: Option<u8>,
    thirty_sixth_byte: Option<u8>,
    thirty_seventh_byte: Option<u8>,
    thirty_eighth_byte: Option<u8>,
    thirty_ninth_byte: Option<u8>,
    fortieth_byte: Option<u8>,
    forty_first_byte: Option<u8>,
    forty_second_byte: Option<u8>,
    forty_third_byte: Option<u8>,
    forty_fourth_byte: Option<u8>,
    forty_fifth_byte: Option<u8>,
    returned: Option<&'node Node>,
}

// Track the Clang semantic preorder through nested lexical compound blocks.
// Each scope owns its source cursor, so closing a block cannot re-admit
// a child outside its original parent span or reorder an emitted effect.
struct OutputScope<'node> {
    node: &'node Node,
    previous_end: u32,
    previous_span_has_terminator: bool,
}

const fn position(value: &Position) -> FrontendPosition {
    FrontendPosition::new(value.byte, value.line, value.column)
}

const fn span(value: &Span) -> FrontendSpan {
    FrontendSpan::new(position(&value.begin), position(&value.end))
}

fn source_digest(value: &str) -> Result<[u8; 32], FrontendJsonError> {
    if value.len() != 64 {
        return Err(FrontendJsonError::Unsupported);
    }
    let mut digest = [0; 32];
    let (pairs, remainder) = value.as_bytes().as_chunks::<2>();
    if !remainder.is_empty() {
        return Err(FrontendJsonError::Unsupported);
    }
    for (target, pair) in digest.iter_mut().zip(pairs) {
        let word = str::from_utf8(pair).map_err(|_error| FrontendJsonError::Unsupported)?;
        if pair.iter().any(u8::is_ascii_uppercase) {
            return Err(FrontendJsonError::Unsupported);
        }
        *target = u8::from_str_radix(word, 16).map_err(|_error| FrontendJsonError::Unsupported)?;
    }
    Ok(digest)
}

// Clang NullStmt spans one semicolon, and standalone integer zero spans one
// digit. Discard only their proven no-effect semantics, not source provenance.
fn valid_single_byte_statement_span(node: &Node, body: &Node, preceding_end: u32) -> bool {
    let start = &node.span.begin;
    let end = &node.span.end;
    start.byte >= preceding_end
        && start.byte >= body.span.begin.byte
        && end.byte <= body.span.end.byte
        && start.byte.checked_add(1) == Some(end.byte)
        && start.line != 0
        && start.column != 0
        && start.line == end.line
        && start.column.checked_add(1) == Some(end.column)
}

// Admit only the exact Clang semantic preorder for the source `(void)0`:
// one to-void cast with an immediately nested i32 zero literal. The cast's
// source end coincides with its literal child's end, unlike compound scopes.
fn valid_zero_void_cast(cast: &Node, operand: Option<&Node>) -> bool {
    let Some(child) = operand else { return false };
    cast.kind == "cast-expression"
        && cast.type_name.as_deref() == Some("void")
        && cast.operation.as_deref() == Some("to-void")
        && child.kind == "integer-literal"
        && child.parent == cast.id
        && cast.id.checked_add(1) == Some(child.id)
        && child.type_name.as_deref() == Some("i32")
        && child.constant_integer.as_deref() == Some("0")
        && child.literal.as_deref() == Some("0")
        && cast.span.begin.byte.checked_add(7) == Some(cast.span.end.byte)
        && cast.span.begin.line == cast.span.end.line
        && cast.span.begin.column.checked_add(7) == Some(cast.span.end.column)
        && child.span.begin.byte.checked_add(1) == Some(child.span.end.byte)
        && child.span.begin.byte.checked_add(1) == Some(cast.span.end.byte)
        && child.span.begin.line == cast.span.end.line
        && child.span.end.line == cast.span.end.line
        && child.span.begin.column.checked_add(1) == Some(cast.span.end.column)
        && child.span.end.column == cast.span.end.column
}

// Clang's semantic preorder contains compound scopes and their children.
// Discard only proven effect-free nulls, literal zero, cast of zero to
// void and compound scopes, checking actual ancestor IDs and nonoverlapping source ranges at every depth. A
// terminal ReturnStmt may belong to any active compound scope, but no node
// can follow it. Scope bounds include braces; child ranges must be interior.
#[expect(
    clippy::too_many_lines,
    reason = "nested source-preorder and no-effect statements share one admission gate"
)]
fn admit_effect_free_body(body: &Node, statements: &[Node]) -> Result<(), FrontendJsonError> {
    let mut scopes = vec![(body, body.span.begin.byte)];
    let mut index = 0;
    while let Some(node) = statements.get(index) {
        while scopes
            .last()
            .is_some_and(|(parent, _)| parent.id != node.parent)
        {
            let _popped = scopes.pop();
        }
        let Some((parent, next_child_byte)) = scopes.last_mut() else {
            return Err(FrontendJsonError::Unsupported);
        };
        let start = &node.span.begin;
        let end = &node.span.end;
        if node.id != u32::try_from(index).unwrap_or(u32::MAX).saturating_add(3)
            || start.byte < *next_child_byte
            || start.byte <= parent.span.begin.byte
            || end.byte >= parent.span.end.byte
            || start.line == 0
            || start.column == 0
            || end.line < start.line
            || end.column == 0
            || (end.line == start.line && end.column <= start.column)
        {
            return Err(FrontendJsonError::Unsupported);
        }
        match node.kind.as_str() {
            "null-statement"
                if valid_single_byte_statement_span(node, parent, *next_child_byte) =>
            {
                *next_child_byte = end.byte;
            }
            // A literal zero directly inside a compound statement is a
            // one-byte expression statement with no reads, writes or effects.
            // It is not safe to discard arbitrary literal descendants or casts.
            "integer-literal"
                if node.type_name.as_deref() == Some("i32")
                    && node.constant_integer.as_deref() == Some("0")
                    && node.literal.as_deref() == Some("0")
                    && valid_single_byte_statement_span(node, parent, *next_child_byte) =>
            {
                *next_child_byte = end.byte;
            }
            "cast-expression"
                if valid_zero_void_cast(node, statements.get(index.saturating_add(1))) =>
            {
                *next_child_byte = end.byte;
                index = index.saturating_add(1); // consume the literal child
            }
            "compound-statement"
                if start
                    .byte
                    .checked_add(2)
                    .is_some_and(|min_end| end.byte >= min_end)
                    && (end.line != start.line
                        || start
                            .column
                            .checked_add(2)
                            .is_some_and(|min_end| end.column >= min_end)) =>
            {
                *next_child_byte = end.byte;
                if scopes.len() >= MAX_COMPOUND_DEPTH {
                    return Err(FrontendJsonError::Unsupported);
                }
                scopes.push((node, start.byte));
            }
            "return-statement" if index == statements.len().saturating_sub(1) => {
                *next_child_byte = end.byte;
            }
            _ => return Err(FrontendJsonError::Unsupported),
        }
        index = index.saturating_add(1);
    }
    Ok(())
}

/// Decode one no-effect void C function with optional nested scopes and returns.
///
/// This validates the serialized Clang artifact shape, **not** the contents
/// of an independently supplied C source. Raw-source digest verification and
/// native frontend execution belong to the future process composition.
///
/// # Errors
///
/// Rejects malformed/duplicate/unknown JSON fields, version/profile drift,
/// extra statements or definitions, and invalid typed-IR source spans.
#[expect(
    clippy::too_many_lines,
    reason = "closed versioned Clang node and typed IR admission"
)]
pub fn decode_void_frontend_json(bytes: &[u8]) -> Result<FrontendArtifact, FrontendJsonError> {
    if bytes.is_empty() || bytes.len() > MAX_FRONTEND_JSON_BYTES {
        return Err(FrontendJsonError::Malformed);
    }
    let input: Artifact =
        serde_json::from_slice(bytes).map_err(|_error| FrontendJsonError::Malformed)?;
    if input.schema_version != 1
        || input.identity != EXPECTED_ARTIFACT
        || input.profile.abi_id != EXPECTED_ABI
        || input.profile.target_profile != EXPECTED_PROFILE
        || input.clang.version != "22.1.8"
        || input.clang.target != "wasm32-unknown-unknown"
        || input.clang.language != "c23"
        || input.source.id.is_empty()
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let [function, body, statements @ ..] = input.nodes.as_slice() else {
        return Err(FrontendJsonError::Unsupported);
    };
    let returned = statements
        .last()
        .filter(|node| node.kind == "return-statement");
    if statements.len() > MAX_EFFECT_FREE_BODY_NODES {
        return Err(FrontendJsonError::Unsupported);
    }
    if function.kind != "function-declaration"
        || function.parent != 0
        || function.id != 1
        || function.name.as_deref().is_none_or(str::is_empty)
        || function.type_name.as_deref() != Some("fn()->void")
        || function.definition.as_deref() != Some("definition")
        || function.inline_specified != Some(false)
        || function.linkage.as_deref() != Some("external")
        || function.storage_class.as_deref() != Some("none")
        || function.constant_integer.is_some()
        || function.literal.is_some()
        || function.operation.is_some()
        || body.kind != "compound-statement"
        || body.parent != function.id
        || body.id != 2
        || once(body).chain(statements.iter()).any(|node| {
            let is_zero = node.kind == "integer-literal";
            let is_zero_cast = node.kind == "cast-expression";
            node.name.is_some()
                || node.reference.is_some()
                || (!is_zero && !is_zero_cast && node.type_name.is_some())
                || (!is_zero && node.constant_integer.is_some())
                || (!is_zero && node.literal.is_some())
                || (!is_zero_cast && node.operation.is_some())
                || node.definition.is_some()
                || node.inline_specified.is_some()
                || node.linkage.is_some()
                || node.storage_class.is_some()
        })
    {
        return Err(FrontendJsonError::Unsupported);
    }
    admit_effect_free_body(body, statements)?;
    let void_function = if let Some(return_node) = returned {
        FrontendReturnVoidFunction::new(FrontendReturnVoidFunctionSpec {
            body_span: span(&body.span),
            definition: String::from("definition"),
            function_span: span(&function.span),
            inline_specified: false,
            linkage: String::from("external"),
            name: function
                .name
                .clone()
                .ok_or(FrontendJsonError::Unsupported)?,
            return_span: span(&return_node.span),
            signature: String::from("fn()->void"),
            storage_class: String::from("none"),
        })
    } else {
        FrontendReturnVoidFunction::new_fallthrough(FrontendFallthroughVoidFunctionSpec {
            body_span: span(&body.span),
            definition: String::from("definition"),
            function_span: span(&function.span),
            inline_specified: false,
            linkage: String::from("external"),
            name: function
                .name
                .clone()
                .ok_or(FrontendJsonError::Unsupported)?,
            signature: String::from("fn()->void"),
            storage_class: String::from("none"),
        })
    };
    let artifact = FrontendArtifact::new_void(
        FrontendArtifactSpec {
            abi_id: input.profile.abi_id,
            artifact_id: input.identity,
            clang_target: input.clang.target,
            clang_version: input.clang.version,
            functions: Vec::new(),
            language: input.clang.language,
            schema_version: input.schema_version,
            source_id: input.source.id,
            source_sha256: source_digest(&input.source.sha256)?,
            target_profile: input.profile.target_profile,
        },
        void_function,
    );
    let _validated =
        lower_frontend_artifact(&artifact).map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    Ok(artifact)
}

/// Produce canonical typed MCTI from a supported normalized C JSON artifact.
///
/// # Errors
///
/// Refuses any unsupported Clang structure or independently invalid typed wire.
pub fn canonical_void_typed_ir(bytes: &[u8]) -> Result<Vec<u8>, FrontendJsonError> {
    let artifact = decode_void_frontend_json(bytes)?;
    let module =
        lower_frontend_artifact(&artifact).map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    let encoded = canonical_bytes(&module).map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    let decoded = canonical_module(&encoded).map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    if decoded != module {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    Ok(encoded)
}

const fn typed_span(value: &Span) -> typed::SourceSpan {
    let begin = &value.begin;
    let end = &value.end;
    typed::SourceSpan::new(
        typed::SourcePosition::new(begin.byte, begin.line, begin.column),
        typed::SourcePosition::new(end.byte, end.line, end.column),
    )
}

// Clang's normalized preorder has complete semantic ancestry but carries only
// offsets, not source text. Accept short gaps around source delimiters only
// when byte and column distances agree on one line. The pinned AST, source
// digest check, and closed node grammar still prove the guest byte effect.
fn bounded_inline_gap(before: &Position, after: &Position, required: u32) -> bool {
    before.line != 0
        && before.line == after.line
        && before.column != 0
        && before
            .byte
            .checked_add(required)
            .is_some_and(|start| start <= after.byte)
        && after.byte.checked_sub(before.byte).is_some_and(|gap| {
            gap <= required.saturating_add(MAX_OUTPUT_INLINE_PADDING)
                && after.column.checked_sub(before.column) == Some(gap)
        })
}

// Each putchar expression has the pinned Clang semantic preorder:
// optional explicit to-void discard -> call -> function decay -> declaration
// ref -> bounded argument wrappers -> literal. One signed unary may occur in
// a checked parenthesis chain; a separate unsigned integral cast may surround
// the leaf. No folded arithmetic, nested discards or side effects are inferred.
#[expect(
    clippy::too_many_lines,
    clippy::too_many_arguments,
    clippy::cognitive_complexity,
    reason = "exact Clang node metadata and positional proof stay together"
)]
fn admitted_output_byte(
    group: &[Node],
    body: &Node,
    previous_end: u32,
    expected_id: u32,
    previous_span_has_terminator: bool,
) -> Option<u8> {
    let discard = group.first().filter(|node| {
        node.kind == "cast-expression" && node.operation.as_deref() == Some("to-void")
    });
    let call_group = if discard.is_some() {
        group.get(1..)?
    } else {
        group
    };
    let [call, cast, callee, rest @ ..] = call_group else {
        return None;
    };
    let statement = discard.unwrap_or(call);
    let call_id = expected_id.checked_add(u32::from(discard.is_some()))?;
    let discard_valid = discard.is_none_or(|outer| {
        outer.id == expected_id
            && outer.parent == body.id
            && outer.type_name.as_deref() == Some("void")
            && outer.name.is_none()
            && outer.reference.is_none()
            && outer.definition.is_none()
            && outer.inline_specified.is_none()
            && outer.linkage.is_none()
            && outer.storage_class.is_none()
            && outer.constant_integer.is_none()
            && outer.literal.is_none()
            && bounded_inline_gap(&outer.span.begin, &call.span.begin, 6)
            && outer.span.end.byte == call.span.end.byte
            && outer.span.end.line == call.span.end.line
            && outer.span.end.column == call.span.end.column
    });
    let (literal, wrappers) = rest.split_last()?;
    if wrappers.len() > MAX_OUTPUT_ARGUMENT_WRAPPERS {
        return None;
    }
    let integral_cast = wrappers.first().is_some_and(|node| {
        node.kind == "cast-expression" && node.operation.as_deref() == Some("integral-cast")
    });
    let unary_index = wrappers
        .iter()
        .position(|node| node.kind == "unary-expression");
    if (integral_cast && unary_index.is_some())
        || wrappers
            .iter()
            .filter(|node| node.kind == "unary-expression")
            .count()
            > 1
    {
        return None;
    }
    let unary = unary_index.and_then(|index| wrappers.get(index));
    let digits = literal.literal.as_deref()?;
    // The source-bound leaf must be a nonnegative representable i32 value,
    // even when Clang inferred unsigned u32 for the source token.
    let operand = digits.parse::<i32>().ok()?;
    if operand.is_negative()
        || digits != operand.to_string()
        || literal.constant_integer.as_deref() != Some(digits)
        || literal.type_name.as_deref() != Some(if integral_cast { "u32" } else { "i32" })
        || (integral_cast && literal.kind != "integer-literal")
    {
        return None;
    }
    let evaluated = match unary {
        Some(node) => match node.operation.as_deref() {
            Some("+") => operand,
            Some("-") => operand.checked_neg()?,
            _ => return None,
        },
        None => operand,
    };
    let evaluated_digits = evaluated.to_string();
    let [byte, ..] = evaluated.to_le_bytes();
    let call_span = &call.span;
    let cast_span = &cast.span;
    let callee_span = &callee.span;
    let literal_span = &literal.span;
    let argument_span = wrappers.first().map_or(literal_span, |node| &node.span);
    let source_width = literal_span.end.byte.checked_sub(literal_span.begin.byte)?;
    // Clang already decodes decimal, octal, hexadecimal, C23 binary and
    // character tokens. Retain its evaluated integer and exact source span;
    // never guess the spelling from a normalized decimal string.
    let width = match literal.kind.as_str() {
        "integer-literal"
            if (1..=32).contains(&source_width)
                && literal_span.begin.line == literal_span.end.line
                && literal_span
                    .end
                    .column
                    .checked_sub(literal_span.begin.column)
                    == Some(source_width) =>
        {
            source_width
        }
        "character-literal"
            if (3..=10).contains(&source_width)
                && literal_span.begin.line == literal_span.end.line
                && literal_span
                    .end
                    .column
                    .checked_sub(literal_span.begin.column)
                    == Some(source_width) =>
        {
            source_width
        }
        _ => return None,
    };

    let mut parent_id = call.id;
    let mut next_id = call_id.checked_add(3)?;
    let mut parentheses = 0usize;
    for (index, node) in wrappers.iter().enumerate() {
        let child = wrappers.get(index.saturating_add(1)).unwrap_or(literal);
        let node_span = &node.span;
        let child_span = &child.span;
        if node.id != next_id
            || node.parent != parent_id
            || node.name.is_some()
            || node.reference.is_some()
            || node.definition.is_some()
            || node.inline_specified.is_some()
            || node.linkage.is_some()
            || node.storage_class.is_some()
            || node.literal.is_some()
            || node.constant_integer.as_deref()
                != Some(
                    if unary_index.is_some_and(|unary_position| index > unary_position) {
                        digits
                    } else {
                        evaluated_digits.as_str()
                    },
                )
        {
            return None;
        }
        let shape = match node.kind.as_str() {
            "parenthesized-expression" => {
                parentheses = parentheses.checked_add(1)?;
                parentheses <= MAX_OUTPUT_PARENTHESES
                    && node.type_name == child.type_name
                    && node.operation.is_none()
                    && bounded_inline_gap(&node_span.begin, &child_span.begin, 1)
                    && bounded_inline_gap(&child_span.end, &node_span.end, 1)
            }
            "cast-expression" => {
                index == 0
                    && integral_cast
                    && node.type_name.as_deref() == Some("i32")
                    && child.type_name.as_deref() == Some("u32")
                    && node.operation.as_deref() == Some("integral-cast")
                    && node_span.begin.byte == child_span.begin.byte
                    && node_span.end.byte == child_span.end.byte
                    && node_span.begin.line == child_span.begin.line
                    && node_span.end.line == child_span.end.line
                    && node_span.begin.column == child_span.begin.column
                    && node_span.end.column == child_span.end.column
            }
            "unary-expression" => {
                unary_index == Some(index)
                    && !integral_cast
                    && node.type_name.as_deref() == Some("i32")
                    && child.type_name.as_deref() == Some("i32")
                    && matches!(node.operation.as_deref(), Some("+" | "-"))
                    && bounded_inline_gap(&node_span.begin, &child_span.begin, 1)
                    && node_span.end.byte == child_span.end.byte
                    && node_span.end.line == child_span.end.line
                    && node_span.end.column == child_span.end.column
            }
            _ => false,
        };
        if !shape {
            return None;
        }
        parent_id = node.id;
        next_id = next_id.checked_add(1)?;
    }
    let valid = discard_valid
        && literal.id == next_id
        && literal.parent == parent_id
        && call.id == call_id
        && call.parent == discard.map_or(body.id, |outer| outer.id)
        && call.kind == "call-expression"
        && call.type_name.as_deref() == Some("i32")
        && call.reference.as_deref() == Some("external:putchar")
        && cast.id == call_id.checked_add(1)?
        && cast.parent == call.id
        && cast.kind == "cast-expression"
        && cast.type_name.as_deref() == Some("ptr(fn(i32)->i32)")
        && cast.operation.as_deref() == Some("function-to-pointer")
        && callee.id == call_id.checked_add(2)?
        && callee.parent == cast.id
        && callee.kind == "declaration-reference-expression"
        && callee.type_name.as_deref() == Some("fn(i32)->i32")
        && callee.reference.as_deref() == Some("external:putchar")
        && [call, cast, callee, literal].iter().all(|node| {
            node.name.is_none()
                && node.definition.is_none()
                && node.inline_specified.is_none()
                && node.linkage.is_none()
                && node.storage_class.is_none()
        })
        && [call, cast, callee]
            .iter()
            .all(|node| node.constant_integer.is_none() && node.literal.is_none())
        && [call, callee, literal]
            .iter()
            .all(|node| node.operation.is_none())
        && [cast, literal].iter().all(|node| node.reference.is_none())
        // NullStmt and CompoundStmt spans include their final delimiter.
        && (statement.span.begin.byte > previous_end
            || (previous_span_has_terminator && statement.span.begin.byte == previous_end))
        && call_span.end.byte < body.span.end.byte
        && call_span.begin.byte == cast_span.begin.byte
        && cast_span.begin.byte == callee_span.begin.byte
        && cast_span.end.byte == callee_span.end.byte
        && bounded_inline_gap(&cast_span.end, &argument_span.begin, 1)
        && bounded_inline_gap(&argument_span.end, &call_span.end, 1)
        && cast_span.begin.column == call_span.begin.column
        && cast_span.begin.line == call_span.begin.line
        && cast_span.begin.byte.checked_add(7) == Some(cast_span.end.byte)
        && literal_span.begin.byte.checked_add(width) == Some(literal_span.end.byte)
        && [
            call_span,
            cast_span,
            callee_span,
            argument_span,
            literal_span,
        ]
        .iter()
        .all(|span| {
            span.begin.line != 0
                && span.begin.column != 0
                && span.end.line != 0
                && span.end.column != 0
                && span.begin.byte < span.end.byte
                && (span.begin.line != span.end.line || span.begin.column < span.end.column)
        });
    valid.then_some(byte)
}

// Between output calls, discard only the same exact source-bound
// no-effect statements admitted by the void-return frontend. Never infer that
// an unrecognized expression lacks observable effects.
fn inert_output_statement(
    nodes: &[Node],
    body: &Node,
    previous_end: u32,
    expected_id: u32,
) -> Option<(usize, u32)> {
    let node = nodes.first()?;
    let closed_metadata = |node: &Node| {
        node.name.is_none()
            && node.reference.is_none()
            && node.definition.is_none()
            && node.inline_specified.is_none()
            && node.linkage.is_none()
            && node.storage_class.is_none()
    };
    if node.id != expected_id
        || node.parent != body.id
        || !closed_metadata(node)
        || node.span.begin.byte <= body.span.begin.byte
        || node.span.begin.byte < previous_end
        || node.span.end.byte >= body.span.end.byte
    {
        return None;
    }
    let end = node.span.end.byte;
    match node.kind.as_str() {
        "null-statement"
            if node.type_name.is_none()
                && node.operation.is_none()
                && node.constant_integer.is_none()
                && node.literal.is_none()
                && valid_single_byte_statement_span(node, body, previous_end) =>
        {
            Some((1, end))
        }
        "integer-literal"
            if node.type_name.as_deref() == Some("i32")
                && node.operation.is_none()
                && node.constant_integer.as_deref() == Some("0")
                && node.literal.as_deref() == Some("0")
                && valid_single_byte_statement_span(node, body, previous_end) =>
        {
            Some((1, end))
        }
        "cast-expression" => {
            let child = nodes.get(1)?;
            (node.constant_integer.is_none()
                && node.literal.is_none()
                && closed_metadata(child)
                && child.operation.is_none()
                && child.id == expected_id.checked_add(1)?
                && valid_zero_void_cast(node, Some(child)))
            .then_some((2, end))
        }
        _ => None,
    }
}

// Bounded literal outputs are identical, except an exact witnessed zero-first pair.
#[expect(
    clippy::too_many_lines,
    clippy::cognitive_complexity,
    reason = "closed bounded C literal-output preorder admission"
)]
fn admit_literal_output_nodes(nodes: &[Node]) -> Result<LiteralOutputNodes<'_>, FrontendJsonError> {
    let [function, body, rest @ ..] = nodes else {
        return Err(FrontendJsonError::Unsupported);
    };
    let (returned, call_nodes) = match rest.split_last() {
        Some((last, preceding)) if last.kind == "return-statement" => (Some(last), preceding),
        _ => (None, rest),
    };
    if call_nodes.is_empty()
        || call_nodes.len()
            > MAX_LITERAL_OUTPUT_CALLS
                .saturating_mul(5 + MAX_OUTPUT_ARGUMENT_WRAPPERS)
                .saturating_add(MAX_INERT_OUTPUT_STATEMENTS.saturating_mul(2))
                .saturating_add(MAX_NESTED_OUTPUT_SCOPES)
        || function.kind != "function-declaration"
        || function.id != 1
        || function.parent != 0
        || function.name.as_deref().is_none_or(str::is_empty)
        || function.type_name.as_deref() != Some("fn()->void")
        || function.definition.as_deref() != Some("definition")
        || function.inline_specified != Some(false)
        || function.linkage.as_deref() != Some("external")
        || function.storage_class.as_deref() != Some("none")
        || function.constant_integer.is_some()
        || function.literal.is_some()
        || function.operation.is_some()
        || function.reference.is_some()
        || body.id != 2
        || body.parent != 1
        || body.kind != "compound-statement"
        || returned.is_some_and(|node| {
            node.id != u32::try_from(nodes.len()).unwrap_or(u32::MAX)
                || node.parent != body.id
                || node.span.begin.byte <= body.span.begin.byte
                || node.span.end.byte >= body.span.end.byte
        })
        || once(body).chain(returned).any(|node| {
            node.name.is_some()
                || node.definition.is_some()
                || node.inline_specified.is_some()
                || node.linkage.is_some()
                || node.storage_class.is_some()
                || node.type_name.is_some()
                || node.reference.is_some()
                || node.operation.is_some()
                || node.constant_integer.is_some()
                || node.literal.is_some()
        })
        || function.span.begin.byte > body.span.begin.byte
        || function.span.end.byte < body.span.end.byte
        || body.span.begin.byte >= body.span.end.byte
        || once(body).chain(returned).any(|node| {
            node.span.begin.line == 0
                || node.span.begin.column == 0
                || node.span.end.line == 0
                || node.span.end.column == 0
                || node.span.begin.byte >= node.span.end.byte
                || (node.span.begin.line == node.span.end.line
                    && node.span.begin.column >= node.span.end.column)
        })
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let mut calls = Vec::new();
    let mut selected_byte = None;
    let mut mixed_byte = None;
    let mut third_byte = None;
    let mut fourth_byte = None;
    let mut fifth_byte = None;
    let mut sixth_byte = None;
    let mut seventh_byte = None;
    let mut eighth_byte = None;
    let mut ninth_byte = None;
    let mut tenth_byte = None;
    let mut eleventh_byte = None;
    let mut twelfth_byte = None;
    let mut thirteenth_byte = None;
    let mut fourteenth_byte = None;
    let mut fifteenth_byte = None;
    let mut sixteenth_byte = None;
    let mut seventeenth_byte = None;
    let mut eighteenth_byte = None;
    let mut nineteenth_byte = None;
    let mut twentieth_byte = None;
    let mut twenty_first_byte = None;
    let mut twenty_second_byte = None;
    let mut twenty_third_byte = None;
    let mut twenty_fourth_byte = None;
    let mut twenty_fifth_byte = None;
    let mut twenty_sixth_byte = None;
    let mut twenty_seventh_byte = None;
    let mut twenty_eighth_byte = None;
    let mut twenty_ninth_byte = None;
    let mut thirtieth_byte = None;
    let mut thirty_first_byte = None;
    let mut thirty_second_byte = None;
    let mut thirty_third_byte = None;
    let mut thirty_fourth_byte = None;
    let mut thirty_fifth_byte = None;
    let mut thirty_sixth_byte = None;
    let mut thirty_seventh_byte = None;
    let mut thirty_eighth_byte = None;
    let mut thirty_ninth_byte = None;
    let mut fortieth_byte = None;
    let mut forty_first_byte = None;
    let mut forty_second_byte = None;
    let mut forty_third_byte = None;
    let mut forty_fourth_byte = None;
    let mut forty_fifth_byte = None;
    let mut scopes = vec![OutputScope {
        node: body,
        previous_end: body.span.begin.byte,
        previous_span_has_terminator: false,
    }];
    let mut inert_count = 0usize;
    let mut nested_count = 0usize;
    let mut offset = 0usize;
    while offset < call_nodes.len() {
        let id = u32::try_from(offset)
            .ok()
            .and_then(|value| value.checked_add(3))
            .ok_or(FrontendJsonError::Unsupported)?;
        let remaining = call_nodes
            .get(offset..)
            .ok_or(FrontendJsonError::Unsupported)?;
        let node = remaining.first().ok_or(FrontendJsonError::Unsupported)?;
        // A child of an earlier block cannot re-enter that closed block.
        while scopes
            .last()
            .is_some_and(|scope| scope.node.id != node.parent)
        {
            let _closed = scopes.pop();
        }
        let scope_depth = scopes.len();
        let scope = scopes.last_mut().ok_or(FrontendJsonError::Unsupported)?;
        if node.kind == "compound-statement" {
            let start = &node.span.begin;
            let end = &node.span.end;
            if node.id != id
                || node.name.is_some()
                || node.reference.is_some()
                || node.definition.is_some()
                || node.inline_specified.is_some()
                || node.linkage.is_some()
                || node.storage_class.is_some()
                || node.type_name.is_some()
                || node.operation.is_some()
                || node.constant_integer.is_some()
                || node.literal.is_some()
                || start.byte < scope.previous_end
                || start.byte <= scope.node.span.begin.byte
                || end.byte >= scope.node.span.end.byte
                || start.byte.checked_add(2).is_none_or(|min| end.byte < min)
                || start.line == 0
                || start.column == 0
                || end.line < start.line
                || end.column == 0
                || start.line < scope.node.span.begin.line
                || end.line > scope.node.span.end.line
                || (start.line == end.line
                    && (end.column.checked_sub(start.column) != end.byte.checked_sub(start.byte)))
                || scope_depth >= MAX_COMPOUND_DEPTH
            {
                return Err(FrontendJsonError::Unsupported);
            }
            nested_count = nested_count.saturating_add(1);
            if nested_count > MAX_NESTED_OUTPUT_SCOPES {
                return Err(FrontendJsonError::Unsupported);
            }
            scope.previous_end = end.byte;
            scope.previous_span_has_terminator = true;
            scopes.push(OutputScope {
                node,
                previous_end: start.byte,
                previous_span_has_terminator: false,
            });
            offset = offset.saturating_add(1);
            continue;
        }
        if let Some((consumed, end)) =
            inert_output_statement(remaining, scope.node, scope.previous_end, id)
        {
            inert_count = inert_count.saturating_add(1);
            if inert_count > MAX_INERT_OUTPUT_STATEMENTS {
                return Err(FrontendJsonError::Unsupported);
            }
            scope.previous_end = end;
            scope.previous_span_has_terminator = node.kind == "null-statement";
            offset = offset.saturating_add(consumed);
            continue;
        }
        if calls.len() >= MAX_LITERAL_OUTPUT_CALLS {
            return Err(FrontendJsonError::Unsupported);
        }
        let discards_return_value =
            node.kind == "cast-expression" && node.operation.as_deref() == Some("to-void");
        let mut argument_end = offset
            .checked_add(3usize.saturating_add(usize::from(discards_return_value)))
            .ok_or(FrontendJsonError::Unsupported)?;
        for _ in 0..MAX_OUTPUT_ARGUMENT_WRAPPERS {
            let Some(argument_node) = call_nodes.get(argument_end) else {
                return Err(FrontendJsonError::Unsupported);
            };
            if !matches!(
                argument_node.kind.as_str(),
                "parenthesized-expression" | "cast-expression" | "unary-expression"
            ) {
                break;
            }
            argument_end = argument_end
                .checked_add(1)
                .ok_or(FrontendJsonError::Unsupported)?;
        }
        let end = argument_end
            .checked_add(1)
            .ok_or(FrontendJsonError::Unsupported)?;
        let group = call_nodes
            .get(offset..end)
            .ok_or(FrontendJsonError::Unsupported)?;
        let byte = admitted_output_byte(
            group,
            scope.node,
            scope.previous_end,
            id,
            scope.previous_span_has_terminator,
        )
        .ok_or(FrontendJsonError::Unsupported)?;
        if selected_byte.is_some_and(|previous| previous != byte) {
            // Exact source-ordered eleven through nineteen-byte witnesses cannot
            // weaken any prior complete finite recipe.
            let witnessed: Vec<_> = [
                selected_byte,
                mixed_byte,
                third_byte,
                fourth_byte,
                fifth_byte,
                sixth_byte,
                seventh_byte,
                eighth_byte,
                ninth_byte,
                tenth_byte,
                eleventh_byte,
                twelfth_byte,
                thirteenth_byte,
                fourteenth_byte,
                fifteenth_byte,
                sixteenth_byte,
                seventeenth_byte,
                eighteenth_byte,
                nineteenth_byte,
                twentieth_byte,
                twenty_first_byte,
                twenty_second_byte,
                twenty_third_byte,
                twenty_fourth_byte,
                twenty_fifth_byte,
                twenty_sixth_byte,
                twenty_seventh_byte,
                twenty_eighth_byte,
                twenty_ninth_byte,
                thirtieth_byte,
                thirty_first_byte,
                thirty_second_byte,
                thirty_third_byte,
                thirty_fourth_byte,
                thirty_fifth_byte,
                thirty_sixth_byte,
                thirty_seventh_byte,
                thirty_eighth_byte,
                thirty_ninth_byte,
                fortieth_byte,
                forty_first_byte,
                forty_second_byte,
                forty_third_byte,
                forty_fourth_byte,
                forty_fifth_byte,
            ]
            .into_iter()
            .flatten()
            .collect();
            let next_eleven = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_ELEVEN_BYTES.len()
                && DISTINCT_ELEVEN_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_ELEVEN_BYTES.get(witnessed.len()) == Some(&byte);
            let next_twelve = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_TWELVE_BYTES.len()
                && DISTINCT_TWELVE_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_TWELVE_BYTES.get(witnessed.len()) == Some(&byte);
            let next_thirteen = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_THIRTEEN_BYTES.len()
                && DISTINCT_THIRTEEN_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_THIRTEEN_BYTES.get(witnessed.len()) == Some(&byte);
            let next_fourteen = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_FOURTEEN_BYTES.len()
                && DISTINCT_FOURTEEN_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_FOURTEEN_BYTES.get(witnessed.len()) == Some(&byte);
            let next_fifteen = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_FIFTEEN_BYTES.len()
                && DISTINCT_FIFTEEN_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_FIFTEEN_BYTES.get(witnessed.len()) == Some(&byte);
            let next_sixteen = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_SIXTEEN_BYTES.len()
                && DISTINCT_SIXTEEN_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_SIXTEEN_BYTES.get(witnessed.len()) == Some(&byte);
            let next_seventeen = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_SEVENTEEN_BYTES.len()
                && DISTINCT_SEVENTEEN_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_SEVENTEEN_BYTES.get(witnessed.len()) == Some(&byte);
            let next_eighteen = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_EIGHTEEN_BYTES.len()
                && DISTINCT_EIGHTEEN_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_EIGHTEEN_BYTES.get(witnessed.len()) == Some(&byte);
            let next_nineteen = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_NINETEEN_BYTES.len()
                && DISTINCT_NINETEEN_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_NINETEEN_BYTES.get(witnessed.len()) == Some(&byte);
            let next_twenty = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_TWENTY_BYTES.len()
                && DISTINCT_TWENTY_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_TWENTY_BYTES.get(witnessed.len()) == Some(&byte);
            let next_twenty_one = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_TWENTY_ONE_BYTES.len()
                && DISTINCT_TWENTY_ONE_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_TWENTY_ONE_BYTES.get(witnessed.len()) == Some(&byte);
            let next_twenty_two = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_TWENTY_TWO_BYTES.len()
                && DISTINCT_TWENTY_TWO_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_TWENTY_TWO_BYTES.get(witnessed.len()) == Some(&byte);
            let next_twenty_three = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_TWENTY_THREE_BYTES.len()
                && DISTINCT_TWENTY_THREE_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_TWENTY_THREE_BYTES.get(witnessed.len()) == Some(&byte);
            let next_twenty_four = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_TWENTY_FOUR_BYTES.len()
                && DISTINCT_TWENTY_FOUR_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_TWENTY_FOUR_BYTES.get(witnessed.len()) == Some(&byte);
            let next_twenty_five = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_TWENTY_FIVE_BYTES.len()
                && DISTINCT_TWENTY_FIVE_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_TWENTY_FIVE_BYTES.get(witnessed.len()) == Some(&byte);
            let next_twenty_six = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_TWENTY_SIX_BYTES.len()
                && DISTINCT_TWENTY_SIX_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_TWENTY_SIX_BYTES.get(witnessed.len()) == Some(&byte);
            let next_twenty_seven = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_TWENTY_SEVEN_BYTES.len()
                && DISTINCT_TWENTY_SEVEN_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_TWENTY_SEVEN_BYTES.get(witnessed.len()) == Some(&byte);
            let next_twenty_eight = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_TWENTY_EIGHT_BYTES.len()
                && DISTINCT_TWENTY_EIGHT_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_TWENTY_EIGHT_BYTES.get(witnessed.len()) == Some(&byte);
            let next_twenty_nine = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_TWENTY_NINE_BYTES.len()
                && DISTINCT_TWENTY_NINE_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_TWENTY_NINE_BYTES.get(witnessed.len()) == Some(&byte);
            let next_thirty = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_THIRTY_BYTES.len()
                && DISTINCT_THIRTY_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_THIRTY_BYTES.get(witnessed.len()) == Some(&byte);
            let next_thirty_one = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_THIRTY_ONE_BYTES.len()
                && DISTINCT_THIRTY_ONE_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_THIRTY_ONE_BYTES.get(witnessed.len()) == Some(&byte);
            let next_thirty_two = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_THIRTY_TWO_BYTES.len()
                && DISTINCT_THIRTY_TWO_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_THIRTY_TWO_BYTES.get(witnessed.len()) == Some(&byte);
            let next_thirty_three = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_THIRTY_THREE_BYTES.len()
                && DISTINCT_THIRTY_THREE_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_THIRTY_THREE_BYTES.get(witnessed.len()) == Some(&byte);
            let next_thirty_four = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_THIRTY_FOUR_BYTES.len()
                && DISTINCT_THIRTY_FOUR_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_THIRTY_FOUR_BYTES.get(witnessed.len()) == Some(&byte);
            let next_thirty_five = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_THIRTY_FIVE_BYTES.len()
                && DISTINCT_THIRTY_FIVE_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_THIRTY_FIVE_BYTES.get(witnessed.len()) == Some(&byte);
            let next_thirty_six = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_THIRTY_SIX_BYTES.len()
                && DISTINCT_THIRTY_SIX_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_THIRTY_SIX_BYTES.get(witnessed.len()) == Some(&byte);
            let next_thirty_seven = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_THIRTY_SEVEN_BYTES.len()
                && DISTINCT_THIRTY_SEVEN_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_THIRTY_SEVEN_BYTES.get(witnessed.len()) == Some(&byte);
            let next_thirty_eight = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_THIRTY_EIGHT_BYTES.len()
                && DISTINCT_THIRTY_EIGHT_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_THIRTY_EIGHT_BYTES.get(witnessed.len()) == Some(&byte);
            let next_thirty_nine = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_THIRTY_NINE_BYTES.len()
                && DISTINCT_THIRTY_NINE_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_THIRTY_NINE_BYTES.get(witnessed.len()) == Some(&byte);
            let next_forty = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_FORTY_BYTES.len()
                && DISTINCT_FORTY_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_FORTY_BYTES.get(witnessed.len()) == Some(&byte);
            let next_forty_one = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_FORTY_ONE_BYTES.len()
                && DISTINCT_FORTY_ONE_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_FORTY_ONE_BYTES.get(witnessed.len()) == Some(&byte);
            let next_forty_two = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_FORTY_TWO_BYTES.len()
                && DISTINCT_FORTY_TWO_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_FORTY_TWO_BYTES.get(witnessed.len()) == Some(&byte);
            let next_forty_three = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_FORTY_THREE_BYTES.len()
                && DISTINCT_FORTY_THREE_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_FORTY_THREE_BYTES.get(witnessed.len())
                    == Some(&byte);
            let next_forty_four = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_FORTY_FOUR_BYTES.len()
                && DISTINCT_FORTY_FOUR_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_FORTY_FOUR_BYTES.get(witnessed.len())
                    == Some(&byte);
            let next_forty_five = witnessed.len() == calls.len()
                && witnessed.len() < DISTINCT_FORTY_FIVE_BYTES.len()
                && DISTINCT_FORTY_FIVE_BYTES
                    .get(..witnessed.len())
                    .is_some_and(|prefix| witnessed == prefix)
                && DISTINCT_FORTY_FIVE_BYTES.get(witnessed.len())
                    == Some(&byte);
            if next_eleven
                || next_twelve
                || next_thirteen
                || next_fourteen
                || next_fifteen
                || next_sixteen
                || next_seventeen
                || next_eighteen
                || next_nineteen
                || next_twenty
                || next_twenty_one
                || next_twenty_two
                || next_twenty_three
                || next_twenty_four
                || next_twenty_five
                || next_twenty_six
                || next_twenty_seven
                || next_twenty_eight
                || next_twenty_nine
                || next_thirty
                || next_thirty_one
                || next_thirty_two
                || next_thirty_three
                || next_thirty_four
                || next_thirty_five
                || next_thirty_six
                || next_thirty_seven
                || next_thirty_eight
                || next_thirty_nine
                || next_forty
                || next_forty_one
                || next_forty_two
                || next_forty_three
                || next_forty_four
                || next_forty_five
            {
                match calls.len() {
                    1 => mixed_byte = Some(byte),
                    2 => third_byte = Some(byte),
                    3 => fourth_byte = Some(byte),
                    4 => fifth_byte = Some(byte),
                    5 => sixth_byte = Some(byte),
                    6 => seventh_byte = Some(byte),
                    7 => eighth_byte = Some(byte),
                    8 => ninth_byte = Some(byte),
                    9 => tenth_byte = Some(byte),
                    10 => eleventh_byte = Some(byte),
                    11 => twelfth_byte = Some(byte),
                    12 => thirteenth_byte = Some(byte),
                    13 => fourteenth_byte = Some(byte),
                    14 => fifteenth_byte = Some(byte),
                    15 => sixteenth_byte = Some(byte),
                    16 => seventeenth_byte = Some(byte),
                    17 => eighteenth_byte = Some(byte),
                    18 => nineteenth_byte = Some(byte),
                    19 => twentieth_byte = Some(byte),
                    20 => twenty_first_byte = Some(byte),
                    21 => twenty_second_byte = Some(byte),
                    22 => twenty_third_byte = Some(byte),
                    23 => twenty_fourth_byte = Some(byte),
                    24 => twenty_fifth_byte = Some(byte),
                    25 => twenty_sixth_byte = Some(byte),
                    26 => twenty_seventh_byte = Some(byte),
                    27 => twenty_eighth_byte = Some(byte),
                    28 => twenty_ninth_byte = Some(byte),
                    29 => thirtieth_byte = Some(byte),
                    30 => thirty_first_byte = Some(byte),
                    31 => thirty_second_byte = Some(byte),
                    32 => thirty_third_byte = Some(byte),
                    33 => thirty_fourth_byte = Some(byte),
                    34 => thirty_fifth_byte = Some(byte),
                    35 => thirty_sixth_byte = Some(byte),
                    36 => thirty_seventh_byte = Some(byte),
                    37 => thirty_eighth_byte = Some(byte),
                    38 => thirty_ninth_byte = Some(byte),
                    39 => fortieth_byte = Some(byte),
                    40 => forty_first_byte = Some(byte),
                    41 => forty_second_byte = Some(byte),
                    42 => forty_third_byte = Some(byte),
                    43 => forty_fourth_byte = Some(byte),
                    44 => forty_fifth_byte = Some(byte),
                    _ => return Err(FrontendJsonError::Unsupported),
                }
            } else if calls.len() == 1 && mixed_byte.is_none() {
                let is_zero_then_literal =
                    selected_byte == Some(0) && matches!(byte, b'Z' | b'P' | b'T' | b'S');
                let is_distinct_nonzero = matches!(
                    (selected_byte, byte),
                    (Some(b'Y'), b'/' | b'$') | (Some(b'Q'), b'.')
                );
                let is_triple_prefix = matches!(
                    (selected_byte, byte),
                    (Some(b'Z'), b'%')
                        | (Some(b'Q'), b'.' | b'"' | 28)
                        | (Some(b'Y'), b'-')
                        | (Some(b'T'), b'"' | b'=')
                        | (Some(b'6'), b'>')
                        | (Some(b'S'), 32)
                );
                if !(is_zero_then_literal || is_distinct_nonzero || is_triple_prefix) {
                    return Err(FrontendJsonError::Unsupported);
                }
                mixed_byte = Some(byte);
            } else if calls.len() == 2 && third_byte.is_none() {
                if !matches!(
                    (selected_byte, mixed_byte, byte),
                    (Some(b'Z'), Some(b'%'), b'H')
                        | (Some(b'Q'), Some(b'.' | 28), b'O')
                        | (Some(b'Q'), Some(b'"'), 27 | 253)
                        | (Some(b'Y'), Some(b'-'), b'P')
                        | (Some(b'T'), Some(b'"'), b'O' | b'Q')
                        | (Some(b'T'), Some(b'='), b'4' | 141)
                        | (Some(b'6'), Some(b'>'), b'5')
                        | (Some(b'S'), Some(32), 23)
                ) {
                    return Err(FrontendJsonError::Unsupported);
                }
                third_byte = Some(byte);
            } else if calls.len() == 3 && fourth_byte.is_none() {
                if !matches!(
                    (selected_byte, mixed_byte, third_byte, byte),
                    (Some(b'T'), Some(b'='), Some(b'4'), b'>')
                        | (Some(b'T'), Some(b'='), Some(141), 209)
                        | (Some(b'Q'), Some(b'"'), Some(27), b'7')
                        | (Some(b'Q'), Some(b'"'), Some(253), 206)
                        | (Some(b'Q'), Some(28), Some(b'O'), 29)
                        | (Some(b'6'), Some(b'>'), Some(b'5'), 2)
                        | (Some(b'S'), Some(32), Some(23), b'<')
                ) {
                    return Err(FrontendJsonError::Unsupported);
                }
                fourth_byte = Some(byte);
            } else if calls.len() == 4 && fifth_byte.is_none() {
                if !matches!(
                    (selected_byte, mixed_byte, third_byte, fourth_byte, byte),
                    (Some(b'Q'), Some(b'"'), Some(27), Some(b'7'), b'9')
                        | (Some(b'Q'), Some(28), Some(b'O'), Some(29), b'P')
                        | (Some(b'6'), Some(b'>'), Some(b'5'), Some(2), b'T')
                        | (Some(b'S'), Some(32), Some(23), Some(b'<'), b'6')
                        | (Some(b'T'), Some(b'='), Some(141), Some(209), 192)
                        | (Some(b'Q'), Some(b'"'), Some(253), Some(206), 165)
                ) {
                    return Err(FrontendJsonError::Unsupported);
                }
                fifth_byte = Some(byte);
            } else if calls.len() == 5 && sixth_byte.is_none() {
                if (
                    selected_byte,
                    mixed_byte,
                    third_byte,
                    fourth_byte,
                    fifth_byte,
                    byte,
                ) != (Some(b'Q'), Some(28), Some(b'O'), Some(29), Some(b'P'), 27)
                    && (
                        selected_byte,
                        mixed_byte,
                        third_byte,
                        fourth_byte,
                        fifth_byte,
                        byte,
                    ) != (Some(b'6'), Some(b'>'), Some(b'5'), Some(2), Some(b'T'), 31)
                    && (
                        selected_byte,
                        mixed_byte,
                        third_byte,
                        fourth_byte,
                        fifth_byte,
                        byte,
                    ) != (Some(b'S'), Some(32), Some(23), Some(b'<'), Some(b'6'), 1)
                    && (
                        selected_byte,
                        mixed_byte,
                        third_byte,
                        fourth_byte,
                        fifth_byte,
                        byte,
                    ) != (Some(b'T'), Some(b'='), Some(141), Some(209), Some(192), 180)
                    && (
                        selected_byte,
                        mixed_byte,
                        third_byte,
                        fourth_byte,
                        fifth_byte,
                        byte,
                    ) != (Some(b'Q'), Some(b'"'), Some(253), Some(206), Some(165), 152)
                {
                    return Err(FrontendJsonError::Unsupported);
                }
                sixth_byte = Some(byte);
            } else if calls.len() == 6 && seventh_byte.is_none() {
                if (
                    selected_byte,
                    mixed_byte,
                    third_byte,
                    fourth_byte,
                    fifth_byte,
                    sixth_byte,
                    byte,
                ) != (
                    Some(b'6'),
                    Some(b'>'),
                    Some(b'5'),
                    Some(2),
                    Some(b'T'),
                    Some(31),
                    24,
                ) && (
                    selected_byte,
                    mixed_byte,
                    third_byte,
                    fourth_byte,
                    fifth_byte,
                    sixth_byte,
                    byte,
                ) != (
                    Some(b'S'),
                    Some(32),
                    Some(23),
                    Some(b'<'),
                    Some(b'6'),
                    Some(1),
                    b'R',
                ) && (
                    selected_byte,
                    mixed_byte,
                    third_byte,
                    fourth_byte,
                    fifth_byte,
                    sixth_byte,
                    byte,
                ) != (
                    Some(b'T'),
                    Some(b'='),
                    Some(141),
                    Some(209),
                    Some(192),
                    Some(180),
                    191,
                ) && (
                    selected_byte,
                    mixed_byte,
                    third_byte,
                    fourth_byte,
                    fifth_byte,
                    sixth_byte,
                    byte,
                ) != (
                    Some(b'Q'),
                    Some(b'"'),
                    Some(253),
                    Some(206),
                    Some(165),
                    Some(152),
                    186,
                ) {
                    return Err(FrontendJsonError::Unsupported);
                }
                seventh_byte = Some(byte);
            } else if calls.len() == 7 && eighth_byte.is_none() {
                if (
                    selected_byte,
                    mixed_byte,
                    third_byte,
                    fourth_byte,
                    fifth_byte,
                    sixth_byte,
                    seventh_byte,
                    byte,
                ) != (
                    Some(b'S'),
                    Some(32),
                    Some(23),
                    Some(b'<'),
                    Some(b'6'),
                    Some(1),
                    Some(b'R'),
                    6,
                ) && (
                    selected_byte,
                    mixed_byte,
                    third_byte,
                    fourth_byte,
                    fifth_byte,
                    sixth_byte,
                    seventh_byte,
                    byte,
                ) != (
                    Some(b'T'),
                    Some(b'='),
                    Some(141),
                    Some(209),
                    Some(192),
                    Some(180),
                    Some(191),
                    210,
                ) && (
                    selected_byte,
                    mixed_byte,
                    third_byte,
                    fourth_byte,
                    fifth_byte,
                    sixth_byte,
                    seventh_byte,
                    byte,
                ) != (
                    Some(b'Q'),
                    Some(b'"'),
                    Some(253),
                    Some(206),
                    Some(165),
                    Some(152),
                    Some(186),
                    182,
                ) {
                    return Err(FrontendJsonError::Unsupported);
                }
                eighth_byte = Some(byte);
            } else if calls.len() == 8 && ninth_byte.is_none() {
                if (
                    selected_byte,
                    mixed_byte,
                    third_byte,
                    fourth_byte,
                    fifth_byte,
                    sixth_byte,
                    seventh_byte,
                    eighth_byte,
                    byte,
                ) != (
                    Some(b'T'),
                    Some(b'='),
                    Some(141),
                    Some(209),
                    Some(192),
                    Some(180),
                    Some(191),
                    Some(210),
                    162,
                ) && (
                    selected_byte,
                    mixed_byte,
                    third_byte,
                    fourth_byte,
                    fifth_byte,
                    sixth_byte,
                    seventh_byte,
                    eighth_byte,
                    byte,
                ) != (
                    Some(b'Q'),
                    Some(b'"'),
                    Some(253),
                    Some(206),
                    Some(165),
                    Some(152),
                    Some(186),
                    Some(182),
                    135,
                ) {
                    return Err(FrontendJsonError::Unsupported);
                }
                ninth_byte = Some(byte);
            } else if calls.len() == 9 && tenth_byte.is_none() {
                if (
                    selected_byte,
                    mixed_byte,
                    third_byte,
                    fourth_byte,
                    fifth_byte,
                    sixth_byte,
                    seventh_byte,
                    eighth_byte,
                    ninth_byte,
                    byte,
                ) != (
                    Some(b'Q'),
                    Some(b'"'),
                    Some(253),
                    Some(206),
                    Some(165),
                    Some(152),
                    Some(186),
                    Some(182),
                    Some(135),
                    203,
                ) {
                    return Err(FrontendJsonError::Unsupported);
                }
                tenth_byte = Some(byte);
            } else {
                return Err(FrontendJsonError::Unsupported);
            }
        } else if mixed_byte.is_some() {
            return Err(FrontendJsonError::Unsupported);
        }
        if selected_byte.is_none() {
            selected_byte = Some(byte);
        }
        let call = group
            .get(usize::from(discards_return_value))
            .ok_or(FrontendJsonError::Unsupported)?;
        let literal = group.last().ok_or(FrontendJsonError::Unsupported)?;
        // Attribute signed constants to their complete source sign rather
        // than the positive leaf; parentheses retain checked source spans.
        let argument = group
            .iter()
            .find(|argument_node| argument_node.kind == "unary-expression")
            .unwrap_or(literal);
        scope.previous_end = node.span.end.byte;
        scope.previous_span_has_terminator = false;
        calls.push((call, argument));
        offset = end;
    }
    let root = scopes.first().ok_or(FrontendJsonError::Unsupported)?;
    let next_begin = returned.map_or(body.span.end.byte, |node| node.span.begin.byte);
    if root.previous_end > next_begin
        || (root.previous_end == next_begin
            && (returned.is_none() || !root.previous_span_has_terminator))
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // A three-byte prefix alone is not an admitted two-byte guest recipe.
    if third_byte.is_none()
        && matches!(
            (selected_byte, mixed_byte),
            (Some(b'Z'), Some(b'%'))
                | (Some(b'Y'), Some(b'-'))
                | (Some(b'T'), Some(b'"' | b'='))
                | (Some(b'Q'), Some(b'"' | 28))
                | (Some(b'6'), Some(b'>'))
        )
    {
        return Err(FrontendJsonError::Unsupported);
    }
    if fourth_byte.is_none()
        && matches!(
            (selected_byte, mixed_byte, third_byte),
            (Some(b'T'), Some(b'='), Some(b'4'))
                | (Some(b'Q'), Some(b'"'), Some(27))
                | (Some(b'Q'), Some(28), Some(b'O'))
                | (Some(b'6'), Some(b'>'), Some(b'5'))
        )
    {
        return Err(FrontendJsonError::Unsupported);
    }
    if fifth_byte.is_none()
        && matches!(
            (selected_byte, mixed_byte, third_byte, fourth_byte),
            (Some(b'Q'), Some(b'"'), Some(27), Some(b'7'))
                | (Some(b'Q'), Some(28), Some(b'O'), Some(29))
                | (Some(b'6'), Some(b'>'), Some(b'5'), Some(2))
        )
    {
        return Err(FrontendJsonError::Unsupported);
    }
    if sixth_byte.is_none()
        && (
            selected_byte,
            mixed_byte,
            third_byte,
            fourth_byte,
            fifth_byte,
        ) == (Some(b'Q'), Some(28), Some(b'O'), Some(29), Some(b'P'))
    {
        return Err(FrontendJsonError::Unsupported);
    }
    if sixth_byte.is_none()
        && (
            selected_byte,
            mixed_byte,
            third_byte,
            fourth_byte,
            fifth_byte,
        ) == (Some(b'6'), Some(b'>'), Some(b'5'), Some(2), Some(b'T'))
    {
        return Err(FrontendJsonError::Unsupported);
    }
    if seventh_byte.is_none()
        && (
            selected_byte,
            mixed_byte,
            third_byte,
            fourth_byte,
            fifth_byte,
            sixth_byte,
        ) == (
            Some(b'6'),
            Some(b'>'),
            Some(b'5'),
            Some(2),
            Some(b'T'),
            Some(31),
        )
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The eight-byte sequence is a complete witness; its shorter distinct
    // prefixes have no separately proved guest program.
    let observed: Vec<_> = [
        selected_byte,
        mixed_byte,
        third_byte,
        fourth_byte,
        fifth_byte,
        sixth_byte,
        seventh_byte,
        eighth_byte,
        ninth_byte,
        tenth_byte,
        eleventh_byte,
        twelfth_byte,
        thirteenth_byte,
        fourteenth_byte,
        fifteenth_byte,
        sixteenth_byte,
        seventeenth_byte,
        eighteenth_byte,
        nineteenth_byte,
        twentieth_byte,
        twenty_first_byte,
        twenty_second_byte,
        twenty_third_byte,
        twenty_fourth_byte,
        twenty_fifth_byte,
        twenty_sixth_byte,
        twenty_seventh_byte,
        twenty_eighth_byte,
        twenty_ninth_byte,
        thirtieth_byte,
        thirty_first_byte,
        thirty_second_byte,
        thirty_third_byte,
        thirty_fourth_byte,
        thirty_fifth_byte,
        thirty_sixth_byte,
        thirty_seventh_byte,
        thirty_eighth_byte,
        thirty_ninth_byte,
        fortieth_byte,
        forty_first_byte,
        forty_second_byte,
        forty_third_byte,
        forty_fourth_byte,
        forty_fifth_byte,
    ]
    .into_iter()
    .flatten()
    .collect();
    if (2..8).contains(&observed.len()) && observed == b"S \x17<6\x01R\x06"[..observed.len()] {
        return Err(FrontendJsonError::Unsupported);
    }
    // The nine-byte recipe also requires the complete witnessed sequence.
    if (2..9).contains(&observed.len())
        && observed == b"T=\x8d\xd1\xc0\xb4\xbf\xd2\xa2"[..observed.len()]
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No proper prefix of the ten-byte source witness is executable as this recipe.
    if (2..10).contains(&observed.len())
        && observed == b"Q\"\xfd\xce\xa5\x98\xba\xb6\x87\xcb"[..observed.len()]
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No proper eleven-byte prefix is an independently proven guest mode.
    if (2..11).contains(&observed.len())
        && DISTINCT_ELEVEN_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // Only the full thirteen-byte sequence has an independently verified layout.
    if (2..13).contains(&observed.len())
        && DISTINCT_THIRTEEN_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // Only the full fourteen-byte sequence has an independently verified layout.
    if (2..14).contains(&observed.len())
        && DISTINCT_FOURTEEN_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The fifteen-byte recipe requires every effect; the two-byte Q. prefix
    // already has a separate, independently verified guest witness.
    if (3..15).contains(&observed.len())
        && DISTINCT_FIFTEEN_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The sixteen-byte recipe has no separately proven proper source prefix.
    if (2..16).contains(&observed.len())
        && DISTINCT_SIXTEEN_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The seventeen-byte recipe has no separately proven proper source prefix.
    if (2..17).contains(&observed.len())
        && DISTINCT_SEVENTEEN_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The eighteen-byte recipe has no separately proven proper source prefix.
    if (2..18).contains(&observed.len())
        && DISTINCT_EIGHTEEN_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The nineteen-byte recipe has no separately proven proper source prefix.
    if (2..19).contains(&observed.len())
        && DISTINCT_NINETEEN_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The twenty-byte recipe has no separately proven proper source prefix.
    if (2..20).contains(&observed.len())
        && DISTINCT_TWENTY_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The twenty-one-byte recipe has no separately proven proper source prefix.
    if (2..21).contains(&observed.len())
        && DISTINCT_TWENTY_ONE_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The twenty-two-byte recipe has no separately proven proper source prefix.
    if (2..22).contains(&observed.len())
        && DISTINCT_TWENTY_TWO_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The twenty-three-byte recipe has no separately proven proper source prefix.
    if (2..23).contains(&observed.len())
        && DISTINCT_TWENTY_THREE_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The twenty-four-byte recipe has no separately proven proper source prefix.
    if (2..24).contains(&observed.len())
        && DISTINCT_TWENTY_FOUR_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The twenty-five-byte recipe has no separately proven proper source prefix.
    if (2..25).contains(&observed.len())
        && DISTINCT_TWENTY_FIVE_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The independently proved 25-byte prefix remains admitted; others refuse.
    if (2..26).contains(&observed.len())
        && observed.len() != 25
        && DISTINCT_TWENTY_SIX_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The twenty-seven-byte recipe only admits proven proper source prefixes.
    if (2..27).contains(&observed.len())
        && !matches!(observed.len(), 25 | 26)
        && DISTINCT_TWENTY_SEVEN_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The twenty-eight-byte recipe admits only independently proven prefixes.
    if (2..28).contains(&observed.len())
        && !(25..=27).contains(&observed.len())
        && DISTINCT_TWENTY_EIGHT_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No proper prefix of the independent twenty-nine-byte trace is proved.
    if (2..29).contains(&observed.len())
        && DISTINCT_TWENTY_NINE_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No proper prefix of the independent thirty-byte trace is proved.
    if (2..30).contains(&observed.len())
        && DISTINCT_THIRTY_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No proper prefix of this independent thirty-one-byte trace is proved.
    if (2..31).contains(&observed.len())
        && DISTINCT_THIRTY_ONE_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No proper prefix of this independent thirty-two-byte trace is proved.
    if (2..32).contains(&observed.len())
        && DISTINCT_THIRTY_TWO_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No proper prefix of this independent thirty-three-byte trace is proved.
    if (2..33).contains(&observed.len())
        && DISTINCT_THIRTY_THREE_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No proper prefix of this independent thirty-four-byte trace is proved.
    if (2..34).contains(&observed.len())
        && DISTINCT_THIRTY_FOUR_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No proper prefix of this independent thirty-five-byte trace is proved.
    if (2..35).contains(&observed.len())
        && DISTINCT_THIRTY_FIVE_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No proper prefix of this independent thirty-six-byte trace is proved.
    if (2..36).contains(&observed.len())
        && DISTINCT_THIRTY_SIX_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No proper prefix of this independent thirty-seven-byte trace is proved.
    if (2..37).contains(&observed.len())
        && DISTINCT_THIRTY_SEVEN_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No proper prefix of this independent thirty-eight-byte trace is proved.
    if (2..38).contains(&observed.len())
        && DISTINCT_THIRTY_EIGHT_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No proper prefix of this independent thirty-nine-byte trace is proved.
    if (2..39).contains(&observed.len())
        && DISTINCT_THIRTY_NINE_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // Proper prefixes of the forty-byte source have no separate guest witness.
    if (2..40).contains(&observed.len())
        && DISTINCT_FORTY_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // Proper prefixes of the forty-one-byte source have no separate guest witness.
    if (2..41).contains(&observed.len())
        && DISTINCT_FORTY_ONE_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No strict proper prefix of the forty-four source is independently proved.
    if (2..44).contains(&observed.len())
        && DISTINCT_FORTY_FOUR_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // No strict proper prefix of the forty-five source is independently proved.
    if (2..45).contains(&observed.len())
        && DISTINCT_FORTY_FIVE_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // Only the two-byte Q. prefix has a separate proven guest witness.
    if (3..43).contains(&observed.len())
        && DISTINCT_FORTY_THREE_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    // The 40-byte prefix has its own independent witness; the 41-byte
    // proper prefix does not match either complete 41- or 42-byte witness.
    if observed.len() == 41 && observed == DISTINCT_FORTY_TWO_BYTES[..41] {
        return Err(FrontendJsonError::Unsupported);
    }
    // All twelve byte effects must be present before selecting this layout.
    if (2..12).contains(&observed.len())
        && DISTINCT_TWELVE_BYTES
            .get(..observed.len())
            .is_some_and(|prefix| observed == prefix)
    {
        return Err(FrontendJsonError::Unsupported);
    }
    Ok(LiteralOutputNodes {
        body,
        byte: selected_byte.ok_or(FrontendJsonError::Unsupported)?,
        calls,
        function,
        mixed_byte,
        third_byte,
        fourth_byte,
        fifth_byte,
        sixth_byte,
        seventh_byte,
        eighth_byte,
        ninth_byte,
        tenth_byte,
        eleventh_byte,
        twelfth_byte,
        thirteenth_byte,
        fourteenth_byte,
        fifteenth_byte,
        sixteenth_byte,
        seventeenth_byte,
        eighteenth_byte,
        nineteenth_byte,
        twentieth_byte,
        twenty_first_byte,
        twenty_second_byte,
        twenty_third_byte,
        twenty_fourth_byte,
        twenty_fifth_byte,
        twenty_sixth_byte,
        twenty_seventh_byte,
        twenty_eighth_byte,
        twenty_ninth_byte,
        thirtieth_byte,
        thirty_first_byte,
        thirty_second_byte,
        thirty_third_byte,
        thirty_fourth_byte,
        thirty_fifth_byte,
        thirty_sixth_byte,
        thirty_seventh_byte,
        thirty_eighth_byte,
        thirty_ninth_byte,
        fortieth_byte,
        forty_first_byte,
        forty_second_byte,
        forty_third_byte,
        forty_fourth_byte,
        forty_fifth_byte,
        returned,
    })
}

/// Compile one through 33 identical source-proven byte `putchar(N)` calls
/// with bounded inert statements and an explicit or implicit void return.
#[expect(
    clippy::too_many_lines,
    reason = "canonical typed-effect projection and re-admission"
)]
fn canonical_literal_output_typed_ir(
    bytes: &[u8],
) -> Result<LiteralOutputProjection, FrontendJsonError> {
    if bytes.is_empty() || bytes.len() > MAX_FRONTEND_JSON_BYTES {
        return Err(FrontendJsonError::Malformed);
    }
    let input: Artifact =
        serde_json::from_slice(bytes).map_err(|_error| FrontendJsonError::Malformed)?;
    if input.schema_version != 1
        || input.identity != EXPECTED_ARTIFACT
        || input.profile.abi_id != EXPECTED_ABI
        || input.profile.target_profile != EXPECTED_PROFILE
        || input.clang.version != "22.1.8"
        || input.clang.target != "wasm32-unknown-unknown"
        || input.clang.language != "c23"
        || input.source.id.is_empty()
    {
        return Err(FrontendJsonError::Unsupported);
    }
    let LiteralOutputNodes {
        function,
        body,
        byte,
        mixed_byte,
        third_byte,
        fourth_byte,
        fifth_byte,
        sixth_byte,
        seventh_byte,
        eighth_byte,
        ninth_byte,
        tenth_byte,
        eleventh_byte,
        twelfth_byte,
        thirteenth_byte,
        fourteenth_byte,
        fifteenth_byte,
        sixteenth_byte,
        seventeenth_byte,
        eighteenth_byte,
        nineteenth_byte,
        twentieth_byte,
        twenty_first_byte,
        twenty_second_byte,
        twenty_third_byte,
        twenty_fourth_byte,
        twenty_fifth_byte,
        twenty_sixth_byte,
        twenty_seventh_byte,
        twenty_eighth_byte,
        twenty_ninth_byte,
        thirtieth_byte,
        thirty_first_byte,
        thirty_second_byte,
        thirty_third_byte,
        thirty_fourth_byte,
        thirty_fifth_byte,
        thirty_sixth_byte,
        thirty_seventh_byte,
        thirty_eighth_byte,
        thirty_ninth_byte,
        fortieth_byte,
        forty_first_byte,
        forty_second_byte,
        forty_third_byte,
        forty_fourth_byte,
        forty_fifth_byte,
        calls,
        returned,
    } = admit_literal_output_nodes(&input.nodes)?;
    let name = function
        .name
        .clone()
        .ok_or(FrontendJsonError::Unsupported)?;
    let void_function = if let Some(returned) = returned {
        FrontendReturnVoidFunction::new(FrontendReturnVoidFunctionSpec {
            body_span: span(&body.span),
            definition: String::from("definition"),
            function_span: span(&function.span),
            inline_specified: false,
            linkage: String::from("external"),
            name,
            return_span: span(&returned.span),
            signature: String::from("fn()->void"),
            storage_class: String::from("none"),
        })
    } else {
        FrontendReturnVoidFunction::new_fallthrough(FrontendFallthroughVoidFunctionSpec {
            body_span: span(&body.span),
            definition: String::from("definition"),
            function_span: span(&function.span),
            inline_specified: false,
            linkage: String::from("external"),
            name,
            signature: String::from("fn()->void"),
            storage_class: String::from("none"),
        })
    };
    let artifact = FrontendArtifact::new_void(
        FrontendArtifactSpec {
            abi_id: input.profile.abi_id,
            artifact_id: input.identity,
            clang_target: input.clang.target,
            clang_version: input.clang.version,
            functions: Vec::new(),
            language: input.clang.language,
            schema_version: input.schema_version,
            source_id: input.source.id,
            source_sha256: source_digest(&input.source.sha256)?,
            target_profile: input.profile.target_profile,
        },
        void_function,
    );
    let base =
        lower_frontend_artifact(&artifact).map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    let original = base
        .functions()
        .first()
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    let block = original
        .blocks()
        .first()
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    let first_argument = calls.first().ok_or(FrontendJsonError::Unsupported)?.1;
    let mut instructions = Vec::with_capacity(calls.len().saturating_mul(2).saturating_add(1));
    instructions.push(LocatedInstruction::new(
        Instruction::ConstantInteger {
            constant: IntegerConstant::new(8, vec![byte]),
            result: ValueId::new(0),
            type_id: TypeId::new(0),
        },
        typed_span(&first_argument.span),
    ));
    for (index, (call, argument)) in calls.into_iter().enumerate() {
        if index == 1
            && let Some(second) = mixed_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![second]),
                    result: ValueId::new(1),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 2
            && let Some(third) = third_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![third]),
                    result: ValueId::new(2),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 3
            && let Some(fourth) = fourth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![fourth]),
                    result: ValueId::new(3),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 4
            && let Some(fifth) = fifth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![fifth]),
                    result: ValueId::new(4),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 5
            && let Some(sixth) = sixth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![sixth]),
                    result: ValueId::new(5),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 6
            && let Some(seventh) = seventh_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![seventh]),
                    result: ValueId::new(6),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 7
            && let Some(eighth) = eighth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![eighth]),
                    result: ValueId::new(7),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 8
            && let Some(ninth) = ninth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![ninth]),
                    result: ValueId::new(8),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 9
            && let Some(tenth) = tenth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![tenth]),
                    result: ValueId::new(9),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 10
            && let Some(eleventh) = eleventh_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![eleventh]),
                    result: ValueId::new(10),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 11
            && let Some(twelfth) = twelfth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![twelfth]),
                    result: ValueId::new(11),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 12
            && let Some(thirteenth) = thirteenth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![thirteenth]),
                    result: ValueId::new(12),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 13
            && let Some(fourteenth) = fourteenth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![fourteenth]),
                    result: ValueId::new(13),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 14
            && let Some(fifteenth) = fifteenth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![fifteenth]),
                    result: ValueId::new(14),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 15
            && let Some(sixteenth) = sixteenth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![sixteenth]),
                    result: ValueId::new(15),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 16
            && let Some(seventeenth) = seventeenth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![seventeenth]),
                    result: ValueId::new(16),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 17
            && let Some(eighteenth) = eighteenth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![eighteenth]),
                    result: ValueId::new(17),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 18
            && let Some(nineteenth) = nineteenth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![nineteenth]),
                    result: ValueId::new(18),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 19
            && let Some(twentieth) = twentieth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![twentieth]),
                    result: ValueId::new(19),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 20
            && let Some(twenty_first) = twenty_first_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![twenty_first]),
                    result: ValueId::new(20),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 21
            && let Some(twenty_second) = twenty_second_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![twenty_second]),
                    result: ValueId::new(21),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 22
            && let Some(twenty_third) = twenty_third_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![twenty_third]),
                    result: ValueId::new(22),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 23
            && let Some(twenty_fourth) = twenty_fourth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![twenty_fourth]),
                    result: ValueId::new(23),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 24
            && let Some(twenty_fifth) = twenty_fifth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![twenty_fifth]),
                    result: ValueId::new(24),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 25
            && let Some(twenty_sixth) = twenty_sixth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![twenty_sixth]),
                    result: ValueId::new(25),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 26
            && let Some(twenty_seventh) = twenty_seventh_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![twenty_seventh]),
                    result: ValueId::new(26),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 27
            && let Some(twenty_eighth) = twenty_eighth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![twenty_eighth]),
                    result: ValueId::new(27),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 28
            && let Some(twenty_ninth) = twenty_ninth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![twenty_ninth]),
                    result: ValueId::new(28),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 29
            && let Some(thirtieth) = thirtieth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![thirtieth]),
                    result: ValueId::new(29),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 30
            && let Some(thirty_first) = thirty_first_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![thirty_first]),
                    result: ValueId::new(30),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 31
            && let Some(thirty_second) = thirty_second_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![thirty_second]),
                    result: ValueId::new(31),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 32
            && let Some(thirty_third) = thirty_third_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![thirty_third]),
                    result: ValueId::new(32),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 33
            && let Some(thirty_fourth) = thirty_fourth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![thirty_fourth]),
                    result: ValueId::new(33),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 34
            && let Some(thirty_fifth) = thirty_fifth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![thirty_fifth]),
                    result: ValueId::new(34),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 35
            && let Some(thirty_sixth) = thirty_sixth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![thirty_sixth]),
                    result: ValueId::new(35),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 36
            && let Some(thirty_seventh) = thirty_seventh_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![thirty_seventh]),
                    result: ValueId::new(36),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 37
            && let Some(thirty_eighth) = thirty_eighth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![thirty_eighth]),
                    result: ValueId::new(37),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 38
            && let Some(thirty_ninth) = thirty_ninth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![thirty_ninth]),
                    result: ValueId::new(38),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 39
            && let Some(fortieth) = fortieth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![fortieth]),
                    result: ValueId::new(39),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 40
            && let Some(forty_first) = forty_first_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![forty_first]),
                    result: ValueId::new(40),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 41
            && let Some(forty_second) = forty_second_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![forty_second]),
                    result: ValueId::new(41),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 42
            && let Some(forty_third) = forty_third_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![forty_third]),
                    result: ValueId::new(42),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 43
            && let Some(forty_fourth) = forty_fourth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![forty_fourth]),
                    result: ValueId::new(43),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        if index == 44
            && let Some(forty_fifth) = forty_fifth_byte
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ConstantInteger {
                    constant: IntegerConstant::new(8, vec![forty_fifth]),
                    result: ValueId::new(44),
                    type_id: TypeId::new(0),
                },
                typed_span(&argument.span),
            ));
        }
        instructions.push(LocatedInstruction::new(
            Instruction::ByteOutput {
                value: ValueId::new(if index == 44 && forty_fifth_byte.is_some() {
                    44
                } else if index == 43 && forty_fourth_byte.is_some() {
                    43
                } else if index == 42 && forty_third_byte.is_some() {
                    42
                } else if index == 41 && forty_second_byte.is_some() {
                    41
                } else if index == 40 && forty_first_byte.is_some() {
                    40
                } else if index == 39 && fortieth_byte.is_some() {
                    39
                } else if index == 38 && thirty_ninth_byte.is_some() {
                    38
                } else if index == 37 && thirty_eighth_byte.is_some() {
                    37
                } else if index == 36 && thirty_seventh_byte.is_some() {
                    36
                } else if index == 35 && thirty_sixth_byte.is_some() {
                    35
                } else if index == 34 && thirty_fifth_byte.is_some() {
                    34
                } else if index == 33 && thirty_fourth_byte.is_some() {
                    33
                } else if index == 32 && thirty_third_byte.is_some() {
                    32
                } else if index == 31 && thirty_second_byte.is_some() {
                    31
                } else if index == 30 && thirty_first_byte.is_some() {
                    30
                } else if index == 29 && thirtieth_byte.is_some() {
                    29
                } else if index == 28 && twenty_ninth_byte.is_some() {
                    28
                } else if index == 27 && twenty_eighth_byte.is_some() {
                    27
                } else if index == 26 && twenty_seventh_byte.is_some() {
                    26
                } else if index == 25 && twenty_sixth_byte.is_some() {
                    25
                } else if index == 24 && twenty_fifth_byte.is_some() {
                    24
                } else if index == 23 && twenty_fourth_byte.is_some() {
                    23
                } else if index == 22 && twenty_third_byte.is_some() {
                    22
                } else if index == 21 && twenty_second_byte.is_some() {
                    21
                } else if index == 20 && twenty_first_byte.is_some() {
                    20
                } else if index == 19 && twentieth_byte.is_some() {
                    19
                } else if index == 18 && nineteenth_byte.is_some() {
                    18
                } else if index == 17 && eighteenth_byte.is_some() {
                    17
                } else if index == 16 && seventeenth_byte.is_some() {
                    16
                } else if index == 15 && sixteenth_byte.is_some() {
                    15
                } else if index == 14 && fifteenth_byte.is_some() {
                    14
                } else if index == 13 && fourteenth_byte.is_some() {
                    13
                } else if index == 12 && thirteenth_byte.is_some() {
                    12
                } else if index == 11 && twelfth_byte.is_some() {
                    11
                } else if index == 10 && eleventh_byte.is_some() {
                    10
                } else if index == 9 && tenth_byte.is_some() {
                    9
                } else if index == 8 && ninth_byte.is_some() {
                    8
                } else if index == 7 && eighth_byte.is_some() {
                    7
                } else if index == 6 && seventh_byte.is_some() {
                    6
                } else if index == 5 && sixth_byte.is_some() {
                    5
                } else if index == 4 && fifth_byte.is_some() {
                    4
                } else if index == 3 && fourth_byte.is_some() {
                    3
                } else if index == 2 && third_byte.is_some() {
                    2
                } else {
                    u32::from(index == 1 && mixed_byte.is_some())
                }),
            },
            typed_span(&call.span),
        ));
    }
    let compiled_function = Function::new(FunctionSpec {
        blocks: vec![BasicBlock::new(BasicBlockSpec {
            id: block.id(),
            instructions,
            phis: block.phis().to_vec(),
            span: block.span(),
            terminator: block.terminator().clone(),
            terminator_span: block.terminator_span(),
        })],
        entry: original.entry(),
        id: original.id(),
        name: String::from(original.name()),
        parameters: original.parameters().to_vec(),
        signature: original.signature(),
        span: original.span(),
    });
    let module = Module::new(ModuleSpec {
        abi_id: String::from(base.abi_id()),
        format_version: base.format_version(),
        functions: vec![compiled_function],
        globals: base.globals().to_vec(),
        proof_obligations: base.proof_obligations().to_vec(),
        source_id: String::from(base.source_id()),
        source_sha256: *base.source_sha256(),
        target_profile: String::from(base.target_profile()),
        types: base.types().to_vec(),
    });
    let encoded = canonical_bytes(&module).map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    if canonical_module(&encoded).map_err(|_error| FrontendJsonError::InvalidTypedIr)? != module {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    let mode = if forty_fifth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralFortyFive
    } else if forty_fourth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralFortyFour
    } else if forty_third_byte.is_some() {
        FrontendGuestMode::DistinctLiteralFortyThree
    } else if forty_second_byte.is_some() {
        FrontendGuestMode::DistinctLiteralFortyTwo
    } else if forty_first_byte.is_some() {
        FrontendGuestMode::DistinctLiteralFortyOne
    } else if fortieth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralForty
    } else if thirty_ninth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralThirtyNine
    } else if thirty_eighth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralThirtyEight
    } else if thirty_seventh_byte.is_some() {
        FrontendGuestMode::DistinctLiteralThirtySeven
    } else if thirty_sixth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralThirtySix
    } else if thirty_fifth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralThirtyFive
    } else if thirty_fourth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralThirtyFour
    } else if thirty_third_byte.is_some() {
        FrontendGuestMode::DistinctLiteralThirtyThree
    } else if thirty_second_byte.is_some() {
        FrontendGuestMode::DistinctLiteralThirtyTwo
    } else if thirty_first_byte.is_some() {
        FrontendGuestMode::DistinctLiteralThirtyOne
    } else if thirtieth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralThirty
    } else if twenty_ninth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTwentyNine
    } else if twenty_eighth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTwentyEight
    } else if twenty_seventh_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTwentySeven
    } else if twenty_sixth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTwentySix
    } else if twenty_fifth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTwentyFive
    } else if twenty_fourth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTwentyFour
    } else if twenty_third_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTwentyThree
    } else if twenty_second_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTwentyTwo
    } else if twenty_first_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTwentyOne
    } else if twentieth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTwenty
    } else if nineteenth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralNineteen
    } else if eighteenth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralEighteen
    } else if seventeenth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralSeventeen
    } else if sixteenth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralSixteen
    } else if fifteenth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralFifteen
    } else if fourteenth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralFourteen
    } else if thirteenth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralThirteen
    } else if twelfth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTwelve
    } else if eleventh_byte.is_some() {
        FrontendGuestMode::DistinctLiteralEleven
    } else if tenth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTen
    } else if ninth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralNine
    } else if eighth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralEight
    } else if seventh_byte.is_some() {
        FrontendGuestMode::DistinctLiteralSeven
    } else if sixth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralSix
    } else if fifth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralQuint
    } else if fourth_byte.is_some() {
        FrontendGuestMode::DistinctLiteralQuad
    } else if third_byte.is_some() {
        FrontendGuestMode::DistinctLiteralTriple
    } else if mixed_byte.is_some() && byte == 0 {
        FrontendGuestMode::ZeroThenLiteral
    } else if mixed_byte.is_some() {
        FrontendGuestMode::DistinctLiteralPair
    } else if byte == 0 {
        FrontendGuestMode::InitialZeroOutput
    } else {
        FrontendGuestMode::SeededByteLiteral
    };
    Ok((encoded, mode))
}

/// Project the two supported C families without dropping observable output.
///
/// # Errors
///
/// Refuses unsupported Clang shapes, metadata drift and invalid typed IR.
pub fn canonical_guest_typed_ir(
    bytes: &[u8],
) -> Result<CanonicalGuestProjection, FrontendJsonError> {
    if let Ok(wire) = canonical_void_typed_ir(bytes) {
        return Ok((wire, FrontendGuestMode::EmptyVoid));
    }
    canonical_literal_output_typed_ir(bytes)
}
