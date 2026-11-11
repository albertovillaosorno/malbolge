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
//   - A digest-bound research-only echo macro and independent source checks.
// - Must-Not:
//   - Claim a VM-resident interpreter or authenticate an untrusted source.
// - Allows:
//   - Inputs: canonical ternary programs and a selected profile.
//   - Outputs: exact digest-bound candidate and verified direct expansion.
//   - Side effects: bounded in-memory allocation only.
// - Split-When:
//   - A guest decoder or executable artifact publisher is implemented.
// - Merge-When:
//   - A verified product bytecode backend owns this candidate format.
// - Summary:
//   - Measures the missing canonical-source digest cost of the CEB1 pilot.
// - Description:
//   - Rejects equal-length provenance/IR swaps using a domain-separated hash.
// - Usage:
//   - Used only by compact_guest_bytecode_strategy research tests.
// - Defaults:
//   - The caller supplies trusted original ternary bytes and a profile.
//
//! Research-only `CEB2` binding for a proposed echo-run macro.
//!
//! This is **not** executable guest bytecode, source authentication, or an
//! independent proof of a producer's truthfulness. A caller still supplies a
//! trusted canonical ternary program and target-profile descriptor. The digest
//! rejects mismatched *bytes* after admission, not malicious matching claims.

use malbolge::ProfileDescriptor;

use crate::strategy::bridge::layout::LinearLayout;
use crate::strategy::bridge::ternary::{
    TernaryProgram, TernaryProgramCodecError, canonical_ternary_bytes,
};
use crate::strategy::{EchoMacroError, admit_echo_macro, encode_echo_macro};

/// The 6-byte structural descriptor plus a 32-byte SHA-256 binding.
pub const BOUND_ECHO_MACRO_BYTES: usize = 38;
const MAGIC: [u8; 4] = *b"CEB2";
const DOMAIN: &[u8] = b"CEB2-ternary-profile-v1\0";

/// Rejections for the source-bound research candidate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum BoundEchoError {
    /// Canonical ternary source failed independent binary serialization.
    Canonical(TernaryProgramCodecError),
    /// The original source cannot be represented by the CEB1 echo model.
    Echo(EchoMacroError),
    /// Encoded CEB2 version, shape, or count is not admitted.
    InvalidCandidate,
    /// SHA-256 fingerprint of source and selected profile does not match.
    SourceMismatch,
    /// Digest framing or input length exceeds a representable SHA-256 domain.
    Unrepresentable,
}

fn source_digest(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<[u8; 32], BoundEchoError> {
    let canonical = canonical_ternary_bytes(program).map_err(BoundEchoError::Canonical)?;
    let profile_bytes = profile.fingerprint().as_bytes();
    // An explicit separator follows a fixed-format profile fingerprint. The
    // canonical ternary wire already length-frames every variable text field.
    let size = DOMAIN
        .len()
        .checked_add(profile_bytes.len())
        .and_then(|value| value.checked_add(1))
        .and_then(|value| value.checked_add(canonical.len()))
        .ok_or(BoundEchoError::Unrepresentable)?;
    let mut input = Vec::with_capacity(size);
    input.extend_from_slice(DOMAIN);
    input.extend_from_slice(profile_bytes);
    input.push(0);
    input.extend_from_slice(&canonical);
    sha256(&input).ok_or(BoundEchoError::Unrepresentable)
}

/// Encodes a structurally checked six-byte macro with a canonical-byte digest.
///
/// The hash includes the selected profile *fingerprint*, not merely its ID,
/// followed by the exact canonical ternary bytes. A caller must independently
/// trust those inputs; this is a byte-binding, not a certificate of provenance.
///
/// # Errors
///
/// Rejects unsupported effect shapes, invalid canonical source, or unboundable
/// sizes without emitting partially valid envelopes.
pub fn encode_bound_echo_macro(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
) -> Result<[u8; BOUND_ECHO_MACRO_BYTES], BoundEchoError> {
    let echo = encode_echo_macro(program, profile).map_err(BoundEchoError::Echo)?;
    let digest = source_digest(program, profile)?;
    let mut envelope = [0u8; BOUND_ECHO_MACRO_BYTES];
    envelope[..4].copy_from_slice(&MAGIC);
    envelope[4..6].copy_from_slice(&echo[4..6]);
    envelope[6..].copy_from_slice(&digest);
    Ok(envelope)
}

/// Checks an entire `CEB2` envelope before independently admitting direct code.
///
/// A digest mismatch never falls back to source-blind `CEB1` admission, even if
/// the source has the same operation count and would produce identical guest
/// output. Actual execution still uses the **direct** VM, not bytecode.
///
/// # Errors
///
/// Rejects version, size, count, profile, source and layout mismatches.
pub fn admit_bound_echo_macro(
    program: &TernaryProgram,
    profile: &'static ProfileDescriptor,
    candidate: &[u8],
) -> Result<LinearLayout, BoundEchoError> {
    let [b'C', b'E', b'B', b'2', lo, hi, digest @ ..] = candidate else {
        return Err(BoundEchoError::InvalidCandidate);
    };
    if digest.len() != 32 {
        return Err(BoundEchoError::InvalidCandidate);
    }
    let structural = [b'C', b'E', b'B', b'1', *lo, *hi];
    // Validate the source and operation count *before* any digest allocation.
    let layout = admit_echo_macro(program, profile, &structural).map_err(BoundEchoError::Echo)?;
    if source_digest(program, profile)?.as_slice() != digest {
        return Err(BoundEchoError::SourceMismatch);
    }
    Ok(layout)
}

/// Maximum optimistic missing-runtime cells for a strictly shorter envelope.
///
/// One `CEB2` byte is unrealistically charged as only one Malbolge memory cell.
/// This is a research upper bound without executable guest decoder costs.
#[must_use]
pub const fn maximum_bound_runtime_cells(direct_cells: usize) -> Option<usize> {
    direct_cells.checked_sub(BOUND_ECHO_MACRO_BYTES + 1)
}

// Self-contained no-dependency SHA-256 for this research format. A product
// compiler should instead use its centrally governed cryptographic primitive.
#[expect(clippy::indexing_slicing, reason = "fixed SHA-256 word schedules")]
#[expect(
    clippy::arithmetic_side_effects,
    reason = "fixed SHA-256 block indexing"
)]
#[expect(
    clippy::many_single_char_names,
    reason = "standard SHA-256 state names"
)]
#[expect(clippy::min_ident_chars, reason = "standard SHA-256 state names")]
#[expect(clippy::cognitive_complexity, reason = "normative SHA-256 rounds")]
#[expect(clippy::too_many_lines, reason = "fixed SHA-256 schedule and rounds")]
#[expect(clippy::tuple_array_conversions, reason = "explicit SHA state slots")]
#[expect(
    clippy::integer_division_remainder_used,
    reason = "SHA-256 block padding"
)]
fn sha256(data: &[u8]) -> Option<[u8; 32]> {
    const ROUND_CONSTANTS: [u32; 64] = [
        0x428a_2f98,
        0x7137_4491,
        0xb5c0_fbcf,
        0xe9b5_dba5,
        0x3956_c25b,
        0x59f1_11f1,
        0x923f_82a4,
        0xab1c_5ed5,
        0xd807_aa98,
        0x1283_5b01,
        0x2431_85be,
        0x550c_7dc3,
        0x72be_5d74,
        0x80de_b1fe,
        0x9bdc_06a7,
        0xc19b_f174,
        0xe49b_69c1,
        0xefbe_4786,
        0x0fc1_9dc6,
        0x240c_a1cc,
        0x2de9_2c6f,
        0x4a74_84aa,
        0x5cb0_a9dc,
        0x76f9_88da,
        0x983e_5152,
        0xa831_c66d,
        0xb003_27c8,
        0xbf59_7fc7,
        0xc6e0_0bf3,
        0xd5a7_9147,
        0x06ca_6351,
        0x1429_2967,
        0x27b7_0a85,
        0x2e1b_2138,
        0x4d2c_6dfc,
        0x5338_0d13,
        0x650a_7354,
        0x766a_0abb,
        0x81c2_c92e,
        0x9272_2c85,
        0xa2bf_e8a1,
        0xa81a_664b,
        0xc24b_8b70,
        0xc76c_51a3,
        0xd192_e819,
        0xd699_0624,
        0xf40e_3585,
        0x106a_a070,
        0x19a4_c116,
        0x1e37_6c08,
        0x2748_774c,
        0x34b0_bcb5,
        0x391c_0cb3,
        0x4ed8_aa4a,
        0x5b9c_ca4f,
        0x682e_6ff3,
        0x748f_82ee,
        0x78a5_636f,
        0x84c8_7814,
        0x8cc7_0208,
        0x90be_fffa,
        0xa450_6ceb,
        0xbef9_a3f7,
        0xc671_78f2,
    ];
    let bit_len = u64::try_from(data.len()).ok()?.checked_mul(8)?;
    let mut padded = Vec::with_capacity(data.len().checked_add(72)?);
    padded.extend_from_slice(data);
    padded.push(0x80);
    while padded.len() % 64 != 56 {
        padded.push(0);
    }
    padded.extend_from_slice(&bit_len.to_be_bytes());
    let mut state = [
        0x6a09_e667u32,
        0xbb67_ae85,
        0x3c6e_f372,
        0xa54f_f53a,
        0x510e_527f,
        0x9b05_688c,
        0x1f83_d9ab,
        0x5be0_cd19,
    ];
    for block in padded.as_chunks::<64>().0 {
        let mut words = [0u32; 64];
        for (slot, word) in words[..16].iter_mut().enumerate() {
            let begin = slot * 4;
            *word = u32::from_be_bytes(block.get(begin..begin + 4)?.try_into().ok()?);
        }
        for index in 16..64 {
            let small0 = words[index - 15].rotate_right(7)
                ^ words[index - 15].rotate_right(18)
                ^ (words[index - 15] >> 3u32);
            let small1 = words[index - 2].rotate_right(17)
                ^ words[index - 2].rotate_right(19)
                ^ (words[index - 2] >> 10u32);
            words[index] = words[index - 16]
                .wrapping_add(small0)
                .wrapping_add(words[index - 7])
                .wrapping_add(small1);
        }
        let (mut a, mut b, mut c, mut d, mut e, mut f, mut g, mut h) = (
            state[0], state[1], state[2], state[3], state[4], state[5], state[6], state[7],
        );
        for (word, constant) in words.into_iter().zip(ROUND_CONSTANTS) {
            let sum1 = e.rotate_right(6) ^ e.rotate_right(11) ^ e.rotate_right(25);
            let choose = (e & f) ^ (!e & g);
            let temp1 = h
                .wrapping_add(sum1)
                .wrapping_add(choose)
                .wrapping_add(constant)
                .wrapping_add(word);
            let sum0 = a.rotate_right(2) ^ a.rotate_right(13) ^ a.rotate_right(22);
            let majority = (a & b) ^ (a & c) ^ (b & c);
            let temp2 = sum0.wrapping_add(majority);
            h = g;
            g = f;
            f = e;
            e = d.wrapping_add(temp1);
            d = c;
            c = b;
            b = a;
            a = temp1.wrapping_add(temp2);
        }
        for (entry, new) in state.iter_mut().zip([a, b, c, d, e, f, g, h]) {
            *entry = entry.wrapping_add(new);
        }
    }
    let mut digest = [0u8; 32];
    for (index, word) in state.into_iter().enumerate() {
        digest[index * 4..index * 4 + 4].copy_from_slice(&word.to_be_bytes());
    }
    Some(digest)
}

#[cfg(test)]
mod tests {
    use super::sha256;

    #[test]
    fn sha256_matches_published_standard_known_answers() {
        // NIST/FIPS canonical SHA-256 empty, short and multi-block vectors.
        for (message, hex) in [
            (
                b"".as_slice(),
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            ),
            (
                b"abc".as_slice(),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            ),
            (
                b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq".as_slice(),
                "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1",
            ),
        ] {
            let result = sha256(message);
            assert!(result.is_some(), "known-answer input is representable");
            let bytes = result.unwrap_or_default();
            let mut rendered = String::new();
            for value in bytes {
                use std::fmt::Write as _;
                assert!(write!(&mut rendered, "{value:02x}").is_ok());
            }
            assert_eq!(rendered, hex);
        }
    }
}
