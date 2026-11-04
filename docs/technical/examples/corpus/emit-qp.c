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
//   - A real two-distinct-byte C-to-Malbolge source example.
// - Must-Not:
//   - Substitute host I/O or claim arbitrary character-string support.
// - Allows:
//   - Inputs: repository-pinned Clang and public guest stdio declaration.
//   - Outputs: two separately computed VM-verified bytes, ASCII Q and period.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest output streams supersede bounded distinct pair witnesses.
// - Merge-When:
//   - Compiler examples demonstrate arbitrary mixed-byte output.
// - Summary:
//   - Source C emits Q. via two exact guest CrazyData instructions.
// - Description:
//   - The compiler and normative VM independently verify both guest bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule --output .temp/emit-qp.malbolge
//     src/interface/command-line/composition/examples/emit-qp.c
// - Defaults:
//   - No general printf, string literals or repeated-byte assumption.
//
#include <stdio.h>

void emit(void) {
  putchar('Q');
  putchar('.');
}
