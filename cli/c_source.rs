// File:
//   - c_source.rs
// Path:
//   - cli/c_source.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
//
// Boundary-Contract:
// - Owns:
//   - Lexical discovery of native-debug adapter symbols in authored C source.
// - Must-Not:
//   - Parse C semantics, infer guest lowering, or inspect comments and literals
//     as executable declarations.
// - Allows:
//   - Inputs: raw bytes from one C translation unit.
//   - Outputs: exact native-debug adapter capability flags.
//   - Side effects: none.
// - Split-When:
//   - Split when adapter selection requires semantic compiler evidence.
// - Merge-When:
//   - Merge when another module owns identical C lexical capability discovery.
// - Summary:
//   - Fail-closed lexical selection for host-only C debug adapters.
// - Description:
//   - Recognizes exact function-like identifiers outside comments and literals.
// - Usage:
//   - Called before constructing the CLI native C debug-run plan.
// - Defaults:
//   - Unknown text selects no adapter.
//
// Related documents:
// - cli/README.md
//
// Large file:
//   - false
//

//! Lexical C-source inspection for native debug adapter selection.

use std::iter::{Copied, Peekable};
use std::slice::Iter;

const DOOM_HOST_MARKERS: [&[u8]; 2] =
    [b"DoomHost_GuestMemoryRegion", b"DoomHost_VideoInitialize"];
const GUEST_OUTPUT_MARKER: &[u8] = b"__malbolge_output_byte";

type SourceBytes<'source> = Peekable<Copied<Iter<'source, u8>>>;

/// Native-debug adapter capabilities discovered in one C source unit.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct CSourceAdapters {
    doom_host: bool,
    guest_output: bool,
}

impl CSourceAdapters {
    /// Whether the source references both required DOOM host entry points.
    #[must_use]
    pub const fn doom_host(self) -> bool {
        self.doom_host
    }

    /// Whether the source references the fundamental guest byte-output symbol.
    #[must_use]
    pub const fn guest_output(self) -> bool {
        self.guest_output
    }
}

/// Inspect one translation unit without treating comments or literals as code.
#[must_use]
pub fn inspect_c_source(source: &[u8]) -> CSourceAdapters {
    let spliced = splice_lines(source);
    CSourceAdapters {
        doom_host: DOOM_HOST_MARKERS
            .iter()
            .all(|marker| contains_function_identifier(&spliced, marker)),
        guest_output: contains_function_identifier(
            &spliced,
            GUEST_OUTPUT_MARKER,
        ),
    }
}

fn contains_function_identifier(source: &[u8], target: &[u8]) -> bool {
    let mut bytes = source.iter().copied().peekable();
    let mut pending_identifier = Vec::new();
    while let Some(byte) = bytes.next() {
        if byte.is_ascii_whitespace() {
            continue;
        }
        if skip_comment(byte, &mut bytes) {
            continue;
        }
        if matches!(byte, b'"' | b'\'') {
            skip_quoted(byte, &mut bytes);
            pending_identifier.clear();
            continue;
        }
        if is_identifier_start(byte) {
            pending_identifier = read_identifier(byte, &mut bytes);
            continue;
        }
        if byte == b'(' && pending_identifier == target {
            return true;
        }
        pending_identifier.clear();
    }
    false
}

const fn is_identifier_continue(byte: u8) -> bool {
    is_identifier_start(byte) || byte.is_ascii_digit()
}

const fn is_identifier_start(byte: u8) -> bool {
    byte.is_ascii_alphabetic() || byte == b'_'
}

fn read_identifier(first: u8, bytes: &mut SourceBytes<'_>) -> Vec<u8> {
    let mut identifier = vec![first];
    while let Some(byte) = bytes.next_if(|byte| is_identifier_continue(*byte)) {
        identifier.push(byte);
    }
    identifier
}

fn skip_block_comment(bytes: &mut SourceBytes<'_>) {
    let mut previous = None;
    for byte in bytes.by_ref() {
        if previous == Some(b'*') && byte == b'/' {
            return;
        }
        previous = Some(byte);
    }
}

fn skip_comment(first: u8, bytes: &mut SourceBytes<'_>) -> bool {
    if first != b'/' {
        return false;
    }
    match bytes.peek().copied() {
        Some(b'/') => {
            let _consumed = bytes.next();
            skip_line_comment(bytes);
            true
        },
        Some(b'*') => {
            let _consumed = bytes.next();
            skip_block_comment(bytes);
            true
        },
        _ => false,
    }
}

fn skip_line_comment(bytes: &mut SourceBytes<'_>) {
    for byte in bytes.by_ref() {
        if matches!(byte, b'\n' | b'\r') {
            return;
        }
    }
}

fn skip_quoted(terminator: u8, bytes: &mut SourceBytes<'_>) {
    while let Some(byte) = bytes.next() {
        if byte == b'\\' {
            let _escaped = bytes.next();
        } else if byte == terminator {
            return;
        }
    }
}

fn splice_lines(source: &[u8]) -> Vec<u8> {
    let mut bytes = source.iter().copied().peekable();
    let mut result = Vec::with_capacity(source.len());
    while let Some(byte) = bytes.next() {
        if byte == b'\\' && skip_line_ending(&mut bytes) {
            continue;
        }
        result.push(byte);
    }
    result
}

fn skip_line_ending(bytes: &mut SourceBytes<'_>) -> bool {
    if bytes.next_if_eq(&b'\n').is_some() {
        return true;
    }
    if bytes.peek() != Some(&b'\r') {
        return false;
    }
    let mut probe = bytes.clone();
    let _probe_start = probe.peek();
    let _probe_carriage_return = probe.next();
    if probe.next() != Some(b'\n') {
        return false;
    }
    let _consumed_carriage_return = bytes.next();
    let _consumed_line_feed = bytes.next();
    true
}
