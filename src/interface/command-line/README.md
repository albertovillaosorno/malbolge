# Command Line

## Purpose

The user-facing Malbolge command-line interface.

## Ownership

This boundary is owned by `function:command-line`.

## Prohibitions

It must not bypass another function or architectural kind boundary.

## Navigation

- [`contract/reference.md`](contract/reference.md): detailed
  pre-migration reference.
- `adapter-outbound/`: governed `adapter-outbound` parts.
- `application/`: governed `application` parts.
- `composition/`: governed `composition` parts.
- `contract/`: governed `contract` parts.

## Exact guest byte input

`malbolge program.malbolge` retains its existing deterministic empty-input
behavior: each `/` instruction observes the selected profile's EOF value.
`malbolge program.malbolge --input-stdin` explicitly reads at most 256 raw
bytes from standard input before loading the VM, then passes the complete byte
vector to the normative classic or capsule-selected profile VM. NUL, `0xA8`,
`0xFF`, and any other byte are data, not delimiters; after consumption the
profile's defined EOF value applies. This mode is bounded to 257 read bytes
for limit admission, then rejects overlong inputs before executing any guest
instruction. The input stream must close to signal EOF. The flag is not
forwarded to native C debug runs, which retain their existing argument model.

Example (the source must itself read and output bytes):

```sh
printf '\000A' | malbolge program.malbolge --input-stdin
```

The CLI does not authenticate the origin of supplied bytes or enforce a whole
process resource budget. It does not change interpreter semantics, restore
program state between runs, or claim that an arbitrary program reads stdin.

## Opt-in guest instruction count

`malbolge program.malbolge --report-steps` writes one machine-readable
`malbolge-steps-v1:<decimal>` line to **stderr** after successful VM
termination. The count is the sum of the normative VM `RunOutcome` committed
instruction counts, including the terminating instruction and all completed
execution chunks; it is not inferred from source length. It works with classic
raw programs and selected-profile capsules (including the profile batch
backend). `--input-stdin` and `--report-steps` can appear in either order and
at most once each; no option silently enables the other. Without the report
flag, stderr remains unchanged. Guest stdout remains exactly the guest bytes.

This count is observable execution evidence on the selected local VM, not a
proof of timing precision, host CPU instructions, physical power or a memory
budget. For long-running or externally interrupted programs, no successful
terminal count is issued. A failing stderr write reports a nonzero exit.

## Bounded source-C-to-guest composition (opt-in)

`composition/scripts/c2malbolge.py` composes the existing pinned native C
frontend, the normalized JSON-to-typed adapter, and the verified Malbolge
layout publisher in **sequence**. A nonzero frontend exit, oversized JSON,
changed C source, or JSON source-ID/SHA-256 mismatch stops before invoking the
JSON adapter. The adapter then performs canonical typed/ternary admission;
the layout backend independently verifies and publishes the resulting guest
program with its no-clobber and VM checks.

```sh
python3.14 -B src/interface/command-line/composition/scripts/c2malbolge.py \
  --frontend /path/to/malbolge_c_frontend \
  --json-adapter /path/to/c2malbolge_json \
  --layout-backend /path/to/malbolge_layout \
  --guest-include /path/to/guest/include \
  --resource-dir /path/to/pinned/clang/resources \
  --source-id examples/noop.c --output .temp/noop.malbolge \
  --capsule examples/noop.c
```

All three executables are explicit caller-trusted capabilities. This is a
bounded integration entrypoint, **not** the finished turnkey installer or
arbitrary C compiler. It currently accepts only the normalized Clang shape
supported by the JSON adapter (one no-effect `void` function with either an
empty body or an explicit `return;`), and does not implement C process-return
ABI or guest libc.
The pinned Clang frontend is required for real source compilation; its
absence cannot be replaced by synthetic JSON test evidence. The two source
reads constrain a specific invocation, not a persistent filesystem snapshot.
