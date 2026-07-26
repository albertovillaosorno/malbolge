# Algorithm Research Records

Each child directory is one research question or algorithm and mirrors the same
stable identifier under `algorithms/` when executable experimentation is needed.

A mature record contains only the artifacts it actually needs from this shape:

```text
docs/research/algorithms/<id>/
|-- README.md       question, hypotheses, method, results, threats to validity
|-- theory.tex      definitions, derivations, proofs, equivalence arguments
`-- figures/        authored or reproducibly generated publication figures
```

Citations resolve against the canonical bibliography under
`docs/bibliography/`; do not fork citation metadata into dozens of
algorithm-local BibTeX databases unless a publication format requires a generated
subset.

`README.md` should identify the correctness oracle, workloads and provenance,
independent and dependent variables, baselines, hardware controls, randomization
and seeds, stopping rules, benchmark methodology, negative results, and the
criteria required before the algorithm may influence production code.

A `.tex` file is required only when there is actual mathematics to state. Do not
manufacture decorative equations to satisfy structure.
