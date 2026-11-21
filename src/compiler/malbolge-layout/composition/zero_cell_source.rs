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
//   - Genuine source-loaded N15 zero synthesis through two guest crazy writes.
// - Must-Not:
//   - Treat one zero word as adjacent C32 zero or assume unknown entry A=0.
// - Allows:
//   - Inputs: initial zero-accumulator N15 and a finite 94-phase source tail.
//   - Outputs: graphical code, exact loader seeds and final zero data address.
//   - Side effects: none; normative VM validates source execution separately.
// - Split-When:
//   - General executable C32 zero initialization subsumes this first word.
// - Merge-When:
//   - The source-C literal linker owns placement and guest initialization.
// - Summary:
//   - Emits a real p;p store of zero absent from the virgin graphical loader.

//! A bounded first step toward a physically written C32 zero initializer.
//!
//! Every fully graphical N15 source begins with A=0. A single `p` cannot
//! produce a zero trit from a zero accumulator, but a second `p` can. This
//! source proves one *written* 15-trit zero; it does not provide the adjacent
//! high word required for a canonical C32 zero local, nor a general block
//! entry with an unknown accumulator.

use std::iter::repeat_n;

use malbolge::{ProfileDescriptor, current_profile, profile_crazy};

use super::{LinearOpcode, unique_graphical_cell, unwritten_loader_word};

const PREFIX_BOUND: usize = 94;

/// Failure to emit the bounded one-word N15 source-zero write.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ZeroCellSourceError {
    /// This fixed graphical grammar has no loader-admitted zero write.
    NoLoadableZero,
    /// No 15-trit modern profile word can be inferred for this profile.
    UnsupportedProfile,
}

/// Exact source-backed two-write plan for a zero result at the second cell.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ZeroCellSource {
    /// First source-loaded `p` data address; the next cell receives zero.
    pub first_data_address: u32,
    /// Initial source-loader first `p` operand.
    pub first_initial_word: u32,
    /// First `p` result, independently consumed by the next `p`.
    pub first_written_word: u32,
    /// Original loader word at the second write location.
    pub second_initial_word: u32,
    /// Graphical N15 source including one unreachable loader tail cell.
    pub source: Vec<u8>,
    /// Guest memory address whose second `p` write produces actual zero.
    pub zero_data_address: u32,
    /// Exact zero-initializing `p` instruction position.
    pub zero_store_code_address: u32,
}

/// Emit a source whose second real `p` writes exactly zero from initial A=0.
///
/// Enumerates at most 94 no-op prefixes and at most 94 graphical tail bytes
/// for `o*;j;p;p;v;tail`. The original `j` code byte chooses the first data
/// address, and both untouched operands must come from the actual six-phase
/// source loader. No initial data word is zero or host-provided. The first
/// matching source is deterministic by prefix then tail order.
///
/// This is a one-word building block, **not** a finished C32 zero initializer,
/// a general entry-state-independent constant, or a dynamic checksum linker.
///
/// # Errors
///
/// Rejects historical profiles and a missing loadable physical zero writer.
#[expect(
    clippy::excessive_nesting,
    clippy::too_many_lines,
    reason = "finite graphical prefix and original loader seed search"
)]
pub fn build_zero_cell_source(
    profile: &ProfileDescriptor,
) -> Result<ZeroCellSource, ZeroCellSourceError> {
    use ZeroCellSourceError::{NoLoadableZero, UnsupportedProfile};
    if profile != current_profile() {
        return Err(UnsupportedProfile);
    }
    let memory_words = usize::try_from(profile.memory_words())
        .map_err(|_error| NoLoadableZero)?;
    for prefix in 0..PREFIX_BOUND {
        let mut source = Vec::with_capacity(prefix.saturating_add(5));
        for opcode in repeat_n(LinearOpcode::NoOperation, prefix).chain([
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::CrazyData,
            LinearOpcode::Halt,
        ]) {
            source.push(
                unique_graphical_cell(profile, opcode, source.len())
                    .map_err(|_error| NoLoadableZero)?,
            );
        }
        let Some(&jump_byte) = source.get(prefix) else {
            return Err(NoLoadableZero);
        };
        let first_data_address = usize::from(jump_byte).saturating_add(1);
        if first_data_address <= source.len().saturating_add(1)
            || first_data_address.saturating_add(1) >= memory_words
        {
            continue;
        }
        for tail in 33..=126u8 {
            if unique_graphical_cell(
                profile,
                LinearOpcode::SkippedDataByte { byte: u32::from(tail) },
                source.len(),
            ) != Ok(tail)
            {
                continue;
            }
            source.push(tail);
            let first_seed =
                unwritten_loader_word(&source, first_data_address, profile)
                    .map_err(|_error| NoLoadableZero)?;
            let second_seed = unwritten_loader_word(
                &source,
                first_data_address.saturating_add(1),
                profile,
            )
            .map_err(|_error| NoLoadableZero)?;
            let first_result =
                profile_crazy(first_seed, 0, profile.word_trits());
            let second_result =
                profile_crazy(second_seed, first_result, profile.word_trits());
            if second_result == 0 {
                let word = |value: usize| {
                    u32::try_from(value).map_err(|_error| NoLoadableZero)
                };
                return Ok(ZeroCellSource {
                    first_data_address: word(first_data_address)?,
                    first_initial_word: first_seed,
                    first_written_word: first_result,
                    second_initial_word: second_seed,
                    source,
                    zero_data_address: word(
                        first_data_address.saturating_add(1),
                    )?,
                    zero_store_code_address: word(prefix.saturating_add(2))?,
                });
            }
            _ = source.pop();
        }
    }
    Err(NoLoadableZero)
}
