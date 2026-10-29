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
