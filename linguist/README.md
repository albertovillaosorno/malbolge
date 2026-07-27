# GitHub Linguist support for Malbolge

> **Status: WIP - do not submit yet.**
>
> This staging area is blocked on a functional `c2malbolge` path. The final Linguist sample must be produced by the real compiler/toolchain, not by a hand-crafted placeholder.

This directory prepares the technical pieces for a future contribution to [github-linguist/linguist](https://github.com/github-linguist/linguist).

It intentionally does not maintain popularity statistics or adoption counts. Any usage/adoption information required by the upstream pull-request process should be handled from the current upstream requirements at submission time, not copied into this staging area now.

## Current contents

```text
linguist/
|-- README.md
|-- sample.c
`-- grammar/
    |-- LICENSE
    |-- README.md
    `-- syntaxes/
        `-- malbolge.tmLanguage.json
```

`sample.c` is the human-readable source candidate. There is deliberately no generated Malbolge sample yet.

## Language model

The Linguist contribution should register one language named **Malbolge** and one TextMate scope:

```text
source.malbolge
```

The historical Ben Olmstead C interpreter and the written 1998 specification disagree on some runtime behavior. Those disagreements do not create two lexical languages. This repository treats the written specification as the authority for specification-conformant execution and preserves historical interpreter behavior separately.

The final Linguist contribution should therefore not invent separate entries such as `Malbolge (Ben)` and `Malbolge (spec)`.

## Grammar design

Malbolge instruction identity is position-dependent. For loaded non-whitespace position `i`:

```text
xlat1[(source_byte - 33 + i) mod 94]
```

The VM accepts the byte only when the decoded value is one of:

```text
j i * p < / v o
```

A stateless TextMate regex cannot correctly assign one of those opcode identities to a literal source glyph without tracking the global non-whitespace position modulo 94. The grammar therefore scopes only facts that are independently correct:

- graphical ASCII source units;
- invalid source-representation bytes;
- accepted ASCII whitespace is left unscoped.

See [`grammar/README.md`](grammar/README.md) for the exact VM-derived byte boundary and validation requirements.

## Sample strategy

`sample.c` exists now so the source can evolve alongside the compiler contract. It is intentionally small and bounded: it exercises function calls, local state, static data, loops, branches, array indexing, integer arithmetic, rotation, the classic crazy operation, and word wrap behavior without turning the future generated artifact into a stress test.

The final Linguist sample should still prove the actual modern toolchain rather than merely prove that a hand-written Malbolge string can be loaded.

The intended flow is:

```text
representative C source
        |
        v
repository-owned C validation
        |
        v
     c2malbolge
        |
        v
final Malbolge artifact
        |
        +--> modern VM load/execute verification
        `--> future Linguist sample candidate
```

The generated Malbolge sample should be created only after this path is executable. `sample.c` must not be presented upstream as a Malbolge classifier sample.

## Completion criteria

This staging area remains **WIP** until all applicable items below are complete:

- [ ] A native `c2malbolge` path can consume admitted C and emit a valid Malbolge program for an explicit target profile.
- [ ] The Rust/C VM source-whitespace discrepancy documented in grammar/README.md has been resolved or normatively specified.
- [x] `sample.c` passes the currently executable repository-owned guest-C bootstrap validation and pinned clang-format checks.
- [ ] `sample.c` passes the authoritative `malbolge-*` clang-tidy checks once that plugin gate is complete.
- [x] `sample.c` is bounded and exercises a representative baseline of C constructs useful to the future compiler path without intentionally creating pathological compile time or guest runtime.
- [x] Every helper/function in `sample.c` is reached from `main`; no dead demonstration helper exists only to inflate feature coverage.
- [ ] `c2malbolge` compiles that exact C source reproducibly.
- [ ] The emitted Malbolge artifact is accepted by the modern VM loader for its declared profile.
- [ ] Executing the artifact produces the expected observable behavior under the specification-conformant VM.
- [ ] The final artifact is small enough to be useful as a Linguist classifier sample. If it is excessively large, simplify the C sample rather than hand-editing compiler output.
- [ ] The final sample source, generated artifact, generation command, target profile, expected behavior, and license/provenance are documented together.
- [ ] The dedicated grammar repository is published under a Linguist-approved license.
- [ ] The grammar passes the current Linguist grammar compiler and `script/add-grammar` from a clean current Linguist checkout.
- [ ] The final extension or filename mapping is chosen and checked against the current `lib/linguist/languages.yml` at submission time.
- [ ] Any required disambiguation heuristic is added only if the final mapping conflicts with another Linguist language.
- [ ] `script/update-ids` generates the final `language_id`; the ID is never chosen manually.
- [ ] `bundle exec rake test` passes in the Linguist checkout.
- [ ] `bundle exec script/cross-validation --test` passes with the final sample set.
- [ ] The current upstream PR template is copied fresh and every required field is completed with current information.

Only after these gates are satisfied should this README stop calling the work WIP.

## Data to fill before submission

Do not freeze these values now. Resolve them from the final implementation and current Linguist repository immediately before opening the PR.

| Field | Source of truth |
| --- | --- |
| Final extension or filename mapping | Actual compiler/toolchain convention plus current Linguist mappings |
| Grammar repository URL | Published dedicated grammar repository |
| Sample URL | Final compiler-produced sample committed in this repository |
| Sample license | License covering the exact sample and its source |
| Target profile | Compiler invocation and artifact metadata |
| Generation command | Working `c2malbolge` CLI at that revision |
| Expected sample behavior | VM verification fixture/result |
| Color | Final proposed value and rationale, if a color is proposed |
| Heuristic requirement | Current Linguist mapping conflicts |
| `language_id` | Output of `script/update-ids` |

## Expected future patch shape

The final Linguist patch is expected to touch the normal new-language surfaces. Generated files must be produced by Linguist's scripts rather than edited manually.

```text
lib/linguist/languages.yml
samples/Malbolge/<FINAL_SAMPLE>
grammars.yml                 # generated/updated by Linguist tooling
vendor/...                   # managed by script/add-grammar
.gitmodules                  # managed by script/add-grammar
```

Conceptual `languages.yml` entry before running `script/update-ids`:

```yaml
Malbolge:
  type: programming
  extensions:
  - ".<FINAL_EXTENSION>"
  tm_scope: source.malbolge
  ace_mode: text
```

Add `color` only when the final value and rationale are settled.

## Future PR draft

Suggested title: `Add Malbolge`

The block below is reusable drafting material. Before submission, reconcile it with the **current** upstream PR template instead of assuming this snapshot is still exact.

````markdown
## Description

Add support for Malbolge, Ben Olmstead's 1998 esoteric programming language.

This contribution adds language detection, a TextMate-compatible grammar, and a representative sample produced by the Malbolge toolchain.

Malbolge instruction decoding depends on the loaded non-whitespace source position:

```text
xlat1[(source_byte - 33 + loaded_position) mod 94]
```

The grammar therefore does not assign fixed opcode scopes to literal source glyphs. It conservatively scopes encoded graphical source units and invalid source-representation bytes, leaving position-dependent instruction validation to the Malbolge loader/toolchain.

The written 1998 specification and the historical C interpreter disagree on some execution semantics. Those are runtime compatibility differences rather than separate lexical languages, so this contribution defines one language named `Malbolge` with the TextMate scope `source.malbolge`.

### Implementation data

- Grammar repository: `<GRAMMAR_REPOSITORY_URL>`
- Final mapping: `<EXTENSION_OR_FILENAME>`
- Sample source: `<SAMPLE_SOURCE_URL>`
- Sample license: `<SAMPLE_LICENSE>`
- Sample generated with: `<C2MALBOLGE_COMMAND>`
- Target profile: `<TARGET_PROFILE>`
- Verification: `<VM_TEST_OR_COMMAND>`
- Color, if proposed: `<COLOR>`
- Color rationale, if proposed: `<COLOR_RATIONALE>`
- Heuristics: `<NOT_REQUIRED_OR_DETAILS>`

## Checklist

<!-- Replace this section with the current upstream Linguist checklist before submission. -->

- [x] I am adding a new language.
- [ ] Final extension/filename mapping is present in `languages.yml`.
- [ ] Real compiler-produced sample is included and its source/license are documented.
- [ ] Syntax-highlighting grammar is published and included through `script/add-grammar`.
- [ ] `script/update-ids` has generated the language ID.
- [ ] Any required heuristic for a shared mapping is included and tested.
- [ ] Linguist test suite passes.
- [ ] Linguist cross-validation passes.
- [ ] Every field required by the current upstream PR template has been completed at submission time.
````

## Local grammar validation

The staging grammar can be checked locally for JSON validity and exact byte-class boundaries. The final gate is still Linguist's own grammar compiler.

The local reference checkout used for this staging work is `C:/Repos/reference/mit/linguist`. Its grammar compiler wrapper requires Go/Docker tooling that is not available on this workstation at the moment, so that upstream-specific compiler gate remains explicitly incomplete rather than being treated as passed.
