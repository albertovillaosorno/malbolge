# Source-Bound Diff Tests

Tests for `algorithms/diff` use only repository-owned synthetic fixture trees.
No DOOM source belongs in this directory.

The suite currently proves exact reconstruction, source-span reuse, deterministic
identity primitives, insertion-stable anchors, structural/anchor threshold
boundaries, distributed multi-file evidence, wrong-source rejection, opaque asset
non-dominance, behavior threshold boundaries, mandatory compatibility,
already-fixed bug routing, unavailable-probe failure, behavior-only clone
rejection, bounded no-shell process execution, source-mirror isolation,
source/oracle-authored bug transcript classification, HKDF-SHA-256 vectors,
T-of-N source-bound key recovery, below-threshold/no-source rejection, tamper
rejection, insufficient-file-distribution rejection, and offset-shifted anchor
recovery, plus the RFC 8439 ChaCha20-Poly1305 AEAD vector and ciphertext/tag/AAD
tamper rejection. Protected exact-plan tests also prove deterministic ciphertext,
no plaintext literal retention, transform-without-source rejection, metadata AEAD
binding, oracle-free exact reconstruction, and no output before authentication.
Compatible-variant placement and Rust emission remain unfinished.
