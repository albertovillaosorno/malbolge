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
//   - Standard-library host transport for monotonic-time and sleep
//     capabilities.
// - Must-Not:
//   - Expose a wall-clock epoch, native timer handle, or mutable guest memory.
// - Allows:
//   - Inputs: already-admitted timing capability invocations.
//   - Outputs: staged canonical response frames and result bytes.
//   - Side effects: runner-local monotonic observation and host thread sleep.
// - Split-When:
//   - Async timers or another host runtime require independent lifecycle.
// - Merge-When:
//   - One standard timing transport remains sufficient for synchronous runners.
// - Summary:
//   - Implements production monotonic-time and relative-sleep host effects.
// - Description:
//   - Uses one private Instant origin and never exposes system wall-clock time.
// - Usage:
//   - Selected by runners that advertise the two timing capability families.
// - Defaults:
//   - Nonblocking positive sleeps return WOULD_BLOCK without sleeping.
//

//! Standard-library transport for version-one timing host capabilities.

use std::thread;
use std::time::{Duration, Instant};

use crate::host_capability::{
    HOST_CALL_FLAG_NONBLOCKING, HostCapabilityError, HostCapabilityFrame,
    HostCapabilityStatus,
};
use crate::host_capability_port::{
    HostCapabilityInvocation, HostCapabilityTransport,
    HostCapabilityTransportResponse,
};
use crate::host_capability_time::{
    HOST_MONOTONIC_TIME_CAPABILITY_ID, HOST_SLEEP_CAPABILITY_ID,
    decode_host_sleep_v1_request, encode_host_monotonic_time_v1_result,
};

/// Failure owned by the synchronous standard-library timing transport.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SystemTimingTransportError {
    /// The admitted request payload could not be decoded as its timing schema.
    InvalidPayload(HostCapabilityError),
    /// This transport was invoked for a non-timing capability family.
    UnsupportedCapability,
}

/// Synchronous production transport for version-one timing host capabilities.
#[derive(Clone, Copy, Debug)]
pub struct SystemTimingHostCapabilityTransport {
    last_nanoseconds: u64,
    origin: Instant,
}

impl Default for SystemTimingHostCapabilityTransport {
    fn default() -> Self {
        Self::new()
    }
}

impl SystemTimingHostCapabilityTransport {
    fn monotonic_response(
        &mut self,
        invocation: HostCapabilityInvocation<'_>,
    ) -> HostCapabilityTransportResponse {
        let Ok(nanoseconds) = u64::try_from(self.origin.elapsed().as_nanos())
        else {
            return status_response(
                invocation.frame,
                HostCapabilityStatus::HostError,
            );
        };
        if nanoseconds < self.last_nanoseconds {
            return status_response(
                invocation.frame,
                HostCapabilityStatus::HostError,
            );
        }
        self.last_nanoseconds = nanoseconds;
        let mut frame = invocation.frame;
        frame.result_length = 8;
        frame.status = HostCapabilityStatus::Complete;
        HostCapabilityTransportResponse {
            frame,
            staged_result: encode_host_monotonic_time_v1_result(nanoseconds)
                .to_vec(),
        }
    }

    /// Creates a runner-local monotonic origin for future observations.
    #[must_use]
    pub fn new() -> Self {
        Self {
            last_nanoseconds: 0,
            origin: Instant::now(),
        }
    }

    fn sleep_response(
        invocation: HostCapabilityInvocation<'_>,
    ) -> Result<HostCapabilityTransportResponse, SystemTimingTransportError>
    {
        let nanoseconds = decode_host_sleep_v1_request(invocation.request)
            .map_err(SystemTimingTransportError::InvalidPayload)?;
        let mut frame = invocation.frame;
        if nanoseconds != 0 && frame.flags & HOST_CALL_FLAG_NONBLOCKING != 0 {
            frame.status = HostCapabilityStatus::WouldBlock;
        } else {
            if nanoseconds != 0 {
                thread::sleep(Duration::from_nanos(nanoseconds));
            }
            frame.status = HostCapabilityStatus::Complete;
        }
        Ok(HostCapabilityTransportResponse {
            frame,
            staged_result: Vec::new(),
        })
    }
}

impl HostCapabilityTransport for SystemTimingHostCapabilityTransport {
    type Error = SystemTimingTransportError;

    fn invoke(
        &mut self,
        invocation: HostCapabilityInvocation<'_>,
    ) -> Result<HostCapabilityTransportResponse, Self::Error> {
        match invocation.frame.capability_id {
            HOST_MONOTONIC_TIME_CAPABILITY_ID => {
                Ok(self.monotonic_response(invocation))
            },
            HOST_SLEEP_CAPABILITY_ID => Self::sleep_response(invocation),
            _ => Err(SystemTimingTransportError::UnsupportedCapability),
        }
    }
}

const fn status_response(
    mut frame: HostCapabilityFrame,
    status: HostCapabilityStatus,
) -> HostCapabilityTransportResponse {
    frame.result_length = 0;
    frame.status = status;
    HostCapabilityTransportResponse {
        frame,
        staged_result: Vec::new(),
    }
}
