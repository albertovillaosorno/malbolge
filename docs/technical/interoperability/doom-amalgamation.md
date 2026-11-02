# User-supplied DOOM source interoperability generator

## Status

Source-level implementation accepted. Malbolge lowering and execution remain
outside this completed stage.

## Purpose

Transform the accepted normalized multi-translation-unit DOOM source into one
canonical `doom.c` without making the ignored single-file oracle a distributable
dependency.

## Scope

This contract governs the deterministic source-bound transformation from the
accepted normalized DOOM tree to the canonical single-file C artifact. It does
not own later C-to-Malbolge compilation, host-capability execution, or native
runner policy.

## Current Behavior

<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
`src/research/algorithms/domain/algorithms/doom/generator/amalgamation_oracle.py`
constructs a deterministic
single-TU oracle from accepted generated quality output. It embeds project
headers, preserves system includes and provenance, orders translation units, and
isolates private collisions. `generator/amalgamate.py` feeds that source/oracle
pair to generic `algorithms/diff/`, which emits the source-bound
`src/research/algorithms/composition/algorithms/doom/amalgamate/main.rs`
transform.

The transform consumes
`quality/out/doom_fixed/linuxdoom-1.10/` and publishes exactly one ignored file,
`amalgamate/out/doom.c`, without requiring the oracle.

### Accepted Identity

- transform SHA-256:
  `7bcd19b073c5839c4c9119a0b871e4e4cd6e63dbedeb7571b6099f234e92f439`;
- canonical C SHA-256:
  `a7fbecc1a6faba9fb974399d2b1def32c52734f1a557c0d8dbcdbc9357daab80`;
- output size: 2,507,561 bytes / 79,336 lines;
- deterministic repeated generation/materialization: pass;
- wrong, absent, or mutated source rejection before publication: pass;
- byte identity with local oracle and end-to-end fixture: pass.

## Invariants

- The user-owned root source is never modified.
- Only accepted generated quality output is admitted.
- WAD/data bytes do not enter amalgamation identity or payload.
- The ignored oracle is authoring evidence only.
- The generated transform remains source-bound.
- Partial or mismatched output is never published as accepted.
- Quality and amalgamation remain separate algorithms.

## Failure Behavior

This stage ends at canonical C. Guest-C acceptance is evidence that `doom.c` is
prepared for the declared C surface, not proof that the entire program has been
lowered or executed as Malbolge. Complete compatibility requires generating and
running `doom.malbolge` with the versioned capability ABI.

## Verification

The generic diff encodes reconstruction but is not the C semantic authority.
Pinned Clang and deterministic native evidence establish that the output
preserves translation-unit preprocessing, internal linkage isolation,
declaration ordering, include behavior, and provenance.

The accepted `doom.c` passes strict six-target Clang validation and builds with
ASan+UBSan plus the Windows adapter. The optional Windows sanitizer build
preflights its `.debug` directory and `doom-sanitize.exe` output to reject
redirected parents/leaves and nonregular existing executable targets before
invoking native Zig. Clang syntax and Zig sanitizer builds require exact
native process receipts that identify the unchanged launched argv, integer
status, and uncaptured output mode; forged success cannot certify validation.
Host execution errors retain their original exception as the cause of a typed
DOOM debug failure without evaluating foreign exception formatters. This
admission is not atomic with Zig's later output open.

The direct sanitizer-debug runner creates a unique physical log in the
executable's `logs/` directory for each run, refusing linked log directories
or parents instead of writing outside the selected debug tree. Before guest
execution, it binds the new log's random-name receipt to the requested directory
and verifies the empty regular descriptor has the same unique inode as the
named log. It rejects foreign, preexisting, and multiply linked log receipts.
After execution, it checks that the named output still matches its open
descriptor before echoing at most one MiB to the console. The complete
sanitizer diagnostic stream remains in the retained log file. The direct
sanitizer guest process must also return a native completion for the exact
immutable executable/argument tuple, integer status and uncaptured output;
malformed receipts and host launch faults raise typed DOOM debug errors.
Neither the log path nor its output bytes may be substituted after process
execution; these local admission checks do not make arbitrary concurrent parent
replacement atomic. Console summaries and bounded log echoes must receive an exact native
write count and successful flush before the debug runner proceeds; incomplete
or foreign output delivery raises a typed DOOM debug error. Optional LLDB
execution likewise requires native exact-argv and integer-status process
receipts before forwarding the debugger's exit code.

A no-CRT deterministic harness produced identical multi-TU and single-TU
framebuffer/audio transcripts:

```text
92ff55046afd3976
4571f707b08d56cd
912da30aff88aaed
```

## References

- [DOOM quality and modernization pass](doom-modernization.md)
- [Source-Bound Diff Generator](../tooling/source-bound-diff-generator.md)
- [Compiler Pipeline And Guest Runtime][compiler-runtime]

[compiler-runtime]:
  ../adr/compiler-pipeline-and-guest-runtime.md
