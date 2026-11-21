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
//   - Exhaustive signed C23 EOF discrimination for two crazy data operands.
// - Must-Not:
//   - Publish code, position operand cells, or assert a working guest branch.
// - Allows:
//   - Inputs: exact current N15 profile, two data words and branch targets.
//   - Outputs: a checked all-byte/EOF algebraic target-word plan.
//   - Side effects: none; 257 bounded scalar transitions per admission.
// - Split-When:
//   - Physical layout verifies input-dependent data writes and jumps.
// - Merge-When:
//   - Executable C23 EOF control implements the full verified operation.
// - Summary:
//   - Proves a necessary data-word discriminator, not runtime guest control.

//! Exact pre-layout data-word discriminator for C's signed EOF sentinel.
//!
//! Two mathematical `p` operations can map every successful byte to one
//! identical word and EOF to a different word. The actual machine requires
//! placed operands, verified writes, a data-pointer revisit and an `i` at a
//! reachable code cell before either word can control a jump. None of those
//! physical operations are provided by this module.

use malbolge::{ProfileDescriptor, current_profile, profile_crazy};

/// A verified candidate for a future runtime C23 `getchar() != EOF` branch.
///
/// Both data operands and output words are *mathematical* constants, not
/// code-cell addresses assigned by the linker. The future `i` would read the
/// output word and continue at that word plus one.
pub const CURRENT_C23_EOF_CONTROL_WORDS: [u32; 2] = [14_348_906, 486];
/// Proposed `i` operand words for successful input and true EOF respectively.
///
/// These select hypothetical code positions 244 and 487, not existing guest
/// code. Any actual jump must separately prove both destinations are valid.
pub const CURRENT_C23_EOF_TARGET_WORDS: [u32; 2] = [243, 486];
/// Two-crazy candidate after the **physical Iy C23 converter** has already
/// stored the exact successful byte or encoded EOF=62,207 at M96.
///
/// Its first data operand has trit five=2, so an actual N15 linker must
/// synthesize that word before execution. Its trit six=1 distinguishes
/// raw N15 EOF from the converted C23 word; the two representations must
/// not be substituted. Both values are data-only.
pub const CURRENT_IY_CONVERTED_EOF_CONTROL_WORDS: [u32; 2] = [14_348_097, 80];
/// Hypothetical `i` operands for Iy-converted byte and EOF respectively.
/// They imply code positions 81 and 810; neither landing pad is generated.
pub const CURRENT_IY_CONVERTED_EOF_TARGET_WORDS: [u32; 2] = [80, 809];

/// Why a proposed mathematical EOF control-word plan was rejected.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum C23EofControlWordError {
    /// A successful `getchar()` byte would select the wrong branch word.
    ByteMismatch {
        /// Byte whose proposed guest control word is wrong.
        byte: u8,
        /// Actual result of both scalar crazy operations.
        actual: u32,
    },
    /// The signed EOF sentinel would select the wrong branch word.
    EofMismatch {
        /// Actual result of both scalar crazy operations at EOF.
        actual: u32,
    },
    /// Different C paths must not alias the same jump operand.
    IndistinguishableTargets,
    /// One proposed crazy operand is outside the target memory-word domain.
    InvalidOperand,
    /// A target cannot name a valid post-increment profile code address.
    InvalidTarget,
    /// Only the canonical modern 15-trit profile has the assumed sentinel.
    UnsupportedProfile,
}

/// A 257-case-proved *data-only* candidate, with no executable guest code.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct C23EofControlWordPlan {
    operands: [u32; 2],
    targets: [u32; 2],
}

impl C23EofControlWordPlan {
    /// Hypothetical code addresses if a later `i` reads either final word.
    ///
    /// This is purely the VM jump's increment rule; no control flow, memory
    /// placement or source encoding has been admitted.
    #[must_use]
    pub const fn next_code_addresses(self) -> [u32; 2] {
        [
            self.targets[0].saturating_add(1),
            self.targets[1].saturating_add(1),
        ]
    }

    /// Proposed successive `p` data operands, in execution order.
    #[must_use]
    pub const fn operands(self) -> [u32; 2] {
        self.operands
    }

    /// Necessary initial-memory write obligations for the two operand words.
    ///
    /// Every graphical source byte is below `3^5 = 243`, so its fifth trit
    /// (zero-based) is zero. For that trit, the loader recurrence starting
    /// with `(0, 0)` alternates `(1, 0)` and `(0, 1)`; it never produces 2.
    /// An operand whose fifth trit is 2 therefore **must** be synthesized
    /// by a real guest data write before a `p` can read it. A `false` flag
    /// does NOT prove that the operand is otherwise loadable or reachable.
    /// This is a necessary condition, not physical placement or a guest.
    #[must_use]
    #[expect(
        clippy::integer_division_remainder_used,
        reason = "one exact base-three digit of an already-admitted N15 word"
    )]
    pub const fn mandatory_runtime_operand_writes(self) -> [bool; 2] {
        [
            (self.operands[0] / 243) % 3 == 2,
            (self.operands[1] / 243) % 3 == 2,
        ]
    }

    /// Required final `p` accumulator words: byte then EOF.
    #[must_use]
    pub const fn targets(self) -> [u32; 2] {
        self.targets
    }
}

/// Admit a mathematical two-crazy signed-input branch discriminator.
///
/// Each successful byte 0..255 must map to `targets[0]` and the *distinct*
/// N15 EOF word must map to `targets[1]`. The resulting exact values are
/// potential operands of a later input-dependent `i`, **not** a physically
/// executable jump. This checker never writes the source, changes the VM,
/// tests only selected samples, or treats the host as the guest.
///
/// # Errors
///
/// Refuses the wrong profile, out-of-range words, indistinguishable targets,
/// or the first wrong byte/EOF transition.
fn admit_eof_word_plan(
    profile: &ProfileDescriptor,
    operands: [u32; 2],
    targets: [u32; 2],
    input_word: impl Fn(u32) -> u32,
) -> Result<C23EofControlWordPlan, C23EofControlWordError> {
    if profile != current_profile() {
        return Err(C23EofControlWordError::UnsupportedProfile);
    }
    if operands
        .iter()
        .any(|operand| *operand >= profile.word_modulus())
    {
        return Err(C23EofControlWordError::InvalidOperand);
    }
    if targets
        .iter()
        .any(|target| *target >= profile.word_modulus().saturating_sub(1))
    {
        return Err(C23EofControlWordError::InvalidTarget);
    }
    if targets[0] == targets[1] {
        return Err(C23EofControlWordError::IndistinguishableTargets);
    }
    let mapped = |word| {
        let intermediate =
            profile_crazy(operands[0], input_word(word), profile.word_trits());
        profile_crazy(operands[1], intermediate, profile.word_trits())
    };
    for byte in u8::MIN..=u8::MAX {
        let actual = mapped(u32::from(byte));
        if actual != targets[0] {
            return Err(C23EofControlWordError::ByteMismatch { byte, actual });
        }
    }
    let actual = mapped(profile.eof_word());
    if actual != targets[1] {
        return Err(C23EofControlWordError::EofMismatch { actual });
    }
    Ok(C23EofControlWordPlan { operands, targets })
}

/// Admit a raw-N15-input two-crazy EOF discriminator, without guest code.
///
/// # Errors
///
/// Rejects wrong profiles, invalid operand/target words, or any mismatched
/// byte/EOF scalar transition.
pub fn admit_c23_eof_control_word_plan(
    profile: &ProfileDescriptor,
    operands: [u32; 2],
    targets: [u32; 2],
) -> Result<C23EofControlWordPlan, C23EofControlWordError> {
    admit_eof_word_plan(profile, operands, targets, |raw| raw)
}

/// Admit two mathematical EOF-control `p` operands **after** Iy conversion.
///
/// The 91-cell Iy guest converter physically executes `p` at C77/C78,
/// leaving successful bytes as exact words 0..255 and true EOF as M96=62,207.
/// The input mapping here independently recomputes that known conversion;
/// no `p`, pointer motion, branch, landing pad or source-C result is linked.
/// This is a different operation from using raw N15 EOF=14,348,906.
///
/// # Errors
///
/// Refuses unsupported profiles, impossible operands or target addresses,
/// and any byte/EOF mapping that fails the 257-case exact scalar oracle.
pub fn admit_c23_iy_converted_eof_control_word_plan(
    profile: &ProfileDescriptor,
    operands: [u32; 2],
    targets: [u32; 2],
) -> Result<C23EofControlWordPlan, C23EofControlWordError> {
    admit_eof_word_plan(profile, operands, targets, |raw| {
        profile_crazy(
            121,
            profile_crazy(7_138_732, raw, profile.word_trits()),
            profile.word_trits(),
        )
    })
}
