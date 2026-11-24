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
//   - Finite, position-sensitive placement of a linear source-loadable leaf
//     behind an indirect guest code-pointer operand.
// - Must-Not:
//   - Assume a guest i is reached, that its D selects this operand, or that
//     preceding self-modification preserves the leaf or pointer value.
// - Allows:
//   - Inputs: already-admitted source, pointer-cell position, open code range,
//     protected cells and a terminal I/O/no-op instruction sequence.
//   - Outputs: a deterministic graphical candidate and exact landing address.
//   - Side effects: owned allocation only; no VM or host I/O.
// - Split-When:
//   - Source-locked CFG placement links arbitrary branches and phi pads.
// - Merge-When:
//   - General physical code relocation proves source and dynamic entry state.
// - Summary:
//   - Prevents indirect continuation bytes from violating source admission.

//! A small, explicitly pre-link *candidate* for a guest indirect continuation.
//!
//! Malbolge's `i` reads a word through D and resumes at word+1, but the
//! pointer word is itself graphical source and must decode to a legal opcode
//! at *its own* source position. Merely choosing the desired target is not
//! sufficient. All original and resulting code cells are admitted here.
//! Guest execution, read provenance, pointer preservation, code encryption
//! and the original C23 semantics remain independent verification obligations.

use malbolge::{
    ProfileDescriptor, current_profile, decode_profile_instruction,
};

use super::admit_c23_probe_graphical_source;

const MAX_SOURCE_CELLS: usize = 4096;
const MAX_SUFFIX_CELLS: usize = 32;
const LOADABLE_OPCODES: &[u8] = b"ji*p</ov";

/// Why a finite indirect source suffix cannot be placed as requested.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IndirectSourceSuffixError {
    /// The source is malformed or exceeds this bounded candidate study.
    InvalidSource,
    /// The pointer site, landing window or protected positions are invalid.
    InvalidPlacement,
    /// Only a bounded straight-line I/O/no-op leaf ending in a halt is
    /// admitted.
    InvalidSuffix,
    /// An instruction in the requested leaf lacks graphical positional code.
    MissingGraphicalEncoding,
    /// Every open landing site needs a pointer byte that fails source
    /// admission.
    NoSourceLoadablePointer,
    /// The geometry depends on the canonical current N15 decoder and loader.
    UnsupportedProfile,
}

/// A graphical candidate; **not** evidence that any guest `i` reaches it.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IndirectSourceSuffixPlan {
    /// Position an actual `i` must select after incrementing its operand.
    pub landing_address: u32,
    /// Source-valid byte at the promised pointer cell, not a guest write.
    pub pointer_word: u8,
    /// Fully graphical source with the pointer cell and leaf re-encoded.
    pub source: Vec<u8>,
}

/// Place one finite, fallthrough guest leaf behind a graphical `i` operand.
///
/// The returned candidate changes only `pointer_cell` and the chosen suffix
/// window. All `protected` cells must stay unchanged; the caller must list
/// any dynamically read/written source cells and all already-reached code.
/// `landing_from..=landing_through` is a finite, nonempty code window.
/// Each leaf may contain `o`, `/` or `<`, followed by exactly one final `v`.
/// The first admissible landing address is chosen, reproducibly. The caller
/// must **separately** prove the real guest's D points to the pointer cell at
/// a reached `i`, no intervening write changes it, and the leaf was not
/// previously encrypted or overwritten.
///
/// # Errors
///
/// Refuses malformed source, unsatisfiable geometry, an invalid leaf, an
/// unsupported profile or an unencodable pointer/leaf. Never publishes code.
#[expect(
    clippy::arithmetic_side_effects,
    clippy::indexing_slicing,
    clippy::too_many_arguments,
    clippy::too_many_lines,
    reason = "bounded checked geometry precedes all source reads and writes"
)]
pub fn plan_source_loaded_indirect_suffix(
    profile: &ProfileDescriptor,
    source: &[u8],
    pointer_cell: usize,
    landing_from: usize,
    landing_through: usize,
    suffix: &[u8],
    protected: &[usize],
) -> Result<IndirectSourceSuffixPlan, IndirectSourceSuffixError> {
    use IndirectSourceSuffixError::{
        InvalidPlacement, InvalidSource, InvalidSuffix,
        MissingGraphicalEncoding, NoSourceLoadablePointer, UnsupportedProfile,
    };
    if profile != current_profile() {
        return Err(UnsupportedProfile);
    }
    if !(2..=MAX_SOURCE_CELLS).contains(&source.len())
        || admit_c23_probe_graphical_source(source).is_err()
    {
        return Err(InvalidSource);
    }
    if suffix.is_empty()
        || suffix.len() > MAX_SUFFIX_CELLS
        || suffix.last() != Some(&b'v')
        || !suffix[..suffix.len() - 1]
            .iter()
            .all(|opcode| matches!(opcode, b'o' | b'/' | b'<'))
    {
        return Err(InvalidSuffix);
    }
    if pointer_cell >= source.len()
        || landing_from == 0
        || landing_from <= pointer_cell
        || landing_through < landing_from
        || landing_through >= source.len()
        || protected.len() > MAX_SOURCE_CELLS
        || protected.iter().any(|position| {
            *position >= source.len() || *position == pointer_cell
        })
    {
        return Err(InvalidPlacement);
    }
    let max_start = source
        .len()
        .checked_sub(suffix.len())
        .ok_or(InvalidPlacement)?;
    if landing_from > max_start {
        return Err(InvalidPlacement);
    }
    for landing in landing_from..=landing_through.min(max_start) {
        let possible_word = u8::try_from(landing - 1)
            .ok()
            .filter(|word| (33..=126).contains(word));
        let Some(pointer_word) = possible_word else {
            continue;
        };
        let pointer_opcode = decode_profile_instruction(
            u32::from(pointer_word),
            u32::try_from(pointer_cell).map_err(|_error| InvalidPlacement)?,
        );
        if !pointer_opcode.is_some_and(|op| LOADABLE_OPCODES.contains(&op)) {
            continue;
        }
        if (landing..landing + suffix.len())
            .any(|position| protected.contains(&position))
        {
            continue;
        }
        let mut patched = source.to_vec();
        patched[pointer_cell] = pointer_word;
        let mut encodable = true;
        for (offset, opcode) in suffix.iter().copied().enumerate() {
            let position = landing + offset;
            let Some(graphical) = (33..=126u8).find(|byte| {
                decode_profile_instruction(
                    u32::from(*byte),
                    u32::try_from(position).unwrap_or(u32::MAX),
                ) == Some(opcode)
            }) else {
                encodable = false;
                break;
            };
            patched[position] = graphical;
        }
        if !encodable {
            return Err(MissingGraphicalEncoding);
        }
        if admit_c23_probe_graphical_source(&patched).is_err() {
            return Err(InvalidSource);
        }
        return Ok(IndirectSourceSuffixPlan {
            landing_address: u32::try_from(landing)
                .map_err(|_error| InvalidPlacement)?,
            pointer_word,
            source: patched,
        });
    }
    Err(NoSourceLoadablePointer)
}
