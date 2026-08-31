# DOOM Algorithm Recipes

This directory contains thin DOOM-specific recipes that configure generic
generators. A recipe declares **what** source/oracle pair and policy to use; it
does not implement the diff algorithm itself.

`quality.py` is the first consumer. It configures `algorithms/diff` to learn the
quality transformation from the local root `doom/` source and the ignored manual
oracle under `algorithms/doom/quality/in/doom/`. Its output is
`src/research/algorithms/composition/algorithms/doom/quality/main.rs`.

`doom.py` now owns the Linux DOOM C/H identity adapter. It selects only the
`linuxdoom-1.10` C/header subtree, excludes WAD/IPX surfaces from source
identity,
and emits a framed C preprocessing-token view that ignores comments and ordinary
formatting without erasing token boundaries or preprocessor line termination.
The C identity adapter now has a mapped form as well. `mapped_c_identity()`
emits
the same framed preprocessing-token identity as `canonicalize_c_identity()`
while
retaining the raw byte span that produced each token or directive-end marker.
This is
the domain hook used by generic semantic compatible placement to preserve
candidate

comments and formatting outside transformed semantic regions. A read-only source
+
oracle smoke mapped 273 C/header files with zero identity mismatches.

The DOOM domain also owns source provenance, authoring preflight, and compatible
file
mapping. `DOOM_SOURCE_PIN` names `https://github.com/id-Software/DOOM.git`
commit
`a77dfb96cb91780ca334d0d4cfd86957558007e0`. A fresh checkout with
`core.autocrlf=false` matched the ignored local baseline byte-for-byte across
all 165
official files; the deterministic pinned snapshot digest is
`20f6b67369b98c3f62b7c8ff34493ef9647c88bce7b85c82b9ecd72bad336d8b`. `data/` is
explicitly excluded from that code pin.

`map_compatible_file()` remains available for generic semantic-placement
research,
but DOOM quality no longer needs fuzzy source admission.
`validate_authoring_oracle()`
requires the normalized oracle root to contain exactly `data/`,
`linuxdoom-1.10/`,
and `LICENSE`. Unexpected authoring artifacts fail closed rather than
becoming
target-only payload. The previously detected accidental PowerShell root entry
was
removed from the ignored authoring corpus before the accepted transform was
regenerated.

The domain facade now also exposes the first executable behavior program.
`behavior_probes.py` defines a Windows x86-64 / pinned LLVM 22.1.8 fixed-point
identity probe. It compiles the candidate mirror's real `m_fixed.c` with a
repository-owned freestanding harness, links a no-CRT PE, executes it, and
records
the exit code as behavior evidence. The harness and header shims contain no
copied

DOOM source. Additional compatibility/bug probes stay in the DOOM domain.
Generic
matching, probe execution, source binding, reconstruction, and Rust emission
remain
under `algorithms/diff/`.

`amalgamation_oracle.py` deterministically constructs the ignored accepted
single-TU authoring oracle from generated quality output. It preserves source
provenance, embeds project headers once, keeps system headers external, orders
macro-destructive translation units last, and isolates known private-name
collisions.

`amalgamate.py` is the completed second consumer. It binds accepted
`quality/out/doom_fixed/linuxdoom-1.10/` source to the ignored one-file oracle
and generates
`src/research/algorithms/composition/algorithms/doom/amalgamate/main.rs` through
the same generic exact
emitter used by quality.

The intended invocations are from the repository root:

```text
python -m algorithms.doom.generator.quality
python -m algorithms.doom.generator.amalgamation_oracle
python -m algorithms.doom.generator.amalgamate
```

`algorithms/diff` now implements exact authoring, source-span reuse, exact
source
revision pins, authenticated dynamic passthrough roots, threshold key unlock,
RFC 8439
payload protection, protected materialization, and deterministic std-only Rust
emission. `quality.py` uses that complete exact path with `data/` as
passthrough. The
generic fuzzy/semantic compatible path remains available as research
infrastructure
but is no longer a blocker for DOOM quality generation.
