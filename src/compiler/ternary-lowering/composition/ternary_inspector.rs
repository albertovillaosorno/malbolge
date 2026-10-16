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
//   - Bounded child execution for canonical ternary-state extraction.
// - Must-Not:
//   - Decode sidecar JSON or override independent ternary-stage validation.
// - Allows:
//   - Inputs: explicit interpreter, inspector, codec, and progress paths.
//   - Outputs: bounded complete stdout or stable process-rejection category.
//   - Side effects: one inspector child and two bounded pipe-drain workers.
// - Split-When:
//   - External compiler orchestration owns process-group cancellation.
// - Merge-When:
//   - A governed transport shared by both stages becomes an explicit port.
// - Summary:
//   - Bounds ternary compiler recovery inspector execution and output.
// - Description:
//   - Constrains pipe bytes and deadline with concurrent stream admission.
// - Usage:
//   - Invoked by the ternary progress composition before state decoding.
// - Defaults:
//   - A child timeout, diagnostic, or overflow rejects without partial state.
//

//! Bounded pipe and child-process transport for ternary checkpoint extraction.

use std::io::{self, Read as _};
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::mpsc::{self, Receiver, Sender};
use std::thread;
use std::time::{Duration, Instant};

const POLL: Duration = Duration::from_millis(10);
const CHILD_DEADLINE: Duration = Duration::from_secs(60);
const STATE_LIMIT: usize = 64 * 1024 * 1024;
const DIAGNOSTIC_LIMIT: usize = 8 * 1024;
const EXTRACT_SWITCH: &str = "--extract-checkpoint";

/// Transport outcome distinct from subsequent ternary-state admission.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) enum TransportError {
    /// Configured interpreter could not be launched.
    Launch,
    /// Inspector process or byte-stream contract was not admitted.
    Rejected,
}

#[derive(Clone, Copy, Debug)]
struct TransportBudget {
    deadline: Duration,
    diagnostic_bytes: usize,
    state_bytes: usize,
}

impl TransportBudget {
    const DEFAULT: Self = Self {
        deadline: CHILD_DEADLINE,
        diagnostic_bytes: DIAGNOSTIC_LIMIT,
        state_bytes: STATE_LIMIT,
    };
}

#[derive(Clone, Copy, Debug)]
enum PipeKind {
    Diagnostic,
    State,
}

struct PipeEvent {
    bytes: io::Result<Vec<u8>>,
    kind: PipeKind,
}

struct RequestedInspector<'path> {
    codec: &'path str,
    inspector: &'path Path,
    interpreter: &'path Path,
    sidecar: &'path Path,
}

fn receive_pipe(
    pipe: impl io::Read + Send + 'static,
    kind: PipeKind,
    ceiling: usize,
    sender: Sender<PipeEvent>,
) -> Result<(), TransportError> {
    let limit = u64::try_from(ceiling)
        .ok()
        .and_then(|max| max.checked_add(1))
        .ok_or(TransportError::Rejected)?;
    let _thread = thread::Builder::new()
        .name(String::from("ternary-inspector-pipe"))
        .spawn(move || {
            let mut bytes = Vec::new();
            let result = pipe.take(limit).read_to_end(&mut bytes);
            let _delivered = sender.send(PipeEvent {
                bytes: result.map(|_read| bytes),
                kind,
            });
        })
        .map_err(|_error| TransportError::Rejected)?;
    Ok(())
}

fn accept_event(
    event: PipeEvent,
    budget: TransportBudget,
    state: &mut Option<Vec<u8>>,
    diagnostics: &mut Option<Vec<u8>>,
) -> Result<(), TransportError> {
    let (destination, max) = match event.kind {
        PipeKind::Diagnostic => (diagnostics, budget.diagnostic_bytes),
        PipeKind::State => (state, budget.state_bytes),
    };
    let bytes = event.bytes.map_err(|_error| TransportError::Rejected)?;
    if destination.is_some() || bytes.len() > max {
        return Err(TransportError::Rejected);
    }
    *destination = Some(bytes);
    Ok(())
}

fn terminate(child: &mut Child) {
    let _killed = child.kill();
    let _reaped = child.wait();
}

fn collect(
    child: &mut Child,
    receiver: &Receiver<PipeEvent>,
    budget: TransportBudget,
    started: Instant,
) -> Result<Vec<u8>, TransportError> {
    let mut state: Option<Vec<u8>> = None;
    let mut diagnostics: Option<Vec<u8>> = None;
    loop {
        if started.elapsed() >= budget.deadline {
            return Err(TransportError::Rejected);
        }
        let status = child
            .try_wait()
            .map_err(|_error| TransportError::Rejected)?;
        if status.is_some_and(|exit| !exit.success()) {
            return Err(TransportError::Rejected);
        }
        if status.is_some() && state.is_some() && diagnostics.is_some() {
            return match (state, diagnostics) {
                (Some(bytes), Some(errors)) if errors.is_empty() => Ok(bytes),
                _ => Err(TransportError::Rejected),
            };
        }
        let remaining = budget
            .deadline
            .checked_sub(started.elapsed())
            .ok_or(TransportError::Rejected)?;
        if state.is_some() && diagnostics.is_some() {
            // Both pipes can close before the child exits. The sender channel
            // then disconnects; only the child's final status remains pending.
            thread::sleep(remaining.min(POLL));
            continue;
        }
        match receiver.recv_timeout(remaining.min(POLL)) {
            Ok(event) => {
                accept_event(event, budget, &mut state, &mut diagnostics)?;
            },
            Err(mpsc::RecvTimeoutError::Timeout) => {},
            Err(mpsc::RecvTimeoutError::Disconnected) => {
                return Err(TransportError::Rejected);
            },
        }
    }
}

fn extract_with_budget(
    request: &RequestedInspector<'_>,
    budget: TransportBudget,
) -> Result<Vec<u8>, TransportError> {
    if budget.deadline.is_zero() {
        return Err(TransportError::Rejected);
    }
    let started = Instant::now();
    let mut child = Command::new(request.interpreter)
        .arg(request.inspector)
        .arg(EXTRACT_SWITCH)
        .arg(request.codec)
        .arg(request.sidecar)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|_error| TransportError::Launch)?;
    let result = (|| {
        let (sender, receiver) = mpsc::channel();
        let stdout = child.stdout.take().ok_or(TransportError::Rejected)?;
        let stderr = child.stderr.take().ok_or(TransportError::Rejected)?;
        receive_pipe(
            stdout,
            PipeKind::State,
            budget.state_bytes,
            sender.clone(),
        )?;
        receive_pipe(
            stderr,
            PipeKind::Diagnostic,
            budget.diagnostic_bytes,
            sender,
        )?;
        collect(&mut child, &receiver, budget, started)
    })();
    if result.is_err() {
        terminate(&mut child);
    }
    result
}

/// Inspect committed ternary state while bounding child resources.
///
/// # Errors
///
/// Returns [`TransportError::Launch`] only for a child spawn failure; all
/// other process, deadline, and stream failures return `Rejected`.
pub(super) fn extract_ternary_checkpoint(
    interpreter: &Path,
    inspector: &Path,
    codec: &str,
    sidecar: &Path,
) -> Result<Vec<u8>, TransportError> {
    extract_with_budget(
        &RequestedInspector {
            codec,
            inspector,
            interpreter,
            sidecar,
        },
        TransportBudget::DEFAULT,
    )
}

#[cfg(test)]
#[path = "../../../../tests/compiler/ternary-lowering/inspector_transport.rs"]
mod tests;
