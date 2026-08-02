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
//   - Deterministic valid-source generation, replay identity, and shrinking.
// - Must-Not:
//   - Decide VM correctness or use ambient/random host entropy.
// - Allows:
//   - Inputs: fixed seed/ordinal plus public classic decode admission.
//   - Outputs: reproducible source/input/budget cases and shrink candidates.
//   - Side effects: test-process memory only.
// - Split-When:
//   - Split when another generator family needs different admission semantics.
// - Merge-When:
//   - Merge when one verifier owns identical replay/shrink identity.
// - Summary:
//   - Generates replayable valid classic inputs and deterministic smaller
//   - cases.
// - Description:
//   - Source bytes are valid by construction at every loaded code position.
// - Usage:
//   - Consumed by deterministic differential property tests.
// - Defaults:
//   - No nondeterministic RNG; seed and ordinal fully identify each case.
//

//! Deterministic VM fuzz cases with exact replay and shrink identity.

use std::iter::repeat_with;

use malbolge::{Word, decode_instruction};

const ALLOWED_INSTRUCTIONS: &[u8; 8] = b"ji*p</vo";
const DEFAULT_SEED: u64 = 0x5eed_cafe_2026_0727;
const MAX_BUDGET: u8 = 32;
const MAX_INPUT: u8 = 8;
const MAX_SOURCE_EXTRA: u8 = 31;
const MIN_SOURCE: usize = 2;
const SHRINK_FLOOR_BUDGET: usize = 1;

/// One deterministic valid-source fuzz case with exact replay identity.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FuzzCase {
    /// Maximum semantic steps requested by the differential property.
    pub budget: usize,
    /// Deterministic byte input supplied to both runtimes.
    pub input: Vec<u8>,
    /// Case ordinal combined with the seed to derive this case.
    pub ordinal: u32,
    /// Root deterministic seed used to derive this case.
    pub seed: u64,
    /// Position-valid classic Malbolge source bytes.
    pub source: Vec<u8>,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Generator(u64);

impl Generator {
    const fn new(seed: u64) -> Self {
        Self(seed)
    }

    fn next_byte(&mut self) -> u8 {
        let mut value = self.0;
        value ^= value << 13u32;
        value ^= value >> 7u32;
        value ^= value << 17u32;
        self.0 = value;
        value.to_le_bytes().first().copied().unwrap_or(0)
    }
}

fn admitted(byte: u8, position: usize) -> bool {
    let Ok(pointer_raw) = u16::try_from(position) else {
        return false;
    };
    let Ok(pointer) = Word::new(pointer_raw) else {
        return false;
    };
    let decoded = decode_instruction(Word::from_byte(byte), pointer);
    decoded
        .is_some_and(|instruction| ALLOWED_INSTRUCTIONS.contains(&instruction))
}

fn choose_valid_byte(position: usize, selector: u8) -> Result<u8, String> {
    let candidates = (33u8..=126)
        .filter(|byte| admitted(*byte, position))
        .collect::<Vec<_>>();
    if candidates.is_empty() {
        return Err(format!("no admitted source byte at position {position}"));
    }
    let index = usize::from(selector).rem_euclid(candidates.len());
    candidates
        .get(index)
        .copied()
        .ok_or_else(|| String::from("valid-source selector escaped candidates"))
}

fn derived_seed(seed: u64, ordinal: u32) -> u64 {
    seed ^ u64::from(ordinal).wrapping_mul(0x9e37_79b9_7f4a_7c15)
}

/// Generates one valid deterministic fuzz case from replay identity.
///
/// # Errors
///
/// Returns an error only if a loaded position unexpectedly has no admitted
/// graphical source byte or a deterministic selector escapes its candidate set.
pub fn generate_case(seed: u64, ordinal: u32) -> Result<FuzzCase, String> {
    let mut generator = Generator::new(derived_seed(seed, ordinal));
    let source_extra = generator.next_byte().rem_euclid(MAX_SOURCE_EXTRA);
    let source_len = MIN_SOURCE.saturating_add(usize::from(source_extra));
    let input_len = usize::from(generator.next_byte().rem_euclid(MAX_INPUT));
    let budget = usize::from(
        generator
            .next_byte()
            .rem_euclid(MAX_BUDGET)
            .saturating_add(1),
    );
    let mut source = Vec::with_capacity(source_len);
    for position in 0..source_len {
        source.push(choose_valid_byte(position, generator.next_byte())?);
    }
    let input = repeat_with(|| generator.next_byte())
        .take(input_len)
        .collect::<Vec<_>>();
    Ok(FuzzCase {
        budget,
        input,
        ordinal,
        seed,
        source,
    })
}

/// Returns the fixed repository seed used by the default differential corpus.
#[must_use]
pub const fn default_seed() -> u64 {
    DEFAULT_SEED
}

/// Returns deterministic nonexpanding candidates for failure minimization.
#[must_use]
pub fn shrink_candidates(case: &FuzzCase) -> Vec<FuzzCase> {
    let mut candidates = Vec::new();
    if case.source.len() > MIN_SOURCE {
        let reduced_len = case.source.len().div_ceil(2).max(MIN_SOURCE);
        let mut reduced = case.clone();
        reduced.source.truncate(reduced_len);
        candidates.push(reduced);
    }
    if !case.input.is_empty() {
        let mut reduced = case.clone();
        reduced.input.truncate(case.input.len().div_ceil(2));
        candidates.push(reduced);
    }
    if case.budget > SHRINK_FLOOR_BUDGET {
        let mut reduced = case.clone();
        reduced.budget = case.budget.div_ceil(2).max(SHRINK_FLOOR_BUDGET);
        candidates.push(reduced);
    }
    candidates
}

#[test]
fn replay_identity_reconstructs_identical_case() -> Result<(), String> {
    let first = generate_case(DEFAULT_SEED, 17)?;
    let replay = generate_case(first.seed, first.ordinal)?;
    if first == replay {
        Ok(())
    } else {
        Err(String::from("seed/ordinal replay changed generated case"))
    }
}

#[test]
fn shrink_sequence_is_deterministic_and_nonexpanding() -> Result<(), String> {
    let case = generate_case(DEFAULT_SEED, 9)?;
    let first = shrink_candidates(&case);
    let second = shrink_candidates(&case);
    if first != second {
        return Err(String::from("deterministic shrink sequence changed"));
    }
    for candidate in first {
        if candidate.source.len() > case.source.len()
            || candidate.input.len() > case.input.len()
            || candidate.budget > case.budget
        {
            return Err(String::from("shrink candidate expanded fuzz case"));
        }
    }
    Ok(())
}
