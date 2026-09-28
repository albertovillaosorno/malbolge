// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Canonical module topology for pre-layout ternary machine lowering.
// - Must-Not:
//   - Re-own typed IR, target layout, Malbolge encoding, or runtime execution.
// - Allows:
//   - Inputs: explicit inbound typed-IR semantic projection records.
//   - Outputs: one logical Rust surface for ternary lowering and its tests.
//   - Side effects: composition only.
// - Split-When:
//   - The target representation gains independently packaged capabilities.
// - Merge-When:
//   - Another root owns this exact lowering module topology.
// - Summary:
//   - Declares the canonical pre-layout ternary lowering module tree.
// - Description:
//   - Keeps downstream layout/encoding separate from typed semantic lowering.
// - Usage:
//   - Included by compiler lowering integration tests and future composition.
// - Defaults:
//   - Upstream compiler implementation types never cross this function
//     boundary.
//

//! Canonical module topology for pre-layout ternary machine lowering.

#[path = "../port-inbound/byte_stream_wrapper.rs"]
mod byte_stream_wrapper_input;
#[path = "../application/encode_machine_io.rs"]
mod encode_machine_io;
#[path = "../port-inbound/frame_helper.rs"]
mod frame_helper_input;
#[path = "../port-inbound/heap_helper.rs"]
mod heap_helper_input;
#[path = "../port-inbound/typed_ir.rs"]
mod input;
#[path = "../port-inbound/instruction_decoder.rs"]
mod instruction_decoder_input;
#[path = "../application/lower.rs"]
mod lower;
#[path = "../application/lower_frame_helper.rs"]
mod lower_frame_helper;
#[path = "../application/lower_heap_helper.rs"]
mod lower_heap_helper;
#[path = "../application/lower_runtime_helper.rs"]
mod lower_runtime_helper;
#[path = "../application/lower_runtime_intrinsic.rs"]
mod lower_runtime_intrinsic;
#[path = "../domain/model.rs"]
mod model;
#[path = "../application/plan_byte_stream_wrapper.rs"]
mod plan_byte_stream_wrapper;
#[path = "../application/plan_startup.rs"]
mod plan_startup;
#[path = "../application/program_codec.rs"]
mod program_codec;
#[path = "progress_resume.rs"]
mod progress_resume;
#[path = "../application/realize_byte_stream_control_flow.rs"]
mod realize_byte_stream_control_flow;
#[path = "../application/realize_byte_stream_wrapper.rs"]
mod realize_byte_stream_wrapper;
#[path = "../application/realize_frame_helper.rs"]
mod realize_frame_helper;
#[path = "../application/realize_heap_helper.rs"]
mod realize_heap_helper;
#[path = "../application/realize_runtime_helper.rs"]
mod realize_runtime_helper;
#[path = "../application/realize_runtime_io.rs"]
mod realize_runtime_io;
#[path = "../port-inbound/runtime_helper.rs"]
mod runtime_helper_input;
#[path = "../port-inbound/runtime_intrinsic.rs"]
mod runtime_intrinsic_input;
#[path = "../application/stage.rs"]
mod stage;
#[path = "../port-inbound/startup.rs"]
mod startup_input;
#[path = "../port-inbound/target_profile.rs"]
mod target_profile_input;

pub use byte_stream_wrapper_input::ByteStreamWrapperRequest;
pub use encode_machine_io::{MachineIoEncodingError, encode_machine_io};
pub use frame_helper_input::FrameHelperRequest;
pub use heap_helper_input::HeapHelperRequest;
pub use input::*;
pub use instruction_decoder_input::ProfileInstructionDecoder;
pub use lower::{TernaryLoweringError, lower_typed_ir};
pub use lower_frame_helper::{FrameHelperLoweringError, lower_frame_helper};
pub use lower_heap_helper::{HeapHelperLoweringError, lower_heap_helper};
pub use lower_runtime_helper::{
    RuntimeHelperLoweringError, lower_runtime_helper,
};
pub use lower_runtime_intrinsic::{
    RuntimeIntrinsicLoweringError, lower_runtime_intrinsic,
};
pub use model::*;
pub use plan_byte_stream_wrapper::{
    ByteStreamWrapperPlanningError, plan_byte_stream_wrapper,
};
pub use plan_startup::{StartupPlanningError, plan_startup};
pub use program_codec::{
    TERNARY_PROGRAM_CODEC_ID, TernaryProgramCodecError,
    TernaryProgramValidationError, canonical_ternary_bytes,
    canonical_ternary_program, validate_ternary_program,
};
pub use progress_resume::{
    TernaryProgressCheckpointError, resume_ternary_from_progress,
};
pub use realize_byte_stream_control_flow::{
    ByteStreamControlFlowError, realize_byte_stream_control_flow,
};
pub use realize_byte_stream_wrapper::{
    ByteStreamWrapperRealizationError, realize_byte_stream_wrapper,
};
pub use realize_frame_helper::realize_frame_helper;
pub use realize_heap_helper::realize_heap_helper;
pub use realize_runtime_helper::realize_runtime_helper;
pub use realize_runtime_io::{RuntimeIoRealizationError, realize_runtime_io};
pub use runtime_helper_input::RuntimeHelperRequest;
pub use runtime_intrinsic_input::RuntimeIntrinsicRequest;
pub use stage::{TernaryStageError, TernaryStageInput, enter_ternary_stage};
pub use startup_input::StartupRequest;
pub use target_profile_input::TargetProfileIo;
