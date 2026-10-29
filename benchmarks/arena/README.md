# Algorithm Evaluation Arena

This directory owns cross-algorithm evaluation definitions and reproducible
comparison reports. Capacity curves and multi-objective Pareto frontiers take
precedence over any convenience score. The standalone **analyzer** is offline
and cannot certify submitted evidence; separate bounded host-C and classic
target-reference producers now record real, narrowly scoped experiments.

## Analyze retained observations

Run with the repository-pinned Python interpreter:

```sh
python3.14 -B benchmarks/arena/analyze.py path/to/study.json
```

The command prints deterministic JSON, or exits with code 2 without a report
when admission or comparison fails. Its input limit is 16 MiB. Version-one
input has one `study` and a nonempty `observations` array:

```json
{
  "schema_version": 1,
  "study": {
    "id": "study-identity-v1",
    "question": "Does B improve time without increasing code size?",
    "hypothesis": "B has a better time/size frontier than A.",
    "baseline": "A",
    "rejection_observation": "B is dominated or fails verification.",
    "stage": "ternary-ir",
    "target_profile": "malbolge-2026",
    "host": "reviewed-host-identity",
    "toolchain": "reviewed-toolchain-identity",
    "budget": {"time_ns": 1000000000, "memory_bytes": 104857600},
    "objectives": ["elapsed_ns", "artifact_bytes"]
  },
  "observations": [
    {
      "algorithm": "A",
      "case": {
        "family": "arithmetic-dag", "version": 1,
        "difficulty": 1, "seed": 7,
        "workload_sha256":
          "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
      },
      "trial": 0,
      "outcome": "verified",
      "verifier": "independent-verifier-v1",
      "verifier_verdict": "accepted",
      "experiment_manifest": "algorithms/example/experiment.toml",
      "raw_sample": "algorithms/example/out/samples.csv",
      "metrics": {"elapsed_ns": 1000, "artifact_bytes": 4096}
    }
  ]
}
```

This is **an illustrative schema example, not a benchmark result**. A real
comparison needs matched observations from at least two algorithms and the
baseline. All algorithms in each family/version/difficulty cohort must include
the same `(seed, workload_sha256, trial)` combinations and the same named
verifier for each matched case. Duplicate trials,
unknown metrics, absent declared successful-run costs, mismatched cohorts,
noncanonical paths, unsupported outcomes, malformed JSON, and an algorithm
claiming to have verified its own successful output are rejected.

Currently recognized costs are `elapsed_ns`, `artifact_bytes`, `runtime_steps`,
`peak_rss_bytes`, `peak_vram_bytes`, `verifier_ns`, and optional `energy_uj`.
The energy metric is an exact nonnegative integer number of microjoules,
recorded only when a trustworthy measurement is available. All costs are
minimized; the number of verified trials is maximized. A claimed `verified`
outcome needs a separately named verifier and an `accepted` verdict. Failures
retain their own outcomes (`verifier_rejected`, `no_solution`,
`resource_exhausted`, or `tool_failed`) and at least an elapsed duration.

## Optional linked-run evidence preflight

The standalone analyzer accepts reported records without opening referenced
files. For a stronger **identity-only** preflight, run from the repository root
with the repository-owned validation modules on the Python import path:

```sh
export PYTHONPATH=src/automation/repository/composition
python3.14 -B -m benchmarks.arena.evidence path/to/study.json --root .
```

This optional entrypoint parses each referenced experiment run through the
existing `scripts.validate.experiment_manifest.parse_manifest` authority. It
matches algorithm ID, challenge family, difficulty, seed, target profile,
reported workload SHA-256, host, toolchain, oracle, outcome, and raw-output path
against the arena record. Only bounded regular manifest files and existing,
nonempty raw samples under the supplied root are admitted; symlink hops,
missing artifacts, and identity drift fail closed.

Both arena CLI entrypoints publish completed JSON reports through a
single-record checked text writer. A valid `write()` must return the exact
character count, not a boolean, absent value, short count or overstated count,
and a successful `flush()` must follow before the command returns zero. Writer
and flush failures now produce nonzero operator exits with a diagnostic.
An already-emitted prefix on a failed output stream **cannot be rolled back**;
this is a reliable success/failure signal, not atomic stdout publication.

Both arena CLI entrypoints now read the caller's study JSON through a
bounded descriptor-owner. It checks the initial regular-file metadata against
the opened descriptor, then rechecks device/inode/size and nanosecond
modification/change timestamps before and after the read. Where available,
nonblocking/no-follow open flags prevent a raced FIFO or linked leaf from
turning a previously admitted regular path into a blocking or redirected read.
A replaced input or prematurely ended read fails before publishing any report.
Legitimate partial reads are accumulated to the inode's admitted byte length;
nonbinary/overlong chunks and read-stream failures reject without a report.
These checks defend against observed races but do not provide a filesystem
snapshot or authenticate the source. The caller must establish provenance.

Arena evidence file readers now check regular-path and opened-descriptor
identity, size, and modification/change timestamps before and after
bounded reads, including a post-read ancestor-link admission. A replaced
path, a substituted inode, or an observed same-inode rewrite fails before an
aggregate report is
published. POSIX descriptor opens use nonblocking and no-follow flags when
available, so a raced FIFO or leaf symlink cannot hang the source reader.
These are observable race defenses, **not** a promise of an atomic filesystem
snapshot or authenticated source provenance.

The identity-only output includes `evidence_preflight` counts. A stronger,
optional raw-row check is documented below; neither mode runs the independent
semantic verifier.

## Optional host-C challenge-oracle replay

The evidence-aware CLI can additionally *execute* the canonical challenge C
source to cross-check its independent four-byte oracle. This is an explicit
operator opt-in, not a default admission condition:

```sh
export PYTHONPATH=src/automation/repository/composition
python3.14 -B -m benchmarks.arena.evidence path/to/study.json --root . \
  --challenge-root path/to/challenge-bundles \
  --require-host-c-challenge-oracle
```

The `--challenge-root` prerequisite is mandatory. All retained
`program.c`, `oracle.bin`, and `manifest.json` files must first pass exact
regeneration, SHA-256, profile, and canonical-file admission; the host oracle
checker then regenerates the same source in memory. It never compiles a
caller-provided candidate program or follows a reported candidate-artifact
path. The repository-pinned LLVM 22.1.8 Clang compiles that source at both
`-O0` and `-O2`, links a small separate entry-function harness, and executes
each result to compare the complete 32-bit return value with `oracle.bin`.
The generated program's standalone `main` is not used for oracle comparison.

A host replay covers at most 16 distinct cases of at most 512 nodes each;
each compiler, linker and executable child has a 15-second timeout. The mode
requires an available pinned compiler and the repository's `.temp/` workspace;
all temporary objects/executables are removed on completion or failure. The
output adds `host_c_challenge_oracles_replayed`, `host_c_replay_modes`, and
`host_c_replay_source_sha256` under `evidence_preflight`. An error or timeout
fails admission without emitting a capacity/Pareto report. Without the new
flag, no host compiler subprocess is launched and previous outputs are
unchanged.

**Scope:** This checks the generator oracle against separate native C
execution on the recorded host, at two optimization levels. It does *not*
execute or independently verify **either compared algorithm's output**, nor
does it prove Malbolge semantics, sampling independence, resource-budget
enforcement, hardware utilization, or real performance measurements. Host
compilation and execution are not an OS-enforced sandbox, so operators must
keep the trusted checked-in generator and pinned compiler within their trust
policy. Full compiler-candidate verification remains open.

## Bounded measured classic Malbolge target reference

A first, strictly bounded **real-target** study now runs the checked-in
`malbolge_layout` executable and the independent general `malbolge` VM runner
on two classic-profile code layouts. Both execute the same empty-input
EOF-byte echo (one `0xA8` byte per input/output pair); the candidate prepends
one inert `nop` per pair. This compares address-sensitive native Malbolge
**source bytes and measured emission-plus-execution elapsed time**, not C
lowering or guest runtime throughput. It measures emitted executable text
length, not capsule framing or memory footprint.

From the repository root, build the two product executables using the pinned
Cargo toolchain, then run:

```sh
export PYTHONPATH=src/automation/repository/composition
python3.14 -B -m benchmarks.arena.target_echo_reference \
  --pairs 1 4 16 --trials 2
```

The study requires repository-local built executables under
`.cache/rust/target/debug/`, an existing `.temp` root, and an explicit
canonical `malbolge-1998` profile. It rejects zero, duplicate, invalid or
more than four difficulty levels; each level has between 1 and 64 echo
pairs, with one to three repetitions. The two arms alternate execution order
by repetition to reduce (but not eliminate) order bias. Each executable child
has a 15-second wall timeout. The target process boundary now uses a
POSIX-isolated child session and concurrent selector-based pipe reads with
explicit **4-KiB stdout** and **16-KiB stderr** hard limits. It rejects an
additional byte on either stream, a cumulative wall timeout, and
ordinary pipe-retaining descendants. Cleanup signals the original isolated
process group and reaps the direct child; detached descendants and any
physical memory or CPU budget enforcement remain outside this claim.
The runner checks complete stdout against the expected bytes; mismatches
remain `verifier_rejected`, and launcher failures, stream overruns and
child timeouts remain `tool_failed`, never credited as successes. It also
checks exact source length, graphical byte domain, the per-attempt output
path, and exact
executable identity before/after the study.

New studies retain `study.json`, actual raw graphical `candidates/*.malbolge`,
one per-attempt `arena-raw-v1` CSV and versioned experiment-run TOML, under a
unique Git-ignored `.temp/arena-target-echo-*/` directory. Their raw-byte
hashes, declared resource budgets and per-trial identity are re-admitted
through the normal arena evidence boundary, followed by a matched-cohort
capacity/Pareto analysis. The CLI prints the local study path, not a
performance verdict. An independent caller can inspect the resulting file:

```sh
python3.14 -B -m benchmarks.arena.analyze \
  .temp/arena-target-echo-EXAMPLE/study.json
```

Every newly produced classic target study now passes a distinct post-run
read-only source audit **before** its command can publish a successful study.
The audit independently decodes each retained graphical byte using the frozen
classic XLAT1 table and its exact source position, requiring the claimed
input/output/no-op/halt sequence. Reported sizes and raw-file hashes alone do
not satisfy this check. It additionally requires the producer's fixed study
question, stage, budgets, case identities and paired trial plan; exact
manifest/raw/candidate path inventory; identical reported source revision
across run manifests; and strict run/raw/budget links. It rejects foreign
producer declarations and unrecognized or linked candidate files. Successful
source digests are derived from inspected bytes; failed trials remain visible
but their historical failures are **not** reproduced or authenticated.

Audit any retained bounded classic target study without launching an external
process:

```sh
python3.14 -B -m benchmarks.arena.target_echo_audit \
  .temp/arena-target-echo-EXAMPLE/study.json
```

Every offline audit also pins the original study JSON, run TOML and raw
CSV bytes before cross-record admission, then reopens and compares every
fingerprint before returning a report. A final run/raw/candidate inventory
rescan rejects late additions and substitutions. These checks cover every
bounded retained trial input, including changes that leave files parseable.
They do not supply an atomic filesystem snapshot or source attestation.

To **opt in to a new VM execution** of every retained successful source, use
`--replay-candidates`. Replay requires the current local `malbolge_layout` and
`malbolge` executable bytes to match the jointly recorded SHA-256 toolchain
fingerprint. It checks exact EOF output again and reopens each source after
execution to reject observed source changes. The auditor also reopens each
successful source immediately before returning its report. This catches
observed mutations between decoding and result construction. VM replay does
not prove the original benchmark used those executable bytes, independently
verify arbitrary programs, reproduce recorded times or replay failed trials.
If binaries were rebuilt, offline source admission remains available, while
VM replay rejects the toolchain drift until original binaries are recovered.
Opt-in replay uses the same bounded POSIX subprocess transport, so a hostile
or broken VM cannot produce unlimited buffered output before rejection.

The separate `--require-source-commit-object` option also asks local Git to
resolve the identical source revision claimed by every run manifest to an
actual **commit** object. It rejects missing, foreign-type or unavailable
objects without changing the default offline audit. This confirms only that
the recorded Git object exists locally; it does not authenticate historical
execution, prove the worktree was clean, or verify a cryptographic signature.
The lookup clears inherited `GIT_*` environment overrides so ambient object
or repository selectors cannot substitute another local Git database.
Both opt-in switches may be combined on the same command.

The exact executable hashes and Git revision are recorded as **claimed
provenance**, not execution attestation. The declared 60-second/1024-MiB
study budget is not physically enforced in aggregate; individual child wall
timeouts do not establish peak resident memory. Wall-clock samples include
process startup, source emission, loading, and VM termination, and should not
be interpreted as a calibrated throughput or a speedup claim. The EOF oracle
checks only this narrow classic I/O behavior, not general computation or
modern-profile control flow. This is the first measured `.malbolge` stage in
the arena, **not** verification of the general C-to-Malbolge compiler, and
no production strategy is selected from these observations.

## Actual host-C reference study (not Malbolge performance)

For a small **real measured host-C baseline** over at least two parametric
challenge difficulty levels, use this opt-in runner:

```sh
export PYTHONPATH=src/automation/repository/composition
python3.14 -B -m benchmarks.arena.reference_study arithmetic-dag \
  --difficulties 4 8 32 --seed 7 --trials 3
```

The reference runner's operator JSON summary now uses the same checked
single-record text publisher as the arena analyzer: a complete write count
and a successful stdout flush are mandatory before it returns code zero.
A failed stream returns code two even if validated ignored study files have
already been retained; emitted stdout fragments cannot be rolled back.

The tool runs repository-pinned Clang 22.1.8 at `-O0` and `-O2` for each
matched case/replicate, compiling the canonical regenerated C, linking the
independent entry-return harness, and executing the native program. It records
actual `perf_counter_ns` elapsed time for compile + link + oracle execution,
plus native executable byte length and kernel-observed maximum direct-child
resident memory, retaining failures rather
than synthesizing costs or treating a failed run as verified. It saves
`study.json`, one `arena-raw-v1` CSV and run TOML per trial, all three canonical
challenge bundle files, an `artifacts.json` map, and the exact compiled
executables and their SHA-256 identities in a unique **Git-ignored**
`.temp/arena-host-c-study-*/` directory. The tool's JSON stdout reports the
study path and the number of observations, not an authoritative conclusion.
Before publishing the local study, the producer also reopens every retained
successful native executable through the arena's bounded non-symlink file
reader, checks its path against the originating trial, and independently
compares its SHA-256 and exact byte size with the reported artifact metadata.
Missing/extra artifacts or forged success-size associations fail closed.
This is file-to-report integrity only; no independently authenticated
compiler optimizer output or resource measurement is implied.

Each new study also retains a version-one `failures.json` sidecar. Every
`tool_failed` attempt carries exactly one entry keyed by its run-manifest
path, with the sanitized compiler/linker/oracle diagnostic bounded to 256
printable ASCII characters. No child stderr dump or unrelated host state is
published. The producer checks that diagnostic keys match failed attempts
and that successful ones never claim failure records. Post-run audit checks
the exact same relation and rejects missing, extra, malformed, nonprintable
or overlong entries. Earlier all-success studies with no `failures.json` remain
admissible; if any failed trial exists, the sidecar is required. The text is
**source-reported failure context**, not an independently rerun failure or
proof that a compiler crashed in the claimed way.

The run manifest records the current Git commit, host, toolchain, target-profile
fingerprint, source digest, raw-data SHA-256, explicit budget declarations, and
exact trial number. The producer rechecks every emitted trial with the arena's
strict raw-row, run-identity, budget and challenge-bundle preflights.

To audit a previously saved local reference study **without rerunning its
measurements**, use the independent read-only inspector:

```sh
python3.14 -B -m benchmarks.arena.reference_audit \
  .temp/arena-host-c-study-EXAMPLE/study.json
```

It only admits canonical `.temp/arena-host-c-study-*/study.json` paths and
requires the exact host-C stage, Clang `-O0`/`-O2` arms, verifier, declared
budget, profile, source study identity, and bounded trial/difficulty structure.
Manifest and raw-sample names must also match the producer's exact
`<algorithm>-nodes-<difficulty>-trial-<trial>` stem, not just the containing
`runs/` or `raw/` directories. Renaming all related evidence consistently
cannot satisfy the producer's trial-name convention. The fixed native
reference study question, hypothesis and rejection observation must also
match those emitted by its producer; the generic analyzer permits other
research questions for unrelated experiments.
Every difficulty must contain the identical consecutive trial indices from the
one native producer plan; merely balancing the two algorithms within each
level is insufficient. The generic arena analyzer still admits unequal sample
sizes across difficulty levels for other independently produced studies.
It rechecks canonical challenge-bundle regeneration, all versioned run
manifests, raw rows/digests, declared budgets, and each retained executable's
SHA-256, path and recorded byte length before reporting the capacity curve
and Pareto frontier. Its artifacts, failures and resource-control JSON readers
reject duplicate keys (including nested keys), nonfinite numbers, and parser
recursion failures instead of silently accepting ambiguous receipts.
Missing, altered, symlinked and malformed inputs fail without a report. By
default no host compiler, benchmark or native binary is executed.
`--replay-oracles` separately compiles and executes **only** the
canonical generated challenge C at both optimization modes; it never runs a
retained trial binary. For a stronger **same-host source-to-executable** check,
add
`--rebuild-binaries` to the offline audit. After all files and reported hashes
pass, it independently recompiles the canonical regenerated C and its oracle
harness through pinned Clang for each distinct challenge/optimization mode.
The newly compiled executable must match **every** corresponding retained
successful native executable byte-for-byte. Rebuilding once per identical
source/arm avoids duplicate work across repetitions. This catches a forged
retained binary even when its `artifacts.json` SHA-256 is updated to match.
Rebuilds use new temporary files and run only the fresh canonical C harness;
**retained executables are never launched**. The audit reports the distinct
`host_c_reference_builds_reproduced` count, zero unless explicitly enabled.
Deterministic executable bytes depend on the same pinned linker, libraries,
ABI and host environment; a later changed toolchain may fail exact replay
without implying a historical result was dishonest. This is reproducibility
of host-C output bytes, not independent Malbolge verification.

The post-run audit also requires every distinct trial manifest to report the
**same source Git revision**, rather than accepting individually unrelated
40-hex commit labels. The report retains `recorded_source_commit`; add
`--require-source-commit-object` to check that the claimed revision exists
as a Git **commit** object in the selected local repository. This is opt-in
because shallow clones and archived studies might not retain the object.
An existing object proves neither that the benchmark executed those exact
sources nor that its host/toolchain or measurements were authenticated.

The audit now also requires each recorded run's method class, implementation,
configuration, output root, and accelerator declaration to match the fixed
host-C reference producer. This prevents a self-consistent but foreign TOML
provenance declaration from being described as the reference runner's output;
it does not authenticate the underlying machine, source or execution.

The strict producer audit also has real native source/rebuild regressions
for `composed-pipeline`, `ternary-fold`, `pointer-walk`, and `alias-walk`, each
with canonical oracle replay and retained-file immutability assertions. These
expand the tested generator families, not the scope of performance conclusions.

The audit never proves that reported wall-clock
measurements were authentic, that resource limits were enforced, or that
candidate Malbolge artifacts were created or verified. File consistency is
not an atomic snapshot against concurrent filesystem mutation.

The limits are one to four positive distinct difficulties, 512 nodes per case,
and one to five paired repetitions. Native child compile/link/execute each have
a 15-second deadline; per-run declared budget is 60 seconds and 1024 MiB.
Linux host-C compiler, linker, and oracle children now run through util-linux
`prlimit` in their own POSIX process sessions, with kernel-enforced
**per-child**
limits of 1024 MiB of **virtual address space** (`RLIMIT_AS`), 16 seconds of
CPU time (`RLIMIT_CPU`), and 8 MiB per output file (`RLIMIT_FSIZE`). Each
stage also has a parent-enforced 15-second wall deadline; the runner attempts
to terminate the entire session's original process group after each child,
including on timeout. Missing Linux/prlimit refuses to launch an unbounded
fallback. Newly produced studies retain a version-two
`resource-controls.json` declaring those exact per-child ceilings, Linux
`prlimit` launcher, process-group cleanup mode, local wall deadline and
GNU `time` maximum-RSS measurement method.
The producer refuses to create a new study if the limiter or RSS measurement
tool is unavailable.
The post-run auditor reads this bounded nonlinked JSON and requires exact
field names, value types and policy equality; it reports
`resource_controls_record_checked` as `true` or `false`. Add
`--require-resource-controls-record` to reject older studies with no such
receipt. The original ignored pilot predates enforcement and remains readable,
but cannot claim this receipt, even if newly rebuilt reference binaries use
the current child limits. Version-one receipts from earlier controlled pilots
remain readable for their original two-cost comparisons; a claimed new RSS
objective requires a version-two measurement receipt. A matching producer
record is **not** proof of historical enforcement or memory attribution.

Linux process-group cleanup and inherited rlimits are not cgroup
isolation: escaped process groups, aggregate multi-process RSS/CPU budgets,
the Python producer's work, and aggregate physical peak memory remain
unaccounted for. The declared 60-second/1024-MiB study budget is **not** an
aggregate physically enforced limit. On successful host-C references, GNU
`time` supplies `ru_maxrss` in Linux KiB for each direct compile, link and
oracle child; `peak_rss_bytes` is the maximum of those three values converted
to bytes. The maximum includes child wrapper overhead but does **not** measure
simultaneous descendant memory, Python producer memory or GPU usage. New
capacity curves and Pareto frontiers include RSS as a third declared cost;
older two-cost studies retain their original meaning. Generated source and
the reference oracle use the canonical `malbolge-2026.3` profile identity,
but native execution targets the
host C ABI. The recorded study stage is explicitly
`host-c-reference-not-malbolge`; do **not** treat it as Malbolge compiler
output, verified Malbolge semantics, independent optimizer correctness,
study-wide resource enforcement, or evidence that one strategy is faster.
The study files stay local/ignored and require host-specific review before
publication. Unverified independence assumptions preclude inferential claims.

## Optional version-one raw CSV check

Add `--require-raw-rows` to the `benchmarks.arena.evidence` command to verify
retained CSV contents against every reported observation. The fixed
`arena-raw-v1` CSV header begins with `schema_version`, `algorithm`, `family`,
`version`, `difficulty`, `seed`, `workload_sha256`, `trial`, `outcome`,
`verifier`, and `verifier_verdict`. It ends with `artifact_bytes`, `elapsed_ns`,
`peak_rss_bytes`, `peak_vram_bytes`, `runtime_steps`, and `verifier_ns`.

Each row has the literal schema version `1`, canonical nonnegative integers,
and exact reported identity and metric values. Missing optional metrics use
empty cells, distinct from zero. All referenced rows must be present exactly
once, with no extra rows, even when several trials share one file. Each CSV
is limited to 16 MiB. The report adds a SHA-256 digest per inspected raw file.

A separate `arena-raw-v2` schema adds the `energy_uj` CSV column in the
alphabetical metrics sequence (after `artifact_bytes` and before `elapsed_ns`),
with `schema_version` set to the literal `2`. The complete version-one header
and spellings remain unchanged. A v1 raw file **cannot** support an energy
measurement even if JSON claims one: such a link fails closed rather than
dropping the extra metric. Version-two files may omit an unmeasured energy
metric using an empty cell; a declared `energy_uj` study objective requires a
value for every verified result. Trials with unknown energy must not acquire
invented zeroes or estimates. Both formats use the same 16 MiB file limit,
complete-row matching, and SHA-256 source-byte evidence checks.

This strengthens **report-to-file consistency**, not the trust in the file's
producer. It does not replay a verifier, prove hardware measurements, or
authenticate a Git commit; real conclusions still require separate validation.

## Interpretation and trust boundary

The `capacity_curve` reports attempts, verified attempts, exact success
fractions, failure counts, and the median of **successful** samples for each
objective. A median is `[numerator, denominator]`, not a rounded float.

It also reports `median_absolute_deviation` (unscaled median absolute
deviation) and `successful_range` (minimum and maximum) for every declared
cost, conditional on verified success. Missing successes yield null
conditional statistics, not fabricated zeroes. The `all_attempt_elapsed_ns`
record reports exact median, median absolute deviation, and observed range
across **every** attempt, including rejection, exhaustion, and no solution.
These statistics alone are descriptive, not confidence intervals or proof of
independent trials. For a separate optional inferential view, run the analyzer
or the evidence-aware CLI with `--median-intervals-95`. It adds exact
nonparametric order-statistic intervals to each conditional successful cost
median, the all-attempt elapsed median, and each paired baseline cost-difference
median when at least six and at most 4096 observations are present. Smaller or
larger samples produce `null`, never fabricated bounds or extrapolated data.

Each available interval reports integer `lower`/`upper` sample endpoints,
`sample_count`, and achieved two-sided binomial coverage as an exact rational
`[numerator, denominator]`. The target is at least 19/20 (95%); coverage can
exceed 95% because finite-sample order statistics have discrete ranks. The
chosen ranks are the narrowest *symmetric-rank* interval meeting that target,
without any floating-point approximation. For distributions with ties, the
reported coverage is a conservative lower bound rather than an exact achieved
probability. The calculation requires **independent, identically distributed**
replicates for inferential interpretation. The arena cannot establish that
assumption from trial labels, seeds, reported digests, or a matching verifier.
An all-success subset targets the **conditional** cost median of successful
trials only; paired differences require **both** arms to verify. None of these
intervals measures algorithm success probability or covers failure cost
without such qualification. They do not change the exact descriptive medians,
Pareto frontier, success counts, or capacity maxima, and do not establish
statistical significance, verifier execution or physical measurements. The
`median_interval_policy` report object records the assumptions and bounds;
without the opt-in flag, all earlier version-one report fields and values stay
unchanged. Statistical uncertainty and replication remain governed by the
benchmark protocol before any research conclusion is accepted.
`pareto_frontiers` compares verified-count and successful-only median costs
within an exactly matched difficulty cohort. Algorithms without a verified
trial remain in the curve but cannot enter the conditional frontier.

The secondary `paired_baseline_comparisons` reports each candidate against
only the declared baseline for every difficulty cohort. It counts trials where
both verified, only the baseline verified, only the candidate verified, or
neither verified. For each declared cost, it reports candidate-lower, tied,
and candidate-higher counts and the exact median of *candidate minus baseline*
over trials where **both** were verified. A negative signed difference means
lower candidate cost; if there were no mutually verified trials, that median
is null. In the optional interval view, only these *both-success* paired
signed differences contribute to their own conditional median interval.
Paired differences are descriptive and do not replace the Pareto frontier or
establish statistical significance.

For an additional opt-in paired asymmetry view, use `--paired-exact-tests` on
either arena CLI (independently or with `--median-intervals-95`). It adds an
exact two-sided conditional-binomial test for **verified outcome discordance**:
the counts where only the baseline or only the candidate verified. It also adds
a sign test for each cost objective using only *both-verified* matched pairs in
which the costs actually differ (candidate lower versus higher). Same-cost
ties and pairs with a failed arm never enter a cost sign test. No discordant
pairs, or more than 4096 discordant pairs, produce `null` rather than an
invented probability. Every available test reports `discordant_pairs` and an
exact two-sided `p_two_sided` as a reduced rational `[numerator, denominator]`.

These tests use the null assumption of symmetric discordant outcomes,
conditional on the number of such pairs. Valid inference additionally assumes
independent matched trials; the analyzer cannot verify that assumption, or
prove that a reported verifier ran. The probabilities are **unadjusted for
multiple comparisons** across objectives, algorithms, and difficulties. The
arena does not transform an unadjusted p-value into a declaration of
statistical significance or a native-tier promotion decision. This separate
view does not change descriptive outcomes, medians, Pareto frontiers, or
capacity claims. Its `paired_exact_test_policy` block records these limits;
the default version-one output remains byte-for-byte unchanged without the
opt-in flag.

An additional `--adjust-paired-tests` flag, **requiring**
`--paired-exact-tests`, applies a study-wide exact Holm-Bonferroni step-down
family-wise correction to **all available** paired verification-asymmetry and
cost-sign hypotheses from every candidate, objective, and difficulty. It
reports the exact reduced `p_holm_adjusted` rational alongside each unadjusted
`p_two_sided`; null tests do not count toward the family size. The
`paired_exact_test_policy` then records the exact number of tested hypotheses
and the defined study-wide family. The correction uses exact integer fractions
and remains monotone for tied probabilities. Holm can control family-wise
error under arbitrary dependence **provided each individual p-value is valid**.
It does not fix unverified independent-pair assumptions, questionable physical
measurements, or selectively chosen studies. Adjusted probabilities still do
not certify statistical significance or change any Pareto, capacity, or tier
promotion decision. With no opt-in adjustment, the previous unadjusted view
remains byte-identical.

For an optional inferential view of the *reported* success fraction, both
arena CLIs also accept `--success-intervals-95`. It adds a conservative
Clopper-Pearson binomial confidence interval to each capacity point, using
the exact number of reported `verified` outcomes out of **all attempts**,
including failures. Each `verification_success_probability_interval_95`
has `lower` and `upper` reduced rational `[numerator, denominator]` bounds,
plus `verified` and `sample_count`. The underlying exact binomial tail roots
are enclosed by outward rounding to a fixed grid of 1/4096; no floating-point
normal approximation or false claim of exact irrational endpoints is used.
Under independent, identically distributed Bernoulli trials, those bounds
retain at least 95% nominal two-sided coverage. Counts above 512 or empty
cohorts produce `null`, not extrapolated results. In particular, zero reported
successes does **not** mean the true success probability is known to be zero.

The `verification_success_interval_policy` records the grid, maximum samples,
nominal confidence, and the critical unverified **iid sampling assumption**.
The arena cannot authenticate the reported verifier outcome, guarantee trial
independence or physical execution, or infer stochastic reliability from a
conveniently chosen or correlated corpus. The option is independent of median
and paired uncertainty; none of these intervals changes the Pareto frontier,
capacity maxima or promotion decisions. Historical version-one reports retain
the same fields without the opt-in flag.

The `highest_observed_verified_difficulty` is a measured maximum, not an
interpolated difficulty threshold or a proof of monotonic capacity.

The default analyzer enforces schema and comparison consistency only. It
**does not** open experiment manifests, check raw files, rederive a challenge
source digest, or prove work was completed within the declared resource budget.
It rejects reported successful values above the stated time and resident-memory
limits, but it does not check how those values were measured. An independent
semantic oracle and reviewed raw evidence remain prerequisites for performance
claims under the repository benchmark protocol and experiment-identity
contracts.

Input filenames and reported verdicts must not be treated as evidence of
correctness or authenticated provenance. The sample data in automated tests
is entirely synthetic and must never be cited as Malbolge performance.

Run the self-contained regression suite:

```sh
PYTHONPATH=src/automation/repository/composition python3.14 -B -m pytest \
  benchmarks/arena/tests/ -q
```

## Existing retained classic timing studies

Two source-pinned September 4, 2026 research comparisons already contain five
paired repetitions, declared hypotheses, registered verifier identities,
quality-map fingerprints, and nonempty raw timing samples. The read-only
`historical_pairs` adapter admits those two recorded formats as **historical,
source-reported evidence** without executing a candidate or verifier:

```sh
export PYTHONPATH=src/automation/repository/composition
python3.14 -B -m benchmarks.arena.historical_pairs \
  benchmarks/research/evidence/2026-09-04-classic-prefix-decomposition-linux
python3.14 -B -m benchmarks.arena.historical_pairs \
  benchmarks/research/evidence/2026-09-04-classic-verified-block-reuse-linux
```

The adapter reads only canonical, non-symlink research files under the selected
root, with an individual 4 MiB input cap. It reuses the version-one experiment
and benchmark-protocol parsers, requires the exact paired trial population,
checks preregistered baselines, matched workload/host/profile identities,
and compares retained quality-map and structural counts against the recorded
measurement declarations. The independent retained `source-commit.txt` pin
must agree with the experiment-run commit. Only the registered CSV column sets
are admitted. It fingerprints the exact experiment, benchmark, raw and source
commit file bytes in `historical_evidence.source_sha256`.

The prefix-decomposition record has a baseline timing median of 831,921,051 ns
and a candidate timing median of 835,180,632 ns. Prefix decomposition reports
2 of 5 paired timing wins and 8,742 verifier calls instead of 8,836; the
reported timing comparison does not support a speedup claim.

The verified-block-reuse record has a baseline timing median of 1,617,672,749 ns
and a candidate timing median of 851,323,429 ns. Reuse reports 5 of 5 paired
timing wins and 8,836 verifier calls instead of 17,672. Those observations
apply to the frozen corpus and recorded Linux host, not arbitrary workloads.

The two research studies have *different challenge families and difficulty
identities*. They are never pooled into a joint arena frontier. The adapter
compares elapsed time only; it retains the reported verifier-call counts as
separate structural metadata rather than relabeling them as a timing cost.
Every projected trial is **reported verified** from the source manifest and
quality-map identity, not independently re-verified by this adapter. Reports
mark the evidence as `source-reported-not-reverified`. No new
measurements, semantic proof, or capacity scaling claim is created.

## Optional trial-scoped run manifests

The version-one experiment manifest parser admits aggregate run records, so
an identity-only preflight cannot tell whether a second reported repetition
had a distinct recorded run. For an additional *source-reported* per-trial
binding, add `--require-trial-run-identity` to the `benchmarks.arena.evidence`
command. This implies `--require-raw-rows`, whether or not it is explicitly
supplied, and requires each observation to reference a distinct experiment-run
manifest. Each such manifest must retain the governed core run fields and add
this version-one extension:

```toml
[arena_trial]
schema_version = 1
trial = 0
raw_sha256 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
```

`trial` is the exact nonnegative observation repetition index, not the
challenge seed or number of retained repetitions. `raw_sha256` is the
lowercase SHA-256 of the complete referenced CSV file's actual bytes. It
must agree with the inspected `arena-raw-v1` file, whose complete row set
must independently match the admitted JSON observations. A single raw file
may contain several trials, but each run manifest is specific to just one
trial; duplicate manifest references, changed file bytes, unmatched trial
numbers, invalid extension schema, and missing raw evidence are rejected.

A matching recorded digest proves only that a producer-linked manifest and
raw file are consistent. Neither the producer's measurements nor the
reported independent verifier verdict become trusted by this preflight.
Existing research projects with one aggregate run manifest covering multiple
repetitions should continue to use the identity-only or raw-rows checks until
they actually produce source-pinned per-trial run records. Do not split or
fabricate aggregate provenance merely to satisfy the stronger mode.

## Optional declared run-budget agreement

To detect inconsistent *reported* run limits, add
`--require-budget-agreement` to `benchmarks.arena.evidence`. This mode is
independent of `--require-raw-rows` and `--require-trial-run-identity` and
requires the standard experiment run `[budget]` table to explicitly include
positive integer `seconds` and `memory_mib`. Every linked run must declare
limits that match the study's `time_ns` and `memory_bytes` **exactly** after
multiplying seconds by 1,000,000,000 and MiB by 1,048,576. Fractional seconds
or non-MiB-aligned study limits cannot meet this opt-in agreement contract;
they should use a separate, properly versioned timing-unit specification.

This check catches different budget declarations for two algorithms on the
same compared workload, as well as silent unit conversion or rounding drift.
It does **not** prove that the runner enforced either limit or accurately
reported resource use. Neither the ordinary identity-only mode nor legacy
aggregate research evidence is required to carry both budget fields until
this stronger agreement check is requested.

## Scoped type checking

The repository-wide Pyright project currently selects `src/`, `tests/`, and
`verifier/` but not this independent benchmark package. To check the arena's
Python implementation and synthetic regressions without changing that shared
selection, run the pinned checker with the local standard-level policy:

```sh
.dependencies/python/3.14.7/bin/basedpyright \
  --project benchmarks/arena/pyrightconfig.json --threads 1
```

The scoped check covers this package and imports the repository's governed
experiment/benchmark validators. It complements, rather than replaces, the
pinned Ruff checks, synthetic/replayed evidence tests, and Jig validation.

## Optional canonical challenge-bundle replay

The ordinary arena case digest is a producer-reported workload identity, not a
source authentication. For studies using the completed sixteen-family
`benchmarks.challenges.generate` generator, the optional `--challenge-root`
preflight regenerates each **distinct** challenge and compares exact source,
oracle, and canonical manifest bytes to the files retained under a local root:

```sh
export PYTHONPATH=src/automation/repository/composition
python3.14 -B -m benchmarks.arena.evidence path/to/study.json \
  --root . --challenge-root benchmarks/challenge-bundles
```

For a case with family `arithmetic-dag`, version `1`, seed `7`, difficulty
`4`, the caller publishes the three original generated files at:

```text
benchmarks/challenge-bundles/arithmetic-dag/v1/seed-7/nodes-4/program.c
benchmarks/challenge-bundles/arithmetic-dag/v1/seed-7/nodes-4/oracle.bin
benchmarks/challenge-bundles/arithmetic-dag/v1/seed-7/nodes-4/manifest.json
```

This opt-in mode explicitly interprets the arena `difficulty` integer as the
generator's `nodes` parameter and `workload_sha256` as SHA-256 of the exact
`program.c` bytes, not a digest of an unrelated input package. All matched
algorithms and trials citing that case must agree on that same regenerated
source digest. The selected study profile must reproduce the canonical
manifest's profile and fingerprint. Noncanonical files, unsafe links,
unsupported generator families, missing bytes, or identity drift fail before
any arena summary is published. Files are never regenerated **to disk** by
this check: only an in-memory deterministic replay is performed.

The preflight is bounded to 64 distinct challenge identities per study,
4,096 nodes per generated challenge, 8 MiB per C source, 32 KiB per manifest,
and an exact four-byte oracle. Larger research experiments need a separately
reviewed bounded replay policy rather than silently skipping checks. Results
include `regenerated_challenge_bundles` and the checked C source digests in
`challenge_source_sha256`. The historical generic analysis, including other
challenge producers and workloads with a different digest definition, remains
available without this option.

The synthetic integration regression under
`benchmarks/arena/tests/test_challenge_bundles.py` composes **all** optional
preflights on one reproducibly generated source/oracle: full v2 CSV energy
rows, per-trial source-reported raw SHA-256, exact declared run budgets, common
reported accelerator identity, and regenerated challenge workload digest. It
also proves that a mutated oracle or a modified-but-self-consistent raw report
cannot pass the full gate without their corresponding source declarations.
This is a fixture integration test, not a real compiler performance run.

The generator and its oracle can share a common-mode defect, and byte-exact
replay does not establish that the compiler used the retained source, that the
named verifier executed, or that a measured candidate was correct. This
checks **workload provenance**, not measured performance or guest semantics.

## Optional accelerator cohort agreement

The governed experiment run manifests include a reported `accelerator`
identity, which may differ across algorithms even when the study host and
toolchain strings agree. To require the same **declared** accelerator for
every run in a comparison, add `--require-matched-accelerator` to the arena
evidence command. This opt-in mode emits `declared_run_accelerators`, keyed by
canonical manifest path, and rejects mixed accelerator declarations before
publishing any capacity or Pareto result.

The default mode continues to admit cross-device studies (e.g., CPU versus
GPU algorithms), which may be scientifically useful when the experiment
protocol explicitly controls and attributes heterogeneous resources. A common
recorded accelerator string alone does not authenticate physical hardware,
resource utilization, power consumption or actual execution; even matching
labels remain source-reported provenance rather than independent attestation.
