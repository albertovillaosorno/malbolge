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

On Unix, the `composition/scripts/c2malbolge` executable shim invokes this
same Python 3.14 driver with unchanged options and exit status. The existing
`composition/scripts/install-unix.sh [destination]` now installs both
`malbolge` and `c2malbolge` command symlinks. Each shim resolves its original
repository script path even when invoked through an installation symlink;
installation does not build the native C frontend or Rust binaries.

When the repository-pinned Clang frontend and Rust binaries have already been
built, an opt-in shortcut selects those exact repository-local tools and
resources without copying their paths or inventing normalized JSON:

```sh
python3.14 -B src/interface/command-line/composition/scripts/c2malbolge.py \
  --repository-tools --capsule --output .temp/noop.malbolge examples/noop.c
```

After installing the Unix shims into a directory on `PATH`, the same command
can be run directly as:

```sh
c2malbolge --repository-tools --capsule \
  --output .temp/noop.malbolge examples/noop.c
malbolge --repository-tools .temp/noop.malbolge --report-steps
```

For the **Unix `malbolge` shim**, a leading `--repository-tools` selects the
existing repository-built `.cache/rust/target/debug/malbolge` VM. This is useful
when the `scripts/bin/malbolge` release binary was built against older sources:
the compiler and guest runner then use the current repository binaries. If the
debug VM has not been built, this explicit selector rejects without silently
running an outdated release VM. Without the selector, `malbolge` retains its
original installed-release behavior; `build-unix.sh` refreshes that release
binary. This wrapper selector is not forwarded to the normative VM.

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
arbitrary C compiler. It currently accepts only the exact normalized
Clang shapes admitted by the JSON adapter: effect-free void functions
(including nested scopes, standalone `0;` and `(void)0;`), and consecutive
`putchar(N);` statements followed by `return;` in a void function. One to
32 writes of `0` produce actual NUL bytes. Only independently witnessed
nonzero byte/count pairs can compile: currently `23` once, `65` twice, or
`146` three times. Other nonzero values/counts, mixed byte values,
noncanonical integer spellings, interleaved effects, excess calls, the
general C process-return ABI and guest libc remain unsupported rather than
silently dropping effects. Each accepted output runs in the independent VM.
The pinned Clang frontend is required for real source compilation; its
absence cannot be replaced by synthetic JSON test evidence. The three source
digest reads constrain a specific invocation, not a persistent filesystem
snapshot; external consumers must still manage later source changes.
