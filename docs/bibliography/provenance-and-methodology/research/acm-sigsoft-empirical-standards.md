# ACM SIGSOFT Empirical Standards for Software Engineering

## Status

Verified; evidence verified.

## Subject

- Canonical name: ACM SIGSOFT Empirical Standards for Software Engineering
- Subject class: Software-engineering empirical research methodology
- Stable identifier: Empirical Standards for Software Engineering Research
- Publisher or authority: ACM SIGSOFT

## Repository Use

Malbolge uses these standards as external prior art for choosing a research
method appropriate to the question being asked. They support method-specific
evidence requirements rather than one universal validity checklist.

The repository particularly applies the Engineering Research, Benchmarking,
Optimization Study, and Replication standards to compiler/runtime research.
Malbolge defines its own stricter fail-closed correctness and provenance rules;
this source does not directly govern repository policy.

## Provenance

The ACM SIGSOFT Empirical Standards describe community expectations for
conducting and reporting software-engineering studies. The standards are
method-specific and publish author/reviewer checklists rather than treating all
empirical work as one methodology.

Relevant verified guidance includes:

- engineering research should describe and conceptually evaluate the proposed
  artifact, discuss limitations, identify appropriate alternatives, and justify
  comparative evaluation;
- benchmarking should describe setup and workload sufficiently for independent
  replication, use enough repetitions/duration to assess stability, and retain
  raw measurements rather than only aggregate values;
- optimization studies should define search space, solution representation,
  fitness functions, algorithm/parameters, justified baselines, and sources of
  stochasticity; stochastic approaches should be repeated or the limitation
  justified, and variation/distributions should be reported;
- replication is a deliberate planned repeat of an identified earlier study,
  with motivation and enough dataset/process detail to understand what changed.

## Identity And Version

- Canonical site: ACM SIGSOFT Empirical Standards
- Standards site observed: 2026-07-26
- Cited report identity: Paul Ralph et al., *Empirical Standards for Software
  Engineering Research*, arXiv:2010.03525
- Source license statement: CC0 1.0 for the Empirical Standards

## License Or Terms

The standards site states that the Empirical Standards are licensed CC0 1.0.
This bibliography record summarizes verified methodological guidance and does
not
change the repository's MIT licensing or copy external text wholesale.

## Evidence

### Verified

- The standards are explicitly method-specific; different research methods have
  different expectations and quality criteria.
- Benchmarking guidance requires reproducible setup/workload descriptions,
  stability assessment through adequate runs/duration, and persistence of raw
  measurements instead of aggregate-only collection.
- Engineering Research covers technological artifacts including algorithms,
  languages, tools, and systems and expects strengths/weaknesses/limitations
  plus
  justified comparison or a rationale when comparison is impractical.
- Optimization Study guidance requires explicit search/fitness formulation,
  justified baselines, stochasticity disclosure, repeated stochastic trials when
  feasible, and reporting variation rather than only central tendency.
- The standards distinguish evidence-based results from interpretation and
  speculation in multiple applicable study classes.

### Unresolved

Malbolge does not claim compliance with every SIGSOFT standard for every record.
Each research record must declare the applicable method class and explain any
intentional deviation from the repository methodology or method-specific prior
art.

## Sources

- <https://www2.sigsoft.org/EmpiricalStandards/>
  - accessed 2026-07-26.
- <https://www2.sigsoft.org/EmpiricalStandards/about/>
  - accessed 2026-07-26.
- <https://www2.sigsoft.org/EmpiricalStandards/docs/standards>
  - accessed 2026-07-26.
