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
//   - One eighteen-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: four printable, four control and ten high-bit bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits eighteen ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify eighteen ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-eighteen.malbolge \
//     docs/technical/examples/corpus/emit-eighteen.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(84);
  putchar(34);
  putchar(25);
  putchar(62);
  putchar(56);
  putchar(3);
  putchar(9);
  putchar(221);
  putchar(135);
  putchar(209);
  putchar(165);
  putchar(153);
  putchar(191);
  putchar(8);
  putchar(199);
  putchar(198);
  putchar(194);
  putchar(145);
}
