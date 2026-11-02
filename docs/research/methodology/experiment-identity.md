# Reproducible experiment identity and manifest

## Status

Implemented

## Research Question

What evidence and method are required to evaluate reproducible experiment
identity and manifest?

## Background

Define a versioned experiment manifest that records algorithm identity, exact
implementation/configuration, target profile, workload hashes, seeds, stopping
rules, host/accelerator identity, memory budget, compiler/tool versions, and
output location so any reported experiment can be reconstructed without editing
source constants.

- Status: Implemented
- Record type: Methodology
- Planning identity: `reproducible-experiment-identity-and-manifest`
- Last reviewed: 2026-07-26

## Prior Work

Prior-work claims must resolve through canonical records under
`docs/bibliography/`.

## Hypothesis

- One manifest is sufficient to reconstruct the exact challenge, algorithm,
  seed, budget, target profile, toolchain, host/accelerator identity, and local
  output location of a reported run.
- The research record separates observed evidence from interpretation and
  preserves negative/null outcomes that affect the conclusion.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.

## Method

Experiment manifest schema v1 is validated by
`src/automation/repository/composition/scripts/validate/experiment_manifest.py`.
Manifest file loading rejects invalid UTF-8 through the stable experiment error
boundary before TOML admission.

It admits only physical, non-redirected regular
files under a 1 MiB limit, reads through a no-follow/nonblocking descriptor
where available. Raw opening receipts must be exact native signed file
descriptors; the buffered reader and raw file object must be exact native
wrappers bound to the opened descriptor, which must remain unchanged before and
after reading.

Initial and post-read status checks require exact native stat
receipts and native integer mode, device, inode, size, and nanosecond
timestamps before interpreting filesystem identity. The initial file
verdict is an exact native boolean, not a host-supplied truthiness result.

Parent and leaf symbolic-link and junction verdicts must also be exact
native booleans, on both
initial and post-read inspection; foreign truthiness hooks never run. Stream
reads must provide exact native bytes before any length inspection, and UTF-8
decoder failures retain their original cause without formatting foreign
exception subclasses.

The reader rejects replacement or modification by
rechecking
device, inode, extent, and timestamps after reading. Repository-manifest
validation accepts working-directory-relative and absolute in-root paths without
resolving
away symbolic-link aliases; parent traversal is rejected. After source bytes
are admitted, repository identity must bind to the registered physical
research algorithm directory and the canonical `experiment.toml` leaf; neither
a matching directory basename nor rewritten provenance can mint a new ID.

TOML parser capacity errors, including oversized decimal integer tokens,
return typed manifest errors instead of host exceptions. The core parser now
also refuses a runtime replacement of the standard-library TOML decoder before
admitting source identity. Three red-first regressions show that otherwise a
native-shaped forged receipt can hide invalid syntax, change the declared
schema version, or replace a recorded Git commit without changing source text.
This pins the chosen decoder provider, not the authenticity of a source file or
all of the interpreter runtime's internals. TOML remains the checked-in
serialization, but the schema owns semantics independently of that format.
The standalone manifest validator CLI only reports success after an
exact native text-write count and a completed flush. Short writes, foreign
output receipts, and failed stdout delivery return nonzero; failed diagnostic
delivery cannot convert invalid manifests into a successful process exit.

Shared research discovery also rejects IDs that collide under Unicode case
folding, including a domain ID that aliases the composition state-graph ID.
The experiment and lifecycle validators receive this fail-closed discovery
result, independently of the research mirror's two-sided shape check.
Every research mirror carries `algorithms/<id>/experiment.toml` with:

- `schema_version = 1`;
- `[experiment]` identity, record kind, method class, and deterministic seed;
- `[challenge]` family, positive difficulty, target profile, and exact
  `malbolge-profile-v1` fingerprint whenever the target is one canonical
  profile;
- `[budget]` with at least one positive integer stopping bound;
- `[verification]` with `required = true` and an explicit oracle; and
- `[provenance]` with exact implementation, configuration, and local-output
  paths bound to the algorithm ID.

`record_kind = "plan"` freezes intended configuration without pretending a run
already occurred and must not contain a `[run]` table. `record_kind = "run"`
additionally requires a lowercase 40-hex Git commit, lowercase SHA-256 workload
hash, host identity, accelerator identity, toolchain identity, a closed outcome,
and the repository-relative raw-output path. Repository-relative paths reject
absolute, Windows drive/root, parent-traversal, and TOML-escaped NUL forms
before filesystem consumers receive them, independent of host.

Backslash path
separators are also rejected: evidence names use portable forward slashes so
Linux and Windows resolve the same repository-relative identity. Paths
containing Windows-reserved components, including device names, NTFS alternate
data streams, and trailing spaces or dots, are rejected even on POSIX hosts.
Accepted outcomes include success, no solution, candidate invalidity, resource
exhaustion, and tool failure so negative evidence remains reconstructible
instead of disappearing from analysis.

Canonical target profiles are content-bound, not name-only. A manifest naming
`malbolge-1998`, `malbolge-2026.1`, `malbolge-2026.2`, or
`malbolge-2026` must carry
`challenge.target_profile_fingerprint`, and the validator recomputes the
expected
fingerprint from validated `malbolge.json`. A mismatch emits stable
`MALBOLGE-PROFILE-ID-001`; an unknown ID never falls back. Explicit aggregate
research scopes (`profile-independent`, `multi-profile`, and the classic-word
benchmark domain) must omit the fingerprint so they cannot masquerade as one
canonical semantic profile.

Algorithm-specific tables may extend the core manifest without weakening these
required identities. Source claims still resolve through `docs/bibliography/`.
TOML is a [cataloged configuration
format](../../bibliography/specifications-and-standards/toml.md).

## Evidence

- All nine current research-mirror manifests validate under schema v1,
  including
  the checked-in template.
- `tests/test_experiment_manifest.py` proves repository identity, exact run
  commit/workload hashes, canonical profile fingerprint requirements and
  mismatch diagnostics, explicit noncanonical scopes, retained negative
  outcomes, fail-closed outcome vocabulary, positive stopping bounds,
  mandatory verification, and strict plan-versus-run separation.
- `.dependencies/python/3.14.7/Scripts/python-jig.cmd
  src/automation/repository/composition/scripts/validate/experiment_manifest.py`
  validates the checked-in corpus and
  reports the exact manifest count.
- Individual studies still own their hypotheses, raw outputs, interpretation,
  and threats to validity; this schema records identity rather than fabricating
  study-specific evidence.

## Results

Nine checked-in research plans now share one validated schema, and every
canonical-profile plan is bound to the generated profile fingerprint.
Recorded-run fixtures demonstrate that source commit, workload hash,
environment identity, outcome, and raw-output path are mandatory only when
observed evidence is claimed.
The schema therefore distinguishes preregistration/configuration from
observation
without requiring placeholder hardware or tool versions for work not yet run.

## Threats to Validity

The validator proves manifest structure and repository identity, not that a
caller supplied truthful host/toolchain strings or that a benchmark methodology
is statistically adequate. Workload selection, hardware effects, replication,
and measurement analysis remain responsibilities of the owning study and the
benchmark protocol. Algorithm-specific extension tables are intentionally not
interpreted by schema v1.

## Conclusion

Experiment manifest schema v1 is the active reproducible-identity contract. A
checked-in plan is not evidence of a run; a recorded run must bind exact source,
workload, environment, outcome, raw-output identity, and canonical target
profile fingerprint where applicable. This closes manifest identity while
leaving statistical adequacy and study conclusions to downstream owners.

## References

- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
