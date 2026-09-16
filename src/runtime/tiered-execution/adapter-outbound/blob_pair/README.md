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


Filesystem locking is now provided by one reusable coordination adapter. The
legacy constructors still derive their existing sibling lock paths, while
`with_coordination(...)` lets both the single-blob and pair adapters join one
explicit caller-selected lock domain. Coordination guards are non-cloneable and
carry exact lock-path identity. This layer changes no storage semantics.

Crate-internal prelocked operations now require one matching exclusive guard for
bounded blob load/CAS and pair-generation reclamation. They reject a guard from
a different coordinator before state access or deletion. One host-real case
holds one guard once across blob CAS/load and pair reclamation, proving that the
shared lock boundary no longer requires recursive acquisition.


Composition now uses that seam for journal-driven reclamation. One exclusive
guard spans bounded journal load/validation and exact generation reclamation;
missing journal state is a non-mutating outcome, while an explicitly present
empty journal authorizes removal of every superseded generation except current.
Two host-real cases cover the missing-journal no-op and exact preserved revision
behavior from a present durable journal.


A separate guarded transition now updates retention before cleanup. It compares
canonical journal bytes, confirms journal directory durability after commit, and
only then reclaims generations using the replacement retention. Conflict never
deletes; journal durability failure stops before reclamation, while a durable
journal plus pre-deletion reclamation rejection remains committed journal
evidence. Three host-real cases cover durable transition cleanup, stale
conflict with
zero generation deletion, and durable journal retention after reclamation
rejection.

Caller-directed bounded retry now wraps that guarded transition. Each conflict
feeds its exact typed current journal into caller reconciliation before another
attempt; exhausted conflict remains terminal evidence. Callback failure and
every committed journal or cleanup outcome stop immediately, so the runtime
still chooses no merge, backoff, ordering, or retention policy.


A policy-neutral retry-control hook now runs only between a retryable conflict
and the next attempt. It receives the exact number of completed attempts and
returns `Continue` or `Stop`; `Stop` preserves that conflict as terminal
evidence. The hook runs after the filesystem guard is released, so a caller may
perform synchronous waiting, yielding, or cancellation checks without the
runtime reading a clock, sleeping, or selecting fairness/backoff policy.

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


Exact retention sets also have a canonical `MBPRET01` frame: eight magic bytes,
one little-endian `u64` revision count, then that many canonical 24-byte
revisions in caller order. Encode and decode reject duplicates, malformed nested
revisions, and count/length drift. Frame order is preserved evidence only and
still carries no chronology, expiry, or automatic retention policy.


Composition now binds this frame to the existing bounded blob persistence
service as an explicit durable retention journal. Missing storage remains
`Missing`; present bytes rebuild the exact process-local retention owner, and a
post-publication durability failure remains committed evidence. Journal storage
still does not select revisions or schedule reclamation.


The same composition boundary also exposes one-shot conditional durable journal
publication. Expected retention is compared as canonical bytes; conflict returns
the exact current journal decoded back into typed retention, while corrupt
conflict bytes fail closed. Only successful publication performs durability
confirmation.

A host-real cross-instance case advances one journal through one file store,
then proves a stale second store returns the advanced typed retention as
conflict while leaving it authoritative. This layer does not retry, merge,
reorder, or select revisions. Refreshing expected state and blindly replaying
the same whole-set replacement would overwrite another writer's explicit
retention choices, so retry requires caller-owned reconciliation.


A separate composition retry layer now accepts that caller-owned reconciliation
callback plus a positive attempt budget. It restores typed current retention
once, invokes the callback before every CAS attempt, and feeds any typed
conflict state into the next callback invocation. Exhausted conflict budget
returns the
final conflict unchanged; callback failure, successful durability, and committed
post-publication durability failure stop immediately. The runtime still chooses
no union, intersection, ordering, backoff, or retention policy.


The durable retention journal is not by itself a safe concurrent reclamation
fence. The generic file-blob journal and the pair-generation reclaimer use
different sibling lock files, so loading a preserve set and later deleting under
the pair lock can race a journal writer that retains another revision in
between. Composition must not expose a load-journal-then-reclaim helper until
journal mutation and generation deletion share one serialization or transaction
boundary. Process-local callers may still restore the journal and coordinate
reclamation themselves when they own all relevant mutation authority.


The reviewed next filesystem design is one explicit coordination object that
owns a caller-selected lock path and yields non-cloneable shared/exclusive guard
tokens. Pair reclamation and retention-journal mutation can then bind to the
same coordinator, while internal prelocked operations require the matching
guard instead of reacquiring the lock. This mirrors the compiler progress
sidecar transaction shape: acquire once, read/validate all participating state,
mutate, then release after the commit boundary. Merely pointing today's two
adapters at the same lock filename is insufficient because their public methods
would recursively acquire that lock and can deadlock.

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
