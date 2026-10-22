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
//   - Deadline and bounded stdout/stderr admission for one inspector child.
// - Must-Not:
//   - Parse the checkpoint, trust diagnostics, or choose interpreter paths.
// - Allows:
//   - Inputs: explicit tool and pointer paths, codec and resource limits.
//   - Outputs: one complete opaque stdout payload or stable transport failure.
//   - Side effects: child spawn/termination and two capped drain workers.
// - Split-When:
//   - Platform-specific descendant cancellation needs a dedicated adapter.
// - Merge-When:
//   - Another child transport is identical in ownership and failure policy.
// - Summary:
//   - Extracts opaque state without hanging on filled pipes or stalled
//     children.
// - Description:
//   - Concurrent bounded drains and a deadline guard direct-child lifetime.
// - Usage:
//   - Called from compiler-stage composition with explicitly trusted tools.
// - Defaults:
//   - Direct child terminates on time or output budget violation.
//

//! Bounded checkpoint-inspector child transport.

use std::io::{self, Read as _};
#[cfg(target_os = "linux")]
use std::os::unix::process::CommandExt as _;
use std::path::Path;
use std::process::{Child, Command, Stdio};
use std::sync::mpsc::{self, Receiver, TryRecvError};
use std::thread;
use std::time::{Duration, Instant};

const EXTRACT_ARGUMENT: &str = "--extract-checkpoint";
const POLL_INTERVAL: Duration = Duration::from_millis(5);
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(60);
const MAX_STATE_BYTES: usize = 64 * 1024 * 1024;
const MAX_DIAGNOSTIC_BYTES: usize = 8 * 1024;

/// Failure categories for an explicitly configured inspector child.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) enum InspectorFailure {
    /// The explicit interpreter could not be spawned.
    Launch,
    /// A child failed, timed out, exceeded a bound, or emitted diagnostics.
    Rejected,
}

#[derive(Clone, Copy)]
struct InspectorLimits {
    stderr: usize,
    stdout: usize,
    timeout: Duration,
}

impl InspectorLimits {
    const DEFAULT: Self = Self {
        stderr: MAX_DIAGNOSTIC_BYTES,
        stdout: MAX_STATE_BYTES,
        timeout: DEFAULT_TIMEOUT,
    };
}

type PipeReceiver = Receiver<io::Result<Vec<u8>>>;
type PipePoll = Result<Option<Vec<u8>>, InspectorFailure>;

struct PipeReceivers {
    stderr: PipeReceiver,
    stdout: PipeReceiver,
}

#[derive(Clone, Copy)]
struct ExtractRequest<'path> {
    codec: &'path str,
    inspector: &'path Path,
    interpreter: &'path Path,
    progress: &'path Path,
}

fn drain_pipe(
    pipe: impl io::Read + Send + 'static,
    limit: usize,
) -> Result<PipeReceiver, InspectorFailure> {
    let (sender, receiver) = mpsc::sync_channel(1);
    let maximum = u64::try_from(limit)
        .ok()
        .and_then(|length| length.checked_add(1))
        .ok_or(InspectorFailure::Rejected)?;
    let _reader = thread::Builder::new()
        .name(String::from("compiler-inspector-drain"))
        .spawn(move || {
            let mut bytes = Vec::new();
            let result = pipe.take(maximum).read_to_end(&mut bytes);
            let _sent = sender.send(result.map(|_count| bytes));
        })
        .map_err(|_error| InspectorFailure::Rejected)?;
    Ok(receiver)
}

fn poll_pipe(receiver: &PipeReceiver, limit: usize) -> PipePoll {
    match receiver.try_recv() {
        Ok(Ok(bytes)) if bytes.len() <= limit => Ok(Some(bytes)),
        Ok(Ok(_) | Err(_)) | Err(TryRecvError::Disconnected) => {
            Err(InspectorFailure::Rejected)
        },
        Err(TryRecvError::Empty) => Ok(None),
    }
}

fn terminate(child: &mut Child) {
    #[cfg(target_os = "linux")]
    {
        // The isolated process group includes ordinary inherited-pipe holders.
        let _group_signal = Command::new("/usr/bin/kill")
            .args(["-s", "KILL", "--"])
            .arg(format!("-{}", child.id()))
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
    }
    let _killed = child.kill();
    let _reaped = child.wait();
}

fn collect(
    child: &mut Child,
    readers: &PipeReceivers,
    limits: InspectorLimits,
    started: Instant,
) -> Result<Vec<u8>, InspectorFailure> {
    let mut status = None;
    let mut state = None;
    let mut diagnostics = None;
    loop {
        if started.elapsed() >= limits.timeout {
            return Err(InspectorFailure::Rejected);
        }
        if state.is_none() {
            state = poll_pipe(&readers.stdout, limits.stdout)?;
        }
        if diagnostics.is_none() {
            diagnostics = poll_pipe(&readers.stderr, limits.stderr)?;
        }
        if diagnostics.as_ref().is_some_and(|bytes| !bytes.is_empty()) {
            // A closed diagnostic stream already disqualifies all stdout.
            // Do not wait for inherited stdout handles to close.
            return Err(InspectorFailure::Rejected);
        }
        if status.is_none() {
            status = child
                .try_wait()
                .map_err(|_error| InspectorFailure::Rejected)?;
        }
        if status.is_some_and(|exit| !exit.success()) {
            // No valid checkpoint can follow a failed inspector exit.
            // Do not wait for descendants holding inherited pipe handles.
            return Err(InspectorFailure::Rejected);
        }
        if status.is_some() && state.is_some() && diagnostics.is_some() {
            let successful = status.is_some_and(|exit| exit.success())
                && diagnostics.as_ref().is_some_and(Vec::is_empty);
            return if successful {
                state.ok_or(InspectorFailure::Rejected)
            } else {
                Err(InspectorFailure::Rejected)
            };
        }
        thread::sleep(POLL_INTERVAL);
    }
}

fn extract_with_limits(
    request: ExtractRequest<'_>,
    limits: InspectorLimits,
) -> Result<Vec<u8>, InspectorFailure> {
    if limits.timeout.is_zero() {
        return Err(InspectorFailure::Rejected);
    }
    // A bare interpreter name would launch through ambient host PATH.
    if !request.interpreter.is_absolute()
        && request.interpreter.components().count() < 2
    {
        return Err(InspectorFailure::Launch);
    }
    // Python treats a lone dash as a stdin script even after `--`.
    if request.inspector == Path::new("-") {
        return Err(InspectorFailure::Rejected);
    }
    let started = Instant::now();
    let mut command = Command::new(request.interpreter);
    let _configured = command
        .arg("-I")
        .arg("--")
        .arg(request.inspector)
        .arg(EXTRACT_ARGUMENT)
        .arg(request.codec)
        .arg(request.progress)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(target_os = "linux")]
    let _group = command.process_group(0);
    let mut child =
        command.spawn().map_err(|_error| InspectorFailure::Launch)?;
    let result = (|| {
        let stdout_pipe =
            child.stdout.take().ok_or(InspectorFailure::Rejected)?;
        let stderr_pipe =
            child.stderr.take().ok_or(InspectorFailure::Rejected)?;
        let stdout = drain_pipe(stdout_pipe, limits.stdout)?;
        let stderr = drain_pipe(stderr_pipe, limits.stderr)?;
        collect(
            &mut child,
            &PipeReceivers { stderr, stdout },
            limits,
            started,
        )
    })();
    if result.is_err() {
        terminate(&mut child);
    }
    result
}

/// Extract one complete byte payload through the caller's trusted inspector.
///
/// # Errors
///
/// Returns [`InspectorFailure::Launch`] for spawn failure and
/// [`InspectorFailure::Rejected`] for every other child/transport failure.
pub(super) fn extract_checkpoint(
    interpreter: &Path,
    inspector: &Path,
    codec: &str,
    progress: &Path,
) -> Result<Vec<u8>, InspectorFailure> {
    extract_with_limits(
        ExtractRequest {
            codec,
            inspector,
            interpreter,
            progress,
        },
        InspectorLimits::DEFAULT,
    )
}

#[cfg(test)]
#[path = "../../../../tests/compiler/typed-ir/inspector_transport.rs"]
mod tests;
