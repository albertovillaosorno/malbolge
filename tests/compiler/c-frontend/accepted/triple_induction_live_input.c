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
//   - Three-level source-proven unsigned induction for real guest byte I/O.
// - Must-Not:
//   - Infer a counter from an unrelated scope or fold live guest stdin.
// - Allows:
//   - Inputs: eight successful live bytes in nested finite induction.
//   - Outputs: nine writes with the sixth guest byte duplicated.
//   - Side effects: eight getchar and nine putchar calls.
// - Split-When:
//   - General guest C runtime branching subsumes finite induction selection.
// - Merge-When:
//   - Arbitrary finite counter scopes replace the bounded ancestor proof.
// - Summary:
//   - A three-counter conjunction selects plane two, row one, column two.
//
#include <stdio.h>
void emit(void) {
    for (unsigned plane = 1U; plane <= 2U; plane += 1U) {
        for (unsigned row = 1U; row <= 2U; row += 1U) {
            for (unsigned col = 1U; col <= 2U; col += 1U) {
                int current = getchar();
                if (plane == 2U && row == 1U && col == 2U) {
                    putchar(current);
                    putchar(current);
                } else {
                    putchar(current);
                }
            }
        }
    }
}
