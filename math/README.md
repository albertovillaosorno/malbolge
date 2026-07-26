# Mathematical Authority

`math/` contains machine-governed mathematical specifications used by Malbolge
semantics, compiler research, optimization, and verification.

A `.tex` artifact states a mathematical contract. It is not automatically a
proof that an implementation satisfies that contract. Executable correspondence,
finite-domain checks, proof tooling, and verifier evidence remain separate
obligations.

- `specification/` owns normative machine and compiler mathematics.
- `algorithms/` owns opt-in mathematical contracts for research algorithms.
