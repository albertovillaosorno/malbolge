// File:
//   - annotated.rs
// Path:
//   - tests/vm/annotated.rs
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
//   - Annotated-source canonicalization, formatting, source-map, and VM
//     evidence.
// - Must-Not:
//   - Redefine raw loader semantics or rely on compiler source-map machinery.
// - Allows:
//   - Inputs: explicit annotated fixtures and canonical VM source.
//   - Outputs: byte-exact canonicalization and differential execution evidence.
//   - Side effects: test-local allocation only.
// - Split-When:
//   - Split when compiler/decompiler structural annotations gain independent
//     tests.
// - Merge-When:
//   - Merge when all source frontend behavior has one integration-test owner.
// - Summary:
//   - Proves annotated presentation is semantically inert and hash-safe.
// - Description:
//   - Exercises comments, line endings, mapping, wrapping, and VM equivalence.
// - Usage:
//   - Composed by `tests/vm.rs`.
// - Defaults:
//   - Bare hash remains code; only line-start hash plus space/tab is a comment.
//
// Related documents:
// - docs/technical/tooling/annotated-malbolge-source-format.md
// - vm/src/annotated.rs
//
// Large file:
//   - false

//! Annotated Malbolge source presentation and semantic-inertness evidence.

use malbolge::{
    AnnotatedLoadError, AnnotatedSourceError, ExecutionMachine, ExecutionMode,
    Machine, ProfileMachine, canonicalize_annotated_source, current_profile,
    format_annotated_source,
};

use crate::{TestResult, check_equal, normalize_result};

const CANONICAL_ROUNDTRIP: &[u8] = b"#ctO##/\\?";
const ROUNDTRIP_SOURCE: &[u8] = b"ctO";

#[test]
fn annotated_comment_marker_preserves_all_hash_code_forms() -> TestResult {
    check_canonical(b"#", b"#", "bare hash")?;
    check_canonical(b"#X", b"#X", "hash prefix")?;
    check_canonical(b"#\n", b"#", "hash before newline")?;
    check_canonical(b"# \nA", b"A", "space comment")?;
    check_canonical(b"\t#\tcomment\r\nA", b"A", "tab comment")?;
    check_canonical(
        b"A # comment\nB",
        b"A#commentB",
        "inline hash remains code",
    )
}

#[test]
fn annotated_comments_are_line_ending_independent() -> TestResult {
    for source in [
        b"# comment\nctO".as_slice(),
        b"# comment\r\nctO".as_slice(),
        b"# comment\rctO".as_slice(),
    ] {
        check_canonical(
            source,
            ROUNDTRIP_SOURCE,
            "line ending canonicalization",
        )?;
    }
    Ok(())
}

#[test]
fn annotated_formatter_roundtrips_hash_heavy_canonical_source() -> TestResult {
    for width in [1usize, 2, 3, 8, 64] {
        let formatted = normalize_result(format_annotated_source(
            CANONICAL_ROUNDTRIP,
            width,
        ))?;
        let canonical =
            normalize_result(canonicalize_annotated_source(&formatted))?;
        check_equal(
            canonical.bytes(),
            CANONICAL_ROUNDTRIP,
            "formatter canonical roundtrip",
        )?;
    }
    Ok(())
}

#[test]
fn annotated_source_map_tracks_original_loaded_positions() -> TestResult {
    let source = b"# header\r\nc \r\n\t# block\r\ntO";
    let canonical = normalize_result(canonicalize_annotated_source(source))?;
    check_equal(canonical.bytes(), ROUNDTRIP_SOURCE, "source-map bytes")?;
    let observed = canonical
        .locations()
        .iter()
        .map(|location| (location.offset(), location.line(), location.column()))
        .collect::<Vec<_>>();
    let expected = vec![(10usize, 2usize, 1usize), (24, 4, 1), (25, 4, 2)];
    check_equal(&observed, &expected, "source-map locations")
}

#[test]
fn annotated_invalid_presentation_fails_closed() -> TestResult {
    let invalid_source = canonicalize_annotated_source(&[b'c', 0x80]);
    check_equal(
        &invalid_source,
        &Err(AnnotatedSourceError::InvalidPresentationByte {
            offset: 1,
            byte: 0x80,
        }),
        "invalid presentation byte",
    )?;
    let invalid_comment = canonicalize_annotated_source(&[b'#', b' ', 0x80]);
    check_equal(
        &invalid_comment,
        &Err(AnnotatedSourceError::InvalidCommentByte {
            offset: 2,
            byte: 0x80,
        }),
        "invalid comment byte",
    )?;
    check_equal(
        &format_annotated_source(ROUNDTRIP_SOURCE, 0),
        &Err(AnnotatedSourceError::ZeroWrapWidth),
        "zero wrap width",
    )
}

#[test]
fn annotated_vm_execution_matches_canonical_classic_and_current() -> TestResult
{
    let annotated = b"# input/output roundtrip\r\nc\n# output\r\nt\nO";
    check_classic_execution(annotated)?;
    check_execution_facade(annotated)?;
    check_profile_execution(annotated)
}

fn check_classic_execution(annotated: &[u8]) -> TestResult {
    let input = vec![b'A'];
    let mut canonical = normalize_result(Machine::from_source(
        ROUNDTRIP_SOURCE,
        input.clone(),
    ))?;
    let mut presented =
        normalize_result(Machine::from_annotated_source(annotated, input))?;
    let canonical_outcome = normalize_result(canonical.run(8))?;
    let presented_outcome = normalize_result(presented.run(8))?;
    check_equal(
        &presented_outcome,
        &canonical_outcome,
        "classic annotated outcome",
    )?;
    check_equal(
        presented.output(),
        canonical.output(),
        "classic annotated output",
    )?;
    check_equal(
        &presented.registers(),
        &canonical.registers(),
        "classic annotated registers",
    )
}

fn check_execution_facade(annotated: &[u8]) -> TestResult {
    let mut canonical = normalize_result(ExecutionMachine::from_source(
        ROUNDTRIP_SOURCE,
        vec![b'A'],
        ExecutionMode::Specification,
    ))?;
    let mut presented =
        normalize_result(ExecutionMachine::from_annotated_source(
            annotated,
            vec![b'A'],
            ExecutionMode::Specification,
        ))?;
    let canonical_outcome = normalize_result(canonical.run(8))?;
    let presented_outcome = normalize_result(presented.run(8))?;
    check_equal(
        &presented_outcome,
        &canonical_outcome,
        "facade annotated outcome",
    )?;
    check_equal(
        presented.output(),
        canonical.output(),
        "facade annotated output",
    )
}

fn check_profile_execution(annotated: &[u8]) -> TestResult {
    let profile = current_profile();
    let input = vec![b'A'];
    let mut canonical = normalize_result(ProfileMachine::from_source(
        profile,
        ROUNDTRIP_SOURCE,
        input.clone(),
    ))?;
    let mut presented = normalize_result(
        ProfileMachine::from_annotated_source(profile, annotated, input),
    )?;
    let canonical_outcome = normalize_result(canonical.run(8))?;
    let presented_outcome = normalize_result(presented.run(8))?;
    check_equal(
        &presented_outcome,
        &canonical_outcome,
        "profile annotated outcome",
    )?;
    check_equal(
        presented.output(),
        canonical.output(),
        "profile annotated output",
    )?;
    check_equal(
        &presented.registers(),
        &canonical.registers(),
        "profile annotated registers",
    )
}

#[test]
fn annotated_constructor_preserves_loader_rejection_boundary() -> TestResult {
    let observed = Machine::from_annotated_source(b"# comment\nQ", Vec::new());
    match observed {
        Err(AnnotatedLoadError::Load(_error)) => Ok(()),
        Err(AnnotatedLoadError::Annotated(error)) => Err(format!(
            "annotated preprocessing rejected loader-bound fixture: {error}"
        )),
        Ok(_machine) => {
            Err(String::from("invalid canonical source was admitted"))
        },
    }
}

fn check_canonical(
    source: &[u8],
    expected: &[u8],
    context: &str,
) -> TestResult {
    let canonical = normalize_result(canonicalize_annotated_source(source))?;
    check_equal(canonical.bytes(), expected, context)
}
