# Compact guest bytecode strategy

## Status

Proposed

## Research Question

Does `compact-guest-bytecode-strategy` provide a reproducible verified benefit
over its declared baseline for the Malbolge compiler or execution problem
without weakening semantic correctness?

## Background

Evaluate a VM-inside-Malbolge strategy where large programs are represented as
compact bytecode interpreted by a reusable Malbolge runtime when that reduces
code-size explosion or compilation cost.

- Status: Proposed
- Research ID: `compact-guest-bytecode-strategy`
- Last reviewed: 2026-07-26

## Prior Work

- `../../../bibliography/platforms-and-runtimes/compiler/llvm-ir.md`

## Hypothesis

- H1: the proposed technique improves at least one preregistered objective under
  an equivalent resource budget while all accepted outputs pass the independent
  verifier.
- H0/rejection condition: the technique is unsound, cannot reproduce its result,
  or provides no meaningful advantage over the declared baseline on the admitted
  challenge distribution.

## Method

The executable mirror lives at `algorithms/compact-guest-bytecode-strategy/`.
Experiments use versioned configuration, explicit seeds where stochastic
behavior exists, fixed resource budgets, parametric challenge identities, and
the same verifier used for baselines. Raw regenerable output stays in the
mirror's Git-ignored `out/`.

## Evidence

Candidate generation, heuristics, models, and accelerators are untrusted. A
research result can compare quality or cost only after the trusted semantic
verifier accepts the candidate under the declared target profile.

- The research compares direct lowering with a reusable guest bytecode/runtime
  design on code size, compile time, runtime cost, memory pressure, and verifier
  complexity before adoption.
- The stage has deterministic input/output form, rejects malformed or
  unsupported input explicitly, and preserves source/profile provenance needed
  downstream.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.

## Results: Bounded Structural Pilot v0 (2026-10-29)

A first reproducible **non-executable** candidate now exists at
`../../../../algorithms/compact-guest-bytecode-strategy/`. The versioned
`pilot-v0.toml` and Rust model use the canonical current profile and
`malbolge-ternary-ir-v1`, admitting only one void function of `n` adjacent
successful byte-input/byte-output pairs with the same SSA identity. The
candidate is a six-byte `CEB1` descriptor consisting of a four-byte prefix
and a little-endian `u16` pair count;
no resident Malbolge interpreter can execute it yet.

The test independently checks the original canonical ternary program, expands
the descriptor to **direct** Malbolge code on the host and compares every
source byte and execution witness against the product byte-echo backend.
The actual normative VM executes one expanded 256-pair source for every
possible successful byte, including `0` and `255`, with the exact output
and input-consumption trace. Another 4095-cell direct source executes all
2047 admitted pairs in order, including high-bit and zero byte patterns.
Other cases cover code-size extremes and adversarial malformed candidates.
The original source identity is not embedded in the six-byte descriptor:
another equally long, separately validated program is accepted, proving
that standalone authentication remains missing.

A second, process-level baseline uses the real `malbolge_layout` publisher with
`--ternary-file` for `n = 1, 7, 64, 256`. Each validated MCTR checkpoint is
published to a fresh `.malbolge` file; its bytes match the independently
expanded candidate's position-sensitive direct source exactly. This exercises
the actual artifact path and confirms the direct source-size baseline rather
than relying only on an in-memory encoder. The **candidate** is still expanded
on the host and is not published or executed as guest bytecode.

Under the deliberately optimistic assumptions that one candidate byte occupies
one Malbolge memory cell and all missing runtime/packaging cells can be counted
in the same units, the **necessary** strict-size-win inequality is
`R + 6 < 2n + 1`, where `R` is the **unimplemented** guest interpreter plus
loader, dispatch, source-authentication, relocation, and packaging footprint.
No value of `R` has been measured or independently admitted. The table shows
the largest hypothetical nonnegative `R` that *could* fit; it does not show an
executed bytecode artifact or a realized improvement.

| Echo pairs | Direct cells | Descriptor | Max R (0 extra) | Max R (+32) |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 3 | 6 | None | None |
| 2 | 5 | 6 | None | None |
| 3 | 7 | 6 | 0 | None |
| 7 | 15 | 6 | 8 | None |
| 20 | 41 | 6 | 34 | 2 |
| 64 | 129 | 6 | 122 | 90 |
| 256 | 513 | 6 | 506 | 474 |
| 2047 | 4095 | 6 | 4088 | 4056 |

The right-hand sensitivity column additionally reserves 32 hypothetical
Malbolge memory cells for source-binding metadata, requiring
`R + 6 + 32 < 2n + 1`. No such source binding is implemented; the 32-cell
figure is not evidence of a cryptographic digest or a complete envelope.

The first two cases are **negative even with a free guest interpreter** under
this idealized model. With the 32-cell binding sensitivity, the first four
cases are already negative. Every other case remains unresolved until one real
Malbolge guest interpreter decodes the candidate and its total code/data
footprint is independently verified. The `n=3` case has no interpreter budget
at all. The direct baseline is only the supported successful-I/O subset, not
ordinary C code or a representative compilation workload.

Run the exact versioned pilot:

```sh
cargo test --locked --test compact_guest_bytecode_strategy --quiet
cargo clippy --locked --test compact_guest_bytecode_strategy -- -D warnings
```

No wall-time speedups, guest runtime costs, memory-pressure results, search
measurements, verifier-work estimates, or Pareto comparisons are reported.
Synthetic byte projections are not evidence of broad compiler workloads.

The falsifying observation for H1 is a verified resident runtime whose
**total** code/data cells never outperform direct lowering across the
preregistered cases, or whose guest-observable behavior differs at any admitted
input. A failed decoder, missing source/profile identity or unverifiable code
also rejects adoption regardless of an optimistic payload saving.

## Results: Exact Canonical-Source Binding Sensitivity v1 (2026-10-29)

The separate `pilot-v1.toml` preserves the v0 six-byte `CEB1` baseline and
introduces 38-byte `CEB2` (magic + little-endian pair count + SHA-256 digest).
A domain-separated digest now binds the selected profile *fingerprint* and
exact canonical ternary source, including source identity, ABI, function names,
spans and effect sequence. This rejects same-count valid foreign-source swaps
that v0 admits; it is not an authenticated signature and requires a separately
trusted canonical input. Every single-byte candidate mutation is refused,
including version downgrade, count, digest, and malformed length. Known-answer
SHA-256 cases, the eight direct-layout comparisons, and valid equal-count
source substitutions supply separate checks; direct guest execution remains
the v0 verified source baseline, not bytecode execution.

The v1 **necessary but insufficient** strict-win model is now
`R + 38 < 2n + 1`, where `R` includes still-absent guest decoder, loader,
interpreter, and packaging. An optimistic byte-to-cell conversion remains
assumed, and the 32 digest bytes do not imply a 32-cell executable source
binding. The table compares the actual host descriptor bytes with the unchanged
direct Malbolge source-cell counts; it is a sensitivity bound, not a physical
packing or performance result.

| Echo pairs | Direct cells | Bound CEB2 bytes | Max R optimistic |
| ---: | ---: | ---: | ---: |
| 1 | 3 | 38 | None |
| 2 | 5 | 38 | None |
| 3 | 7 | 38 | None |
| 7 | 15 | 38 | None |
| 20 | 41 | 38 | 2 |
| 64 | 129 | 38 | 90 |
| 256 | 513 | 38 | 474 |
| 2047 | 4095 | 38 | 4056 |

The v1 bound exactly matches v0's previously **hypothetical** 32-cell binding
cost, but gives that overhead an explicit host-byte format and falsifiable
byte-binding test. No Malbolge-resident SHA-256, compact-bytecode interpreter,
or authentic source anchor is available; verified runtime benefits remain
unknown. CEB2 remains a non-executable proposal.

A fixed seven-pair wire framing vector was independently recalculated with
Python's standard-library SHA-256 (587 canonical MCTR bytes and selected
profile fingerprint); the Rust regression pins its exact digest, preventing a
matching encoder/decoder bug from silently changing this research format.
Across four bounded sizes, the actual external `malbolge_layout` publisher
also emits the same direct source as both candidate expanders. The comparison
is byte-for-byte but still offers **no** resident guest-bytecode execution.

## Results: Actual Graphical Loader Residency v2 (2026-10-29)

Version-two research now tests the missing Malbolge memory-cell packing
assumption, separately from any interpreter claim. A real position-sensitive
loader admits exactly eight graphical glyph choices per loaded position (the
eight canonical opcode letters). The research image encodes the existing
38-byte CEB2 descriptor in groups of three bits by choosing one of those
eight characters at each address.

That requires `ceil(304/3) = 102` source
cells with two canonical zero pad bits. The fixed three-cell direct byte-echo
prefix halts before the tail, producing a 105-cell loadable source image.
This is a literal graphical source packing observation, not a general
compression lower bound for structured CEB2 data or the complete word memory.

The normative current-profile VM loads the image, executes only the direct
single-byte echo and leaves all proposed payload cells unchanged. Host-side
independent reconstruction checks exact glyph position and CEB2 digest;
loader-admissible candidate-byte mutations and malformed/extra source fail
closed. The guest does **not** use the payload: even the 7-pair case runs only
one byte before halting, and no claim of equivalent n-pair execution follows.

| Echo pairs | Direct cells | Literal CEB2 cells | Max hypothetical R |
| ---: | ---: | ---: | ---: |
| 1 | 3 | 102 | None |
| 2 | 5 | 102 | None |
| 3 | 7 | 102 | None |
| 7 | 15 | 102 | None |
| 20 | 41 | 102 | None |
| 64 | 129 | 102 | 26 |
| 256 | 513 | 102 | 410 |
| 2047 | 4095 | 102 | 3992 |

For this literal encoding only, strict size advantage now *necessarily*
requires `R + 102 < 2n + 1`, with `R` covering all runtime code, decoder,
loader/dispatch linkage, provenance verification and additional data. The
three-cell demonstration prefix is included in `R`, but is not a runtime
that interprets the resident bytes. Actual total footprint, throughput and
semantic equivalence of a VM-resident decoder remain unknown. The v0/v1
38-byte hypothetical one-to-one packing understates this concrete test's
source-cell cost by 64 cells; other bit encodings and data initialization
techniques have not been excluded.

## Results: Genuine Guest CEB2 Memory Read v3 (2026-10-29)

The v3 source removes the earlier restriction that the Malbolge guest never
reads resident data. Its first `j` loads source glyph `40`, then actual
`D := M[0]` and pointer advancement move D to address 41, the start of a
102-cell CEB2 tail. Twelve real `o` steps advance D to address 53, payload
ordinal 12 encoding three low count-field bits (descriptor bits 36–38).

At code position 13, the guest executes `*`: it reads that cell's ASCII word,
rotates it under profile trit semantics and writes the changed value to both
M[53] and A. `<` at position 14 outputs the low byte, and `v` halts at 15.
No-op padding fills positions 16–40; CEB2 glyphs occupy positions 41–142.
The complete source is **143 loader-valid cells** (41 prefix/padding, 102
payload), with exactly **16 reached guest steps** for every encoded count.

The normative VM tests five source-bound CEB2 counts (1/7/20/64/256), with
independent scalar output oracle, original vs rotated memory word, all other
payload cells unmodified, and varying results across distinct counts. An
independent sixteen-step execution trace proves real data read at 53, guest
write to 53, post-instruction encryption and final output/termination. A
loader-valid count-glyph substitution makes the same VM emit a different byte
but is rejected by host CEB2 admission. This is now *guest data computation*,
not only a host-expanded source or loader-only data-residency claim.

A separate process-level comparison publishes two independently host-admitted
seven- and 64-pair probe sources as version-one `.malbolge` capsules through
the canonical `build_capsule` library. The **real general Malbolge runner**
executes those artifacts with `--report-steps` and produces distinct exact
stdout bytes matching the scalar glyph-rotation oracle. Both stderr receipts
report exactly 16 committed guest steps. This tests actual artifact framing,
profile dispatch and process output; the host still constructs the source
and the guest still computes only the diagnostic single-cell rotation.

**It is not bytecode interpretation or semantic equivalence.** The guest
rotates one ASCII glyph; it neither calculates the packed ordinal, decodes
the full count, authenticates the source, loops, consumes input nor emits the
n requested echo outputs. The 16 guest steps do not implement an n-pair
program. At 64 pairs the 143-cell probe exceeds the 129-cell direct program
despite doing less work. Neither that comparison nor the earlier hypothetical
`R + 102 < 2n + 1` (for an unimplemented *equivalent* interpreter) proves an
actual source-size or throughput benefit. The probe does not measure the
runtime footprint `R` required to execute arbitrary stored bytecode.

A complete guest decoder and looping echo interpreter with independent
end-to-end semantic verification are still required for P2 adoption.

## Results: Guest Indirect Dispatch into CEB2 Data v4 (2026-10-29)

A fourth test changes the reached guest operation at code position 13 from
`*` (v3's data rotation) to `i` (native indirect code jump), retaining the
same source-bound, host-verified 38-byte CEB2 descriptor mapped into 102
loader-valid glyphs at positions 41–142. The actual VM first executes `j`
(source glyph 40 at address zero), then twelve no-ops to position D at 53.
The reached `i` reads the stored count glyph `M[53]`, assigns it to C and
performs canonical XLAT2 encryption on `M[C]` before incrementing C. The
next fetched and executed code is at `initial M[53] + 1`, inside the
resident CEB2 data tail. Crucially, the guest program chooses this target
from the descriptor's physical value; the host does not pass it a branch.

An eight-way test exhausts the three-bit rank encoded at descriptor bits
36–38 (little-endian count bits 3, 2, 1). Nonzero echo pair counts
32/2/4/6/8/10/12/14 produce independently calculated guest target code
addresses 46/47/65/81/82/104/110/123. Normative VM traces demonstrate
the exact code/data register state, physical read, post-jump source-cell
encryption, and first instruction fetch and decode at those variable target
positions. The CEB2 host verifier still rejects a loader-admissible changed
count glyph, while the actual guest jump demonstrably follows the tampered
value. This provides an observed control-flow effect that v3's rotation
probe alone did not provide.

The experiment does not implement any bytecode VM. The target *Malbolge
code* is taken verbatim from descriptor glyph positions and decoded with
XLAT1, rather than interpreting an application bytecode operation. No loop,
count termination, source authentication or input byte-echo equivalence
exists. The fixed 143-cell source is an exploratory counterexample to the
notion that placing a descriptor alone provides an equivalent compact
execution strategy. No size, compilation-time, or guest-step advantage may
be inferred from this non-equivalent diagnostic.

A directly reproduced negative case strengthens the code/data warning: the
`i` transition XLAT2-encrypts `M[initial M[53]]` **inside the original CEB2
payload** before the following instruction fetch. The committed word differs
from the exact source glyph and the resulting memory-backed image is no
longer admissible as the original bound CEB2 source. This is an actual
resident-code/data mutation cost, not hypothetical VM design overhead. A
future interpreter must protect or verify its bytecode despite classic
instruction encryption; using a naive descriptor-region indirect jump as a
bytecode dispatch loop would destroy the stream it is supposed to read.

## Threats to Validity

The pilot has no guest interpreter, no real bytecode loader, no linked data
layout, no source-authenticating envelope, and no measured decoder cost.
Comparing binary descriptor bytes to graphical instruction cells is optimistic
and may be physically impossible at the assumed one-cell-per-byte density.
The host expands a macro into direct Malbolge instructions, rather than
executing bytecode inside Malbolge. Successful byte I/O does not cover EOF,
status errors, arbitrary arithmetic, control flow, or whole-program C ABI.
The tested current-profile word width and deterministic synthetic trace family
cannot be generalized to classic or later profiles. Compiler time, guest
runtime time, resident memory, proof complexity, workload bias and
code-size-versus-throughput tradeoffs remain entirely unmeasured.

Further experiments must admit a real resident guest runtime and independently
compare it with the direct baseline on identical source, profile, inputs and
resource budgets, reporting negative results and any bound limitations.

## Conclusion

This pilot establishes a closed six-byte repeat-echo research encoding and a
quantitative *conditional* break-even budget, **not** bytecode feasibility.
Without verified guest execution and the missing cost dimensions, H1 remains
unresolved and there is no basis to adopt guest bytecode in the compiler.

## References

- [Compiler Pipeline And Guest
  Runtime](../../../technical/adr/compiler-pipeline-and-guest-runtime.md)
- [Deterministic C Surface And Clang
  Tooling](../../../technical/adr/deterministic-c-surface-and-clang-tooling.md)
- [Verification Trust
  Boundary](../../../technical/adr/verification-trust-boundary.md)
