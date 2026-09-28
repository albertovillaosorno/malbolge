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
#[path = "../port-inbound/typed_ir.rs"]
mod input;
#[path = "../port-inbound/instruction_decoder.rs"]
mod instruction_decoder_input;
#[path = "../application/lower.rs"]
mod lower;
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
#[path = "../application/realize_runtime_io.rs"]
mod realize_runtime_io;
#[path = "../port-inbound/runtime_helper.rs"]
mod runtime_helper_input;
#[path = "../port-inbound/runtime_intrinsic.rs"]
mod runtime_intrinsic_input;
#[path = "../port-inbound/startup.rs"]
mod startup_input;
#[path = "../port-inbound/target_profile.rs"]
mod target_profile_input;

pub use byte_stream_wrapper_input::ByteStreamWrapperRequest;
pub use encode_machine_io::{MachineIoEncodingError, encode_machine_io};
pub use input::*;
pub use instruction_decoder_input::ProfileInstructionDecoder;
pub use lower::{TernaryLoweringError, lower_typed_ir};
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
pub use realize_runtime_io::{RuntimeIoRealizationError, realize_runtime_io};
pub use runtime_helper_input::RuntimeHelperRequest;
pub use runtime_intrinsic_input::RuntimeIntrinsicRequest;
pub use startup_input::StartupRequest;
pub use target_profile_input::TargetProfileIo;
