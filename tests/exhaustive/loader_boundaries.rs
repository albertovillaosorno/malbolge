// File:
//   - loader_boundaries.rs
// Path:
//   - tests/exhaustive/loader_boundaries.rs
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
//   - Exhaustive finite-domain classic loader admission/rejection boundaries.
// - Must-Not:
//   - Reimplement memory fill or weaken position-dependent decode admission.
// - Allows:
//   - Inputs: public load/decode APIs and the finite byte/decode-phase domains.
//   - Outputs: exact typed loader acceptance/rejection evidence.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when scalable-profile loader domains need separate exhaustive
//   - proof.
// - Merge-When:
//   - Merge when another suite owns identical source-admission boundaries.
// - Summary:
//   - Exhausts invalid bytes and all 94 decode phases around loader admission.
// - Description:
//   - Mutates one valid 94-word source at every phase to an invalid
//   - instruction.
// - Usage:
//   - Runs under the deterministic property-verification Cargo target.
// - Defaults:
//   - Failure reports exact byte offset or loaded position.
//
// Related documents:
// - docs/technical/verification/property-fuzz-and-exhaustive-testing.md
// - docs/technical/specification/malbolge-1998.md
//
// Large file:
//   - false
//

//! Exhaustive classic loader byte and positional-decode admission checks.

use malbolge::{LoadError, MEMORY_WORDS, Word, decode_instruction, load};

const ALLOWED_INSTRUCTIONS: &[u8; 8] = b"ji*p</vo";
const DECODE_PHASES: usize = 94;

fn pointer(position: usize) -> Result<Word, String> {
    let raw = u16::try_from(position)
        .map_err(|error| format!("pointer conversion failed: {error}"))?;
    Word::new(raw)
        .map_err(|error| format!("pointer construction failed: {error}"))
}

fn is_admitted(byte: u8, position: usize) -> Result<bool, String> {
    let decoded = decode_instruction(Word::from_byte(byte), pointer(position)?);
    Ok(decoded.is_some_and(|value| ALLOWED_INSTRUCTIONS.contains(&value)))
}

fn byte_with_admission(position: usize, admitted: bool) -> Result<u8, String> {
    for byte in 33u8..=126 {
        if is_admitted(byte, position)? == admitted {
            return Ok(byte);
        }
    }
    Err(format!(
        "no graphical byte with admitted={admitted} at position {position}"
    ))
}

fn valid_phase_source() -> Result<Vec<u8>, String> {
    (0..DECODE_PHASES)
        .map(|position| byte_with_admission(position, true))
        .collect()
}

#[test]
fn every_non_whitespace_non_graphical_byte_is_rejected() -> Result<(), String> {
    let prefix = byte_with_admission(0, true)?;
    let suffix = byte_with_admission(1, true)?;
    for raw in 0u16..=u16::from(u8::MAX) {
        let byte = u8::try_from(raw)
            .map_err(|error| format!("byte conversion failed: {error}"))?;
        if byte.is_ascii_whitespace() || (33..=126).contains(&byte) {
            continue;
        }
        let observed = load(&[prefix, byte, suffix]);
        let expected = Err(LoadError::InvalidSourceByte { offset: 1, byte });
        if observed != expected {
            return Err(format!("invalid byte={byte}: observed={observed:?}"));
        }
    }
    Ok(())
}

#[test]
fn every_decode_phase_has_valid_and_invalid_instruction_bytes()
-> Result<(), String> {
    let source = valid_phase_source()?;
    let _memory =
        load(&source).map_err(|error| format!("valid source: {error}"))?;
    for position in 0..DECODE_PHASES {
        let invalid = byte_with_admission(position, false)?;
        let mut mutated = source.clone();
        let Some(slot) = mutated.get_mut(position) else {
            return Err(String::from("phase mutation escaped valid source"));
        };
        *slot = invalid;
        let observed = load(&mutated);
        let expected =
            Err(LoadError::InvalidInstruction { position, byte: invalid });
        if observed != expected {
            return Err(format!(
                "invalid pos={position} byte={invalid}: {observed:?}"
            ));
        }
    }
    Ok(())
}

#[test]
fn recurrence_and_capacity_boundaries_fail_closed() -> Result<(), String> {
    for source in [Vec::new(), b" \t\r\n".to_vec()] {
        let observed = load(&source);
        if observed != Err(LoadError::InsufficientRecurrenceBase) {
            return Err(format!(
                "empty recurrence base mismatch: {observed:?}"
            ));
        }
    }
    let one_word = vec![byte_with_admission(0, true)?];
    let one_word_observed = load(&one_word);
    if one_word_observed != Err(LoadError::InsufficientRecurrenceBase) {
        return Err(format!(
            "one-word recurrence base mismatch: {one_word_observed:?}"
        ));
    }
    let oversized = vec![b'!'; MEMORY_WORDS.saturating_add(1)];
    let oversized_observed = load(&oversized);
    if oversized_observed != Err(LoadError::SourceTooLong) {
        return Err(format!(
            "oversized source mismatch: {oversized_observed:?}"
        ));
    }
    Ok(())
}
