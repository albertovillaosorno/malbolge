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
//   - Three-level finite C induction with selected inner loop exits.
// - Must-Not:
//   - Turn an inner break into an outer exit or re-read a continued byte.
// - Allows:
//   - Inputs: seven live bytes in three scoped unsigned loops.
//   - Outputs: eight writes with the third byte duplicated.
//   - Side effects: seven getchar and eight putchar calls.
// - Split-When:
//   - Runtime loop control replaces finite source-time effects.
// - Merge-When:
//   - General scoped C control-flow lowering subsumes the bounded proof.
// - Summary:
//   - One continue and one inner break preserve the enclosing loops.
//
#include <stdio.h>
void emit(void) {
    for (unsigned plane = 1U; plane <= 2U; plane += 1U) {
        for (unsigned row = 1U; row <= 2U; row += 1U) {
            for (unsigned col = 1U; col <= 2U; col += 1U) {
                int current = getchar();
                if (plane == 1U && row == 2U && col == 1U) {
                    putchar(current);
                    putchar(current);
                    continue;
                }
                if (plane == 2U && row == 1U && col == 1U) {
                    putchar(current);
                    break;
                }
                putchar(current);
            }
        }
    }
}
