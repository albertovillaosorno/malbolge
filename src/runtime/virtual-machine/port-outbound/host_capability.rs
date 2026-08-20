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
//   - Transport-neutral outbound host-capability invocation contract.
// - Must-Not:
//   - Expose mutable guest memory, host pointers, or one backend transport ABI.
// - Allows:
//   - Inputs: validated call identity and immutable request payload bytes.
//   - Outputs: one response frame plus host-staged result bytes.
//   - Side effects: delegated to the selected outbound transport only.
// - Split-When:
//   - Async completion requires independently owned lifetime semantics.
// - Merge-When:
//   - One outbound contract owns every host effect transport shape.
// - Summary:
//   - Carries admitted semantic capability calls to replaceable transports.
// - Description:
//   - Keeps guest frame identity independent from interpreter, JIT, or runner.
// - Usage:
//   - Consumed by the VM host-capability application dispatcher.
// - Defaults:
//   - A transport receives immutable request bytes and stages all result bytes.
//

//! Outbound transport contract for admitted semantic host-capability calls.

use crate::host_capability::HostCapabilityFrame;

/// Immutable admitted request offered to one host-effect transport.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct HostCapabilityInvocation<'request> {
    /// Canonical semantic call identity and guest range declarations.
    pub frame: HostCapabilityFrame,
    /// Immutable request payload copied from no host-owned memory.
    pub request: &'request [u8],
}

/// Host-owned response staged before any guest memory mutation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct HostCapabilityTransportResponse {
    /// Canonical response identity and completion status.
    pub frame: HostCapabilityFrame,
    /// Complete response bytes staged outside guest memory.
    pub staged_result: Vec<u8>,
}

/// Replaceable transport for one already-admitted semantic capability call.
pub trait HostCapabilityTransport {
    /// Transport-local failure that remains distinct from guest ABI rejection.
    type Error;

    /// Performs one host effect and returns a fully staged response.
    ///
    /// # Errors
    ///
    /// Returns only transport-local failures. Guest frame and range validation
    /// belongs to the application dispatcher before this method is invoked.
    fn invoke(
        &mut self,
        invocation: HostCapabilityInvocation<'_>,
    ) -> Result<HostCapabilityTransportResponse, Self::Error>;
}
