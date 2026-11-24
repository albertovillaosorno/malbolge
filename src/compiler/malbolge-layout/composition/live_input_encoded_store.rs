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
//   - Source-loaded, full-byte-injective N15 input-dependent memory writes.
// - Must-Not:
//   - Claim this encoded word is a canonical C32 signed getchar result.
// - Allows:
//   - Inputs: canonical N15 and 94 code phases with two graphical tail cells.
//   - Outputs: graphical /;j;p;v source and exact loader-backed store address.
//   - Side effects: none; target execution belongs to the independent VM.
// - Split-When:
//   - Source-C32 normalization and physical branch linking become general.
// - Merge-When:
//   - A source-linked C23 input-state allocator subsumes this intermediate.
// - Summary:
//   - Retains independently all 256 bytes and true EOF through real guest p.

//! Source-loaded guest writes retaining all 257 raw-input classes.
//!
//! For input bytes, the five lowest trits independently span all of 0,1,2.
//! `crazy(seed, input)` is bijective in each of these coordinates only when
//! the corresponding seed trit is one. Input bytes 0..255 use only 0/1 in
//! coordinate five, so its seed trit may be zero or one. EOF differs in
//! higher trits and stays distinct because every crazy seed distinguishes
//! right-operand trits zero and two. This is an *encoded* state, not C32.

use std::iter::repeat_n;

use malbolge::{ProfileDescriptor, current_profile};

use super::{
    CodeVisitRequirement, LinearOpcode, encode_code_visits,
    unique_graphical_cell, unwritten_loader_word,
};

const PHASE_BOUND: usize = 94;
const LOWER_FIVE_ONES: u32 = 121;
const FIVE_TRIT_MODULUS: u32 = 243;
const SIXTH_TRIT_RADIX: u32 = 3;

/// Strictly physical N15 input-state search failure.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum LiveInputEncodedStoreError {
    /// No bounded graphical tail yields the requested injective data stores.
    NoLoadableSeed,
    /// The caller supplied a noncanonical profile.
    UnsupportedProfile,
}

/// Full guest source and actual initial data operand for one encoded input.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LiveInputEncodedStoreSource {
    /// `p` writes its result here, after a real `j`.
    pub data_address: u32,
    /// Loader-initialized `p` operand, not a host-seeded VM word.
    pub initial_data_word: u32,
    /// Zero-based actual `/` code cell.
    pub input_code_address: u32,
    /// Loader-admitted graphical program, including two unreachable tail
    /// cells.
    pub source: Vec<u8>,
    /// Zero-based actual `p` code cell.
    pub store_code_address: u32,
}

/// Two separately retained, source-loaded raw input words in a real N15 guest.
///
/// The second `j` reads an untouched loader-expanded word two cells past the
/// first store, then moves D to a second, disjoint destination. Each `p`
/// retains every byte and true EOF without a host-provided memory seed.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LiveTwoInputEncodedStoreSource {
    /// Address written by the first reached `p`.
    pub first_data_address: u32,
    /// Unmodified loader word read by the first `p`.
    pub first_initial_data_word: u32,
    /// First reached `/` code address.
    pub first_input_code_address: u32,
    /// First reached `p` code address.
    pub first_store_code_address: u32,
    /// Address written by the second reached `p`, distinct from the first.
    pub second_data_address: u32,
    /// Unmodified loader word read by the second `p`.
    pub second_initial_data_word: u32,
    /// Second reached `/` code address.
    pub second_input_code_address: u32,
    /// Second reached `p` code address.
    pub second_store_code_address: u32,
    /// Complete graphical source, including two unreachable loader-tail cells.
    pub source: Vec<u8>,
}

/// Source-loaded input word retained before a separate physical zero write.
///
/// Two genuine `j` instructions separate the raw input destination from a
/// later `*;p;p;p` arithmetic chain. The `*` discards the input accumulator
/// but does not overwrite its earlier stored word. This does not implement
/// C23 signed normalization, two-cell C32 zero or an input-dependent loop.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LiveInputThenZeroSource {
    /// First reached `/` instruction.
    pub input_code_address: u32,
    /// Data cell receiving one injective raw input encoding.
    pub input_data_address: u32,
    /// Unmodified loader operand for the input-dependent `p`.
    pub input_seed: u32,
    /// Exact graphical source with two unreachable loader-tail bytes.
    pub source: Vec<u8>,
    /// Fresh data cells used by `*;p;p;p`, after the second `j`.
    pub zero_chain_address: u32,
    /// Loader-derived initial words at all four chain positions.
    pub zero_chain_seeds: [u32; 4],
    /// The fourth chain write produces actual zero here.
    pub zero_data_address: u32,
}

/// Guest input data word physically revisited by a second data jump.
///
/// After the first `/` and `p`, one loader-backed `j` returns D to the
/// physically overwritten cell. The next `j` then reads the *new* value
/// rather than the virgin loader word, making the final D depend on the
/// observed input. This is an encoded, noncanonical input state, not a C32
/// source local, a guest branch on EOF or a reusable guest loop.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LiveInputReentrySource {
    /// Real `/` code address, after the no-op prefix.
    pub input_code_address: u32,
    /// Second `j` code address, reading the input-modified data word.
    pub input_reentry_code_address: u32,
    /// First return `j` code address, reading an untouched loader word.
    pub return_code_address: u32,
    /// Untouched loader cell selecting the previous stored data address.
    pub return_data_address: u32,
    /// Initial source loader value, exactly `store_data_address - 1`.
    pub return_initial_word: u32,
    /// Number of reached no-op instructions between `p` and return.
    pub return_padding: usize,
    /// Complete graphical source, including two unreachable loader-tail cells.
    pub source: Vec<u8>,
    /// The first `p` code address.
    pub store_code_address: u32,
    /// Written input state and subsequently reread `j` operand address.
    pub store_data_address: u32,
    /// Virgin source-loader word at the input state cell.
    pub store_initial_word: u32,
}

/// Fixed 261-cell physical source reaching expanded memory without assuming
/// that its initial `j` can directly read an expanded loader word.
///
/// The first `j` selects source M41, a `p` overwrites that cell with a
/// high-value pointer, and two genuine `j` operations reread the new value.
/// C18 reads M58=40 and C19 reads the source-written M41.
/// The temporary source cell is never fetched: this prefix halts at C39.
/// Input at C37 writes an encoded raw input to expanded memory at C38.
/// then writes an invertibly encoded raw input to expanded memory at C38. The
/// resulting word is not signed C23 `getchar` or a linked checksum block;
/// following code and its mutation hazards remain unproved.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LongSourceInputBootstrapSource {
    /// Expanded data word physically written by C38.
    pub data_address: u32,
    /// Genuine `p` operand loaded by the normative memory recurrence.
    pub initial_data_word: u32,
    /// High pointer written into a source cell by C1.
    pub high_pointer_word: u32,
    /// Actual `/` guest code address.
    pub input_code_address: u32,
    /// Source cell overwritten by C1 and reread by C19.
    pub modified_source_address: u32,
    /// Original source word forcing C18 to revisit the modified cell.
    pub return_source_address: u32,
    /// Entire loader-valid source, including unreachable reserve cells.
    pub source: Vec<u8>,
    /// Reached, input-dependent `p` source address.
    pub store_code_address: u32,
}

/// Construct a real 261-cell source-backed high-pointer bootstrap.
///
/// C0 relocates D to M41. C1 writes a full-width pointer there using its
/// initially valid source byte 92. C2..C17 advance over valid code cells.
/// C18 reads the authentic source operand M58=40 to return D to M41, and
/// C19 reads the rewritten pointer to relocate D into expanded memory.
/// C20..C36 are no-ops, C37 reads a byte or EOF, C38 writes its reversible
/// input encoding using a loader-derived all-ones word, and C39 halts.
/// The C41/M58 source cells and both tail words are loader-admitted.
/// Both initial source mutation and input encoding are real guest effects;
/// no source-C operation, signed EOF conversion or control edge is linked.
///
/// # Errors
///
/// Refuses a noncurrent target or drifted graphical/loader geometry.
pub fn build_long_source_input_bootstrap_source(
    profile: &ProfileDescriptor,
) -> Result<LongSourceInputBootstrapSource, LiveInputEncodedStoreError> {
    use LiveInputEncodedStoreError::{NoLoadableSeed, UnsupportedProfile};
    if profile != current_profile() {
        return Err(UnsupportedProfile);
    }
    const SOURCE_CELLS: usize = 261;
    const TEMPORARY: usize = 41;
    const RETURN: usize = 58;
    const INPUT: usize = 37;
    const STORE: usize = INPUT + 1;
    let mut source = Vec::with_capacity(SOURCE_CELLS);
    for code in 0..SOURCE_CELLS {
        let opcode = match code {
            0 | 18 | 19 => LinearOpcode::RelocateDataPointer,
            1 | STORE => LinearOpcode::CrazyData,
            INPUT => LinearOpcode::InputWord,
            39 => LinearOpcode::Halt,
            _ => LinearOpcode::NoOperation,
        };
        source.push(
            unique_graphical_cell(profile, opcode, code)
                .map_err(|_error| NoLoadableSeed)?,
        );
    }
    source[TEMPORARY] = 92;
    source[RETURN] = 40;
    source[259] = 62;
    source[260] = 62;
    // The first pointer must select the exact source cell that C1 writes;
    // the second pointer must return there before the third `j` executes.
    if usize::from(source[0]).saturating_add(1) != TEMPORARY
        || usize::from(source[RETURN]).saturating_add(1) != TEMPORARY
        || [(TEMPORARY, 92), (RETURN, 40), (259, 62), (260, 62)]
            .iter()
            .any(|&(address, byte)| {
                unique_graphical_cell(
                    profile,
                    LinearOpcode::SkippedDataByte { byte },
                    address,
                ) != Ok(u8::try_from(byte).unwrap_or_default())
            })
    {
        return Err(NoLoadableSeed);
    }
    let high_pointer_word = malbolge::profile_crazy(
        u32::from(source[TEMPORARY]),
        0,
        profile.word_trits(),
    );
    let data_address = high_pointer_word
        .checked_add(
            u32::try_from(STORE.saturating_sub(19))
                .map_err(|_error| NoLoadableSeed)?,
        )
        .ok_or(NoLoadableSeed)?;
    if usize::try_from(data_address).unwrap_or(0) < SOURCE_CELLS
        || data_address >= profile.memory_words()
    {
        return Err(NoLoadableSeed);
    }
    let initial_data_word = unwritten_loader_word(
        &source,
        usize::try_from(data_address).map_err(|_error| NoLoadableSeed)?,
        profile,
    )
    .map_err(|_error| NoLoadableSeed)?;
    if initial_data_word != malbolge::profile_crazy(0, 0, profile.word_trits())
    {
        return Err(NoLoadableSeed);
    }
    Ok(LongSourceInputBootstrapSource {
        data_address,
        high_pointer_word,
        initial_data_word,
        input_code_address: u32::try_from(INPUT)
            .map_err(|_error| NoLoadableSeed)?,
        modified_source_address: u32::try_from(TEMPORARY)
            .map_err(|_error| NoLoadableSeed)?,
        return_source_address: u32::try_from(RETURN)
            .map_err(|_error| NoLoadableSeed)?,
        source,
        store_code_address: u32::try_from(STORE)
            .map_err(|_error| NoLoadableSeed)?,
    })
}

/// Long-source N15 bootstrap retaining two disjoint input observations.
///
/// C39 i consumes untouched expanded loader operand 62, jumping over C41,
/// which was overwritten with a non-graphical data pointer by the first p.
/// C63 resumes code after the source mutation, with a second input and p.
/// This is finite physical continuation, not signed C23 or a reusable loop.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LongSourceTwoInputBootstrapSource {
    /// Expanded first store address.
    pub first_data_address: u32,
    /// Loader seed used by the first input encoding.
    pub first_initial_data_word: u32,
    /// Reached first input code position.
    pub first_input_code_address: u32,
    /// Reached first store code position.
    pub first_store_code_address: u32,
    /// Forward-jump code position.
    pub jump_code_address: u32,
    /// Source cell changed to the high pointer, never fetched.
    pub modified_source_address: u32,
    /// Destination code cell after the forward jump.
    pub resume_code_address: u32,
    /// Expanded, disjoint second store address.
    pub second_data_address: u32,
    /// Loader seed used by the second input encoding.
    pub second_initial_data_word: u32,
    /// Reached second input code position.
    pub second_input_code_address: u32,
    /// Reached second store code position.
    pub second_store_code_address: u32,
    /// Reached final halt code position.
    pub halt_code_address: u32,
    /// Full 261-cell graphical source, including skipped cell C41.
    pub source: Vec<u8>,
}

/// Build source-backed expanded memory writes from two real input reads.
///
/// The genuine i at C39 consumes loader M[first+1]=62, landing at C63.
/// Three no-ops, input C66 and p C67 make the second write at first+6.
/// Both input data seeds are the loader-derived ternary all-ones word.
///
/// # Errors
///
/// Rejects a noncanonical profile, non-graphical encoding, or loader drift.
pub fn build_long_source_two_input_bootstrap_source(
    profile: &ProfileDescriptor,
) -> Result<LongSourceTwoInputBootstrapSource, LiveInputEncodedStoreError> {
    use LiveInputEncodedStoreError::NoLoadableSeed;
    const JUMP: usize = 39;
    const RESUME: usize = 63;
    const SECOND_INPUT: usize = 66;
    const SECOND_STORE: usize = 67;
    const HALT: usize = 68;
    let first = build_long_source_input_bootstrap_source(profile)?;
    let mut source = first.source;
    for (address, opcode) in [
        (JUMP, LinearOpcode::JumpForward { target: 63 }),
        (SECOND_INPUT, LinearOpcode::InputWord),
        (SECOND_STORE, LinearOpcode::CrazyData),
        (HALT, LinearOpcode::Halt),
    ] {
        source[address] = unique_graphical_cell(profile, opcode, address)
            .map_err(|_error| NoLoadableSeed)?;
    }
    let operand_address =
        first.data_address.checked_add(1).ok_or(NoLoadableSeed)?;
    let operand = unwritten_loader_word(
        &source,
        usize::try_from(operand_address).map_err(|_error| NoLoadableSeed)?,
        profile,
    )
    .map_err(|_error| NoLoadableSeed)?;
    if operand != u32::try_from(RESUME - 1).map_err(|_error| NoLoadableSeed)? {
        return Err(NoLoadableSeed);
    }
    let second_data_address =
        first.data_address.checked_add(6).ok_or(NoLoadableSeed)?;
    if second_data_address >= profile.memory_words() {
        return Err(NoLoadableSeed);
    }
    let second_initial_data_word = unwritten_loader_word(
        &source,
        usize::try_from(second_data_address)
            .map_err(|_error| NoLoadableSeed)?,
        profile,
    )
    .map_err(|_error| NoLoadableSeed)?;
    if second_initial_data_word != first.initial_data_word {
        return Err(NoLoadableSeed);
    }
    Ok(LongSourceTwoInputBootstrapSource {
        first_data_address: first.data_address,
        first_initial_data_word: first.initial_data_word,
        first_input_code_address: first.input_code_address,
        first_store_code_address: first.store_code_address,
        jump_code_address: u32::try_from(JUMP)
            .map_err(|_error| NoLoadableSeed)?,
        modified_source_address: first.modified_source_address,
        resume_code_address: u32::try_from(RESUME)
            .map_err(|_error| NoLoadableSeed)?,
        second_data_address,
        second_initial_data_word,
        second_input_code_address: u32::try_from(SECOND_INPUT)
            .map_err(|_error| NoLoadableSeed)?,
        second_store_code_address: u32::try_from(SECOND_STORE)
            .map_err(|_error| NoLoadableSeed)?,
        halt_code_address: u32::try_from(HALT)
            .map_err(|_error| NoLoadableSeed)?,
        source,
    })
}

/// One finite, source-loaded N15 self-modifying input loop.
///
/// The C68 indirect code jump reenters C63 twelve times while its physical
/// data pointer advances through untouched loader words. After the twelfth
/// backedge, C65 has self-encrypted to `v` and halts on step 115. Subsequent
/// graphical code bytes are not rewritten by the host, and this fixed
/// self-modifying schedule is not a reusable source-C/EOF loop.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LongSourceFiniteInputLoopSource {
    /// One canonical graphical source including its source-tail loader seeds.
    pub source: Vec<u8>,
    /// Preserved first input encoding written at C38.
    pub first_data_address: u32,
    /// Preserved second input encoding written at C67.
    pub second_data_address: u32,
    /// Original loader seed at each of those two physical store addresses.
    pub initial_data_word: u32,
    /// Reentered code-cell address C63.
    pub loop_entry_code_address: u32,
    /// Backedge source-cell address C68.
    pub backedge_code_address: u32,
    /// Final, self-encrypted halt at C65, not at the backedge.
    pub final_halt_code_address: u32,
}

/// Build a genuine bounded backward `i` path over mutable source instructions.
///
/// This deliberately differs from a hand-unrolled read sequence: the same
/// C63..C68 graphical code cells execute on repeated visits and mutate under
/// XLAT2. Each of twelve `i` operands is a different, unwritten N15 loader
/// word, all equal to C63-1. The code-site visit schedule and exact halt are
/// independently replayed by the normative VM; they are not inferred from
/// these loader values alone.
///
/// # Errors
///
/// Rejects any source/profile or loader-seed drift before providing a witness.
pub fn build_long_source_finite_input_loop_source(
    profile: &ProfileDescriptor,
) -> Result<LongSourceFiniteInputLoopSource, LiveInputEncodedStoreError> {
    use LiveInputEncodedStoreError::NoLoadableSeed;
    const ENTRY: u32 = 63;
    const BACKEDGE: u32 = 68;
    const BACKEDGES: u32 = 12;
    let plan = build_long_source_two_input_bootstrap_source(profile)?;
    let mut source = plan.source;
    let backedge = source
        .get_mut(usize::try_from(BACKEDGE).map_err(|_error| NoLoadableSeed)?)
        .ok_or(NoLoadableSeed)?;
    *backedge = encode_code_visits(profile, BACKEDGE, &[
        CodeVisitRequirement::Decoded(b'i'),
    ])
    .map_err(|_error| NoLoadableSeed)?;
    for iteration in 0..BACKEDGES {
        let stride = iteration
            .checked_mul(6)
            .and_then(|offset| offset.checked_add(1))
            .ok_or(NoLoadableSeed)?;
        let address = plan
            .second_data_address
            .checked_add(stride)
            .ok_or(NoLoadableSeed)?;
        let operand = unwritten_loader_word(
            &source,
            usize::try_from(address).map_err(|_error| NoLoadableSeed)?,
            profile,
        )
        .map_err(|_error| NoLoadableSeed)?;
        if operand != ENTRY - 1 {
            return Err(NoLoadableSeed);
        }
    }
    Ok(LongSourceFiniteInputLoopSource {
        source,
        first_data_address: plan.first_data_address,
        second_data_address: plan.second_data_address,
        initial_data_word: plan.first_initial_data_word,
        loop_entry_code_address: ENTRY,
        backedge_code_address: BACKEDGE,
        final_halt_code_address: 65,
    })
}

/// Predicate for lossless raw 0..255 and EOF in a single guest crazy word.
///
/// Five low seed trits must be one. Since successful input values occupy
/// only trits 0 and 1 at position five, its seed trit must not equal two.
#[expect(
    clippy::integer_division,
    clippy::integer_division_remainder_used,
    reason = "exact ternary byte and EOF input encoding test"
)]
const fn retains_all_raw_inputs(seed: u32) -> bool {
    seed % FIVE_TRIT_MODULUS == LOWER_FIVE_ONES
        && (seed / FIVE_TRIT_MODULUS) % SIXTH_TRIT_RADIX != 2
}

/// Reuse the same finite graphical source/loader-tail census for one or two
/// source-backed input stores. The callback may require an additional, truly
/// disjoint address but cannot substitute a synthetic loader word.
#[expect(
    clippy::excessive_nesting,
    clippy::too_many_lines,
    reason = "exact bounded loader seed and graphical phase enumeration"
)]
fn find_injective_source<T>(
    profile: &ProfileDescriptor,
    suffix: &[LinearOpcode],
    mut accept: impl FnMut(
        &[u8],
        usize,
        u32,
        usize,
    ) -> Result<Option<T>, LiveInputEncodedStoreError>,
) -> Result<T, LiveInputEncodedStoreError> {
    use LiveInputEncodedStoreError::{NoLoadableSeed, UnsupportedProfile};
    if profile != current_profile() {
        return Err(UnsupportedProfile);
    }
    let memory_words = usize::try_from(profile.memory_words())
        .map_err(|_error| NoLoadableSeed)?;
    for prefix in 0..PHASE_BOUND {
        let mut source = Vec::with_capacity(
            prefix.saturating_add(suffix.len()).saturating_add(2),
        );
        for operation in repeat_n(LinearOpcode::NoOperation, prefix)
            .chain(suffix.iter().copied())
        {
            let cell = unique_graphical_cell(profile, operation, source.len())
                .map_err(|_error| NoLoadableSeed)?;
            source.push(cell);
        }
        let Some(&jump_byte) = source.get(prefix.saturating_add(1)) else {
            return Err(NoLoadableSeed);
        };
        let first_data_address = usize::from(jump_byte).saturating_add(1);
        if first_data_address <= source.len().saturating_add(2)
            || first_data_address >= memory_words
        {
            continue;
        }
        for first in 33..=126u8 {
            if unique_graphical_cell(
                profile,
                LinearOpcode::SkippedDataByte { byte: u32::from(first) },
                source.len(),
            ) != Ok(first)
            {
                continue;
            }
            source.push(first);
            for last in 33..=126u8 {
                if unique_graphical_cell(
                    profile,
                    LinearOpcode::SkippedDataByte { byte: u32::from(last) },
                    source.len(),
                ) != Ok(last)
                {
                    continue;
                }
                source.push(last);
                let seed =
                    unwritten_loader_word(&source, first_data_address, profile)
                        .map_err(|_error| NoLoadableSeed)?;
                if retains_all_raw_inputs(seed)
                    && let Some(plan) =
                        accept(&source, first_data_address, seed, prefix)?
                {
                    return Ok(plan);
                }
                _ = source.pop();
            }
            _ = source.pop();
        }
    }
    Err(NoLoadableSeed)
}

/// Build a bounded N15 source retaining all 257 raw `getchar` classes.
///
/// The exhaustive search tries 0..93 `o` prefixes before `/;j;p;v` and
/// at most 94² graphical two-cell tails. Only tails admitted by the strict
/// layout decoder are considered; data operands are read from the six-phase
/// source loader. The first matching seed is canonical by search order.
///
/// This does not produce C23 signed `-1`, canonical C32 frame writes,
/// a second usable read, source arithmetic, or guest-controlled branching.
///
/// # Errors
///
/// Rejects noncanonical profiles or a missing source-loadable seed.
pub fn build_live_input_injective_store_source(
    profile: &ProfileDescriptor,
) -> Result<LiveInputEncodedStoreSource, LiveInputEncodedStoreError> {
    use LiveInputEncodedStoreError::NoLoadableSeed;
    find_injective_source(
        profile,
        &[
            LinearOpcode::InputWord,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::Halt,
        ],
        |source, data_address, seed, prefix| {
            Ok(Some(LiveInputEncodedStoreSource {
                data_address: u32::try_from(data_address)
                    .map_err(|_error| NoLoadableSeed)?,
                initial_data_word: seed,
                input_code_address: u32::try_from(prefix)
                    .map_err(|_error| NoLoadableSeed)?,
                source: source.to_vec(),
                store_code_address: u32::try_from(prefix.saturating_add(2))
                    .map_err(|_error| NoLoadableSeed)?,
            }))
        },
    )
}

/// Build a bounded source preserving two independent raw input observations.
///
/// Exhausts 0..93 no-op prefixes and at most 94² legal graphical tails of
/// `/;j;p;/;j;p;v`. No data word is host-seeded. The second `j` reads the
/// original loader word at `first_data_address + 2`, never the first written
/// cell. Both stores must admit all 257 byte/EOF classes independently.
///
/// This does not normalize signed C23 input, implement a source-C local,
/// branch on EOF, combine the words into arithmetic, or link the checksum.
///
/// # Errors
///
/// Refuses noncurrent profiles and the absence of a safe two-store layout.
pub fn build_live_two_input_injective_store_source(
    profile: &ProfileDescriptor,
) -> Result<LiveTwoInputEncodedStoreSource, LiveInputEncodedStoreError> {
    use LiveInputEncodedStoreError::NoLoadableSeed;
    find_injective_source(
        profile,
        &[
            LinearOpcode::InputWord,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::InputWord,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::Halt,
        ],
        |source, first_data_address, first_seed, prefix| {
            let memory_words =
                usize::try_from(profile.memory_words()).unwrap_or(0);
            let word = |value: usize| {
                u32::try_from(value).map_err(|_error| NoLoadableSeed)
            };
            let jump_address = first_data_address.saturating_add(2);
            if jump_address >= memory_words {
                return Ok(None);
            }
            let second_jump =
                unwritten_loader_word(source, jump_address, profile)
                    .map_err(|_error| NoLoadableSeed)?;
            let second_data_address =
                usize::try_from(second_jump.saturating_add(1))
                    .map_err(|_error| NoLoadableSeed)?;
            if second_data_address <= source.len().saturating_add(2)
                || second_data_address >= memory_words
                || second_data_address == first_data_address
            {
                return Ok(None);
            }
            let second_seed =
                unwritten_loader_word(source, second_data_address, profile)
                    .map_err(|_error| NoLoadableSeed)?;
            if !retains_all_raw_inputs(second_seed) {
                return Ok(None);
            }
            Ok(Some(LiveTwoInputEncodedStoreSource {
                first_data_address: word(first_data_address)?,
                first_initial_data_word: first_seed,
                first_input_code_address: word(prefix)?,
                first_store_code_address: word(prefix.saturating_add(2))?,
                second_data_address: word(second_data_address)?,
                second_initial_data_word: second_seed,
                second_input_code_address: word(prefix.saturating_add(3))?,
                second_store_code_address: word(prefix.saturating_add(5))?,
                source: source.to_vec(),
            }))
        },
    )
}

/// Emit a bounded input-retaining store followed by an independent zero.
///
/// The finite source grammar is `o*;/;j;p;j;*;p;p;p;v;tail;tail` with at
/// most 94 no-op prefixes and 94² legal graphical tails. Both data-pointer
/// relocations read genuine source/expanded-loader memory. The first `p`
/// injectively retains every byte and EOF, and the second arithmetic chain
/// overwrites A without clobbering the earlier data word.
///
/// # Errors
///
/// Refuses forged profiles or an unsatisfiable loader-derived placement.
#[expect(
    clippy::too_many_lines,
    reason = "bounded physical two-region source and loader search"
)]
pub fn build_live_input_then_zero_source(
    profile: &ProfileDescriptor,
) -> Result<LiveInputThenZeroSource, LiveInputEncodedStoreError> {
    use LiveInputEncodedStoreError::NoLoadableSeed;
    find_injective_source(
        profile,
        &[
            LinearOpcode::InputWord,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::RotateData,
            LinearOpcode::CrazyData,
            LinearOpcode::CrazyData,
            LinearOpcode::CrazyData,
            LinearOpcode::Halt,
        ],
        |source, input_data_address, input_seed, prefix| {
            let memory_words = usize::try_from(profile.memory_words())
                .map_err(|_error| NoLoadableSeed)?;
            let next = input_data_address.saturating_add(1);
            if next >= memory_words {
                return Ok(None);
            }
            let relocated_word = unwritten_loader_word(source, next, profile)
                .map_err(|_error| NoLoadableSeed)?;
            let base = usize::try_from(relocated_word.saturating_add(1))
                .map_err(|_error| NoLoadableSeed)?;
            if base <= source.len().saturating_add(2)
                || base.saturating_add(3) >= memory_words
                || (base..=base.saturating_add(3)).contains(&input_data_address)
            {
                return Ok(None);
            }
            let mut seeds = [0; 4];
            for (offset, seed) in seeds.iter_mut().enumerate() {
                *seed = unwritten_loader_word(
                    source,
                    base.saturating_add(offset),
                    profile,
                )
                .map_err(|_error| NoLoadableSeed)?;
            }
            let rotated =
                malbolge::profile_rotate(seeds[0], profile.word_modulus());
            let first = malbolge::profile_crazy(
                seeds[1],
                rotated,
                profile.word_trits(),
            );
            let second =
                malbolge::profile_crazy(seeds[2], first, profile.word_trits());
            let third =
                malbolge::profile_crazy(seeds[3], second, profile.word_trits());
            if third != 0 {
                return Ok(None);
            }
            let word = |value: usize| {
                u32::try_from(value).map_err(|_error| NoLoadableSeed)
            };
            Ok(Some(LiveInputThenZeroSource {
                input_code_address: word(prefix)?,
                input_data_address: word(input_data_address)?,
                input_seed,
                source: source.to_vec(),
                zero_chain_address: word(base)?,
                zero_chain_seeds: seeds,
                zero_data_address: word(base.saturating_add(3))?,
            }))
        },
    )
}

/// Build source-backed, byte-dependent guest data-pointer reentry.
///
/// Enumerates at most 15 padding lengths (0..=14), 94 positional no-op
/// prefixes and 94 squared graphical two-cell tails for the exact grammar
/// `o*;/;j;p;o*;j;j;v;tail;tail`. The return `j` must read an unmodified
/// loader word equal to the previous `p` data address minus one. The next
/// `j` reads the *physically updated* `p` result, so it relocates to a
/// different D for every byte and actual EOF.
///
/// The bound is intentional: this demonstrates genuine mutable guest data
/// reuse and data-dependent pointer placement, not executable C control,
/// signed EOF normalization or a restartable checksum loop.
///
/// # Errors
///
/// Rejects a noncanonical N15 profile or the absence of a layout within the
/// fixed 15 x 94 x 94² search budget.
#[expect(
    clippy::too_many_lines,
    reason = "finite physical source-loaded reentry search"
)]
pub fn build_live_input_reentry_source(
    profile: &ProfileDescriptor,
) -> Result<LiveInputReentrySource, LiveInputEncodedStoreError> {
    use LiveInputEncodedStoreError::{NoLoadableSeed, UnsupportedProfile};
    if profile != current_profile() {
        return Err(UnsupportedProfile);
    }
    let memory_words = usize::try_from(profile.memory_words())
        .map_err(|_error| NoLoadableSeed)?;
    for padding in 0..=14usize {
        let mut suffix = vec![
            LinearOpcode::InputWord,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::CrazyData,
        ];
        suffix.extend(repeat_n(LinearOpcode::NoOperation, padding));
        suffix.extend([
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::RelocateDataPointer,
            LinearOpcode::Halt,
        ]);
        let found = find_injective_source(
            profile,
            &suffix,
            |source, store_address, seed, prefix| {
                let return_address =
                    store_address.saturating_add(1).saturating_add(padding);
                if return_address <= source.len().saturating_add(2)
                    || return_address >= memory_words
                {
                    return Ok(None);
                }
                let return_word =
                    unwritten_loader_word(source, return_address, profile)
                        .map_err(|_error| NoLoadableSeed)?;
                if return_word
                    != u32::try_from(store_address.saturating_sub(1))
                        .map_err(|_error| NoLoadableSeed)?
                {
                    return Ok(None);
                }
                let word = |n: usize| {
                    u32::try_from(n).map_err(|_error| NoLoadableSeed)
                };
                Ok(Some(LiveInputReentrySource {
                    input_code_address: word(prefix)?,
                    input_reentry_code_address: word(
                        prefix.saturating_add(4).saturating_add(padding),
                    )?,
                    return_code_address: word(
                        prefix.saturating_add(3).saturating_add(padding),
                    )?,
                    return_data_address: word(return_address)?,
                    return_initial_word: return_word,
                    return_padding: padding,
                    source: source.to_vec(),
                    store_code_address: word(prefix.saturating_add(2))?,
                    store_data_address: word(store_address)?,
                    store_initial_word: seed,
                }))
            },
        );
        match found {
            Ok(plan) => return Ok(plan),
            Err(NoLoadableSeed) => {},
            Err(UnsupportedProfile) => return Err(UnsupportedProfile),
        }
    }
    Err(NoLoadableSeed)
}
