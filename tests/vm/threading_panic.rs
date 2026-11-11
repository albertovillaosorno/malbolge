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
//   - Scoped host scheduler panic-propagation regressions.
// - Must-Not:
//   - Touch guest VM semantics or depend on OS scheduling order.
// - Allows:
//   - Inputs: pure item functions, barriers, and controlled host panics.
//   - Outputs: stable typed worker failure without propagating host unwind.
//   - Side effects: short-lived scoped threads and caught worker panics.
// - Split-When:
//   - More host scheduler adapters require separate panic contracts.
// - Merge-When:
//   - Equivalent tested scheduler behavior resides elsewhere.
// - Summary:
//   - Guarantees every scoped handle is explicitly joined on worker panic.
// - Description:
//   - Simultaneous worker failures select the first input-order worker error.
// - Usage:
//   - Included by the standard scoped-thread host adapter in unit tests.
// - Defaults:
//   - No guest machine, filesystem, or external process is involved.
//

//! Scoped host thread worker-failure regression evidence.

use std::panic::catch_unwind;
use std::sync::{Arc, Barrier};

use super::ScopedThreadParallelism;
use crate::parallel_port::{ParallelExecutionError, ParallelExecutionPort as _};

#[expect(clippy::panic, reason = "test exercises caught host worker panics")]
fn both_workers_panic(barrier: Arc<Barrier>) {
    let _arrived = barrier.wait();
    drop(barrier);
    panic!("controlled scoped worker failure");
}

#[test]
fn simultaneous_worker_panics_return_first_typed_error() {
    let barrier = Arc::new(Barrier::new(2));
    let requests = vec![Arc::clone(&barrier), barrier];
    let observed =
        catch_unwind(|| ScopedThreadParallelism::execute(requests, 2, both_workers_panic));
    assert!(matches!(
        observed,
        Ok(Err(ParallelExecutionError::WorkerPanicked { worker: 0 }))
    ));
}

fn fail_later_workers(worker: u8) -> u8 {
    assert_eq!(worker, 0, "controlled later worker failure");
    worker
}

#[test]
fn later_worker_panics_return_earliest_failed_index() {
    let observed = catch_unwind(|| {
        ScopedThreadParallelism::execute(vec![0u8, 1u8, 2u8], 3, fail_later_workers)
    });
    assert!(matches!(
        observed,
        Ok(Err(ParallelExecutionError::WorkerPanicked { worker: 1 }))
    ));
}

fn double(value: u8) -> u8 {
    value.wrapping_mul(2)
}

#[test]
fn successful_scoped_workers_keep_input_order() {
    let result = ScopedThreadParallelism::execute(vec![3u8, 1u8, 4u8, 2u8], 3, double);
    assert_eq!(result, Ok(vec![6u8, 2u8, 8u8, 4u8]));
}
