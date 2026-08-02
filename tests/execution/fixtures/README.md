# Tiered execution fixtures

`region-effect-v3.hex` is the independently rendered byte-exact vector for the
portable effect-IR v3 encoding exercised by `tests/tiered_execution.rs`. The
415-byte encoding begins with `MBIR`, binds the declared profile ID and
canonical
fingerprint, then carries the immutable target-profile requirement envelope:
published version, eight stable semantic features, word trits, and directly
addressed profile capacity. Verified budget, outcome, live-ins, and ordered
effects follow.

The twenty `native-*-coff.hex` fixtures freeze the complete direct Windows
COFF
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

Direct deopt and initial-halt revision 4, halt-observation revision 5,
halt-fetch/non-graphical/no-operation revision 2, and
jump-code/jump-data/rotate/crazy revision 1 use metadata v3. Exact
x86-64/AArch64 object sizes are 413/415 bytes for
deopt,
495/564 for register/counter halt, 466/490 for initial halt, 535/628 for
graphical
halt fetch, 538/631 for non-graphical termination, 557/658 for no-operation,
622/731 for jump-code, 564/699 for jump-data, 578/732 for rotate, and
577/731 for crazy, respectively.
The wider fixtures bind `input_consumed=0x0000000123456789` and
`output_len=0x000000023456789a`, proving full-width counter materialization. The
fetched-terminal pairs bind `C=5` and an 8-word memory requirement: halt-fetch
requires `memory[5]=76`, which the VM-owned profile decoder maps to `v`, while
non-graphical requires `memory[5]=0`. The no-operation pair requires 9 words,
binds `memory[5]=77`, VM-classifies it as no-op, encrypts it to 65, and advances
`C=5`/`D=7` to 6/8 without changing accumulator, counters, or termination. The
jump-data pair requires the exact 125-word exit footprint, binds code/data
live-ins
`memory[5]=35` and `memory[7]=123`, encrypts the code word to 93, and advances
`C=5`/`D=7` to 6/124. The jump-code pair requires 13 words and binds
`memory[5]=93`, `memory[7]=11`, and `memory[11]=68`; it encrypts the loaded
target
to 33 and advances `C/D` to 12/8. The rotate pair requires 9 words, binds
`memory[5]=34` and `memory[7]=10`, writes the rotated data value 1594326 and
encrypted code value 122, and advances `A/C/D` to 1594326/6/8. The crazy
pair also requires 9 words, binds `A=20`, `memory[5]=57`, and
`memory[7]=10`, writes Crazy result 2391494 and encrypted code value 91, and
advances `A/C/D` to 2391494/6/8. Every memory-backed fixture guards its exact
metadata-bound IR footprint before dereferencing guest memory.

All fixtures are textual hexadecimal so repository hygiene can inspect them.
Tests reconstruct the exact bytes and compare them with the Rust emitters;
fixture
updates are valid only when the owning emitter and the full validation surface
change together.
