# Source-Bound Diff Generator

## Status

Active. Exact authoring/materialization, generic identity primitives, tree-level
structural/stable-anchor admission, the first language-aware consumer identity
adapter, generic behavior-evidence semantics, a portable bounded process-probe
executor, the first DOOM identity behavior program, and threshold source-bound
key
unlock, RFC 8439 ChaCha20-Poly1305, protected exact-plan materialization, and
standalone std-only Rust emission for the exact baseline are implemented.
Broader DOOM
compatibility/bug probes and compatible-variant admission/placement remain
unfinished.

## Purpose

Define `algorithms/diff/`, a generic generator that learns deterministic
source-tree transformations from a local source/oracle pair and emits a
distributable transform that still requires sufficiently compatible source
material to reconstruct the target.

The engine is generic infrastructure. It must not contain DOOM-specific C
knowledge, source paths, bug lists, or host/runtime policy.

## Scope

- `algorithms/diff/`
- repository-owned synthetic fixtures under `algorithms/diff/tests/`
- thin consumer recipes such as
  `src/research/algorithms/domain/algorithms/doom/generator/quality.py`
- source-bound transform emission and materialization contracts

Application-specific behavior probes and compatibility policy remain with the
consumer rather than inside the generic engine.

## Current Behavior

### Generation Model

Generation has two distinct phases.

During authoring, a local recipe supplies an admitted source tree, local
target/oracle tree, output policy, structural/behavioral thresholds, and an
optional domain module. The oracle is development evidence and is not a required
distributable input.

During materialization, the emitted transform receives a candidate source tree.
Before writing target files it must establish enough compatible source evidence
to
satisfy the recipe policy. It then reconstructs target output from admitted
source plus source-bound transformation material.

Possession of the generated transform alone must be insufficient to materialize
the local oracle.

The public authoring recipe first requires exact host-native `pathlib.Path`
values for source, oracle, generated output and optional domain module; a
caller-defined path subclass cannot redirect source reads or publication before
recipe preflight. Four red-first regressions cover every path role.
The public authoring recipe rejects NUL-bearing or host-unencodable source,
oracle, module, and output paths, as well as NUL-bearing or non-UTF-8 profile
identifiers, before domain preflight or source-tree reads. The generated Rust
output destination must resolve outside both input trees, including through
symlinked aliases, and must not resolve to the imported domain-policy
module. Passthrough roots must be canonical UTF-8 relative paths with unique,
sorted, disjoint topology; invalid roots fail before domain callbacks run.
These checks preserve authoring inputs against ordinary generator writes.
The emitted Rust runtime likewise rejects candidate-source-contained output
roots (including symlinked parent aliases) before creating staging directories.
Neither preflight is atomic against concurrent path replacement; external
writer coordination remains necessary.

All implemented public metadata boundaries now admit exact runtime types before
using them as evidence or touching output. Numeric thresholds and counts reject
boolean aliases. Identity trees, anchors, behavior observations, probe programs,
provenance pins, mapped and semantic edits, exact, relocatable, and compatible
plans, and source-bound shares require immutable exact records. Compatible
instruction/correction paths and selected provenance-pin roots additionally
reject Windows drive-absolute and drive-relative labels at construction, before
consumer tree access. Cryptographic key, nonce, plaintext, AAD, and payload
fields require exact bytes. Invalid
direct Python construction fails through the owning domain error rather than
relying on coercion or leaking `TypeError`, `AttributeError`, or

`OverflowError`. Compatible consumer mappers and output postconditions also
wrap callback failures and reject foreign return records before publication.

### Exact Authoring Baseline

The implemented exact layer snapshots regular files by normalized relative path,
rejects symlinks and special entries, and models the target as deterministic
file
instructions. Byte-identical target files reuse source files directly. Modified
same-path files reuse exact source byte spans discovered by a deterministic
block
matcher and retain only unmatched oracle bytes as local authoring literals.
Both full input snapshots are rechecked after instruction construction so a
persistent source or oracle change during replay cannot return a stale plan.
These checks cannot make source-tree reads atomic against concurrent writers.

Exact plan creation now constructs five categories of internal records through
captured native allocation and original initializers: byte-matching and tree
planning contexts, source slices and local literals, output instructions, and
the final exact plan (`d9021ca1c`). Fourteen red-first late `__new__`/`__init__`
regressions cover those records. All 237 focused exact tests and 2,716
integrated diff tests passed; scoped Ruff and strict source BasedPyright had
zero errors. These are class-hook guards, not protection against direct
stored-instance mutation or external filesystem races.

Internal exact tree snapshots also pin native allocation and original
initializers for `FileRecord` and `TreeSnapshot` after filesystem callbacks
(`ddb920753`). Ten red-first late constructor-hook regressions passed, along
with 322 focused exact/model and 2,799 integrated diff tests. Scoped Ruff and
source BasedPyright reported zero errors (three older warnings). As with the
other guards, direct instance mutation and external writer races remain
outside this protection.

This local plan is verification evidence, not a distributable transform. Raw
`OracleLiteral` bytes must never cross the public emission boundary. A later
source-binding stage must convert them to recovery material that cannot be
materialized without sufficient admitted source evidence.

Exact materialization verifies the static source snapshot before writing,
constructs
the result under a staging path, verifies the static target snapshot, and
publishes
only after equality succeeds. Recipes may declare authenticated
`passthrough_roots`
for external runtime inputs. Such roots must match source/oracle during
authoring, are
then excluded from static snapshots/source binding, and are copied recursively
from
the runtime candidate into staging. Symlinks and special entries still fail
closed. Recursive snapshot and passthrough enumeration also surfaces filesystem

scan failures instead of treating an inaccessible subtree as absent.
A second static source snapshot after staging rejects persistent source edits or
new files before publication, with staging cleanup on rejection. Declared
passthrough roots remain dynamic. The final check and rename are not atomic;
external concurrent writers still need coordination. The no-replace
directory publisher also rejects host selectors that disagree with the actual
runtime OS, preventing a caller from selecting an overwrite-capable rename.
Source-pin snapshot and revision verification, relocatable tree planning and
placement, and executable local domain module loading also reject foreign `Path`
subclasses before source checks, output creation, or import hooks. Six red-first
regressions cover the three independent public boundaries. Consumer
module and ancestor status receipts must also be native `os.stat_result`
objects before the domain module executes. Invalid receipts cannot authorize
import, and errors from import, hook lookup, status, or resolution retain their
typed causes without invoking foreign exception string/representation hooks.
Domain module namespace names also hash the exact native path using the
host filesystem codec captured before domain hooks execute. Imported
`os.fsencode` alone was insufficient because it still calls mutable
`os.fspath`. The module resolver fails closed if later code replaces
`os.fspath`, `os.getcwd`, `os.lstat`, or `os.readlink`, even when the outer
`realpath` implementation remains pinned. A second native status check
confirms that the resolved regular file still has the admitted device and
inode before import. Five red-first regressions cover forged namespace
names, redirected module files, same-inode hardlinks, and CWD/link hooks.
Neither status check nor import is atomic against external filesystem writes;
this is not a sandbox for trusted consumer-domain code.
A frozen, slotted Python evidence record still permits its *class* slot
reader or `__getattribute__` to be replaced after consumer code executes.
Source-lineage, behavior, and conjunctive transform admission therefore read
original captured reason-slot descriptors when validating direct evidence,
returning `admitted`, or deciding whether to raise admission errors. Three
source, four behavior, and five gate regressions cover forged direct receipts,
failed evidence promoted to success, and incorrectly typed errors.

Five additional focused hardening changes also pin the original aggregate
source-lineage scores, anchor counts, file receipts, and policy; conjunctive
gate source and behavior references; behavior scores, correction routes,
profiles, observations, and minimum threshold; profile and observation
collection tuples throughout evaluation; and identity digest, compatibility,
and bug-state observation outcomes. Seventy-six red-first getter and slot
regressions cover direct construction, policy consistency, and admission
verdicts. These checks reject forged class-level readers but do not prevent
trusted code directly rewriting instance storage, mutating third-party
callbacks, or changing files concurrently. Immutable record construction and
process-hook isolation do not defend against arbitrary trusted code directly
rewriting stored object state.

Four further fail-closed boundaries keep consumer domain admission and authoring
bound to the original record storage. `DiffDomain` invokes its captured
constructor validator and reads the original callable hook slots, rather than
trusting a later `__post_init__` or class getter. Generator preflight requires
an exact domain bundle and invokes its stored source-provenance and
oracle-validation callbacks; a late getter cannot skip either check. `SourcePin`
and `SourcePinEvidence` likewise retain their original constructor validators
and read stored repository, selected roots, file count, and snapshot digest
when verifying an observed tree. The four behavior-program record types keep
captured constructor guards and slot readers; source/oracle authoring,
transcript classification, and candidate observation use the admitted stored
probe groups and bug digests. Twenty-four red-first tests reproduced validator
replacement, spoofed metadata or callbacks, omitted probes, and altered bug
states before these fixes. Trusted callback execution, direct instance-storage
mutation, and concurrent filesystem writers remain separate trust boundaries;
these changes do not create a sandbox or an atomic source snapshot.

Domain hook loading now constructs the validated `DiffDomain` bundle with
captured native allocation and its original initializer (`23646a309`). Two
red-first `__init__`/`__new__` cases show imported consumer code could replace
callable hooks or interrupt record creation after module admission. All 90
domain tests and scoped Ruff checks passed; source BasedPyright reported zero
errors, while the test file retains one pre-existing path-typing diagnostic.
Class-hook isolation does not protect trusted direct record storage changes.

The public generator recipe captures all fifteen original field slots in a
private immutable snapshot before validation. The same validated snapshot is
used for domain preflight and exact publication, so a late class property or
`__getattribute__` replacement cannot conceal malformed policy or redirect the
chosen source, oracle, mode, or output after preflight. Twenty-eight red-first
regressions cover stored invalid fields and post-validation class edits. This
does not protect against deliberate direct mutation of stored instance values.

The internal `_RecipeSnapshot` now uses its captured original NamedTuple
allocator (`7bab64eb0`) instead of consulting later class `__new__` or
`__init__` hooks during recipe policy checks. Four red-first regressions
cover exact and compatible modes; all 205 focused generator tests, scoped
Ruff, and diff checks passed. The integrated diff run had 2,736 passes and
14 failures from concurrently edited compatible constructor regressions,
so no green integration verdict is claimed for this commit. Source strict
BasedPyright retains four pre-existing diagnostics. Trusted direct mutation
and filesystem races remain separate boundaries.

The `DiffRecipe` constructor also writes all fifteen fields through the same
captured native descriptors, instead of a dataclass-generated initializer that
would dispatch replaceable class property setters. Fifteen malformed-field
and fifteen valid-field regressions in `21e31bba1` prove that class setters
cannot launder invalid recipe input before the original-slot snapshot and
policy check. The defect was reproduced red-first; all 2,501 diff tests
passed after that signed commit. This
protects class-level setter substitution, not direct instance edits, mutation
of trusted module internals, or concurrent filesystem writes.

The six exact-authoring model records (`FileRecord`, `TreeSnapshot`,
`SourceSlice`, `OracleLiteral`, `ExactInstruction`, and `ExactAuthoringPlan`)
now invoke original constructor validators instead of late class
`__post_init__` hooks. Instruction kind checks and plan/source-reference
verification read captured original slots for instructions, snapshots,
file digests, target metadata, and source-slice coordinates. Twenty-five
red-first tests cover invalid or valid dataclass replacements, forged
instruction and plan getters, changed validation helpers, and source digest
or slice-offset spoofing. This protects the local model admission boundary
from late class hooks, not intentional instance-storage mutation or racing
external filesystem writers.

The six exact-authoring model constructors now also write all seventeen
fields through captured original storage descriptors instead of
`object.__setattr__`, which dispatches replaceable class property setters.
Six red-first invalid-record and seventeen valid-construction regressions
prevent a late setter from laundering unsafe paths or other evidence before
validation. The four protected-plan records similarly write twenty fields
through original descriptors, with four red-first invalid-construction and
twenty valid-field cases protecting authenticated payload and plan metadata.
`SourcePin` and `SourcePinEvidence` likewise write seven original slots;
two red-first malformed-count cases and seven valid-field cases prevent
forged setters from changing source revision commitments. All remain process
class-hook guards, not protection from direct instance-storage mutation or
external concurrent filesystem changes.

Measured `SourcePinEvidence` now uses captured native allocation and its
original initializer when returning a source snapshot (`9aa20356d`). Three
red-first initializer forgeries previously changed the counted source files,
changed the SHA-256 digest, or promoted a deliberately incorrect revision pin;
an isolated `__new__` case protects snapshot allocation. All 125 provenance
tests and 2,689 integrated diff tests passed, with zero scoped Ruff and
BasedPyright errors (46 pre-existing type warnings). This guards against late
class hooks, not direct trusted object edits or concurrent filesystem writers.

The seven portable probe record constructors likewise write their twenty-three
fields through captured native descriptors. Seven red-first malformed-input
cases and twenty-three valid-field cases stop class property setters from
rewriting path, executable, timeout, output-limit, or transcript metadata before
the existing constructor guards. The five compatible correction, instruction,
build, authoring-plan, and materialization request records similarly pin thirty
field writes: five red-first and thirty valid-field regressions cover unsafe
paths, plan shape, and publication requests. Compatible envelopes continue to
validate through their existing captured slot-reading views. These setter
fixes do not claim to shield all later consumer getters, direct record mutation,
or concurrent filesystem writers.

The private compatible `_BuildContext` and `_MaterializeContext` now write seven
transient authoring and routing fields through captured original slots, and
subsequent planning reads the original descriptors. Seven reproduced late-setter
interceptions and three getter-redirection regressions in `5a37898fa` guard
source/oracle selection, candidate reads, mapper selection, and semantic
correction routing. All 235 compatible tests passed after that signed commit;
2,539 integrated diff tests passed before it. The guarantees exclude direct
instance-storage mutation and concurrent filesystem modification.

Five further class-hook admission repairs close late setter and getter
redirection in the trusted consumer and decision records. The seven `DiffDomain`
hooks (`12b1c897b`) now construct through their original descriptors, as do
ciphertext and tag in `AuthenticatedPayload` (`2d38d3b73`), and source,
behavior, and rejection reasons in `TransformAdmissionEvidence` (`3332c420b`).
The four behavior-program records write thirteen fields through captured slots
(`321a99ba7`). The internal `_AggregateEvidence` scores and file counts
(`44b31171a`) now use four original descriptors for both constructor writes
and reason computation. Previously, late aggregate getters could make a tree
with *no candidate source files* pass source-lineage admission. Fifty-five
red-first and valid-input regression cases cover these five changes. These
repairs isolate late class-property replacement, not arbitrary instance
storage rewriting or concurrent source-tree mutations. The complete synthetic
diff suite passed 2,464 tests after these changes; this is bounded regression
evidence, not an unconditional compatibility or security proof.

Pinned-source snapshots also require native `os.stat_result` receipts for the
source root, selected paths and parent components, and file-identity rechecks.
Foreign mode and inode records cannot certify pinned provenance. Filesystem
status, junction, traversal, resolution, and delegated-read failures retain
typed causes without running foreign exception string or representation hooks.
These checks are not atomic against concurrent external source writers.
Exact tree snapshot, authoring and materialization root admission and compatible
build/materialize request admission independently require exact host-native
`Path` objects. Foreign path subclasses cannot redirect source/oracle reads,
candidate admission or output publication. Eight red-first public API regressions
cover the independent roles before any path method runs.
The Python generated-Rust source emitter separately requires an exact native
`pathlib.Path` output before rendering or staging bytes. Its default native path
remains valid; caller-defined path subclasses never receive filesystem calls.
The emitter also requires native `os.stat_result` receipts when checking the
output leaf and ancestor directories before creating or replacing output.
Forged metadata cannot approve output publication or overwrite an existing file.
Output status, junction, parent creation, rename and temporary cleanup errors
retain typed causes and native diagnostic text without executing foreign
exception string hooks; cleanup errors cannot mask the original failure.
The exact Rust emitter also serializes source/target metadata, authenticated
ciphertext and tag, threshold binding, anchor policy, and bound shares from
captured original record slots. Class getters substituted after admission
cannot rewrite emitted recovery constants. Template self-overwrite checks,
output ancestor traversal, and rename receipts compare pinned native path
spellings instead of late `Path.__eq__`. Twenty-six red-first regressions
cover these emission and publication hooks. The output preflight still cannot
make concurrent filesystem writes atomic and is not a sandbox for trusted code.

The Python emitter's staged UTF-8 writer, output-directory creation, atomic
file replacement, and owned temporary cleanup now use captured native host
operations rather than replaceable `Path` methods or a late `os.mkdir` hook.
Original `Path.parent`, `Path.name`, and `Path.with_name` operations also bind
output ancestor checks and temporary staging to the admitted destination.
Seven targeted regressions cover late `Path.open`, `Path.replace`,
`Path.mkdir`, `Path.unlink`, `Path.parent`, `Path.with_name`, and `os.mkdir`
redirection; five were first demonstrated failing before their repairs.
After the follow-up, all 132 emitter tests and 2,252 integrated diff tests
excluding a concurrently edited probe suite passed. These measures cannot
make path checks atomic against external filesystem races or isolate arbitrary
trusted consumer code that directly mutates module bindings.

The standalone Rust exact runtime now checks source-root metadata without
following links before attempting a candidate snapshot (`e894ca859`). A
compile-and-run regression first reproduced a linked source root passing
verification and publishing an output tree; the fix rejects that root before
publication, matching Python exact snapshot policy. All 133 Rust emitter tests
passed after commit, and 2,823 integrated diff tests passed before commit with
concurrent peer changes. Scoped Ruff and strict emitter-source BasedPyright had
zero diagnostics. Standalone `rustfmt --check` still reports broad preexisting
template-format differences, while Jig doctor reports an absent graph; neither
is a clean repository-wide verdict. The fix does not prevent parent-directory
races or source-tree changes by concurrent writers.

The exact Python materializer now opens staging files through an
import-pinned native `io.open` in exclusive `xb` mode; a pre-existing staging
file cannot be silently truncated. Original `Path.parent` and `Path.name`
readers, pinned joinpath, and native `os.mkdir` isolate staging placement and
directory creation from late consumer class/host hooks. Three regressions
reproduced redirection before the repair; additional cases cover late
`io.open`, `Path.mkdir`, `os.mkdir`, basename spoofing and duplicate staged
files. The signed `5d32765f5` change passed 223 exact tests and 2,421 diff
tests excluding concurrently edited relocatable tests. Direct mutation of
trusted module internals and concurrent filesystem writers remain separate,
non-atomic boundaries.

Compatible Python materialization also protects its own staging writes,
parent creation and output basename from late host hooks. Its import-pinned
`io.open` uses exclusive `xb`, with native `os.mkdir` and original
`Path.parent`/`Path.name`/joinpath operations preserving the staging identity.
Three reproductions first failed under write, parent, and staging-root
redirection. Additional regression cases cover late `io.open`, `os.mkdir`,
`Path.mkdir`, and linked or pre-existing staged leaves. The signed
`6e08a186a` change passed 243 compatible tests and 2,250 integrated tests
excluding active peer suites. Direct mutation of trusted module bindings and
external concurrent filesystem writers remain separate risks. Standalone
BasedPyright still reports thirteen older compatible-model diagnostics outside
these staging changes.

Generator exact replay separately reads stored native file and snapshot
fields, and its output checks use original path-ancestry comparisons rather
than late class equality or parent hooks. Signed generator commits
`28dc8284d` and `a15eccef2` introduced twelve red-first cases, passed 184
focused and 2,619 integrated diff tests, and left direct private-instance
mutation and concurrent external filesystem writers outside the guard. A
global Jig check exceeded 90 seconds without a conclusive pass.

Exact generator source identity also constructs child file paths without late
`Path.__truediv__`, `Path.joinpath`, `Path.with_segments`, `builtins.type`,
`Path.__new__`/`__init__`, or `os.fspath` hooks. The signed `aedb58b65`
fix first pinned source path joining, followed by `5cc2fcf1b` using captured
native `pathlib` raw-path and cached-string slots to bypass nested constructor
and string-formatting dispatch. Seven additional path-hook cases (including
six red-first failures) and ten canonical spelling cases preserve native
path equality for dot, root, double-root, and nested paths on the tested host.
The final local evidence was 201 generator tests and 2,651 integrated diff
tests, with scoped Ruff, BasedPyright, and diff checks clean. These are
in-process hook guards, not an atomic defense against external source changes
or arbitrary mutation of trusted private storage.

The same publisher admits only the running host's exact native `pathlib.Path`
type for both staging and destination before querying filesystem methods.
Caller-defined `Path` subclasses may override path resolution, file status, or
rename behavior and cannot establish publication authority. Two red-first
regressions prove foreign path conversion does not run for either role, without
relaxing the existing directory, host-selector, or no-replace admission rules.
Directory publication also requires exact native `os.stat_result` receipts for
the staged directory before rename and the published destination afterward.
Foreign metadata claiming directory type or matching inode identity cannot
trigger a rename or certify its completion. A post-rename attestation failure
reports unsuccessful confirmation without deleting an already moved directory.
Staging/destination identity uses pinned native path spellings rather than
mutable `Path.__eq__` methods. Two red-first regressions show that late equality
overrides cannot falsely equate distinct roots or admit an identical pair.
Linux renameat2 errors also normalize the native `ctypes.ArgumentError`
raised by ABI setup or invocation to their typed `OSError` outcomes rather
than leaking a ctypes exception. The original exception type is pinned
against later alias substitution. DCO `fb8c2583b` adds a red-first call
failure and loader/alias regressions; all 67 publication tests passed, as
did 2,257 other diff tests excluding live probe edits.
The matcher used for source-span reuse remains separate from canonical identity
and
stable admission anchors.

### Canonical Identity

Whole-tree byte equality is too fragile for admission. Canonical identity may
ignore comments, whitespace, formatting, and line endings when computing
structural similarity and stable anchors.

Canonicalization is an identity mechanism only. It does not authorize dropping
comments, copyright/provenance text, or other source bytes from reconstructed
output. Output construction uses admitted source material and explicit
transformation rules.

Stable anchors should be token- or content-defined so harmless insertions do not
shift every anchor in a file. Aggregate similarity alone never authorizes
materialization.

### Implemented Stable-Anchor Primitive

The generic anchor primitive scans sliding byte windows with a deterministic
64-bit
polynomial rolling hash and selects windows from that content-derived value.
Only
selected windows receive SHA-256 fingerprints. Selection therefore depends on
window content rather than absolute position while avoiding a cryptographic hash
at
every byte offset. Unchanged windows remain recognizable after insertions shift
their offsets. Duplicate SHA-256 digests count once for coverage, and a
deterministic
minimum-rolling-hash fallback prevents a non-empty sparse input from producing
no

evidence.

This primitive does not by itself admit a tree. Tree-level distribution rules,
minimum anchor counts, canonical language-aware views, ambiguous-match handling,
and the configured coverage threshold still belong to the unfinished admission
layer. Anchor digests are evidence only and must not be treated as
source-binding
secrets.

Internal `StableAnchor` and `AnchorCoverage` construction now uses captured
native allocation and original record initializers rather than late class
`__new__`/`__init__` hooks (`926581d03`). Five regressions cover short and
scanned source windows, unrelated coverage, and isolated class allocation
substitutions. All 58 fingerprint tests and 2,656 integrated diff tests passed;
scoped Ruff and BasedPyright reported zero errors (three older type warnings).
This isolates class-hook redirection, not direct record storage mutation or
concurrent source writers. Repository-wide Jig has no clean verdict.

### Implemented Tree-Level Admission

The generic admission layer accepts only consumer-selected canonical identity
files. It is reference-driven: candidate-only files do not improve similarity.
Each reference file has equal aggregate weight, so large binary/opaque files
cannot
dominate merely through byte count or number of fingerprints. Consumers are
still
expected to exclude files that do not belong to source identity.

Structural similarity uses a denser content-defined fingerprint view and a
symmetric overlap score. Stable-anchor coverage uses the sparse anchor primitive
and asymmetric reference-anchor survival. Coverage is averaged per eligible
file,
not over a global anchor bag. Policy separately requires a minimum number of
files
with at least one real matching anchor and per-file coverage at or above the
configured threshold. This prevents one concentrated region from satisfying the

distributed lineage requirement.

Synthetic tests exercise exact and insertion-compatible admission, unrelated
source rejection, the representable floating-point boundary immediately above
and
below both thresholds, concentration in only one file, and candidate-only opaque
assets. These checks remain necessary but insufficient until behavior and source
binding also pass.

Internal source admission now constructs `IdentityFile`, `IdentityTree`,
`FileAdmissionEvidence`, `_AggregateEvidence`, and `TreeAdmissionEvidence`
using captured native allocation and original validating initializers
(`aef38184b`). Ten red-first `__init__`/`__new__` regressions cover identity
creation and per-file/aggregate verdicts; all 138 focused tests and 2,681
integrated diff tests passed. This prevents class-hook redirection during
lineage calculation, not direct trusted record edits or concurrent writers.

### First Language-Aware Consumer Identity

`src/research/algorithms/domain/algorithms/doom/generator/doom.py` provides the
first domain identity adapter.
It restricts identity to C/header files under `linuxdoom-1.10`, so the large WAD
and the separate IPX source family do not affect Linux source-lineage scores.
The
adapter applies C line splicing before comment handling, preserves
comment-internal
newlines, protects string/character literals, frames preprocessing tokens
unambiguously, and records preprocessor-directive line termination while
ignoring
ordinary presentation whitespace.

Synthetic tests prove comment/formatting equivalence, comment-looking bytes
inside
literals, whitespace-sensitive punctuator boundaries, preprocessor line endings,
backslash-newline splicing, malformed-comment failure, and source-tree
selection.
The generic engine remains language-agnostic; this adapter is consumer policy,
not
a C mode hidden inside `algorithms/diff`.

A local calibration smoke compared the 124 selected source identity files
against
the current normalized oracle descendant. All 124 source paths were present in
the
oracle view. With the provisional 0.50 structural and 0.66 anchor thresholds,
the
aggregate structural score was 0.780928, aggregate anchor coverage was 0.766396,
and 94 of 123 anchor-eligible source files individually met 0.66 coverage. This
is
useful stress evidence, not final compatibility calibration and not legal
evidence.

### Behavioral Identity

The implemented evaluator supports three probe classes supplied by a consumer:

- identity probes for stable lineage behavior;
- compatibility probes for transform preconditions;
- bug probes for conditional corrections.

Every identity probe must execute. Matching identity observations contribute
equally to the configured behavior-similarity threshold. Compatibility probes
are
hard preconditions. Bug probes classify the candidate as defect `present`,
already
`fixed`, or `unknown`; present defects route a named correction to apply, fixed
defects route that correction to skip, and unknown state fails closed. Bug
probes

therefore remain deliberately separate from identity probes.

`gate.py` combines source-lineage and behavior evidence conjunctively.
Behavioral
evidence never replaces source evidence, and source scores never replace failed
behavior preconditions. Synthetic tests include a
perfect-behavior/unrelated-source
clone and prove it is rejected. The generic evaluator consumes normalized
observations only; executing application-specific probes remains consumer work.

Internal behavior-evidence reports now use native allocation and the original
validating initializer instead of later class constructors (`85857aea2`).
Four red-first cases preserve behavior admission and failed compatibility
rejection under replaced `BehaviorEvidence.__init__`/`__new__` hooks. All 149
focused behavior tests and 2,685 integrated diff tests passed; scoped Ruff
and diff checks were clean. Source strict type checking retains six unrelated
existing diagnostics. This does not defend against direct stored-record edits.

Internal `combine_admission()` now creates its `TransformAdmissionEvidence`
report through captured native allocation and the original validating
initializer instead of replaceable class `__new__`/`__init__` hooks
(`7b8038188`). Four red-first tests prove accepted reports remain accepted
and rejected source lineage cannot be promoted by forged constructors.
All 43 focused gate tests passed after commit; 2,668 integrated diff tests,
scoped Ruff, and strict source BasedPyright passed before publication.
Direct instance-storage mutation and trusted module internals remain outside
this guard. `jig doctor` reports degraded and the global `jig check` timed
out after 120 seconds in native validation, so no green Jig verdict is claimed.

### Portable Behavior Programs

The generic execution layer now has a process-program representation designed to
be reproducible by the future Rust emitter. Commands never use shell
interpolation.
Executables are logical tool references or rooted artifacts; argv paths are
structured beneath authorized source, repository, or scratch roots. Before
mirroring, the executor rejects structured repository-relative arguments and
executables that resolve within the original source tree, including symlink
aliases, as well as existing regular-file hardlinks sharing source device/inode
identity. Source and repository inode checks require native `os.stat_result`
receipts, so foreign identity records cannot certify hardlink disjointness.
Unrelated hardlinks remain admitted. Executable admission
also requires an exact host-native `os.stat_result` before trusting regular-file
mode; foreign status receipts reject execution, and status errors never invoke
foreign exception string hooks. Other host faults in root/path/tool resolution,
source snapshots, inode status, temporary workspace, and source mirroring also
retain typed causes without invoking foreign exception formatters. This prevents
a repository-rooted path from bypassing the source mirror, including when
post-run source checks are
disabled. It is not an OS sandbox: arbitrary raw string argv and
consumer-selected
executable behavior still require external trust and isolation policy. Commands
carry
explicit timeouts, expected exit status, bounded stdout/stderr capture, optional
stdin, plus explicit flags selecting stdout and/or process exit code into the
observation transcript. A command may instead require one exact exit code when
its

return value is a success precondition rather than behavior data. Executable
spawn and reader/writer thread startup failures, including unexpected ordinary
host dependency errors, are wrapped as probe execution errors while terminating
the launched child. Direct-child wait failures remain typed after attempted
cleanup, preserving the original native cause. Child stdout and stderr now use
concurrent pipe readers that enforce output byte quotas. They abort
overflowing commands before completion. Pipe read/write/close failures are
recorded by worker threads and reject the transcript. Raw reads now require
exact native byte results within the requested chunk length and a native,
in-range C-int file-descriptor receipt before calling the OS reader. Unexpected
ordinary invalid-stream errors are recorded as failures instead of silently
terminating a worker. Each reader and the nonempty stdin writer also
mark explicit clean completion; unexpected worker exits lacking that marker
cannot be confused with successful pipe capture. A concurrent
stdin writer preserves full-duplex behavior. Stream teardown also requires
native `None` completion on reader, writer, unused, and empty-stdin pipes;
foreign completion receipts reject the transcript or remain secondary to the
original failure. The wall deadline starts before
process launch and covers reader/writer setup, child and pipe completion.

Unrepresentably large timeout integers reject through the probe execution
boundary before spawning, rather than leaking host float-conversion overflow.
A child that already exited by the time delayed pipe setup finishes still fails
if the elapsed wall budget has expired. On POSIX, completed and failed commands
terminate residual
members of their dedicated process group after capturing the leader result.
Ordinary helpers that close their inherited pipes cannot continue running after
success. Windows still stops only the direct child on failure; descendants that
detach their POSIX session are also outside cleanup. Cross-platform child-tree
cleanup remains open.

The six transient `_PipeCapture` fields (quota, fragments, byte count, overflow,
error, completion) and seven `_RunningProbe` fields (process, pipes, workers,
stdin errors and acknowledgment) now construct through captured native slots.
Runtime quota checks, worker-health checks, cleanup, and transcript assembly
also read and update those original slots instead of late replaceable class
properties. Commit `504e00c81` adds 26 red-first class getter/setter cases
plus a direct quota-spoof regression: a two-byte quota previously retained
five bytes after a forged `limit` getter. All 338 focused probe tests passed
after the commit, and 2,595 integrated diff tests passed before it. The repair
prevents late class-property substitution, not direct mutation of live state,
trusted host-process interference, or external filesystem races.

Probe execution now also allocates `_CommandResult`, `_PipeCapture`, and
`_RunningProbe` receipts through native object allocation and captured
original initializers (`82e32113e`). Eight new `__init__`/`__new__`
constructor-hook tests cover late substitutions after process callbacks,
with allocation cases isolated from the shared Python test interpreter.
All 346 focused probe-execution tests passed after the commit and 2,778
integrated diff tests passed before it; scoped Ruff and source BasedPyright
had no errors. This does not isolate arbitrary direct writes to live records
or external process/filesystem interference.

The completed-child receipt is now an internal `_CapturedProcess` with
captured native allocation, the original initializer, and native slot reads
(`6c1263d65`). This removes mutable `subprocess.CompletedProcess` class,
constructor, stdout, stderr, and return-code getters from the evidence path.
Five late-hook regressions failed before the fix; eleven new cases passed,
as did all 357 postcommit focused and 2,799 precommit integrated diff tests.
Scoped Ruff, source BasedPyright, and diff checks were clean. Direct
live-object mutation and external process/filesystem races remain outside
these boundaries.

A probe batch validates the candidate source as a regular-file-only tree and
rejects an OS temporary-directory parent resolving inside that source before
creating scratch state, preventing recursive self-copying when `TMPDIR` points
into the candidate. The admitted absolute temporary parent is pinned for the
batch and each nested scratch workspace, so a later global TMPDIR selection
change cannot redirect them into the source. The runner then copies the source
into an isolated temporary mirror without following symbolic links.
The mirror's complete byte snapshot must match the pre-copy source snapshot,
including when post-run original-source immutability checks are disabled.
Invalid trees, unexpected links, or copy drift fail within the probe error
boundary before commands execute. This is a consistency check, not an atomic
filesystem snapshot; caller coordination is required against concurrent writers.
Programs receive the mirror path rather than the user input path. The mirror
byte-tree is checked after **each command**, including on failure, and again at
program boundaries. This prevents a command from modifying source bytes for a
later command to consume and then restoring them before program completion;
a within-command change-and-restore remains outside this post-exit scan. When
enabled, a separate post-run
source comparison verifies the original tree after normal completion **and**
when probe execution raises, preserving the original failure if source bytes are
unchanged and reporting source drift otherwise. This detects but cannot restore
writes made through trusted raw argv. Compile-then-run
programs are possible because one command may create
a
scratch executable consumed by a later command.

The executor validates the complete process description before snapshotting,
copying, or launching anything: roots/enums, executable records, argv tuples,
NUL-free portable UTF-8 argv strings, relative paths, and tool identifiers,
stdin bytes, exit codes, timeout/output limits, digest flags, program batches,
tool bindings, and source-immutability flags all use exact admitted types.
The `ProbeRunContext` admission further requires exact host-native `Path`
values for the source root, repository root, and bound tool executable paths,
so user-defined string, resolution, or status overrides cannot run at record
construction. Three red-first regressions cover those independent roles.

Behavior authoring rejects identity and bug programs without at least one
stdout or exit-code transcript selector when constructing their typed records,
before any source or oracle processes execute. Direct authored records enforce
the same condition to prevent empty-transcript digests from masquerading as
identity or bug evidence. Compatibility success-only probes need no selector.
Behavior authoring snapshots its original source and (when bug probes exist)
corrected oracle before executing any source or oracle probe batch. Both byte
trees are checked after source probes and again after oracle probes, including
exceptional exits. This prevents an oracle-stage side effect or concurrent
persistent source edit from making the authored baseline stale. When no bug
program is present, no oracle source tree is needed. This is not an atomic
snapshot against external writers.
Behavior authoring runs identity programs on the original source. Bug programs
run
on both original source and the local corrected oracle; their selected-stdout
transcripts must differ. Those two digests become the portable `present` and
`fixed`
baselines. Candidate execution matching neither baseline produces `unknown` and
fails closed. Candidate behavior observation verifies one full source byte-tree
snapshot before copying one dedicated observation source mirror (symlinks are
not followed), and the mirror must match that admitted snapshot before probes.
All identity, compatibility, and bug programs run against the same mirror, which
prevents interleaved live source edits from combining probe evidence from
different source versions. Original candidate and mirror snapshots are rechecked
after each probe group. Source/oracle repository and tool bindings are
compared using pinned host realpath resolution and canonical path strings,
including Windows case semantics. Four red-first regressions ensure late
`Path.__eq__` or `os.path.realpath` overrides cannot merge distinct bindings
before a probe runs. Observation mirror copy completion likewise requires
matching pinned native path strings: two red-first regressions prevent late
equality overrides from admitting a foreign completion or rejecting a valid
one. Context resolution, source snapshot and baseline recheck, mirror creation,
and temporary observation root failures retain typed causes without executing
foreign exception formatting callbacks. The copy is not atomic; external source
writers can race the snapshot/copy boundary and still require coordination.
Compatibility programs contribute success/failure rather than an identity
digest. Application-specific harnesses and logical tool resolution
remain
consumer policy; the generic engine only owns execution and transcript
semantics.

Behavior transcript batch matching, selected-digest admission, identity
observation, and present/fixed bug classification now read the original
`ProbeTranscript` ID, digest, and selected-command slots. Program enumeration,
profile assembly, and observation labels likewise use the original
`ProbeProgram` ID slot. This prevents post-authoring class getters from
relabelling a foreign transcript, inventing selected output, or changing
present/fixed routing. Six red-first getter-spoof regressions are fixed by
`68324e4e5`: all 124 focused behavior tests passed after the commit, and
2,637 integrated diff tests passed before it. This is a late class-hook guard,
not a defense against direct mutable process state or external writers.

Portable behavior authoring and observation now build ten authoritative
record types through original validator-backed initializers and native
allocation (`375e65304`): identity/compatibility/bug profile probes,
`BehaviorProfile`, authored bug and program receipts, three observation
classes, and `BehaviorObservations`. Twenty red-first late `__init__`/
`__new__` regressions prove that a completed source/oracle probe or
candidate observation cannot replace those constructors. Allocation-hook
cases run in separate interpreters to avoid CPython type-slot leakage.
All 144 focused behavior-program tests passed after the commit and 2,778
integrated diff tests passed beforehand. Scoped Ruff and source BasedPyright
reported zero errors (nine existing type warnings). The boundary is late
class-hook substitution, not directly rewritten record storage or races
with external filesystem writers. Repository-wide Jig is not verified.

Behavior mirror creation also now pins the admitted `ProbeRunContext`
source, repository, and tool-binding slots and builds the derived mirror
context with its original initializer and native allocation (`b7f2df5f9`).
This replaces `dataclasses.replace` after mirror-copy callbacks, preventing
late `__init__`/`__new__` or getter hooks from redirecting the mirrored
process authority. The original candidate root is retained for each
post-copy source-drift check, even when a class getter points instead to
the unchanged mirror. Five red-first regressions cover these boundaries.
All 149 behavior-program tests passed after commit; 2,804 integrated diff
tests passed before commit. Scoped Ruff and source BasedPyright reported
zero errors (nine existing type warnings). Direct private-state mutation
and non-atomic external filesystem writes remain outside this guard.
Repository-wide Jig doctor is degraded (cached graph absent); the full
check did not finish within a 110-second bound.

### First DOOM Executable Identity Probe

The first consumer program is
`windows-x86_64-clang22-v1:fixed-point-arithmetic`. It is intentionally an
identity
probe, not a bug probe. The DOOM domain asks pinned Clang 22.1.8 to compile the
candidate mirror's `linuxdoom-1.10/m_fixed.c` together with a repository-owned
MIT
freestanding harness and minimal standard-header shims. `lld-link` produces a
no-CRT x86-64 PE with a private entry point. The process exit code encodes
selected

`FixedMul`/`FixedDiv` results and becomes the transcript observation.

A local read-only smoke over the historical ignored source and the local
modernized
oracle produced the same transcript digest for both trees:
`f0b37d59c86384e4ee628ec0e637c60aaa7ca35e5ecdb826687fc35c37d133e2`.
The value is calibration evidence for this versioned Windows profile, not a
legal
identifier and not a claim that one probe is sufficient for final 0.80 behavior
admission. Repository tests use synthetic MIT `m_fixed` fixtures instead of
local
DOOM bytes and prove semantically equivalent implementations produce equal probe
transcripts.

The attempted `R_PointToDist(0, 0)` bug probe remains deliberately uncommitted.
Its
containing renderer translation unit retains many unrelated externally visible
roots under the available COFF/LTO toolchain. Rather than introduce fake
semantic
stubs or force unresolved symbols, that bug stays pending until it has an honest
isolation strategy or a different executable harness.

### Source Binding

The first source-binding layer is now implemented for high-entropy
reconstruction
key material. The generator selects canonical stable-anchor windows across
source
files by content digest, round-robins them across files, and computes
`T = ceil(N * configured_fraction)`. The fraction is interpreted using its
canonical decimal representation and the ceiling is computed with integer
arithmetic, preserving exact decimal boundaries and requiring the extra share
for a representable fraction immediately above a boundary. A floating-point
product must not round that stricter policy down to fewer shares. The secret is
split T-of-N over GF(256). Each
share is XOR-masked with HKDF-SHA-256 output whose input key material is the
exact
canonical anchor window and whose context also binds the source path, anchor
digest,
share coordinate, and transform context. A SHA-256 commitment rejects incorrect

reconstruction. Recovery independently enforces the configured minimum number of
distinct source files, so many surviving anchors from one large file cannot
satisfy
the distributed-evidence requirement by themselves. Authoring now rejects a
Shamir threshold below the minimum distinct-file requirement; both Python
recovery and the generated Rust runtime reject a contradictory envelope before
recovering a secret. This is a necessary policy consistency condition, not a
cryptographic proof of distinct-file dependence: multiple shares may belong to
one file, so an offline holder of enough shares from fewer files could recover
the key outside the runtime distribution gate. Stronger cryptographic
file-distribution guarantees remain a separate design problem.

The anchor sample is deliberately content-ranked rather than offset-ranked. In a
local read-only DOOM calibration with 127 bound shares and the provisional 0.66
threshold, the modernized oracle retained 105 recoverable shares; 84 were
required,
and the synthetic 32-byte key recovered successfully. The earlier offset-ranked
sample retained only 59, demonstrating why positional sampling was rejected
rather
than weakening the threshold. This smoke is engineering calibration, not a legal
criterion.

Repository-owned synthetic tests cover the RFC 5869 SHA-256 vector, every exact
T-of-N combination in the fixture, T-1 failure, empty/unrelated source
rejection,
metadata tampering, deterministic generation, multi-file distribution, and
source
insertions that shift anchor offsets.

Recovery also admits the distributable binding structure before inspecting the
candidate source: threshold/minimum-file counts are positive exact integers,
share coordinates and source-anchor identities are unique, paths are canonical,
and digest/share lengths are exact. Malformed metadata cannot lower a threshold
(for example via a negative or boolean value) or be ignored merely because
enough other shares survive.

Internal source-binding key evidence now constructs `_AnchorMaterial`,
`BoundShare`, `ThresholdBinding`, and `_RecoveredShare` through captured
native allocation and original initializers (`b6d41a9ea`). Eight red-first
`__new__`/`__init__` tests show later class substitutions cannot rewrite
anchor windows, masked shares, binding envelopes, or recovered share data.
The exact pair passed 147 focused tests, with 2,668 integrated diff tests
passing before publication. This prevents late class-hook substitution,
not deliberate stored-instance mutation or external source races.

The authenticated-encryption primitive itself is now implemented separately
using
RFC 8439 ChaCha20-Poly1305. Its Section 2.8.2 test vector matches exactly,
including
ciphertext and Poly1305 tag; a development cross-check against Node crypto
produced
the same bytes. The Python implementation remains deterministic
authoring/reference
code; the emitted exact Rust runtime now carries the fixed-limb runtime
implementation.

Python AEAD encryption now returns detached `AuthenticatedPayload` evidence
through captured native allocation and the original record initializer
(`96837b2ff`), not mutable class `__new__` or `__init__` hooks. Two red-first
initializer cases showed that late consumers could replace computed ciphertext
or a valid Poly1305 tag; an isolated allocation-hook case covers `__new__`.
All 37 payload tests and 2,671 integrated diff tests passed, with scoped Ruff
and BasedPyright reporting zero errors (four existing type warnings). The
change does not isolate direct trusted module or instance-storage edits.

`protected.py` now combines key binding and authenticated encryption for exact
authoring plans. Every `OracleLiteral` is moved into one deterministic plaintext
stream. Protected instructions retain only source slices or offsets into that
stream.
The stream is encrypted as one ChaCha20-Poly1305 message; source/target
snapshots,
context, output paths, expected hashes, source paths, segment types, offsets,
and
lengths are authenticated as AAD. The 256-bit payload key is then bound to
canonical

source anchors. Recovery must unlock that key and authenticate the full payload
before
the transactional exact materializer can create its staging output.

Protected exact authoring now pins native allocation and original initializers
for its `_PayloadBuilder`, `PayloadSlice`, `ProtectedInstruction`,
`ProtectedMetadata`, and `ProtectedExactPlan` (`d2df13a43`). It also calls the
original payload-builder append method, so a late class replacement cannot
rewrite authenticated literal ranges. Eleven red-first regressions cover both
constructor hooks and buffer interception; all 147 focused tests passed. The
first integrated run had 2,702 passes and two failures in concurrently
edited exact-planner tests; the subsequent integrated run passed all 2,724
tests after that peer's exact-planner fix. This isolates class hooks,
not direct instance-storage edits or external filesystem races.

A read-only DOOM exact-baseline smoke generated 152 protected instructions and a
2,116,232-byte ciphertext with a 16-byte tag. The binding contained 127 shares
with
an 84-share threshold and a 32-file minimum. After the payload key schedule was
strengthened to include unserialized canonical source bytes, the smoke was
rerun:
materialization under `.temp` again reproduced the 152-file local oracle
snapshot
exactly, while fresh source and oracle snapshots proved both input trees
remained
unchanged. The generated 4,655,420-byte Rust source also compiled through Rust
1.97.1
with `-D warnings --emit=obj`; executable linking on this workstation is blocked
only
by absent Windows SDK import libraries. All smoke outputs were deleted

afterward.

After the DOOM source revision was hard-pinned, the product recipe moved back to
the
exact emitter with `data/` as an authenticated passthrough root. A clean
temporary
oracle mirror excluding the already-detected accidental PowerShell root produced
a
4,646,568-byte Rust transform. Rust GNU 1.97.1 compiled and executed it
successfully
against the untouched root `doom/`; the output contained 151 files and matched
the
clean mirror byte-for-byte, while the WAD was copied from the runtime input. The
temporary mirror, transform, executable, and output were deleted afterward. The
unexpected entry was subsequently removed explicitly, and the accepted real
oracle

and transform were regenerated.

Shamir coefficients and the payload key are derived deterministically to
preserve
byte-identical generation. The payload key schedule includes a digest over the
consumer-selected canonical source identity bytes that is not serialized into
the
transform, together with authenticated-plan and literal-stream digests.
Transform
metadata plus a guessed target plaintext is therefore insufficient to reproduce
the
payload key without source evidence. The property remains computational source
binding
and authenticated reconstruction rather than information-theoretic secrecy or
DRM;
possessing admitted source is intentionally sufficient to unlock the transform.

The Python Poly1305 implementation is reference/authoring code. The emitted
exact Rust
runtime uses a fixed-limb implementation, derives raw anchor evidence from the
actual
candidate source tree, authenticates the payload before publication, and is the
current
distributable exact-baseline format. After staging, it rechecks the exact static
source snapshot before publication and excludes authenticated dynamic
passthrough roots from that comparison. This catches persistent source drift
throughout staging; concurrent writers can still race the final check and
rename because the filesystem operation is not an atomic input snapshot.
Final publication uses atomic no-replace directory semantics on Linux
(`renameat2` with `RENAME_NOREPLACE`) and the Windows no-overwrite rename;
unsupported hosts fail closed. A competing empty output directory cannot be
replaced even when it appears between staging and publication.
Compatible/fuzzy emission remains
fail-closed
until the runtime can reproduce consumer-selected canonical identity, structural
and
anchor admission, behavior probes, bug routing, and compatible placement
semantics.

### First Compatible Placement Primitive

`relocatable.py` now removes absolute-offset dependence from source-backed exact
segments. Authoring stores only SHA-256 boundary-window locators for each source
range. A candidate materializer requires each boundary to resolve uniquely and
copies
the current candidate bytes between the resolved boundaries. This preserves
insertions
inside an otherwise stable source range and preserves whole-file candidate
differences
for source-copy instructions. Missing, duplicate, reversed, or contracted
placement

evidence rejects transactionally. Before staging, the relocatable materializer
also resolves candidate and output roots and rejects output paths inside the
candidate tree, including linked-parent aliases. This prevents ordinary output
publication from mutating its source. Status, resolution, linked-ancestor,
source snapshot, read, write, staging creation, publication, and cleanup
failures remain typed even when a foreign callback overrides exception
formatting or notes. Secondary cleanup failures preserve the original error
as their cause; unchecked host exception hooks cannot authorize publication.
Concurrent filesystem writers can still race a non-atomic input snapshot or
path check and require coordination.

Relocatable authoring now creates internal `RangeLocator`,
`RelocatableSourceRange`, `RelocatableInstruction`, and
`RelocatableAuthoringPlan` records using captured native allocation and the
original validation-backed initializers (`39c042c07`). Eight red-first
`__init__`/`__new__` regressions protect locator, segment, instruction, and
plan construction from late class hooks. All 201 focused relocatable tests
and 2,732 integrated diff tests passed; scoped Ruff and source BasedPyright
had zero errors. Direct stored-instance tampering and concurrent source
changes remain outside this boundary.

Relocatable output staging now uses import-pinned `io.open` with exclusive `xb`
mode, native `os.mkdir` for parent creation, and original `Path.parent`,
`Path.name`, and `Path.with_name` readers. Late consumer replacements of these
filesystem methods cannot send a staged file or directory to a different
location after admission. Four red-first tests reproduced redirected bytes,
intercepted staging creation, changed staging names, and altered output parents;
all pass after `65c7738a8`. Existing injected write, creation, and short-byte
receipt failures test the captured host seams rather than mutable class hooks.
All 193 relocatable tests passed post-commit; 2,619 integrated diff tests passed
before the commit. Trusted in-process module-binding mutation and external
filesystem races remain separate, unresolved isolation boundaries.

Direct relocatable plan construction rejects output file paths that also name
ancestor directories of other output files. Source and output instruction
labels reject Windows drive-absolute and drive-relative forms before placement.
Relocatable authoring now verifies the exact plan's source snapshot both before
and after constructing boundary locators. Static snapshot comparison excludes
explicit exact passthrough roots, but detects changed patched or copied files
and nonportable linked entries. These two checks remain non-atomic against
external writers.

This is deliberately a placement primitive, not compatible admission. Synthetic
tests
also prove a byte change at a required boundary still rejects. That negative
fixture
locks the reason for the next domain-mapped token layer: C comments and
formatting may
be irrelevant to identity while changing raw boundary bytes, so semantic
placement
must locate canonical units and map them back to candidate byte spans.
Target-only
literals remain local authoring material until compatible protection/emission
wraps
this layer. Exact and relocatable plan records now reject boolean range aliases,
mutable segment collections, foreign plan/instruction records, and non-Path

filesystem roots before placement begins.

### Mapped Semantic Compatible Placement

The second placement layer removes the byte-boundary limitation. Generic
`MappedView`
records canonical units together with the raw source span that produced each
unit.
`semantic.py` hashes those units with domain separation, authors non-equal
source to
target ranges using deterministic sequence matching, and stores only hashed
source
unit/context locators plus local target replacement bytes. Candidate placement
requires
a unique semantic range, edits only its mapped raw span, preserves all other
candidate
bytes, and re-maps the output to verify the exact intended canonical unit
sequence.

The first domain mapper is DOOM C. It retains raw spans through line-ending
normalization, comments, literals, directive line ends, and backslash-newline
splicing
without changing the existing identity stream. Synthetic tests preserve
candidate
comments, formatting, and an unrelated upstream function while applying a
semantic
replacement. Format-only oracle differences produce zero edits. A changed
required
semantic region remains fail-closed; later bug routing may explicitly skip a
named

correction when behavior evidence classifies that defect as already fixed.

A read-only equivalence smoke over the original and normalized local trees
processed
273 C/header files and 549,978 mapped units with zero mismatches against the
existing
canonicalizer. This proves identity-equivalent mapping, not final
compatible-tree
correctness. Mapped units now require exact byte streams, integer coordinates,
and immutable unit records; semantic locators/edits/plans require exact SHA-256
digests and immutable records, and build/apply validate views, context width,
plan, and mapper before placement.

Slotted mapped and semantic records do not make their class getters immutable.
The mapped unit/view constructor validators, canonical-key extraction, raw
coordinate readers, and semantic placement now use captured original slot
descriptors rather than class attributes replaceable after consumer code runs.
Semantic locator, edit, and plan construction and application likewise read
stored source/context digests, replacement bytes/digests, and edit sequences
through the original slots. Their explicit frozen-record constructors also
invoke validators captured before domain hooks, rather than dispatching through
replaceable class `__post_init__` methods. Compatible authoring and correction
routing consume the same pinned semantic edit sequence when selecting copy
versus patch, checking correction cardinality, and replaying required edits.
Red-first
regressions show late getter and descriptor replacements cannot certify mutable
record fields, authorize changed candidate units, move replacements to a forged
raw span, skip valid edits, or accept incomplete correction vectors. This is a
late process-hook isolation boundary, not protection against trusted code that
directly rewrites private object storage or races an external filesystem writer.

Semantic authoring now additionally constructs `SemanticLocator`,
`SemanticEdit`, `SemanticAuthoringPlan`, and `_SemanticBuildContext` with
captured native allocation and original initializer guards (`fa60753bb`).
Eight red-first `__init__`/`__new__` cases cover late class-hook substitutions
without altering mapped-source edits. All 127 focused tests passed after
commit and 2,724 integrated diff tests passed before publication; scoped Ruff
had no findings, and no new strict type diagnostics appeared. These are
class-hook guards, not isolation from trusted direct object mutation.

Semantic placement and compatible tree authoring/materialization wrap
consumer mapper and postcondition failures without evaluating foreign exception
formatters. Their typed failure keeps the original callback exception as its
cause, and compatible staging still cleans up before publication. If cleanup
also fails, both failure descriptions avoid foreign string hooks; the original
materialization exception remains the cause of the typed cleanup failure.
Compatible host adapters also contain root/path resolution, status,
ancestor inspection, source reads, snapshots, staging writes, directory
creation, and publication exceptions without calling foreign formatters or
notes getters. They retain typed causes and clean owned staging where possible;
path checks still require external writer coordination.

`compatible.py` now composes admission, behavior evidence, file topology,
semantic
placement, conservative opaque-file gates, candidate-only preservation,
target-only
conflict checks, and transactional postconditions into an in-memory compatible
plan.
Four compatible authoring and replay envelopes capture their original frozen
constructor validators. At construction, captured field descriptors prevent
late
class getters from concealing invalid instruction, request, or plan values. The
public build/materialize entrypoints and nested replay instructions also use
those stored slots before calling consumer hooks; late getters cannot redirect
the output root, erase intended target files, or replace target literals.
Correction binding reads original correction and instruction locations and
rebuilds the plan without dataclass getters. Exact-gated replay additionally
uses original exact-instruction, source-slice, oracle-literal, and file digest
slots for byte reconstruction and target-hash checks, rejecting unknown patch
segment types. Tree drift checks compare original snapshot and file fields
rather than replaceable dataclass equality, preventing a late equality override
from concealing post-plan source or postcondition candidate mutations. Twenty-
nine red-first constructor, getter, replay, binding, and tree-equality cases
plus three source-span/literal guard cases cover this scope. The full compatible
unit passes 190 tests; the full integrated diff suite passes 2,225 tests
with no exclusions. These guards isolate late class
hooks, not direct writes to instance storage, malicious consumer callbacks, or
concurrent source/output writers.

Compatible authoring, correction binding, and materialization now also
construct internal `CompatibleInstruction`, `CompatibleAuthoringPlan`,
`_BuildContext`, `_MaterializeContext`, and routed `SemanticAuthoringPlan`
receipts through original initializers and native allocation (`e0039b3fb`).
Fourteen red-first `__init__`/`__new__` cases cover late hooks after mapper,
authoring, and admission callbacks. All 257 compatible tests and 2,778
integrated diff tests passed before publication; scoped Ruff and source
BasedPyright reported zero errors, with 24 older type warnings. Allocation
hooks are isolated in child interpreters to avoid contaminating unrelated
tests. Direct modification of retained record storage and external writers
remain outside this class-hook boundary.

Named bug corrections can now be bound to deterministic semantic edit indexes.
Materialization requires every bound correction to receive exactly one
behavior `apply` or `skip` route and rejects routes for unbound corrections.
Opaque exact-gated files now hash their generated bytes against the bound target
SHA-256 before staging the file. Forged inner exact payloads reject even if the
candidate source hash and the authoring plan's declared hashes match.
Nested exact source paths, when present, must also match the outer compatible
instruction's source path during direct plan construction; literal-only exact
instructions retain their source-free representation.
The candidate byte-tree snapshot is captured before staging and checked again
after the optional read-only postcondition. Staged file bytes are also
re-snapshotted across that callback. Observed source or staging changes,
additions, removals, or symlinks reject before publication and trigger owned
staging cleanup. These checks are not an atomic snapshot and cannot prevent a
concurrent writer racing the final check-to-rename gap; external coordination
remains necessary.
Skipped edits preserve upstream fixes while unconditional semantic edits still
apply. Consumer domains still need to author those bindings, and target-only
bytes remain local authoring material until compatible source-bound

serialization exists.

The first full DOOM compatible-authoring smoke exposed a scalability defect in
generic
sequence matching and did not finish within the runner limit. The replacement
matcher
uses unique canonical k-grams at widths 8/4/2/1, a monotonic LIS anchor chain,
common
prefix/suffix trimming, and recursive gap partitioning. With that matcher the
same
read-only plan finishes in 11.159 seconds: 117 semantic-patch files, 7 mapped
candidate
copies, 2 opaque exact-gated files, and 26 target-only creates across 152 target
paths.
Those semantic files contain 6,257 edits and 251,933 raw replacement bytes.

### Exact Baseline and Compatible Variants

For the exact source tree used during generation:

```text
source + generated transform == oracle byte-for-byte
```

A later compatible source variant may preserve legitimate upstream differences
rather than matching the historical oracle hash. Such output must satisfy all
declared postconditions, behavior probes, provenance checks, and downstream
validators.

### Threshold Policy

Similarity percentages are consumer configuration, not generic constants. The
first DOOM quality recipe records exploratory values of 0.50 structural
similarity, 0.66 stable-anchor coverage, and 0.80 behavior similarity. Those
values remain provisional until calibration fixtures justify them.

### DOOM Consumers

The first consumer is DOOM quality generation:

```text
root doom/ + local normalized oracle
             |
             v
src/research/algorithms/domain/algorithms/doom/generator/quality.py
             |
             v
       algorithms/diff
             |
             v
src/research/algorithms/composition/algorithms/doom/quality/main.rs
```

The second exact consumer now reuses the same generic engine for deterministic
amalgamation:
normalized multi-file DOOM plus a local accepted single-file oracle produces the
source-bound transformation used to materialize canonical `doom.c`.

## Invariants

- The engine remains agnostic to DOOM, C, Malbolge, and license-specific policy.
- Canonicalization used for identity cannot silently delete source provenance.
- Behavior-only similarity cannot replace source-lineage evidence.
- Target material is not materialized before configured source-binding evidence
  succeeds.
- Exact-baseline generation/materialization is deterministic and byte-identical.
- Ordering does not depend on filesystem enumeration, locale, current time, or
  unversioned randomness.
- Similarity percentages are technical policy, not legal thresholds.
- Source binding is not documented as proof of copyright/license compliance or
  any jurisdictional conclusion.

## Failure Behavior

The generator and emitted transform fail explicitly on insufficient structural
similarity, insufficient anchor coverage, failed mandatory probes, failed source
binding, ambiguous source matches, malformed transform data, violated
preconditions, or failed output postconditions.

Source-binding failure occurs before accepted target files are published.
Partial
target trees are never treated as accepted output.

## Verification

Generic tests use only repository-owned synthetic fixtures and cover:

- exact byte reconstruction;
- repeated deterministic generation/materialization;
- comment-only edits and whole-tree reformatting;
- source insertions that preserve stable anchors;
- created, deleted, moved, and modified files;
- binary payload policy when enabled;
- candidates immediately above/below admission thresholds;
- mandatory behavior mismatch and bug-already-fixed compatibility;
- wrong-source, no-source, and behavior-clone rejection;
- source-binding failure before target publication.

Repository closure uses `jig validate --root .` after focused tests pass.

## References

- `src/research/algorithms/composition/algorithms/diff/README.md`
- `src/research/algorithms/domain/algorithms/doom/generator/README.md`
- `docs/technical/interoperability/doom-modernization.md`
- `docs/technical/interoperability/doom-amalgamation.md`
- `docs/legal/adr/legal-research-and-repository-boundary.md`
