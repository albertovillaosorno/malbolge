# Tiered execution fixtures

`region-effect-v2.hex` is the independently rendered byte-exact vector for the
portable effect-IR v2 encoding exercised by `tests/tiered_execution.rs`. The
209-byte encoding begins with `MBIR`, binds the declared profile ID before the
canonical profile fingerprint, and then carries the verified budget, outcome,
live-ins, and ordered effects.

The six `native-*-coff.hex` fixtures freeze the complete direct Windows COFF
objects for x86-64 and AArch64. Every direct object contains:

1. one executable, non-writable `.text` section;
2. one initialized, read-only `.mbprof` section with no relocations;
3. the exact `malbolge_native_region_apply` external function symbol; and
4. no undefined host dependency.

`.mbprof` starts with `MBPF`, metadata version 1, a reserved zero field, and
`u32`-length-prefixed UTF-8 bytes for the exact profile ID and fingerprint. COFF
structural admission compares those bytes against the artifact key. Missing,
duplicated, writable, executable, relocated, malformed, or mismatched metadata
fails closed before semantic machine-code admission.

All fixtures are textual hexadecimal so repository hygiene can inspect them.
Tests reconstruct the exact bytes and compare them with the Rust emitters; fixture
updates are valid only when the owning emitter and the full validation surface
change together.
