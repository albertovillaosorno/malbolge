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
//   - Exact physical storage of one successful input byte in N15 memory.
// - Must-Not:
//   - Represent the true EOF sentinel as C23 signed i32 or claim a C loop.
// - Allows:
//   - Inputs: the current profile, bounded graphical prefix/tail phases.
//   - Outputs: source-loaded two-stage crazy identity and data addresses.
//   - Side effects: none; real guest execution is separately verified.
// - Split-When:
//   - General signed input normalization and branching replace this slice.
// - Merge-When:
//   - An executable source-linked guest state writer subsumes the placement.
// - Summary:
//   - Recovers all 256 byte values using two actual guest data writes.
//
//! A source-loadable two-`p` identity, not signed C23 `getchar` lowering.
//!
//! For one ternary digit, crazy with the fixed *data* trit one swaps zero
//! and one while leaving two unchanged. Applying it twice is identity on
//! every 15-trit input word, including the true EOF sentinel. Find two
//! loader-derived all-one operands at independently relocated data sites;
//! both guest `p` instructions must execute and physically write memory.

use std::iter::repeat_n;

use malbolge::{ProfileDescriptor, current_profile};

use super::{LinearOpcode, unique_graphical_cell, unwritten_loader_word};

const CODE_PHASES: usize = 94;
const GRAPHICAL_START: u8 = 33;
const GRAPHICAL_END: u8 = 126;
const IDENTITY_OPERAND: u32 = 7_174_453;

/// Failure to place two source-loaded inverse crazy operations.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ByteExactInputStoreError {
    /// No graphical phase and tail produced both virgin all-one operands.
    NoLoadablePlacement,
    /// This exact physical grammar is defined only for current 15-trit N15.
    UnsupportedProfile,
}

/// Guest program and explicit physical witnesses for one raw input store.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ByteExactInputStoreSource {
    /// Second `p` writes the exact raw word here, independent of the input.
    pub exact_data_address: u32,
    /// Source-loaded all-one operand at the exact destination.
    pub exact_initial_word: u32,
    /// Second reached `p` code site.
    pub exact_store_code_address: u32,
    /// First `p` writes the involuted input here.
    pub first_data_address: u32,
    /// Source-loaded all-one operand at the first address.
    pub first_initial_word: u32,
    /// First reached `p` code site.
    pub first_store_code_address: u32,
    /// First reached `/` source address.
    pub input_code_address: u32,
    /// Graphical physical source, including two unexecuted loader-tail bytes.
    pub source: Vec<u8>,
}

// A three-cell chain uses the virgin word following the first p operand to
// relocate D to an independent second p operand. All reads use loader state.
fn exact_store_address(
    source: &[u8],
    first_address: usize,
    profile: &ProfileDescriptor,
    identity_operand: u32,
) -> Result<Option<usize>, ByteExactInputStoreError> {
    use ByteExactInputStoreError::NoLoadablePlacement;
    let first_seed = unwritten_loader_word(source, first_address, profile)
        .map_err(|_error| NoLoadablePlacement)?;
    if first_seed != identity_operand {
        return Ok(None);
    }
    let pointer_seed =
        unwritten_loader_word(source, first_address.saturating_add(1), profile)
            .map_err(|_error| NoLoadablePlacement)?;
    let exact_address = usize::try_from(pointer_seed)
        .map_err(|_error| NoLoadablePlacement)?
        .saturating_add(1);
    if exact_address <= source.len().saturating_add(2)
        || exact_address >= usize::try_from(profile.memory_words()).unwrap_or(0)
        || exact_address == first_address
    {
        return Ok(None);
    }
    let exact_seed = unwritten_loader_word(source, exact_address, profile)
        .map_err(|_error| NoLoadablePlacement)?;
    Ok((exact_seed == identity_operand).then_some(exact_address))
}

// Two graphical tail cells fix both independent virgin crazy operands.
// A flat Cartesian search avoids nesting the source-encoding conditions.
fn graphical_tail_candidate(
    profile: &ProfileDescriptor,
    prefix_source: &[u8],
    prefix: usize,
    first_address: usize,
) -> Result<Option<ByteExactInputStoreSource>, ByteExactInputStoreError> {
    use ByteExactInputStoreError::NoLoadablePlacement;
    let tail_start = prefix_source.len();
    let pair_bytes = (GRAPHICAL_START..=GRAPHICAL_END).flat_map(|first| {
        (GRAPHICAL_START..=GRAPHICAL_END).map(move |last| (first, last))
    });
    for (first, last) in pair_bytes {
        let first_opcode =
            LinearOpcode::SkippedDataByte { byte: u32::from(first) };
        let last_opcode =
            LinearOpcode::SkippedDataByte { byte: u32::from(last) };
        if unique_graphical_cell(profile, first_opcode, tail_start) != Ok(first)
            || unique_graphical_cell(
                profile,
                last_opcode,
                tail_start.saturating_add(1),
            ) != Ok(last)
        {
            continue;
        }
        let mut source = prefix_source.to_vec();
        source.extend([first, last]);
        let Some(exact_destination) = exact_store_address(
            &source,
            first_address,
            profile,
            IDENTITY_OPERAND,
        )?
        else {
            continue;
        };
        let word = |address: usize| {
            u32::try_from(address).map_err(|_error| NoLoadablePlacement)
        };
        return Ok(Some(ByteExactInputStoreSource {
            exact_data_address: word(exact_destination)?,
            exact_initial_word: IDENTITY_OPERAND,
            exact_store_code_address: word(prefix.saturating_add(4))?,
            first_data_address: word(first_address)?,
            first_initial_word: IDENTITY_OPERAND,
            first_store_code_address: word(prefix.saturating_add(2))?,
            input_code_address: word(prefix)?,
            source,
        }));
    }
    Ok(None)
}

/// Build a real N15 `/;j;p;j;p;v` byte-exact input store.
///
/// Searches 94 prefixes and at most 94 squared tails per prefix, subject to
/// actual positional decoding and virgin source loader memory. The first `j`
/// uses its *own source byte* to relocate D, and the second `j` uses the
/// untouched word after the first store. No VM memory is injected by the host.
///
/// This writes `0..255` exactly as low guest words on successful reads. At
/// EOF it instead writes the N15 sentinel, not the C23 signed 32-bit pair
/// `[4_644_102, 299]`; no C branch, phi or loop is implemented.
///
/// # Errors
///
/// Rejects noncurrent profiles or an exhausted finite placement search.
pub fn build_byte_exact_input_store_source(
    profile: &ProfileDescriptor,
) -> Result<ByteExactInputStoreSource, ByteExactInputStoreError> {
    use ByteExactInputStoreError::{NoLoadablePlacement, UnsupportedProfile};
    if profile != current_profile() {
        return Err(UnsupportedProfile);
    }
    let memory_words = usize::try_from(profile.memory_words())
        .map_err(|_error| NoLoadablePlacement)?;
    let operations = [
        LinearOpcode::InputWord,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::Halt,
    ];
    for prefix in 0..CODE_PHASES {
        let mut source = Vec::with_capacity(
            prefix.saturating_add(operations.len()).saturating_add(2),
        );
        for operation in repeat_n(LinearOpcode::NoOperation, prefix)
            .chain(operations.iter().copied())
        {
            let byte = unique_graphical_cell(profile, operation, source.len())
                .map_err(|_error| NoLoadablePlacement)?;
            source.push(byte);
        }
        let jump_byte = source
            .get(prefix.saturating_add(1))
            .copied()
            .ok_or(NoLoadablePlacement)?;
        let first_address = usize::from(jump_byte).saturating_add(1);
        if first_address <= source.len().saturating_add(2)
            || first_address.saturating_add(1) >= memory_words
        {
            continue;
        }
        if let Some(plan) =
            graphical_tail_candidate(profile, &source, prefix, first_address)?
        {
            return Ok(plan);
        }
    }
    Err(NoLoadablePlacement)
}
