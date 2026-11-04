# Normalized C JSON to Typed IR

## Purpose

Decode the exact pinned Clang version-one frontend JSON into a
source-preserving typed-IR void-return or bounded literal-byte-output projection,
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

## Witnessed guest C output

A separate **exact** pinned-Clang source shape is also executable:

```c
#include <stdio.h>
void emit(void) { putchar(0); return; }
```

The exact pinned-Clang shape admits one through 33 calls to
`putchar(N);` with optional final `return;`, where every `N` emits the same
low-eight-bit byte. The evaluated C integer is a nonnegative `i32` value
(including `256..2147483647`) and must be a bounded single-line integer token
(decimal, octal, hexadecimal or C23 binary) or a single C character literal
(including bounded escape spellings). One optional exact single pair of
parentheses or an unsigned `u32` integer token converted to `i32` is also
admitted per call. For example, `putchar((65)); putchar(65u);`,
`putchar(0x41); putchar(0101);`, `putchar(321); putchar(65);`, and
`putchar('\0');` retain Clang's source spans and evaluated integer values.
The C `putchar` low-byte conversion is applied only after checked `i32`
admission, never by truncating a malformed or overflowing JSON integer.
Each call proves its direct `putchar` reference, one exact literal argument
and function-to-pointer decay;
the complete normalized preorder contains four or five nodes per call, plus
two structural nodes and optional explicit `return;`, preserving exact source
ancestry and ordered nonoverlapping spans. Lexical compound scopes may contain
these calls and inert statements; each nested scope preserves its own Clang
parent ID, checked source span and original output order. The adapter admits at
most 128 nested scopes with depth at most 64. Up to 128 inert statements
(`;`, `0;`, or `(void)0;`) may occur before, between or after calls at any
admitted depth. Each complete source-bound node is checked without inventing
guest I/O for an inert statement. Nonzero literal expressions, early nested
returns, unexpected metadata, effectful nested bodies and other side effects
still reject. The adapter emits one canonical `u8` constant and
the corresponding number of `ByteOutput` effects.
For zero, the downstream publisher uses `--initial-zero-output --typed-stdin`,
which independently verifies guest stdout of one to 33 NUL bytes. Nonzero
bytes use the separate `--seeded-byte-literal --typed-stdin` backend, where
each byte/count combination must have its own position-sensitive guest-VM
witness. For example, one `putchar(23)`, two `putchar(65)` calls and three
`putchar(146)` calls, and thirty-three `putchar(40)` calls compile and
execute with exact byte output. One `putchar(65)` also has an independently
checked single-byte guest crazy-operation witness. The backend's currently
witnessed subset is enumerated in
`src/compiler/byte-echo-bridge/README.md`; **not** every value or count is
realizable. Integer tokens over 32 source bytes, negative or unrepresentable
`i32` values, and more than 33 calls refuse source admission. An
unwitnessed combination fails layout admission without publishing a `.malbolge` artifact.

An omitted final `return;` uses the original function body span to model
C's defined implicit void return; no synthetic source statement is added.
Nested parentheses, nonliteral arithmetic, call-result handling, arbitrary
output streams, interleaved effectful statements,
`getchar`, EOF, I/O errors, general guest libc and C entry ABI remain
unsupported. Mixing distinct **output bytes** in one source refuses
admission; distinct `i32` literals with the same low byte preserve their own
source spans.
The pinned Clang frontend must supply the source-bound integer or character
token, its canonical evaluated `i32` value and a bounded single-line span;
the adapter never decodes C integer or escape syntax or accepts fabricated
byte constants.

`canonical_guest_typed_ir` selects this trace or the existing effect-free void
trace without dropping observable effects. `canonical_void_typed_ir` preserves
its prior no-effect-only admission contract and callers.

`canonical_void_typed_ir` returns no-effect MCTI bytes for
`malbolge_layout --empty-void --typed-stdin` while
`canonical_guest_typed_ir` additionally returns a mode for the supported
bounded literal-byte output trace. This adapter does not invoke Clang, authenticate an
independently supplied C source against its JSON SHA-256, implement a complete
C command line, realize C process-return ABI or replace the independent guest
VM preflight. Its tests run both accepted families through real guest code.

## Executable handoff

`c2malbolge_json` accepts normalized JSON on **stdin**, an explicit trusted
`malbolge_layout` executable, and a fresh `.malbolge` output path. It validates
JSON, produces canonical MCTI, and selects the exact verified
`--empty-void`, `--initial-zero-output`, or `--seeded-byte-literal` mode
with `--typed-stdin`.
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
