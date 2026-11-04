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
//   - A real five-distinct-byte C-to-Malbolge binary source example.
// - Must-Not:
//   - Substitute host I/O or claim arbitrary binary streams.
// - Allows:
//   - Inputs: repository-pinned Clang and public guest stdio declarations.
//   - Outputs: five independently computed guest bytes, including ESC.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest binary byte streams supersede bounded sequences.
// - Merge-When:
//   - Compiler examples demonstrate arbitrary mixed-byte output.
// - Summary:
//   - Source C emits Q, double quote, ESC, 7, 9 from guest CrazyData writes.
// - Description:
//   - The compiler and normative VM independently verify each emitted byte.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-qesc79.malbolge \
//     docs/technical/examples/corpus/emit-qesc79.c
// - Defaults:
//   - Only this exact five-output trace is currently witnessed.
//
#include <stdio.h>

void emit(void) {
  putchar('Q');
  putchar('"');
  putchar(27);
  putchar('7');
  putchar('9');
}
