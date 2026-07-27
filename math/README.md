# Mathematical Authority

`math/` contains machine-governed mathematical specifications used by Malbolge
semantics, compiler research, optimization, and verification.

A `.tex` artifact states a mathematical contract. It is not automatically a
proof that an implementation satisfies that contract. Executable correspondence,
finite-domain checks, proof tooling, and verifier evidence remain separate
obligations.

- `specification/` owns normative machine and compiler mathematics.
- `algorithms/` owns opt-in mathematical contracts for research algorithms.

Shared notation lives in `malbolge-notation.tex`. Every standalone mathematical
document imports it. Validate source layout and compile every document with:

`python scripts/validate/math_specifications.py`

Generated LaTeX artifacts belong only under `.cache/latex/`.

`specification/correspondence.toml` maps promoted `eq:*` labels to executable
evidence. Validate that graph with
`python scripts/validate/math_correspondence.py`. A manifest link
records traceability and declared domain; it does not strengthen the underlying
test's proof coverage.
