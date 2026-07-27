# Source-Bound Diff Tests

Tests for `algorithms/diff` use only repository-owned synthetic fixture trees.
No DOOM source belongs in this directory.

The suite currently proves exact reconstruction, source-span reuse, deterministic
identity primitives, insertion-stable anchors, structural/anchor threshold
boundaries, distributed multi-file evidence, wrong-source rejection, and opaque
asset non-dominance. Threshold source binding, behavior-clone rejection, and Rust
emission remain unfinished.
