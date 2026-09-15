# Tiered-execution filesystem atomic blob-pair adapter

## Purpose

Bind the storage-neutral atomic blob-pair port to one explicit host filesystem
manifest path without granting the adapter telemetry, policy, or codec
authority.

## Publication model

The manifest is the only mutable publication pointer. Each successful
replacement creates two immutable same-directory generation files, writes and
synchronizes both completely, then writes and synchronizes a staging manifest.
Atomic `rename` of that staging manifest is the single commit point. Readers
first read one complete manifest and then load only the two immutable members it
names indirectly through its epoch/generation token.

A persistent sibling `.lock` file coordinates cooperating readers and
publishers. Readers hold a shared lock from manifest observation through both
immutable member reads. Generation creation, manifest replacement, and
revision-conditional comparison hold the exclusive lock. Conflict returns the
complete current bounded pair plus its revision; byte-equal newer generations
still conflict with stale revisions.

Shared reader locking makes explicit generation reclamation safe: the exclusive
reclaimer cannot proceed while a cooperating reader still depends on an older
manifest generation. A crash before manifest replacement can still leave
unreferenced generation files, but those files are never visible as current pair
state and can be removed by a later explicit reclamation pass.

## Reclamation boundary

Generation deletion is explicit and is not part of replacement.
`reclaim_generations()` acquires the exclusive sibling lock, validates the
current manifest before deleting anything, preserves both members named by that
manifest, and considers only exact generation-member names owned by this
manifest basename. Missing manifest state treats every exact owned generation
member as unreferenced. Non-UTF-8 manifest basenames fail before deletion
because the adapter cannot prove exact cross-platform ownership safely.

`reclaim_generations_preserving()` additionally accepts opaque revisions that
the caller already owns and preserves every exact matching generation. The
adapter compares revisions for equality only; it never orders revisions,
chooses a retention window, or infers which historical generations matter.

The optional storage-neutral reclaimable-pair port exposes this operation
without filesystem types. Its reclamation application use case forwards one
caller-selected exact preserve slice unchanged and runs one reclamation pass.
A separate process-local retention owner records only revisions callers
explicitly retain or release; equality controls membership and insertion order
has no temporal meaning. Automatic selection and scheduling remain outside the
adapter.

The fixed 24-byte manifest now interprets its first `u64` as a store epoch and
its second `u64` as the committed generation. Initial publication seeds the
epoch once; every later cooperating writer keeps that epoch and derives the next
generation from the current manifest under the exclusive lock. Crash-orphan
collisions are skipped monotonically within the same epoch, and `u64` exhaustion
fails closed. Reclamation never resets the manifest generation, so published
revision identity is not reused across ordinary process restarts or cleanup.


Opaque filesystem revisions also have a separate canonical 24-byte
`MBPREV01` representation for durable callers: eight magic bytes followed by
the little-endian epoch and generation. Decode rejects wrong length, magic, and
zero generation; the representation exposes no ordering or retention policy.

Staging manifests, the lock, the current manifest, and foreign or prefix-near
files are never reclamation candidates. Reclamation attempts every eligible file
and retains exact completed removals plus failed paths and host error kinds.
Directory synchronization after removals is committed durability evidence, so a
sync failure never claims rollback. Repeating reclamation rescans under the
exclusive lock and is idempotent.

## Failure semantics

A missing manifest means no pair has been published. A malformed manifest,
missing referenced generation member, oversized member, or filesystem failure
fails closed rather than inventing partial pair state. Failure before manifest
replacement leaves the previous manifest authoritative. On hosts where standard
`rename` cannot atomically replace an existing manifest, overwrite may fail
safely rather than deleting the previous manifest first.

Pair durability confirmation is separate from publication. After the manifest
has committed, the adapter synchronizes its directory; a failure at that point
is post-publication durability evidence and must not be interpreted as rollback.

## Does not own

- telemetry framing, validation, assessment, or policy selection;
- pair byte-limit selection;
- directory creation or manifest discovery;
- reclamation scheduling, retention selection, or background garbage collection;
- protection from writers that ignore the sibling lock;
- general N-object transactions or distributed consensus.
