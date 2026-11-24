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

use std::collections::{BTreeMap, BTreeSet};

use malbolge::{
    ProfileDescriptor, ProfileMachine, ProfileStepTrace, RunOutcome,
    Termination, current_profile, decode_profile_instruction,
};

use super::admit_c23_probe_graphical_source;
use super::source_input_trace::{
    SourceBranchLanding, SourceInputPrefixProof, SourceInputProbe,
    SourceInputTraceError, verify_source_branch_io_landing,
    verify_source_branch_landing,
};
use super::typed_cfg_adapter::state_relocation::{
    GuestCodeOperationAnchor, GuestCodeProposals,
};

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
    input_consumed: usize,
    output: Vec<u8>,
    return_address: Option<u32>,
    steps: usize,
    transfer_step: usize,
    trace: Vec<ProfileStepTrace>,
}

impl IndirectSourceSuffixGuestProof {
    /// Number of bytes consumed by actual guest input instructions.
    #[must_use]
    pub const fn input_consumed(&self) -> usize {
        self.input_consumed
    }

    /// Exact bytes emitted by the normative guest, not a host C projection.
    #[must_use]
    pub fn output(&self) -> &[u8] {
        &self.output
    }

    /// Next code address selected by a terminal `i`, if that leaf has one.
    #[must_use]
    pub const fn return_address(&self) -> Option<u32> {
        self.return_address
    }

    /// Number of completed transitions through the final guest halt.
    #[must_use]
    pub const fn steps(&self) -> usize {
        self.steps
    }

    /// VM transition index of the genuine `i` that enters the suffix.
    #[must_use]
    pub const fn transfer_step(&self) -> usize {
        self.transfer_step
    }

    /// Every normative transition, including prefix writes, actual indirect
    /// reads, suffix state changes, encrypted-code return, and the real halt.
    /// This finite, input-specific evidence is not a source-C oracle.
    #[must_use]
    pub fn trace(&self) -> &[ProfileStepTrace] {
        &self.trace
    }
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

/// One untrusted, source-loaded, *guest-written* indirect-control witness.
///
/// Unlike a source-resident suffix pointer, `pointer_cell` may be in
/// loader-expanded memory. The pointer must be derived through real guest
/// data writes after an input instruction, not a constant placed by the host.
/// The allowed destinations are finite physical sites, not source-C branches.
#[derive(Clone, Copy, Debug)]
pub struct SourceWrittenIndirectGuestProbe<'source> {
    /// Explicit finite set of permitted actual successor code addresses.
    pub allowed_landings: &'source [u32],
    /// Exactly one reached `i` at this code site must select the destination.
    pub indirect_code_cell: u32,
    /// Complete finite input stream; EOF is represented by exhaustion.
    pub input: &'source [u8],
    /// Guest-memory address that the reached `i` must read.
    pub pointer_cell: u32,
    /// Complete graphical source used by the normative loader.
    pub source: &'source [u8],
    /// Positive finite bound on the normative run, including the real halt.
    pub step_budget: usize,
}

/// Why a guest-written, input-derived branch cannot be authenticated.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SourceWrittenIndirectGuestError {
    /// Source, input, target geometry or finite budgets are invalid.
    InvalidBound,
    /// The actual VM failed, stopped prematurely or did not genuinely halt.
    InvalidGuestExecution,
    /// The reached instruction read a different data cell or jumped wrongly.
    InvalidIndirectTransfer,
    /// No graphical, loader-admitted N15 source was supplied.
    InvalidSource,
    /// No earlier guest `p` or `*` wrote the live pointer cell.
    MissingGuestPointerWrite,
    /// No reached indirect instruction exists at the nominated code site.
    MissingIndirectTransfer,
    /// The pointer lacks a conservative data path from an actual input read.
    MissingInputProvenance,
    /// No pointer lineage originates at the caller-required guest input site.
    MissingRequiredInputProvenance,
    /// The nominated code site executed `i` more than once.
    RepeatedIndirectTransfer,
    /// The guest-computed destination is not in the declared finite set.
    UnexpectedLanding,
}

/// Opaque finite normative proof of a guest-written indirect control transfer.
///
/// The source and stdin remain attached to the proof so it cannot be used as
/// an unqualified success token for another binary or input. Input provenance
/// is a necessary physical dataflow condition, **not** source-C branch truth.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceWrittenIndirectGuestProof {
    input: Vec<u8>,
    input_consumed: usize,
    landing_address: u32,
    output: Vec<u8>,
    pointer_input_steps: Vec<usize>,
    pointer_word: u32,
    pointer_write_step: usize,
    source: Vec<u8>,
    steps: usize,
    trace: Vec<ProfileStepTrace>,
    transfer_step: usize,
}

impl SourceWrittenIndirectGuestProof {
    /// Exact finite input authenticated by the normative run.
    #[must_use]
    pub fn input(&self) -> &[u8] {
        &self.input
    }

    /// Actual count of bytes consumed by reached input instructions.
    #[must_use]
    pub const fn input_consumed(&self) -> usize {
        self.input_consumed
    }

    /// Actual first code address after the source-nominated `i`.
    #[must_use]
    pub const fn landing_address(&self) -> u32 {
        self.landing_address
    }

    /// Actual guest output, not a simulated source-C result.
    #[must_use]
    pub fn output(&self) -> &[u8] {
        &self.output
    }

    /// Trace indices of genuine guest input instructions with a physical
    /// dataflow path to the final indirect-pointer word. Includes EOF reads.
    /// This conservative lineage is not a proof of source-C branch truth.
    #[must_use]
    pub fn pointer_input_steps(&self) -> &[usize] {
        &self.pointer_input_steps
    }

    /// Full-width word actually read by the reached indirect instruction.
    #[must_use]
    pub const fn pointer_word(&self) -> u32 {
        self.pointer_word
    }

    /// Index of the latest reached p/* write, including idempotent writes.
    #[must_use]
    pub const fn pointer_write_step(&self) -> usize {
        self.pointer_write_step
    }

    /// Exact original graphical source authenticated by the normative loader.
    #[must_use]
    pub fn source(&self) -> &[u8] {
        &self.source
    }

    /// Complete normative transition count, including real `v` halt.
    #[must_use]
    pub const fn steps(&self) -> usize {
        self.steps
    }

    /// Exact reached physical code, data, encryption, register and I/O events.
    #[must_use]
    pub fn trace(&self) -> &[ProfileStepTrace] {
        &self.trace
    }

    /// Index of the single authenticated indirect instruction.
    #[must_use]
    pub const fn transfer_step(&self) -> usize {
        self.transfer_step
    }
}

/// One finite authenticated guest-written indirect execution result.
///
/// A concrete alias keeps the public verifier signature within the pinned
/// 80-column Rust formatter profile without hiding its explicit error type.
pub type SourceWrittenIndirectGuestResult =
    Result<SourceWrittenIndirectGuestProof, SourceWrittenIndirectGuestError>;

/// Canonical source-C input operation proposed to feed a physical pointer.
///
/// This identifies a typed source operation, not a guest source address.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct SourceInputPointerOrigin {
    /// Canonical source basic block containing the input operation.
    pub block: u32,
    /// Canonical function containing the input operation.
    pub function: u32,
    /// Original instruction ordinal within that source block.
    pub ordinal: u32,
}

/// Require a source-authenticated input effect to feed a physical guest `i`.
///
/// The source operation identity and physical input address are independently
/// checked using the existing typed input trace verifier and normative VM.
/// This is only a necessary source-to-physical dataflow condition, not C
/// predicate, arithmetic, state, edge or loop equivalence.
#[derive(Clone, Copy, Debug)]
pub struct SourceBoundIndirectGuestProbe<'source> {
    /// Allowed physical successors after the authentic `i`.
    pub allowed_landings: &'source [u32],
    /// Reached physical instruction that must execute `i` exactly once.
    pub indirect_code_cell: u32,
    /// Canonical source operation anchors for the input trace checker.
    pub operation_anchors: &'source [GuestCodeOperationAnchor],
    /// Source-authenticated operations whose inputs must feed the pointer.
    pub origins: &'source [SourceInputPointerOrigin],
    /// Guest data word from which the reached `i` must read its operand.
    pub pointer_cell: u32,
    /// Source CFG physical-placement proposals, not guest code evidence.
    pub proposals: GuestCodeProposals<'source>,
    /// Independent source input trace obligation on the identical binary.
    pub source_input: SourceInputProbe<'source>,
}

/// Why source-typed `getchar` ancestry and a reached guest pointer disagree.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SourceBoundIndirectGuestError {
    /// The source-bound input and guest pointer use different source images.
    SourceMismatch,
    /// No source operation was requested or its identities were duplicated.
    InvalidOriginSelection,
    /// A required typed source operation did not execute a matching input.
    MissingSourceInputOrigin,
    /// Source-typed input sites, CFG prefix or physical input did not validate.
    SourceInput(SourceInputTraceError),
    /// Guest-written pointer, reached indirect control or lineage is invalid.
    GuestPointer(SourceWrittenIndirectGuestError),
    /// Two independent normative VM replays do not describe the same run.
    InconsistentGuestTrace,
    /// The reached guest transfer crosses an extra physical input read.
    OutOfOrderGuestBranch,
}

/// Opaque joined proof of source-identified inputs and a guest-written branch.
///
/// The verifier owns both executions; a caller cannot inject a mutable,
/// fabricated source-input proof to authenticate a different guest pointer.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceBoundIndirectGuestProof {
    source_input: SourceInputPrefixProof,
    guest_pointer: SourceWrittenIndirectGuestProof,
}

impl SourceBoundIndirectGuestProof {
    /// Real input events authenticated against the canonical source CFG.
    #[must_use]
    pub const fn source_input(&self) -> &SourceInputPrefixProof {
        &self.source_input
    }

    /// Real guest pointer write, input ancestry, transfer and output trace.
    #[must_use]
    pub const fn guest_pointer(&self) -> &SourceWrittenIndirectGuestProof {
        &self.guest_pointer
    }
}

/// Reusable pristine N15 source for a finite guest-written branch corpus.
///
/// Construction authenticates the graphical source *once*, including its
/// full loader expansion. Every `verify` call forks fresh, isolated VM state
/// before input replay; no earlier run can lend its memory or I/O to another.
#[derive(Debug)]
pub struct SourceWrittenIndirectGuestVerifier {
    pristine: ProfileMachine,
    source: Vec<u8>,
}

impl SourceWrittenIndirectGuestVerifier {
    /// Load and authenticate one current-profile graphical source.
    ///
    /// # Errors
    ///
    /// Refuses noncanonical profiles, malformed source or failed VM loading.
    pub fn new(
        profile: &ProfileDescriptor,
        source: &[u8],
    ) -> Result<Self, SourceWrittenIndirectGuestError> {
        use SourceWrittenIndirectGuestError::{
            InvalidGuestExecution, InvalidSource,
        };
        if profile != current_profile()
            || !(2..=MAX_SOURCE_CELLS).contains(&source.len())
            || admit_c23_probe_graphical_source(source).is_err()
        {
            return Err(InvalidSource);
        }
        let pristine =
            ProfileMachine::from_source(current_profile(), source, Vec::new())
                .map_err(|_error| InvalidGuestExecution)?;
        Ok(Self {
            pristine,
            source: source.to_vec(),
        })
    }

    /// Original admitted graphical source shared by all isolated guest runs.
    #[must_use]
    pub fn source(&self) -> &[u8] {
        &self.source
    }

    /// Authenticate one input stream from a fresh copy of this source.
    ///
    /// # Errors
    ///
    /// Refuses invalid budgets, failed guest execution, missing input-derived
    /// pointer writes, and wrong physical indirect successors.
    #[expect(
        clippy::too_many_arguments,
        reason = "independent physical input and transfer geometry"
    )]
    pub fn verify(
        &self,
        input: &[u8],
        indirect_code_cell: u32,
        pointer_cell: u32,
        allowed_landings: &[u32],
        step_budget: usize,
    ) -> SourceWrittenIndirectGuestResult {
        if input.len() > MAX_INDIRECT_SUFFIX_PROOF_INPUT
            || step_budget == 0
            || step_budget > MAX_INDIRECT_SUFFIX_PROOF_STEPS
            || usize::try_from(indirect_code_cell)
                .map_or(true, |site| site >= self.source.len())
            || pointer_cell >= current_profile().memory_words()
            || allowed_landings.is_empty()
            || allowed_landings.len() > 8
            || allowed_landings
                .iter()
                .any(|site| *site >= current_profile().memory_words())
        {
            return Err(SourceWrittenIndirectGuestError::InvalidBound);
        }
        let vm = self.pristine.fork_with_input(input.to_vec()).map_err(
            |_error| SourceWrittenIndirectGuestError::InvalidGuestExecution,
        )?;
        verify_source_written_indirect_with_machine(
            current_profile(),
            SourceWrittenIndirectGuestProbe {
                allowed_landings,
                indirect_code_cell,
                input,
                pointer_cell,
                source: &self.source,
                step_budget,
            },
            vm,
        )
    }

    /// Require the entire input ancestry of a physical `i` pointer to come
    /// from specifically authenticated canonical C source input operations.
    ///
    /// The source-input verifier checks every reached `/` against its typed
    /// C operation and source CFG prefix, while the separate guest verifier
    /// proves the actual pointer write and selected `i` successor. Both
    /// execute the *same source bytes and input* independently and must agree
    /// on the halted trace and output. Extra or skipped source reads may be
    /// valid but cannot be silently credited as pointer ancestors.
    /// This never claims C predicate truth, arithmetic, phi or loop linkage.
    ///
    /// # Errors
    ///
    /// Rejects forged source operation identities, mismatched guest images,
    /// source input failures, missing pointer origin and divergent VM replay.
    pub fn verify_source_bound(
        &self,
        probe: &SourceBoundIndirectGuestProbe<'_>,
    ) -> Result<SourceBoundIndirectGuestProof, SourceBoundIndirectGuestError>
    {
        self.verify_source_bound_with_return(probe, false)
    }

    /// Additionally require a complete source-CFG return path after the
    /// source-typed physical input events feeding a reached guest pointer.
    ///
    /// This refuses a real guest that halts after reading only a valid
    /// prefix of the C EOF loop. It still does not prove source values,
    /// guest arithmetic, physical branch-predicate parity or source output.
    ///
    /// # Errors
    ///
    /// Refuses every source-bound failure, including a source path that
    /// cannot return after exactly the physical guest input observations.
    pub fn verify_source_return_bound(
        &self,
        probe: &SourceBoundIndirectGuestProbe<'_>,
    ) -> Result<SourceBoundIndirectGuestProof, SourceBoundIndirectGuestError>
    {
        self.verify_source_bound_with_return(probe, true)
    }

    /// Bind one known source-C conditional to the actually selected guest
    /// indirect destination, following an exact source input/return path.
    ///
    /// The typed source predicate is recomputed only from source-known scalar
    /// operations in the same finite CFG walk as the real input sequence.
    /// Unknown or conflicting return paths refuse. Pointer input ancestry,
    /// the source return path and the physical guest transition are verified
    /// separately before comparing arms. This does not prove that the guest
    /// computed the typed predicate or executed the other source operations.
    ///
    /// # Errors
    ///
    /// Refuses invalid branch identity, source-unknown predicate, incorrect
    /// physical arm, or any source-return or guest pointer proof failure.
    pub fn verify_source_return_branch_bound(
        &self,
        probe: &SourceBoundIndirectGuestProbe<'_>,
        branch: SourceBranchLanding,
    ) -> Result<SourceBoundIndirectGuestProof, SourceBoundIndirectGuestError>
    {
        let joined = self.verify_source_return_bound(probe)?;
        verify_source_branch_landing(
            probe.source_input.canonical,
            &joined.source_input.observations,
            branch,
            joined.guest_pointer.landing_address(),
        )
        .map_err(SourceBoundIndirectGuestError::SourceInput)?;
        Ok(joined)
    }

    /// Additionally place the actual guest `i` **between** the input reads
    /// before and after the nominated source conditional.
    ///
    /// The direction-only binding above deliberately does not infer guest
    /// execution ordering. For a branch after `N` source input operations,
    /// exactly `N` authenticated `/` transitions must precede the physical
    /// indirect transfer. A later read before the guest branch fails even
    /// when its pointer selects the direction predicted by source C. This is
    /// necessary physical input/control ordering, not proof that the guest
    /// computes the signed predicate or implements the full source CFG.
    ///
    /// # Errors
    ///
    /// Refuses the direction/source-return verifier's failures, or a reached
    /// physical `i` separated from its source branch by another input read.
    pub fn verify_source_return_branch_ordered(
        &self,
        probe: &SourceBoundIndirectGuestProbe<'_>,
        branch: SourceBranchLanding,
    ) -> Result<SourceBoundIndirectGuestProof, SourceBoundIndirectGuestError>
    {
        let joined = self.verify_source_return_branch_bound(probe, branch)?;
        let read_count = source_read_count_before_guest_transfer(
            joined
                .source_input
                .observations
                .iter()
                .map(|read| read.trace_index),
            joined.guest_pointer.transfer_step(),
        );
        if read_count != branch.after_inputs {
            return Err(SourceBoundIndirectGuestError::OutOfOrderGuestBranch);
        }
        Ok(joined)
    }

    /// Require the source-known conditional *and* the actual complete I/O
    /// stream to coexist on one bounded source-C return path, alongside the
    /// reached guest pointer and its input/control chronology.
    ///
    /// The previous ordered method intentionally admits prefix experiments
    /// whose marker output is unrelated to the C program. This stricter
    /// verifier cannot: source-known output values and effect order must
    /// agree with the very same path that selects the physical branch arm.
    /// It still does not prove full-width guest locals or source arithmetic
    /// was executed by the target, and it must not publish a program alone.
    ///
    /// # Errors
    ///
    /// Refuses each source/guest direction and chronology failure, plus
    /// unknown, reordered or mismatched source-visible output effects.
    pub fn verify_source_return_branch_io_ordered(
        &self,
        probe: &SourceBoundIndirectGuestProbe<'_>,
        branch: SourceBranchLanding,
    ) -> Result<SourceBoundIndirectGuestProof, SourceBoundIndirectGuestError>
    {
        let joined = self.verify_source_return_branch_ordered(probe, branch)?;
        verify_source_branch_io_landing(
            probe.source_input.canonical,
            &joined.source_input,
            branch,
            joined.guest_pointer.landing_address(),
        )
        .map_err(SourceBoundIndirectGuestError::SourceInput)?;
        Ok(joined)
    }

    #[expect(
        clippy::too_many_lines,
        reason = "source and guest checks retain both complete trace receipts"
    )]
    fn verify_source_bound_with_return(
        &self,
        probe: &SourceBoundIndirectGuestProbe<'_>,
        require_source_return: bool,
    ) -> Result<SourceBoundIndirectGuestProof, SourceBoundIndirectGuestError>
    {
        use SourceBoundIndirectGuestError::{
            GuestPointer, InconsistentGuestTrace, InvalidOriginSelection,
            MissingSourceInputOrigin, SourceInput, SourceMismatch,
        };
        if probe.source_input.physical_source != self.source {
            return Err(SourceMismatch);
        }
        let expected = probe.origins.iter().copied().collect::<BTreeSet<_>>();
        if expected.is_empty()
            || expected.len() != probe.origins.len()
            || expected.len() > MAX_INDIRECT_SUFFIX_PROOF_STEPS
        {
            return Err(InvalidOriginSelection);
        }
        let source_input = if require_source_return {
            probe.source_input.verify_return_with_operation_anchors(
                probe.proposals,
                probe.operation_anchors,
            )
        } else {
            probe.source_input.verify_with_operation_anchors(
                probe.proposals,
                probe.operation_anchors,
            )
        }
        .map_err(SourceInput)?;
        let mut observed = BTreeSet::new();
        let input_transitions = source_input
            .observations
            .iter()
            .filter_map(|input| {
                let identity = SourceInputPointerOrigin {
                    block: input.block,
                    function: input.function,
                    ordinal: input.ordinal,
                };
                expected.contains(&identity).then(|| {
                    let _new = observed.insert(identity);
                    (input.trace_index, input.code_address)
                })
            })
            .collect::<Vec<_>>();
        if observed != expected {
            return Err(MissingSourceInputOrigin);
        }
        let guest_pointer = self
            .verify_from_input_transitions(
                probe.source_input.input,
                &input_transitions,
                probe.indirect_code_cell,
                probe.pointer_cell,
                probe.allowed_landings,
                probe.source_input.step_budget,
            )
            .map_err(GuestPointer)?;
        let RunOutcome::Terminated {
            reason: Termination::HaltInstruction,
            steps,
        } = source_input.outcome
        else {
            return Err(InconsistentGuestTrace);
        };
        if steps != guest_pointer.steps()
            || source_input.bytes_consumed != guest_pointer.input_consumed()
            || source_input.guest_output != guest_pointer.output()
        {
            return Err(InconsistentGuestTrace);
        }
        Ok(SourceBoundIndirectGuestProof {
            source_input,
            guest_pointer,
        })
    }

    /// Prove that precisely one guest input site supplies the branch pointer.
    ///
    /// The site identifies the physical `/` instruction, whether it read a
    /// byte or EOF. Other input sites may execute, but their values cannot
    /// contribute to this pointer. The proof describes *possible physical
    /// dataflow*, not source-C condition equivalence.
    ///
    /// # Errors
    ///
    /// Refuses any physical guest failure or unexpected input ancestry.
    #[expect(
        clippy::too_many_arguments,
        reason = "explicit guest read and indirect branch binding"
    )]
    pub fn verify_from_input_site(
        &self,
        input: &[u8],
        input_code_cell: u32,
        indirect_code_cell: u32,
        pointer_cell: u32,
        allowed_landings: &[u32],
        step_budget: usize,
    ) -> SourceWrittenIndirectGuestResult {
        self.verify_from_input_sites(
            input,
            &[input_code_cell],
            indirect_code_cell,
            pointer_cell,
            allowed_landings,
            step_budget,
        )
    }

    /// Prove the complete set of physical input sites feeding a guest pointer.
    ///
    /// This accepts a nonempty, duplicate-free set of code addresses and
    /// requires it to equal the sites of *all* input transitions that can
    /// flow into the final `i` operand. The proof keeps every contributing
    /// trace index, so a future CFG verifier can distinguish loop iterations
    /// at one source site. The source-C predicate and loop remain unproven.
    ///
    /// # Errors
    ///
    /// Refuses invalid read-site sets, any physical guest failure, and
    /// missing or extraneous guest input origins.
    #[expect(
        clippy::too_many_arguments,
        reason = "source input-site set and independent guest transfer geometry"
    )]
    pub fn verify_from_input_sites(
        &self,
        input: &[u8],
        input_code_cells: &[u32],
        indirect_code_cell: u32,
        pointer_cell: u32,
        allowed_landings: &[u32],
        step_budget: usize,
    ) -> SourceWrittenIndirectGuestResult {
        use SourceWrittenIndirectGuestError::{
            InvalidBound, MissingRequiredInputProvenance,
        };
        let expected =
            input_code_cells.iter().copied().collect::<BTreeSet<_>>();
        if expected.is_empty()
            || expected.len() != input_code_cells.len()
            || expected.len() > MAX_INDIRECT_SUFFIX_PROOF_STEPS
            || expected.iter().any(|code_address| {
                *code_address >= current_profile().memory_words()
            })
        {
            return Err(InvalidBound);
        }
        let proof = self.verify(
            input,
            indirect_code_cell,
            pointer_cell,
            allowed_landings,
            step_budget,
        )?;
        let observed = authenticated_pointer_input_origins(&proof)?
            .into_iter()
            .map(|(_index, code_address)| code_address)
            .collect::<BTreeSet<_>>();
        if observed != expected {
            return Err(MissingRequiredInputProvenance);
        }
        Ok(proof)
    }

    /// Bind the complete pointer ancestry to exact guest input transitions.
    ///
    /// Each `(trace_index, code_cell)` pair must identify an actual reached
    /// `/`, including reads that observe EOF. Unlike address-only site sets,
    /// this distinguishes repeated reads at one code site across loop trips.
    /// This finite physical proof does not authenticate source-C loop counts
    /// or condition equivalence; a CFG verifier must provide those separately.
    ///
    /// # Errors
    ///
    /// Refuses duplicate/out-of-bound claims, failed guest execution, and
    /// missing or unexpected input transition origins for the final pointer.
    #[expect(
        clippy::too_many_arguments,
        reason = "exact guest transition and physical branch geometry"
    )]
    pub fn verify_from_input_transitions(
        &self,
        input: &[u8],
        input_transitions: &[(usize, u32)],
        indirect_code_cell: u32,
        pointer_cell: u32,
        allowed_landings: &[u32],
        step_budget: usize,
    ) -> SourceWrittenIndirectGuestResult {
        use SourceWrittenIndirectGuestError::{
            InvalidBound, MissingRequiredInputProvenance,
        };
        let expected =
            input_transitions.iter().copied().collect::<BTreeSet<_>>();
        if expected.is_empty()
            || expected.len() != input_transitions.len()
            || expected.len() > step_budget
            || expected.iter().any(|(index, code_cell)| {
                *index >= step_budget
                    || *code_cell >= current_profile().memory_words()
            })
        {
            return Err(InvalidBound);
        }
        let proof = self.verify(
            input,
            indirect_code_cell,
            pointer_cell,
            allowed_landings,
            step_budget,
        )?;
        if authenticated_pointer_input_origins(&proof)? != expected {
            return Err(MissingRequiredInputProvenance);
        }
        Ok(proof)
    }
}

// Count actual normative VM input transitions before (not at or after)
// the nominated indirect instruction. Source block ordinals and physical
// code addresses cannot be substituted for chronological trace indices.
pub(super) fn source_read_count_before_guest_transfer(
    read_steps: impl IntoIterator<Item = usize>,
    transfer_step: usize,
) -> usize {
    read_steps
        .into_iter()
        .filter(|read| *read < transfer_step)
        .count()
}

/// Reconstruct exact physical input transition identities from VM evidence.
/// A boolean taint or a code address alone cannot identify repeated reads.
fn authenticated_pointer_input_origins(
    proof: &SourceWrittenIndirectGuestProof,
) -> Result<BTreeSet<(usize, u32)>, SourceWrittenIndirectGuestError> {
    proof
        .pointer_input_steps()
        .iter()
        .map(|index| {
            proof.trace().get(*index).and_then(|step| {
                (step.decoded == Some(b'/') && step.input.is_some())
                    .then_some((*index, step.before.registers.code_pointer))
            })
        })
        .collect::<Option<BTreeSet<_>>>()
        .ok_or(SourceWrittenIndirectGuestError::InvalidGuestExecution)
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
    // A caller will use every returned observation as a state-transfer
    // witness. Reject incomplete or internally inconsistent trace delivery,
    // even if the VM's aggregate run outcome reports an authentic halt.
    if trace.len() != steps
        || trace.last().is_none_or(|last| {
            last.after.termination != Some(Termination::HaltInstruction)
                || last.after.input_consumed != vm.input_consumed()
                || last.after.output_len != vm.output().len()
        })
    {
        return Err(InvalidGuestExecution);
    }
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
    let in_suffix = |step: &ProfileStepTrace| {
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
        trace,
    })
}

/// Authenticate a real input-dependent, guest-written N15 indirect pointer.
///
/// Source admission and a completed VM halt are checked independently of
/// caller-proposed destinations. At the reached `i`, the full-width operand
/// must come from a prior guest data write with a conservative path back to
/// an executed `/`. All earlier `p`/`*` data writes are tracked by address;
/// an unrelated, numerically equal constant pointer is not sufficient.
/// Exact source-C condition and all-input branch parity remain separate.
///
/// # Errors
///
/// Rejects invalid geometry, nonhalt, absent/repeated transfer, a different
/// physical operand, a constant pointer, missing input dataflow or any landing
/// outside the explicit finite destination set.
pub fn verify_source_written_indirect_guest(
    profile: &ProfileDescriptor,
    probe: SourceWrittenIndirectGuestProbe<'_>,
) -> Result<SourceWrittenIndirectGuestProof, SourceWrittenIndirectGuestError> {
    SourceWrittenIndirectGuestVerifier::new(profile, probe.source)?.verify(
        probe.input,
        probe.indirect_code_cell,
        probe.pointer_cell,
        probe.allowed_landings,
        probe.step_budget,
    )
}

#[expect(
    clippy::too_many_lines,
    reason = "source-authenticated complete normative trace and guest dataflow"
)]
fn verify_source_written_indirect_with_machine(
    profile: &ProfileDescriptor,
    probe: SourceWrittenIndirectGuestProbe<'_>,
    mut vm: ProfileMachine,
) -> Result<SourceWrittenIndirectGuestProof, SourceWrittenIndirectGuestError> {
    use SourceWrittenIndirectGuestError::{
        InvalidBound, InvalidGuestExecution, InvalidIndirectTransfer,
        InvalidSource, MissingGuestPointerWrite, MissingIndirectTransfer,
        MissingInputProvenance, RepeatedIndirectTransfer, UnexpectedLanding,
    };
    if profile != current_profile() {
        return Err(InvalidSource);
    }
    if !(2..=MAX_SOURCE_CELLS).contains(&probe.source.len())
        || admit_c23_probe_graphical_source(probe.source).is_err()
    {
        return Err(InvalidSource);
    }
    if probe.step_budget == 0
        || probe.step_budget > MAX_INDIRECT_SUFFIX_PROOF_STEPS
        || probe.input.len() > MAX_INDIRECT_SUFFIX_PROOF_INPUT
        || usize::try_from(probe.indirect_code_cell)
            .map_or(true, |at| at >= probe.source.len())
        || probe.pointer_cell >= profile.memory_words()
        || probe.allowed_landings.is_empty()
        || probe.allowed_landings.len() > 8
        || probe
            .allowed_landings
            .iter()
            .any(|at| *at >= profile.memory_words())
    {
        return Err(InvalidBound);
    }
    let mut trace = Vec::new();
    let RunOutcome::Terminated {
        reason: Termination::HaltInstruction,
        steps,
    } = vm
        .run_traced(probe.step_budget, &mut |step| trace.push(*step))
        .map_err(|_error| InvalidGuestExecution)?
    else {
        return Err(InvalidGuestExecution);
    };
    if trace.len() != steps
        || trace.last().is_none_or(|last| {
            last.after.termination != Some(Termination::HaltInstruction)
                || last.after.input_consumed != vm.input_consumed()
                || last.after.output_len != vm.output().len()
        })
    {
        return Err(InvalidGuestExecution);
    }
    let mut transfers = trace.iter().enumerate().filter(|(_index, step)| {
        step.before.registers.code_pointer == probe.indirect_code_cell
            && step.decoded == Some(b'i')
    });
    let Some((transfer_step, transfer)) = transfers.next() else {
        return Err(MissingIndirectTransfer);
    };
    if transfers.next().is_some() {
        return Err(RepeatedIndirectTransfer);
    }
    let Some(read) = transfer.memory_reads.data else {
        return Err(InvalidIndirectTransfer);
    };
    let next_code = if read.value == profile.memory_words().saturating_sub(1) {
        0
    } else {
        read.value.saturating_add(1)
    };
    if transfer.before.registers.data_pointer != probe.pointer_cell
        || read.address != probe.pointer_cell
        || transfer.after.registers.code_pointer != next_code
    {
        return Err(InvalidIndirectTransfer);
    }
    if !probe
        .allowed_landings
        .contains(&transfer.after.registers.code_pointer)
    {
        return Err(UnexpectedLanding);
    }

    // A set of actual input-transition indices, rather than a Boolean, lets
    // a source-C linker distinguish the input read that feeds this branch.
    // This is a *possible physical dataflow* claim; exact source-C predicate
    // equivalence remains an independent obligation. The final pointer
    // version must be a reached p/* write, not a loader seed or XLAT2 alone.
    let mut input_lineage_by_word = BTreeMap::<u32, BTreeSet<usize>>::new();
    let mut accumulator_lineage = BTreeSet::<usize>::new();
    let mut last_pointer_write = None;
    for (index, step) in trace.iter().take(transfer_step).enumerate() {
        let address = step.before.registers.data_pointer;
        let data_lineage = input_lineage_by_word
            .get(&address)
            .cloned()
            .unwrap_or_default();
        let next_accumulator_lineage = match step.decoded {
            Some(b'/') if step.input.is_some() => BTreeSet::from([index]),
            Some(b'/') => return Err(InvalidGuestExecution),
            Some(b'p') => {
                accumulator_lineage.union(&data_lineage).copied().collect()
            },
            Some(b'*') => data_lineage,
            _ => accumulator_lineage,
        };
        // The VM reports only *changed-value* memory deltas. An actual
        // p/* writing the same word still counts as a physical write and
        // propagates input lineage even when memory_delta.data is None.
        if matches!(step.decoded, Some(b'p' | b'*')) {
            if step
                .memory_reads
                .data
                .is_none_or(|operand| operand.address != address)
            {
                return Err(InvalidGuestExecution);
            }
            if next_accumulator_lineage.is_empty() {
                let _previous = input_lineage_by_word.remove(&address);
            } else {
                let _previous = input_lineage_by_word
                    .insert(address, next_accumulator_lineage.clone());
            }
            if address == probe.pointer_cell {
                last_pointer_write = Some(index);
            }
        } else if step.memory_delta.data.is_some() {
            return Err(InvalidGuestExecution);
        }
        // XLAT2 preserves mathematical ancestry of a data word but cannot
        // certify that an earlier guest store remains the pointer's *final*
        // write. Refuse an encrypted pointer until a fresh p/* writes it.
        if step
            .memory_delta
            .encryption
            .is_some_and(|effect| effect.address == probe.pointer_cell)
        {
            last_pointer_write = None;
            let _previous = input_lineage_by_word.remove(&probe.pointer_cell);
        }
        accumulator_lineage = next_accumulator_lineage;
    }
    let pointer_write_step =
        last_pointer_write.ok_or(MissingGuestPointerWrite)?;
    let pointer_input_steps = input_lineage_by_word
        .remove(&probe.pointer_cell)
        .filter(|origins| !origins.is_empty())
        .ok_or(MissingInputProvenance)?
        .into_iter()
        .collect();
    Ok(SourceWrittenIndirectGuestProof {
        input: probe.input.to_vec(),
        input_consumed: vm.input_consumed(),
        landing_address: transfer.after.registers.code_pointer,
        output: vm.output().to_vec(),
        pointer_input_steps,
        pointer_word: read.value,
        pointer_write_step,
        source: probe.source.to_vec(),
        steps,
        trace,
        transfer_step,
    })
}
