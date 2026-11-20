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
//   - C23 two signed reads, first EOF coalescence, and second EOF branch.
// - Must-Not:
//   - Infer second EOF from first input or discard either real read.
// - Allows:
//   - Inputs: zero, one, or more binary stdin bytes.
//   - Outputs: first value or 106 on EOF, then 30 on second EOF or 154.
//   - Side effects: getchar and putchar only.
// - Split-When:
//   - General signed C23 branching replaces source-bound admission.
// - Merge-When:
//   - General dynamic CFG linker passes original mutable checksum.
// - Summary:
//   - Real second-byte-dependent C23 branch matches a physical guest path.
//
#include <stdio.h>

void emit(void) {
    int first = getchar();
    putchar(first == EOF ? 106 : first);
    int second = getchar();
    if (second == EOF) {
        putchar(30);
    } else {
        putchar(154);
    }
}
