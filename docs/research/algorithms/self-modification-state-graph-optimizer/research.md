# Self-modification state-graph optimizer

## Status

Active

## Research Question

Does `self-modification-state-graph-optimizer` provide a reproducible verified
benefit over its declared baseline for the Malbolge compiler or execution
problem without weakening semantic correctness?

## Background

Model executable Malbolge regions as versioned state-transition graphs whose
nodes capture only semantically relevant code/data state. Derive mathematically
verified reductions that collapse equivalent mutation histories, eliminate
redundant encryption/update work, hoist invariant crazy/rotate computations, and
identify regions safe for direct native execution. Express the equivalence and
reduction rules in `.tex` and validate each admitted rewrite against executable
VM evidence.

- Status: Active
- Research ID: `self-modification-state-graph-optimizer`
- Last reviewed: 2026-07-26

## Prior Work

- `../../../bibliography/publications/superoptimization/egg.md`

## Hypothesis

- Baseline hypothesis: exact-state deduplication can reuse identical classic VM
  observations without changing graph edges or execution semantics even when the
  digest function collides adversarially.
- Reduction hypothesis (future): a smaller future-relevant key can merge more
  states than the exact baseline while preserving every admitted future
  observation on its declared domain.
- H0/rejection condition: any hash-only merge, any unequal exact snapshots
  merged
  by the baseline, or any reduced-key pair whose future observations diverge
  rejects the corresponding technique immediately.

## Method

The executable mirror lives at
`algorithms/self-modification-state-graph-optimizer/`. Experiments use versioned
configuration, explicit seeds where stochastic behavior exists, fixed resource
budgets, parametric challenge identities, and the same verifier used for
baselines. Raw regenerable output stays in the mirror's Git-ignored `out/`.

## Evidence

Candidate generation, heuristics, models, and accelerators are untrusted. A
research result can compare quality or cost only after the trusted semantic
verifier accepts the candidate under the declared target profile.

- The research identifies the minimal future-relevant state and observational
  equivalence relation, then proves/test-validates every graph merge or
  mutation-history collapse before using it for native execution.
- Definitions state domains and assumptions precisely; executable code cannot
  claim a mathematical reduction outside those stated preconditions.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.
- Every correctness-relevant equation or equivalence used by implementation has
  explicit domain assumptions and a traceable executable correspondence check.

## Results

The exact-state baseline is executable in
`src/research/algorithms/composition/state-graph/state_graph.rs`. A node is
confirmed by complete classic profile identity, registers, deterministic input
and cursor, committed output prefix, termination state, and all 59,049 memory
words. FNV-1a is used only to select a comparison bucket.

Three deterministic fixtures currently pass:

- replaying the same bounded execution reuses nodes and edges;
- forcing every snapshot to digest `0` still keeps distinct input states in
  separate nodes because complete snapshots are compared;
- only normative specification mode is admitted by this baseline.

<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
`src/specification/formal-model/math/algorithms/self-modification-state-graph-optimizer.tex`
formalizes the
exact projection and collision-safe merge rule. Both equations are registered in
`src/specification/formal-model/math/specification/correspondence.toml` and
mapped directly to the algorithm's
owned tests.

The first reduced-state key is now admitted for one structural fact:
`future_input_snapshot` removes only the contents of bytes strictly before the
committed input cursor while retaining that cursor and the exact remaining input
suffix. The `cbO` fixture (`<`, `<`, `v`) exhausts all 256 possible first input
bytes, applies one common second byte that overwrites `A`, and proves the
reduced
keys are equal both before and after the common future halt.

A second structural reduction is also admitted for already terminated states.
`terminal_future_snapshot` keeps profile identity, committed output prefix, and
termination reason while dropping memory, registers, and input state. Fixtures
vary valid halt-source memory, `A/D`, and input and still produce one future
key;
a live machine is rejected from this domain.

The exact baseline now also consumes the runtime-owned
`ProfileMachineState` checkpoint directly. `profile.rs` indexes the complete
validated checkpoint by profile fingerprint, I/O state, registers, and every
profile memory word; a current `malbolge-2026.2` replay deduplicates and a
forced
constant digest does not merge checkpoints with different input. This extends
the
correctness oracle to 4,782,969-word current states without duplicating
checkpoint
validation.

The exact current checkpoint cost is now measured independently at commit
`2c2365f`. Fifteen post-warmup samples per operation give medians of 7,194,700
ns
for full `snapshot_state()` cloning, 26,241,400 ns for digest/insertion of a
prepared checkpoint, and 30,756,600 ns for digest plus exact replay
confirmation.
Every operation retained one checksum across all samples. Raw samples, host,
toolchain, command, and profile geometry are versioned under
`benchmarks/research/state-graph/evidence/2026-07-27-windows-x86_64/`.

A profile-size-independent memory result now supplies the next reduction
boundary. For every instruction family, one normative step can change at most
two
memory cells: an optional data-cell write for crazy/rotate plus the committed
self-encryption target. Complete-memory classic and current fixtures observe
exactly two changes for crazy/rotate, one for ordinary committed instructions,
and zero for halt/atomic rejection. This proves `|Delta M| <= 2` without using
private transition-plan metadata.

The same fixtures now cross-check the incremental trace representation. Classic
`MemoryDelta` and profile `ProfileMemoryDelta` are produced by the real step
engine and contain only actual final changes. For all 18 instruction-family/
profile cases, the normalized trace tuples `(address,before,after)` equal the
complete-memory difference exactly; same-address data/encryption writes collapse
to one final change and halt/rejection remain empty. This makes the trace a
validated O(1)-sized input for persistent-memory research while the full scan
remains the independent oracle.

The first persistent-memory candidate is now executable in `memory.rs`. It
stores one shared complete root plus immutable exact trace patches. Applying a
patch validates every `before` word against the current persistent view; empty
deltas reuse the current node. In the current-profile fixture, every traced step
is applied to the persistent chain and `materialize()` is compared to the full
runtime checkpoint after that same step. All complete memories match. A forged
`before` value is rejected before insertion.

These results do not justify removing the live input cursor, changing the
remaining suffix, removing live output history, or dropping arbitrary live
memory/register state without proof. They do establish shared-root plus bounded
patches as a correctness-preserving alternative to repeated full-checkpoint
memory copies. The exact current checkpoint remains the reconstruction oracle;
performance of patch application/read/compaction must be measured separately
before production promotion.

## Threats to Validity

Initial threats include challenge-family bias, hardware/toolchain sensitivity,
search-seed variance, verifier bounds, and overfitting to small Malbolge blocks.
Each experiment must narrow these threats before drawing a conclusion.

## Conclusion

Accept exact-state deduplication as the conservative graph baseline and admit
the exact baseline for both classic and validated current-profile checkpoints,
plus two structural reductions: consumed input-prefix contents are
future-irrelevant when cursor/suffix stay exact, and already-terminated states
may drop dead memory/register/input state while retaining
profile/output/termination. Do not yet promote live memory/register/output
reductions or a native-execution shortcut. Each further reduction must
independently defeat the exact baseline.

## References

- [Verification Trust
  Boundary](../../../technical/adr/verification-trust-boundary.md)
- [Research Evidence And Algorithm
  Mirror](../../adr/research-evidence-and-algorithm-mirror.md)

A post-commit read-depth matrix at `51fb0b6` now isolates the linked-chain risk.
Latest-patch reads remain approximately 18 ns/op from depth 1 through 4096, but
an address absent from every patch rises from 18.27 ns/op at depth 1
to 20751.17 ns/op at depth 4096. A fit over depths 64/512/4096 is about
5.20 ns per traversed patch. Raw 15-sample evidence and operation counts
are versioned under
`benchmarks/research/state-graph/evidence/2026-07-27-depth-windows-x86_64/`.

Periodic full compaction alone is not promoted. Using the measured
11.47 ms snapshot cost as a lower bound and one average
root-miss per step, the simple `S/N + alpha*N/2` model has its optimum near
2099 patches and still costs about
10.93 microseconds per step before VM
work. The model is explicitly illustrative, not a throughput claim. The next
candidate therefore requires persistent sharing **and** read cost bounded
independently of patch-history depth.

The next correctness candidate is now implemented in `index.rs`: a persistent
64-way radix overlay with four six-bit address chunks above the same shared full
root. The 24-bit capacity contains the current 14-trit address domain and is
explicitly rejected rather than widened implicitly. Reads are structurally
bounded to at most four radix levels independent of patch-history length.

Correctness evidence remains checkpoint-based rather than performance-based.
Real current trace deltas reconstruct every complete runtime checkpoint exactly;
a separate fixture accumulates 4096 distinct overrides and still returns the
latest override and an untouched root cell correctly. A forged `before` value
fails before path copying. Performance is deliberately unclaimed until a
post-commit benchmark compares indexed apply/root/latest reads to the linked
baseline.

Post-commit measurement at `ec459d0` promotes the bounded radix from correctness
candidate to the current-profile state-graph memory candidate. With 4096
distinct
overrides, latest reads remain 24.61 ns/op,
root fallbacks remain 20.70 ns/op, and applying
a new override is 1159.62 ns/op. The corresponding
linked root miss is 24118.75 ns/op, about
1165.0 times the radix latency. A real
two-cell radix apply measures 1665.06 ns/op versus a
6.79 ms full snapshot clone.

This is still a representation microbenchmark, not end-to-end VM throughput.
The next correctness/performance boundary is exact state identity. Current
`ProfileStateGraph` hashes and compares complete checkpoints; the radix
candidate
must gain deterministic incremental identity and collision-confirming equality
without re-materializing all 4,782,969 words per observation.

The next identity candidate is now executable in `state.rs`. One incremental
graph
is explicitly bound to a single immutable profile/input/memory-root lineage.
Changing state consists only of input cursor, committed output, registers,
termination, and canonical radix overlay. Input/profile/root identity therefore
uses shared allocations instead of repeated complete comparisons; independently
constructed roots fail closed as foreign lineage.

State evolution consumes only public `ProfileStepTrace` records. Input/output
observations are checked against the current incremental state, memory uses the
exact trace delta, and every resulting state materializes back to the complete
runtime checkpoint exactly. Bucket identity combines incremental component
digests in constant-size work. Exact state equality remains the merge authority:
a forced constant digest does not merge distinct states, while exact replay
returns the same node ID. Performance remains unclaimed until this graph is
benchmarked directly against `ProfileStateGraph` full-checkpoint insert/replay.

Post-commit state-identity measurement at `f317f3e` removes complete checkpoint
hash/equality from the expected graph fast path. Incremental trace application
is
923.78 ns/op, new-state observation is
535.82 ns/op, and exact replay is
406.67 ns/op. The complete-checkpoint baselines in
the same run are 26.29 ms insert and
30.48 ms replay, giving measured representation
ratios of approximately 49070x and
74958x.

This does not establish VM or native-tier throughput. It does promote
lineage-bound incremental identity as the current graph candidate. The remaining
obvious history-sized update is committed output: `state.rs` still clones the
entire output `Vec<u8>` whenever one byte is emitted. Output persistence is the
next falsifiable representation slice before native-region work.

The remaining history-sized state update now has a correctness candidate in
`output.rs`. The initial committed output prefix is shared once; each later byte
creates one immutable parent-linked tail node. Exact output equality keeps bytes
as authority after digest/length filters, while shared tails make ordinary
replay
constant-time. Independent branches producing the same three-byte suffix compare
exactly, different suffixes remain distinct, and a 65,536-byte history
materializes correctly.

The long-history fixture initially exposed recursive `Arc` destruction as a host
stack overflow. The implementation now iteratively unwraps uniquely owned tail
nodes until a shared prefix is reached, and the same 65,536-byte test passes.
Performance is not yet claimed: a post-commit benchmark must compare persistent
append against the previous complete-`Vec` clone as output length grows.

Post-commit persistent-output evidence at `1d229d0` removes the last obvious
history-length copy from the ordinary incremental-state update. Persistent
append
measures 107.70 ns at empty history, 139.82 ns at 1 KiB, 138.87 ns at 64 KiB,
and
144.53 ns at 256 KiB. The previous complete-vector clone/push measures 84.45 ns,
230.60 ns, 3.12 microseconds, and 20.83 microseconds respectively. The candidate
therefore accepts a small fixed empty-history overhead in exchange for
effectively
flat append cost; the 256 KiB ratio is about 144x.

This remains a representation microbenchmark. Materialization and rare exact
comparison of non-shared equal branches can still scale with output length, but
they are not the per-step fast path. Memory, state identity, and
committed-output
storage now all have bounded/incremental ordinary update paths. The next
research
question is semantic: identify native-executable regions with explicit
self-modification guards and deterministic deoptimization conditions.

The first native-shortcut safety class is now executable without introducing
code generation. `region.rs` treats every `ExactRegionCertificate` as untrusted.
Recording runs the normative `ProfileMachine` from an exact incremental entry
and
captures the bounded outcome plus complete trace sequence; verification performs
that normative execution again and requires exact outcome, trace, and
incremental
exit-state equality before returning `VerifiedExactRegion`.

Runtime reuse is deliberately conservative: `accepts_entry()` requires exact
incremental-state equality, never digest equality. A state advanced by even the
first real trace fails the guard. An otherwise valid certificate with a tampered
outcome fails reverification, and an invalid self-encryption transition returns
a
VM error before any verified region exists. This establishes a safe exact-state
specialization/deoptimization baseline for future AOT/JIT code. It does **not**
yet establish a reduced stable-region guard: that requires explicit future read
and dependency evidence so irrelevant state can be omitted from the guard.

Post-commit region timing at `f16785d` confirms the desired verifier/hot-guard
asymmetry. Exact entry-state guard hits measure 55.51 ns/op and
misses 59.09 ns/op, while normative certificate verification
measures 9.09 ms. The verifier is roughly
163799 times the guard-hit latency because it
materializes and re-executes normative state deliberately.

This result changes the motivation for guard reduction. Exact guards are already
cheap enough to remain the correctness baseline; dependency/read-set guards are
valuable because they may admit the same verified region from states that differ
only in memory the region cannot observe. The next slice therefore records
semantic memory reads from the real profile transition engine before attempting
a
broader guard.

The normative VM now exposes the dependency evidence needed for reduced region
guards. Each `ProfileStepTrace` carries `memory_reads` populated by the real
transition engine, not by opcode inference in research code. The fixed roles are
code fetch, optional data-pointer read, and optional encryption-target read, so
a
requested current-profile step performs at most three semantic memory reads.
Every instruction family plus rejected jump encryption has an exact
role/address/
value fixture. Rejected transitions retain reads performed before the error
while
committing no memory delta.

This enables a standard read-before-write live-in calculation for a verified
region: an entry-memory value belongs in the guard only when the region reads
that
address before any verified region write dominates it. The next slice derives
and
validates that guard against direct VM execution.

The first reduced native-region guard is now executable. Verification derives a
memory live-in set directly from the already verified trace: semantic reads are
processed before each step's committed writes, and an address constrains entry
memory only when no earlier region write dominates that read. Repeated live-in
reads must agree exactly. No opcode decoder or heuristic dependency model exists
in the research layer.

Runtime admission still requires exact non-memory state and the same immutable
profile/input/root lineage, then checks only the derived live-in memory values.
The shortcut applies verified after-values to the candidate's indexed memory
without requiring the certificate's original `before` at write-only locations;
this preserves candidate differences outside the verified write set. The
end-to-end fixture changes such an irrelevant cell: exact entry equality rejects
the state, the dependency guard accepts it, and shortcut/direct normative runs
produce identical complete exit checkpoints while preserving the irrelevant
value. Changing the first live-in dependency fails the guard and returns
`DependencyGuardMismatch`.

This is the first demonstrated semantic state-collapse useful to native reuse,
not merely a storage optimization. Post-commit evidence at `1988f14` measures an
exact guard hit at 60.57 ns, a dependency guard hit at 106.88 ns, and a
dependency guard miss at 72.22 ns. The reduced guard is deliberately a
little more expensive than exact equality because it reads the verified live-in
set, but that cost buys reuse across future-irrelevant memory differences.

Applying the already verified dependency shortcut measures 6.88
microseconds versus 889.60 microseconds for a prepared normative VM
run of the same bounded region, about 129.36x on this host. Certificate
verification remains deliberately expensive at 8.78 ms and is
not a hot-path operation. These are region microbenchmarks, not an end-to-end
native-tier claim. Dependency guards and verified effects are promoted as the
correctness/performance baseline; the next research risk is replacing the
interpreted verified-effect application with a real native code artifact while
retaining the same verifier and deoptimization boundary.


The deoptimization boundary is now executable as well. `execute_or_deopt()` does
not treat a dependency-guard miss as an error: it reconstructs the candidate
checkpoint, runs the normative profile VM for the verified region budget,
records
real traces, and reapplies those traces to the original incremental lineage. An
irrelevant-memory variant takes the verified shortcut; a valid advanced state
misses the guard and produces exactly the direct normative exit; and a changed
live-in that makes execution invalid propagates the same typed VM rejection.
This freezes tier selection before native code exists: a future backend may
replace only the verified-shortcut implementation, never the deoptimization
semantics.

A first portable artifact boundary now freezes what that future backend is
allowed to consume. Product-owned `execution/ir::EffectOp` projects each
verified trace to only the state-changing subset: exact before/after
observations, deterministic input/output effects, and final memory delta.
`UntrustedRegionArtifact` additionally carries
IR version, canonical profile fingerprint, verifier-derived live-ins, region
budget, and outcome. `verify_against()` independently reprojects the verified
region and requires exact equality of every field before producing
`VerifiedRegionArtifact`.

The verified artifact executes compact effects directly on guard hit while still
checking before-state and deterministic I/O progression. On guard miss it uses
the already proved normative deoptimization path. Fixtures tamper effect count,
profile fingerprint, format version, dependency set, budget, and outcome and
require verifier rejection; admitted shortcut/deopt results equal the existing
verified-region baselines. This is a portable effect-IR research precursor, not
yet x86-64/AArch64 bytes or a stable serialized native cache format.
`src/runtime/tiered-execution/domain/ir/main.rs` now owns that portable schema
as product code; research
consumes it rather than defining a second effect type. The next boundary is an
independently validated host-code artifact.
