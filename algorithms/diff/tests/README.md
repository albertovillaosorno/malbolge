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
Exact Rust-emission tests compile generated standalone source with `rustc -D
warnings`, execute the binary, verify exact reconstruction, and exercise wrong-source
and existing-output rejection. Compatible-variant placement/emission remains
unfinished.

Relocatable compatible placement tests preserve candidate insertions inside source-
backed ranges, preserve whole-file candidate changes, reject missing/ambiguous
boundaries transactionally, and lock the current byte-boundary reformat limitation.
Mapped semantic-placement tests cover canonical-to-raw span validation, zero-width
semantic markers, deterministic hashed locators, replacement/insertion/deletion,
candidate formatting and unrelated semantic additions, ambiguous/missing source
evidence, and fail-closed re-tokenization at unsafe replacement seams.
