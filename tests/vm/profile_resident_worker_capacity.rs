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
//   - Resident subprocess worker-permit capacity regression.
// - Must-Not:
//   - Spawn real devices or change guest execution semantics.
// - Allows:
//   - Inputs: isolated atomic counters and the exact worker-permit contract.
//   - Outputs: checked capacity exhaustion and release invariants.
//   - Side effects: temporary process-local permit ownership.
// - Split-When:
//   - Worker lifecycle gains more independently owned resource constraints.
// - Merge-When:
//   - Permit capacity is checked by another equivalent test surface.
// - Summary:
//   - Proves worker slots remain reserved until the owner drops.
// - Description:
//   - Holds all permits, rejects overflow, and validates RAII release.
// - Usage:
//   - Included only by the resident process adapter during library unit tests.
// - Defaults:
//   - Does not touch the production process-global worker counter.
//

//! Isolated resident subprocess worker-capacity tests.

use std::sync::atomic::{AtomicUsize, Ordering};

use super::{MAX_RESIDENT_EXCHANGE_WORKERS, ResidentExchangePermit};

#[test]
fn worker_permits_bound_capacity_until_owner_drops() {
    let active = AtomicUsize::new(0);
    let permits: Vec<_> = (0..MAX_RESIDENT_EXCHANGE_WORKERS)
        .filter_map(|_| {
            ResidentExchangePermit::acquire(
                &active,
                MAX_RESIDENT_EXCHANGE_WORKERS,
            )
        })
        .collect();
    assert_eq!(permits.len(), MAX_RESIDENT_EXCHANGE_WORKERS);
    assert_eq!(
        active.load(Ordering::Acquire),
        MAX_RESIDENT_EXCHANGE_WORKERS
    );
    assert!(ResidentExchangePermit::acquire(
        &active,
        MAX_RESIDENT_EXCHANGE_WORKERS,
    ).is_none());
    drop(permits);
    assert_eq!(active.load(Ordering::Acquire), 0);
    assert!(ResidentExchangePermit::acquire(
        &active,
        MAX_RESIDENT_EXCHANGE_WORKERS,
    ).is_some());
    assert_eq!(active.load(Ordering::Acquire), 0);
}
