# Native artifact bootstrap

## Purpose

Own the first host-code lowering boundary from portable verified-effect IR to
explicitly untrusted native compilation artifacts.

## Owns

- structural validation required before native lowering;
- deterministic C23 bootstrap lowering from `RegionEffectProgram`;
- exact binding to `NativeArtifactKey` target assumptions;
- untrusted native source/object artifact containers;
- fail-closed structural admission of self-contained Windows COFF objects;
- canonical direct x86-64/AArch64 deopt-only objects with byte-exact semantic
  verification;
- target triples for the pinned Clang bootstrap backend.

## Does Not Own

- verification/admission of native machine code;
- executable-memory allocation or invocation;
- x86-64/AArch64 direct instruction selection;
- deoptimization authorization or verifier lineage guards;
- durable native-cache storage.

## Contents

`main.rs` implements the bootstrap backend. It does not make C part of the VM
semantics: Clang is only an initial code-generation adapter used to cross the
first real host-object boundary while direct architecture backends remain open.

The generated function has a two-phase shape. It first validates its local ABI
state, exact entry observation, expected input bytes/EOF, memory live-ins, first
values of every written cell, and output capacity. Only after every local guard
passes does it append output, write each touched memory address once at its final
value, and commit final registers/cursors/termination.

Those local checks are defense in depth, not verifier authority.
`RegionEffectProgram` deliberately lacks the complete Rust lineage identity used
by `VerifiedExactRegion::accepts_dependency_entry`; the host must cross that
verifier-owned guard before any future native runner can invoke this artifact.

Both source and compiler-output wrappers are named `Untrusted*`. Attaching bytes
to the correct cache key does not prove that those bytes implement the IR.

`coff.rs` adds a narrower structural gate for Windows bootstrap objects. It
parses the object bytes directly in safe Rust, checks x86-64/AArch64 machine
identity against the native target key, requires one executable/non-writable
`.text`, requires the exact `malbolge_native_region_apply` entry, rejects other
external functions and undefined external dependencies, and permits relocations
only when they resolve to symbols defined inside the same object. The resulting
`StructurallyAdmittedNativeObjectArtifact` is still not semantic authority. An
independent semantic validator must establish that boundary before executable
promotion exists.

The first direct backend is intentionally a deoptimization floor rather than a
fast path. `direct.rs` emits one deterministic Windows COFF object per ISA whose
only callable function returns native status `1` (`guard miss`) without reading
or writing the supplied state pointer. The exact x86-64 and AArch64 objects are
frozen by independently rendered hex fixtures. Semantic promotion requires
structural COFF admission plus byte-for-byte equality with the canonical object;
a one-byte opcode mutation remains structurally valid but fails semantic
admission. This establishes an executable native tier that is correct by always
falling back, before any direct region-effect instruction selection is trusted.

The second direct template is the first state-applying fast path. The
`direct-initial-halt` backend accepts exactly one portable-IR shape: one effect
from zero registers/counters with no I/O, no memory live-ins/writes, and no prior
termination to the same observation with `HaltInstruction`, one-step terminated
outcome, and budget one. Its machine code preflights those ABI fields before the
first write, sets only the termination byte to halt, and returns `applied=0`; any
mismatch or null state returns `guard-miss=1` without mutation. Complete x86-64
and AArch64 COFF bytes are independently frozen. A changed commit immediate may
remain structurally valid but fails semantic admission. Development evidence
links both ISA objects and executes x86-64 hit/miss/null cases, with miss state
byte-identical before and after. General region-effect code generation remains
outside this reviewed subset.

`select_verified_direct_native()` now owns deterministic direct-template
selection for the implemented Windows surface. It classifies IR before creating
a backend identity: exact zero-register halt selects `direct-initial-halt`, any
other zero-counter/no-I/O/no-memory one-step halt selects
`direct-halt-registers`, and every other IR selects the byte-verified deopt stub. Backend/emission/verification errors are
never reinterpreted as fallback, and unsupported host formats fail explicitly.
This removes backend-ID choice from callers while keeping unsupported IR safe.

`direct-halt-registers` generalizes the halt template across the complete 32-bit
`A`, `C`, and `D` domains while keeping input/output counters zero and admitting
no memory/I/O effects. x86-64 encodes exact `cmp imm32` guards; AArch64 materializes
each value with reviewed `movz`/`movk` pairs before comparison. Independent
whole-object fixtures bind a nontrivial `0x12345678 / 0x9abcdef0 / 0x13579bdf`
case for both ISAs. Development execution on x86-64 preserves all three matching
registers and commits only halt; changing one register returns guard miss with
the complete ABI state unchanged. The ARM64 object links successfully.
