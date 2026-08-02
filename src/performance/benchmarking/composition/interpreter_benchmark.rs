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
//   - Cargo composition for the interpreter benchmark executable.
// - Must-Not:
//   - Contain benchmark logic or create a language-oriented architecture.
// - Allows:
//   - Inputs: the responsibility-owned benchmark implementation.
//   - Outputs: one Cargo auto-discovered benchmark executable.
//   - Side effects: delegated benchmark process behavior only.
// - Split-When:
//   - Split when another benchmark responsibility needs its own executable.
// - Merge-When:
//   - Merge when Cargo no longer requires a binary composition surface.
// - Summary:
//   - Thin Cargo entrypoint for
//     `src/performance/benchmarking/application/interpreter/main.rs`.
// - Description:
//   - Keeps benchmark logic under its responsibility-owned directory.
// - Usage:
//   - Invoked with `cargo run --release --bin interpreter_benchmark`.
// - Defaults:
//   - Includes the benchmark implementation without adding behavior.
//

//! Cargo composition root for the interpreter benchmark executable.

#[path = "interpreter/main.rs"]
pub mod benchmark;

use std::io::Result as IoResult;

fn main() -> IoResult<()> {
    benchmark::run()
}
