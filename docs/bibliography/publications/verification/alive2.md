# Alive2 Translation Validation

## Status

Verified; evidence verified.

## Subject

- Canonical name: Alive2: Bounded Translation Validation for LLVM
- Subject class: Compiler verification research paper and tool
- Stable identifier: DOI 10.1145/3453483.3454030
- Publisher or authority: Nuno P. Lopes, Juneyoung Lee, Chung-Kil Hur, Zhengyang
  Liu, and John Regehr

## Repository Use

Alive2 is direct prior work for the repository's policy that an optimizer should
not be trusted to certify its own rewrites and that translation validation can
check optimized output against source semantics.

## Provenance

The author's publication page and official project repository are primary
sources. The paper appeared at PLDI 2021.

## Identity And Version

- Canonical name: Alive2: Bounded Translation Validation for LLVM
- Subject class: Compiler verification research paper and tool
- Stable identifier: DOI 10.1145/3453483.3454030
- Publisher or authority: Nuno P. Lopes, Juneyoung Lee, Chung-Kil Hur, Zhengyang
  Liu, and John Regehr

## License Or Terms

This is external material. Citation does not relicense the source or import its
terms into the repository MIT license.

## Evidence

### Verified

- Alive2 performs bounded translation validation for LLVM IR.
- The tool uses symbolic execution/refinement checking and SMT infrastructure.
- Bounded resource use can cause some bugs to be missed; the method is not an
  unbounded universal proof of all LLVM transformations.
- The project provides translation-validation integrations and standalone tools.

### Unresolved

Malbolge translation validation needs a target-specific semantic model. Alive2
is methodological prior work, not a drop-in verifier for this repository.

## Sources

- <https://web.ist.utl.pt/nuno.lopes/pubs.php?id=alive2-pldi21> - accessed
  2026-07-26.
- <https://github.com/AliveToolkit/alive2> - accessed 2026-07-26.
