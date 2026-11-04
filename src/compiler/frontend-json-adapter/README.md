# Normalized C JSON to Typed IR

## Purpose

Decode the exact pinned Clang version-one frontend JSON into the existing
source-preserving typed-IR void-return projection, then emit independently
re-admitted canonical MCTI bytes. This separate compiler workspace package
contains the JSON dependency; the VM's dependency-free crate remains unchanged.

## Supported slice

For the effect-free void family, the complete normalized artifact must contain exactly one no-argument external
`fn()->void` definition with a compound body containing only standalone
null statements (`;`), single-digit standalone zero expressions (`0;`),
exact casts of zero to void (`(void)0;`), nested compound scopes, and an optional final `return;` (including inside
a nested scope). Thus `void noop(void) {}`, `void noop(void) {0; return;}`,
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

Its seven normalized nodes must prove a direct `putchar(0)` call with one
literal-zero argument, exact function-to-pointer callee decay, a terminal void
return, and no other effects. The adapter emits canonical MCTI containing an
8-bit zero constant and one `ByteOutput` instruction. The downstream publisher
selects `--initial-zero-output --typed-stdin` and independently verifies the
result through the real Malbolge VM. Guest stdout contains exactly `0x00`.
This is successful-output evidence only: call-result handling, general
`putchar`, other byte values, `getchar`, EOF, I/O errors, guest libc and C entry
ABI remain unsupported. Nonzero or multiple output calls refuse compilation.

`canonical_guest_typed_ir` selects this trace or the existing effect-free void
trace without dropping observable effects. `canonical_void_typed_ir` preserves
its prior no-effect-only admission contract and callers.

`canonical_void_typed_ir` returns MCTI bytes ready for the opt-in
`malbolge_layout --empty-void --typed-stdin` publisher. This adapter does not
invoke Clang, authenticate a separately supplied C source against its JSON
SHA-256, implement a complete C command line, realize C process-return ABI or
replace the independent guest VM preflight. Its tests exercise the real
normalized-artifact data shape and independently compile the accepted result
into the existing two-step guest program.

## Executable handoff

`c2malbolge_json` accepts normalized JSON on **stdin**, an explicit trusted
`malbolge_layout` executable, and a fresh `.malbolge` output path. It validates
JSON, produces canonical MCTI, and pipes those bytes to the existing
`--empty-void --typed-stdin` verifier/publisher. Optional `--capsule` uses the
current profile's embedded identity. The compiler frontend itself must have
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
