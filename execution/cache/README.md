# Native artifact cache

## Purpose

Own collision-safe native artifact reuse keys and caller-owned process-local
storage before durable cache persistence exists.

## Owns

- canonical portable-IR identity bytes;
- rejection of region addressing beyond the declared profile capacity;
- host operating-system and ISA identity;
- backend and native ABI revisions;
- sorted required code-generation features;
- non-authoritative lookup digests followed by full equality;
- process-local exact-key lookup, insertion, replacement, removal, and clearing.

## Does Not Own

- native machine-code emission;
- durable cache directories, serialization, or eviction policy;
- synchronization or shared ownership between callers;
- executable-memory allocation;
- verifier acceptance of an untrusted `RegionEffectProgram`.

## Contents

`main.rs` deliberately uses FNV only as an in-process bucket accelerator. Full
canonical IR bytes and every target assumption remain part of `Eq`, so a digest
collision cannot authorize native reuse. A future serialized cache may add a
cryptographic content address without changing this correctness rule.

`RegionEffectIdentity` is stricter than raw IR transport. It first requires
`RegionEffectProgram::fits_declared_profile_capacity()` and returns typed
`NativeIdentityError::ProfileCapacity` before hashing or retaining canonical
bytes. This is a structural identity invariant, not verifier acceptance of the
region's claimed effects.

`NativeArtifactKey` combines the complete canonical IR identity with
`NativeTargetIdentity`: operating-system family, host ISA, backend ID/revision,
native ABI revision, and a sorted/deduplicated required-feature set. This means
Windows/x86-64 and Linux/x86-64 never share a key merely because the instruction
set matches, and changing a backend/ABI/feature assumption invalidates reuse.

`NativeArtifactCache<Value>` is a caller-owned process-local store over those
keys. It groups entries by the non-authoritative digest, then confirms complete
key equality for every read, replacement, and removal. Distinct keys in one
forced-collision bucket remain independently readable and removable. Stored
values gain no semantic authority merely by being cached; callers must insert
only artifacts admitted by their owning boundary.

The cache has no implicit limit, eviction, synchronization, persistence, retry,
or discovery. `clear()` is explicit, and dropping the caller-owned value releases
all retained entries. A later disk cache may add SHA-256/content-addressed
filenames, but it must still confirm the complete key rather than promote a
digest to semantic authority.
