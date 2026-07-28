# Research Tests

Keep deterministic semantic, regression, and experiment-harness tests for this
algorithm here. Research output is not accepted as correctness evidence by
itself.

`exact_duplicate.rs` covers duplicate-rich, all-unique, empty, shared-prefix,
near-length, and one-byte-different corpora. Every distinct byte sequence must
retain its own representative; only byte-identical inputs may share one.
