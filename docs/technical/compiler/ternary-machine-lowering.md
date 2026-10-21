# Ternary machine lowering

## Status

Active

## Purpose

Lower typed C IR into a compact ternary virtual-machine representation suited to
Malbolge instead of translating C operations directly instruction by
instruction.

## Scope

This document governs the following declared TODO scope:

- `compiler/`
- `src/`
- `tests/compiler/`
- `tests/ternary_lowering.rs`

## Current Behavior

### Implemented Initial Model

`src/compiler/ternary-lowering/` now owns the first executable pre-layout target
model. Its inbound port accepts a copied semantic projection from already
validated typed IR rather than importing the upstream implementation type. The
application lowerer currently admits no-argument functions containing one
entry block, no phi nodes, exact `bool`/`u8`/`i32`/`u32` constants,
`i32`/`u32` bitwise AND/OR/XOR, addition/subtraction, multiplication,
signed/unsigned division and remainder, and typed left and right shifts,
unsigned byte-to-word extension,
signedness-changing and same-kind 32-bit integer bitcasts,
32-bit-to-`u8` and signed `i8` truncation, and
typed-IR
`ByteInput`/`ByteOutput` effects with an `i32`, `u32`, `i8`, `u8`, Boolean, or
value-free `void` return.
Other admitted typed-IR shapes fail explicitly.

Exact 32-bit constant bit patterns are converted to a fixed 21-trit,
least-significant-trit-first scalar. Twenty trits are insufficient for every
`u32` bit pattern, while 21 trits cover the complete 32-bit representation
domain. The pre-layout program retains upstream function/value IDs plus exact
source spans, source digest, ABI identity, typed-IR version, and target-profile
identity.

Every unsigned 8-bit constant is represented by exactly six least-significant
trits first: five trits cannot span all byte values. A new `MaterializeU8`
operation carries its upstream SSA result and source span, and its byte value
can feed `ByteOutput` without host evaluation or signed widening.

The pre-layout projection now copies each validated typed function's result
category. An admitted `u8` function can return a defined successful byte;
an `i32` function must still return a defined signed 32-bit value. A `u32`
function may return only a separately typed, exact unsigned 32-bit value.
The lowerer rejects forged categories and mismatched return SSA value types.

During lowering, defined byte, signed 32-bit, and unsigned 32-bit SSA
identities are tracked separately by
ordered sets rather than scanned in insertion-order vectors. Definition
checks and operand validation thus take logarithmic lookup time while keeping
exact duplicate detection, deterministic output order, and canonical bytes.
The collection change does not weaken the independent program validator.

Independent canonical restoration has now been checked across all 729 valid
six-trit digit combinations, accepting only values `0..255`. Every value
`256..728` fails scalar admission, and a forged byte-definition SSA ID or
an output use of the wrong scalar type fails independent stage validation.

Canonical `MCTR` decoding bounds collection counts against remaining wire
bytes and grows decoded function/operation vectors only as records are parsed.
Each function requires at least 36 bytes and each operation at least 25 bytes,
including the operation tag and fixed 24-byte provenance span. This bound is
exact for `ReturnVoid`; shorter declared collections are rejected before an
invalid operation tag is read.

An exaggerated count with just enough trailing padding no longer causes an
eager count-sized allocation before the first malformed record is rejected.
The decoder does not yet impose a separate global object-memory ceiling.

Typed `ByteInput`/`ByteOutput` lower in source order to explicit target
byte-effect operations with SSA type/order validation. These operations preserve
the typed IR's successful `u8` semantics and do not impersonate the raw profile
input word or its EOF case.

The same SSA boundary lowers exact typed `i32` and `u32` bitwise AND, OR,
and XOR, plus validated `i32`-to-`u8` truncation. Each bitwise operation
requires both prior SSA operands to have the declared signed or unsigned
32-bit type and preserves operand/result identities and provenance without
executing guest values on the host.

Together with constant materialization and `ByteOutput`, AND and truncation
express the exact low-eight-bit transformation used by
`malbolge_guest_output_byte`. Direct calls to that runtime helper are not yet
recognized by this stage.

Canonical `MCTR` version-one encoding retains existing operation tags `0..5`
byte-for-byte. Closed tags `6` (bitwise OR) and `7` (bitwise XOR) carry three
`u32` SSA identities and their 24-byte source span. Tag `8` materializes `u8`
with a result `u32`, exactly six trits, and the same source span. Tag `9`
encodes `ReturnU8` as the 24-byte terminator span and returned byte SSA ID,
leaving historical `i32` return tag `4` byte-exact.

Tags `10` and `11` add `MaterializeU32` and `ReturnU32` respectively. The
materialization carries a result ID, the same exact 21-trit bit pattern as
signed 32-bit materialization, and the original source span. The return tag
carries the same terminator span and SSA ID as earlier return operations.

The independent decoder admits `ReturnU8` and `ReturnU32` only as final
terminators using values of the matching unsigned type; tag `4` continues to
require signed `i32`. Rewriting a signed tag to its unsigned counterpart is
rejected even when all scalar trits are valid.

Tags `12`, `13`, and `14` encode unsigned 32-bit AND, OR, and XOR with the
same three SSA IDs and 24-byte source span as signed tags `0`, `6`, and `7`.
Their independent stage validation rejects wrong-typed operand definitions,
forged signed tags, missing SSA uses, or duplicate result identities.

Both operands may legally reference the same previously defined unsigned SSA
value. An admitted typed-IR fixture verifies all three bitwise operations over
zero, unit, sign-bit, alternating-bit, and maximum unsigned patterns, and
checks complete canonical ternary checkpoint restoration without duplicating
the shared operand's definition.

A complementary signed `i32` alias fixture verifies AND/OR/XOR when both
operands use one defined SSA identity, retaining the original 32-bit pattern,
source spans, typed return, and independent canonical target restoration across
the same five boundary patterns. Neither signedness is evaluated on the host.

Tag `15` adds `TruncateU32ToU8` with the same SSA-result, 24-byte source
span, and SSA-use layout as signed truncation tag `5`. The lowerer requires a
defined `u32` operand, produces an exact unsigned byte, and retains the low
eight bits without host execution. Independent checkpoint validation rejects
a signed truncation tag applied to unsigned input and undefined SSA uses.

Tag `16` adds `ZeroExtendU8ToU32` with the same result-ID, 24-byte source
span, and source-use layout as the existing casts. It accepts only a defined
byte-valued SSA operand and produces a distinct unsigned 32-bit SSA result;
the target stage does not evaluate guest bytes or invent EOF behavior.
Canonical admission rejects retagging this cast as either truncation form.

Tags `17` and `18` add `BitcastI32ToU32` and `BitcastU32ToI32` with the
same result-ID, 24-byte source span, and SSA-use layout as existing casts.
Each direction preserves all 32 original bits without host execution and
creates a new result under the required destination signedness. Independent
checkpoint admission rejects swapped direction tags and undefined uses.
The exact scalar bits, SSA IDs, and source provenance round-trip without
changing any older operation tag.

A synthetic second cast appended to an admitted typed-IR projection verifies
signed-to-unsigned-to-signed and reverse chains over representative boundary
bits. Independent canonical recovery preserves both cast SSA definitions
and the final return category. When the destination signedness matches,
a separate result may also reinterpret the original source without a new
bit pattern or loss of source provenance.

Tags `19` through `22` add `AddI32`, `AddU32`, `SubtractI32`, and
`SubtractU32`. They use the existing left/result/right SSA ID and 24-byte
source-span layout for 32-bit binary operations without changing older tags.
The pre-layout stage preserves signedness and does not execute arithmetic or
claim wrapping signed overflow semantics; target realization remains separate.
Independent decoder validation rejects wrong-signedness operands, unknown
SSA uses, duplicate results, and the next unassigned tag `23`.

Tags `23` and `24` add `MultiplyI32` and `MultiplyU32` with the exact
left/result/right SSA identity and 24-byte span used by existing 32-bit
binary operations. Both operands must be previously defined with the exact
signed or unsigned result type; the symbolic stage does not evaluate integer
arithmetic, impose a signed-overflow interpretation, or change old encodings.
Independent canonical admission rejects a retagged signedness, undefined uses,
and the first unassigned tag `25`. Fresh lowering matches inspector-backed
checkpoint recovery; all ten crash-publication boundaries preserve each of
the two multiplication generation identities.

Tags `25` through `28` add typed `ShiftLeftI32`, `ShiftLeftU32`,
`ShiftRightArithmeticI32`, and `ShiftRightLogicalU32` operations with the
original three SSA IDs and 24-byte source span. Source operands and shift
counts must be previously defined at the exact signed or unsigned 32-bit
category; the symbolic stage does not evaluate shift counts or assume
undefined signed-shift behavior. Independent canonical admission rejects
swapped signedness/direction and unknown SSA uses; tag `29` was unassigned
at initial admission and now identifies signed division.
Fresh compiler selection converges with inspector-backed progress restoration,
including all ten crash boundaries for every supported shift variant.

Tags `29` through `32` add `DivideI32`, `DivideU32`, `RemainderI32`, and
`RemainderU32` with the same three SSA identities and 24-byte source span as
other 32-bit binary operations. Signed and unsigned variants require operands
and result types with matching signedness; the pre-layout compiler does not
evaluate guest division, division by zero, or signed overflow. Canonical
checkpoint admission rejects swapped signedness, missing SSA operands,
duplicate definitions, and unknown tag `60`. Fresh typed lowering
and inspector-backed checkpoint recovery converge across all ten crash
boundaries for each of the four operations.

A separate admitted typed-IR boundary suite preserves symbolic division and
remainder when the divisor is zero, and when the operand pair is
`0x80000000`/`0xFFFFFFFF`. It verifies the original divisor bit pattern,
SSA and provenance identities, canonical target encoding, and complete
checkpoint restoration without executing an invalid or overflowing host
arithmetic operation.

Tags `33` and `34` add `BitcastI32ToI32` and `BitcastU32ToU32` with the
existing result-ID, source-span, and operand-ID cast layout. Both operations
preserve the original 32-bit pattern without host evaluation and create a
separate SSA definition of the same signedness. Typed-IR admission and
canonical restoration preserve distinct source/result identities for all
boundary patterns and reject cross-signedness tag substitution, undefined
sources, and future tag `60`. Real inspector-backed restoration converges
with fresh lowering; all ten crash-publication boundaries preserve both
same-kind generations without rewriting any prior opcode.

Tags `35` through `38` add `EqualI32`, `EqualU32`, `NotEqualI32`,
and `NotEqualU32`, each with two previously defined, same-kind 32-bit SSA
operands, a distinct boolean SSA result, and the existing binary-operation
identity/span layout. Tag `39` adds `ReturnBool` with the historical return
record layout. The stage keeps comparisons symbolic instead of evaluating
signed or unsigned guest values on the host, and does not widen the Boolean
result into a byte or integer implicitly. Independent canonical admission
requires exact operand signedness and rejects retagged signedness, undefined or
duplicate SSA, malformed boolean returns, and the next unassigned tag `60`;
typed-IR and ternary round trips cover both comparisons, signed and unsigned
32-bit boundary patterns, and legal aliasing of both operand uses to one SSA
value, preserving source spans and complete target identity.

Tags `40` through `43` add `LessSignedI32`, `LessSignedEqualI32`,
`LessUnsignedU32`, and `LessUnsignedEqualU32` in that order. Each retains
two same-kind, previously defined 32-bit SSA operands, produces one distinct
Boolean SSA result, and uses the canonical binary identity/span layout.
The pre-layout stage never performs a signed or unsigned host comparison.

Typed-IR admission rejects predicates that disagree with the operand
signedness. Independent canonical checkpoint restoration rejects such
substitutions, undefined operands, duplicate Boolean results, and unknown
tag `60`. Regression fixtures cover both predicates across signed/unsigned
boundary patterns, exact source bits, and legal aliased SSA operands.

Tag `44` adds `BoolToI32` using the canonical cast result-ID,
source-span, and value-ID layout. Validated typed-IR `BoolToSigned` now accepts
a defined Boolean SSA input and exact `i32` destination only; it preserves
the zero-or-one conversion symbolically without computing a guest value in
the host or silently reinterpreting Boolean as an integer.

Independent target validation rejects an integer-typed source, duplicate
result ID, and swapped bitcast tags; canonical restoration rejects the next
unassigned tag `60`. A typed-IR round-trip fixture combines integer
comparison, Boolean conversion, and signed return across boundary patterns.
Other destination widths and Boolean operations remain outside this slice.

Tags `45` and `46` add `I32ToBool` and `U32ToBool` with the existing
cast result-ID, source-span, and operand-ID layout. Admitted typed-IR
`IntegerToBool` consumes a defined exact signed or unsigned 32-bit source and
produces a distinct Boolean SSA result, preserving C nonzero truth semantics
symbolically without comparing a value in host arithmetic.

Independent target validation rejects signedness-tag substitutions, undefined
source IDs, duplicate result definitions, and casts using a noninteger source.
Typed-IR and canonical ternary round trips cover zero, the signed boundary,
and maximum 32-bit bit patterns with Boolean returns; unknown tag `60` remains
unassigned in the initial 32-bit conversion slice. The subsequent byte case
has its own tag and contract below; pointer truth conversion remains open.

Tag `47` adds `U8ToBool` in the same canonical cast layout. Its source
must be a previously defined successful `u8` scalar (including deterministic
byte input or materialized byte constants), and its result is a distinct
Boolean SSA identity retaining the original source span and byte value bits.

Canonical checkpoint validation rejects retagging that source as signed or
unsigned 32-bit, duplicate result identities, undefined byte operands, and
the next unassigned opcode `60`. Typed-IR and target round trips cover zero,
one, `0x7f`, `0x80`, `0xff`, and the successful byte-input effect without host
truth evaluation. EOF/raw input-word handling remains a separate realization.

Tag `48` adds `MaterializeBool` for a validated one-bit typed-IR Boolean
constant. Its canonical payload is the operation tag, a little-endian `u32`
result ID, exactly one digit `0` or `1`, and the unchanged 24-byte source span.
The new Boolean SSA value can return directly through `ReturnBool` or feed an
explicit `BoolToI32` conversion; the lowerer does not fold a guest cast.

The independent decoder rejects out-of-domain Boolean digits as `InvalidScalar`,
treats duplicate or missing Boolean SSA definitions as validation failures,
and rejects unassigned tag `60`. Typed-IR and checkpoint round trips cover
both values with direct Boolean and promoted signed returns, preserving the
original source span and result identities.

An exhaustive decoder regression enumerates all 256 possible byte digits for
both original Boolean constants, requiring canonical restoration for `0` and
`1` alone and `InvalidScalar` for every other value.

Production progress-inspector recovery now agrees with fresh lowering for
both Boolean constant-return forms and explicit signed promotion. Invalid
digits and unknown tags fail closed after opaque state extraction, and all
ten checkpoint crash boundaries retain only committed generations.

A separate composition regression preserves five distinct SSA identities
across the source Boolean literal, signed conversion, unsigned-byte
truncation, byte truth conversion, and final signed conversion. False and true
retain their source spans through typed-IR and ternary canonical round trips.

Independent canonical and inspector recovery reject mismatched truncation,
cast-width substitutions, and undefined byte operands; all ten crash
publication boundaries preserve the committed predecessor checkpoint.

Production inspector-backed progress recovery now converges with fresh
lowering for signed and unsigned equality, ordered comparisons, Boolean-to-i32,
and all signed, unsigned, and byte-width integer-to-Boolean casts. A separate
u32-to-u8-to-Boolean-to-i32 fixture retains each intermediate SSA definition,
including values whose high 24 bits truncate to a zero byte.

Inspector restoration rejects cross-signedness comparison opcodes and
cross-width cast retagging before returning checkpoint state. All ten durable
checkpoint publication/crash boundaries retain only committed generations
when advancing from the original constant-return program to each selected
Boolean comparison, byte source, or conversion family.

Tag `49` adds a value-free `ReturnVoid` terminator for validated no-result
function signatures. The canonical record consists of its tag plus the exact
24-byte source span, with no SSA operand, dummy result, or host-side return
value. The inbound projection distinguishes `Void` from unsupported `Other`
and rejects either a missing value in a nonvoid function or a present value
in a void function.

The independent decoder accepts the new 25-byte minimum operation record but
rejects shorter records before dereferencing their tags. Semantic validation
requires `ReturnVoid` to be the final operation, preserving prior byte effects
in source order; malformed value/return types and successor tag `60` fail
closed. Empty void functions and byte-input/output void functions round-trip
from admitted typed IR through canonical target bytes without host execution.

Production inspector recovery agrees with fresh lowering for both void cases,
and rejects unknown retagged terminators after checkpoint extraction. All ten
crash-publication boundaries preserve the committed generation for each case.

Mixed two-function modules also preserve independent SSA scopes and typed
returns when a void member precedes or follows an `i32`-returning member.
Canonical restoration and the production inspector converge in either order,
including void byte effects; the independent validator rejects reordered
function IDs. All ten crash-publication boundaries preserve the previously
committed generation for each combination.

Tag `50` materializes one signed `i8` SSA identity with its exact source
span and a six-trit encoding of the original unsigned-byte-shaped bit pattern.
It is distinct from unsigned `u8` materialization tag `8`: the signed
interpretation belongs to the SSA type and is not evaluated on the host.

Tag `51` adds `SignExtendI8ToI32`, preserving the original cast span, new
signed `i32` result ID and previously defined signed byte source ID in the
canonical cast layout. Only validated typed-IR signed extension from `i8` to
`i32` is admitted; other widths remain outside this slice.

All 256 source byte patterns survive the canonical typed-IR projection and
ternary checkpoint round trips, including `0x7f`, `0x80`, and `0xff`.
Independent restoration rejects unsigned-byte retagging, zero-extension
substitution, undefined SSA values and successor tag `60`.

Production progress-inspector recovery converges with fresh lowering for
representative positive and negative byte patterns. All ten checkpoint
publication/crash boundaries preserve only the committed generation for each
selected signed-byte extension state.

Tag `52` adds `I8ToBool`, a distinct Boolean SSA result from one defined
signed-byte operand. It uses the existing result-ID, 24-byte source-span and
operand-ID cast layout while preserving C nonzero truth testing symbolically,
without treating signed bytes as unsigned input effects.

All 256 signed 8-bit patterns round-trip through typed IR and canonical
target bytes with the correct Boolean return type and untouched source bits.
Independent validation rejects unsigned-byte or signed-word cast tags,
undefined SSA, duplicate results, wrong destination kinds and unknown tag `60`.

Production inspector restoration matches fresh lowering for positive and
negative signed-byte truth conversions. It independently rejects retagged
signedness and tag `60`; all ten durable crash boundaries preserve the
previously committed generation for representative source patterns.

Tags `53` and `54` add equal-width narrow integer reinterpretations:
`BitcastI8ToU8` and `BitcastU8ToI8`. Both use the existing cast-record layout
with a distinct SSA result, exactly one previously defined byte-width operand,
and the original typed-IR cast provenance. Their six-trit source pattern is
never evaluated, widened or changed on the host.

For each direction, all 256 possible source-byte patterns preserve the exact
typed-IR constant, conversion SSA identity and destination-specific extension
through canonical typed/target round trips. The independent decoder rejects
cross-direction, signed-word and Boolean retags, undefined operand IDs,
duplicate SSA result definitions, and first unknown tag `60`.

The production inspector restores each direction and agrees with fresh entry
for zero, sign-boundary and maximum patterns. Ten process-crash/checkpoint
publication boundaries protect the previously committed generation for each
selected signedness direction and source bit pattern.

Tags `55` and `56` add same-kind byte reinterpretations:
`BitcastI8ToI8` and `BitcastU8ToU8`. A validated equal-width typed-IR cast
preserves the exact signedness category but allocates a distinct SSA result;
even zero and all-one patterns never collapse the two value identities.

Both same-kind forms round-trip all 256 possible source bytes through the
admitted typed projection, canonical target wire, and matching typed integer
extension/return without host evaluation. Independent restoration rejects
cross-kind and swapped-direction retags, duplicate or undefined SSA, and
future tag `60`.

Production inspector restoration agrees with fresh lowering for the same-kind
forms. Every crash-publication boundary preserves the previously committed
checkpoint for representative zero and sign-boundary patterns.

Tag `57` adds `ReturnI8`, a signed-byte terminator consuming a defined
`i8` SSA operand without implicit 32-bit promotion. It retains the exact
source span and operand ID under the existing 29-byte value-return layout.

A fully validated typed `i8` constant-return function round-trips all 256
byte patterns through typed IR, fresh projection and canonical target bytes.
Direct projected returns from a signed constant or unsigned-byte-to-signed
bitcast also preserve original SSA and source-span identities for each pattern.

Independent checkpoint admission rejects retyping `ReturnI8` as unsigned
byte, signed word, or unsigned word; undefined operands and tag `60` fail
closed. Production-inspector restoration agrees with fresh lowering and all
ten crash-publication boundaries preserve committed state for representative
byte patterns and both supported signed-byte source families.

Tags `58` and `59` add `TruncateI32ToI8` and `TruncateU32ToI8`.
Both are symbolic low-eight-bit conversions from separately typed 32-bit
sources to a fresh signed-byte SSA result. They preserve the original cast
span and unchanged source SSA without host sign interpretation.

Validated typed-IR fixtures round-trip all 256 low byte patterns for each
source signedness with zero, high-sign-bit, and all-one upper word bits.
Each path terminates directly through signed-byte `ReturnI8`, preserving
independent definition and use identities in canonical `MCTR` checkpoints.

Independent admission rejects cross-signedness retags, unsigned-byte result
substitutions, duplicate results, undefined sources, truncated records, and
unknown tag `60`. Production inspector recovery converges with fresh lowering
and all ten crash-publication boundaries retain only committed generations
for representative low-byte and upper-word patterns.

Older decoders reject newly emitted tags, and resume remains bound to the exact
compiler toolchain fingerprint. This slice does not yet realize branching or
C integer promotions of the Boolean result.

Real progress-inspector restoration now converges with fresh compilation for
all three unsigned bitwise operations. Rewritten signed bitwise tags are
rejected by independent canonical stage admission after checkpoint extraction.
All ten crash publication boundaries also preserve the committed generation
when moving from signed to unsigned bitwise-return state.

The real compiler progress inspector restores canonical unsigned 32-bit
returns with the same output as fresh typed lowering. A checkpoint whose
`ReturnU32` tag is rewritten to signed `Return` is rejected after opaque-state
extraction, and all ten crash boundaries preserve the committed generation
while the return type changes from signed to unsigned.

The product compiler's fresh ternary selection and real progress-inspector
checkpoint restoration now converge for a byte-return function. A forged
checkpoint that rewrites `ReturnU8` to the `i32` return tag fails independent
post-extraction stage validation. All ten crash publication boundaries have
been exercised when the committed state changes from `i32` to `u8` return.

Scalar decoding rejects digits outside `0..2`, six-trit values above 255, and
any noncanonical byte spelling.

Independent `MCTR` restoration rejects forged OR/XOR result IDs, missing SSA
operand identities, and the next unassigned operation tag even when a producer
bypasses inbound typed-IR projection and lowering.

A separate pure runtime-helper port now admits exactly
`malbolge_guest_decode_input_word` and `malbolge_guest_output_byte` under the
reviewed current profile. It lowers those identities to declarative recipes
rather than host-evaluated values: input records the `0..255` byte domain, the
profile-projected EOF word, exact `EOF == -1` bits, and valid/invalid runtime
statuses; output records the low-eight-bit mask. An EOF projection overlapping
the byte domain fails closed.

Input-helper realization now expands the canonical recipe into four ordered
pre-layout exits: null result pointer publishes `INVALID_ARGUMENT` without a
write, byte input publishes the raw word as `i32` plus `VALID`, exact EOF
publishes `-1` plus `VALID`, and the final unmatched branch preserves result
storage while publishing `INVALID_INPUT_WORD`. Output-helper realization keeps
the exact low-byte mask. No branch addresses or host evaluation enter this
representation.

A separate call-frame helper port admits exactly
`malbolge_guest_frame_validate`, `malbolge_guest_frame_encode`, and
`malbolge_guest_frame_decode` under `malbolge-c32-v1` and
`malbolge-guest-runtime-v1` identity. Shared declarative semantics bind the
ABI's
32-byte hidden header and 16-byte frame alignment plus runtime statuses
`VALID=0`, `INVALID_ARGUMENT=1`, and `INVALID_FRAME=5`.

Frame-validator realization preserves the checked-in C condition order as six
pre-layout exits: null frame pointer, extent below 32 bytes, misaligned extent,
null argument-block pointer, nonzero flags, then success. The first branch
returns `INVALID_ARGUMENT`, the four shape branches return `INVALID_FRAME`, and
the final branch returns `VALID`.

Frame encode/decode realization binds the eight ABI `u32` fields at byte offsets
`0,4,8,12,16,20,24,28` in checked-in C order and marks each transfer
little-endian. Encode checks the output wire pointer/size, validates the source
frame, builds a scratch wire image, then publishes all 32 bytes atomically.
Decode checks both pointers/size, reads all fields into scratch state, validates
that scratch frame, and only then publishes the decoded frame.

A separate heap-helper port admits exactly `malbolge_guest_heap_init` and
`malbolge_guest_heap_allocate` under the same ABI/runtime identities. Shared
semantics bind 16-byte alignment/header geometry, minimum block span 32 bytes,
`VALID=0`, `INVALID_ARGUMENT=1`, `OUT_OF_MEMORY=2`, and
`CORRUPT_STATE=3`. Heap initialization preserves the checked-in short-circuit
guards and publishes `arena`, `capacity`, and `used=0` only after they pass,
then
zeros exactly the supplied arena capacity.

Allocation first requires caller-owned result storage and canonical heap shape,
then publishes `result = NULL` before complete chain validation. Zero-size
requests return `VALID` with that null result. Positive sizes compute the
16-byte-aligned payload plus 16-byte header with overflow-to-`OUT_OF_MEMORY`,
then scan blocks in ascending offset order and select the first free block whose
span fits.

A first-fit match uses the checked-in split-or-claim rule: a remainder of at
least 32 bytes becomes a canonical free block, otherwise the whole block is
claimed. The payload pointer is published only after metadata mutation, then the
helper returns `VALID`. If no free block fits, allocation overflow-checks
`used + required` against capacity, writes one allocated tail header, publishes
the tail payload pointer, then publishes the new `used` extent and returns
`VALID`. No global arena address is selected by this helper boundary.

Zeroed allocation first requires result storage and publishes `result = NULL`.
If count or size is zero it delegates directly to the canonical zero-size
allocator path. Otherwise `count * size` is checked in the `u32` domain with
overflow mapped to `OUT_OF_MEMORY`, then the positive total is delegated to the
canonical allocator plan. The helper preserves the checked-in post-allocation
status/non-null test before zeroing exactly `total` payload bytes and returning
`VALID`.

Release first validates canonical heap shape and the complete block chain, so a
late corrupt block fails before the target block is mutated. A null
pointer
returns `VALID`; otherwise the helper requires an exact payload-pointer match to
an allocated block, rewrites that block with preserved span plus
zero
requested/reserved words and free state, then coalesces adjacent free blocks.
Finally it scans for a free tail block and, when present, publishes that block's
offset as the new `used` extent before returning `VALID`.

Release first validates canonical heap shape and the complete block chain, so a
late corrupt block fails before the target block is mutated. A null
pointer
returns `VALID`; otherwise the helper requires an exact payload-pointer match to
an allocated block, rewrites that block with preserved span plus
zero
requested/reserved words and free state, then coalesces adjacent free blocks.
Finally it scans for a free tail block and, when present, publishes that block's
offset as the new `used` extent before returning `VALID`.

The current typed IR cannot yet represent declaration-only external helper
callees: direct `Call` targets resolve only to module-local functions, and every
function must own a reachable entry block. Therefore direct helper-call
integration remains open even though helper branch/result/status semantics now
have an explicit pre-layout execution plan.

A public byte-stream wrapper planner composes those helper recipes with the raw
intrinsic operations using the checked-in guest stdio order. `getchar` plans
`InputWord` before decode and returns decoded `i32` byte-or-EOF semantics;
`putchar` plans low-byte reduction before `OutputByte` and returns the emitted
byte widened to `i32`. A follow-on realization step revalidates the complete
wrapper plan and replaces only the raw intrinsic with the profile-bound
`MachineIoOperation`; forged plan order and malformed/colliding profile
projections fail closed.

Wrapper-control-flow realization then re-derives the machine plan before making
the public wrapper sequence explicit. `getchar` initializes decoded storage to
EOF, performs machine input, executes the input-helper control flow, guards for
`VALID`, returns EOF on helper failure, and otherwise returns the decoded `i32`.
`putchar` executes low-byte helper semantics, performs machine output, and
returns
the emitted byte widened to `i32`. No branch address or source-cell placement is
assigned at this stage.

The canonical libc manifest remains unchanged and both routines stay
`contracted_unavailable` until wrapper source placement and complete target
layout are executable.

The separate raw runtime-intrinsic port admits only
`malbolge_guest_intrinsic_input_word` and
`malbolge_guest_intrinsic_output_byte` under the exact `malbolge-2026` profile.
Those identities lower to distinct pre-layout `InputWord` and `OutputByte`
operations; `InputWord` explicitly includes the selected profile's EOF word.
Unknown intrinsic names or profile drift fail closed.

A separate target-profile projection copies the current descriptor's exact
profile ID, input/output instruction bytes, and EOF word. Runtime I/O
realization uses only that projection, producing profile-bound machine
operations
without hardcoded `/` or `<` characters; colliding projected input/output
instructions or profile drift fail closed.

For an already-selected code-pointer position, the target-cell encoder exhausts
graphical ASCII `33..126` through a canonical instruction-decoder port and
requires exactly one source cell whose VM decode equals the realized operation.
The compiler therefore does not copy XLAT1. Missing or ambiguous inverse
encodings fail closed.

A separate startup port accepts a heap extent only after another stage has
resolved its guest logical location. Startup planning validates the exact
`malbolge-c32-v1` object-pointer encoding, 16-byte arena alignment, aligned
capacity of at least 32 bytes, `u32` logical-address containment, exact
`malbolge-2026` profile identity, and exact
`malbolge_guest_runtime_bind_heap` symbol. The resulting plan contains exactly
one bind action followed by user entry, so later layout/linkage cannot silently
place allocation-capable user code before the required bind.

This is executable compiler lowering but not complete target code generation.
Global layout/address assignment, concrete heap-arena placement, executable
runtime-call encoding, complete source sequencing, typed-IR external-call
binding, wrapper branch-address/source-cell placement, target serialization, and
complete Malbolge emission remain downstream work.

### Authoritative Inputs

The first implementation must consume existing identities without renaming or
reinterpreting them:

- canonical compiler state is `malbolge-typed-ir-v1` under ABI
  `malbolge-c32-v1`, preserving the module's exact source and target-profile
  provenance;
- guest-runtime semantics are versioned by `malbolge-guest-runtime-v1`, whose
  current reviewed target profile is `malbolge-2026`;
- compiler-generated startup must realize the one-shot
  `malbolge_guest_runtime_bind_heap` entry before allocation wrappers become
  available to user code;
- byte input and output must realize the exact declaration-only identities
  `malbolge_guest_intrinsic_input_word` and
  `malbolge_guest_intrinsic_output_byte`; and
- the guest-runtime contract's `host_fallback` value is `forbidden`, so none of
  these operations may be replaced by host callbacks in accepted lowering.

The pre-layout program now has one concrete portable serialization identity,
`malbolge-ternary-ir-v1`. Canonical bytes begin with `MCTR`, then little-endian
wire version `1` and the retained typed-IR input version. ABI, target-profile,
and source identities are length-prefixed UTF-8; the normalized-source SHA-256
is copied as 32 raw bytes; functions remain ordered and carry dense IDs, names,
source spans, and ordered operations.

Version-one operation tags are explicit repository-owned bytes in semantic enum
order: `AndI32=0`, `ByteInput=1`, `ByteOutput=2`, `MaterializeI32=3`,
`Return=4`, and `TruncateI32ToU8=5`. Source positions use fixed little-endian
`u32` byte/column/line fields. Materialized `i32` values encode exactly 21
one-byte trits in least-significant-first order; trits outside `0..2` or ternary
values outside the 32-bit domain fail restoration.

Serialization first independently validates program identity, portable source
identity, dense/unique function identity, contained source spans, SSA definition
and use ordering, value kind, and one final `i32` return. Restoration performs
the same validation and then requires byte-for-byte canonical re-encoding before
acceptance. Rust enum discriminants, host widths, debug formatting, target
layout
addresses, and auxiliary startup/wrapper planning models are not wire authority.

## Invariants

- Every IR operation lowers to explicit ternary/runtime operations with defined
  pre/postconditions and no direct host implementation of guest computation.
- Guest-runtime semantic identities supplied by `guest-runtime-and-allocator`
  lower to executable ternary/Malbolge-oriented operations without host callback
  substitution.
- The stage has deterministic input/output form, rejects malformed or
  unsupported input explicitly, and preserves source/profile provenance needed
  downstream.

## Failure Behavior

Malformed inbound projection identity, retained globals/proof obligations,
non-`i32` or malformed constants, invalid/undefined `i32` AND operands, invalid
or undefined truncation inputs, non-`u8` byte input, byte output before a byte
definition, duplicate projected SSA identities, byte-valued returns, unknown raw
runtime intrinsic names, runtime-intrinsic/profile drift, unknown pure runtime
helper identities, helper/profile drift, ambiguous helper EOF projections,
frame-helper ABI/runtime/identity drift, heap-helper ABI/runtime/identity
drift, colliding projected profile I/O opcodes, invalid startup identities,
null/misaligned/undersized/
overflowing heap extents, multi-block/phi/parameterized function shapes, and
unsupported instructions or terminators fail closed before a pre-layout target
program is returned. Later
layout/profile failures must likewise fail before accepted target code is
emitted.

## Verification

- `tests/ternary_lowering.rs` loads the tracked canonical typed-IR golden
  through
  complete typed-IR admission, projects it across the explicit inbound port, and
  proves deterministic `return 7` lowering, exact 21-trit scalar recovery, exact
  function/instruction/terminator source-span preservation, and module identity
  preservation.
- Scalar tests cover zero, one, positive signed maximum, the sign-bit pattern,
  and all-one bits; projection tests reject target-profile drift and truncated
  constant bytes; a richer admitted typed-IR golden is rejected as unsupported.
- A valid byte-input/output typed-IR fixture is completely admitted,
  canonicalized, restored exactly, projected across the inbound port, and
  lowered
  deterministically to ordered byte-input/output target effects plus the
  existing
  `i32` return path. Adversarial projection tests reject non-`u8` input,
  undefined
  output values, duplicate SSA IDs, and byte-valued returns.
- Public byte-stream wrapper-plan evidence cross-checks `c-libc-v1.json` and the
  checked-in guest `stdio.c` implementation, proving intrinsic/helper order for
  both `getchar` and `putchar`, exact wrapper return semantics, and fail-closed
  rejection of wrapper/profile/EOF drift without changing libc availability.
- Wrapper profile-realization evidence revalidates the canonical plan, binds
  `getchar`/`putchar` raw I/O to current-profile input/output machine opcodes,
  preserves helper/order/return semantics, and rejects forged order or colliding
  profile opcode projections before publishing a machine operation.
- Wrapper-control-flow evidence re-derives the machine plan and proves exact
  `getchar` initialization, machine-input, helper, status-guard, and
  success-return
  ordering plus exact `putchar` helper, machine-output, and widened-return
  ordering. Forged helper execution and target-profile drift fail closed before
  publishing wrapper control flow.
- Pure runtime-helper evidence cross-checks the guest-runtime JSON contract, C
  declarations, and byte-stream implementation. It binds only the exact decode
  and low-byte helper identities, copies EOF from `current_profile()`, records
  `0..255`, `-1`, status, and mask semantics without accepting concrete guest
  values, and rejects identity/profile drift or EOF overlap with the byte
  domain.
- Helper-execution evidence binds `VALID=0`, `INVALID_ARGUMENT=1`, and
  `INVALID_INPUT_WORD=4` to the runtime header, then proves the input decoder
  expands to the exact ordered null/byte/EOF/invalid exits with explicit result
  and status publications. Realized wrapper plans retain that helper execution
  alongside profile-bound machine I/O.
- Frame-helper evidence cross-checks the ABI JSON, runtime header, and
  checked-in
  `frame.c`. It binds exact validate/encode/decode identities, the fixed field
  offsets, header/alignment/status constants, ordered validator exits, and
  deferred publication. Encode validation precedes field encoding/output copy;
  decode validation follows scratch field reads and precedes caller-frame
  publication. ABI, runtime, or helper identity drift fails closed.
- Heap-helper evidence cross-checks `heap.c`, the runtime header, and JSON
  contract. Initialization binds exact alignment/minimum/status constants and
  proves guarded state publication plus capacity-wide zeroing. Allocation proves
  null-result publication before chain validation, zero-size success, checked
  required-span arithmetic, first-fit split-or-claim reuse, corrupt-chain
  rejection, capacity/overflow OOM, tail metadata/result publication, and final
  `used` publication.
- Zeroed-allocation evidence proves null-result publication, zero-size
  delegation, product overflow-to-OOM, canonical allocator delegation,
  post-allocation status/non-null gating, and exact payload zeroing before
  `VALID`. ABI/runtime/helper identity drift fails closed.
- Release evidence proves complete-chain preflight before mutation, null
success,
  exact allocated-payload lookup, canonical free-header publication, adjacent
  free-block coalescing, and free-tail `used` trimming. Source checks bind that
  order directly to `heap.c`; ABI/runtime/helper identity drift fails closed.
- Release evidence proves complete-chain preflight before mutation, null
success,
  exact allocated-payload lookup, canonical free-header publication, adjacent
  free-block coalescing, and free-tail `used` trimming. Source checks bind that
  order directly to `heap.c`; ABI/runtime/helper identity drift fails closed.
- Raw intrinsic identity evidence reads the guest-runtime JSON contract and
  declaration header, proves the exact input/output names remain synchronized,
  lowers only those names under `malbolge-2026` to distinct `InputWord` and
  `OutputByte` semantics, and rejects unknown names or profile drift.
- Target-profile realization evidence projects exact I/O instruction bytes and
  EOF state from `current_profile()` and proves the resulting machine I/O
  operations match that descriptor without compiler-local opcode literals. It
  rejects profile identity drift and colliding projected input/output opcodes.
- Target-cell encoding adapts the canonical VM `decode_profile_instruction`
  through an inbound decoder port. Tests exhaust all 94 decode phases for both
  profile-derived I/O operations and prove every emitted cell is graphical and
  decodes back exactly; missing or ambiguous decoder behavior fails closed.
- Low-byte helper-path evidence admits a valid typed-IR `i32` AND plus
  `i32`-to-`u8` truncation sequence, canonicalizes/restores it exactly, lowers
  it
  through the same SSA boundary, and feeds the `u8` result to `ByteOutput`.
  Adversarial projections reject wrong result types and undefined AND/truncation
  operands. This closes the operation vocabulary needed by the runtime output
  helper body, not direct helper-call recognition.
- Canonical ternary-codec evidence round-trips the constant-return, byte-I/O,
  and low-byte fixtures across `malbolge-ternary-ir-v1`, covering every current
  operation tag. It rejects every truncated prefix, wrong magic/version,
  trailing
  bytes, unknown operation tags, invalid trits, forged function identity, and
  invalid in-memory program/profile/SSA state before acceptance.
- Startup-plan evidence cross-checks the guest-runtime header and JSON contract,
  then proves a valid layout-resolved ABI pointer/capacity emits exactly one
  `BindHeap` before user entry. Tests reject ABI/profile/symbol drift, null or
  misaligned arena pointers, capacities below one header-plus-payload span,
  misaligned capacities, and logical-address overflow.
- Global heap placement, executable bind-call/source sequencing, typed-IR
  external-call binding, and wrapper branch-address/source-cell placement remain
  open target-lowering work.
- Expected durable artifact surface: `compiler/`, `src/`, `tests/compiler/`, and
  `tests/ternary_lowering.rs`.
- Required evidence: golden/round-trip or normalized stage fixtures,
  deterministic hashes where promised, and end-to-end lowering regression cases.
- Runtime realization evidence: consume guest-runtime semantic identities
  unchanged and prove their executable ternary/Malbolge lowering, including the
  one-time heap startup bind and declaration-only byte-I/O intrinsic symbols.
- Prerequisite completion evidence: `typed-compiler-ir`,
  `guest-runtime-and-allocator`, `malbolge-specific-optimization-mathematics`.
## References

- [Compiler Pipeline And Guest
  Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Deterministic C Surface And Clang
  Tooling](../adr/deterministic-c-surface-and-clang-tooling.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)

### Governing ADR Paths

- `docs/technical/adr/compiler-pipeline-and-guest-runtime.md`
- `docs/technical/adr/deterministic-c-surface-and-clang-tooling.md`
- `docs/technical/adr/verification-trust-boundary.md`
