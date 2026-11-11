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
//   - A real three-distinct-byte C-to-Malbolge source example.
// - Must-Not:
//   - Substitute host I/O or claim arbitrary character-string support.
// - Allows:
//   - Inputs: repository-pinned Clang and public guest stdio declaration.
//   - Outputs: three separately computed VM-verified bytes, ASCII Z%H.
//   - Side effects: guest byte output only.
// - Split-When:
//   - General guest output streams supersede bounded distinct triples.
// - Merge-When:
//   - Compiler examples demonstrate arbitrary mixed-byte output.
// - Summary:
//   - Source C emits Z%H via three verified guest CrazyData writes.
// - Description:
//   - The compiler and normative VM independently verify all three bytes.
// - Usage:
//   - c2malbolge --repository-tools --capsule --output .temp/emit-zph.malbolge
//     src/interface/command-line/composition/examples/emit-zph.c
// - Defaults:
//   - No general printf, string literals or arbitrary byte transitions.
//
#include <stdio.h>

void emit(void) {
  putchar('Z');
  putchar('%');
  putchar('H');
}
