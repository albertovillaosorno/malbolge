# Normalized C JSON to Typed IR

## Purpose

Decode the exact pinned Clang version-one frontend JSON into the existing
source-preserving typed-IR void-return projection, then emit independently
re-admitted canonical MCTI bytes. This separate compiler workspace package
contains the JSON dependency; the VM's dependency-free crate remains unchanged.

## Supported slice

The complete normalized artifact must contain exactly one no-argument external
`fn()->void` definition with a compound body containing optional standalone
null statements (`;`) and an optional final `return;`. Thus both
`void noop(void) {}` and `void noop(void) {; ; return;}` compile to the same
verified two-cell guest. An absent explicit return uses the original body
span to attribute its defined implicit return; no invented C return statement
is inserted into the frontend artifact. Null statements must have source-order,
source-span and direct-parent evidence; they are the only ignored nodes.
Clang metadata, target identity, source digest spelling, semantic preorder,
parent IDs, field grammar and typed-IR provenance are all checked. Unknown or
duplicate fields, extra source statements and all non-void programs reject.

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
for this source-driven command, and are absent from the current test host. The
adapter's normalized-JSON acceptance and real-VM test do not claim that the
complete native source command was executed. The explicit executable path is
a caller-trusted capability, not discovered via `PATH` implicitly.
