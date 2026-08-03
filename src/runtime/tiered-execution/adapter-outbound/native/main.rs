// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Bootstrap lowering from portable effect IR to untrusted native artifacts.
// - Must-Not:
//   - Admit machine code, replace verifier lineage guards, or define VM
//   - semantics.
// - Allows:
//   - Inputs: portable region-effect IR and exact native target identity.
//   - Outputs: deterministic C23 and opaque untrusted compiler object bytes.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when direct ISA emitters or native validation gain independent
//   - owners.
// - Merge-When:
//   - Merge when one native backend abstraction owns bootstrap and direct
//   - emitters.
// - Summary:
//   - Produces the first real host-code candidate boundary without trusting it.
// - Description:
//   - Validates IR structure, renders atomic guarded C, and preserves exact
//   - keys.
// - Usage:
//   - Composed by tiered execution tests and future AOT/JIT orchestration.
// - Defaults:
//   - Clang C23 bootstrap artifacts are always untrusted after generation.
//

//! First untrusted native-artifact lowering boundary for portable effect IR.

#[path = "aarch64/main.rs"]
mod aarch64;
mod abi;
mod coff;
mod direct;
mod profile_metadata;
#[path = "x86_64/main.rs"]
mod x86_64;

use std::collections::BTreeMap;
use std::fmt::{Display, Formatter, Result as FormatResult, Write as _};

use abi::C_ABI_PREFIX;
pub use abi::{
    NATIVE_REGION_ACCUMULATOR_OFFSET, NATIVE_REGION_CODE_POINTER_OFFSET,
    NATIVE_REGION_DATA_POINTER_OFFSET, NATIVE_REGION_INPUT_CONSUMED_OFFSET,
    NATIVE_REGION_INPUT_LEN_OFFSET, NATIVE_REGION_INPUT_OFFSET,
    NATIVE_REGION_MEMORY_OFFSET, NATIVE_REGION_MEMORY_WORDS_OFFSET,
    NATIVE_REGION_OUTPUT_CAPACITY_OFFSET, NATIVE_REGION_OUTPUT_LEN_OFFSET,
    NATIVE_REGION_OUTPUT_OFFSET, NATIVE_REGION_STATE_SIZE,
    NATIVE_REGION_TERMINATION_OFFSET, NativeRegionCallFrame,
    NativeRegionCallFrameError, NativeRegionObservationError,
    NativeRegionState, NativeRegionStatus, NativeRegionStatusError,
    NativeTerminationTag, NativeTerminationTagError,
};
pub use coff::{
    CoffAdmissionError, StructurallyAdmittedNativeObjectArtifact,
    structurally_admit_coff,
};
pub use direct::{
    CachedPreflightedExecutionTier, CachedVerifiedDirectSequencePlan,
    DIRECT_CRAZY_BACKEND_ID, DIRECT_CRAZY_BACKEND_REVISION,
    DIRECT_DEOPT_BACKEND_ID, DIRECT_DEOPT_BACKEND_REVISION,
    DIRECT_HALT_FETCH_BACKEND_ID, DIRECT_HALT_FETCH_BACKEND_REVISION,
    DIRECT_HALT_REGISTERS_BACKEND_ID, DIRECT_HALT_REGISTERS_BACKEND_REVISION,
    DIRECT_INITIAL_HALT_BACKEND_ID, DIRECT_INITIAL_HALT_BACKEND_REVISION,
    DIRECT_INPUT_BACKEND_ID, DIRECT_INPUT_BACKEND_REVISION,
    DIRECT_JUMP_CODE_BACKEND_ID, DIRECT_JUMP_CODE_BACKEND_REVISION,
    DIRECT_JUMP_DATA_BACKEND_ID, DIRECT_JUMP_DATA_BACKEND_REVISION,
    DIRECT_NO_OPERATION_BACKEND_ID, DIRECT_NO_OPERATION_BACKEND_REVISION,
    DIRECT_NON_GRAPHICAL_BACKEND_ID, DIRECT_NON_GRAPHICAL_BACKEND_REVISION,
    DIRECT_OUTPUT_BACKEND_ID, DIRECT_OUTPUT_BACKEND_REVISION,
    DIRECT_ROTATE_BACKEND_ID, DIRECT_ROTATE_BACKEND_REVISION,
    DirectCacheDisposition, DirectCrazyError, DirectDeoptError,
    DirectHaltFetchError, DirectHaltRegistersError, DirectHost,
    DirectInitialHaltError, DirectInputError, DirectJumpCodeError,
    DirectJumpDataError, DirectNativeKind, DirectNoOperationError,
    DirectNonGraphicalError, DirectOutputError, DirectRotateError,
    DirectSelectionError, DirectSequenceError, PreflightedExecutionTier,
    VerifiedCrazyNativeObjectArtifact, VerifiedDeoptNativeObjectArtifact,
    VerifiedDirectNativeArtifact, VerifiedDirectNativeCache,
    VerifiedDirectSequencePlan, VerifiedHaltFetchNativeObjectArtifact,
    VerifiedHaltRegistersNativeObjectArtifact,
    VerifiedInitialHaltNativeObjectArtifact, VerifiedInputNativeObjectArtifact,
    VerifiedJumpCodeNativeObjectArtifact, VerifiedJumpDataNativeObjectArtifact,
    VerifiedNoOperationNativeObjectArtifact,
    VerifiedNonGraphicalNativeObjectArtifact,
    VerifiedOutputNativeObjectArtifact, VerifiedRotateNativeObjectArtifact,
    emit_direct_crazy_coff, emit_direct_deopt_coff,
    emit_direct_halt_fetch_coff, emit_direct_halt_registers_coff,
    emit_direct_initial_halt_coff, emit_direct_input_coff,
    emit_direct_jump_code_coff, emit_direct_jump_data_coff,
    emit_direct_no_operation_coff, emit_direct_non_graphical_coff,
    emit_direct_output_coff, emit_direct_rotate_coff,
    select_cached_preflighted_execution_tier,
    select_cached_verified_direct_sequence, select_preflighted_execution_tier,
    select_verified_direct_native, select_verified_direct_sequence,
    verify_direct_crazy, verify_direct_deopt_stub, verify_direct_halt_fetch,
    verify_direct_halt_registers, verify_direct_initial_halt,
    verify_direct_input, verify_direct_jump_code, verify_direct_jump_data,
    verify_direct_no_operation, verify_direct_non_graphical,
    verify_direct_output, verify_direct_rotate,
};
use malbolge::{
    ProfileMachineObservation, ProfileMemoryWrite, RunOutcome, TraceInput,
};

use crate::execution_cache::{
    HostIsa, HostOperatingSystem, NativeArtifactKey, NativeIdentityError,
    NativeTargetIdentity,
};
use crate::execution_ir::{EFFECT_IR_VERSION, RegionEffectProgram};

/// Stable bootstrap backend identity bound into native artifact keys.
pub const CLANG_C23_BOOTSTRAP_BACKEND_ID: &str = "clang-c23-bootstrap";
/// Bootstrap revision that emits profile-bound `.mbprof` metadata.
pub const CLANG_C23_BOOTSTRAP_BACKEND_REVISION: u32 = 2;
/// First native call-frame ABI revision for generated bootstrap regions.
pub const NATIVE_REGION_ABI_REVISION: u16 = 1;

/// Failure while preparing an untrusted native artifact candidate.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeArtifactError {
    /// Compiler returned an empty object candidate.
    EmptyObject,
    /// Region has no effect boundary from which an entry/exit can be derived.
    EmptyRegion,
    /// Native artifact identity cannot be constructed from this IR/target.
    Identity(NativeIdentityError),
    /// Input metadata disagrees with before/after observation counters.
    InputTransition,
    /// Portable IR schema is not the implemented version.
    IrVersion,
    /// A verifier live-in disagrees with the first written value at its
    /// address.
    MemoryLiveIn,
    /// Memory writes disagree about the value flowing through one address.
    MemoryTransition,
    /// Adjacent effect observations do not form one continuous region.
    ObservationChain,
    /// Region outcome disagrees with effect count or final termination state.
    Outcome,
    /// Output metadata disagrees with before/after observation counters.
    OutputTransition,
    /// Rendering into owned source text unexpectedly failed.
    Rendering,
    /// Requested target does not name the bootstrap backend/revision/ABI.
    TargetBackend,
    /// Bootstrap backend does not claim target-specific CPU feature lowering.
    TargetFeatures,
}

impl Display for NativeArtifactError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        f.write_str(match self {
            Self::EmptyObject => "native compiler returned an empty object",
            Self::EmptyRegion => "native bootstrap requires a non-empty region",
            Self::Identity(_error) => {
                "native artifact identity construction failed"
            },
            Self::InputTransition => "region input transition is inconsistent",
            Self::IrVersion => "unsupported portable IR version",
            Self::MemoryLiveIn => "region memory live-in is inconsistent",
            Self::MemoryTransition => {
                "region memory transition is inconsistent"
            },
            Self::ObservationChain => "region observations are not continuous",
            Self::Outcome => "region outcome is inconsistent with effects",
            Self::OutputTransition => {
                "region output transition is inconsistent"
            },
            Self::Rendering => "native bootstrap C rendering failed",
            Self::TargetBackend => {
                "target does not select the bootstrap backend"
            },
            Self::TargetFeatures => {
                "bootstrap backend requires no CPU features"
            },
        })
    }
}

impl From<NativeIdentityError> for NativeArtifactError {
    fn from(error: NativeIdentityError) -> Self {
        Self::Identity(error)
    }
}

/// Deterministic source candidate bound to one exact portable IR/target key.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UntrustedNativeSourceArtifact {
    key: NativeArtifactKey,
    source: String,
    target_triple: &'static str,
}

/// Opaque compiler output that has not crossed native semantic validation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UntrustedNativeObjectArtifact {
    key: NativeArtifactKey,
    object: Vec<u8>,
    target_triple: &'static str,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct MemoryFlow {
    final_value: u32,
    initial_value: u32,
}

#[derive(Debug)]
struct LoweringPlan<'program> {
    entry: ProfileMachineObservation,
    final_observation: ProfileMachineObservation,
    input_checks: Vec<(usize, TraceInput)>,
    memory: BTreeMap<u32, MemoryFlow>,
    output_bytes: Vec<(usize, u8)>,
    program: &'program RegionEffectProgram,
}

impl UntrustedNativeSourceArtifact {
    /// Returns the complete cache/native identity claimed by this candidate.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        &self.key
    }

    /// Returns deterministic bootstrap C23 source.
    #[must_use]
    pub fn source(&self) -> &str {
        &self.source
    }

    /// Returns the exact Clang target triple selected by the target identity.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.target_triple
    }
}

impl UntrustedNativeObjectArtifact {
    /// Attaches opaque compiler bytes to the still-untrusted source identity.
    ///
    /// This constructor performs no semantic admission. A matching key only
    /// records the claim that the compiler output belongs to this candidate.
    ///
    /// # Errors
    ///
    /// Returns [`NativeArtifactError::EmptyObject`] for empty compiler output.
    pub fn from_compiler_output(
        source: &UntrustedNativeSourceArtifact,
        object: Vec<u8>,
    ) -> Result<Self, NativeArtifactError> {
        if object.is_empty() {
            return Err(NativeArtifactError::EmptyObject);
        }
        Ok(Self {
            key: source.key.clone(),
            object,
            target_triple: source.target_triple,
        })
    }

    /// Attaches arbitrary emitter bytes to one claimed native identity.
    ///
    /// No structural or semantic admission occurs here. This constructor exists
    /// so independent emitters can cross the same explicitly untrusted
    /// boundary.
    #[must_use]
    pub const fn from_emitter_output(
        key: NativeArtifactKey,
        object: Vec<u8>,
        target_triple: &'static str,
    ) -> Self {
        Self {
            key,
            object,
            target_triple,
        }
    }

    /// Returns the full claimed native artifact key.
    #[must_use]
    pub const fn key(&self) -> &NativeArtifactKey {
        &self.key
    }

    /// Returns opaque native object bytes with no semantic authority.
    #[must_use]
    pub fn object(&self) -> &[u8] {
        &self.object
    }

    /// Returns the target triple used to request compiler output.
    #[must_use]
    pub const fn target_triple(&self) -> &'static str {
        self.target_triple
    }
}

impl<'program> LoweringPlan<'program> {
    fn new(
        program: &'program RegionEffectProgram,
    ) -> Result<Self, NativeArtifactError> {
        if program.format_version != EFFECT_IR_VERSION {
            return Err(NativeArtifactError::IrVersion);
        }
        let first = program
            .effects
            .first()
            .ok_or(NativeArtifactError::EmptyRegion)?;
        let last = program
            .effects
            .last()
            .ok_or(NativeArtifactError::EmptyRegion)?;
        validate_effect_chain(program)?;
        validate_outcome(program, last.after)?;
        let mut memory = BTreeMap::new();
        for live_in in &program.memory_live_ins {
            merge_live_in(&mut memory, live_in.address, live_in.value)?;
        }
        let mut input_checks = Vec::new();
        let mut output_bytes = Vec::new();
        for effect in &program.effects {
            if let Some(input) = effect.input {
                input_checks.push((effect.before.input_consumed, input));
            }
            if let Some(output) = effect.output {
                output_bytes.push((effect.before.output_len, output));
            }
            for write in
                [effect.memory_delta.data, effect.memory_delta.encryption]
                    .into_iter()
                    .flatten()
            {
                merge_write(&mut memory, write)?;
            }
        }
        Ok(Self {
            entry: first.before,
            final_observation: last.after,
            input_checks,
            memory,
            output_bytes,
            program,
        })
    }

    fn render(
        &self,
        key: &NativeArtifactKey,
    ) -> Result<String, NativeArtifactError> {
        let target = key.target();
        let mut output = String::new();
        writeln!(
            &mut output,
            "/* Malbolge untrusted native bootstrap candidate. */"
        )
        .map_err(|_error| NativeArtifactError::Rendering)?;
        writeln!(&mut output, "/* Profile ID: {} */", self.program.profile_id)
            .map_err(|_error| NativeArtifactError::Rendering)?;
        writeln!(
            &mut output,
            "/* Profile fingerprint: {} */",
            self.program.profile_fingerprint
        )
        .map_err(|_error| NativeArtifactError::Rendering)?;
        writeln!(&mut output, "/* Target: {} */", clang_target_triple(target))
            .map_err(|_error| NativeArtifactError::Rendering)?;
        writeln!(
            &mut output,
            "/* Backend: {} rev {} / ABI {} */",
            target.backend_id(),
            target.backend_revision(),
            target.native_abi_revision()
        )
        .map_err(|_error| NativeArtifactError::Rendering)?;
        render_profile_metadata(&mut output, key)?;
        output.push_str(C_ABI_PREFIX);
        self.render_preflight(&mut output)?;
        self.render_commit(&mut output)?;
        output.push_str("    return MB_NATIVE_APPLIED;\n}\n");
        Ok(output)
    }

    fn render_commit(
        &self,
        output: &mut String,
    ) -> Result<(), NativeArtifactError> {
        for (offset, byte) in &self.output_bytes {
            writeln!(
                output,
                "    state->output[MB_U64({offset})] = MB_U8({byte});"
            )
            .map_err(|_error| NativeArtifactError::Rendering)?;
        }
        for (address, flow) in &self.memory {
            if flow.initial_value != flow.final_value {
                writeln!(
                    output,
                    "    state->memory[MB_U64({address})] = MB_U32({});",
                    flow.final_value
                )
                .map_err(|_error| NativeArtifactError::Rendering)?;
            }
        }
        let final_state = self.final_observation;
        writeln!(
            output,
            "    state->input_consumed = MB_U64({});",
            final_state.input_consumed
        )
        .map_err(|_error| NativeArtifactError::Rendering)?;
        writeln!(
            output,
            "    state->output_len = MB_U64({});",
            final_state.output_len
        )
        .map_err(|_error| NativeArtifactError::Rendering)?;
        writeln!(
            output,
            "    state->accumulator = MB_U32({});",
            final_state.registers.accumulator
        )
        .map_err(|_error| NativeArtifactError::Rendering)?;
        writeln!(
            output,
            "    state->code_pointer = MB_U32({});",
            final_state.registers.code_pointer
        )
        .map_err(|_error| NativeArtifactError::Rendering)?;
        writeln!(
            output,
            "    state->data_pointer = MB_U32({});",
            final_state.registers.data_pointer
        )
        .map_err(|_error| NativeArtifactError::Rendering)?;
        writeln!(
            output,
            "    state->termination = MB_U8({});",
            NativeTerminationTag::from_termination(final_state.termination)
                .code()
        )
        .map_err(|_error| NativeArtifactError::Rendering)?;
        Ok(())
    }

    fn render_host_preflight(
        &self,
        output: &mut String,
    ) -> Result<(), NativeArtifactError> {
        output.push_str(
            "    if (state == 0) { return MB_NATIVE_INVALID_ARGUMENT; }\n",
        );
        output.push_str(concat!(
            "    if (state->input_consumed > state->input_len || ",
            "state->output_len > state->output_capacity) { ",
            "return MB_NATIVE_INVALID_ARGUMENT; }\n"
        ));
        if !self.memory.is_empty() {
            output.push_str(concat!(
                "    if (state->memory == 0) { ",
                "return MB_NATIVE_INVALID_ARGUMENT; }\n"
            ));
        }
        if self
            .input_checks
            .iter()
            .any(|(_offset, input)| matches!(input, TraceInput::Byte(_)))
        {
            output.push_str(concat!(
                "    if (state->input == 0) { ",
                "return MB_NATIVE_INVALID_ARGUMENT; }\n"
            ));
        }
        if !self.output_bytes.is_empty() {
            output.push_str(concat!(
                "    if (state->output == 0) { ",
                "return MB_NATIVE_INVALID_ARGUMENT; }\n"
            ));
        }
        if self.final_observation.output_len > self.entry.output_len {
            writeln!(
                output,
                concat!(
                    "    if (state->output_capacity < MB_U64({})) ",
                    "{{ return MB_NATIVE_INVALID_ARGUMENT; }}"
                ),
                self.final_observation.output_len
            )
            .map_err(|_error| NativeArtifactError::Rendering)?;
        }
        Ok(())
    }

    fn render_memory_preflight(
        &self,
        output: &mut String,
    ) -> Result<(), NativeArtifactError> {
        for (address, flow) in &self.memory {
            writeln!(
                output,
                concat!(
                    "    if (state->memory_words <= MB_U64({address})) ",
                    "{{ return MB_NATIVE_INVALID_ARGUMENT; }}"
                ),
                address = address
            )
            .map_err(|_error| NativeArtifactError::Rendering)?;
            writeln!(
                output,
                concat!(
                    "    if (state->memory[MB_U64({address})] ",
                    "!= MB_U32({value})) ",
                    "{{ return MB_NATIVE_GUARD_MISS; }}"
                ),
                address = address,
                value = flow.initial_value
            )
            .map_err(|_error| NativeArtifactError::Rendering)?;
        }
        Ok(())
    }

    fn render_preflight(
        &self,
        output: &mut String,
    ) -> Result<(), NativeArtifactError> {
        self.render_host_preflight(output)?;
        render_observation_guard(output, self.entry)?;
        self.render_memory_preflight(output)?;
        for (offset, input) in &self.input_checks {
            render_input_guard(output, *offset, *input)?;
        }
        Ok(())
    }
}

/// Lowers one portable region to deterministic untrusted C23 source.
///
/// The returned candidate is not executable authority. A future runner must
/// first satisfy the verifier-owned `VerifiedExactRegion` dependency/lineage
/// guard, and native machine code requires an independent admission boundary.
///
/// # Errors
///
/// Returns [`NativeArtifactError`] when IR structure or target assumptions are
/// inconsistent with the bootstrap backend contract.
pub fn lower_clang_c23(
    program: &RegionEffectProgram,
    target: NativeTargetIdentity,
) -> Result<UntrustedNativeSourceArtifact, NativeArtifactError> {
    validate_target(&target)?;
    let plan = LoweringPlan::new(program)?;
    let key = NativeArtifactKey::new(program, target)?;
    let target_triple = clang_target_triple(key.target());
    let source = plan.render(&key)?;
    Ok(UntrustedNativeSourceArtifact {
        key,
        source,
        target_triple,
    })
}

fn render_profile_metadata(
    output: &mut String,
    key: &NativeArtifactKey,
) -> Result<(), NativeArtifactError> {
    let metadata = profile_metadata::canonical_profile_metadata(key)
        .ok_or(NativeArtifactError::Rendering)?;
    output.push_str("#pragma section(\".mbprof\", read)\n");
    output.push_str("__declspec(allocate(\".mbprof\"))\n");
    output.push_str("const unsigned char malbolge_profile_metadata[] = {\n");
    for chunk in metadata.chunks(12) {
        output.push_str("    ");
        for byte in chunk {
            write!(output, "0x{byte:02x}, ")
                .map_err(|_error| NativeArtifactError::Rendering)?;
        }
        output.push('\n');
    }
    output.push_str("};\n\n");
    Ok(())
}

fn validate_target(
    target: &NativeTargetIdentity,
) -> Result<(), NativeArtifactError> {
    if target.backend_id() != CLANG_C23_BOOTSTRAP_BACKEND_ID
        || target.backend_revision() != CLANG_C23_BOOTSTRAP_BACKEND_REVISION
        || target.native_abi_revision() != NATIVE_REGION_ABI_REVISION
    {
        return Err(NativeArtifactError::TargetBackend);
    }
    if !target.required_features().is_empty() {
        return Err(NativeArtifactError::TargetFeatures);
    }
    Ok(())
}

fn validate_effect_chain(
    program: &RegionEffectProgram,
) -> Result<(), NativeArtifactError> {
    let mut previous_after = None;
    for effect in &program.effects {
        if effect.before.termination.is_some()
            || previous_after.is_some_and(|previous| previous != effect.before)
        {
            return Err(NativeArtifactError::ObservationChain);
        }
        validate_input_transition(effect.before, effect.after, effect.input)?;
        validate_output_transition(effect.before, effect.after, effect.output)?;
        previous_after = Some(effect.after);
    }
    Ok(())
}

const fn validate_input_transition(
    before: ProfileMachineObservation,
    after: ProfileMachineObservation,
    input: Option<TraceInput>,
) -> Result<(), NativeArtifactError> {
    let expected = match input {
        None | Some(TraceInput::EndOfInput) => before.input_consumed,
        Some(TraceInput::Byte(_byte)) => {
            before.input_consumed.saturating_add(1)
        },
    };
    if after.input_consumed == expected {
        Ok(())
    } else {
        Err(NativeArtifactError::InputTransition)
    }
}

fn validate_output_transition(
    before: ProfileMachineObservation,
    after: ProfileMachineObservation,
    output: Option<u8>,
) -> Result<(), NativeArtifactError> {
    let expected = output.map_or(before.output_len, |_byte| {
        before.output_len.saturating_add(1)
    });
    if after.output_len == expected {
        Ok(())
    } else {
        Err(NativeArtifactError::OutputTransition)
    }
}

fn validate_outcome(
    program: &RegionEffectProgram,
    final_observation: ProfileMachineObservation,
) -> Result<(), NativeArtifactError> {
    let steps = program.effects.len();
    match program.outcome {
        RunOutcome::BudgetExhausted { steps: observed }
            if observed == steps
                && observed == program.step_budget
                && final_observation.termination.is_none() =>
        {
            Ok(())
        },
        RunOutcome::Terminated { reason, steps: observed }
            if observed == steps
                && observed <= program.step_budget
                && final_observation.termination == Some(reason) =>
        {
            Ok(())
        },
        RunOutcome::BudgetExhausted { .. } | RunOutcome::Terminated { .. } => {
            Err(NativeArtifactError::Outcome)
        },
    }
}

fn merge_live_in(
    memory: &mut BTreeMap<u32, MemoryFlow>,
    address: u32,
    value: u32,
) -> Result<(), NativeArtifactError> {
    match memory.get(&address) {
        None => {
            let _previous = memory.insert(address, MemoryFlow {
                final_value: value,
                initial_value: value,
            });
            Ok(())
        },
        Some(flow) if flow.initial_value == value => Ok(()),
        Some(_flow) => Err(NativeArtifactError::MemoryLiveIn),
    }
}

fn merge_write(
    memory: &mut BTreeMap<u32, MemoryFlow>,
    write: ProfileMemoryWrite,
) -> Result<(), NativeArtifactError> {
    match memory.get_mut(&write.address) {
        None => {
            let _previous = memory.insert(write.address, MemoryFlow {
                final_value: write.after,
                initial_value: write.before,
            });
            Ok(())
        },
        Some(flow) if flow.final_value == write.before => {
            flow.final_value = write.after;
            Ok(())
        },
        Some(_flow) => Err(NativeArtifactError::MemoryTransition),
    }
}

fn render_observation_guard(
    output: &mut String,
    entry: ProfileMachineObservation,
) -> Result<(), NativeArtifactError> {
    writeln!(
        output,
        concat!(
            "    if (state->input_consumed != MB_U64({input}) || ",
            "state->output_len != MB_U64({output_len}) || ",
            "state->accumulator != MB_U32({accumulator}) || ",
            "state->code_pointer != MB_U32({code}) || ",
            "state->data_pointer != MB_U32({data}) || ",
            "state->termination != MB_U8({termination})) ",
            "{{ return MB_NATIVE_GUARD_MISS; }}"
        ),
        input = entry.input_consumed,
        output_len = entry.output_len,
        accumulator = entry.registers.accumulator,
        code = entry.registers.code_pointer,
        data = entry.registers.data_pointer,
        termination =
            NativeTerminationTag::from_termination(entry.termination).code()
    )
    .map_err(|_error| NativeArtifactError::Rendering)
}

fn render_input_guard(
    output: &mut String,
    offset: usize,
    input: TraceInput,
) -> Result<(), NativeArtifactError> {
    match input {
        TraceInput::Byte(byte) => writeln!(
            output,
            concat!(
                "    if (state->input_len <= MB_U64({offset}) || ",
                "state->input[MB_U64({offset})] != MB_U8({byte})) ",
                "{{ return MB_NATIVE_GUARD_MISS; }}"
            ),
            offset = offset,
            byte = byte
        ),
        TraceInput::EndOfInput => writeln!(
            output,
            concat!(
                "    if (state->input_len != MB_U64({offset})) ",
                "{{ return MB_NATIVE_GUARD_MISS; }}"
            ),
            offset = offset
        ),
    }
    .map_err(|_error| NativeArtifactError::Rendering)
}

const fn clang_target_triple(target: &NativeTargetIdentity) -> &'static str {
    match (target.host_os(), target.host_isa()) {
        (HostOperatingSystem::Windows, HostIsa::X86_64) => {
            "x86_64-pc-windows-msvc"
        },
        (HostOperatingSystem::Windows, HostIsa::AArch64) => {
            "aarch64-pc-windows-msvc"
        },
        (HostOperatingSystem::Linux, HostIsa::X86_64) => {
            "x86_64-unknown-linux-gnu"
        },
        (HostOperatingSystem::Linux, HostIsa::AArch64) => {
            "aarch64-unknown-linux-gnu"
        },
        (HostOperatingSystem::MacOs, HostIsa::X86_64) => "x86_64-apple-darwin",
        (HostOperatingSystem::MacOs, HostIsa::AArch64) => "arm64-apple-darwin",
    }
}
