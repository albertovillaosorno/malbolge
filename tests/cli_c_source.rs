// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Regression evidence for C native-debug adapter source selection.
// - Must-Not:
//   - Execute a host compiler or claim guest lowering.
// - Allows:
//   - Inputs: synthetic C translation-unit bytes.
//   - Outputs: exact adapter capability assertions.
//   - Side effects: none.
// - Split-When:
//   - Split when end-to-end native execution needs independent evidence.
// - Merge-When:
//   - Merge when another test owns the same lexical selection contract.
// - Summary:
//   - C lexical adapter-selection regression tests.
// - Description:
//   - Proves comments, literals, token prefixes, and line splices are inert.
// - Usage:
//   - Collected by the repository Cargo test suite.
// - Defaults:
//   - Non-code marker text selects no adapter.
//

//! Regression tests for C native-debug adapter lexical selection.

#[path = "../src/interface/command-line/application/c_source.rs"]
pub mod c_source;

use c_source::inspect_c_source;
use malbolge as _;

#[test]
fn guest_output_requires_exact_function_like_code_token() {
    let declaration =
        inspect_c_source(b"void __malbolge_output_byte(unsigned int value);");
    assert!(declaration.guest_output());

    for source in [
        b"// __malbolge_output_byte(1)\nint main(void){return 0;}".as_slice(),
        b"/* __malbolge_output_byte(1) */ int main(void){return 0;}",
        b"const char *x = \"__malbolge_output_byte(1)\";",
        b"int __malbolge_output_byte_suffix;",
        b"int __malbolge_output_byte;",
    ] {
        assert!(!inspect_c_source(source).guest_output());
    }
}

#[test]
fn comments_between_identifier_and_call_are_admitted() {
    let source =
        b"void __malbolge_output_byte/* compiler intrinsic */(unsigned);";
    assert!(inspect_c_source(source).guest_output());
}

#[test]
fn translation_phase_line_splicing_precedes_marker_recognition() {
    let source = b"void __malbolge_\\\noutput_byte(unsigned int value);";
    assert!(inspect_c_source(source).guest_output());
    let continued_comment =
        b"// ignored \\\n__malbolge_output_byte(1)\nint main(void){return 0;}";
    assert!(!inspect_c_source(continued_comment).guest_output());
}

#[test]
fn doom_adapter_requires_both_exact_function_like_markers() {
    let complete = inspect_c_source(
        b"void DoomHost_GuestMemoryRegion(void);\n"
            .iter()
            .chain(b"void DoomHost_VideoInitialize(void);")
            .copied()
            .collect::<Vec<_>>()
            .as_slice(),
    );
    assert!(complete.doom_host());

    let partial = inspect_c_source(b"void DoomHost_GuestMemoryRegion(void);");
    assert!(!partial.doom_host());
}
