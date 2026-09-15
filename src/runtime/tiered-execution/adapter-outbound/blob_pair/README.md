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

Shared reader locking is a prerequisite for safe generation reclamation: a
future exclusive reclaimer can know that no cooperating reader still depends on
an older manifest generation. This adapter does not delete generations yet. A
crash before manifest replacement can therefore leave unreferenced generation
files, but those files are never visible as current pair state.

## Reclamation boundary

Generation deletion remains explicit and is not part of replacement. A future
reclamation pass must acquire the exclusive sibling lock, validate the current
manifest before deleting anything, preserve both members named by that manifest,
and consider only exact generation-member names owned by this manifest basename.
Missing manifest state may treat every exact owned generation member as
unreferenced. Staging manifests, the lock, the current manifest, and foreign or
prefix-near files are never reclamation candidates.

Reclamation must attempt every eligible file and retain exact cleanup evidence.
If some removals succeed before another fails, the result must report completed
removals beside the failed paths and host error kinds rather than claiming
rollback. Directory synchronization after removals is a separate committed
durability boundary: sync failure must preserve evidence that deletion already
changed process-visible filesystem state. Repeating reclamation must be
idempotent by rescanning under the exclusive lock.

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
- generation reclamation or garbage collection;
- protection from writers that ignore the sibling lock;
- general N-object transactions or distributed consensus.
