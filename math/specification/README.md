# Specification Mathematics

This directory contains normative mathematical models for language and compiler
semantics. `malbolge-1998.tex` owns the classic specialization;
`profile-model.tex` owns profile-width mathematics shared by versioned target
profiles. Both import `../malbolge-notation.tex`.

Human-facing explanations remain under `docs/technical/specification/`; this
directory owns the mathematical artifact rather than explanatory prose.

`correspondence.toml` maps every labelled `eq:` definition to its admitted domain
and executable Rust evidence. Validate that traceability with
`python scripts/validate/math_correspondence.py`; run the referenced Cargo tests
to execute the semantic evidence itself.
