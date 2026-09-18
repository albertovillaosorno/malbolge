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
//   - Session-backed native host composition for executable-memory commands.
// - Must-Not:
//   - Admit lifecycle evidence, perform local memory syscalls, or invoke code.
// - Allows:
//   - Inputs: existing native executable-memory adapter requests.
//   - Outputs: decoded untrusted MBNPM1 reports or stable host errors.
//   - Side effects: bounded exchanges through one retained child session.
// - Split-When:
//   - Runner integration requires independent call-session policy.
// - Merge-When:
//   - One complete process host owns both memory and runner implementations.
// - Summary:
//   - Binds MBNPM1 memory operations to one persistent native child session.
// - Description:
//   - Existing safe lifecycle code remains the sole report-admission authority.
// - Usage:
//   - Passed to native loaders and later to single-host execution
//     orchestration.
// - Defaults:
//   - Remote, framing, transport, or response-shape failure fails closed.
//

//! Persistent-session implementation of the native executable-memory port.

use std::fmt::{Display, Formatter, Result as FormatResult};

use super::lifecycle::{
    NativeExecutableMappingReport, NativeExecutableReleaseRequest,
    NativeInstructionSyncReport,
};
use super::platform::{
    NativeExecutableAllocationRequest, NativeExecutableCodeCopyReport,
    NativeExecutableMemoryAdapter, NativeInstructionSyncRequest,
};
use super::process_memory_wire::{
    NativeProcessMemoryRequest, NativeProcessMemoryResponse,
    NativeProcessMemoryWireError, decode_native_process_memory_response,
    encode_native_process_memory_request,
    native_process_memory_response_byte_limit,
};
use super::process_session::{NativeProcessSession, NativeProcessSessionError};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum NativeProcessHostErrorKind {
    Remote,
    ResponseShape,
    Session,
    Wire,
}

/// Stable failure surfaced by one persistent native process host.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeProcessHostError {
    kind: NativeProcessHostErrorKind,
    remote_code: u32,
    session_error: Option<NativeProcessSessionError>,
    wire_error: Option<NativeProcessMemoryWireError>,
}

/// One persistent child owner for native executable-memory and future calls.
#[derive(Debug)]
pub struct NativeProcessHost {
    session: NativeProcessSession,
}

impl Display for NativeProcessHostError {
    fn fmt(&self, f: &mut Formatter<'_>) -> FormatResult {
        match self.kind {
            NativeProcessHostErrorKind::Remote => write!(
                f,
                "native process host remote failure code {}",
                self.remote_code,
            ),
            NativeProcessHostErrorKind::ResponseShape => {
                f.write_str("native process host response shape drifted")
            },
            NativeProcessHostErrorKind::Session => {
                f.write_str("native process host session failure")
            },
            NativeProcessHostErrorKind::Wire => match self.wire_error {
                Some(error) => {
                    write!(f, "native process host wire failure: {error}")
                },
                None => f.write_str("native process host wire failure"),
            },
        }
    }
}

impl NativeProcessHostError {
    const fn remote(code: u32) -> Self {
        Self {
            kind: NativeProcessHostErrorKind::Remote,
            remote_code: code,
            session_error: None,
            wire_error: None,
        }
    }

    /// Returns the child-defined platform code when this is a remote failure.
    #[must_use]
    pub const fn remote_code(self) -> Option<u32> {
        match self.kind {
            NativeProcessHostErrorKind::Remote => Some(self.remote_code),
            NativeProcessHostErrorKind::ResponseShape
            | NativeProcessHostErrorKind::Session
            | NativeProcessHostErrorKind::Wire => None,
        }
    }

    const fn response_shape() -> Self {
        Self {
            kind: NativeProcessHostErrorKind::ResponseShape,
            remote_code: 0,
            session_error: None,
            wire_error: None,
        }
    }

    const fn session(error: NativeProcessSessionError) -> Self {
        Self {
            kind: NativeProcessHostErrorKind::Session,
            remote_code: 0,
            session_error: Some(error),
            wire_error: None,
        }
    }

    /// Returns transport detail when the persistent session failed.
    #[must_use]
    pub const fn session_error(self) -> Option<NativeProcessSessionError> {
        self.session_error
    }

    const fn wire(error: NativeProcessMemoryWireError) -> Self {
        Self {
            kind: NativeProcessHostErrorKind::Wire,
            remote_code: 0,
            session_error: None,
            wire_error: Some(error),
        }
    }

    /// Returns MBNPM1 framing detail when the command wire failed.
    #[must_use]
    pub const fn wire_error(self) -> Option<NativeProcessMemoryWireError> {
        self.wire_error
    }
}

impl NativeProcessHost {
    fn exchange_memory(
        &mut self,
        request: &NativeProcessMemoryRequest,
    ) -> Result<NativeProcessMemoryResponse, NativeProcessHostError> {
        let encoded = encode_native_process_memory_request(request)
            .map_err(NativeProcessHostError::wire)?;
        let response_limit = native_process_memory_response_byte_limit(request)
            .map_err(NativeProcessHostError::wire)?;
        let response = self
            .session
            .exchange(&encoded, response_limit)
            .map_err(NativeProcessHostError::session)?;
        let decoded = decode_native_process_memory_response(&response, request)
            .map_err(NativeProcessHostError::wire)?;
        match decoded {
            NativeProcessMemoryResponse::Failure(code) => {
                Err(NativeProcessHostError::remote(code))
            },
            success @ (NativeProcessMemoryResponse::Allocate(_)
            | NativeProcessMemoryResponse::Copy(_)
            | NativeProcessMemoryResponse::Protect(_)
            | NativeProcessMemoryResponse::Release
            | NativeProcessMemoryResponse::Synchronize(_)) => Ok(success),
        }
    }

    /// Takes ownership of one already-spawned persistent native child session.
    #[must_use]
    pub const fn new(session: NativeProcessSession) -> Self {
        Self { session }
    }

    /// Reports whether transport failure has invalidated this child session.
    #[must_use]
    pub const fn session_poisoned(&self) -> bool {
        self.session.poisoned()
    }
}

impl NativeExecutableMemoryAdapter for NativeProcessHost {
    type Error = NativeProcessHostError;

    fn allocate_writable(
        &mut self,
        request: NativeExecutableAllocationRequest,
    ) -> Result<NativeExecutableMappingReport, Self::Error> {
        let wire_request = NativeProcessMemoryRequest::Allocate(request);
        let response = self.exchange_memory(&wire_request)?;
        let NativeProcessMemoryResponse::Allocate(report) = response else {
            return Err(NativeProcessHostError::response_shape());
        };
        Ok(report)
    }

    fn copy_code(
        &mut self,
        mapping: NativeExecutableMappingReport,
        code: &[u8],
    ) -> Result<NativeExecutableCodeCopyReport, Self::Error> {
        let wire_request = NativeProcessMemoryRequest::Copy {
            code: code.into(),
            mapping,
        };
        let response = self.exchange_memory(&wire_request)?;
        let NativeProcessMemoryResponse::Copy(report) = response else {
            return Err(NativeProcessHostError::response_shape());
        };
        Ok(report)
    }

    fn protect_read_execute(
        &mut self,
        mapping: NativeExecutableMappingReport,
    ) -> Result<NativeExecutableMappingReport, Self::Error> {
        let wire_request = NativeProcessMemoryRequest::Protect(mapping);
        let response = self.exchange_memory(&wire_request)?;
        let NativeProcessMemoryResponse::Protect(report) = response else {
            return Err(NativeProcessHostError::response_shape());
        };
        Ok(report)
    }

    fn release(
        &mut self,
        request: NativeExecutableReleaseRequest,
    ) -> Result<(), Self::Error> {
        let wire_request = NativeProcessMemoryRequest::Release(request);
        let response = self.exchange_memory(&wire_request)?;
        let NativeProcessMemoryResponse::Release = response else {
            return Err(NativeProcessHostError::response_shape());
        };
        Ok(())
    }

    fn synchronize_instructions(
        &mut self,
        request: NativeInstructionSyncRequest,
    ) -> Result<NativeInstructionSyncReport, Self::Error> {
        let wire_request = NativeProcessMemoryRequest::Synchronize(request);
        let response = self.exchange_memory(&wire_request)?;
        let NativeProcessMemoryResponse::Synchronize(report) = response else {
            return Err(NativeProcessHostError::response_shape());
        };
        Ok(report)
    }
}
