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
//   - Finite position-sensitive indirect-leaf placement and source-rederived
//     physical N15 guest execution of the proposed leaf.
// - Must-Not:
//   - Infer a jump from code placement, claim a whole source-C branch or loop,
//     or substitute host calculations for guest-executed effects.
// - Allows:
//   - Inputs: source-locked pointer, protected cells, suffix and finite stdin.
//   - Outputs: graphical candidate or exact reached guest trace observations.
//   - Side effects: isolated bounded normative VM execution in proof mode.
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
//! The separate physical verifier re-derives a candidate from its original
//! source, then checks a finite normative VM trace including pointer read,
//! actual landing, leaf opcodes and halt. Source-C semantics, general CFG
//! linkage and unbounded input behavior remain independent obligations.

use malbolge::{
    ProfileDescriptor, ProfileMachine, RunOutcome, Termination,
    current_profile, decode_profile_instruction,
};

use super::admit_c23_probe_graphical_source;

const MAX_SOURCE_CELLS: usize = 4096;
const MAX_SUFFIX_CELLS: usize = 32;
const LOADABLE_OPCODES: &[u8] = b"ji*p</ov";

/// Maximum normative transitions admitted by one physical suffix check.
pub const MAX_INDIRECT_SUFFIX_PROOF_STEPS: usize = 4096;
/// Maximum explicit stdin bytes accepted by a finite suffix check.
pub const MAX_INDIRECT_SUFFIX_PROOF_INPUT: usize = 4096;

/// Why a finite indirect source suffix cannot be placed as requested.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IndirectSourceSuffixError {
    /// The pointer site, landing window or protected positions are invalid.
    InvalidPlacement,
    /// The source is malformed or exceeds this bounded candidate study.
    InvalidSource,
    /// Only a bounded linear leaf ending in a halt or indirect transfer is
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

/// Why a physical execution does not establish the requested indirect leaf.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum IndirectSourceSuffixGuestError {
    /// Original source, source identity or protected cells do not re-plan.
    CandidateMismatch,
    /// Source/output/input/step geometry is outside this finite proof bound.
    InvalidBound,
    /// The source is not an executable, normally halting N15 guest.
    InvalidGuestExecution,
    /// The reached indirect instruction did not read the authentic pointer.
    InvalidIndirectTransfer,
    /// The suffix did not execute at the exact promised code cells/opcodes.
    InvalidSuffixExecution,
    /// The expected first indirect instruction never executed exactly once.
    MissingIndirectTransfer,
    /// The proposed suffix was entered before the authenticated jump.
    PrematureSuffixExecution,
    /// The suffix was executed again after its first completed visit.
    RepeatedSuffixExecution,
}

/// Source and physical execution obligations for one planned indirect leaf.
///
/// `original` is the pre-patch graphical source. Reconstructing the exact
/// candidate from it prevents a forged plan from borrowing a genuine VM run.
/// The caller supplies the *actual* source `i` site, not an assumed jump.
#[derive(Clone, Copy, Debug)]
pub struct IndirectSourceSuffixGuestProbe<'source> {
    /// Untrusted proposed placement and exact candidate source bytes.
    pub candidate: &'source IndirectSourceSuffixPlan,
    /// Exact source address expected to execute the indirect instruction.
    pub indirect_code_cell: u32,
    /// The complete finite guest input, never compiler-precomputed output.
    pub input: &'source [u8],
    /// Source from which the pointer and suffix were prepared.
    pub original: &'source [u8],
    /// Data pointer target which the indirect instruction must read.
    pub pointer_cell: usize,
    /// Source cells whose original bytes must be preserved by placement.
    pub protected: &'source [usize],
    /// Positive upper bound on real guest instructions, including termination.
    pub step_budget: usize,
    /// Exact linear suffix opcodes, including its terminal `v` or `i`.
    pub suffix: &'source [u8],
}

/// Actual guest evidence from one completed, source-identical indirect leaf.
///
/// This proves only one finite input, one source and one leaf execution; it
/// does not prove unbounded C CFG control, signed EOF conversion or arithmetic.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct IndirectSourceSuffixGuestProof {
    /// Number of bytes consumed by actual guest input instructions.
    pub input_consumed: usize,
    /// Exact bytes emitted by the normative guest, not a host C projection.
    pub output: Vec<u8>,
    /// Next code address selected by a terminal `i`, if that leaf has one.
    pub return_address: Option<u32>,
    /// Number of completed transitions through the final guest halt.
    pub steps: usize,
    /// VM transition index of the genuine `i` that enters the suffix.
    pub transfer_step: usize,
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
/// window. All `protected` cells stay **byte-for-byte unchanged**, including
/// any protected cell inside the suffix: such an overlap is allowed only if
/// the original byte already decodes to the requested opcode. The caller must
/// list all dynamically read/written source cells and already-reached code.
/// `landing_from..=landing_through` is a finite, nonempty code window.
/// The leaf may use linear `o`, `/`, `<`, `j`, `p`, `*`, followed by
/// exactly one final `v` or `i`. A terminal `i` is an actual control
/// transfer, not an assumed halt: the caller must separately prove its
/// reached operand, destination, any replayed encrypted code, and eventual
/// termination on every admitted input. Data-pointer moves and writes have
/// no source-time correctness claim; normative VM traces prove their effects.
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
        || !suffix
            .last()
            .is_some_and(|opcode| *opcode == b'v' || *opcode == b'i')
        || !suffix[..suffix.len() - 1].iter().all(|opcode| {
            matches!(opcode, b'o' | b'/' | b'<' | b'j' | b'p' | b'*')
        })
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
        let mut patched = source.to_vec();
        patched[pointer_cell] = pointer_word;
        let mut encodable = true;
        let mut missing_encoding = false;
        for (offset, opcode) in suffix.iter().copied().enumerate() {
            let position = landing + offset;
            let is_protected = protected.contains(&position);
            if is_protected
                && decode_profile_instruction(
                    u32::from(source[position]),
                    u32::try_from(position).unwrap_or(u32::MAX),
                ) != Some(opcode)
            {
                encodable = false;
                break;
            }
            if is_protected {
                continue;
            }
            let Some(graphical) = (33..=126u8).find(|byte| {
                decode_profile_instruction(
                    u32::from(*byte),
                    u32::try_from(position).unwrap_or(u32::MAX),
                ) == Some(opcode)
            }) else {
                encodable = false;
                missing_encoding = true;
                break;
            };
            patched[position] = graphical;
        }
        if !encodable {
            if missing_encoding {
                return Err(MissingGraphicalEncoding);
            }
            continue;
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

/// Execute and verify one source-planned indirect guest suffix in the real VM.
///
/// First reconstruct the *same* planned byte image from the pre-patch source,
/// including its graphical pointer, protected cells and requested suffix. A
/// completed normative N15 trace must then show the named `i` reading that
/// unchanged operand, landing at the promised first code cell, executing all
/// suffix opcodes in source order, and eventually halting by real `v`. A
/// terminal suffix `i` may return to earlier encrypted code; that return is
/// included in the VM run and its actual destination is reported. The entry
/// and suffix must each be reached exactly once in this bounded witness.
///
/// This is a finite **physical code** admission gate only. Its observed
/// output and input consumption are evidence for callers to compare with an
/// independent source-C oracle; no guest artifact is published here.
///
/// # Errors
///
/// Refuses re-planning drift, a missing/wrong physical operand or target,
/// hidden earlier/repeated suffix visits, mismatched actual decoded code,
/// nonhalt, invalid source, and exceeded execution or input bounds.
#[expect(
    clippy::too_many_lines,
    reason = "exact re-planned source and one finite normative transition audit"
)]
pub fn verify_source_loaded_indirect_suffix_guest(
    profile: &ProfileDescriptor,
    probe: IndirectSourceSuffixGuestProbe<'_>,
) -> Result<IndirectSourceSuffixGuestProof, IndirectSourceSuffixGuestError> {
    use IndirectSourceSuffixGuestError::{
        CandidateMismatch, InvalidBound, InvalidGuestExecution,
        InvalidIndirectTransfer, InvalidSuffixExecution,
        MissingIndirectTransfer, PrematureSuffixExecution,
        RepeatedSuffixExecution,
    };
    if probe.step_budget == 0
        || probe.step_budget > MAX_INDIRECT_SUFFIX_PROOF_STEPS
        || probe.input.len() > MAX_INDIRECT_SUFFIX_PROOF_INPUT
        || usize::try_from(probe.indirect_code_cell)
            .map_or(true, |site| site >= probe.original.len())
    {
        return Err(InvalidBound);
    }
    let landing = usize::try_from(probe.candidate.landing_address)
        .map_err(|_error| InvalidBound)?;
    let rebuilt = plan_source_loaded_indirect_suffix(
        profile,
        probe.original,
        probe.pointer_cell,
        landing,
        landing,
        probe.suffix,
        probe.protected,
    )
    .map_err(|_error| CandidateMismatch)?;
    if rebuilt != *probe.candidate {
        return Err(CandidateMismatch);
    }
    // The re-planner already proved this is exactly current_profile().
    let mut vm = ProfileMachine::from_source(
        current_profile(),
        &probe.candidate.source,
        probe.input.to_vec(),
    )
    .map_err(|_error| InvalidGuestExecution)?;
    let mut trace = Vec::new();
    let outcome = vm
        .run_traced(probe.step_budget, &mut |step| trace.push(*step))
        .map_err(|_error| InvalidGuestExecution)?;
    let RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps,
    } = outcome
    else {
        return Err(InvalidGuestExecution);
    };
    let transfers = trace
        .iter()
        .enumerate()
        .filter(|(_index, step)| {
            step.before.registers.code_pointer == probe.indirect_code_cell
                && step.decoded == Some(b'i')
        })
        .map(|(index, _step)| index)
        .collect::<Vec<_>>();
    let [transfer_step] = transfers.as_slice() else {
        return Err(MissingIndirectTransfer);
    };
    let transfer = trace.get(*transfer_step).ok_or(InvalidGuestExecution)?;
    if transfer.before.registers.data_pointer
        != u32::try_from(probe.pointer_cell).map_err(|_error| InvalidBound)?
        || transfer
            .memory_reads
            .data
            .map(|read| (read.address, read.value))
            != Some((
                u32::try_from(probe.pointer_cell)
                    .map_err(|_error| InvalidBound)?,
                u32::from(probe.candidate.pointer_word),
            ))
        || transfer.after.registers.code_pointer
            != probe.candidate.landing_address
    {
        return Err(InvalidIndirectTransfer);
    }
    let suffix_end = landing
        .checked_add(probe.suffix.len())
        .ok_or(InvalidBound)?;
    let in_suffix = |step: &malbolge::ProfileStepTrace| {
        let code = usize::try_from(step.before.registers.code_pointer)
            .unwrap_or(usize::MAX);
        (landing..suffix_end).contains(&code)
    };
    if trace
        .get(..*transfer_step)
        .ok_or(InvalidGuestExecution)?
        .iter()
        .any(in_suffix)
    {
        return Err(PrematureSuffixExecution);
    }
    let start = transfer_step.checked_add(1).ok_or(InvalidBound)?;
    let end = start.checked_add(probe.suffix.len()).ok_or(InvalidBound)?;
    let suffix_trace = trace.get(start..end).ok_or(InvalidSuffixExecution)?;
    for (offset, (step, &opcode)) in
        suffix_trace.iter().zip(probe.suffix).enumerate()
    {
        if step.before.registers.code_pointer
            != u32::try_from(landing.checked_add(offset).ok_or(InvalidBound)?)
                .map_err(|_error| InvalidBound)?
            || step.decoded != Some(opcode)
        {
            return Err(InvalidSuffixExecution);
        }
    }
    if trace
        .get(end..)
        .ok_or(InvalidSuffixExecution)?
        .iter()
        .any(in_suffix)
    {
        return Err(RepeatedSuffixExecution);
    }
    let last = suffix_trace.last().ok_or(InvalidSuffixExecution)?;
    let return_address = if probe.suffix.last() == Some(&b'i') {
        let resumed = trace.get(end).ok_or(InvalidSuffixExecution)?;
        if resumed.before.registers.code_pointer
            != last.after.registers.code_pointer
        {
            return Err(InvalidSuffixExecution);
        }
        Some(last.after.registers.code_pointer)
    } else {
        if end != trace.len() {
            return Err(InvalidSuffixExecution);
        }
        None
    };
    Ok(IndirectSourceSuffixGuestProof {
        input_consumed: vm.input_consumed(),
        output: vm.output().to_vec(),
        return_address,
        steps,
        transfer_step: *transfer_step,
    })
}
