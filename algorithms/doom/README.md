# DOOM Algorithm Suite

`algorithms/doom/` owns the repository's DOOM application algorithms. DOOM is a
demanding interoperability corpus, not a new repository architecture layer and
not a general-purpose source port.

The user-supplied source remains external and ignored. Durable repository content
contains only algorithms, recipes, contracts, tests, and aggregate evidence
needed to reproduce admitted transformations.

## Layout

```text
algorithms/doom/
|-- generator/
|   |-- quality.py
|   `-- doom.py
|-- quality/
|   |-- main.rs
|   |-- in/
|   `-- out/
|-- amalgamate/
|   |-- main.rs
|   |-- in/
|   `-- out/
`-- adapters/
```

`generator/` contains thin DOOM recipes and domain policy. Its C identity adapter
selects Linux DOOM C/header source only; opaque assets such as the WAD do not enter
structural lineage scoring. Generic source-tree matching, source binding, and
transformation emission belong in `algorithms/diff/`.

`quality/` is the first product stage. Its ignored `in/doom/` tree is the manual
modernization oracle used while generating `quality/main.rs`; its ignored
`out/doom_fixed/` tree is the normalized result materialized from the lawful
root `doom/` source.

`amalgamate/` is a later optional stage. It consumes only accepted quality output
and eventually uses the same generic diff infrastructure to generate the
source-bound transformation that materializes one canonical `doom.c`.

`adapters/` reserves application-side capability integration that must remain
outside the guest. Native runner implementations still belong to the runtime or
platform responsibility that owns them.

## Pipeline

```text
local root doom/
      |
      v
generator/quality.py + algorithms/diff
      |
      v
quality/main.rs
      |
      v
quality/out/doom_fixed/
      |
      v
future amalgamation recipe + algorithms/diff
      |
      v
amalgamate/main.rs
      |
      v
one canonical doom.c
```

The exact baseline used to author a generated transform must reproduce its local
oracle byte-for-byte. Compatible later source variants may preserve legitimate
upstream differences only when all configured postconditions and validation gates
still pass.

See `docs/technical/tooling/source-bound-diff-generator.md`,
`docs/technical/interoperability/doom-modernization.md`, and
`docs/technical/interoperability/doom-amalgamation.md`.
