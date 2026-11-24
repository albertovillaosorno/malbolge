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
//   - Genuine source-loaded N15 zero synthesis and adjacent raw-input writes.
// - Must-Not:
//   - Treat raw N15 EOF or physical pairs as signed C23 source locals.
// - Allows:
//   - Inputs: zero-entry N15, real guest input and finite graphical tails.
//   - Outputs: graphical code, loader seeds and physical word addresses.
//   - Side effects: none; normative VM validates source execution separately.
// - Split-When:
//   - General executable C32 zero initialization subsumes this first word.
// - Merge-When:
//   - The source-C literal linker owns placement and guest initialization.
// - Summary:
//   - Emits zero initializers and byte-driven adjacent guest word writes.

//! Source-loaded zero constructors and physical raw-input word pairs.
//!
//! Every fully graphical N15 source begins with A=0. A single `p` cannot
//! produce a zero trit from a zero accumulator, but a second `p` can. This
//! first source proves one *written* 15-trit zero. A separate bounded
//! source executes data-pointer reentry and writes both adjacent C32-zero
//! cells. A separate input-backed pair writes `[byte, 0]` for 256 bytes,
//! but not signed-C23 EOF, general source C state, or arbitrary entry A.

use std::iter::repeat_n;

use malbolge::{
    ProfileDescriptor, current_profile, encrypt_profile_cell, profile_crazy,
};

use super::{LinearOpcode, unique_graphical_cell, unwritten_loader_word};

const C32_ZERO_CODE_CELLS: usize = 60;
const C32_ZERO_INPUT_CODE_CELLS: usize = 31;
const LOADER_TAIL_CELLS: usize = 2;

const PREFIX_BOUND: usize = 94;

/// Failure to emit a bounded, loader-valid N15 physical word plan.
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

/// N15 byte/EOF input written into a real adjacent two-word physical region.
///
/// The low word holds the raw unsigned byte (or unnormalized profile EOF),
/// and the physically initialized high word holds zero. This is **not** the
/// C23 signed `getchar` result on EOF or a linked C source-local frame.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestByteC32PairSource {
    /// Reached first `p` storing an injective encoding at low+2.
    pub encoded_store_code_address: u32,
    /// Reached physical `p` initializing the high word to zero.
    pub high_zero_code_address: u32,
    /// Reached genuine `/` consuming one byte or observing true EOF.
    pub input_code_address: u32,
    /// Reached physical `*` priming the low word with trit-wise ones.
    pub low_prime_code_address: u32,
    /// Reached final `p` writing the actual raw byte into the low word.
    pub low_store_code_address: u32,
    /// Adjacent high physical word, zeroed before the input operation.
    pub pair_high_address: u32,
    /// Lower physical word, storing each successful guest byte exactly.
    pub pair_low_address: u32,
    /// Four virgin loader words in the adjacent destination region.
    pub relocated_initial_words: [u32; 4],
    /// First loader-derived pointer relocation and scratch writes.
    pub scratch_data_address: u32,
    /// Virgin loader words at the three scratch operations.
    pub scratch_initial_words: [u32; 3],
    /// Source code and unreachable padding plus two graphical loader seeds.
    pub source: Vec<u8>,
}

/// Source-loaded raw-byte C32 storage followed by one real guest output.
///
/// The output reads the accumulator after the low-word write, not a C23
/// signed-EOF scalar. A true EOF still emits a byte and does not implement a
/// source-C `getchar`/`putchar` EOF guard.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestByteC32PairEchoSource {
    /// Reached halted-code site after the new output step.
    pub halt_code_address: u32,
    /// Reached genuine output instruction after storing both C32 words.
    pub output_code_address: u32,
    /// The authenticated physical adjacent data plan and executable source.
    pub pair: GuestByteC32PairSource,
}

/// Four real guest reloads of the raw low word followed by output.
///
/// Each three-jump chain reads the high-zero word, the already-encrypted
/// source C1 word, and a virgin loader cell before returning to the low
/// word. Physical rotations update that low word and the accumulator;
/// their output is independent of the incoming accumulator at reload.
/// This is not a native C23 byte echo, signed EOF conversion or C32 frame.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestByteC32PairReloadSource {
    /// Reached halt after four genuine data reload/rotation cycles.
    pub halt_code_address: u32,
    /// Reached output after the fourth accumulator reload.
    pub output_code_address: u32,
    /// Reached physical rotations reading and rewriting the stored low word.
    pub rotation_code_addresses: [u32; 4],
    /// Authenticated source-loader raw-byte pair and executable source.
    pub pair: GuestByteC32PairSource,
}

/// A physical byte/EOF-distinguishing nonlocal ternary state word.
///
/// This guest rotates the previously stored encoded input at low+2, then
/// uses it as A in a genuine crazy write to the original raw low cell.
/// True EOF has a distinct resulting 15-trit value from all 256 bytes,
/// but this is not a signed C23 EOF guard or normalized C32 local.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestByteC32PairEofDistinguishSource {
    /// Reached physical rotation of the original encoded word.
    pub encoded_rotation_code_address: u32,
    /// Reached data write combining the raw and rotated-encoded words.
    pub mixed_store_code_address: u32,
    /// Reached output after the mixed physical store.
    pub output_code_address: u32,
    /// Reached terminating instruction after the output.
    pub halt_code_address: u32,
    /// Authentic loader-backed raw-byte source and physical locations.
    pub pair: GuestByteC32PairSource,
}

/// Real guest EOF-zero predicate and pointer-selected source data lookup.
///
/// Two three-jump returns reuse the written low word. A `p` with both
/// operands equal to the prior nonlocal mixture produces zero **only** for
/// raw N15 EOF among the 257 possible `/` results. A final `j` reads that
/// written predicate and selects D1 for EOF or a high data address for bytes.
/// The selected `*` then makes the output depend on the pointed-to memory.
/// This is an EOF-specific data effect, not a source-C conditional branch,
/// signed C23 local, or a published checksum.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestByteC32PairEofZeroPointerSource {
    /// Reached second physical `p` producing zero only on raw EOF.
    pub zero_store_code_address: u32,
    /// Reached `j` reading the input-dependent predicate from memory.
    pub selected_pointer_code_address: u32,
    /// Reached `*` reading the physically selected data word.
    pub data_rotation_code_address: u32,
    /// Reached real output from the selected data word.
    pub output_code_address: u32,
    /// Reached source halt after the selected data read and output.
    pub halt_code_address: u32,
    /// Original source-loaded byte-pair layout with the new continuation.
    pub pair: GuestByteC32PairSource,
}

/// Source-loaded N15 EOF/byte selector with one output class for every byte.
///
/// The C20 data write is zero only on EOF. C21 rotates the already-zero high
/// word, clearing A without changing that physical cell. C23 returns to the
/// actual predicate word, C24 selects an input-dependent loader address, and
/// C25 `p` combines that selected word with A=0 before the real C26 output.
/// All successful bytes emit 53 and EOF emits 62 in the bounded N15 guest.
/// This is *data-path* classification: it does not branch with `i`, store a
/// signed C23 `getchar`, or link the source checksum to executable code.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestByteC32PairEofClassifySource {
    /// Reached `*` clearing the accumulator from the zero high word.
    pub accumulator_clear_code_address: u32,
    /// Reached `j` selecting EOF or a successful-byte loader address.
    pub selected_pointer_code_address: u32,
    /// Reached `p` writing the selected word and classified accumulator.
    pub classified_store_code_address: u32,
    /// Reached actual output from the classified accumulator.
    pub output_code_address: u32,
    /// Reached physical halt after output.
    pub halt_code_address: u32,
    /// Original N15 physical source and adjacent signed-width storage.
    pub pair: GuestByteC32PairSource,
}

/// A genuine guest full-word EOF flag after source-loaded input writes.
///
/// This continues the physically stored two-class C25 result with one more
/// reached `p`: successful input produces the exact 15-trit zero and true
/// N15 EOF produces the exact 15-trit word 15. An output and halt follow.
/// The flag is not a C23 Boolean, canonical signed EOF, or code-pointer
/// branch, and the original source-C checksum remains unlinked.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct GuestByteC32PairEofFlagSource {
    /// Reached data instruction producing the full-width 0/15 flag.
    pub flag_store_code_address: u32,
    /// Reached instruction emitting that flag as one byte.
    pub output_code_address: u32,
    /// Reached final halt instruction.
    pub halt_code_address: u32,
    /// Real source-loaded raw input pair and its code/data state.
    pub pair: GuestByteC32PairSource,
}

#[derive(Clone, Copy, Eq, PartialEq)]
enum AdjacentPhysicalMode {
    RawBytePair,
    ZeroPair,
    ZeroThenInput,
}

struct PhysicalAdjacentSource {
    encoded_store_code_address: Option<u32>,
    high_address: u32,
    high_code_address: u32,
    input_code_address: Option<u32>,
    low_address: u32,
    low_final_code_address: u32,
    low_first_code_address: u32,
    relocated_initial_words: [u32; 4],
    scratch_data_address: u32,
    scratch_initial_words: [u32; 3],
    source: Vec<u8>,
}

impl From<PhysicalAdjacentSource> for AdjacentC32ZeroSource {
    fn from(found: PhysicalAdjacentSource) -> Self {
        Self {
            input_code_address: found.input_code_address,
            relocated_initial_words: found.relocated_initial_words,
            scratch_data_address: found.scratch_data_address,
            scratch_initial_words: found.scratch_initial_words,
            source: found.source,
            zero_high_address: found.high_address,
            zero_high_code_address: found.high_code_address,
            zero_low_address: found.low_address,
            zero_low_code_address: found.low_final_code_address,
        }
    }
}

impl TryFrom<PhysicalAdjacentSource> for GuestByteC32PairSource {
    type Error = ZeroCellSourceError;

    fn try_from(found: PhysicalAdjacentSource) -> Result<Self, Self::Error> {
        use ZeroCellSourceError::NoLoadableZero;
        // Only RawBytePair may enter this conversion; absent code sites
        // refuse instead of being guessed or replaced by a sentinel.
        Ok(Self {
            encoded_store_code_address: found
                .encoded_store_code_address
                .ok_or(NoLoadableZero)?,
            high_zero_code_address: found.high_code_address,
            input_code_address: found
                .input_code_address
                .ok_or(NoLoadableZero)?,
            low_prime_code_address: found.low_first_code_address,
            low_store_code_address: found.low_final_code_address,
            pair_high_address: found.high_address,
            pair_low_address: found.low_address,
            relocated_initial_words: found.relocated_initial_words,
            scratch_data_address: found.scratch_data_address,
            scratch_initial_words: found.scratch_initial_words,
            source: found.source,
        })
    }
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
    find_physical_adjacent_source(profile, AdjacentPhysicalMode::ZeroPair)
        .map(AdjacentC32ZeroSource::from)
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
    find_physical_adjacent_source(profile, AdjacentPhysicalMode::ZeroThenInput)
        .map(AdjacentC32ZeroSource::from)
}

/// Emit the source-loaded adjacent-zero initializer followed by a real C37
/// N15 input and a C38 halt, preserving the original 62 graphical cells.
///
/// This is a fixed first-two-effect *guest prefix* for the source-C checksum:
/// C14 writes high zero, C17 writes low zero, and C37 performs genuine `/`.
/// C18..C36 are real reached no-ops. The input is not converted to signed
/// C23 or written to SSA state, and there is no source-C branch, phi, loop,
/// or complete checksum artifact. Only source-loader-backed memory is used.
///
/// # Errors
///
/// Refuses unsupported profiles or a missing graphical source encoding.
pub fn build_adjacent_c32_zero_then_c37_input_source(
    profile: &ProfileDescriptor,
) -> Result<AdjacentC32ZeroSource, ZeroCellSourceError> {
    use ZeroCellSourceError::NoLoadableZero;
    let mut candidate = build_adjacent_c32_zero_source(profile)?;
    for (site, operation) in [
        (18usize, LinearOpcode::NoOperation),
        (37usize, LinearOpcode::InputWord),
        (38usize, LinearOpcode::Halt),
    ] {
        let byte = unique_graphical_cell(profile, operation, site)
            .map_err(|_error| NoLoadableZero)?;
        *candidate.source.get_mut(site).ok_or(NoLoadableZero)? = byte;
    }
    candidate.input_code_address = Some(37);
    Ok(candidate)
}

/// Build one real input-driven `[raw_input, 0]` adjacent data pair.
///
/// This graphical N15 source uses three loader-backed `j` reentries and
/// physically writes both pair words. The high word becomes zero before `/`.
/// A `*` primes the low word to the all-ones ternary operand, then `/;p;j;p`
/// encodes and decodes each raw input through an invertible crazy pair.
/// For all 256 successful bytes the pair is an exact C32 `[byte, 0]` value.
/// **EOF is not signed C23 `-1`:** the raw N15 EOF word is kept in the low
/// cell with zero high, so no source-C `getchar` local may yet be published.
/// The contract requires A=C=D=0 at entry and the exact current profile.
///
/// # Errors
///
/// Refuses unsupported profiles or an absent loader-valid graphical layout.
pub fn build_guest_byte_c32_pair_source(
    profile: &ProfileDescriptor,
) -> Result<GuestByteC32PairSource, ZeroCellSourceError> {
    find_physical_adjacent_source(profile, AdjacentPhysicalMode::RawBytePair)
        .and_then(GuestByteC32PairSource::try_from)
}

/// Append a genuine output after both physical input-dependent pair writes.
///
/// This bounded source reuses the exact loader seeds and scratch/data writes
/// of the raw input pair. C13 becomes the profile's output instruction and
/// C14 becomes halt; the final two graphical loader-tail bytes stay unchanged.
/// Successful byte reads are echoed only after storing `[byte, 0]` in guest
/// memory. True EOF is **not** guarded, and emits its raw byte projection.
/// This cannot be published as signed-C23 `getchar`/`putchar` or a checksum.
///
/// # Errors
///
/// Refuses unsupported profile or missing/unencodable 14/15 code sites.
pub fn build_guest_byte_c32_pair_echo_source(
    profile: &ProfileDescriptor,
) -> Result<GuestByteC32PairEchoSource, ZeroCellSourceError> {
    use ZeroCellSourceError::NoLoadableZero;
    let mut pair = build_guest_byte_c32_pair_source(profile)?;
    for (site, operation) in [
        (13usize, LinearOpcode::OutputByte),
        (14usize, LinearOpcode::Halt),
    ] {
        let byte = unique_graphical_cell(profile, operation, site)
            .map_err(|_error| NoLoadableZero)?;
        *pair.source.get_mut(site).ok_or(NoLoadableZero)? = byte;
    }
    Ok(GuestByteC32PairEchoSource {
        halt_code_address: 14,
        output_code_address: 13,
        pair,
    })
}

/// Mix physical raw and rotated-encoded input words, then output a byte.
///
/// After the original byte-pair store, one no-op moves D to the encoded
/// word at low+2. A reached `*` rotates that word and loads the result
/// into A. The untouched loader cell at low+3 then redirects D back to
/// the raw low word. A reached `p` genuinely computes and stores
/// `crazy(raw, rotate(crazy(ones, raw)))`, preserving the adjacent
/// physical zero high word. All 257 input classes give an EOF-distinct
/// 15-trit result, but successful bytes are not preserved and output
/// is not a C23 EOF guard.
///
/// # Errors
///
/// Rejects noncurrent profile, unexpected physical layout or absent code.
pub fn build_guest_byte_c32_pair_eof_distinguish_source(
    profile: &ProfileDescriptor,
) -> Result<GuestByteC32PairEofDistinguishSource, ZeroCellSourceError> {
    use ZeroCellSourceError::NoLoadableZero;
    let mut pair = build_guest_byte_c32_pair_source(profile)?;
    if pair.source.len() != 33
        || pair.pair_high_address != pair.pair_low_address.saturating_add(1)
    {
        return Err(NoLoadableZero);
    }
    // The original C11 already uses low+3 as a virgin source-loader
    // operand to return D to low; C15 reuses this exact jump.
    let return_word = unwritten_loader_word(
        &pair.source,
        usize::try_from(pair.pair_low_address.saturating_add(3))
            .map_err(|_error| NoLoadableZero)?,
        profile,
    )
    .map_err(|_error| NoLoadableZero)?;
    if return_word.saturating_add(1) != pair.pair_low_address {
        return Err(NoLoadableZero);
    }
    for (site, operation) in [
        (13usize, LinearOpcode::NoOperation),
        (14, LinearOpcode::RotateData),
        (15, LinearOpcode::RelocateDataPointer),
        (16, LinearOpcode::CrazyData),
        (17, LinearOpcode::OutputByte),
        (18, LinearOpcode::Halt),
    ] {
        *pair.source.get_mut(site).ok_or(NoLoadableZero)? =
            unique_graphical_cell(profile, operation, site)
                .map_err(|_error| NoLoadableZero)?;
    }
    Ok(GuestByteC32PairEofDistinguishSource {
        encoded_rotation_code_address: 14,
        mixed_store_code_address: 16,
        output_code_address: 17,
        halt_code_address: 18,
        pair,
    })
}

/// Convert the nonlocal byte/EOF word into a physical EOF-zero predicate.
///
/// The first three `j` instructions reenter the existing mixed low word:
/// high zero -> encrypted source C1 -> untouched loader M101 -> low.
/// A real `p` now has equal data and accumulator operands. The exact
/// ternary diagonal maps 0/2 to 1 and 1 to 0, so its result is zero only
/// if the mixed word was the all-ones EOF state. A second return reaches
/// that physically updated low word; a fourth `j` moves D to predicate+1.
/// The subsequent `*` reads **that** selected memory location and `<`
/// emits its rotated low byte. No guest `i` branch or C23 normalization is
/// inferred from the physical data-pointer selection.
///
/// # Errors
///
/// Refuses unsupported or changed source-loader/pointer properties.
pub fn build_guest_byte_c32_pair_eof_zero_pointer_source(
    profile: &ProfileDescriptor,
) -> Result<GuestByteC32PairEofZeroPointerSource, ZeroCellSourceError> {
    use ZeroCellSourceError::NoLoadableZero;
    let mut pair =
        build_guest_byte_c32_pair_eof_distinguish_source(profile)?.pair;
    if pair.source.len() != 33
        || pair.pair_high_address != pair.pair_low_address.saturating_add(1)
        || pair.relocated_initial_words != [36, 7_174_417, 36, 7_174_417]
    {
        return Err(NoLoadableZero);
    }
    let encrypted_c1 = encrypt_profile_cell(u32::from(
        *pair.source.get(1).ok_or(NoLoadableZero)?,
    ))
    .ok_or(NoLoadableZero)?;
    let indirect_address = usize::try_from(encrypted_c1.saturating_add(1))
        .map_err(|_error| NoLoadableZero)?;
    if indirect_address < pair.source.len()
        || unwritten_loader_word(&pair.source, indirect_address, profile)
            .map_err(|_error| NoLoadableZero)?
            .saturating_add(1)
            != pair.pair_low_address
    {
        return Err(NoLoadableZero);
    }
    for (site, operation) in [
        (17usize, LinearOpcode::RelocateDataPointer),
        (18, LinearOpcode::RelocateDataPointer),
        (19, LinearOpcode::RelocateDataPointer),
        (20, LinearOpcode::CrazyData),
        (21, LinearOpcode::RelocateDataPointer),
        (22, LinearOpcode::RelocateDataPointer),
        (23, LinearOpcode::RelocateDataPointer),
        (24, LinearOpcode::RelocateDataPointer),
        (25, LinearOpcode::RotateData),
        (26, LinearOpcode::OutputByte),
        (27, LinearOpcode::Halt),
    ] {
        *pair.source.get_mut(site).ok_or(NoLoadableZero)? =
            unique_graphical_cell(profile, operation, site)
                .map_err(|_error| NoLoadableZero)?;
    }
    Ok(GuestByteC32PairEofZeroPointerSource {
        zero_store_code_address: 20,
        selected_pointer_code_address: 24,
        data_rotation_code_address: 25,
        output_code_address: 26,
        halt_code_address: 27,
        pair,
    })
}

/// Write one of two EOF-dependent guest output classes using physical data.
///
/// This continuation reuses the genuine source-loaded EOF-zero C20 writer.
/// A C21 `*` clears A by rotating the adjacent high-zero word, C22 `o`
/// advances to the unchanged loader return word, C23 `j` returns D to the
/// input-dependent predicate, C24 `j` selects data through that actual word,
/// and C25 `p` physically folds the selected memory word into A. The final
/// C26 `<` emits 53 on every successful input byte and 62 on true EOF.
/// No guest code-pointer branch, source-C conditional or checksum is linked.
///
/// # Errors
///
/// Refuses unsupported profile, changed source-loader state or missing code.
pub fn build_guest_byte_c32_pair_eof_classify_source(
    profile: &ProfileDescriptor,
) -> Result<GuestByteC32PairEofClassifySource, ZeroCellSourceError> {
    use ZeroCellSourceError::NoLoadableZero;
    let mut pair =
        build_guest_byte_c32_pair_eof_zero_pointer_source(profile)?.pair;
    if pair.source.len() != 33
        || pair.pair_high_address != pair.pair_low_address.saturating_add(1)
        || pair.relocated_initial_words != [36, 7_174_417, 36, 7_174_417]
    {
        return Err(NoLoadableZero);
    }
    for (site, operation) in [
        (21usize, LinearOpcode::RotateData),
        (22, LinearOpcode::NoOperation),
        (25, LinearOpcode::CrazyData),
    ] {
        *pair.source.get_mut(site).ok_or(NoLoadableZero)? =
            unique_graphical_cell(profile, operation, site)
                .map_err(|_error| NoLoadableZero)?;
    }
    Ok(GuestByteC32PairEofClassifySource {
        accumulator_clear_code_address: 21,
        selected_pointer_code_address: 24,
        classified_store_code_address: 25,
        output_code_address: 26,
        halt_code_address: 27,
        pair,
    })
}

/// Compute a small full-width EOF flag in the real N15 guest data path.
///
/// The existing C25 `p` gives a uniform full word 7,174,453 for all bytes
/// and a distinct 7,174,462 for EOF, following true physical input and
/// state writes. At C26 the data pointer has already advanced: a second
/// reached `p` reads the selected next word and stores exactly zero for
/// all successful input bytes or exactly 15 for EOF. C27 outputs the flag
/// and C28 halts in 29 normative steps.
///
/// This does not implement source-C `getchar` normalization, branch with
/// guest `i`, or complete checksum control flow.
///
/// # Errors
///
/// Refuses unsupported profiles and changed source-loader geometry.
pub fn build_guest_byte_c32_pair_eof_flag_source(
    profile: &ProfileDescriptor,
) -> Result<GuestByteC32PairEofFlagSource, ZeroCellSourceError> {
    use ZeroCellSourceError::NoLoadableZero;
    let mut pair = build_guest_byte_c32_pair_eof_classify_source(profile)?.pair;
    if pair.source.len() != 33
        || pair.pair_high_address != pair.pair_low_address.saturating_add(1)
        || pair.relocated_initial_words != [36, 7_174_417, 36, 7_174_417]
    {
        return Err(NoLoadableZero);
    }
    for (site, operation) in [
        (26usize, LinearOpcode::CrazyData),
        (27, LinearOpcode::OutputByte),
        (28, LinearOpcode::Halt),
    ] {
        *pair.source.get_mut(site).ok_or(NoLoadableZero)? =
            unique_graphical_cell(profile, operation, site)
                .map_err(|_error| NoLoadableZero)?;
    }
    Ok(GuestByteC32PairEofFlagSource {
        flag_store_code_address: 26,
        output_code_address: 27,
        halt_code_address: 28,
        pair,
    })
}

/// Reload the physically stored low word through four real guest rotations.
///
/// The adjacent high-zero word provides a genuine reentry path: one jump
/// reads the high zero to select D1, the second reads source C1 as it
/// actually exists after its own earlier post-instruction encryption,
/// and the third reads untouched expanded loader M101 to select the low
/// word. Each rotation reads and rewrites that word, replacing the incoming
/// accumulator. Four rounds fit before the source-loader scratch at M41.
///
/// Output is the fourth ternary rotation modulo 256, **not** the original
/// byte. The low word is no longer the raw input and signed EOF is not
/// normalized. This is state-feedback evidence, not C23 publication.
///
/// # Errors
///
/// Rejects unsupported profile, changed loader return or unencodable code.
pub fn build_guest_byte_c32_pair_reload_source(
    profile: &ProfileDescriptor,
) -> Result<GuestByteC32PairReloadSource, ZeroCellSourceError> {
    use ZeroCellSourceError::NoLoadableZero;
    let mut pair = build_guest_byte_c32_pair_source(profile)?;
    // Require the original high-zero gateway and independently validate the
    // loaded pointer chain. Do not assume a revised search has the same tail.
    if pair.pair_high_address != pair.pair_low_address.saturating_add(1)
        || pair.source.len() != 33
    {
        return Err(NoLoadableZero);
    }
    let encrypted_c1 = encrypt_profile_cell(u32::from(
        *pair.source.get(1).ok_or(NoLoadableZero)?,
    ))
    .ok_or(NoLoadableZero)?;
    let destination = usize::try_from(encrypted_c1.saturating_add(1))
        .map_err(|_error| NoLoadableZero)?;
    if destination < pair.source.len() {
        return Err(NoLoadableZero);
    }
    let restored_low =
        unwritten_loader_word(&pair.source, destination, profile)
            .map_err(|_error| NoLoadableZero)?
            .saturating_add(1);
    if restored_low != pair.pair_low_address {
        return Err(NoLoadableZero);
    }
    let mut sites = [0u32; 4];
    for (round, site) in sites.iter_mut().enumerate() {
        for hop in 0..3 {
            let address = 13usize
                .saturating_add(round.saturating_mul(4))
                .saturating_add(hop);
            *pair.source.get_mut(address).ok_or(NoLoadableZero)? =
                unique_graphical_cell(
                    profile,
                    LinearOpcode::RelocateDataPointer,
                    address,
                )
                .map_err(|_error| NoLoadableZero)?;
        }
        let address = 16usize.saturating_add(round.saturating_mul(4));
        *pair.source.get_mut(address).ok_or(NoLoadableZero)? =
            unique_graphical_cell(profile, LinearOpcode::RotateData, address)
                .map_err(|_error| NoLoadableZero)?;
        *site = u32::try_from(address).map_err(|_error| NoLoadableZero)?;
    }
    for (address, operation) in [
        (29usize, LinearOpcode::OutputByte),
        (30usize, LinearOpcode::Halt),
    ] {
        *pair.source.get_mut(address).ok_or(NoLoadableZero)? =
            unique_graphical_cell(profile, operation, address)
                .map_err(|_error| NoLoadableZero)?;
    }
    Ok(GuestByteC32PairReloadSource {
        halt_code_address: 30,
        output_code_address: 29,
        rotation_code_addresses: sites,
        pair,
    })
}

#[expect(
    clippy::cognitive_complexity,
    clippy::excessive_nesting,
    clippy::too_many_lines,
    reason = "three physical write modes and exact bounded loader search"
)]
fn find_physical_adjacent_source(
    profile: &ProfileDescriptor,
    mode: AdjacentPhysicalMode,
) -> Result<PhysicalAdjacentSource, ZeroCellSourceError> {
    use ZeroCellSourceError::{NoLoadableZero, UnsupportedProfile};
    if profile != current_profile() {
        return Err(UnsupportedProfile);
    }
    let memory_words = usize::try_from(profile.memory_words())
        .map_err(|_error| NoLoadableZero)?;
    let code_cells = if mode == AdjacentPhysicalMode::ZeroPair {
        C32_ZERO_CODE_CELLS
    } else {
        C32_ZERO_INPUT_CODE_CELLS
    };
    let source_cells = code_cells.saturating_add(LOADER_TAIL_CELLS);
    // These eight operations create a scratch zero, write a zero high cell,
    // then return to the low word. The suffix selects an authentic physical
    // low-word write, not a simulated C operation.
    let common = [
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::CrazyData,
        LinearOpcode::RelocateDataPointer,
        LinearOpcode::CrazyData,
        LinearOpcode::CrazyData,
        LinearOpcode::CrazyData,
        LinearOpcode::RelocateDataPointer,
    ];
    let suffix: &[LinearOpcode] = match mode {
        AdjacentPhysicalMode::ZeroPair => {
            &[LinearOpcode::CrazyData, LinearOpcode::Halt]
        },
        AdjacentPhysicalMode::ZeroThenInput => &[
            LinearOpcode::CrazyData,
            LinearOpcode::InputWord,
            LinearOpcode::Halt,
        ],
        AdjacentPhysicalMode::RawBytePair => &[
            LinearOpcode::RotateData,
            LinearOpcode::InputWord,
            LinearOpcode::CrazyData,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::Halt,
        ],
    };
    let body_cells = common.len().saturating_add(suffix.len());
    for prefix in 0..PREFIX_BOUND {
        if prefix.saturating_add(body_cells) > code_cells {
            break;
        }
        let mut source = Vec::with_capacity(source_cells);
        for opcode in repeat_n(LinearOpcode::NoOperation, prefix)
            .chain(common)
            .chain(suffix.iter().copied())
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
                    let valid_low = match mode {
                        AdjacentPhysicalMode::ZeroPair
                        | AdjacentPhysicalMode::ZeroThenInput => {
                            profile_crazy(first, third, profile.word_trits())
                                == 0
                        },
                        AdjacentPhysicalMode::RawBytePair => {
                            // p with an all-ones data operand swaps ternary
                            // 0/1 and fixes 2; applying it twice is exactly
                            // identity, even for the raw profile EOF word.
                            let ones = 7_174_453;
                            malbolge::profile_rotate(
                                first,
                                profile.word_modulus(),
                            ) == ones
                                && third == ones
                        },
                    };
                    if high == 0
                        && valid_low
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
                        let input = mode != AdjacentPhysicalMode::ZeroPair;
                        let raw_byte =
                            mode == AdjacentPhysicalMode::RawBytePair;
                        return Ok(PhysicalAdjacentSource {
                            encoded_store_code_address: raw_byte
                                .then(|| as_word(prefix.saturating_add(10)))
                                .transpose()?,
                            high_address: as_word(
                                relocated_address.saturating_add(1),
                            )?,
                            high_code_address: as_word(
                                prefix.saturating_add(5),
                            )?,
                            input_code_address: input
                                .then(|| as_word(prefix.saturating_add(9)))
                                .transpose()?,
                            low_address: as_word(relocated_address)?,
                            low_final_code_address: as_word(
                                prefix.saturating_add(if raw_byte {
                                    12
                                } else {
                                    8
                                }),
                            )?,
                            low_first_code_address: as_word(
                                prefix.saturating_add(8),
                            )?,
                            relocated_initial_words: words,
                            scratch_data_address: as_word(first_address)?,
                            scratch_initial_words: scratch,
                            source,
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
