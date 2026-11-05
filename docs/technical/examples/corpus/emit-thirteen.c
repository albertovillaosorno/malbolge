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
//   - One thirteen-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: four ASCII bytes, two control bytes and seven high-bit bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits BC0, SYN, T, TAB and seven distinct high-bit bytes.
// - Description:
//   - The compiler and real VM independently verify thirteen ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-thirteen.malbolge \
//     docs/technical/examples/corpus/emit-thirteen.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar('B');
  putchar('C');
  putchar('0');
  putchar(22);
  putchar('T');
  putchar(9);
  putchar(191);
  putchar(198);
  putchar(200);
  putchar(135);
  putchar(227);
  putchar(171);
  putchar(164);
}
