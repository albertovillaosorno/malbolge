# Malbolge layout and encoding

The initial executable target encoder admits only bounded straight-line
machine operations: `NoOperation`, profile `InputWord`/`OutputByte`, and final
`Halt`. It can also emit either a single `RelocateDataPointer` (`j`) prologue
followed by real `RotateData` (`*`) and `CrazyData` (`p`) operations, and
bounded chains of strictly forward `JumpForward` (`i`) code jumps. The jumps
may precede the single relocation when its dynamically read data word proves
that all later data writes remain outside source. Jumps after relocation are
not admitted. There is no conditional branch, backward jump, or executable
external guest helper.

The encoder assigns code addresses starting at zero and uniquely inverts the
normative profile decoder over all 94 graphical source bytes. Independent
admission checks every emitted code byte, selected profile ID/fingerprint,
exact positions, length, and terminal halt. No translation table is copied.

Data relocation is necessary before rotate/crazy: without it, code and
data pointers advance together and mutate the currently executing cell.
The single `j` may occur after no-op/raw byte I/O or forward jumps, but must
precede rotate/crazy and **all** following code must be jump-free. Its
operand comes from the *actual current data-pointer memory word* at that
step, not necessarily the `j` graphical code byte. For an earlier jump,
`C` and `D` have diverged; the operand can reside in a skipped no-op cell
whose value has already been XLAT2-encrypted. The source-memory shadow
models those prior encryptions before checking `j`.

The verifier requires the current `j` operand to be **at least the entire
source length**, so D becomes the operand plus one and all subsequent data
writes remain outside emitted code. If its base would overlap source, it
fails closed even when the `j` code character itself looks safe. Source-
length extension past an encrypted operand also fails before publication.
Earlier jump/no-op source positions remain fully graphical and uniquely
encoded. Missing, duplicate, premature arithmetic and potentially aliasing
relocation are rejected.
A separate exhaustive decoder-phase test enumerates all safely addressable
rotate/crazy placements at positions 1 through 93, under both declared
profiles, and independently checks the encoded instruction and execution
witness lengths. It complements the longer real-VM boundary regression.

Forward jumps (`i`) can now form a bounded strictly increasing code path.
The **first** jump, while `D == C`, reads its own graphical code cell as a
target word. Each later jump instead reads the memory cell selected by the
*evolving data pointer*, potentially in an earlier skipped no-op region.
The checker models the exact XLAT2 mutation after every nonhalt step,
including `target - 1` after a jump. This matters because the next jump may
read a cell **encrypted by an earlier jump**, rather than its original source
byte. The independently admitted claimed target must equal the current data
word plus one, be strictly forward, and stay inside emitted source.

Every gap between a jumped-from and jumped-to source address must contain only
canonical graphical no-op padding. A skipped jump, skipped I/O, backward edge,
forged target, a jump after relocation, or inconsistent modified operands
reject before publication. No reachable source instruction is
revisited; full mutable code-state or conditional branching remains open.
The original one-jump 94-phase checks remain, and tests now execute real
2- and 3-jump chains under both canonical VMs, including an encrypted operand
read by the third jump and adversarial wrong-target/gap probes. A separate
regression verifies that a later jump may also read an already *executed*
no-op that has since been XLAT2-encrypted; the original code-cell byte is not
a trustworthy jump operand after execution.

An opt-in library-level forward-padding planner,
`encode_auto_padded_forward_layout`, accepts logical
`PaddedForwardStep::{Instruction, Jump}` and inserts the exact graphical
no-op gap for each independently admissible forward jump. Its output includes
both the verified linear layout and the mapping of logical operations to
physical source positions. Each target is derived from the evolving
`D`-pointer memory word, including earlier XLAT2 encryption; no caller-supplied
jump destination is trusted. The planner rejects backward/short targets,
post-relocation jumps, oversized code and unsupported logical plans. The
original machine-op CLI still requires concrete `jump:TARGET` tokens;
the opt-in `--auto-layout` mode uses this solver explicitly.

The library planner also accepts `PaddedForwardStep::AutoRelocate`. It inserts
*reached* no-ops to find the earliest safe decoder phase within 94 positions
for a `j` data-pointer relocation, taking the remaining logical suffix,
current data pointer and previously encrypted jump operands into account.
The planner also returns an exact source-cell origin table alongside
logical-to-physical code positions: each graphical cell is either an
original logical step, inserted *reached* relocation padding, or skipped
jump padding. The table is constructed only after independently admitted
VM path evidence; this is a bounded machine-step map, not a C source map.
The resulting source and data-write witness undergo the normal independent
layout check. Current/historical VM tests cover a long suffix and a two-jump
chain followed by safe rotate/crazy writes; duplicate relocations, a jump
after relocation and impossible source-length bounds reject. The CLI does
accepts a symbolic relocation token only after `--auto-layout`.

Every admitted layout returns deterministic, step-indexed witnesses for
**four** facts: reachable code pointer, data pointer at the start of each
step, code cell encrypted after each nonhalt step, and the *planned guest
data-write address* for each rotate/crazy step (none otherwise, including
halt). The data-write address must be outside the entire emitted source.
Current/historical normative VM tests compare all four against actual
per-step control state, XLAT2 memory changes, and data-cell reads/writes
from the independent transition trace. Actual data-write **values** depend
on guest input and earlier arithmetic, so these layout witnesses do not
claim to predict values or arbitrary guest semantic equivalence.

The source has two to 4096 cells (with a stricter bound for relocated data),
contains exactly one final halt, and carries the canonical selected profile
identity. Real current and historical profile-VM tests prove byte I/O,
rotate/crazy execution, forward skip-to-target semantics, halting, and
invalid placement rejection.

This is **not** a C-to-Malbolge compiler. Arbitrary ternary-IR operations,
general control-flow jumps, data/global layout, calls, runtime linkage,
source maps, full mutable code-state planning, and final capsule production
remain open.

## Explicit-profile source file emitter

The first source-producing command is a **bounded machine-op subset tool**,
not the C frontend or the complete compiler:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-1998 \
  --output .temp/echo.malbolge -- input output halt
```

The same publisher now has an explicit symbolic layout mode. Only after
`--auto-layout` does `jump` mean a forward target chosen from the live
`D`-pointer word; `auto-relocate` asks for the earliest safe `j` phase.
`--auto-layout` also accepts the other ordinary machine tokens (`nop`,
`input`, `output`, `rotate`, `crazy`, `halt`, and explicit `relocate`), but
refuses numeric `jump:TARGET` and any ternary-file operand:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 \
  --output .temp/auto-jump.malbolge -- \
  --auto-layout jump input output halt
```

For relocated guest ternary arithmetic, place `auto-relocate` before
`rotate`/`crazy`, followed by the final `halt`. The planner expands
unreachable source cells with inert no-ops for jumps, and inserts *reached*
no-ops to find a safe relocation phase within 94 decoder positions.
The expanded plan is **independently re-admitted** and run in the normative
profile VM before the same atomic, no-clobber raw or capsule publisher.
The reported VM step count excludes unreachable padding, while the
`.malbolge` byte count includes all physical source cells. The default
machine-token mode remains unchanged and still requires `jump:TARGET`.

The real external-process regressions compare symbolic output byte-for-byte
against the original concrete-token publisher, reload both profiles' files
in their independent VMs, and verify input/output, XLAT2 jump behavior and
relocated rotate/crazy data writes. A separate process-level round trip
executes a generated historical raw source and modern profile capsule through
`malbolge <path> --input-stdin`; the general runner must return the exact
binary bytes `0x00 0xff` from two successful input/output pairs.
A separate three-hop symbolic-chain fixture verifies that a later `i` reads
an XLAT2-encrypted operand rather than its original source byte. The
resulting historical raw and modern capsule programs are byte-identical to
the concrete three-hop baseline and execute exact `0x00` or `0xff` through
the real general runner with guest stdin.
Unsupported paths, malformed options, unsafe data moves and occupied
output paths reject before publication.
Neither mode provides conditional branching, loops, guest storage, EOF
semantics, or source-C lowering.

For a self-describing modern-profile `.malbolge` that the general command
runner can load directly, request the existing version-one capsule format:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 \
  --output .temp/modern-echo.malbolge --capsule -- input output halt
```

The compiler can also consume a **canonical pre-layout ternary wire file**,
provided its already-validated effect trace is one or more adjacent
successful `ByteInput`/`ByteOutput` SSA echo pairs and a void return:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 \
  --output .temp/echo-from-ternary.malbolge --capsule -- \
  --ternary-file .temp/echo.mctr
```

The original `--ternary-file` form retains strict adjacent-pair echo
admission. A separate explicit mode accepts a *latest-successful-read* trace:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 \
  --output .temp/latest-read.malbolge --capsule -- \
  --latest-byte-trace --ternary-file .temp/latest-read.mctr
```

In this opt-in mode, every output must reference exactly the latest read's
SSA result. Reads may be unused and a read can be output more than once.
Replaying an older SSA byte after another input, writing before the first
input, scalar operations and non-void returns remain unsupported. The
successful-byte condition excludes EOF and failed I/O; no guest byte storage
or transformation is synthesized. Both modes produce identical bytes for
admitted adjacent echo programs.

### Direct canonical typed-IR file publication

A third bounded input form skips the caller-managed MCTR file. It accepts a
complete canonical `malbolge-typed-ir-v1` (`MCTI`) module and runs the existing
`typed-echo-adapter` inside the **same** artifact publisher:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 \
  --output .temp/from-typed.malbolge --capsule -- \
  --typed-file .temp/echo.mcti
```

The default `--typed-file` retains strict adjacent echo. The separately
opt-in `--latest-byte-trace --typed-file .temp/latest.mcti` admits repeated
output of the latest successful byte and ignored consumed reads under the
same narrow semantic restrictions as the ternary-wire route. **This is not
source-C compilation**: the input must already be an independently admitted,
canonically serialized typed module with one void, zero-argument function,
no globals or proof obligations, and only the supported successful `u8`
byte operations. Source digest/ID and ABI identity remain copied provenance.

A typed input is a regular, nonempty file of at most 1 MiB. The adapter
independently revalidates the MCTI module, generates MCTR bytes, and admits
the graphical source. The publisher then **separately restores those MCTR
bytes and re-encodes the complete source** using its original independent
ternary bridge, requiring byte-for-byte identical source, execution-step
count and exact selected profile ID/fingerprint before the normative VM's
empty-input and two successful-byte-pattern preflights. Raw and capsule
artifacts use the existing atomic no-clobber publisher. Tests verify that
direct MCTI output equals the previous MCTI-to-MCTR-to-file route for both
modes, malformed/cross-profile/stale SSA/oversize inputs refuse publication,
and existing output is never modified. A separate process regression
executes a directly published typed latest-read capsule through the real
`malbolge --input-stdin` runner, verifying binary `0x00`, `0xff` and `0x80`
input with repeated outputs `0x00 0x00 0x80 0x80`. Hostile mode ordering,
missing path and extra operands also reject before target publication.
No EOF/error/guest ABI is added. Canonical typed-IR v1 binds its target
identity to **`malbolge-2026`**, even though the standalone machine-layout
CLI supports historical and immutable versioned profiles. Typed-file mode
therefore rejects profile selection drift (including those four other
registered identities) before target effect projection; successful current
profile capsules execute through both the normative VM and general runner.
The direct typed file mode also passes the physical 4096-cell cap with one
successful read and 4094 outputs, while the next cell is refused without a
published artifact.

Both canonical file modes accept only bounded nonempty regular files.
On **Linux and Android**, the publisher opens the candidate with native
`O_NONBLOCK` and checks the resulting **file descriptor** before reading,
so a named pipe (even one substituted for a regular symlink just before
open) cannot block on an absent writer. The open uses only safe Rust
`OpenOptionsExt`; no new FFI or dependency is required. The 1 MiB limit,
exact read length and canonical MCTI/MCTR admission still apply to the
actual opened bytes. Ordinary symlinks to regular files remain supported.
On other platforms the earlier resolved-path metadata check precedes open,
followed by an independent descriptor check: it rejects stable FIFOs but
does **not** close the pathname-swap window.

Real subprocess tests reject FIFO and FIFO-symlink inputs in both wire
modes, preserve valid regular symlinks, and repeatedly switch a candidate
symlink atomically between a bounded invalid file and a writerless FIFO
while both publisher modes execute. No swapped invalid input may block or
publish. This is bounded race stress, not exhaustive scheduling proof or
an authenticated stable pathname; a replaced regular file still requires
independent canonical byte admission.

### Canonical initial-zero byte output

An additional explicit opt-in `--initial-zero-output` prefix now publishes
the independently checked initial-accumulator-zero subset. The canonical
MCTI or MCTR source must contain exactly one `u8` zero constant followed by
one or more outputs of that identical SSA byte and final void return, with
at most 4095 output cells. The guest's initial accumulator is already zero:
the source contains actual Malbolge `OutputByte` operations and one halt,
not a host-side print or a hidden typed byte emulation. It consumes zero
input even when the guest runner has pending bytes.

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/zeros.malbolge \
  --capsule -- --initial-zero-output --typed-file .temp/zeros.mcti
cat .temp/zeros.mctr | cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/zeros-piped.malbolge \
  -- --initial-zero-output --ternary-stdin
```

`--initial-zero-output` works with both canonical file and stdin modes;
it cannot be mixed with `--latest-byte-trace` or machine-op tokens. The
publisher checks the typed source and exact re-decoded MCTR target again,
then separately executes the normative VM with empty and nonempty guest
inputs and requires exact zero output and zero input consumption before
atomic raw/capsule publication. The strict default, latest-read flow,
bounded wire sizes, and refusal to overwrite an existing output remain.
Real MCTI and MCTR stream tests keep their output paths absent both while
the canonical prefix is incomplete and after all bytes arrive but before
EOF; only closing the pipe permits final atomic publication.
This subset supplies no nonzero constant realization, guest EOF/status,
libc calls, heap operations, or complete C compilation.

### Bounded canonical wire streaming on standard input

Canonical MCTI and MCTR can also be supplied directly from a producer process
without a caller-managed intermediate file:

```sh
cat .temp/echo.mcti | cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/streamed.malbolge \
  --capsule -- --typed-stdin
cat .temp/latest-read.mctr | cargo run --bin malbolge_layout -- \
  --profile malbolge-2026 --output .temp/trace.malbolge \
  --capsule -- --latest-byte-trace --ternary-stdin
```

`--typed-stdin` and `--ternary-stdin` are **explicit**, mutually exclusive
source modes, each requiring zero path operands. Both accept a nonempty
canonical binary wire of at most **1,048,576 bytes**, read through the input
stream until EOF or the first overflow byte. Empty/truncated/noncanonical,
wrong-profile, unsupported SSA/effect flow and oversized streams refuse
publication. The default modes remain strict adjacent echoes; opt into the
latest-read subset only with `--latest-byte-trace` directly before the stdin
mode. These are compiler-input pipes, **not** executable guest byte stdin
(`malbolge --input-stdin` is a separate runtime action). Neither new mode
makes raw C source or a C ABI executable.

The publisher reuses the exact independently re-decoded MCTR source, normative
VM termination and two successful-byte trace checks, optional profile capsule
and atomic no-clobber output stage already used for regular-file inputs.
Tests compare real subprocess stdin and file outputs byte-for-byte across
MCTI/MCTR strict and latest-read examples; error cases do not create or
overwrite the final file. A writer must eventually close its pipe: an
unclosed stdin stream can legitimately wait for its upstream producer, unlike
the forbidden implicit opening of FIFO paths in the regular-file modes.
A separate process regression writes the first 16 MCTI bytes, checks that
no target exists while the producer keeps stdin open, then streams the
remaining bytes individually and closes the pipe. Only after EOF may the
publisher emit the exact target source; the source is independently
compared with canonical typed compilation.

`--ternary-file` is mutually exclusive with individual decoded machine-op
tokens. Its sole operand must be an existing, nonempty regular file with at
most 1,048,576 bytes. The complete MCTR version-one stream is independently
restored through `canonical_ternary_program` and passed to the separate
`byte-echo-bridge` admissibility checker; invalid/truncated/noncanonical
wire, wrong profile, or unsupported effect/control/data flow fails before
publication. The returned source is loaded and executed by the normative
profile VM at its declared execution-witness step count and then published
through exactly the same raw/capsule and no-clobber file path as machine-op
mode. Real external-process tests validate a successful three-byte trace
(including `0x00`/`0xff`) and reject canonical but semantically unsupported
SSA output, profile drift, corrupted wire and oversized files. Before any
publication, the emitter additionally runs two deterministic *successful*
input-byte patterns through the real normative VM and checks output
according to the admitted ordered read/write effect trace, consumed-input
count, and terminal instruction step. This is a bounded
execution regression, not a proof of all possible input traces or I/O errors.
Missing/empty input files, extra operands, and existing target paths also
fail without changing the output directory.

The source contains exactly the successful-input-byte interpretation of the
admitted ternary operations; it does **not** encode the source-C runtime ABI,
EOF or failed-I/O behavior, and the empty-input preflight checks VM
reachability/termination only; the additional successful-byte preflight checks
two concrete effect traces. `MCTR` metadata including its source hash is
copied provenance, not independent cryptographic source authentication.
A full C-to-Malbolge frontend and general guest-runtime realization remain
out of scope.

Independent process tests also publish real raw/capsule jump-then-`j`
rotate/crazy programs for both canonical profiles, reopen the files and
confirm VM data-pointer changes and an actual guest data-word mutation.
A second fixture reads an earlier jump's XLAT2-encrypted data operand and
rejects a lengthened source crossing its exact relocated-data bound.

A separate external-process regression now passes a three-jump instruction
list through the actual `malbolge_layout` emitter in both canonical profiles.
It verifies raw and version-one capsule bytes independently, reloads and
executes the resulting real VM source with successful input, and rejects a
forged later jump destination without publishing an output file.

The optional `--capsule` flag follows `--output PATH` and precedes the `--`
separator. The producer verifies the raw graphical machine code first, then
wraps it in the canonical historical-safe fallback/space-tab sideband using
the existing VM `build_capsule` API. Before publication it independently
parses the capsule and checks canonical profile ID, fingerprint and exact raw
payload bytes. The normal `malbolge` command runner then selects the embedded
profile and executes the payload; the historical classic interpreter instead
sees the fixed safe fallback (output `!`). External process tests verify both
paths. The raw format remains available by omitting `--capsule`.

It accepts an exact canonical `--profile` ID, a *new* `.malbolge` output path
whose parent directory already exists, and `--` followed by 2–4096 closed
opcode tokens: `nop`, `input`, `output`, `rotate`, `crazy`, `relocate`, `halt`,
and `jump:<unsigned-decimal-code-address>`. The latter is a **claimed**
post-increment jump target that must equal the graphical source-cell byte
plus one at that exact address. Only the previously verified one-shot jump
and data relocation shapes are allowed. Unsupported opcodes, unsupported
control/data flow, noncanonical profiles, malformed arguments and unsafe
source layouts fail before output publication.

The producer independently re-admits its emitted graphical bytes and loads
and executes them with the normative `ProfileMachine` for the selected
profile using empty input. It requires a halt at the exact admitted step
count before any source is published. This execution check validates the
bounded machine subset's shape and control flow, **not** arbitrary input
semantics or equivalent C computation. It stages the complete byte stream
in the output directory, reopens and byte-compares the stage, then uses an
atomic hard link to publish without replacing an existing target or symlink.
An interrupted producer can leave an ignored, hidden `.stage-<pid>` file,
but it cannot expose a partially written final target. A successful command
prints a short informational diagnostic to stderr and writes no stdout.

Raw `.malbolge` bytes still do **not** embed a modern target-profile
identity: consumers must supply the same explicit profile, or select the
`--capsule` option. The general-purpose runner treats *raw* files as classic,
whereas recognized capsules carry a pinned canonical profile/fingerprint and
use the profile-aware interpreter. The initial publisher is a machine-subset
emitter only; even with a capsule it does **not** claim C/ternary lowering,
source maps, guest-runtime linkage or support for general control flow.
