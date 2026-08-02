# Historical Malbolge museum

## Purpose

`examples/museum/` records historically important Malbolge programs without
turning third-party source code into repository test data, compiler fixtures, or
MIT-licensed project material.

This is a museum, not a conformance corpus.

## Boundary

Museum entries may record:

- author and date;
- primary and archived source locations;
- historical behavior and significance;
- locally observed byte length and SHA-256 for identification;
- compatibility notes discovered by our own tooling.

Museum entries do **not** imply permission to redistribute a historical program.
When an explicit redistribution license cannot be established from an
authoritative source, the program itself is intentionally not vendored.

The museum also does not contain:

- DOOM source or derived DOOM code;
- project compiler sources or compiler outputs;
- benchmark algorithms or challenge fixtures;
- GitHub mirrors used merely as secondary copies;
- generated C views.

Generated or decompiled views belong to local tooling output and are
rebuildable.

## Current exhibits

- `hello-world-andrew-cooke/` — Andrew Cooke's 2000 beam-search-generated
  `HEllO WORld` program.
- `99-bottles-straight-line/` — Johannes E. Schindelin's 2005
  print/decode/decompress demonstration.
- `99-bottles-real-loop/` — Hisashi Iizawa's 2005 real-loop implementation,
  associated with the Nagoya Malbolge programming work.

## Tooling

The planned professional Malbolge decompiler is a general product tool and is
not museum-specific. A small museum helper may invoke that decompiler to create
local C or other readable views, but generated views must remain outside the
committed museum unless their authorship/licensing is independently clear.

A locally acquired classic specimen may be rendered without adding it to the
museum:

```text
cargo run --bin museum_convert -- INPUT.malbolge OUTPUT.c
```

The helper never downloads a specimen and always selects frozen
`malbolge-1998`.
