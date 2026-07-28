# Quality Comparison Report

> **Generated-output acceptance snapshot.** The checked-in `metrics.json` and
> `report.tex` compare the untouched root source with the source-bound generated
> `quality/out/doom_fixed/` tree. The compact report is aggregate evidence; the
> dedicated guest validator and six-target matrix remain the hard acceptance gates.

`generate.py` creates the compact, reproducible before/after report for the
DOOM quality experiment.

The accepted comparison is between two different local trees:

- repository-root `doom/` is the untouched pinned baseline corpus;
- `../out/doom_fixed` is the generated normalized corpus.

`generate.py` still defaults to the local oracle for authoring experiments, so final
acceptance refreshes pass `--after algorithms/doom/quality/out/doom_fixed` explicitly.

The generator runs the pinned LLVM 22.1.8 compiler, formatter, and repository
clang-tidy policy over both trees. It emits aggregate counts only:

- `report.tex` is the human-readable report with tables and charts;
- `metrics.json` contains the same aggregate measurements for auditing.

Individual finding paths and messages are never copied into either artifact.
This keeps the report size independent of the number of diagnostics and avoids
artificially inflating repository source-line metrics with a diagnostic ledger.

WAD files are treated as test data, not source. Their count, bytes, and
SHA-256 identity are reported separately and never contribute to C/header LOC
or source-byte measurements.

The generator fails closed if either corpus changes between measurement and
validation. It never emits a report assembled from mixed revisions of a live
local tree.

Run from the repository root:

```text
python algorithms/doom/quality/comparison/generate.py
```

Optional `--before`, `--after`, `--tex`, and `--json` arguments make the input
and output paths explicit for experiments.