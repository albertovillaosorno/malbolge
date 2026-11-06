// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - LicenseRef-Proprietary
// Confidential:
//   - true
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Source-bound constant reassignment of automatic unsigned C storage.
// - Must-Not:
//   - Claim arithmetic, aliasing, dynamic assignments, or loops are lowered.
// - Allows:
//   - Inputs: one automatic unsigned with ordered literal reassignments.
//   - Outputs: the last assigned byte via real guest putchar semantics.
//   - Side effects: guest output only.
// - Split-When:
//   - General mutable C state lowering subsumes the bounded regression.
// - Merge-When:
//   - General compiler matrix includes exact local assignment provenance.
// - Summary:
//   - A real C write replaces an earlier initialized local value.
// - Description:
//   - Reject discarding assignments or using the stale initializer.
// - Usage:
//   - Replayed through pinned Clang, typed IR, layout, and guest VM.
// - Defaults:
//   - Unsupported mutations never publish a guest artifact.

#include <stdio.h>

void emit(void) {
    unsigned value = 0U;
    value = 66U;
    value = 65U;
    putchar(value);
}
