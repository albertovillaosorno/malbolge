# Multi-objective compiler algorithm evaluation arena

## Status

Active. Offline analysis, host-C baseline and bounded classic target pilot
implemented; general verified guest compiler evidence remains pending.

## Research Question

What evidence and method are required to evaluate multi-objective compiler
algorithm evaluation arena?

## Background

Evaluate compiler and execution algorithms over scalable challenge families and
produce capacity curves and Pareto frontiers rather than one pass/fail score.
Measure time-to-verified-solution, generated-code size, runtime instructions,
peak memory/VRAM, verifier cost, energy or device utilization when available,
success probability for stochastic methods, and maximum solved difficulty under
fixed budgets. Preserve raw evidence so an algorithm that is faster at easy
instances but scales worse than another remains distinguishable instead of both
appearing equally "perfect" after crossing an arbitrary threshold.

- Status: Active (bounded measured reference stages, no general guest compiler)
- Record type: Methodology
- Planning identity: `multi-objective-compiler-algorithm-evaluation-arena`
- Last reviewed: 2026-10-29

## Prior Work

Prior-work claims must resolve through canonical records under
`docs/bibliography/`.

## Hypothesis

- Authoritative comparisons retain capacity curves and Pareto frontiers; an
  aggregate score, if offered, is explicitly secondary and cannot hide
  time/quality/memory/size/verifier trade-offs.
- The arena measures every available execution/compiler stage without making
  a later target backend a prerequisite for the evaluation infrastructure; final
  `.malbolge` measurements are added when verified artifacts become available.
- The work states a falsifiable question or hypothesis, an explicit baseline,
  and an observation that would reject or materially weaken the proposed
  technique before performance conclusions are accepted.
- If executable algorithm research is required, the stable ID is mirrored under
  `docs/research/algorithms/<id>/` and `algorithms/<id>/`; ordinary product
  engineering is not forced into that mirror.
- Performance conclusions use equivalent workloads and report raw-sample
  provenance, resource budgets, dispersion/uncertainty, and failure/success
  behavior rather than only a best-case number.

## Method

Work under this record uses stable identities, explicit inputs and assumptions,
independent correctness evidence where applicable, and retained negative/null
results. Source claims resolve through `docs/bibliography/`.

`benchmarks/arena/analyze.py` now implements one deterministic offline input
boundary, documented under `benchmarks/arena/README.md`. Its version-one JSON
keeps one explicit study question, hypothesis, baseline, falsification
observation, compiler/execution stage, target and host/toolchain identities,
positive time/memory budgets, and ordered cost objectives. Per-trial records
retain algorithm, challenge family/version/difficulty/seed, workload SHA-256,
trial number, outcome, named external verifier, verdict, exact paths to
experiment identity and raw sample, and measured cost dimensions. Claimed
verified timings above the study time budget, or reported resident memory
above its budget, fail admission without authorizing unmeasured resource use.

The analyzer compares only cohorts with identical seeds, workload digests, and
trial numbers at each challenge difficulty. The named verifier must agree
for each matched challenge and trial across compared algorithms. Unmatched,
duplicate, or unverifiable comparisons fail closed. Every comparison requires
the declared baseline. An independently
named verifier and an accepted verdict are required to *report* success;
rejection, exhaustion, no-solution, and tool failures remain visible.

The analyzer does not replay that verifier or authenticate the references yet.

Curves retain trial counts, exact success fractions, per-outcome counts, and
cost medians conditional on verified success. Medians are exact integer
fractions, including even-sized and very large samples. Observed ranges
and exact median absolute deviations describe successful-cost dispersion,
while an all-attempt elapsed-time summary exposes failed-run cost. These
statistics are descriptive by default, not confidence intervals or
inferential evidence. An optional `--median-intervals-95` analysis adds exact
finite-sample distribution-free order-statistic 95%-or-higher intervals for
successful-cost medians, all-attempt elapsed medians, and candidate-minus-
baseline *both-success* paired cost medians. A two-sided binomial recurrence
finds the narrowest qualifying symmetric observed ranks without floating-point
arithmetic; reports include exact coverage fractions, integer rank endpoints
and sample counts. Fewer than six or more than 4096 observations give null
intervals. Ties may only improve the conservative lower bound on coverage.
This is inferential **only** under unverified independent identically
distributed sampling assumptions. Neither independence, physical timing,
randomization, nor verifier replay follows from the labels or this estimator;
selection on success changes the population being estimated. The default JSON
and nominal Pareto selection remain unchanged by the opt-in calculation.

A third optional inference view, `--success-intervals-95`, bounds the
reported probability of verifier success among **all** attempts, retaining
failure outcomes rather than treating only successful trials as a random
population. A conservative Clopper-Pearson calculation inverts exact two-sided
binomial tails and rounds probability roots outward to a 1/4096 rational grid,
without floating-point normal approximations. Inference is only justified for
independent identically distributed Bernoulli trials, which the research input
and the reported verifier labels do **not** themselves establish. Sample sizes
above 512 yield null rather than unbounded computation; zero successes yield a
nonzero possible upper success rate. The view is descriptive if the sampling
and verifier assumptions are not externally checked, and does not alter
nominal Pareto rankings or the default JSON schema.

The Pareto relation
minimizes declared costs and maximizes verified trial count inside each matched
cohort; zero-success algorithms remain in curves but are omitted from the
conditional frontier. The reported highest verified difficulty is observed,
not extrapolated, and there is no single aggregate performance score.

An opt-in evidence preflight under `benchmarks/arena/evidence.py` now imports
the repository's existing experiment-run manifest parser. It matches each
reported trial to its named run, challenge family/difficulty/seed, target
profile, workload fingerprint, host/toolchain, oracle, outcome, and raw output.
Repository-root relative manifest files must be bounded, canonical, regular,
and parseable; referenced raw samples must be present, nonempty, and ordinary.

The preflight also supports an opt-in `arena-raw-v1` CSV check using
`--require-raw-rows`. This verifies that the complete raw CSV row multiset
matches the reported trial identities, outcomes and exact integer costs,
including failed trials. SHA-256 fingerprints of the inspected file bytes
support later reproducibility checks.

The additional opt-in `--require-trial-run-identity` mode extends each
experiment run manifest with a versioned `[arena_trial]` table containing the
exact trial number and SHA-256 of the full referenced `arena-raw-v1` CSV. It
requires one distinct run manifest per observation and automatically enables
complete raw-row checking; one unscoped aggregate run cannot stand in for
multiple purportedly independent repetitions. These producer-declared
bindings are not proof of physical replication or verifier execution.

A separate opt-in `--require-budget-agreement` mode reads every governed
experiment run's `[budget]` table and requires explicit positive integer
`seconds` and `memory_mib` declarations. Those values must convert exactly to
the study's declared `time_ns` and `memory_bytes`, without rounding or allowing
one algorithm a different recorded resource budget. This is a reporting
consistency check only, not physical runtime or peak-memory enforcement.

Version-two `arena-raw-v2` evidence adds an optional exact integer `energy_uj`
(microjoules) cost to the six preexisting dimensions. Its CSV schema marker is
`2` and its fixed header adds one column without changing version-one bytes.
Source-reported energy cannot silently appear in a version-one file, and a
verified observation cannot omit energy when the study declares it as an
objective. This is *representation* support only: energy samples, meter
calibration, host attribution, uncertainty and physical validity remain
unproven until real measurement evidence is admitted and reviewed.

A separate opt-in `--challenge-root` mode now binds each distinct arena
case to the completed deterministic parametric compiler challenge generator.
The case family, version, seed and `difficulty` (interpreted as `nodes`) plus
study target profile drive a bounded read-only regeneration of canonical
`program.c`, `oracle.bin` and `manifest.json` bytes. The arena workload SHA-256
must equal the regenerated C source digest. A repeated case with a different
digest fails even if both algorithms report that forged identity. Files must
be ordinary, canonical, unlinked and bounded, and the profile fingerprint
remains under the generator's existing authority. No compiler or verifier is
run; this does not prove the optimizer consumed the retained challenge.

A separate `--require-host-c-challenge-oracle` mode now requires the
canonical `--challenge-root` preflight, then executes the **generator's**
C entry function against the recorded four-byte oracle. The checker
re-generates the checked source before launching the repository-pinned
Clang 22.1.8 compiler at `-O0` and `-O2`, links an independent return-value
harness, and requires both native executions to match. It accepts at most
16 distinct cases of 512 nodes and gives each child 15 seconds, with temporary
source/object/executable files removed after the check. The matched C source
fingerprints and modes remain visible in the evidence preflight. Canonical
bundle corruption fails before any compiler launch; failed compilation,
execution or timeout fails the entire preflight without emitting a report.
This is real host-C **challenge oracle replay**, not verification of an
algorithm's generated candidate artifact, not proof of Malbolge semantics,
and not authentication of any producer-reported elapsed time or memory use.
There is no OS sandbox or physical budget enforcement. The final candidate
verifier and real multi-difficulty compiler comparison remain outstanding.

A separate first *real target Malbolge* pilot now pairs the actual
`malbolge_layout` source emitter with the general classic `malbolge` VM on
fixed empty-input byte-echo programs. The direct arm uses one input/output
pair per requested logical byte; the comparison adds one inert no-op per pair.
Classic EOF returns low byte `0xA8`, which the external VM must emit exactly
once per pair to count as an observed verified trial. The producer admits
1..64 pairs at up to four distinct difficulties, 1..3 paired repetitions,
actual graphical source bytes, strict per-run TOML/raw-CSV identity, real
external process outcomes, and source-size/elapsed-time observations. It
alternates arm order across repetitions and records negative outcomes rather
than conferring success when a tool fails or output differs. The resulting
ignored `.temp/arena-target-echo-*/study.json` is independently checked by
the arena's existing raw/manifest/budget admission before capacity/Pareto
analysis; separate external-process and tampering regressions constrain this
claim. The prior lack of an actual `.malbolge` measurement is narrowed only
for this small, fixed classic target-subset.

The producer and opt-in replay now run external emitter/VM children through
`benchmarks/arena/target_process.py`: POSIX-isolated child sessions,
selector-drained stdout/stderr (4 KiB and 16 KiB separately), and one 15-second
wall deadline that includes child launch, pipe closure and direct-child exit.
Any stream overrun or pipe-retaining ordinary descendant past the deadline is
a typed failure with a direct-child reap and best-effort original process-group
termination. Regressions inject oversized standard/error streams, deliberately
fragmented dual-stream output, idle children and an ordinary descendant that
would otherwise keep the caller waiting on inherited pipes. This bounds host
capture allocations; it is not an OS memory quota, process sandbox, complete
descendant containment (detached sessions remain outside the group), or a
physically enforced study-wide budget. The pilot requires POSIX for this
subprocess boundary and makes no Windows process-supervision claim.
The same transport now supports an optional bounded exact 256-byte binary
input channel, with nonblocking delivery and a positive wall deadline even
when the child refuses to read. A new opt-in `--input-stdin` mode in the
product CLI passes these bytes to classic and selected-profile normative VM
constructors. End-to-end CLI tests check all 256 byte values followed by
classic EOF and actual current-profile binary input, while the unchanged
default still uses an empty input buffer.

A second opt-in real-target study `--input-mode patterned` now fixes an
independently reconstructable eight-byte periodic input vector, including NUL,
`0xFF`, `0xA8` and high-bit bytes. For each difficulty `pairs`, a generated
classic source reads and outputs all `pairs` supplied bytes and then performs
one final input/output pair at EOF. The complete expected output, including
this final `0xA8`, is checked from the actual process bytes. A distinct study
ID, fixed oracle, case family and SHA-256 workload identity bind the exact
input payload to the reported records and per-trial receipts. Direct and
one-nop-per-pair sources have `2*(pairs+1)+1` and `3*(pairs+1)+1` bytes.
The read-only auditor independently reconstructs the fixed byte vector,
checks positional classic decode for every instruction and, when requested,
replays retained successful sources through the same exact hashed toolchain.
The original empty-input EOF mode is byte-identical and backward compatible.

A separate **opt-in** `--measure-steps` study now obtains actual normative VM
`RunOutcome` instruction counts through `malbolge --report-steps` stderr,
rather than projecting instruction count only from the generated source's
length. The CLI adds per-chunk counts exactly, including the terminating step,
refuses integer overflow, and leaves default output unchanged. The arena
requires a complete canonical machine-readable receipt and records a missing
or invalid receipt as `tool_failed`, not a guest semantic rejection. It
retains its integer in `runtime_steps` and adds that metric to a three-cost
Pareto comparison.
The two version-two study identities bind this changed measurement contract
without invalidating older EOF and patterned studies. Inverse classic source
decode independently establishes the exact expected count on the admitted
straight-line I/O subset and rejects forged or missing runtime measurements;
replay additionally checks the full stderr receipt against the original
count using the exact recorded VM binary. Forged study-count and replay-count
regressions distinguish production correctness from independent audit. In
this narrow linear subset, each emitted source byte is executed exactly once,
so guest steps and source bytes are perfectly
correlated. There is no new evidence about general program control-flow
runtime work, physical power, CPU throughput or independently authenticated
historic execution. No memory instrumentation, worktree attestation, general
bytecode compiler, profile-independent execution, or physical resource
enforcement is implied.

A distinct preregistered forward-jump study extends the target I/O subset
to **strictly forward, non-revisited code** and makes real `runtime_steps`
differ from code size. The control walks through 99 executed graphical
no-ops before `pairs + 1` input/output steps (including final EOF), while
the `malbolge_layout --auto-layout jump` proposal enters an equal-sized
source with one forward jump and 98 skipped no-op cells. Both run the same
`00 FF A8 5A 80 01 7F FE` periodic input oracle followed by the canonical
EOF byte. Both contain exactly `102 + 2*pairs` source cells; the true
normative VM count is `102 + 2*pairs` for the walking control and
`4 + 2*pairs` for the jumping candidate. At difficulty 64 the real counts
are 230 vs 132. The hypothesis is rejected if size differs, output fails,
or the jump saves no VM instructions. The study fixes an independent source
fingerprint, case family, oracle and study ID, and retains paired trials,
strict CSV/TOML evidence, original VM step receipts and optional replay.

The independent source auditor reconstructs the target from the initial
source cell's *actual integer value* `0x62`, checks that jump target 99
skips exactly 98 graphical no-ops, verifies the position-sensitive classic
opcode of every source cell, and checks expected counted semantic steps.
Mutable source is admitted only for a single forward jump; later revisits,
loops, conditional control flow and data relocation are not supported by
this small cohort. Replayed output and complete stderr step receipt must
match the original retained claim. This establishes a genuine code-size vs
runtime-work tradeoff but not host speedup (elapsed times mix process startup
and code emission), energy savings, or verified arbitrary compilation.

An additional **explicitly opt-in** target protocol measures actual
per-candidate static verifier cost, with a distinct
`classic-patterned-forward-skip-verifier-cost-v2` study ID and a fourth
`verifier_ns` Pareto objective. For each successful bounded forward-jump
candidate, the producer invokes the independent read-only source checker,
which reopens the regular candidate bytes and checks every position-sensitive
classic opcode, fixed jump operand, skipped padding, reached code and exact
source length. Its monotonic elapsed nanoseconds are measured separately and
included in the total trial duration. The independent read-only auditor
requires a positive measured verifier cost no greater than the complete
trial duration for each verified v2 candidate, rejects the metric in older
cohorts and failed trials, and binds the exact
value through the existing CSV/run evidence. This protocol measures **only
static source admission**, not the complete semantic oracle, actual VM replay,
CPU instructions or a physical memory budget. Source-reported timing cannot be
independently authenticated by the later audit; host scheduling variance
requires multiple controlled samples before any verifier speedup inference.
The original three-cost and two-cost studies are unchanged.

A third, *dynamic verifier-cost* protocol makes the missing VM oracle time
explicit rather than conflating it with static checking. Only
`--measure-verifier --verifier-mode replay` creates the separate
`classic-patterned-forward-skip-replay-cost-v3` study and the
`classic-forward-jump-patterned-second-vm-v1` run oracle. After a correct
production run, each candidate is re-opened, decoded by the independent
source checker, and executed by a second bounded **process of the same
normative Malbolge VM** with fresh patterned binary input. The second run
must reproduce exact guest bytes, final EOF and strict step receipt, and the
original graphical source must remain stable after replay. A semantic output
mismatch or changed candidate is rejected; runner/receipt faults become tool
failures. Only fully admitted cases receive `verifier_ns`, which now includes
source decoding, process startup, repeat VM execution, pipe transfer and
post-replay evidence admission. `elapsed_ns` includes the primary and second
VM runs, so these costs describe one *verified attempt*, not comparable
single-execution wall times. The v3 verifier name and stable study ID jointly
prevent accidental relabeling of v2 source-only observations with only an ID
change. The read-only auditor binds source/metric/manifest/CSV identity and
can execute the retained guest again with the recorded binary fingerprint;
it cannot authenticate the original measured duration. This is a real second
execution, not a distinct independent interpreter, arbitrary C translation,
physically enforced whole-study budgets or an attested performance estimate.

A separate v4 target study adds **actually enforced per-child Linux
resource ceilings** to the measured source-plus-second-VM replay protocol.
Only `--limit-child-resources` combined with the v3 forward-skip replay
flags activates `classic-patterned-forward-skip-limited-replay-v4` and the
separate `classic-forward-jump-limited-second-vm-v1` oracle identity.

Before creating any study output, the producer requires Linux and `prlimit`;
source emission, first VM execution and measured second VM execution each
run with inherited hard `RLIMIT_AS=1 GiB` virtual-address-space, `RLIMIT_CPU=8`
seconds, and `RLIMIT_FSIZE=8 MiB` regular-output-file quotas. Their existing
15-second wall deadline, bounded stdout/stderr capture and process-group
cleanup are unchanged. An optional later audit VM replay applies the same
child resource controls, ensuring it does not silently downgrade to an
unlimited check.

Real subprocess regressions inspect kernel-visible limit values, exceed the
hard output-file cap, preserve 256 binary input bytes and EOF, and demonstrate
rejection when `prlimit` is unavailable. The static auditor enforces v4 study
and verifier identity separately from v3, while exact raw CSV and run
manifests retain the successful four-cost observations without claiming
additional unmeasured resource metrics.

These per-child ceilings do **not**
measure peak resident memory, contain detached descendants, impose aggregate
study-wide CPU/RAM caps, or prove that any historical producer actually ran
under the claimed policy. This remains a bounded classic echo study, not
general C compilation, full guest-program proof or performance attestation.

A distinct v5 target protocol now adds an actual *measured* fifth
Pareto cost. Only the versioned `--measure-child-rss` opt-in, combined with
all physically limited v4 replay flags, creates the
`classic-patterned-forward-skip-limited-rss-v5` study and its separate
`classic-forward-jump-limited-rss-second-vm-v1` oracle. Linux `prlimit` and
GNU time are mandatory before any study output is allocated. The two
mandatory executables are found only under the OS-default `/bin:/usr/bin`
search path, not through caller-controlled `PATH`. Synthetic fake limiter and
meter binaries cannot shadow them; the OS-provided tools are still trusted,
not independently attested. Each emitted candidate is measured during the
source-emitter process, primary normative VM run and measured second verifier
VM run; GNU time reports Linux kernel
`ru_maxrss` in KiB, with explicit exact conversion to `peak_rss_bytes`.

The observed cost is the maximum of those **three per-child** peaks, not
the aggregate resident memory of a compiler session or the sum across
concurrent processes. Every accepted candidate must have three complete,
positive, bounded measurements; failed stages or missing/malformed reports
are tool failures with no successful fifth cost.

The independent post-run
source auditor checks v5 study/oracle identity, exact five-objective
policy and the report's 1 GiB ceiling/KiB granularity. Existing arena
raw CSV, run TOML and JSON matching checks bind the claimed metric, while
optional future VM replay retains the v4 per-child physical caps.

No
historic GNU time receipt is retained or cryptographically authenticated;
read-only audit **cannot** reconstruct or trust the original measured RSS.
No resident-memory cgroup total, process-tree aggregate, system energy,
VRAM, deterministic host timing or general C lowering is established.

A separate v6 resource-evidence protocol makes the previous v5
maximum RSS claim **inspectably decomposable**. Only the additional
`--retain-rss-stages` opt-in creates
`classic-patterned-forward-skip-rss-receipts-v6` with oracle
`classic-forward-jump-rss-receipts-second-vm-v1`. The five Pareto metrics,
child limits, verified classic workload and v1-v5 protocols remain unchanged.

For each successful run, deterministic `rss/<stem>.json` stores separate
source-reported emitter, primary VM and measured verifier VM peak resident
bytes. Each receipt also binds the declared algorithm, difficulty, trial
number and workload SHA-256, rejecting accidental cross-cohort swaps. A
version-one `[arena_rss]` run-manifest extension records SHA-256
of the exact receipt bytes. The independent audit requires complete
canonical stage names, precise positive KiB granularity, unchanged 1 GiB
limit, the reported maximum, and an exact per-trial receipt inventory.

Auditor input snapshots include the stage receipts alongside the study,
trial TOMLs and raw CSVs; they are rechecked before any report is returned,
including after an optional independent normative VM replay. Missing,
malformed, extra, symlinked, differently hashed or internally inconsistent
stage receipts fail rather than granting an unmeasured Pareto objective.

Receipts **do not authenticate historical measurements**: the original GNU
time capture files are deleted after child exit, and matching report bytes
can still be forged by a producer controlling all study inputs. This is
not per-study peak resident usage, process-tree aggregate containment,
attested kernel metering, or validation of general target compilation.

Version seven separates historical producer conversion from the retained
raw resource reading. Only `--retain-raw-rss`, combined with all v6 flags,
selects `classic-patterned-forward-skip-raw-rss-v7` with the dedicated
`classic-forward-jump-raw-rss-second-vm-v1` verifier. Every previously
versioned study retains its original bytes, five v5-v7 objectives and
bounded execution contract.

Each successful v7 trial's schema-two canonical RSS receipt adds the actual
captured GNU time `--format=%M` single-line output strings for emitter,
primary VM and second VM, with exact `[arena_rss]` schema-two SHA-256 linked
through the run. The independent source auditor parses these strings into
positive integer KiB with strict ASCII and line termination, proves that
each reported byte value equals 1,024 times the source reading and that
`peak_rss_bytes` is their maximum, rechecks unchanged run/raw/receipt bytes
and optionally verifies target VM output. Wrong historical raw conversion,
missing third-stage evidence, forged inconsistent tool text, non-ASCII and
extra lines fail closed even if the attacker refreshes the manifest digest.

A separate opt-in, read-only audit `--stage-rss-breakdown` computes
per-stage medians and ranges for each accepted algorithm/difficulty cohort,
with explicit trial totals, failed-trial counts and only matched-both-verified
per-trial median candidate-minus-baseline differences. It is derived from
the same source-admitted, hash-linked v6/v7 receipt bytes and undergoes the
same post-analysis recheck against linked input drift and inventory changes.
This provides a means to test whether emitter peak memory hides real VM
changes without expanding the published study's five Pareto cost metrics.
A missing matched-success cohort is reported with no invented numeric costs.

The raw tool bytes are retained **by the producer**, not cryptographically
signed by an independent kernel or a trusted resource agent. A producer
controlling all study inputs can fabricate consistent observations. No
aggregate process-tree RSS containment, cgroup budget, system energy, VRAM,
calibrated host wall-time speedup or general guest C compilation is claimed.

The earlier linear study remains a falsifiable source-size hypothesis (the
nop-padded source should use one extra graphical code byte per pair), not a
general compiler-size or performance result. Host wall times include compiler
process startup, code emission, runner startup, and VM execution. The recorded
resource budget is declared but not enforced study-wide; no hardware
attestation or
statistical speedup inference is claimed, and the source bytes do not carry
modern capsule identity. Neither classic I/O check independently proves
C-to-Malbolge translation, arithmetic correctness, heap/call linking, or
unrestricted target-profile execution. Broader verified guest workloads and
multiple physically controlled host observations remain open.

A separate `benchmarks/arena/target_echo_audit.py` now provides producer-
specific **read-only post-run source admission** for these classic target
studies. It accepts only canonical ignored study locations, checks the fixed
research claims, bounded consecutive trial populations, case fingerprints,
exact run/raw/candidate paths, source revision consistency, producer-specific
manifest provenance, and full strict arena raw/budget preflight. For every
reported verified program it independently decodes each retained graphical
byte against the frozen classic translation table and position-specific
expected input/output/no-op/halt trace. Forging a different same-length source
is thus rejected even when its manifest and raw CSV remain self-consistent.
The real study producer calls this audit before returning a successful study;
a subprocess echoing the expected bytes cannot make a forged code stream pass.

The optional `--replay-candidates` audit mode requires the local emitter/VM
binary fingerprints to match the recorded combined toolchain fingerprint,
reexecutes all retained successful sources through the general classic VM,
and checks full expected EOF output and unchanged source bytes afterward.
A separate final source-byte recheck before report publication catches observed
mutations after initial independent decode, including changes that occur while
the Pareto comparison is assembled. A real 64-pair regression emits and replays
129- and 193-cell programs across the classic 94-position decode phase wrap.

The audit now pins the full original study JSON and all declared per-trial
manifest/raw bytes before cross-record preflight. After assembling the offline
comparison, it reopens every admitted input and verifies matching exact SHA-256
before publishing the result. It also rescans the run/raw/candidate inventories
for late additions or removals. Tests mutate otherwise valid JSON, CSV and
TOML after their initial checks, and inject unreported files after admission;
all must reject rather than returning a stale report. The reader protects
individual descriptors from observed inode or timestamp drift, but these
multiple reads do not establish an atomic snapshot against an adversary that
can race or restore bytes between checks. A distinct opt-in Git-object gate
checks that the revision consistently reported by run manifests resolves to a
local Git commit object, refusing absent or non-commit objects. This extends
reported source provenance beyond syntactic cross-record agreement without
claiming that a particular worktree or build actually executed. Git-specific
environment variables are removed from the child lookup so inherited Git
object-directory and worktree overrides cannot substitute another
Git database. All four source-commit producer/auditor lookups also resolve the
Git executable through the OS-default `/bin:/usr/bin` search path; a fake
caller-`PATH` Git cannot provide a forged SHA-1 or claim an absent commit
object exists. This still trusts local Git and its object database.
Neither static admission nor opt-in replay authenticates historical
measurements, validates reported failures by reexecution, enforces aggregate
resources, or proves arbitrary guest semantics. Missing original binaries can
block replay while leaving the offline source evidence inspectable.

The bounded host-C *reference study* runner now measures actual compiler,
linker and native oracle-check wall time, executable size and maximum
per-stage kernel RSS for pinned
Clang `-O0` versus `-O2` on exactly paired generator cases. It writes an
ignored local output tree containing reproducible canonical challenge bundles,
per-trial versioned run manifests, retained `arena-raw-v1` CSV rows, a study
JSON file and SHA-256-identified native executables. Its publisher reruns the
strict trial-run/raw-row, declared budget and source-bundle identity preflights.
The producer independently reopens each retained successful executable,
rechecks exact originating trial path and SHA-256, and requires byte length to
match the reported artifact-size metric. Failures cannot claim successful
binaries; missing, extra, linked or tampered artifacts fail the local study.
This is integrity of locally retained host artifacts, not independent proof of
candidate compilation, host resource enforcement or measurement attribution.
On Linux, pinned host-C compile, link and oracle stages now execute under
util-linux `prlimit` in separate POSIX sessions. Per-child kernel limits are
1024 MiB of virtual address space, 16 seconds of CPU time, and 8 MiB per
output file; parent process monitoring supplies a 15-second wall limit per
stage and best-effort original-process-group cleanup after success or timeout.
The runner fails closed if Linux or `prlimit` is unavailable. Live regression
children inspect actual inherited kernel rlimits, exhaust the CPU/file-size
limits, and verify normal descendant shutdown in both success/timeout paths.
Each new host-C study writes a version-two `resource-controls.json` with
per-child limit policy and the GNU `time` measurement identity. It refuses
to begin if either `prlimit` or GNU `time` is absent. Both host-C stage
wrappers now resolve from the OS-default `/bin:/usr/bin` search path rather
than user-controlled `PATH`, so caller-supplied fake limiter/meter executables
cannot impersonate the configured kernel enforcement or reported RSS. The
system binaries remain trusted dependencies, not independently attested.
Child stage usage is reported through Linux `ru_maxrss` in KiB; the maximum
of successful compile, link and execution stages is converted to exact
`peak_rss_bytes` and retained in raw CSV and analysis as a third cost objective. This is a measured direct
process-stage maximum, not a combined process-tree RSS or proof of full study
memory use. Legacy version-one receipts and two-cost studies remain admitted;
a three-cost RSS study requires the version-two measurement receipt.
The offline auditor admits the bounded normal-file receipt with strict field
names, types and policy values; `--require-resource-controls-record` rejects
legacy study directories with no receipt, while default mode reports them as
unverified for resource-control provenance. A matching sidecar establishes
consistency with current configured controls, not independently authenticated
historical enforcement, aggregate peak physical memory or a cgroup.

These are **per-child** limits and direct-stage peak-RSS observations, not
cgroup restrictions, escape-proof sandboxing, aggregate resource use, or
study-wide enforcement of the declared
60-second/1024-MiB budget. Historical host-C pilots predate this boundary,
and their recorded measurements cannot be retrospectively certified.

The runner and the optional host-C challenge-oracle replay are deliberately
**different**: reference runs measure compiled host C, whereas the existing
arena analyzer accepts producer-reported data. The stage is labeled
`host-c-reference-not-malbolge`; the actual host measurements are not evidence
of Malbolge compiler performance. Independent optimizer candidate verification,
aggregate peak-memory/energy measurement, full physical budget enforcement and a
reviewed generalizable scaling conclusion remain absent.

An independent `benchmarks.arena.reference_audit` command can now reopen
retained host-C reference studies after the producing process exits, without
rerunning measured work. It admits only canonical ignored study paths and
revalidates exact host-C stage/arm/verifier identities, bounded difficulty and
trial scope, complete experiment-run TOML and v1 raw CSV links, declared
budgets, regenerated challenge sources, and the native executable's linked
path, SHA-256 digest, and byte length. The audit also enforces the source
runner's common consecutive trial set across every difficulty, rejecting
unequal repetitions even when the generic arena accepts each paired cohort.
It also binds each trial's manifest and raw filename to the native producer's
exact arm, difficulty and repetition naming rule. A real-study rekeying test
retains valid raw, TOML and binary links while rejecting the renamed paths.
The three fixed native research claims (question, hypothesis, rejection
observation) now match the producer text exactly; changing them in retained
study JSON is a source-identity drift, even though the generic analyzer accepts
other well-formed research questions.
Its default path reads files only; an explicit `--replay-oracles` mode can
rerun the **canonical generator's** native C entry harness, never a retained
trial executable or Malbolge artifact.
The new independent `--rebuild-binaries` option additionally compiles fresh,
canonical host-C executable bytes with the same pinned Clang and independently
compares them byte-for-byte against all retained verified binaries, deduplicated
per source and arm. Mutating an executable while recomputing its reported
SHA-256 can pass file-to-claim checks but not this source-to-binary replay.
The artifact, failure, and resource-control JSON sidecars now reject
ambiguous duplicate names at every depth and nonfinite numeric literals;
scanner recursion failures also produce a typed audit rejection. These are
read-admission safeguards, not proof of historical measurements or authorship.
The mode never executes a retained binary; new oracle harnesses run only from
canonical generator C. Exact reproducibility assumes the same native toolchain,
linker, libraries and host ABI, and does not reproduce recorded wall times or
provide Malbolge candidate verification.

Post-run audit now rejects disagreement among source-commit claims in the
retained per-trial manifests, even if all other record identity fields match.
It also requires the producer's fixed run method, implementation/configuration
paths, output directory and no-accelerator declaration. Valid but foreign
research metadata fails the producer-specific audit; this is a consistency
check, not source or execution attestation. Strict real-native audit regressions
now also cover composed-pipeline, ternary-fold, pointer-walk and alias-walk
families, with canonical oracle replay, byte-for-byte independent native
rebuild, resource/source-object checks and unchanged retained file fingerprints.
The additional challenges establish audit path coverage, not statistical
performance validity or Malbolge compiler execution.
An optional `--require-source-commit-object` gate checks that the shared
claimed SHA-1 resolves to a local Git **commit** object; default audits retain
the claim without requiring a complete local Git history. Local object
existence cannot authenticate the original measurement environment or prove
that its code actually ran; that distinction is explicit in the report.

The inspectable output preserves the observed capacity curves/frontiers but
does not rerun elapsed-time measurements, authenticate the source producers,
or establish an atomic filesystem snapshot. Mutating any retained proof file
or mislabeling the host-C stage rejects the post-run audit.

For negative results, the host-C reference producer now retains a separate
versioned `failures.json` file that maps every failed trial manifest to a
bounded, printable diagnostic from the failed host compiler/linker/oracle
stage. Both producing and offline audit paths require exact agreement of the
failure index with `tool_failed` observations, no entries for accepted runs,
and no missing or forged entries. Invalid schema, overlong/unprintable text,
and absent files when a failure was reported reject. Old fully successful
studies remain readable without the extension. Error text is only recorded
local process evidence, not independent attestation that the stage failed.

The optional `--require-matched-accelerator` check additionally requires all
linked experiment runs to name the same recorded accelerator and retains the
canonical manifest-path-to-device identity map in the output. This protects
same-device comparison claims against silent heterogeneous arms while leaving
explicit cross-accelerator comparisons permitted without this mode. Even
matching declarations do not attest actual hardware or accelerator utilization.

The host-C reference-study producer now also uses that same checked stdout
publisher. A short text write or flush failure causes a nonzero operator exit
rather than claiming the local study summary was delivered successfully;
retained verified local evidence is not deleted on stdout failure.

Both arena CLI commands also share a checked JSON stdout publisher: the
complete report is serialized before one text write, whose returned character
count must be exact, then explicitly flushed before successful command exit.
Short, absent, boolean or overstated write counts and write/flush exceptions
return nonzero. Already emitted prefixes cannot be rolled back after stream
failure; this boundary guards reported publication status, not atomic stdout.

Both the default analyzer and evidence-aware CLI now also use one bounded
study-file input reader: source path and opened descriptor must retain exact
regular-file inode identity, byte size, modification/change times, and a
complete read. POSIX nonblocking/no-follow open flags reject raced FIFO and
linked leaves; injected regular-file replacements and mid-read writes fail
before either CLI emits partial JSON. This narrows the initial study-file
admission race without proving an atomic filesystem snapshot or record origin.
The study input reader now consumes the admitted inode size across bounded
short chunks rather than interpreting one short read as a complete file.
Premature EOF, nonbyte or overlong chunks, and five injected read-stream
exception classes reject through a typed arena error, with the original stream
failure preserved as its cause. Both arena CLI routes share this reader.

The shared evidence-file reader now checks the admitted regular file against
its opened descriptor and verifies device/inode identity, byte length and
nanosecond modification/change timestamps through read completion. It also
rechecks the canonical nonlinked path after read. Nonblocking/no-follow open
flags where available prevent a replaced FIFO or linked leaf from becoming an
indefinite blocking read. Deterministic replacement, in-place rewrite, and
POSIX FIFO substitution regressions prove rejection of observed file drift.
This is not an atomic snapshot guarantee against an adversarial filesystem
scheduler.

A raw match cannot independently prove that the CSV was measured accurately,
that a verifier actually ran, or that resource budgets were enforced.
The test fixtures establish only evidence linkage, not performance results.

A secondary paired baseline view now reports each candidate against the
predeclared baseline on exactly matched trials. Verification outcomes retain
four categories: both solved, baseline-only, candidate-only, and neither.
Cost wins/losses and exact median signed differences are computed only from
pairs where both solutions passed the named independent verifier. This avoids
pretending that a failed run has a successful solution size or cost. The paired
view does not replace the authoritative multidimensional frontier. An
optional `--paired-exact-tests` view now computes exact two-sided conditional
binomial probabilities for verification-outcome asymmetry (McNemar-style
baseline-only/candidate-only successful arms) and cost sign asymmetry among
*both-verified*, non-tied paired measurements. These are distinct estimands:
a verified failure is never assigned a fictitious successful cost. Each test
conditions on its discordant pair count, computes the exact rational null
probability without floating-point rounding, and refuses to infer from zero
or more than 4096 discordant pairs. The test requires independently sampled
matched pairs and a symmetric-sign null; the analyzer cannot verify sampling
independence or physical measurement validity. Across multiple objectives and
cohorts, the probabilities are unadjusted for multiplicity and are not
significance or performance-promotion verdicts. This view does not change
nominal Pareto rankings or existing reports by default.

A further explicit `--adjust-paired-tests` option requires the paired test
view, then applies exact step-down Holm-Bonferroni correction across the
complete study-wide family of nonnull paired outcome and cost-sign tests,
including different algorithms, objective dimensions and difficulty levels.
It retains unadjusted fractions alongside exact adjusted fractions, reports
the total family size, and treats tied p-values consistently. The direct
statistical port admits only exact `Fraction` probabilities in `[0, 1]`, so
nonfinite floats and truthy integer substitutes cannot enter the correction.
Holm controls family-wise error under arbitrary test dependence *only when*
its marginal p-values are valid. It does not establish pair independence, honest verifier
execution, representative workload selection, or physical timing validity;
no significance or performance promotion decision follows automatically.

This first slice intentionally does not require an executable final `.malbolge`
backend; the study's `stage` can describe available compiler or execution
boundaries. All results from real studies must separately pass experiment
manifest validation, benchmark protocol, independent semantic verification,
and raw evidence review before any performance conclusion is published.

## Retained historical comparisons

The read-only `benchmarks/arena/historical_pairs.py` adapter now admits two
existing September 4, 2026 source-pinned classic research records through the
same arena analysis engine. It requires the registered experiment run and
benchmark protocol to agree on challenge, host, raw path, outcome, target
profile, and pairing. It checks complete repeated strategy pairs, registered
quality-map fingerprints, complete registered raw CSV schemas, exact
structural counts, and source-byte hashes. The independent retained
`source-commit.txt` must agree with the manifest's recorded Git revision.
An explicit evidence-status marker states `source-reported-not-reverified`.

The prefix-decomposition study reports 8,836 versus 8,742 verifier calls,
with baseline/candidate timing medians of 831,921,051 and 835,180,632 ns.
Only two of five retained timing pairs favor the candidate; the observed
median speedup hypothesis is not supported on that host.

The verified-block-reuse study reports 17,672 versus 8,836 verifier calls,
with medians of 1,617,672,749 and 851,323,429 ns. All five retained pairs
favor reuse. This is a within-corpus, recorded-host result, not a generalized
performance or difficulty-scaling conclusion.

These are separate challenge families with different difficulty settings, so
their trials never share a comparison frontier. Only elapsed-time costs enter
the imported Pareto projection; registered verifier-call counts are presented
as a separate structural evidence field. The adapter cannot reproduce the
original host measurements or replay the independently recorded verifier.
The original study records remain the result authority.

## Evidence

- Expected durable artifact surface: `benchmarks/arena/`,
  `docs/research/methodology/`, `algorithms/`.
- Required evidence: reproducible run commands, retained challenge and
  algorithm identities, raw multidimensional samples, and independent verifier
  outcomes for every measured stage.
- `benchmarks/arena/analyze.py` admits and compares version-one JSON studies.
  The synthetic regressions under `benchmarks/arena/tests/test_analyze.py`
  exercise exact cohorts, conditional Pareto fronts, failed-trial retention,
  huge exact medians, descriptive dispersion, failure-inclusive elapsed costs,
  deterministic ordering, paired baseline win/loss and failure categories,
  forged verifier status, mismatched verifier cohorts, invalid objective data,
  and fail-closed CLI output.
- `benchmarks/arena/evidence.py` binds reported observations to the governed
  experiment-manifest run parser and to nonempty repository-local raw files.
  Synthetic regressions reject forged profile, challenge, oracle, algorithm,
  workload, host, outcome, and raw path identities; unsafe/missing file links
  and malformed/oversized manifests fail closed.
- `benchmarks/arena/raw_samples.py` optionally matches retained CSV content
  exactly against the reported trial set. Synthetic regressions cover missing,
  extra, duplicate and mismatched rows, plus malformed CSV inputs.
- `benchmarks/arena/trial_runs.py` admits a versioned per-trial manifest
  extension under strict opt-in preflight. Synthetic regressions check
  distinct trial-run bindings, raw-file digests, complete shared CSVs, malformed
  trial/schema metadata, aggregate-manifest reuse, and fail-closed CLI output.
- Version-two `arena-raw-v2` optionally carries per-trial `energy_uj`
  without changing v1 headers. Synthetic tests prove exact energy Pareto
  comparison and rejection of cross-version omissions, forged costs and
  impossible signed energy reports, not measured energy savings.
- An explicit offline binary-rebuild mode compiles canonical source and
  native oracle harness anew for each distinct challenge/Clang mode, comparing
  actual bytes to every retained verified executable. Adversarial tests show
  a matching forged executable SHA-256 is insufficient without independent
  reproducibility; fresh compiler failures also fail closed.
- Post-run source-commit admission compares the exact claim across all
  recorded run manifests and optionally checks that Git can resolve it to a
  real local commit object. Tests include divergent manifests, collectively
  forged missing revisions, and clean historical commit replay.
- The host-C reference runner and post-run auditor now bind a version-one
  `failures.json` sidecar to every reported failed trial, retaining printable
  bounded stage diagnostics alongside all-attempt elapsed costs. Injected
  failures and missing, forged, and invalid diagnostic records fail closed.
- `benchmarks/arena/reference_audit.py` independently reopens retained
  local host-C studies, checks the strict manifest/raw/challenge path and
  binary evidence, then reports the observed frontier without remeasurement.
  Optional canonical host oracle replay is separate. Real-study tamper tests
  reject drift in raw CSVs, run manifests, challenge oracles, binary hashes,
  stage identities, and malformed artifact indices.
- `benchmarks/arena/reference_study.py` records real pinned host-C reference
  time, native executable sizes, exact binary hashes and versioned trial files
  across multiple canonical difficulties and matched `-O0`/`-O2` arms.
  Live and injected-failure tests verify complete run/raw/challenge identity
  linkage and preserve failed attempts; this is not Malbolge performance.
- Host-C reference measurement now uses GNU `time` per direct stage to
  report exact `peak_rss_bytes` (maximum observed Linux `ru_maxrss` after
  KiB-to-byte conversion), retained as a third Pareto cost. Invalid, zero,
  oversized or missing stage readings fail closed; old measurements retain
  their original two-cost analysis. RSS receipts now use the bounded ordinary-
  file admission reader; a link, FIFO, malformed extra whitespace or a
  claimed peak above the configured per-child address-space limit rejects.
  Receipt consistency does not authenticate the kernel measurement source.
- The host-C reference producer now retains version-two Linux child-limit
  policy metadata and blocks new studies when its limiter is unavailable.
  The offline auditor strictly compares the resource-control sidecar to the
  configured process limits; the opt-in required mode rejects old pilots
  missing that metadata and tampering tests cover changes, missing fields,
  linked leaves, schema type drift and corrupted JSON.
- Linux host-C children now inherit kernel-enforced `RLIMIT_AS`,
  `RLIMIT_CPU`, and `RLIMIT_FSIZE` under util-linux `prlimit`, with separate
  process-group wall-timeout cleanup. Real subprocess tests exercise limits,
  successful and timed-out descendants, and unavailable resource tools;
  these controls do not cover aggregate system resource consumption.
- `benchmarks/arena/host_c_oracle.py` optionally compiles canonical
  generated C through pinned Clang at `-O0` and `-O2` and independently checks
  the native entry return against its regenerated four-byte oracle. All 16
  active challenge families pass real replay tests; injected wrong entry
  results, compiler stages, source mutations and oversized batches fail closed.
  The subprocess gate explicitly does not execute a compiler candidate.
- `benchmarks/arena/challenge_bundles.py` optionally replays the original
  generator's exact source/oracle/manifest bytes against a bounded retained
  challenge bundle, binding workload digests to reproducible C source. Synthetic
  regressions cover missing and altered files, canonical profile and difficulty
  identities, unsafe paths, repeated-trial digest drift and fail-closed CLI.
- One end-to-end synthetic admission test composes strict per-trial run
  identity, exact resource declarations, v2 energy CSV, matched reported
  accelerator identity, and deterministic challenge regeneration. Independent
  negative oracle and raw-digest mutations fail before report publication.
- `benchmarks/arena/report_output.py` checks exact text-write character
  counts and flush status on both arena CLI reports. Deterministic broken
  writer fixtures reject short/overstated/malformed counts and flush errors,
  distinguishing nonzero operator failure from impossible stdout rollback.
- `benchmarks/arena/study_file.py` guards bounded study JSON input with
  before/after descriptor and pathname identity, and nonblocking/no-follow
  open flags when available. Deterministic race regressions check ordinary
  replacement, FIFO/link substitution, file rewrite, short reads and both
  fail-closed CLI paths. File-stream constructor faults retain a typed rejection
  and original cause, close the untransferred descriptor, and preserve a failed
  cleanup only as secondary evidence; neither CLI emits a report on failure.
- The retained evidence file reader applies the same descriptor ownership rule:
  injected stream-constructor exceptions have a typed evidence rejection,
  release the raw descriptor, and preserve any cleanup error as secondary
  diagnostics without replacing the original failure. Evidence admission still
  checks observable file identity only, not an atomic filesystem snapshot.
- `benchmarks/arena/multiplicity.py` optionally applies exact study-wide
  Holm-Bonferroni multiplicity correction, preserving every raw probability
  and excluding null hypotheses from the family count. Synthetic reference,
  cross-difficulty, tie-order, and fail-closed CLI tests validate this policy.
- `benchmarks/arena/paired_exact_tests.py` computes unadjusted exact
  two-sided conditional-binomial p-values for the distinct verified-outcome
  and both-success cost-sign hypotheses. Independent `math.comb` references
  check directional symmetry, empty comparisons, ties, extreme counts, and
  exact fractions; CLI and cohort tests retain default compatibility.
- `benchmarks/arena/success_intervals.py` inverts exact binomial tails to
  conservatively round two-sided 95% Clopper-Pearson success-rate bounds
  outward to fixed rational grid endpoints. Independent exhaustive tail
  references cover extremes, symmetry, invalid inputs and large sample limits,
  and both CLI paths preserve default report behavior.
- `benchmarks/arena/median_intervals.py` computes exact 95%-or-higher
  symmetric-rank intervals using binomial coverage, with independent reference
  tests for small/large samples, ties, negative costs and sample bounds.
  Malformed, noninteger cost inputs yield no inferential interval instead of
  numeric endpoints or leaked sorting errors.
  Both analyzer CLIs expose this as an optional view only; default reports and
  existing frontier rankings remain unchanged.
- An additional opt-in accelerator identity gate rejects mixed declared
  devices in studies that require hardware-matched arms, while preserving
  heterogeneous studies when that policy is not requested. Synthetic tests
  cover both cases and fail-closed CLI output.
- A shared bounded file reader now compares path and descriptor identity,
  size and timestamps around manifest/raw/challenge/historical evidence reads.
  Synthetic tests reject an opened-file substitution and an in-place rewrite.
  Evidence reads now consume all observed inode bytes in bounded chunks,
  admitting ordinary short reads but rejecting premature EOF or overlong/nonbyte
  chunks before hashing or parsing a retained run, CSV, or challenge bundle.
  Stable inode metadata alone cannot authorize a valid-looking file prefix.
  File-stream read exceptions (including malformed custom stream failures)
  retain a typed evidence rejection and the original failure cause, so an
  audit cannot accidentally bypass its declared failure boundary.
- `benchmarks/arena/budget_links.py` optionally requires exact resource
  budget declarations from each linked run, rejecting missing/forged integers,
  unit mismatches, and one-unit study drift with fail-closed CLI regressions.
- `benchmarks/arena/historical_pairs.py` replays the two retained classic
  five-pair research sources into arena reports. Source-backed regressions
  assert exact observed medians, paired results, fingerprints, and rejection
  of corrupted raw timing, verifier counts, or preregistered identities.
- `benchmarks/arena/pyrightconfig.json` runs a separate standard-level
  BasedPyright check over the arena package, which is not part of the root
  repository's selected strict Pyright source roots. This complements pinned
  Ruff checks without changing shared tooling policy.
- Research evidence pending: raw sample content authentication,
  protocol-level manifest linkage, bibliography-backed context, real experiment
  configurations, retained negative/null results, and a reviewed conclusion
  with threats to validity.
- Performance evidence pending: raw measurements plus a reproducible
  scaling/statistical summary tied to exact workload and hardware/software
  identity.

## Results

The offline comparison implementation and synthetic regression evidence
exist. The historical adapter additionally projects already-retained host
measurements from the two classic research records above without generating
new samples. Its tests establish replay and cross-record consistency, not
original semantic correctness. No new capacity-scaling result is claimed.

## Threats to Validity

The default analyzer verifies structure, cohort matching, and reported
outcome consistency, but cannot establish that the named verifier ran or that
referenced samples and manifests exist. Opt-in linked-run preflight checks
manifest identities and nonempty sample presence, without verifying their
content or physical execution. It cannot establish actual resource budget
enforcement (only reported overages fail admission).

Median costs conditional on success can hide how long failed runs took;
verified counts remain a separate Pareto objective. For real experiments,
implementation bias, workload selection, hardware variation, truncated trials,
and insufficient replication remain threats.

## Conclusion

Open. The offline comparison slice is implemented; authentic evidence intake,
real stage measurements, protocol-level resource accounting, and reviewed
research conclusions remain. No technique is promoted to product architecture
until independently admitted evidence supports it.

## References

- [Parametric Multi Objective Algorithm
  Evaluation](../adr/parametric-multi-objective-algorithm-evaluation.md)
- [Research Evidence And Algorithm
  Mirror](../adr/research-evidence-and-algorithm-mirror.md)
- [Verification Trust
  Boundary](../../technical/adr/verification-trust-boundary.md)
