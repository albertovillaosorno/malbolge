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
//   - Process-local coupling of caller-authoritative batch order and count
//     FIFO.
// - Must-Not:
//   - Derive global order, require contiguous stamps, persist, or read clocks.
// - Allows:
//   - Inputs: arbitrary strictly increasing caller order and ordered summaries.
//   - Outputs: committed order/window evidence or exact stale-order rejection.
//   - Side effects: mutation of this explicit process-local owner only.
// - Split-When:
//   - Durable ordered state or distributed ordering service gains authority.
// - Merge-When:
//   - One durable count-telemetry owner owns ordering plus FIFO persistence.
// - Summary:
//   - Couples external monotonic batch order to transactional local FIFO
//     append.
// - Description:
//   - First order may be any value; later orders must strictly increase.
// - Usage:
//   - Submit batches in an order established outside the telemetry window.
// - Defaults:
//   - No implicit first stamp, contiguity rule, clock, or ordering source
//     exists.
//

//! Caller-authoritative ordering for process-local cached-retry count
//! telemetry.

use super::{
    NativeContinuationCachedRetryTelemetry,
    NativeContinuationCachedRetryTelemetryWindow,
    NativeContinuationCachedRetryTelemetryWindowBatchAppend,
    NativeContinuationCachedRetryTelemetryWindowError,
};

/// Opaque caller-authoritative monotonic order for one telemetry batch.
#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub struct NativeContinuationCachedRetryTelemetryBatchOrder(u64);

/// Process-local owner coupling external batch order to one count window.
#[derive(Clone, Debug)]
pub struct NativeContinuationCachedRetryTelemetryOrderedWindow {
    last_order: Option<NativeContinuationCachedRetryTelemetryBatchOrder>,
    window: NativeContinuationCachedRetryTelemetryWindow,
}

/// Evidence from one externally ordered transactional batch publication.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct NativeContinuationCachedRetryTelemetryOrderedWindowAppend {
    batch: NativeContinuationCachedRetryTelemetryWindowBatchAppend,
    current_order: NativeContinuationCachedRetryTelemetryBatchOrder,
    previous_order: Option<NativeContinuationCachedRetryTelemetryBatchOrder>,
}

/// Why one externally ordered count-window transition failed without mutation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum NativeContinuationCachedRetryTelemetryOrderedWindowError {
    /// Submitted external order did not strictly advance the current order.
    OrderNotAdvanced {
        /// Exact current order retained by the unchanged owner.
        current: NativeContinuationCachedRetryTelemetryBatchOrder,
        /// Caller-supplied order rejected by the owner.
        submitted: NativeContinuationCachedRetryTelemetryBatchOrder,
    },
    /// Ordered summary batch could not commit transactionally to the FIFO.
    Window(NativeContinuationCachedRetryTelemetryWindowError),
}

impl NativeContinuationCachedRetryTelemetryBatchOrder {
    /// Constructs one opaque caller-authoritative order stamp.
    #[must_use]
    pub const fn from_value(value: u64) -> Self {
        Self(value)
    }

    /// Returns the exact caller-supplied order value.
    #[must_use]
    pub const fn value(self) -> u64 {
        self.0
    }
}

impl NativeContinuationCachedRetryTelemetryOrderedWindowAppend {
    /// Returns exact evidence from the committed destination-local batch
    /// append.
    #[must_use]
    pub const fn batch(
        self,
    ) -> NativeContinuationCachedRetryTelemetryWindowBatchAppend {
        self.batch
    }

    /// Returns the external order committed with this batch.
    #[must_use]
    pub const fn current_order(
        self,
    ) -> NativeContinuationCachedRetryTelemetryBatchOrder {
        self.current_order
    }

    /// Returns the previously committed external order, when one existed.
    #[must_use]
    pub const fn previous_order(
        self,
    ) -> Option<NativeContinuationCachedRetryTelemetryBatchOrder> {
        self.previous_order
    }
}

impl NativeContinuationCachedRetryTelemetryOrderedWindow {
    /// Publishes one caller-ordered summary batch transactionally.
    ///
    /// The first submitted order may be any value. Later submissions must be
    /// strictly greater than the last committed order; gaps remain
    /// caller-owned.
    ///
    /// # Errors
    ///
    /// Returns stale-order or FIFO transition evidence without changing order
    /// or retained telemetry.
    pub fn append_ordered_batch(
        &mut self,
        order: NativeContinuationCachedRetryTelemetryBatchOrder,
        telemetry: &[NativeContinuationCachedRetryTelemetry],
    ) -> Result<
        NativeContinuationCachedRetryTelemetryOrderedWindowAppend,
        NativeContinuationCachedRetryTelemetryOrderedWindowError,
    > {
        if let Some(current) = self.last_order
            && order <= current
        {
            return Err(
                NativeContinuationCachedRetryTelemetryOrderedWindowError::
                    OrderNotAdvanced {
                        current,
                        submitted: order,
                    },
            );
        }
        let previous_order = self.last_order;
        let batch = self.window.append_batch(telemetry).map_err(
            NativeContinuationCachedRetryTelemetryOrderedWindowError::Window,
        )?;
        self.last_order = Some(order);
        Ok(NativeContinuationCachedRetryTelemetryOrderedWindowAppend {
            batch,
            current_order: order,
            previous_order,
        })
    }

    /// Reconstructs exact process-local ordered-window state.
    #[must_use]
    pub const fn from_parts(
        window: NativeContinuationCachedRetryTelemetryWindow,
        last_order: Option<NativeContinuationCachedRetryTelemetryBatchOrder>,
    ) -> Self {
        Self { last_order, window }
    }

    /// Consumes this owner into the exact window and committed external order.
    #[must_use]
    pub fn into_parts(
        self,
    ) -> (
        NativeContinuationCachedRetryTelemetryWindow,
        Option<NativeContinuationCachedRetryTelemetryBatchOrder>,
    ) {
        (self.window, self.last_order)
    }

    /// Consumes this ordered owner into its destination-local telemetry window.
    #[must_use]
    pub fn into_window(self) -> NativeContinuationCachedRetryTelemetryWindow {
        self.window
    }

    /// Returns the last caller-authoritative order committed by this owner.
    #[must_use]
    pub const fn last_order(
        &self,
    ) -> Option<NativeContinuationCachedRetryTelemetryBatchOrder> {
        self.last_order
    }

    /// Constructs an unordered owner around one existing destination window.
    #[must_use]
    pub const fn new(
        window: NativeContinuationCachedRetryTelemetryWindow,
    ) -> Self {
        Self { last_order: None, window }
    }

    /// Borrows the destination-local telemetry window.
    #[must_use]
    pub const fn window(
        &self,
    ) -> &NativeContinuationCachedRetryTelemetryWindow {
        &self.window
    }
}
