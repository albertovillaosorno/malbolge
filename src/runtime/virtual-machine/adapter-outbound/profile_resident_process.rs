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
use std::io::{Read as _, Write as _};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};

use crate::profile_resident_port::ProfileResidentTransport;
use crate::profile_resident_wire::{
    ProfileResidentWireRequest, ProfileResidentWireResponse,
    ProfileResidentWireResult, decode_profile_resident_response,
    encode_profile_resident_batch, profile_resident_response_byte_limit,
};

/// Process-per-batch implementation of the resident wire transport port.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProfileResidentProcessTransport {
    arguments: Vec<OsString>,
    environment: Vec<(OsString, OsString)>,
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
        request: &[u8],
        response_limit: usize,
    ) -> Option<Vec<u8>> {
        let read_capacity = response_limit.checked_add(1)?;
        let read_limit = u64::try_from(read_capacity).ok()?;
        let mut command = Command::new(&self.program);
        let _arguments = command.args(&self.arguments);
        for (key, value) in &self.environment {
            let _environment = command.env(key, value);
        }
        if let Some(directory) = &self.working_directory {
            let _working_directory = command.current_dir(directory);
        }
        let mut child = command
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .ok()?;
        if !write_request(&mut child, request) {
            terminate_child(&mut child);
            return None;
        }
        let Some(stdout) = child.stdout.take() else {
            terminate_child(&mut child);
            return None;
        };
        let mut response = Vec::new();
        let read_result = stdout.take(read_limit).read_to_end(&mut response);
        if read_result.is_err() || response.len() > response_limit {
            terminate_child(&mut child);
            return None;
        }
        match child.wait() {
            Ok(status) => status.success().then_some(response),
            Err(_error) => {
                terminate_child(&mut child);
                None
            },
        }
    }

    /// Creates a process transport for one explicit executable path.
    #[must_use]
    pub const fn new(program: PathBuf) -> Self {
        Self {
            arguments: Vec::new(),
            environment: Vec::new(),
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
        let response = self.exchange_bytes(&encoded, response_limit)?;
        let memory_words = requests.first()?.geometry.memory_words;
        match decode_profile_resident_response(&response, memory_words).ok()? {
            ProfileResidentWireResponse::Results(results) => {
                Some(results.into_iter().map(Some).collect())
            },
            ProfileResidentWireResponse::Unavailable => None,
        }
    }
}

fn terminate_child(child: &mut Child) {
    let _kill_result = child.kill();
    let _wait_result = child.wait();
}

fn write_request(child: &mut Child, request: &[u8]) -> bool {
    let Some(mut stdin) = child.stdin.take() else {
        return false;
    };
    let result = stdin.write_all(request);
    drop(stdin);
    result.is_ok()
}
