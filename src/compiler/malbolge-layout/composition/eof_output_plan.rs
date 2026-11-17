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
//   - Exhaustive C23 signed-input byte-output arithmetic word admission.
// - Must-Not:
//   - Publish guest code, invent data placement, or host-compute guest stdout.
// - Allows:
//   - Inputs: immutable N15 target profile and two candidate data words.
//   - Outputs: a checked input/crazy/crazy/output algebraic operand plan.
//   - Side effects: none; 257 deterministic scalar transitions per admission.
// - Split-When:
//   - The physical guest linker can place both data operands and prove writes.
// - Merge-When:
//   - Runtime C putchar conversion has a general executable implementation.
// - Summary:
//   - Proof over all bytes and signed EOF, without a false executable claim.

//! Pure input-word transformation needed for correct source-C `putchar`.
//!
//! This verifies *only* the data operands for two consecutive `p` operations
//! after a genuine `InputWord` and before a real `OutputByte`. Both `p` opcodes
//! write their respective data cell. A later layout must allocate and prove
//! those exact unmodified words, data pointer progression and non-aliasing
//! executable code. This module does not emit Malbolge code or C artifacts.

use malbolge::{ProfileDescriptor, current_profile, profile_crazy};

/// One candidate for the current 15-trit C23 signed-EOF conversion.
///
/// This is *not* a graphical source or a pointer placement. The backend must
/// not publish a C guest merely because these constant values are known.
pub const CURRENT_C23_SIGNED_OUTPUT_WORDS: [u32; 2] = [87_844, 2_551];

/// Exact reason an algebraic output conversion proposal could not be proved.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum C23SignedOutputWordPlanError {
    /// The proposed target does not have the exact current N15 semantics.
    UnsupportedProfile,
    /// A data word is outside the target's ternary memory-value range.
    InvalidOperand,
    /// One of the 256 successful `getchar` results was changed by the plan.
    ByteMismatch {
        /// Successful C input byte being transformed.
        byte: u8,
        /// Incorrect output after the two proposed crazy operations.
        actual: u8,
    },
    /// C23 EOF must convert from signed `-1` to byte `0xff` at `putchar`.
    EofMismatch {
        /// Incorrect C23 EOF output after the two crazy operations.
        actual: u8,
    },
}

/// Pure operand values that pass all 257 C23 output conversion cases.
///
/// This is **not** a complete executable guest layout: there are no data
/// addresses, `p` source cells, memory-write proofs or VM execution traces.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct C23SignedOutputWordPlan {
    operands: [u32; 2],
}

impl C23SignedOutputWordPlan {
    /// Returns the exact first and second unmodified data operands.
    #[must_use]
    pub const fn operands(self) -> [u32; 2] {
        self.operands
    }
}

/// Exhaustively admit one two-crazy signed-C output conversion proposal.
///
/// Every successful `getchar` byte must survive the two successive crazy
/// operations modulo 256. The 15-trit EOF word must instead produce `0xff`,
/// as C23 `putchar(-1)` performs the unsigned-char conversion. Neither input
/// nor output is simulated at guest runtime by this check; it only admits a
/// mathematical word recipe for later *guest-side* arithmetic and layout.
///
/// # Errors
///
/// Refuses foreign profiles, invalid operands, any changed byte or EOF value.
pub fn admit_c23_signed_output_word_plan(
    profile: &ProfileDescriptor,
    operands: [u32; 2],
) -> Result<C23SignedOutputWordPlan, C23SignedOutputWordPlanError> {
    if profile != current_profile() {
        return Err(C23SignedOutputWordPlanError::UnsupportedProfile);
    }
    if operands
        .iter()
        .any(|operand| *operand >= profile.word_modulus())
    {
        return Err(C23SignedOutputWordPlanError::InvalidOperand);
    }
    let mapped = |input| {
        let first = profile_crazy(operands[0], input, profile.word_trits());
        let second = profile_crazy(operands[1], first, profile.word_trits());
        (second % 256) as u8
    };
    for byte in u8::MIN..=u8::MAX {
        let actual = mapped(u32::from(byte));
        if actual != byte {
            return Err(C23SignedOutputWordPlanError::ByteMismatch {
                byte,
                actual,
            });
        }
    }
    let actual = mapped(profile.eof_word());
    if actual != u8::MAX {
        return Err(C23SignedOutputWordPlanError::EofMismatch { actual });
    }
    Ok(C23SignedOutputWordPlan { operands })
}
