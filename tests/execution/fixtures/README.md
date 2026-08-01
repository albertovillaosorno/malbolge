# Tiered execution fixtures

`region-effect-v3.hex` is the independently rendered byte-exact vector for the
portable effect-IR v3 encoding exercised by `tests/tiered_execution.rs`. The
415-byte encoding begins with `MBIR`, binds the declared profile ID and canonical
fingerprint, then carries the immutable target-profile requirement envelope:
published version, eight stable semantic features, word trits, and directly
addressed profile capacity. Verified budget, outcome, live-ins, and ordered
effects follow.

The six `native-*-coff.hex` fixtures freeze the complete direct Windows COFF
objects for x86-64 and AArch64. Every direct object contains:

1. one executable, non-writable `.text` section;
2. one initialized, read-only `.mbprof` section with no relocations;
3. the exact `malbolge_native_region_apply` external function symbol; and
4. no undefined host dependency.

`.mbprof` starts with `MBPF`, metadata version 2, and a reserved zero field. It
then uses `u32` length prefixes for profile ID, fingerprint, published version,
and each feature; a `u32` feature count preserves stable order, followed by the
word-trit byte and `u32` profile capacity. COFF structural admission compares the
complete payload against the artifact key. Missing, duplicated, writable,
executable, relocated, malformed, or mismatched metadata fails closed before
semantic machine-code admission.

The envelope is sufficient to compare a selected runtime with the complete
profile requirements used by `MALBOLGE-PROFILE-001`. It intentionally does not
claim the program-specific requested-memory value needed for
`MALBOLGE-PROFILE-002`.

All fixtures are textual hexadecimal so repository hygiene can inspect them.
Tests reconstruct the exact bytes and compare them with the Rust emitters; fixture
updates are valid only when the owning emitter and the full validation surface
change together.
