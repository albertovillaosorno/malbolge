// File:
//   - interpreter_benchmark.rs
// Path:
//   - src/bin/interpreter_benchmark.rs
//
// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE
// Path-Rule:
//   - All paths in this header are repository-root relative.
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
//   - Thin Cargo entrypoint for `benchmarks/interpreter/main.rs`.
// - Description:
//   - Keeps benchmark logic under its responsibility-owned directory.
// - Usage:
//   - Invoked with `cargo run --release --bin interpreter_benchmark`.
// - Defaults:
//   - Includes the benchmark implementation without adding behavior.
//
// Related documents:
// - benchmarks/interpreter/main.rs
// - docs/technical/runtime/vm/cpu-vm-table-optimization.md
// - docs/technical/runtime/execution/batch-vm-execution.md
//
// Large file:
//   - false
//

//! Cargo composition root for the interpreter benchmark executable.

#[path = "../../benchmarks/interpreter/main.rs"]
pub mod benchmark;

use std::io::Result as IoResult;

fn main() -> IoResult<()> {
    benchmark::run()
}
