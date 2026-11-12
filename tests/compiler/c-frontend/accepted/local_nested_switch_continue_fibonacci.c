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
//   - Whole C recurrence with loop continuation from nested switch arms.
// - Must-Not:
//   - Project unsupported guest C control or fake runtime output.
// - Allows:
//   - Inputs: pinned C23 bounded local arithmetic and nested switching.
//   - Outputs: twelve source-selected guest bytes.
//   - Side effects: source-proven putchar in selected switch cases.
// - Split-When:
//   - General C runtime control flow replaces finite source replay.
// - Merge-When:
//   - Independent guest control-flow matrix subsumes this example.
// - Summary:
//   - Nested switches carry loop continue and recurrence state updates.
//

#include <stdio.h>
void emit(void) {
    unsigned a = 1U;
    unsigned b = 1U;
    for (unsigned i = 0U; i < 12U; ++i) {
        unsigned next = (a + b) & 255U;
        switch (next & 2U) {
        case 0U:
            switch (next & 1U) {
            case 0U:
                putchar((int)(next & 31U));
                a = b;
                b = next;
                continue;
            default:
                putchar((int)((next ^ 0x1AU) & 31U));
                a = b;
                b = next;
                break;
            }
            break;
        default:
            switch (next & 1U) {
            case 0U:
                putchar((int)(next & 31U));
                a = b;
                b = next;
                continue;
            default:
                putchar((int)((next ^ 0x1AU) & 31U));
                a = b;
                b = next;
                break;
            }
            break;
        }
    }
}
