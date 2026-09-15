# Classic-budget guest C stress fixtures

These fixtures are intentionally small, deterministic freestanding C programs
that exercise compiler behavior rather than output volume. They are designed to
remain plausible candidates for eventual `malbolge-1998` lowering, whose classic
machine has 59,049 words, without claiming a generated-size result before the
C-to-Malbolge backend exists.

Every fixture has no headers, hosted libc calls, heap allocation, threads,
environment state, files, or host callbacks. The only external declaration is
`__malbolge_output_byte`, a fundamental compiler intrinsic that must lower to
Malbolge output in a generated artifact. The native CLI adapter is debug-only
scaffolding and is never part of guest semantics.

Each program emits exactly `OK\n` only after reaching a fixed independently
calculated oracle. Failure emits no bytes.

For native debug execution before Malbolge lowering exists, run any fixture as:

```text
malbolge src/examples/programs/contract/self_host/stress/arithmetic_stress.c
```

The expected output is exactly `OK\n`.

- `arithmetic_stress.c` performs 729 rounds of bounded integer dependencies,
  including multiply, divide, modulo, shifts, masks, xor, or, and addition.
- `control_flow_stress.c` performs 1,458 iterations through a compact seven-way
  state-dependent control-flow graph with repeated convergence and backedges.
- `memory_permutation_stress.c` permutes an 81-element array through computed
  indices, checks a forward digest, reverses every swap, and verifies exact
  restoration.
- `call_chain_stress.c` repeatedly traverses eight distinct direct functions,
  exercising argument passing, return values, temporaries, and call sequencing
  without recursion.
- `state_machine_stress.c` executes 729 transitions over six coupled fields and
  five phases, then checks the complete final state.

The fixtures deliberately avoid large text, large static tables, generated
branch forests, recursion, and artificial memory pressure. Runtime work is high
relative to their static source and data footprint.

No checked-in `.malbolge` artifact is claimed yet. Eventual classic-target
evidence must record generated loaded cells and guest storage and prove the
artifact fits and executes under interpreter-authority `malbolge-1998`.
