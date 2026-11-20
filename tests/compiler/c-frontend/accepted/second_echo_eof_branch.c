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
//   - C23 two signed input values, a second-value echo, and a real EOF branch.
// - Must-Not:
//   - Substitute a host decision for the guest's signed EOF control.
// - Allows:
//   - Inputs: zero or more binary stdin bytes.
//   - Outputs: both input low bytes (106 on EOF), then the second EOF marker.
//   - Side effects: two getchar calls and three putchar calls.
// - Split-When:
//   - General signed C23 conditional byte I/O subsumes this bounded proof.
// - Merge-When:
//   - A verified general guest control-flow linker can express this program.
// - Summary:
//   - Echo the runtime second byte before reporting its true EOF/byte branch.
//
#include <stdio.h>

void emit(void) {
    int first = getchar();
    putchar(first == EOF ? 106 : first);
    int second = getchar();
    if (second == EOF) {
        putchar(106);
        putchar(30);
    } else {
        putchar(second);
        putchar(154);
    }
}
