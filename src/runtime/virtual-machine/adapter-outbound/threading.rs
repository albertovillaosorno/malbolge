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
//   - Scoped host-thread implementation of deterministic parallel mapping.
// - Must-Not:
//   - Interpret VM requests, alter item order, or retain scoped work owners.
// - Allows:
//   - Inputs: independent owned items and the outbound parallelism contract.
//   - Outputs: input-ordered results or exact worker-panic evidence.
//   - Side effects: bounded scoped host thread creation and joining.
// - Split-When:
//   - A persistent pool or another host runtime gains independent lifecycle.
// - Merge-When:
//   - The standard-library thread implementation remains the only adapter.
// - Summary:
//   - Implements deterministic chunked parallel mapping with scoped threads.
// - Description:
//   - Chunk and join order are stable regardless of physical completion order.
// - Usage:
//   - Selected by the VM composition root for public parallel batch APIs.
// - Defaults:
//   - Uses at most one worker per item and never detaches host work.
//

//! Scoped-thread adapter for deterministic host-parallel execution.

use std::thread;

use crate::parallel_port::{ParallelExecutionError, ParallelExecutionPort};

/// Standard-library scoped-thread implementation of parallel execution.
#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct ScopedThreadParallelism;

impl ParallelExecutionPort for ScopedThreadParallelism {
    fn execute<Request, Output>(
        requests: Vec<Request>,
        worker_count: usize,
        execute: fn(Request) -> Output,
    ) -> Result<Vec<Output>, ParallelExecutionError>
    where
        Request: Send,
        Output: Send,
    {
        if worker_count == 0 {
            return Err(ParallelExecutionError::ZeroWorkers);
        }
        if requests.is_empty() {
            return Ok(Vec::new());
        }

        let workers = worker_count.min(requests.len());
        let chunk_size = requests.len().div_ceil(workers);
        let chunks = owned_chunks(requests, chunk_size);
        thread::scope(|scope| {
            let mut handles = Vec::new();
            for (worker, chunk) in chunks.into_iter().enumerate() {
                let handle = scope.spawn(move || execute_chunk(chunk, execute));
                handles.push((worker, handle));
            }
            let mut results = Vec::new();
            for (worker, handle) in handles {
                let mut chunk_results =
                    handle.join().map_err(|_panic| worker_panicked(worker))?;
                results.append(&mut chunk_results);
            }
            Ok(results)
        })
    }
}

fn execute_chunk<Request, Output>(
    chunk: Vec<Request>,
    execute: fn(Request) -> Output,
) -> Vec<Output> {
    chunk.into_iter().map(execute).collect()
}

fn owned_chunks<Request>(
    requests: Vec<Request>,
    chunk_size: usize,
) -> Vec<Vec<Request>> {
    let mut remaining = requests.into_iter();
    let mut chunks = Vec::new();
    loop {
        let chunk = remaining.by_ref().take(chunk_size).collect::<Vec<_>>();
        if chunk.is_empty() {
            break;
        }
        chunks.push(chunk);
    }
    chunks
}

const fn worker_panicked(worker: usize) -> ParallelExecutionError {
    ParallelExecutionError::WorkerPanicked { worker }
}
