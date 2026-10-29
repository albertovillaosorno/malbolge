# Malbolge layout and encoding

The initial executable target encoder admits only bounded straight-line
machine operations: `NoOperation`, profile `InputWord`/`OutputByte`, and final
`Halt`. It can also emit either a single `RelocateDataPointer` (`j`) prologue
followed by real `RotateData` (`*`) and `CrazyData` (`p`) operations, **or**
a bounded chain of strictly forward `JumpForward` (`i`) code jumps. There is
no conditional branch, backward jump, or executable external guest helper.

The encoder assigns code addresses starting at zero and uniquely inverts the
normative profile decoder over all 94 graphical source bytes. Independent
admission checks every emitted code byte, selected profile ID/fingerprint,
exact positions, length, and terminal halt. No translation table is copied.

Data relocation is necessary before rotate/crazy: without it, code and
data pointers advance together and mutate the currently executing cell.
A single `j` may occur at any code position after no-op/raw byte I/O, but
before all rotate/crazy steps and without a code-pointer jump. The VM still
has `D == C` at that point, so the original graphical source byte at the
chosen phase becomes the new data address. Requiring the complete emitted
source length to be at most that exact byte ensures subsequent data writes
stay outside the code region. Later phases can encode a much larger data
base than the first source cell, admitting longer safe executable layouts.
Missing, duplicate, or potentially aliasing relocation is rejected.
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
forged target, mixed data relocation/arithmetic, or inconsistent modified
operand rejects before publication. No reachable source instruction is
revisited; full mutable code-state or conditional branching remains open.
The original one-jump 94-phase checks remain, and tests now execute real
2- and 3-jump chains under both canonical VMs, including an encrypted operand
read by the third jump and adversarial wrong-target/gap probes.

Every admitted layout returns deterministic, step-indexed witnesses for **all
three** relevant facts: reachable code pointer, data pointer at the start of
each step, and code cell encrypted after each nonhalt step. The VM tests check
all three against actual per-step behavior and XLAT2 memory updates under both
profiles. Data-memory *content* writes by rotate/crazy are not part of this
witness; those remain constrained by the proved code/data separation, and no
arbitrary guest semantic equivalence is claimed.

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

The first source-producing command is an **explicit machine-op subset tool**,
not the C frontend or the complete compiler:

```sh
cargo run --bin malbolge_layout -- \
  --profile malbolge-1998 \
  --output .temp/echo.malbolge -- input output halt
```

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
input-byte patterns through the real normative VM and checks exact output,
consumed-input count, and terminal instruction step. This is a bounded
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
