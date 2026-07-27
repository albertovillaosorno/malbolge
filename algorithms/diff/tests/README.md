# Source-Bound Diff Tests

Tests for `algorithms/diff` use only repository-owned synthetic fixture trees.
No DOOM source belongs in this directory.

The eventual suite must prove exact reconstruction, fuzzy admission, threshold
source binding, fail-closed behavior, deterministic generation, and rejection of
wrong-source or behavior-only clones.
