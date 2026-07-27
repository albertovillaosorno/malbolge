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
