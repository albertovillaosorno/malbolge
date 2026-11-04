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
//   - A real four-distinct-byte C-to-Malbolge source example.
// - Must-Not:
//   - Substitute host I/O or claim arbitrary character-string support.
// - Allows:
//   - Inputs: repository-pinned Clang and public guest stdio declaration.
//   - Outputs: four separately computed VM-verified bytes, ASCII T=4>.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest output streams supersede bounded distinct sequences.
// - Merge-When:
//   - Compiler examples demonstrate arbitrary mixed-byte output.
// - Summary:
//   - Source C emits T=4> via four verified guest CrazyData writes.
// - Description:
//   - The compiler and normative VM independently verify all four bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule --output .temp/emit-t4.malbolge
//     src/interface/command-line/composition/examples/emit-t4.c
// - Defaults:
//   - No general printf, string literals or arbitrary byte transitions.
//
#include <stdio.h>

void emit(void) {
  putchar('T');
  putchar('=');
  putchar('4');
  putchar('>');
}
