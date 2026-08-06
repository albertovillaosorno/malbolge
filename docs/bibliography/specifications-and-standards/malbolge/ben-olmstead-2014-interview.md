# Interview With Ben Olmstead

## Status

Verified as authority-decision evidence; canonical page availability unresolved.

## Subject

- Canonical name: Interview with Ben Olmstead
- Subject class: Author interview and historical language commentary
- Stable identifier: Daniel Temkin interview with Ben Olmstead, 2014
- Publisher or authority: Daniel Temkin, Esoteric.Codes; Ben Olmstead as the
  interviewed Malbolge author

## Repository Use

This interview is evidence for resolving disagreements between the 1998 prose
specification and Ben Olmstead's original interpreter. Olmstead states that the
interpreter's non-progress behavior for values outside graphical ASCII was
intended and that the corresponding defect was in the specification. He also
acknowledges a documented-versus-implemented table mismatch and the resulting
community fragmentation.

The repository uses this testimony together with the preserved interpreter
source. Defined and reproducible original-interpreter behavior is authoritative
for `malbolge-1998`; host-dependent behavior and C undefined behavior remain
explicit safe failures rather than language semantics.

## Provenance

Daniel Temkin published the interview on Esoteric.Codes under the site's stated
CC BY 4.0 default. The interview identifies Ben Olmstead as the speaker and
Malbolge's author. A scholarly article independently cites the legacy interview
URL and attributes the same authority dispute to Olmstead.

The repository does not infer more certainty than the source supplies. The
interview uses qualified recollection, so the preserved source code remains the
primary executable evidence for exact behavior.

## Identity And Version

- Stable identifier: Temkin-Olmstead interview 2014
- Interviewer: Daniel Temkin
- Interviewee: Ben Olmstead
- Displayed publication date supplied by the recovered page: 2014-11-03
- Repository access or verification date: 2026-08-04
- Canonical URL supplied for this review:
  `https://esoteric.codes/blog/interview-with-ben-olmstead`
- Legacy URL cited by later literature:
  `http://esoteric.codes/post/101675489813/interview-with-ben-olmstead`

## License Or Terms

Esoteric.Codes states that, except where otherwise noted, site content is
released under CC Attribution 4.0 International. This bibliography record is a
citation and paraphrase; it does not import external terms into the repository's
MIT license.

## Evidence

### Verified

- Olmstead identifies himself as Malbolge's author and discusses the original
  design and interpreter.
- He says stopping or non-progress outside `33..126` was intended and suggests
  the specification, rather than the interpreter, was wrong on that point.
- He acknowledges mismatches between documented and implemented tables.
- The preserved interpreter implements `<` as output, `/` as input, and
  non-progress when the current cell is outside graphical ASCII.
- Later scholarly literature cites the interview while discussing the
  specification/interpreter disagreement.

### Unresolved

- The canonical blog URL returned no page during repository verification on
  2026-08-04, while the user-supplied recovered page and later literature retain
  its content and identity.
- The exact historical URL and publication metadata changed across
  Esoteric.Codes platform migrations.
- The interview's qualified recollection is not used to legitimize undefined C
  behavior, locale dependence, or out-of-bounds accesses.

## Sources

- <https://esoteric.codes/blog/interview-with-ben-olmstead> - canonical URL
  supplied for review; unavailable during verification on 2026-08-04.
- <http://esoteric.codes/post/101675489813/interview-with-ben-olmstead> - legacy
  URL cited by later literature; accessed indirectly on 2026-08-04.
- <https://revistas.ucp.pt/index.php/jsta/article/view/7297> - scholarly
  corroboration and citation trail; accessed 2026-08-04.
- `src/interoperability/historical-malbolge/adapter-outbound/main.c` - preserved
  primary executable evidence in this repository.
