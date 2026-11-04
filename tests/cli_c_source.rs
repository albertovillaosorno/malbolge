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
fn guest_input_requires_exact_function_like_code_token() {
    let declaration =
        inspect_c_source(b"unsigned int __malbolge_input_word(void);");
    assert!(declaration.guest_input());

    for source in [
        b"// __malbolge_input_word()\nint main(void){return 0;}".as_slice(),
        b"/* __malbolge_input_word() */ int main(void){return 0;}",
        b"const char *x = \"__malbolge_input_word()\";",
        b"int __malbolge_input_word_suffix;",
        b"int __malbolge_input_word;",
    ] {
        assert!(!inspect_c_source(source).guest_input());
    }
}

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
fn utf8_prefixed_c23_identifiers_cannot_impersonate_host_adapters() {
    // Clang C23 admits these as one identifier, not a standalone ASCII
    // function token. A high-bit prefix must not select native adapters.
    let source = b"int caf\xc3\xa9__malbolge_input_word(void);\n\
        int caf\xc3\xa9__malbolge_output_byte(void);\n\
        void caf\xc3\xa9DoomHost_GuestMemoryRegion(void);\n\
        void caf\xc3\xa9DoomHost_VideoInitialize(void);";
    let adapters = inspect_c_source(source);
    assert!(!adapters.guest_input());
    assert!(!adapters.guest_output());
    assert!(!adapters.doom_host());
}

#[test]
fn standalone_ascii_adapter_calls_follow_utf8_source_tokens() {
    let source = b"int caf\xc3\xa9(void);\n\
        unsigned __malbolge_input_word(void);\n\
        void __malbolge_output_byte(unsigned);\n\
        void DoomHost_GuestMemoryRegion(void);\n\
        void DoomHost_VideoInitialize(void);";
    let adapters = inspect_c_source(source);
    assert!(adapters.guest_input());
    assert!(adapters.guest_output());
    assert!(adapters.doom_host());
}

#[test]
fn preprocessing_numbers_cannot_impersonate_adapter_identifiers() {
    // Translation-phase preprocessing numbers include identifier suffixes,
    // fractional dots and exponent signs. None is a function identifier.
    for prefix in [
        b"1".as_slice(),
        b"0x",
        b"1.",
        b".1",
        b"1e+",
        b"1E-",
        b"0p+",
        b"1'0",
    ] {
        let input_token = [prefix, b"__malbolge_input_word(0);"].concat();
        assert!(
            !inspect_c_source(&input_token).guest_input(),
            "numeric preprocessing token selected guest input: {input_token:?}"
        );
        let output_token = [prefix, b"__malbolge_output_byte(0);"].concat();
        assert!(
            !inspect_c_source(&output_token).guest_output(),
            "numeric suffix selected guest output: {output_token:?}"
        );
    }
    let source = b"2DoomHost_GuestMemoryRegion(0); \
        3DoomHost_VideoInitialize(0);";
    assert!(!inspect_c_source(source).doom_host());
    let spliced = b"1\\\n__malbolge_input_word(0);";
    assert!(!inspect_c_source(spliced).guest_input());
    let separated = b"int value = 1 + __malbolge_input_word();";
    assert!(inspect_c_source(separated).guest_input());
    let distinct = b"unsigned int value = 1; __malbolge_input_word(); \
        __malbolge_output_byte(0);";
    assert!(inspect_c_source(distinct).guest_input());
    assert!(inspect_c_source(distinct).guest_output());
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
