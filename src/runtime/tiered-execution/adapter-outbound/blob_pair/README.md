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
names indirectly through its process/generation token.

A persistent sibling `.lock` file coordinates cooperating readers and
publishers. Readers hold a shared lock from manifest observation through both
immutable member reads. Generation creation, manifest replacement, and
revision-conditional comparison hold the exclusive lock. Conflict returns the
complete current bounded pair plus its revision; byte-equal newer generations
still conflict with stale revisions, preventing ABA.

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
- reclamation scheduling, retention policy, or background garbage collection;
- protection from writers that ignore the sibling lock;
- general N-object transactions or distributed consensus.
