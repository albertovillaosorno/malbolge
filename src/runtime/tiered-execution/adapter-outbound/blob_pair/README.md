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

A persistent sibling `.lock` file serializes cooperating publishers around
immutable-generation creation and manifest replacement. Readers do not need the
lock because generation files are immutable and are not reclaimed by this
adapter. A crash before manifest replacement can therefore leave unreferenced
generation files, but those files are never visible as current pair state.

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
- pair compare-and-swap semantics;
- protection from writers that ignore the sibling lock;
- general N-object transactions or distributed consensus.
