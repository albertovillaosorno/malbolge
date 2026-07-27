# Native artifact cache identity

## Purpose

Own collision-safe native artifact reuse keys before durable cache storage
exists.

## Owns

- canonical portable-IR identity bytes;
- host operating-system and ISA identity;
- backend and native ABI revisions;
- sorted required code-generation features;
- non-authoritative lookup digests followed by full equality.

## Does Not Own

- native machine-code emission;
- durable cache directories or eviction policy;
- executable-memory allocation;
- verifier acceptance of an untrusted `RegionEffectProgram`.

## Contents

`main.rs` deliberately uses FNV only as an in-process bucket accelerator. Full
canonical IR bytes and every target assumption remain part of `Eq`, so a digest
collision cannot authorize native reuse. A future serialized cache may add a
cryptographic content address without changing this correctness rule.

`NativeArtifactKey` combines the complete canonical IR identity with
`NativeTargetIdentity`: operating-system family, host ISA, backend ID/revision,
native ABI revision, and a sorted/deduplicated required-feature set. This means
Windows/x86-64 and Linux/x86-64 never share a key merely because the instruction
set matches, and changing a backend/ABI/feature assumption invalidates reuse.

The current FNV-1a digest is intentionally only a lookup bucket. Tests force two
different programs to the same digest and require the full keys to remain
unequal. A later disk cache may add SHA-256/content-addressed filenames, but it
must still confirm the complete key rather than promote a digest to semantic
authority.
