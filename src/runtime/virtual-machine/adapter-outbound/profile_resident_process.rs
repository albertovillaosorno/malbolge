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
//   - Standard-process transport for homogeneous resident profile wire batches.
// - Must-Not:
//   - Name accelerator vendors, Python modules, or interpret VM authority.
// - Allows:
//   - Inputs: admitted resident wire requests and explicit process settings.
//   - Outputs: decoded resident wire results or transport-level unavailability.
//   - Side effects: one bounded child-process exchange per attempted batch.
// - Split-When:
//   - Persistent sessions or asynchronous process pools gain own lifecycle.
// - Merge-When:
//   - One process-per-batch transport remains the only MBPRN2 host adapter.
// - Summary:
//   - Binds the MBPRN2 resident profile contract to a child process.
// - Description:
//   - Encodes requests, bounds stdout, and returns untrusted decoded results.
// - Usage:
//   - Configured by composition roots that own a concrete resident worker.
// - Defaults:
//   - Any launch, I/O, framing, shape, or child failure reports unavailable.
//

//! Standard-process transport for resident profile wire batches.

use std::ffi::OsString;
use std::io::{Read, Write as _};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::mpsc::{self, Receiver, TryRecvError};
use std::thread;
use std::time::{Duration, Instant};

use crate::profile_resident_port::ProfileResidentTransport;
use crate::profile_resident_wire::{
    ProfileResidentWireRequest, ProfileResidentWireResponse,
    ProfileResidentWireResult, decode_profile_resident_response,
    encode_profile_resident_batch, profile_resident_response_byte_limit,
};

// The worker may outlive its child when an escaped descendant retains a pipe.
// A permit belongs to the worker until it actually closes its pipe handles.
const MAX_RESIDENT_EXCHANGE_WORKERS: usize = 8;
const DEFAULT_EXCHANGE_TIMEOUT: Duration = Duration::from_secs(60);
static RESIDENT_EXCHANGE_WORKERS: AtomicUsize = AtomicUsize::new(0);
type ExchangeResponse = Option<Vec<u8>>;

struct ResidentExchangePermit<'counter> {
    counter: &'counter AtomicUsize,
}

impl<'counter> ResidentExchangePermit<'counter> {
    fn acquire(counter: &'counter AtomicUsize, maximum: usize) -> Option<Self> {
        let _prior = counter
            .try_update(Ordering::AcqRel, Ordering::Acquire, |active| {
                active.checked_add(1).filter(|next| *next <= maximum)
            })
            .ok()?;
        Some(Self { counter })
    }
}

impl Drop for ResidentExchangePermit<'_> {
    fn drop(&mut self) {
        let _prior = self.counter.fetch_sub(1, Ordering::AcqRel);
    }
}

/// Process-per-batch implementation of the resident wire transport port.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProfileResidentProcessTransport {
    arguments: Vec<OsString>,
    environment: Vec<(OsString, OsString)>,
    exchange_timeout: Duration,
    program: PathBuf,
    working_directory: Option<PathBuf>,
}

impl ProfileResidentProcessTransport {
    /// Appends one exact process argument.
    #[must_use]
    pub fn argument(mut self, argument: OsString) -> Self {
        self.arguments.push(argument);
        self
    }

    /// Adds or replaces one child-process environment variable.
    #[must_use]
    pub fn environment(mut self, key: OsString, value: OsString) -> Self {
        self.environment.retain(|(known, _value)| known != &key);
        self.environment.push((key, value));
        self
    }

    fn exchange_bytes(
        &self,
        request: Vec<u8>,
        response_limit: usize,
    ) -> Option<Vec<u8>> {
        if self.exchange_timeout.is_zero() {
            return None;
        }
        let started = Instant::now();
        let read_capacity = response_limit.checked_add(1)?;
        let read_limit = u64::try_from(read_capacity).ok()?;
        // Acquire before spawning a process or its worker. A worker blocked by
        // escaped pipe holders keeps the slot even after this call times out.
        let permit = ResidentExchangePermit::acquire(
            &RESIDENT_EXCHANGE_WORKERS,
            MAX_RESIDENT_EXCHANGE_WORKERS,
        )?;
        let mut command = Command::new(&self.program);
        let _arguments = command.args(&self.arguments);
        for (key, value) in &self.environment {
            let _environment = command.env(key, value);
        }
        if let Some(directory) = &self.working_directory {
            let _working_directory = command.current_dir(directory);
        }
        #[cfg(target_os = "linux")]
        {
            use std::os::unix::process::CommandExt as _;
            // Ordinary forked pipe holders share the owned process group.
            let _group = command.process_group(0);
        }
        let mut child = command
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .ok()?;
        let (Some(mut stdin), Some(stdout)) =
            (child.stdin.take(), child.stdout.take())
        else {
            terminate_child(&mut child);
            return None;
        };
        let (sender, receiver) = mpsc::sync_channel(1);
        let worker = thread::Builder::new().spawn(move || {
            let _permit = permit;
            let response = if stdin.write_all(&request).is_ok() {
                drop(stdin);
                read_response(stdout, read_limit, response_limit)
            } else {
                None
            };
            let _sent = sender.send(response);
        });
        if worker.is_err() {
            terminate_child(&mut child);
            return None;
        }
        // Do not join a worker after timeout: escaped descendants can retain
        // stdout even after the direct child is dead and reaped.
        let response = await_response(
            &mut child,
            &receiver,
            started,
            self.exchange_timeout,
        );
        if response.is_none() {
            terminate_child(&mut child);
        }
        response
    }

    /// Sets the maximum wall-clock duration of a child exchange.
    ///
    /// A zero duration rejects the batch without launching a child.
    #[must_use]
    pub const fn exchange_timeout(mut self, timeout: Duration) -> Self {
        self.exchange_timeout = timeout;
        self
    }

    /// Creates a process transport for one explicit executable path.
    #[must_use]
    pub const fn new(program: PathBuf) -> Self {
        Self {
            arguments: Vec::new(),
            environment: Vec::new(),
            exchange_timeout: DEFAULT_EXCHANGE_TIMEOUT,
            program,
            working_directory: None,
        }
    }

    /// Sets the child process working directory.
    #[must_use]
    pub fn working_directory(mut self, directory: PathBuf) -> Self {
        self.working_directory = Some(directory);
        self
    }
}

impl ProfileResidentTransport for ProfileResidentProcessTransport {
    fn exchange(
        &mut self,
        requests: &[ProfileResidentWireRequest<'_>],
    ) -> Option<Vec<Option<ProfileResidentWireResult>>> {
        if requests.is_empty() {
            return Some(Vec::new());
        }
        let response_limit =
            profile_resident_response_byte_limit(requests).ok()?;
        let encoded = encode_profile_resident_batch(requests).ok()?;
        let response = self.exchange_bytes(encoded, response_limit)?;
        let memory_words = requests.first()?.geometry.memory_words;
        match decode_profile_resident_response(&response, memory_words).ok()? {
            ProfileResidentWireResponse::Results(results) => {
                Some(results.into_iter().map(Some).collect())
            },
            ProfileResidentWireResponse::Unavailable => None,
        }
    }
}

fn await_response(
    child: &mut Child,
    receiver: &Receiver<ExchangeResponse>,
    started: Instant,
    timeout: Duration,
) -> Option<Vec<u8>> {
    let mut response = None;
    loop {
        let remaining = timeout
            .checked_sub(started.elapsed())
            .filter(|remaining| !remaining.is_zero())?;
        if response.is_none() {
            match receiver.try_recv() {
                Ok(Some(bytes)) => response = Some(bytes),
                Ok(None) | Err(TryRecvError::Disconnected) => return None,
                Err(TryRecvError::Empty) => (),
            }
        }
        match child.try_wait().ok()? {
            Some(status) if !status.success() => return None,
            Some(_) if response.is_some() => {
                return response.filter(|_| started.elapsed() < timeout);
            },
            Some(_) | None => {},
        }
        thread::sleep(remaining.min(Duration::from_millis(5)));
    }
}

fn read_response(
    stdout: impl Read,
    read_limit: u64,
    response_limit: usize,
) -> Option<Vec<u8>> {
    let mut response = Vec::new();
    let _read = stdout.take(read_limit).read_to_end(&mut response).ok()?;
    (response.len() <= response_limit).then_some(response)
}

fn terminate_child(child: &mut Child) {
    #[cfg(target_os = "linux")]
    {
        // Safe Rust uses the absolute host utility to signal ordinary
        // descendants; child.kill() below remains the cross-platform fallback.
        let _group_signal = Command::new("/usr/bin/kill")
            .args(["-s", "KILL", "--"])
            .arg(format!("-{}", child.id()))
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
    }
    let _kill_result = child.kill();
    let _wait_result = child.wait();
}

#[cfg(test)]
#[path = "../../../../tests/vm/profile_resident_worker_capacity.rs"]
mod worker_capacity_tests;
