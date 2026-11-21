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
//   - Genuine source-loaded N15 zero synthesis, including adjacent guest cells.
// - Must-Not:
//   - Treat a physical zero pair as a source-linked C local or unknown-entry A.
// - Allows:
//   - Inputs: initial zero-accumulator N15 and a finite 94-phase source tail.
//   - Outputs: graphical code, exact loader seeds and final zero data address.
//   - Side effects: none; normative VM validates source execution separately.
// - Split-When:
//   - General executable C32 zero initialization subsumes this first word.
// - Merge-When:
//   - The source-C literal linker owns placement and guest initialization.
// - Summary:
//   - Emits one and two-cell zero plans with actual source-loaded guest writes.

//! Source-loaded physical zero constructors for one or two guest words.
//!
//! Every fully graphical N15 source begins with A=0. A single `p` cannot
//! produce a zero trit from a zero accumulator, but a second `p` can. This
//! first source proves one *written* 15-trit zero. A separate bounded
//! source executes data-pointer reentry and writes both adjacent C32-zero
//! cells, without proving a general source-C initializer or arbitrary A.

use std::iter::repeat_n;

use malbolge::{ProfileDescriptor, current_profile, profile_crazy};

use super::{LinearOpcode, unique_graphical_cell, unwritten_loader_word};

const C32_ZERO_CODE_CELLS: usize = 60;
const C32_ZERO_INPUT_CODE_CELLS: usize = 31;
const LOADER_TAIL_CELLS: usize = 2;

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

/// Physical zero write whose result does not depend on the entry accumulator.
///
/// The initial `*` overwrites `A` from a genuine loader word before either
/// `p` runs. The second of three data writes therefore stores zero regardless
/// of the caller's incoming accumulator, provided C and D start at zero.
/// Neither the following data cell nor a complete C32 local is zero.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AccumulatorIndependentZeroCellSource {
    /// First data address after the source-code `j` relocation.
    pub first_data_address: u32,
    /// Original loader words at the consecutive `*;p;p` write destinations.
    pub initial_words: [u32; 3],
    /// A real `/` before the accumulator-clearing rotate, if requested.
    pub input_code_address: Option<u32>,
    /// Exact source including two untouched graphical loader-tail cells.
    pub source: Vec<u8>,
    /// Values genuinely written by `*;p;p`, including zero at index one.
    pub written_words: [u32; 3],
    /// Exact physical address of the zero-producing `p` instruction.
    pub zero_store_code_address: u32,
}

/// Two adjacent, physically written zero words in a source-loaded N15 guest.
///
/// The first data relocation prepares an accumulator and a scratch zero. The
/// second relocation executes three crazy operations, the middle of which
/// writes the high zero word. A third genuine data jump revisits the first
/// word and overwrites it with zero, preserving the adjacent high word.
/// The complete source is initially graphical, and all writes avoid code.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AdjacentC32ZeroSource {
    /// Optional input read strictly after both zero words have been written.
    pub input_code_address: Option<u32>,
    /// Loader-provided operands for three following writes and return jump.
    pub relocated_initial_words: [u32; 4],
    /// Original source-code jump destination before the two scratch writes.
    pub scratch_data_address: u32,
    /// Loader-provided operands for the two scratch writes and first jump.
    pub scratch_initial_words: [u32; 3],
    /// Executable source with unreachable graphical padding and two tail
    /// cells.
    pub source: Vec<u8>,
    /// Second of the two physically zeroed, consecutive 15-trit data cells.
    pub zero_high_address: u32,
    /// First high-word zero write code position before physical reentry.
    pub zero_high_code_address: u32,
    /// First of the two physically zeroed, consecutive 15-trit data cells.
    pub zero_low_address: u32,
    /// Final low-word zero rewrite code position after physical reentry.
    pub zero_low_code_address: u32,
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

/// Search a finite graphical N15 source for an entry-A-independent zero word.
///
/// Enumerates at most 94 reached `o` prefixes, a fixed `j;*;p;p;v`
/// suffix and 94 squared legal graphical loader tails. It never places a
/// synthetic initial data cell or assumes the initial accumulator is zero.
/// The first physical rotation overwrites `A`; the following `p` produces
/// zero at the next data address. The final `p` is a deliberately nonzero
/// adjacent write: this primitive does not initialize a complete C32 zero.
///
/// # Errors
///
/// Rejects noncanonical profiles or an unsatisfied graphical source grammar.
pub fn build_accumulator_independent_zero_cell_source(
    profile: &ProfileDescriptor,
) -> Result<AccumulatorIndependentZeroCellSource, ZeroCellSourceError> {
    find_accumulator_independent_zero_source(profile, false)
}

/// Write one physical zero after a real raw input byte or EOF observation.
///
/// The guest reads input with `/` before the authentic `j;*;p;p;v` writes.
/// The `*` intentionally discards the read value; no source-C `getchar`
/// result, input-dependent branch, or complete C32 local is materialized.
///
/// # Errors
///
/// Rejects unsupported profiles or a missing loader-valid source.
pub fn build_input_then_zero_cell_source(
    profile: &ProfileDescriptor,
) -> Result<AccumulatorIndependentZeroCellSource, ZeroCellSourceError> {
    find_accumulator_independent_zero_source(profile, true)
}

#[expect(
    clippy::excessive_nesting,
    clippy::too_many_lines,
    reason = "physical source search with optional real input"
)]
fn find_accumulator_independent_zero_source(
    profile: &ProfileDescriptor,
    read_input: bool,
) -> Result<AccumulatorIndependentZeroCellSource, ZeroCellSourceError> {
    use ZeroCellSourceError::{NoLoadableZero, UnsupportedProfile};
    if profile != current_profile() {
        return Err(UnsupportedProfile);
    }
    let memory_words = usize::try_from(profile.memory_words())
        .map_err(|_error| NoLoadableZero)?;
    for prefix in 0..PREFIX_BOUND {
        let mut source = Vec::with_capacity(prefix.saturating_add(7));
        if read_input && prefix == 0 {
            continue;
        }
        for opcode in (0..prefix)
            .map(|position| {
                if read_input && position.saturating_add(1) == prefix {
                    LinearOpcode::InputWord
                } else {
                    LinearOpcode::NoOperation
                }
            })
            .chain([
                LinearOpcode::RelocateDataPointer,
                LinearOpcode::RotateData,
                LinearOpcode::CrazyData,
                LinearOpcode::CrazyData,
                LinearOpcode::Halt,
            ])
        {
            source.push(
                unique_graphical_cell(profile, opcode, source.len())
                    .map_err(|_error| NoLoadableZero)?,
            );
        }
        let Some(&jump_byte) = source.get(prefix) else {
            return Err(NoLoadableZero);
        };
        let first_data_address = usize::from(jump_byte).saturating_add(1);
        if first_data_address <= source.len().saturating_add(2)
            || first_data_address.saturating_add(2) >= memory_words
        {
            continue;
        }
        for first_tail in 33..=126u8 {
            if unique_graphical_cell(
                profile,
                LinearOpcode::SkippedDataByte {
                    byte: u32::from(first_tail),
                },
                source.len(),
            ) != Ok(first_tail)
            {
                continue;
            }
            source.push(first_tail);
            for last_tail in 33..=126u8 {
                if unique_graphical_cell(
                    profile,
                    LinearOpcode::SkippedDataByte {
                        byte: u32::from(last_tail),
                    },
                    source.len(),
                ) != Ok(last_tail)
                {
                    continue;
                }
                source.push(last_tail);
                let mut seeds = [0; 3];
                for (offset, seed) in seeds.iter_mut().enumerate() {
                    *seed = unwritten_loader_word(
                        &source,
                        first_data_address.saturating_add(offset),
                        profile,
                    )
                    .map_err(|_error| NoLoadableZero)?;
                }
                let rotated =
                    malbolge::profile_rotate(seeds[0], profile.word_modulus());
                let zero_candidate =
                    profile_crazy(seeds[1], rotated, profile.word_trits());
                if zero_candidate == 0 {
                    let last = profile_crazy(
                        seeds[2],
                        zero_candidate,
                        profile.word_trits(),
                    );
                    return Ok(AccumulatorIndependentZeroCellSource {
                        first_data_address: u32::try_from(first_data_address)
                            .map_err(|_error| NoLoadableZero)?,
                        initial_words: seeds,
                        input_code_address: read_input
                            .then(|| u32::try_from(prefix.saturating_sub(1)))
                            .transpose()
                            .map_err(|_error| NoLoadableZero)?,
                        source,
                        written_words: [rotated, zero_candidate, last],
                        zero_store_code_address: u32::try_from(
                            prefix.saturating_add(2),
                        )
                        .map_err(|_error| NoLoadableZero)?,
                    });
                }
                _ = source.pop();
            }
            _ = source.pop();
        }
    }
    Err(NoLoadableZero)
}

/// Find a graphical N15 source that *writes* adjacent `[0, 0]` data words.
///
/// Search is bounded to a 62-byte source, 60 valid code/padding cells, two
/// graphical loader-tail cells and at most 94 no-op prefixes. Its exact guest
/// body is `j;p;p;j;p;p;p;j;p;v`. The two words are written in reverse order
/// and the second `j` revisit is mandatory: a direct adjacent crazy chain
/// cannot write a second zero from accumulator zero and virgin loader data.
///
/// This is a source-loaded **initializer primitive**, not a variable address
/// allocator, arbitrary-entry-state operation, C23 signed conversion, guest
/// branch or completion of the original mutable EOF checksum linker.
///
/// # Errors
///
/// Refuses noncurrent profiles or an unrepresentable bounded graphical plan.
pub fn build_adjacent_c32_zero_source(
    profile: &ProfileDescriptor,
) -> Result<AdjacentC32ZeroSource, ZeroCellSourceError> {
    find_adjacent_zero_source(profile, false)
}

/// Create the adjacent `[0, 0]` pair before observing a genuine guest input.
///
/// The reached `/` is after the final low-word zero write and cannot change
/// either initialized cell. No guest input is used to compute the zero pair;
/// the input result remains only in A and is not a source-C C32 local.
///
/// # Errors
///
/// Refuses noncurrent profiles or source/loader layouts outside the bound.
pub fn build_adjacent_c32_zero_then_input_source(
    profile: &ProfileDescriptor,
) -> Result<AdjacentC32ZeroSource, ZeroCellSourceError> {
    find_adjacent_zero_source(profile, true)
}

#[expect(
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    clippy::too_many_lines,
    reason = "two physical write modes and exact loader search"
)]
fn find_adjacent_zero_source(
    profile: &ProfileDescriptor,
    read_input: bool,
) -> Result<AdjacentC32ZeroSource, ZeroCellSourceError> {
    use ZeroCellSourceError::{NoLoadableZero, UnsupportedProfile};
    if profile != current_profile() {
        return Err(UnsupportedProfile);
    }
    let memory_words = usize::try_from(profile.memory_words())
        .map_err(|_error| NoLoadableZero)?;
    let code_cells = if read_input {
        C32_ZERO_INPUT_CODE_CELLS
    } else {
        C32_ZERO_CODE_CELLS
    };
    let source_cells = code_cells.saturating_add(LOADER_TAIL_CELLS);
    let body_cells = if read_input {
        11
    } else {
        10
    };
    for prefix in 0..PREFIX_BOUND {
        if prefix.saturating_add(body_cells) > code_cells {
            break;
        }
        let mut source = Vec::with_capacity(source_cells);
        let physical_body = [
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::CrazyData,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::CrazyData,
            LinearOpcode::CrazyData,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
        ];
        for opcode in repeat_n(LinearOpcode::NoOperation, prefix)
            .chain(physical_body)
            .chain(read_input.then_some(LinearOpcode::InputWord))
            .chain([LinearOpcode::Halt])
        {
            source.push(
                unique_graphical_cell(profile, opcode, source.len())
                    .map_err(|_error| NoLoadableZero)?,
            );
        }
        while source.len() < code_cells {
            source.push(
                unique_graphical_cell(
                    profile,
                    LinearOpcode::NoOperation,
                    source.len(),
                )
                .map_err(|_error| NoLoadableZero)?,
            );
        }
        let Some(&first_jump_byte) = source.get(prefix) else {
            return Err(NoLoadableZero);
        };
        let first_address = usize::from(first_jump_byte).saturating_add(1);
        if first_address <= source_cells.saturating_add(2)
            || first_address.saturating_add(2) >= memory_words
        {
            continue;
        }
        for first_tail in 33..=126u8 {
            if unique_graphical_cell(
                profile,
                LinearOpcode::SkippedDataByte {
                    byte: u32::from(first_tail),
                },
                source.len(),
            ) != Ok(first_tail)
            {
                continue;
            }
            source.push(first_tail);
            for last_tail in 33..=126u8 {
                if unique_graphical_cell(
                    profile,
                    LinearOpcode::SkippedDataByte {
                        byte: u32::from(last_tail),
                    },
                    source.len(),
                ) != Ok(last_tail)
                {
                    continue;
                }
                source.push(last_tail);
                let mut scratch = [0; 3];
                for (offset, slot) in scratch.iter_mut().enumerate() {
                    *slot = unwritten_loader_word(
                        &source,
                        first_address.saturating_add(offset),
                        profile,
                    )
                    .map_err(|_error| NoLoadableZero)?;
                }
                let first_written =
                    profile_crazy(scratch[0], 0, profile.word_trits());
                let scratch_zero = profile_crazy(
                    scratch[1],
                    first_written,
                    profile.word_trits(),
                );
                let relocated_address =
                    usize::try_from(scratch[2].saturating_add(1))
                        .map_err(|_error| NoLoadableZero)?;
                if scratch_zero == 0
                    && relocated_address > source_cells
                    && relocated_address.saturating_add(3) < memory_words
                    && !(first_address..=first_address.saturating_add(2))
                        .contains(&relocated_address)
                    && !(relocated_address
                        ..=relocated_address.saturating_add(3))
                        .contains(&first_address)
                {
                    let mut words = [0; 4];
                    for (offset, slot) in words.iter_mut().enumerate() {
                        *slot = unwritten_loader_word(
                            &source,
                            relocated_address.saturating_add(offset),
                            profile,
                        )
                        .map_err(|_error| NoLoadableZero)?;
                    }
                    let first = profile_crazy(
                        words[0],
                        scratch_zero,
                        profile.word_trits(),
                    );
                    let high =
                        profile_crazy(words[1], first, profile.word_trits());
                    let third =
                        profile_crazy(words[2], high, profile.word_trits());
                    let low = profile_crazy(first, third, profile.word_trits());
                    if high == 0
                        && low == 0
                        && words[3].saturating_add(1)
                            == u32::try_from(relocated_address)
                                .map_err(|_error| NoLoadableZero)?
                        && words[0] != 0
                        && words[1] != 0
                    {
                        let as_word = |value: usize| {
                            u32::try_from(value)
                                .map_err(|_error| NoLoadableZero)
                        };
                        return Ok(AdjacentC32ZeroSource {
                            input_code_address: read_input
                                .then(|| as_word(prefix.saturating_add(9)))
                                .transpose()?,
                            relocated_initial_words: words,
                            scratch_data_address: as_word(first_address)?,
                            scratch_initial_words: scratch,
                            source,
                            zero_high_address: as_word(
                                relocated_address.saturating_add(1),
                            )?,
                            zero_high_code_address: as_word(
                                prefix.saturating_add(5),
                            )?,
                            zero_low_address: as_word(relocated_address)?,
                            zero_low_code_address: as_word(
                                prefix.saturating_add(8),
                            )?,
                        });
                    }
                }
                _ = source.pop();
            }
            _ = source.pop();
        }
    }
    Err(NoLoadableZero)
}
