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
//   - One twenty-one-distinct-byte C-to-Malbolge teaching source.
// - Must-Not:
//   - Substitute host output or claim arbitrary byte-stream lowering.
// - Allows:
//   - Inputs: pinned C frontend and guest stdio declarations.
//   - Outputs: ten printable, six control and five high-bit bytes.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest byte-stream lowering supersedes finite witnesses.
// - Merge-When:
//   - Compiler examples demonstrate general mixed-byte output.
// - Summary:
//   - Emits twenty-one ordered and distinct guest-computed binary bytes.
// - Description:
//   - The compiler and real VM independently verify twenty-one ordered bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule \
//     --output .temp/emit-twenty-one.malbolge \
//     docs/technical/examples/corpus/emit-twenty-one.c
// - Defaults:
//   - This finite trace is not general C byte-stream support.
//
#include <stdio.h>

void emit(void) {
  putchar(65);
  putchar(14);
  putchar(59);
  putchar(15);
  putchar(63);
  putchar(10);
  putchar(64);
  putchar(142);
  putchar(38);
  putchar(146);
  putchar(39);
  putchar(150);
  putchar(34);
  putchar(151);
  putchar(141);
  putchar(21);
  putchar(49);
  putchar(24);
  putchar(53);
  putchar(26);
  putchar(47);
}
