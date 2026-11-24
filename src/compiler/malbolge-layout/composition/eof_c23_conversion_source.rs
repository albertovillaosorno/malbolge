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
//   - Loader-valid source placement for two actual signed-input crazy writes.
// - Must-Not:
//   - Call the two-read physical C23 byte converter source-C compilation.
// - Allows:
//   - Inputs: exact current 15-trit target profile.
//   - Outputs: source-valid physical signed-I/O and crazy-code probes.
//   - Side effects: none; downstream normative execution proves the source.
// - Split-When:
//   - General guest operand synthesis replaces fixed graphical placement.
// - Merge-When:
//   - Source-C dynamic CFG linking subsumes the bounded source probes.
// - Summary:
//   - Connects real loader words to input-dependent physical crazy writes.

//! Physical guest loader, byte-I/O and arithmetic, **not** source-C lowering.
//!
//! The `Iy` seed supplies operands for nine genuine rotations and physical
//! crazy operations. The shortened two-read route now emits a correct C23
//! converted byte, including EOF, from the second input. The first input is
//! still consumed and discarded. None of these probes is a compiled C program.

use malbolge::{
    ProfileDescriptor, current_profile, decode_profile_instruction,
};

use super::loader_rotation_source::{
    RepeatedLoaderRotationError, build_c23_seed_nine_rotated_operand_source,
    build_c23_seed_rotated_input_echo_source,
};

const SOURCE_CELLS: usize = 279;

/// Failure to construct the exact graphical input/operand experiment.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum C23OperandProbeSourceError {
    /// A graphical probe needs two source cells for loader expansion.
    InsufficientSourceCells {
        /// Number of provided source words.
        cells: usize,
    },
    /// Source words must fit the current profile's memory domain.
    SourceExceedsMemory {
        /// Number of provided source words.
        cells: usize,
        /// Maximum loaded word count.
        limit: u32,
    },
    /// An operation escaped the frozen source length.
    InvalidPosition {
        /// Rejected source position.
        position: usize,
    },
    /// Source position has no valid graphical encoding for its opcode.
    MissingGraphicalEncoding {
        /// Exact attempted code position.
        position: usize,
        /// Requested decoded opcode.
        opcode: u8,
    },
    /// The source-locked Iy rotation seed could not be prepared.
    RotationPreparation {
        /// Exact failure in the source-locked rotation stage.
        error: RepeatedLoaderRotationError,
    },
    /// A generated graphical cell cannot pass the strict VM loader.
    InvalidGraphicalSourceCell {
        /// Invalid exact source position.
        position: usize,
        /// Source byte the loader would reject.
        byte: u8,
    },
    /// Current 15-trit profile is the only supported loader geometry.
    UnsupportedProfile,
}

fn graphical(
    position: usize,
    opcode: u8,
) -> Result<u8, C23OperandProbeSourceError> {
    let address = u32::try_from(position).unwrap_or(u32::MAX);
    (33..=126u8)
        .find(|byte| {
            decode_profile_instruction(u32::from(*byte), address)
                == Some(opcode)
        })
        .ok_or(C23OperandProbeSourceError::MissingGraphicalEncoding {
            position,
            opcode,
        })
}

fn set(
    source: &mut [u8],
    position: usize,
    opcode: u8,
) -> Result<(), C23OperandProbeSourceError> {
    let byte = graphical(position, opcode)?;
    *source
        .get_mut(position)
        .ok_or(C23OperandProbeSourceError::InvalidPosition { position })? =
        byte;
    Ok(())
}

/// Reject cells that the strict graphical profile loader would reject.
///
/// This checks lexical source admission only. In particular, an instruction
/// that is valid at its *source* position may encrypt into a different opcode
/// before a subsequent execution; VM path verification remains separate.
///
/// # Errors
///
/// Reports the first non-graphical or illegal decoded source cell.
pub fn admit_c23_probe_graphical_source(
    source: &[u8],
) -> Result<(), C23OperandProbeSourceError> {
    if source.len() < 2 {
        return Err(C23OperandProbeSourceError::InsufficientSourceCells {
            cells: source.len(),
        });
    }
    let limit = current_profile().word_modulus();
    if source.len() > usize::try_from(limit).unwrap_or(usize::MAX) {
        return Err(C23OperandProbeSourceError::SourceExceedsMemory {
            cells: source.len(),
            limit,
        });
    }
    for (position, &byte) in source.iter().enumerate() {
        let address = u32::try_from(position).unwrap_or(u32::MAX);
        if !decode_profile_instruction(u32::from(byte), address)
            .is_some_and(|opcode| b"oijp*/<v".contains(&opcode))
        {
            return Err(
                C23OperandProbeSourceError::InvalidGraphicalSourceCell {
                    position,
                    byte,
                },
            );
        }
    }
    Ok(())
}

/// Construct a VM-executable signed-input/two-crazy **probe** source.
///
/// The first `j` at C=8 relocates D to 127; by C=164, D=282.
/// The `/` reads the actual byte or target EOF word; `p` at C=165,166
/// then reads loader-expanded M[283], M[284], and `<` emits at C=167.
/// A 169-step halt occurs at C=168. The output is **not** the C23 byte.
///
/// # Errors
///
/// Rejects wrong profiles or a missing graphical source encoding. The
/// resulting candidate still requires independent normative VM admission.
pub fn build_c23_operand_probe_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    if profile != current_profile() {
        return Err(C23OperandProbeSourceError::UnsupportedProfile);
    }
    let mut source = (0..SOURCE_CELLS)
        .map(|position| graphical(position, b'o'))
        .collect::<Result<Vec<_>, _>>()?;
    for (position, opcode) in [
        (8, b'j'),
        (164, profile.input_instruction()),
        (165, b'p'),
        (166, b'p'),
        (167, profile.output_instruction()),
        (168, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    source
        .get_mut(277..279)
        .ok_or(C23OperandProbeSourceError::InvalidPosition { position: 277 })?
        .copy_from_slice(b"Iy");
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Compose five actual rotations of the correct Iy seed with signed I/O.
///
/// The checked loader initializes M95=7,174,404 and M96=121. Five real
/// `*` instructions reach M95=4,281,052; the mandatory C37 `/` reads a
/// genuine input byte or EOF. Five data-pointer `j` operations then return
/// to M95 through the *encrypted* M37=66, M67=67 and M68=94 chain.
/// Two physical `p` instructions consume both prepared loader operands,
/// followed by a real output and halt. All successful bytes echo exactly,
/// but target EOF emits 0x0f rather than C23 0xff. Four further rotations
/// and input-preserving linkage remain open; this is not a C artifact.
///
/// # Errors
///
/// Refuses noncanonical profiles, a rejected rotation precursor or an
/// unavailable position-sensitive graphical opcode. Normative execution
/// is still required to establish actual instruction effects.
pub fn build_c23_five_rotated_signed_crazy_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    if profile != current_profile() {
        return Err(C23OperandProbeSourceError::UnsupportedProfile);
    }
    let mut source = build_c23_seed_rotated_input_echo_source(profile)
        .map_err(|error| C23OperandProbeSourceError::RotationPreparation {
            error,
        })?;
    // The source-locked input at C37 encrypts M37 from 80 into 66.
    // M67 and M68 are not reached code in this 48-step experiment.
    *source.get_mut(67).ok_or(
        C23OperandProbeSourceError::InvalidPosition { position: 67 },
    )? = 67;
    *source.get_mut(68).ok_or(
        C23OperandProbeSourceError::InvalidPosition { position: 68 },
    )? = 94;
    set(&mut source, 38, b'o')?;
    for position in 39..=43 {
        set(&mut source, position, b'j')?;
    }
    for (position, opcode) in [
        (44, b'p'),
        (45, b'p'),
        (46, profile.output_instruction()),
        (47, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Observe a second signed input after nine physical Iy rotations.
///
/// The `Iy` seed undergoes nine actual M95 rotations and the source's
/// mandatory first `/` at C37. After the last `*`, C66/C67 follow M96
/// and M122; the source-locked M68=94 then executes as a no-op at C68,
/// where self-encryption changes it into 57. C69 advances D to M160,
/// and C70..C72 reset D via M158 and the encrypted M37. C73 reads the
/// *second* input. C74 `j` follows the now-encrypted M68=57 to M58,
/// not the originally intended M95. Two genuine `p` writes therefore
/// consume M58=104 and M59=104, before `<` and `v` at C77/C78.
/// This source is a **negative C23 conversion probe**: it never links
/// mutable C state and cannot implement ordinary single-read getchar.
///
/// # Errors
///
/// Refuses noncanonical profiles, malformed loader preparation or an
/// unavailable graphical opcode. Normative guest execution remains the
/// independent evidence for all physical effects.
pub fn build_c23_nine_rotated_second_input_crazy_probe_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    if profile != current_profile() {
        return Err(C23OperandProbeSourceError::UnsupportedProfile);
    }
    let mut source = build_c23_seed_nine_rotated_operand_source(profile)
        .map_err(|error| C23OperandProbeSourceError::RotationPreparation {
            error,
        })?;
    for (position, opcode) in [
        (66, b'j'),
        (69, b'o'),
        (70, b'j'),
        (71, b'j'),
        (72, b'j'),
        (73, profile.input_instruction()),
        (74, b'j'),
        (75, b'p'),
        (76, b'p'),
        (77, profile.output_instruction()),
        (78, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Execute the complete signed C23 two-crazy conversion **without output**.
///
/// Nine real `*` instructions prepare M95=7,138,732 from the `Iy` seed.
/// The mandatory earlier input at C37 is discarded by later rotations.
/// A second physical `/` at C69 reads the value to convert. After two
/// reset jumps and a five-jump source/encryption-aware pointer chain,
/// C79 and C80 execute `p` against M95 and M96=121 respectively.
/// Source-required M81=94 decodes as `v` and halts at C81 before `<` can
/// emit the converted result. This is guest arithmetic, **not** C I/O
/// lowering or the P2 checksum; relocating the output remains necessary.
///
/// # Errors
///
/// Refuses unsupported profiles and invalid source encoding. Normative
/// VM execution must verify input provenance and both actual writes.
pub fn build_c23_nine_rotated_signed_conversion_without_output_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    if profile != current_profile() {
        return Err(C23OperandProbeSourceError::UnsupportedProfile);
    }
    let mut source = build_c23_seed_nine_rotated_operand_source(profile)
        .map_err(|error| C23OperandProbeSourceError::RotationPreparation {
            error,
        })?;
    for (position, opcode) in [
        (66, b'j'),
        (69, profile.input_instruction()),
        (70, b'j'),
        (71, b'j'),
        (72, b'j'),
        (73, b'j'),
        (74, b'o'),
        (75, b'j'),
        (76, b'j'),
        (77, b'j'),
        (78, b'j'),
        (79, b'p'),
        (80, b'p'),
        // This unexecuted source/data cell supplies the C75 j operand.
        (87, b'p'),
    ] {
        set(&mut source, position, opcode)?;
    }
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Execute and emit the **converted** C23 signed input byte in the guest.
///
/// Nine actual rotations of the Iy loader word finish at C65. C66 then
/// executes the second real signed `/` (C37 still consumes the first).
/// C67 follows M97=7,174,404 to D=7,174,405, and C69 follows the loader's
/// six-period M[7,174,406]=157 to D=158. C70..C74 use previously written
/// pointer words to reach D=80, C75 advances to D=81, and C76 follows the
/// unchanged source-required M81=94 to M95. C77/C78 finally perform both
/// correct C23 `p` operations against M95=7,138,732 and M96=121. C79 `<`
/// emits the converted low byte (including signed EOF => 0xff) and C80
/// halts. This avoids executing C81, whose fixed source byte is `v`.
///
/// This is a genuine guest-physical signed-byte conversion, not ordinary C
/// `getchar`: the first independent read is still consumed at C37.
/// The graphical value 80 at C37 is also an early pointer operand: C10
/// reads M37 before executing C37, C11 follows M81=94, and C12 must rotate
/// M95. Simply replacing the C37 read with graphical no-op 125 changes that
/// early pointer reset. The apparent successful-byte echo then stores the
/// wrong M158/M159 words and fails C23 EOF conversion. This is a local
/// one-cell obstruction, not a general impossibility of single-read code.
/// No source C32 state, checksum branch, phi movement, or looping program.
///
/// # Errors
///
/// Refuses profiles other than current N15, or any missing graphical opcode.
/// Independent normative VM execution must establish the path and output.
pub fn build_c23_nine_rotated_signed_output_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source =
        build_c23_nine_rotated_signed_conversion_without_output_source(
            profile,
        )?;
    for (position, opcode) in [
        (66, profile.input_instruction()),
        (69, b'j'),
        (74, b'j'),
        (75, b'o'),
        (77, b'p'),
        (78, b'p'),
        (79, profile.output_instruction()),
        (80, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Preserve the *first* real signed input in a lossless, virgin data cell.
///
/// The original Iy bootstrap executes five physical rotations of M95 before
/// C37 reads stdin. C42 then reads the source-valid M67=125 (an unreachable
/// `i` opcode), so C43 `p` visits virgin M126=121 and writes
/// `crazy(121, input)`. This stores all 256 bytes and true EOF injectively,
/// without changing the prepared M95 or M96 conversion operands. C44 halts
/// before the sixth rotation. It is deliberately a bounded state-preservation
/// **probe**: there is no route back to M95, C32 normalization, source-C
/// arithmetic, guest output, or checksum loop.
///
/// # Errors
///
/// Rejects a profile outside current N15 or unencodable physical instructions.
/// A real VM witness must check the code and data effects independently.
pub fn build_c23_first_input_lossless_store_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source = build_c23_nine_rotated_signed_output_source(profile)?;
    // Unreached source C67 remains graphically valid but now moves C42's
    // data pointer from M68 to M126, an untouched all-one low-trit operand.
    *source.get_mut(67).ok_or(
        C23OperandProbeSourceError::InvalidPosition { position: 67 },
    )? = 125;
    set(&mut source, 43, b'p')?;
    set(&mut source, 44, b'v')?;
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Preserve and emit the same first guest input after two real crazy writes.
///
/// This extends the source-loaded C37 `/`, C43 `p` store at M126 by advancing
/// D through five no-ops to untouched loader M132=121. The reached C49 `p`
/// applies a second 15-trit crazy operation, restoring every successful raw
/// byte to A while preserving the first injective store at M126. C50 `<`
/// emits that byte and C51 `v` halts. Genuine N15 EOF instead restores the
/// distinct word 7,174,574 and emits 174, **not** the C23 EOF conversion.
/// This is a bounded physical state-and-output primitive, not source-C input
/// handling, an EOF branch, a typed mutable local or checksum lowering.
///
/// # Errors
///
/// Refuses a noncanonical N15 profile, invalid graphical source or any
/// position without the required instruction encoding. VM evidence must
/// separately check every claimed memory and I/O effect.
pub fn build_c23_first_input_saved_and_echoed_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source = build_c23_first_input_lossless_store_source(profile)?;
    for position in 44..=48 {
        set(&mut source, position, b'o')?;
    }
    for (position, opcode) in
        [(49, b'p'), (50, profile.output_instruction()), (51, b'v')]
    {
        set(&mut source, position, opcode)?;
    }
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Preserve and emit two independently stored raw guest inputs in one source.
///
/// The first C37 read, C43/M126 injective store, C49/M132 restoration, and
/// C50 byte output remain the same as the one-input witness. The continuation
/// advances D to M137, reads a **second** real input at C54, writes an
/// independent 257-class representation at C55/M138, then advances five
/// further data cells to untouched loader M144=121. C61 `p` restores each
/// second successful byte for C62 `<`, and C63 `v` halts after 64 steps.
/// Neither later `p` overwrites the original first saved guest input at M126.
/// The two missing-input observations are raw N15 EOF and emit 174, not C23
/// 255; this source is no dynamic EOF loop, checksum, or compiler CFG link.
///
/// # Errors
///
/// Refuses unsupported N15 profiles and unavailable graphical code sites.
/// The returned source requires independent normative VM path validation.
pub fn build_c23_two_inputs_saved_and_echoed_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source = build_c23_first_input_saved_and_echoed_source(profile)?;
    for position in 51..=63 {
        set(&mut source, position, b'o')?;
    }
    for (position, opcode) in [
        (54, profile.input_instruction()),
        (55, b'p'),
        (61, b'p'),
        (62, profile.output_instruction()),
        (63, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Re-enter encrypted guest code after two stored and echoed input attempts.
///
/// This is a physical **EOF instruction-fetch discriminator**, not a valid
/// source-C branch. C63/C64 `j` return D to the encrypted C37 word; C65 `i`
/// enters C67, whose source-required value 125 executes as another `i` and
/// transfers control to encrypted C35. The second traversal reaches C45,
/// now self-encrypted to `p`: it writes `crazy(M49=75, restored_second_input)`
/// into the next instruction at C49. For every successful byte 0..255,
/// that word is non-graphical and the VM terminates at C49. For true N15
/// EOF only, the word becomes graphical 42 and the VM reaches C57 `<` to
/// emit an additional byte before terminating on non-graphical C60.
///
/// No branch has a valid C23 EOF/non-EOF **halt** or backedge. This probe
/// authenticates one input-dependent, self-modifying code-fetch decision,
/// not an executable checksum, legal C if/else or guest loop.
///
/// # Errors
///
/// Rejects a noncanonical target, source-invalid byte or missing positional
/// encoding. Independent normative VM and scalar-trit replay are mandatory.
pub fn build_c23_two_inputs_eof_fetch_probe_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source = build_c23_two_inputs_saved_and_echoed_source(profile)?;
    for (position, opcode) in [(63, b'j'), (64, b'j'), (65, b'i')] {
        set(&mut source, position, opcode)?;
    }
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Extend a first-read lossless store across the eighth real Iy rotation.
///
/// The first signed `/` at C37 feeds a physical C43 `p` write to M126.
/// C44 writes temporary M127, and the C45..C49 pointer chain returns D to
/// M95 without touching M126. C50, C57 and C64 then perform rotations six,
/// seven and eight with two further source-loaded data-pointer resets.
/// C65 halts before reaching the unmodified second `/` at C66 and the
/// source-required C67=125 `i`. The original M96=121 operand remains virgin.
/// This is **not** a ninth rotation, signed C23 conversion, a source-C
/// checksum or an arbitrary-input loop, and no guest output is emitted.
///
/// # Errors
///
/// Rejects non-N15 profiles, non-graphical instructions and failed upstream
/// loadable first-read storage. Normative VM traces must check every effect.
pub fn build_c23_first_input_saved_eight_rotations_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source = build_c23_first_input_lossless_store_source(profile)?;
    for (position, opcode) in [
        (44, b'p'),
        (45, b'j'),
        (46, b'j'),
        (47, b'j'),
        (48, b'o'),
        (49, b'j'),
        (50, b'*'),
        (51, b'j'),
        (52, b'j'),
        (53, b'j'),
        (54, b'j'),
        (55, b'o'),
        (56, b'j'),
        (57, b'*'),
        (58, b'j'),
        (59, b'j'),
        (60, b'j'),
        (61, b'j'),
        (62, b'o'),
        (63, b'j'),
        (64, b'*'),
        (65, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Echo the **first** successful byte with two loader-authentic crazy writes.
///
/// Five real M95 rotations precede the one signed `/` at C37. C42 uses
/// source C67=67 to select D=M68. Six genuine `j` operations at C43..C48
/// traverse source-authenticated pointer words M68=65, M66=68, M69=64,
/// M65=69, M70=63, M64=70, ending at D=M71. The unvisited graphical source
/// words M71=M72=121 are both valid at their own instruction phases.
/// C49 and C50 physically execute `p` on these words, applying the same
/// ternary involution twice; C51 emits the resulting accumulator and C52
/// halts. The input is not substituted or precomputed by the compiler.
///
/// All 256 finite byte inputs echo exactly. At real signed EOF the guest
/// emits 0xae (174), **not** the C23 conversion byte 0xff; that is deliberate
/// evidence that this is neither a signed C23 `getchar` conversion nor a
/// stateful EOF-loop/C checksum. No source-C output is published.
///
/// # Errors
///
/// Rejects noncanonical profile and source-invalid cells. This candidate
/// must be replayed by the normative VM to prove its physical writes/output.
pub fn build_c23_first_input_two_crazy_byte_echo_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source = build_c23_first_input_lossless_store_source(profile)?;
    // The values are BOTH data pointers and valid graphical source cells.
    // Every patched source position is beyond the last executed C52 cell.
    for (position, byte) in [
        (64, 70u8),
        (65, 69),
        (66, 68),
        (67, 67),
        (68, 65),
        (69, 64),
        (70, 63),
        (71, 121),
        (72, 121),
    ] {
        *source.get_mut(position).ok_or(
            C23OperandProbeSourceError::InvalidPosition { position },
        )? = byte;
    }
    for position in 43..=48 {
        set(&mut source, position, b'j')?;
    }
    for (position, opcode) in [
        (49, b'p'),
        (50, b'p'),
        (51, profile.output_instruction()),
        (52, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Convert and emit the second signed input, then fold it into guest state.
///
/// The genuine C66 input and C77/C78 crazy operations leave the fully
/// converted word in M96. C79 emits its correct C23 low byte, while a new
/// reached C80 `p` writes `crazy(M98, converted)` into M98 before the fixed
/// C81 halt. C80's data pointer is M98, whose seed is the lossy 157
/// loader word. M98 loses byte identity but still separates true EOF from
/// every byte by trit six; M96 preserves exact bytes 0..255 versus encoded
/// EOF=62,207. Neither word is a full C23 signed 32-bit result.
/// This physical continuation does not realize source-C 32-bit arithmetic,
/// signed EOF control, a mutable local, or the whole checksum.
///
/// # Errors
///
/// Rejects other profiles or a missing graphical encoding. The returned
/// source must still pass the normative guest trace and byte+EOF controls.
pub fn build_c23_signed_output_with_post_conversion_fold_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source = build_c23_nine_rotated_signed_output_source(profile)?;
    set(&mut source, 80, b'p')?;
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Preserve a live signed input across a physical output and C23 conversion.
///
/// The second actual guest `/` at C69 reads a signed byte or target EOF.
/// C74 emits its *raw* low byte before C79/C80 perform the two correct
/// C23 `p` conversions against M95/M96. This output does not represent the
/// converted result: at EOF it is the N15 sentinel's low byte, not 0xff.
/// C81 still halts without emitting the final converted accumulator, and the
/// earlier C37 `/` still consumes an input attempt. No C source is compiled.
///
/// This candidate tests whether guest I/O can checkpoint an accumulator
/// without clobbering the subsequent source-authentic conversion path.
/// The exact code/data trace still requires independent normative admission.
///
/// # Errors
///
/// Refuses other profiles, missing source encodings and invalid graphical
/// source. It never publishes a source-C artifact.
pub fn build_c23_nine_rotated_input_checkpoint_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source =
        build_c23_nine_rotated_signed_conversion_without_output_source(
            profile,
        )?;
    // Original C74 is a no-op whose data pointer is M86; changing it to
    // output leaves A and D intact for C75..C80's exact pointer chain.
    set(&mut source, 74, profile.output_instruction())?;
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Bypass the frozen C81 pointer/halt cell using a real indirect guest jump.
///
/// The nine Iy rotations and C37/C69 signed input attempts remain unchanged.
/// After C78 resets D to M80, the C79 `i` reads M80=82 and enters C83,
/// encrypting *M82* rather than C79 before the following `o` executes.
/// C84 then halts cleanly without reading again, output or C23 conversion.
/// This is a physical code-pointer relocation probe, not a C translator.
///
/// # Errors
///
/// Refuses unsupported profiles and loader-invalid source cells. VM replay
/// is still required to establish the indirect self-encryption transition.
pub fn build_c23_nine_rotated_indirect_halt_probe_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source =
        build_c23_nine_rotated_signed_conversion_without_output_source(
            profile,
        )?;
    for (position, opcode) in [
        (74, b'o'),
        (75, b'j'),
        (76, b'j'),
        (77, b'o'),
        (78, b'j'),
        (79, b'i'),
        (83, b'o'),
        (84, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    // C78 j reads M83=79, and C79 i reads M80=82. The latter
    // intentionally encrypts M82=80 to 66, a state change any later
    // data-pointer routing must account for.
    *source.get_mut(80).ok_or(
        C23OperandProbeSourceError::InvalidPosition { position: 80 },
    )? = 82;
    *source.get_mut(82).ok_or(
        C23OperandProbeSourceError::InvalidPosition { position: 82 },
    )? = 80;
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}

/// Execute an input-dependent guest crazy write *after* the C81 bypass.
///
/// The source preserves all nine rotations and both signed guest input
/// attempts. C79 indirectly enters C83, encrypting the skipped M82 from
/// 80 to 66. C84 follows that encrypted word to D=67; C85 applies `p`
/// to the earlier encrypted M67=85, and C86 emits the result's low byte.
/// C87 is source-fixed to `p` by the earlier M87=69 pointer read, so its
/// separate write occurs *after* output. C88 then halts in 86 VM steps.
///
/// This demonstrates a real live-input arithmetic/output continuation
/// across an indirect code transfer. The operands are **85 and 123**,
/// not the C23 signed converter's 7,138,732 and 121, and the EOF byte
/// is not C23 `0xff`. It is not source-C compilation or a checksum.
///
/// # Errors
///
/// Rejects unsupported profiles or absent graphical source opcodes. The
/// normative VM must still verify the real output and write sequence.
pub fn build_c23_nine_rotated_indirect_crazy_output_source(
    profile: &ProfileDescriptor,
) -> Result<Vec<u8>, C23OperandProbeSourceError> {
    let mut source =
        build_c23_nine_rotated_indirect_halt_probe_source(profile)?;
    for (position, opcode) in [
        (84, b'j'),
        (85, b'p'),
        (86, profile.output_instruction()),
        (88, b'v'),
    ] {
        set(&mut source, position, opcode)?;
    }
    // M87 must remain 69: C75 reads it to reach the subsequent C79 `i`.
    admit_c23_probe_graphical_source(&source)?;
    Ok(source)
}
