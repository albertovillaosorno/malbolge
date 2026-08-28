// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Product-side trusted initial-halt adaptive-width verification evidence.
// - Must-Not:
//   - Treat research certificates as authority or execute derived geometry.
// - Allows:
//   - Inputs: canonical profiles, exact source bytes, and candidate widths.
//   - Outputs: exact verified-geometry and fail-closed rejection assertions.
//   - Side effects: test-process allocation only.
// - Split-When:
//   - Split when another product proof family gains independent fixtures.
// - Merge-When:
//   - Merge when adaptive width becomes ordinary profile admission evidence.
// - Summary:
//   - Verifies trusted initial-halt geometry admission and source binding.
// - Description:
//   - Covers the QP positive fixture plus width, source, and theorem failures.
// - Usage:
//   - Composed by `tests/vm.rs` under the normal Cargo integration test target.
// - Defaults:
//   - Any unproved or out-of-range case retains no verified geometry.
//

//! Trusted product-side initial-halt adaptive-width verification fixtures.

use malbolge::{
    ProfileLoadError, ProfileWidthProofKind, ProfileWidthVerificationError,
    current_profile, verify_initial_halt_profile_width,
};

use super::{TestResult, check_equal, normalize_result};

const CANONICAL_WORD_TRITS: u8 = 14;
const MINIMUM_WORD_TRITS: u8 = 10;
const MINIMUM_MEMORY_WORDS: u32 = 59_049;
const MINIMUM_MEMORY_WORDS_USIZE: usize = 59_049;
const QP: &[u8] = b"QP";

#[test]
fn initial_halt_verifier_binds_profile_source_and_geometry() -> TestResult {
    let current = current_profile();
    let verified = normalize_result(verify_initial_halt_profile_width(
        current,
        QP,
        MINIMUM_WORD_TRITS,
    ))?;
    check_equal(&verified.profile(), &current, "canonical profile binding")?;
    check_equal(&verified.source(), &QP, "exact source binding")?;
    check_equal(
        &verified.proof_kind(),
        &ProfileWidthProofKind::InitialHalt,
        "proof family",
    )?;
    check_equal(
        &verified.word_trits(),
        &MINIMUM_WORD_TRITS,
        "derived word width",
    )?;
    check_equal(
        &verified.memory_words(),
        &MINIMUM_MEMORY_WORDS,
        "derived memory words",
    )?;
    check_equal(
        &verified.word_modulus(),
        &MINIMUM_MEMORY_WORDS,
        "derived modulus",
    )?;
    check_equal(
        &verified.eof_word(),
        &(MINIMUM_MEMORY_WORDS - 1),
        "derived EOF",
    )
}

#[test]
fn initial_halt_verifier_preserves_raw_source_identity() -> TestResult {
    let source = b" \tQP\n";
    let verified = normalize_result(verify_initial_halt_profile_width(
        current_profile(),
        source,
        MINIMUM_WORD_TRITS,
    ))?;
    check_equal(&verified.source(), &source.as_slice(), "raw source bytes")
}

#[test]
fn initial_halt_verifier_rejects_unreviewed_widths() -> TestResult {
    for requested in [MINIMUM_WORD_TRITS - 1, CANONICAL_WORD_TRITS + 1] {
        let Err(error) =
            verify_initial_halt_profile_width(current_profile(), QP, requested)
        else {
            return Err(format!("unreviewed width {requested} was accepted"));
        };
        check_equal(
            &error,
            &ProfileWidthVerificationError::WidthOutOfRange {
                profile_word_trits: CANONICAL_WORD_TRITS,
                requested,
            },
            "width rejection",
        )?;
    }
    Ok(())
}

#[test]
fn initial_halt_verifier_reuses_exact_profile_source_admission() -> TestResult {
    let invalid = [0x01, b'P'];
    let Err(error) = verify_initial_halt_profile_width(
        current_profile(),
        &invalid,
        MINIMUM_WORD_TRITS,
    ) else {
        return Err(String::from("invalid source byte was accepted"));
    };
    check_equal(
        &error,
        &ProfileWidthVerificationError::Source(
            ProfileLoadError::InvalidSourceByte { offset: 0, byte: 0x01 },
        ),
        "source admission rejection",
    )
}

#[test]
fn initial_halt_verifier_rejects_other_valid_source_families() -> TestResult {
    let Err(error) = verify_initial_halt_profile_width(
        current_profile(),
        b"DP",
        MINIMUM_WORD_TRITS,
    ) else {
        return Err(String::from("non-initial-halt source was accepted"));
    };
    check_equal(
        &error,
        &ProfileWidthVerificationError::InitialInstructionNotHalt {
            decoded: b'o',
        },
        "proof-family rejection",
    )
}

#[test]
fn derived_capacity_precedes_later_source_validation() -> TestResult {
    let oversized = vec![b'Q'; MINIMUM_MEMORY_WORDS_USIZE.saturating_add(1)];
    let Err(error) = verify_initial_halt_profile_width(
        current_profile(),
        &oversized,
        MINIMUM_WORD_TRITS,
    ) else {
        return Err(String::from("source beyond derived memory was accepted"));
    };
    check_equal(
        &error,
        &ProfileWidthVerificationError::Source(ProfileLoadError::SourceTooLong),
        "derived capacity rejection",
    )
}
