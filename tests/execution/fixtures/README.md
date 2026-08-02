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

`.mbprof` starts with `MBPF`, metadata version 3, and a reserved zero field. It
then uses `u32` length prefixes for profile ID, fingerprint, published version,
and each feature; a `u32` feature count preserves stable order, followed by the
word-trit byte, `u32` profile capacity, and exact derived `u64` region memory
requirement. COFF structural admission compares the complete payload against the
artifact key. Missing, duplicated, writable, executable, relocated, malformed,
or mismatched metadata fails closed before semantic machine-code admission.

The envelope carries every input required to preflight direct objects for both
`MALBOLGE-PROFILE-001` and `MALBOLGE-PROFILE-002`. A same-profile object paired
with a key for a different region footprint fails structural admission.

Direct deopt and initial-halt revision 4 plus halt-observation revision 5 use
metadata v3. Exact x86-64/AArch64 object sizes are 413/415 bytes for deopt,
495/564 for register/counter halt, and 466/490 for initial halt respectively. The
halt fixtures bind `input_consumed=0x0000000123456789` and
`output_len=0x000000023456789a`, proving full-width counter materialization.

All fixtures are textual hexadecimal so repository hygiene can inspect them.
Tests reconstruct the exact bytes and compare them with the Rust emitters; fixture
updates are valid only when the owning emitter and the full validation surface
change together.
