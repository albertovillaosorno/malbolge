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
//   - Canonical module topology for the portable typed compiler IR function.
// - Must-Not:
//   - Parse C, lower to Malbolge, or enter the virtual-machine crate topology.
// - Allows:
//   - Inputs: responsibility-owned typed-IR domain and application modules.
//   - Outputs: one logical Rust surface for compiler stages and tests.
//   - Side effects: composition only.
// - Split-When:
//   - Independently packaged compiler IR capabilities gain separate roots.
// - Merge-When:
//   - Another root owns the exact same typed-IR module topology.
// - Summary:
//   - Declares the canonical portable typed compiler IR module tree.
// - Description:
//   - Keeps product compiler semantics outside the runtime VM library.
// - Usage:
//   - Included by compiler IR integration tests and future compiler
//     composition.
// - Defaults:
//   - Only responsibility-owned modules are re-exported.
//

//! Canonical module topology for portable typed compiler IR.

#[path = "../application/cfg.rs"]
mod cfg;
#[path = "../domain/control.rs"]
mod control;
#[path = "../application/encode.rs"]
mod encode;
#[path = "../application/error.rs"]
mod error;
#[path = "../domain/frontend.rs"]
mod frontend_semantics;
#[path = "../domain/ids.rs"]
mod ids;
#[path = "../domain/instruction.rs"]
mod instruction;
#[path = "../application/instructions.rs"]
mod instructions;
#[path = "../application/layout.rs"]
mod layout;
#[path = "../application/lower_frontend.rs"]
mod lower_frontend;
#[path = "../domain/module.rs"]
mod module;
#[path = "../application/proofs.rs"]
mod proofs;
#[path = "../domain/source.rs"]
mod source;
#[path = "../application/types.rs"]
mod type_validation;
#[path = "../domain/types.rs"]
mod types;
#[path = "../application/validate.rs"]
mod validate;
#[path = "../application/values.rs"]
mod values;

pub use control::*;
pub use encode::{CanonicalError, canonical_bytes, canonical_debug_text};
pub use error::ValidationError;
pub use frontend_semantics::*;
pub use ids::*;
pub use instruction::*;
pub use lower_frontend::{FrontendLoweringError, lower_frontend_artifact};
pub use module::*;
pub use source::*;
pub use types::*;
pub use validate::validate_module;
