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
the layout backend independently verifies the guest program. The driver stages
the result privately, rechecks the original C source after guest compilation,
and publishes via an atomic no-clobber link only if the source is still stable.
Failures and late output-name collisions leave no published guest artifact from
the driver; the layout backend retains its own no-clobber and VM checks.

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

When the repository-pinned Clang frontend and Rust binaries have already been
built, an opt-in shortcut selects those exact repository-local tools and
resources without copying their paths or inventing normalized JSON:

```sh
python3.14 -B src/interface/command-line/composition/scripts/c2malbolge.py \
  --repository-tools --capsule --output .temp/noop.malbolge examples/noop.c
```

`--repository-tools` selects the pinned LLVM 22.1.8 frontend, Clang resource
directory, guest headers and existing `c2malbolge_json` / `malbolge_layout`
Rust binaries. It does not install or build them; missing tools fail rather than
falling back to host Clang or synthetic JSON. The source ID defaults to the
source filename (use `--source-id` for an explicit portable identity). Tool
path overrides cannot be mixed with this mode. Source identity checks, guest
verification, private staging, no-clobber publication and `--capsule` semantics
are identical to the explicit-tool invocation. This is a repository development
shortcut, not an automatic production compiler installation.

In explicit-tool mode all three executables are caller-trusted capabilities.
This is a
bounded integration entrypoint, **not** the finished turnkey installer or
arbitrary C compiler. It currently accepts only the normalized Clang shape
supported by the JSON adapter (one no-effect `void` function with optional
null statements (`;`) and optional final `return;`), and does not implement C
process-return ABI or guest libc.
The pinned Clang frontend is required for real source compilation; its
absence cannot be replaced by synthetic JSON test evidence. The three source
digest reads constrain a specific invocation, not a persistent filesystem
snapshot; external consumers must still manage later source changes.
