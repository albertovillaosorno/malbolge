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
//   - One persistent child-process byte session for native host protocols.
// - Must-Not:
//   - Interpret MBNPC1, allocate executable memory, or admit guest semantics.
// - Allows:
//   - Inputs: explicit process configuration and bounded request byte slices.
//   - Outputs: one length-framed response per exchange or stable transport
//     error.
//   - Side effects: one retained child process plus pipe I/O until
//     drop/failure.
// - Split-When:
//   - Asynchronous multiplexing or process pools require independent policy.
// - Merge-When:
//   - One concrete native host protocol becomes the only persistent consumer.
// - Summary:
//   - Retains one bounded child session across native host operations.
// - Description:
//   - Length-prefixes exchanges and poisons the session after transport
//     failure.
// - Usage:
//   - Shared by one stateful native host implementing memory and runner ports.
// - Defaults:
//   - Stderr is discarded; malformed/oversized responses terminate the child.
//

//! Persistent bounded child-process transport for native host protocols.

use std::ffi::OsString;
use std::io::{ErrorKind, Read as _, Write as _};
use std::path::PathBuf;
use std::process::{Child, ChildStdin, ChildStdout, Command, Stdio};

const FRAME_LENGTH_BYTES: usize = size_of::<u64>();

/// Stable transport failure for one persistent native child session.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeProcessSessionError {
    /// Failed to flush one complete request frame.
    Flush(ErrorKind),
    /// Spawned child did not expose piped stdin.
    MissingStdin,
    /// Spawned child did not expose piped stdout.
    MissingStdout,
    /// A prior exchange failure already invalidated this session.
    Poisoned,
    /// Failed while reading the response frame.
    Read(ErrorKind),
    /// Request byte length cannot be represented by the session frame.
    RequestLength,
    /// Announced response length cannot be represented by this host.
    ResponseLength,
    /// Child announced a response larger than the caller-provided bound.
    ResponseTooLarge,
    /// Failed to launch the configured child process.
    Spawn(ErrorKind),
    /// Failed while writing the request frame.
    Write(ErrorKind),
}

/// Immutable configuration for spawning one persistent native child session.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeProcessSessionConfig {
    arguments: Vec<OsString>,
    environment: Vec<(OsString, OsString)>,
    program: PathBuf,
    working_directory: Option<PathBuf>,
}

/// One retained child process with exclusive request/response pipes.
#[derive(Debug)]
pub struct NativeProcessSession {
    child: Child,
    poisoned: bool,
    stdin: ChildStdin,
    stdout: ChildStdout,
}

impl NativeProcessSessionConfig {
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

    /// Creates one explicit persistent-session process configuration.
    #[must_use]
    pub const fn new(program: PathBuf) -> Self {
        Self {
            arguments: Vec::new(),
            environment: Vec::new(),
            program,
            working_directory: None,
        }
    }

    /// Spawns one child with retained piped stdin/stdout.
    ///
    /// # Errors
    ///
    /// Returns [`NativeProcessSessionError`] when launch or pipe acquisition
    /// fails. A partially launched child is terminated before returning.
    pub fn spawn(
        &self,
    ) -> Result<NativeProcessSession, NativeProcessSessionError> {
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
            .map_err(|error| NativeProcessSessionError::Spawn(error.kind()))?;
        let Some(stdin) = child.stdin.take() else {
            terminate_child(&mut child);
            return Err(NativeProcessSessionError::MissingStdin);
        };
        let Some(stdout) = child.stdout.take() else {
            terminate_child(&mut child);
            return Err(NativeProcessSessionError::MissingStdout);
        };
        Ok(NativeProcessSession {
            child,
            poisoned: false,
            stdin,
            stdout,
        })
    }

    /// Sets the child process working directory.
    #[must_use]
    pub fn working_directory(mut self, directory: PathBuf) -> Self {
        self.working_directory = Some(directory);
        self
    }
}

impl NativeProcessSession {
    /// Exchanges one request frame for one response bounded before allocation.
    ///
    /// Every frame is an unsigned little-endian 64-bit payload length followed
    /// by exactly that many payload bytes. Any transport/framing failure
    /// poisons and terminates the session because stream synchronization is
    /// no longer trustworthy.
    ///
    /// # Errors
    ///
    /// Returns [`NativeProcessSessionError`] for poisoned state,
    /// unrepresentable lengths, I/O failure, or a child-announced response
    /// beyond `response_limit`.
    pub fn exchange(
        &mut self,
        request: &[u8],
        response_limit: usize,
    ) -> Result<Vec<u8>, NativeProcessSessionError> {
        if self.poisoned {
            return Err(NativeProcessSessionError::Poisoned);
        }
        let result = self.exchange_inner(request, response_limit);
        if result.is_err() {
            self.poison();
        }
        result
    }

    fn exchange_inner(
        &mut self,
        request: &[u8],
        response_limit: usize,
    ) -> Result<Vec<u8>, NativeProcessSessionError> {
        let request_len = u64::try_from(request.len())
            .map_err(|_error| NativeProcessSessionError::RequestLength)?;
        self.stdin
            .write_all(&request_len.to_le_bytes())
            .map_err(|error| NativeProcessSessionError::Write(error.kind()))?;
        self.stdin
            .write_all(request)
            .map_err(|error| NativeProcessSessionError::Write(error.kind()))?;
        self.stdin
            .flush()
            .map_err(|error| NativeProcessSessionError::Flush(error.kind()))?;
        let mut length = [0u8; FRAME_LENGTH_BYTES];
        self.stdout
            .read_exact(&mut length)
            .map_err(|error| NativeProcessSessionError::Read(error.kind()))?;
        let announced = u64::from_le_bytes(length);
        let response_len = usize::try_from(announced)
            .map_err(|_error| NativeProcessSessionError::ResponseLength)?;
        if response_len > response_limit {
            return Err(NativeProcessSessionError::ResponseTooLarge);
        }
        let mut response = vec![0; response_len];
        self.stdout
            .read_exact(&mut response)
            .map_err(|error| NativeProcessSessionError::Read(error.kind()))?;
        Ok(response)
    }

    fn poison(&mut self) {
        self.poisoned = true;
        terminate_child(&mut self.child);
    }

    /// Reports whether a previous exchange invalidated stream synchronization.
    #[must_use]
    pub const fn poisoned(&self) -> bool {
        self.poisoned
    }
}

impl Drop for NativeProcessSession {
    fn drop(&mut self) {
        terminate_child(&mut self.child);
    }
}

fn terminate_child(child: &mut Child) {
    let _kill_result = child.kill();
    let _wait_result = child.wait();
}
