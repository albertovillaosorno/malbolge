# Normalized C JSON to Typed IR

## Purpose

Decode the exact pinned Clang version-one frontend JSON into a
source-preserving typed-IR void-return or bounded zero-byte-output projection,
then emit independently re-admitted canonical MCTI bytes. This separate
compiler workspace package contains the JSON dependency; the VM's
dependency-free crate remains unchanged.

## Supported slice

For the effect-free void family, the complete normalized artifact must contain
exactly one no-argument external `fn()->void` definition with a compound
body containing only standalone null statements (`;`), single-digit standalone zero expressions (`0;`),
exact casts of zero to void (`(void)0;`), nested compound scopes, and an
optional final `return;` (including inside a nested scope). Thus
`void noop(void) {}`, `void noop(void) {0; return;}`,
`void noop(void) {(void)0; return;}`, and `void noop(void) {{;}}` compile to
the same verified two-cell guest. An absent explicit return uses the original
function body span to attribute its defined implicit return; no invented C return
statement is inserted into the frontend artifact. The bounded semantic preorder
must preserve node IDs, direct-parent ancestry and nonoverlapping source spans
inside each scope. No statement after an explicit return, no nonzero or
compound cast operand, and no effectful or metadata-drifted nested node can be
discarded. Nested depth is capped at 64, with at most 4094 body nodes per
artifact.
Clang metadata, target identity, source digest spelling, semantic preorder,
parent IDs, field grammar and typed-IR provenance are all checked. Unknown or
duplicate fields, extra source statements and all non-void programs reject.

## First observable guest C output

A separate **exact** pinned-Clang source shape is also executable:

```c
#include <stdio.h>
void emit(void) { putchar(0); return; }
```

The same exact pinned-Clang shape now admits one through 32 **consecutive**
`putchar(0);` calls followed by `return;`, with no other statements. Each
call proves its direct `putchar` reference, single literal-zero argument and
function-to-pointer decay; the complete normalized preorder contains
`4 * outputs + 3` nodes with exact source ancestry and ordered nonoverlapping
spans. The adapter emits one canonical 8-bit zero constant followed by the
corresponding number of `ByteOutput` instructions. The downstream publisher
selects `--initial-zero-output --typed-stdin` and independently checks actual
VM output, ranging from one `0x00` byte to 32 consecutive zero bytes.
Call-result handling, general `putchar`, nonzero byte values, interleaved
statements, `getchar`, EOF, I/O errors, guest libc and C entry ABI remain
unsupported. A 33rd output call refuses compilation rather than truncating.

`canonical_guest_typed_ir` selects this trace or the existing effect-free void
trace without dropping observable effects. `canonical_void_typed_ir` preserves
its prior no-effect-only admission contract and callers.

`canonical_void_typed_ir` returns no-effect MCTI bytes for
`malbolge_layout --empty-void --typed-stdin` while
`canonical_guest_typed_ir` additionally returns a mode for the supported
bounded zero-byte output trace. This adapter does not invoke Clang, authenticate an
independently supplied C source against its JSON SHA-256, implement a complete
C command line, realize C process-return ABI or replace the independent guest
VM preflight. Its tests run both accepted families through real guest code.

## Executable handoff

`c2malbolge_json` accepts normalized JSON on **stdin**, an explicit trusted
`malbolge_layout` executable, and a fresh `.malbolge` output path. It validates
JSON, produces canonical MCTI, and selects the exact verified
`--empty-void` or `--initial-zero-output` mode with `--typed-stdin`.
Optional `--capsule` uses the current profile's embedded identity. The compiler frontend itself must have
produced the normalized JSON; the pipeline does not infer semantics from raw C
text or trust an unverified substitute for the selected layout backend.

```sh
malbolge_c_frontend --guest-include GUEST_INCLUDE \
  --resource-dir RESOURCE_DIR --source-id program.c program.c |
  c2malbolge_json --layout-backend malbolge_layout \
    --output program.malbolge --capsule
```

The pinned Clang 22.1.8 frontend executable and its target headers are required
for this source-driven command. Real native C-to-VM process evidence is now
covered by `tests/test_c2malbolge_native_pipeline.py` on hosts with the native
frontend and Rust guest binaries available. The test accepts explicitly named
frontend/resource paths when repository-pinned provisions are absent. This
does not claim an automated turnkey install or broader C language coverage.
The explicit executable path is a caller-trusted capability, not discovered via
`PATH` implicitly.
