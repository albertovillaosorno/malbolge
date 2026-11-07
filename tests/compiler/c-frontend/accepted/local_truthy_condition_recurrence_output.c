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
//   - Source-proven unsigned truthiness in a bounded complete C loop.
// - Must-Not:
//   - Claim runtime guest comparison, guest state or general control flow.
// - Allows:
//   - Inputs: checked automatic unsigned locals and a scalar truthiness predicate.
//   - Outputs: source-derived final byte emitted by the actual Malbolge VM.
//   - Side effects: final putchar only, after compile-time constant folding.
// - Split-When:
//   - General guest control-flow lowering subsumes closed relational folding.
// - Merge-When:
//   - Complete source-to-guest C comparisons provide the same semantics.
// - Summary:
//   - Prove zero/nonzero conditional selection in a stateful C recurrence.
// - Description:
//   - Both branch arms are selected across three bounded loop iterations.
// - Usage:
//   - Compile through pinned frontend and independently replay the guest VM.
// - Defaults:
//   - Unknown operators, source effects and non-u32 operands must refuse.
//
#include <stdio.h>

void emit(void) {
    unsigned a = 3U;
    unsigned b = 5U;
    for (unsigned i = 0U; i < 3U; ++i) {
        unsigned next = ((a * b) << 2U) & 255U;
        if ((next & 8U)) {
            a = (next >> 3U) ^ 1U;
        } else {
            a = next - 1U;
        }
        b = next;
    }
    putchar((int)(a ^ 62U));
}
