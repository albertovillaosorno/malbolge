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

## Explicit raw target-profile execution

Raw `.malbolge` source contains no profile identity. By default,
`malbolge program.malbolge` therefore retains classic interpreter semantics.
If the caller already knows the canonical profile under which an unframed
artifact was compiled, select it explicitly:

```sh
malbolge .temp/raw-current.malbolge --raw-profile malbolge-2026 \
  --report-steps
```

`--raw-profile ID` selects the exact registered profile with no inference from
source contents or fallback to a different profile. It supports the same
`--input-stdin` and `--report-steps` options in any order. Unknown IDs, missing
values and duplicate flags fail before guest execution. The option **cannot**
be used with a capsule: capsule identity and fingerprint remain authoritative,
and attempting to override either fails before guest execution. Prefer capsules
from `malbolge compile` for self-describing, portable current-profile output.
An explicitly selected *current-profile raw* program uses the same opt-in
adaptive-width and resident-worker settings as a current-profile capsule;
the default classic raw path remains unaffected. The option does not apply
to host-only `.c` debug execution.

## Opt-in guest instruction count

`malbolge program.malbolge --report-steps` writes one machine-readable
`malbolge-steps-v1:<decimal>` line to **stderr** after successful VM
termination. The count is the sum of the normative VM `RunOutcome` committed
instruction counts, including the terminating instruction and all completed
execution chunks; it is not inferred from source length. It works with classic
raw programs, explicitly selected raw profiles, and selected-profile
capsules (including the profile batch backend). `--input-stdin` and
`--report-steps` can appear in either order and at most once each; no option
silently enables the other. Without the report flag, stderr remains unchanged.
Guest stdout remains exactly the guest bytes.

This count is observable execution evidence on the selected local VM, not a
proof of timing precision, host CPU instructions, physical power or a memory
budget. For long-running or externally interrupted programs, no successful
terminal count is issued. A failing stderr write reports a nonzero exit.

## One-command bounded C-to-Malbolge compilation

After building the repository-pinned C frontend, Rust JSON adapter, layout
backend, and public `malbolge` binary, the top-level command exposes the same
verified pipeline as the Python driver without manual intermediate stages:

```sh
malbolge compile src/interface/command-line/composition/examples/emit-plus.c \
  -o .temp/compiled-plus.malbolge
malbolge .temp/compiled-plus.malbolge --report-steps
```

The first command publishes a current-profile `.malbolge` **capsule** and the
second independently executes it with the normative VM, emitting `+`. On Unix,
use `malbolge --repository-tools compile ...` through the installed shim to
select the current debug CLI while the installed release binary is stale.
The compile mode accepts exactly one `.c` path followed by `-o` and a fresh
`.malbolge` path. It inherits stable source-digest checking, source bounds,
exact pinned tool selection, independent guest acceptance, atomic no-clobber
publication, and nonzero diagnostics from `c2malbolge.py`. It never runs C on
the host as a compilation substitute. Existing `malbolge program.c` remains a
separate host-only *debug run*.

The command requires Python 3.14 (repository-provisioned when available,
otherwise `python3.14` on Unix `PATH` or `py -3.14` on Windows), plus the
already-built pinned tools. It does not bootstrap, download, or rebuild them.
This is a working slice for the
currently bounded admitted C shapes, **not** the completed turnkey installer,
a full C compiler, or CUDA evidence. For explicit tool paths, direct use of
`c2malbolge.py` remains supported below.

## Bounded source-C-to-guest composition (opt-in)

`composition/scripts/c2malbolge.py` composes the existing pinned native C
frontend, the normalized JSON-to-typed adapter, and the verified Malbolge
layout publisher in **sequence**. A nonzero frontend exit, oversized JSON,
changed C source, or JSON source-ID/SHA-256 mismatch stops before invoking the
JSON adapter. The adapter then performs canonical typed/ternary admission;
the layout backend independently verifies the guest program. The driver stages
the result privately, rechecks the original C source after guest compilation,
and publishes via an atomic no-clobber link only if the source is still stable.
The driver syncs the staged guest file and, on Unix, the final output directory
before reporting success, as the layout publisher does for its own output.
Failures before the link leave no published guest artifact; a **post-link
directory-sync failure** reports failure but may leave the already-created
output in place for inspection rather than removing a published name. Late
output-name collisions do not clobber their owner. The layout backend retains
its own VM and output checks.

```sh
mkdir -p .temp
python3.14 -B src/interface/command-line/composition/scripts/c2malbolge.py \
  --frontend /path/to/malbolge_c_frontend \
  --json-adapter /path/to/c2malbolge_json \
  --layout-backend /path/to/malbolge_layout \
  --guest-include /path/to/guest/include \
  --resource-dir /path/to/pinned/clang/resources \
  --source-id src/interface/command-line/composition/examples/emit-aa.c \
  --output .temp/emit-aa-explicit.malbolge --capsule \
  src/interface/command-line/composition/examples/emit-aa.c
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
mkdir -p .temp
python3.14 -B src/interface/command-line/composition/scripts/c2malbolge.py \
  --repository-tools --capsule --output .temp/emit-aa-python.malbolge \
  src/interface/command-line/composition/examples/emit-aa.c
```

After installing the Unix shims into a directory on `PATH`, the same command
can be run directly as:

```sh
mkdir -p .temp
c2malbolge --repository-tools --capsule \
  --output .temp/emit-aa.malbolge \
  src/interface/command-line/composition/examples/emit-aa.c
malbolge --repository-tools .temp/emit-aa.malbolge --report-steps
```

The checked-in example emits exactly `AA` on guest stdout, with
`malbolge-steps-v1:27` on stderr from the normative repository VM. It uses two
`putchar('A')` calls and an implicit `void` return; it does not claim general C
or libc support. The three compiler examples above are alternative invocations,
with distinct output names to preserve the no-clobber guarantee.

A second checked-in example demonstrates a **single** nonzero output, not a
host-side substitution or an `AA` repetition: the source
`composition/examples/emit-plus.c` calls `putchar('+')`. With the built
repository tools, compile it using the same `--repository-tools --capsule`
invocation and a fresh `.temp/emit-plus.malbolge` output. The installed
`malbolge --repository-tools` VM emits exactly the one byte `+`. The bridge
admits this particular byte/count pair only through an independently witnessed
layout; other bytes or counts still reject without publication.
The same supported byte is also available from `putchar(299)` through C's
low-byte conversion, including when publishing raw graphical `.malbolge`
instead of a capsule.

A checked-in two-distinct-byte example,
`composition/examples/emit-qp.c`, uses separate calls to `putchar('Q')` and
`putchar('.')`. Both bytes are realized by independently verified guest
arithmetic, rather than repeating a saved accumulator or substituting host
output. When the pinned native tools are built, the following compiles and
runs the current-profile program as **raw** graphical Malbolge:

```sh
c2malbolge --repository-tools --output .temp/emit-qp-raw.malbolge \
  src/interface/command-line/composition/examples/emit-qp.c
malbolge --repository-tools .temp/emit-qp-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps
```

The guest emits `Q.` and reports `malbolge-steps-v1:8`. If `--capsule` is
supplied to compilation instead, the runner selects the embedded profile,
without a `--raw-profile` flag. These are finite, witness-verified byte
transitions, not arbitrary C output-stream support.

The three-byte `composition/examples/emit-zph.c` example performs three
independent C `putchar` calls producing `Z%H`. It is an executable witness
for the newly admitted distinct-byte triples, not a string-printing shortcut:

```sh
c2malbolge --repository-tools --output .temp/emit-zph-raw.malbolge \
  src/interface/command-line/composition/examples/emit-zph.c
malbolge --repository-tools .temp/emit-zph-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps
```

The normative guest VM emits `Z%H` and reports `malbolge-steps-v1:8`. The
same checked-in C source, compiled with `--capsule` to a different output
path, emits identical bytes and steps without explicit `--raw-profile`.
Other independently witnessed triples are `Q.O` (9 steps), `Y-P`
(10 steps), `T"O` (12 steps), and `T"Q` (14 steps). Unsupported triples
still fail before publication.

The four-byte `composition/examples/emit-t4.c` example computes four
**distinct** output bytes with four real guest CrazyData writes, producing
`T=4>` in 21 steps. With repository-built tools, either output format runs
under the same current-profile normative VM:

```sh
c2malbolge --repository-tools \
  --output .temp/emit-t4-raw.malbolge \
  src/interface/command-line/composition/examples/emit-t4.c
malbolge --repository-tools .temp/emit-t4-raw.malbolge \
  --raw-profile malbolge-2026 --report-steps
```

Add `--capsule` and choose a different fresh output path for a self-describing
artifact that does not need the explicit `--raw-profile` runner flag. Both
modes are tested against exact guest stdout and instruction counts. This is
a finite separately witnessed byte sequence, not arbitrary string output.

Four larger **binary** teaching pairs are retained in the
[versioned example corpus][binary-corpus]:
[`emit-qesc79-v1`](../../../docs/technical/examples/corpus/emit-qesc79.md)
computes bytes `51 22 1b 37 39` (`Q`, quote, ESC, `7`, `9`) in 23 steps;
[`emit-qop6-v1`](../../../docs/technical/examples/corpus/emit-qop6.md)
computes `51 1c 4f 1d 50 1b` (`Q`, FS, `O`, GS, `P`, ESC) in 15 steps;
[`emit-seven-v1`](../../../docs/technical/examples/corpus/emit-seven.md)
computes `36 3e 35 02 54 1f 18` (`6`, `>`, `5`, STX, `T`, US, CAN)
in 21 steps; and
[`emit-eight-v1`](../../../docs/technical/examples/corpus/emit-eight.md)
computes `53 20 17 3c 36 01 52 06` (`S`, space, ETB, `<`, `6`, SOH, `R`, ACK)
in 21 steps.
The committed capsules are reproducible outputs from actual pinned source-C
compilation and execute without host-level byte substitutions. For example:

```sh
malbolge --repository-tools \
  docs/technical/examples/corpus/emit-qesc79.malbolge \
  --report-steps | od -An -tx1
malbolge --repository-tools \
  docs/technical/examples/corpus/emit-qop6.malbolge \
  --report-steps | od -An -tx1
malbolge --repository-tools \
  docs/technical/examples/corpus/emit-seven.malbolge \
  --report-steps | od -An -tx1
malbolge --repository-tools \
  docs/technical/examples/corpus/emit-eight.malbolge \
  --report-steps | od -An -tx1
```

These selected `malbolge-2026` capsules preserve nonprinting guest bytes;
printing the output as a shell string would obscure their identity. The linked
corpus records pin hashes and fresh-build commands. These finite exact traces
do not constitute general byte-stream or string-output lowering.

[binary-corpus]: ../../../docs/technical/examples/versioned-c-malbolge-corpus.md

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
source filename when it satisfies the frontend's portable ASCII grammar.
Filenames containing spaces, Unicode or other nonportable characters instead
receive a stable `source-<SHA-256>.c` identity derived from the filename bytes;
`--source-id` still overrides this in direct Python mode. Tool
path overrides cannot be mixed with this mode. Source identity checks, guest
verification, private staging, no-clobber publication and `--capsule` semantics
are identical to the explicit-tool invocation. This is a repository development
shortcut, not an automatic production compiler installation.

In explicit-tool mode all three executables are caller-trusted capabilities.
This bounded integration entrypoint is **not** the finished turnkey installer
or an arbitrary C compiler. It accepts only exact normalized Clang shapes:
effect-free void functions (including standalone `0;` and `(void)0;`) and
literal `putchar(N);` calls in their original lexical compound scopes. Up to
128 nested blocks at a maximum compound depth of 64 may surround the output
calls. Up to 128 source-proven inert `;`, `0;`, and `(void)0;` statements
may occur before, between, or after calls at any admitted depth; they
contribute no guest byte effects. For example, sibling blocks containing
`{ putchar(65); } { ; putchar(65); }` emit the two bytes `AA` in order.
Nested early returns, effectful non-output statements and source shapes
outside the bounded lexical admission reject without output publication.
A void function may use a final `return;` in its last lexical scope or an
implicit return at its closing brace. Byte arguments
may be admitted source-bound decimal/radix integers or evaluated character
literals, with one supported parenthesized, unsigned-literal, or unary `+`/`-`
wrapper. The frontend checks representable signed `i32` arguments and emits
the same low byte as C `putchar(int)`: for example, `putchar(256)` emits NUL,
`putchar(321)` and `putchar(-191)` both emit `A`, and `putchar(65559)` emits
byte `23`. A signed unary source argument retains its complete source span;
arbitrary expressions, nested unary operators, and unchecked overflow reject.
One to 33 writes of zero produce actual NUL bytes. Nonzero output additionally
requires a verified byte/count layout (for example, `23` once, `65` twice
or ten times, `146` three times, or `39` thirty-three times). The latter
emits 33 literal apostrophes through the installed compiler and guest VM.
Unwitnessed byte/count pairs, mixed byte values,
interleaved nonzero expressions or other unsupported operations, excess
calls, the general C process-return ABI and guest libc remain unsupported.
Each accepted output runs in the independent VM.
The pinned Clang frontend is required for real source compilation; its
absence cannot be replaced by synthetic JSON test evidence. The three source
digest reads constrain a specific invocation, not a persistent filesystem
snapshot; external consumers must still manage later source changes.
