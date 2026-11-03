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

Generator preflight now reads native recipe paths from their import-captured
original `PurePath` storage, instead of relying on replaceable class getters
(`db9606154`). Six red-first tests cover NUL/surrogate path components being
laundered or valid paths rejected by late `_raw_paths`/`__getattribute__`
patches. All 219 focused generator and 3,190 integrated diff tests passed after
publication. Original-slot path admission does not prevent direct stored-object
mutation or racing external filesystem writers.

Even the captured original `Path.resolve` delegates to the mutable host
`os.path.realpath`. Recipe output containment now requires the import-original
realpath function before and after each path resolution and rechecks it after
consumer-domain preflight, before exact generation (`b60e927dc`). Four red-first
regressions cover false source/oracle containment verdicts, false denial, and a
consumer callback replacing the resolver. All 223 focused generator tests pass;
this fail-closed hook check does not provide atomic protection against concurrent
host mutations or filesystem writers. A postcommit diff-suite rerun passed
all 3,205 tests.

The captured `Path.resolve` also delegates through mutable path-conversion and
construction hooks even when `os.path.realpath` itself is unchanged. Generator
preflight now verifies import-original `os.fspath`, `builtins.type`, and both
base `Path` and concrete platform path methods (`__fspath__`, `__str__`,
`with_segments`, `__getattribute__`, `__new__`, and `__init__`) before and after
resolution and following domain preflight (`2d566f119`). Twenty-five new
regressions cover contained outputs disguised as external paths, forged
denials, and post-domain hook mutation. All 248 focused generator tests pass;
scoped Ruff and BasedPyright report zero errors. A shared-checkout diff run
passed 3,320 tests and failed two concurrent, uncommitted probe-execution
regressions in a separate owned file. This check is not atomic against host
mutation or external filesystem races, nor does it validate every host hook.

A further audit found that original `os.path.realpath` dynamically selects
`os.lstat`, `os.readlink`, `os.getcwd`, and `stat.S_ISLNK`; late replacements
could disguise a source-targeting output symlink as a safe directory, or retarget
a relative output. Generator preflight now verifies these import-original
functions before and after resolution (`138599216`). Eight additional
red-first cases pass, bringing focused generator tests to 256; scoped Ruff and
BasedPyright remain zero-error. Repository-wide `jig doctor` exited cleanly,
but `jig check` did not complete within the 120-second validation budget.
After concurrent probe and admission fixes landed, an independent post-push
full diff-suite rerun passed all 3,340 tests. Hook identity checks are not
atomic under concurrent host or filesystem writes.

The Rust source emitter protects its own runtime template from output overwrite
with the same import-original `os.path.realpath` identity requirement before
and after resolving the template and destination (`f15620ff7`). Two red-first
cases prove that a forged host resolver can otherwise hide a collision or
execute an untrusted denial callback. All 152 focused emitter tests pass;
external writers still require coordination.

Emitter template-identity preflight now additionally pins the import-original
`os.lstat`, `os.readlink`, `os.getcwd`, and `stat.S_ISLNK` helpers used by
`realpath`, and the native `Path` construction/resolution hooks
(`c6154acf4`). Eight red-first host-hook, factory, and symlink-alias
regressions now fail closed before invoking foreign callbacks. All 160 focused
emitter and 3,348 integrated diff tests passed; scoped Ruff, strict
BasedPyright, and diff checks were clean. These identity checks are not atomic
against concurrent host or filesystem mutation.

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

Exact tree roots, snapshot traversal, source reads, and staged writes now reject
late native `pathlib` formatter/cache substitution (`6b230250e`). Previously a
replaced `Path.__getattribute__` for the `_str` cache could turn a requested
source tree into a different directory while still returning a valid snapshot.
Original class-hook identities are checked before path resolution and tree
publication; direct descriptor-bound file reads continue to ignore a replaced
`os.fspath` when the native file identity remains valid. Seven new test cases
cover late cache, formatter, descriptor, and filesystem-path hooks; 254 exact
and 2,916 integrated diff tests passed. Scoped Ruff and BasedPyright had zero
errors. The check is not atomic against external writers or direct instance
storage changes; repository-wide Jig doctor was degraded (graph absent), and
a 110-second Jig check timed out during native validation.

The exact tree boundary independently rejects late changes to import-original
`os.path.realpath` before source and output resolution (`97f5f2a30`). Three
red-first source/output redirection and false-denial cases now fail closed;
a direct descriptor-bound file read still works under a replaced resolver.
All 270 focused exact and 3,240 integrated diff tests passed. This does not
make filesystem resolution atomic against concurrent writers.

The captured native `Path.resolve` still consults `os.lstat`, `os.readlink`,
`os.getcwd`, and `stat.S_ISLNK` inside the original host realpath. Exact root,
output, and nested-file resolution now verifies their import-original identities
before and after each resolution (`32037e9c3`). Four late-hook symlink-alias
cases and three mid-resolution substitutions failed red-first, then passed with
283 postcommit exact tests and 3,398 integrated diff tests. Scoped Ruff, source
strict BasedPyright, and diff checks passed. The guard does not make
filesystem resolution atomic against external writers or concurrent host
mutation; direct descriptor-bound reads remain independent of these hooks.

The same native path operations also dispatch through mutable
`PurePath.with_segments`, `Path.with_segments`, and concrete `Path` allocation
and initialization hooks. Exact resolution now checks those class hooks before
and after resolution (`94613c2cc`); eight red-first factory substitutions
and three mid-resolution cases fail closed, while descriptor-bound file reads
still work with an unrelated late factory. All 295 postcommit exact tests,
scoped Ruff, strict source BasedPyright, and diff checks pass. One integrated
run reached 3,426 passes and six failures in concurrently edited behavior
context tests; a subsequent independent stable-snapshot run passed 3,432 diff
tests. The checks are not atomic against external host or filesystem races.

Even a pinned `Path.walk` delegates to mutable host `os.walk` and `os.scandir`,
while `os.walk` resolves nested children through `os.path.join`. Exact tree
snapshots now require the import-original identities of all three hooks
(`dccb70b71`). Six red-first full and passthrough-excluded snapshot cases
prove late replacements could silently omit included source files. All 276
focused exact tests pass with zero scoped Ruff or strict BasedPyright errors.
The new guards address late hook substitution, not direct module-state
mutation or concurrent filesystem races.

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
The domain import boundary now pins the original importlib spec constructor,
module constructor, and source-file loader execution method (`97ea0cdff`).
Late replacements that previously loaded an unselected Python module despite
native filesystem identity checks fail before module registration or execution.
Three red-first substitution tests passed, with 93 focused domain and 3,210
integrated diff tests green. This is a local post-import hook guard, not
protection from direct internal mutation or concurrent host filesystem writers.
The same boundary pins source-loader `get_code`, `get_data`,
`get_filename`, and `source_to_code` (`1eb1b012a`). Four further red-first
cases proved that each mutable reader could execute unselected source bytes.
All 97 focused domain and 3,240 integrated diff tests passed. The check does
not isolate direct trusted-state mutation or concurrent filesystem writers.
The loader also pins the source-loader initializer and module factory
(`46985396c`): two red-first cases reject path redirection and a pre-execution
side effect. Its `path_stats` hook is now pinned (`d89be2aa0`); one red-first
case proved that forged source metadata could authorize cached bytecode from an
unselected file. All 100 focused domain and 3,255 integrated diff tests pass;
scoped Ruff and strict BasedPyright report zero errors. Direct trusted-state
mutation and concurrent filesystem or bytecode-cache writes remain out of scope.
Rejected domain loads now restore the original `sys.modules` registration
(`38ee4b9bc`) even if executing consumer code replaces or deletes its own key.
The loader also rejects successful execution or late hook lookup that changes
that registration instead of returning an accepted hook bundle under a foreign
module identity. Six initial red-first failures and fourteen total new cases
cover initial imports, accepted-module reloads, execution failures, missing
hooks, and late mutations. All 114 postcommit domain and 3,538 precommit
integrated diff tests passed, with scoped Ruff, strict source/test BasedPyright,
and diff checks clean. This guards only the import registration boundary;
consumer code is still trusted and external concurrent writes are not isolated.

Native domain-module path validation now also pins the original internal
`PurePath` parsing, parent-construction, formatting, cached-slot descriptors,
and host `os.path.join` resolution dependency (`d3ae694d0`). Original
`Path.parent` and `Path.__str__` methods otherwise still dispatch through
mutable internal factories. Two red-first tests exposed a symlinked-parent
admission bypass and a late formatting redirection.

A further import-stage test rejects consumer changes to these factories and
restores registration; a fourth proves a replaced `builtins.any` cannot disable
the guard. All 118 focused domain tests pass postcommit; Ruff, strict
source/test BasedPyright, and diff checks are clean. An independent combined
diff run passed 3,602 tests.

Domain module loading additionally checks imported native `PurePath` parser
components and host `os.path.splitroot`/`splitdrive` helpers before and after
uncached path normalization (`32caad32e`). A substituted splitter previously
redirected an admitted module path to unrelated code. Two red-first cases and
all 120 focused domain tests pass postcommit; scoped Ruff, strict source/test
BasedPyright and diff checks are clean. Later shared validation passed 3,616
diff tests.

This hook guard is not an atomic external path snapshot.

The guard does not sandbox authorized consumer code, prevent direct trusted
object mutations, or make host filesystem checks atomic. Global Jig remains
unverified (`jig doctor` reports the compiled graph absent).

Neither status check nor import is atomic against external filesystem writes;
this is not a sandbox for trusted consumer-domain code.
Generator domain preflight now revalidates the original stored fields of
callback-returned `SourcePinEvidence` with its captured native constructor
guard (`a27f430de`). Previously, an object built with `object.__new__` could
pass the exact-type check despite a missing digest, zero/boolean file count,
or malformed digest, and the generator would proceed to oracle preflight.
Four red-first malformed-record variants and three late validator/getter-hook
regressions now reject that evidence with `DomainContractError` before the
oracle callback. All 263 focused generator tests passed; strict source/test
BasedPyright reported no errors, pinned Ruff findings matched the preexisting
baseline, and the diff check was clean. This validates receipt shape and
invariants, not the truth of a consumer callback's claim or concurrent changes
to external files. Repository-wide Jig verification remains unverified.
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

Exact generation also binds source identity replay and post-protection drift
checks to the original stored `ExactAuthoringPlan` source and target snapshots
(`8bc123dd2`). Late class properties or `__getattribute__` hooks could
previously substitute a changed source or oracle snapshot for the planned
evidence, allowing stale material to reach Rust emission. Eight
descriptor/getter regressions now prove rejection of changed trees and continued
use of valid stored plans. All 213 generator and 2,874 integrated diff tests
passed before concurrent exact-reader changes. Scoped Ruff, strict
BasedPyright, and diff checks were clean. Jig doctor was degraded with its
graph absent, and a 100-second Jig check timed out during native validation.
This guard does not isolate direct stored-instance mutation or external
filesystem races.

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

The nested model admission boundary also reruns captured original validators
for exact native file records inside `TreeSnapshot`, segments inside patch
instructions, and both source/target snapshots and instructions inside
`ExactAuthoringPlan` (`1d0a9d529`). Previously `object.__new__` records with
malformed hashes, sizes, paths, segment coordinates, or inconsistent instruction
kinds could bypass child constructors. Incomplete stored slots now raise typed
`TreeModelError` rather than leaking `AttributeError`. Nineteen red-first cases
passed, with 94 model tests and 3,015 integrated diff tests passing before
commit and 167 model/fingerprint tests passing after commit. Scoped Ruff,
strict BasedPyright, and diff checks were clean. These checks are not atomic
against instance mutation or external source-tree races; Jig doctor remains
degraded (graph absent), and the bounded global check timed out.

Exact materialization now reruns the import-captured `ExactAuthoringPlan`
validator before filesystem access (`ddf59bc5d`). Ten red-first cases reject
fabricated exact plans with malformed nested metadata or missing slots,
including records altered through late class hooks. All 266 focused exact
tests passed after commit, and 3,102 integrated diff tests passed before it;
scoped Ruff and source BasedPyright had zero errors. Jig doctor remained
degraded and a bounded 115-second global check timed out without a pass.
Direct instance mutation after preflight and concurrent filesystem writers
remain outside these guards.

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

Source-pin root admission also rejects late `pathlib` class getter and cache
substitutions before using the captured path formatter (`bce5af0c1`). The
original class-chain dependency snapshot prevents forged root spellings from
selecting another tree and producing unrelated provenance evidence. Fifteen
red-first class, descriptor, and builtin cases passed, as did 140 provenance
tests rechecked after publication. The integrated diff suite previously passed
2,840 tests before this provenance change was committed. Scoped Ruff and
source BasedPyright remained error-free. This protects in-process class-hook
substitution, not direct stored-instance edits or external filesystem races.

The public `require_source_pin()` boundary now revalidates both the exact
native `SourcePin` revision record and the resulting `SourcePinEvidence`
snapshot receipt using the original captured validators (`30bcce4c5`).
A constructor-bypassed pin with an empty revision label, incomplete fields,
or foreign numeric/digest subclasses could previously certify a matching
filesystem snapshot despite invalid revision metadata. Forged exact snapshot
receipts with equality-compatible foreign values are now also rejected before
comparison. Ten initial red-first cases exposed the bypass and four further
cases cover equality-compatible foreign types; all 154 provenance and 3,074
integrated diff tests passed. Scoped Ruff, strict BasedPyright, and diff checks
were clean. This does not provide concurrent writer exclusion or isolation
from trusted direct stored-instance mutation, and global Jig validation still
lacks a green result.

Source provenance root resolution now checks the import-captured host
`os.path.realpath` before preflight, again after the root status receipt,
and after the original `Path.resolve` (`11740f2b4`). A late host resolver
could previously redirect an admitted source snapshot to a different tree,
reject a valid pin, or be installed during the status callback. Six red-first
snapshot/pin cases prove the guard; all 160 provenance and 3,273 integrated
diff tests passed, with scoped Ruff, source strict BasedPyright, and diff
checks clean. Existing unrelated test typing diagnostics remain. These
identity checks do not make resolution atomic against external filesystem
writers or isolate trusted direct mutation. Jig doctor remains degraded
(graph absent), and a bounded 120-second global check timed out without a
repository-wide green verdict.

The original `Path.resolve` still calls the host resolver's mutable
`os.fspath`, `os.lstat`, `os.readlink`, `os.getcwd`, and `stat.S_ISLNK` helpers,
and constructs its result through replaceable pathlib factories. Source-pin
normalization now checks their import-original identities alongside the
existing realpath guard before and after resolution (`6379d6e85`). Eight
red-first cases cover redirected regular-root symlink status, linked parent
redirection, relative-root working-directory substitution, and
`Path.with_segments` result replacement for both snapshot and pin-verification
paths. All 168 postcommit provenance tests and 3,366 integrated diff tests
passed; scoped Ruff, strict source BasedPyright, and diff checks were clean.
Existing provenance-test typing diagnostics remain outside this scoped change.
These checks cannot make filesystem snapshots atomic, isolate external writers,
or prevent direct mutations of trusted module state. Jig doctor remained
degraded (cached graph absent), and the repository-wide check was not green.

A follow-up source-pin identity audit (`c883eb6cc`) identified a distinct
lexical alias on POSIX: a literal `subdir\file.c` entry and an otherwise
empty `subdir/` could previously certify the same path digest and revision
pin as a genuine `subdir/file.c` from another tree. Discovered file and
directory labels now undergo the same portable canonical-path admission as
pinned roots. Host-native Windows separators are normalized only on Windows;
literal POSIX backslashes, reserved device names, alternate streams, and
trailing-dot entries reject before any snapshot can be certified. The same
change pins `stat.S_ISDIR`, which original strict `os.path.realpath` also calls,
against late false-directory and false-denial substitutions. Nine red-first
cases cover both surfaces; all 177 postcommit provenance and 3,386
integrated diff tests pass, as do scoped Ruff, strict source BasedPyright,
and diff checks. Existing test-file typing errors, external
filesystem races, and the incomplete global Jig gate remain limitations.

Provenance relative-label derivation now also pins dependencies of the
import-original `Path.relative_to` (`87cac5fb1`): `PurePath.parents` and
equality methods, inherited `_PathParents` membership/iteration, its class
alias, `pathlib.chain`, and the original builtin `hasattr`, `enumerate`,
`isinstance`, `len`, and `str` functions. Eight red-first hook substitutions
previously executed late callbacks before source snapshot admission. The
source-label guard rejects those changes before and after relative derivation;
all 185 provenance and 484 combined provenance/compatible tests pass
postcommit.

Scoped Ruff, source strict BasedPyright, and diff checks are
clean, while 51 previously existing provenance-test typing errors remain.
External filesystem races, direct trusted-state mutation, and global Jig
verification are not closed by this in-process guard.

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

The Python Rust emitter also refuses late changes to the native `pathlib`
string/attribute dependency chain and `os.fspath` before checking output
identity or opening staging files (`85914b0a5`). Three red-first regressions
covered a substituted path getter, redirected file-status evidence, and a
multi-part `os.fspath` rewrite. The emitter's postcommit suite passed 140
tests; the integrated diff suite passed 2,853 tests before that commit, with
scoped Ruff and strict BasedPyright clean. This rejects tested in-process hook
substitution, not concurrent filesystem replacement or arbitrary trusted
module-state mutation.

The emitter's path-string and output-template resolver guards now pin the
import-original `any()` (`a63aeb867`). A later consumer had been able to
replace the global helper and bypass the native `pathlib` hook checks, invoking
substituted `_tail` or `with_segments` behavior during output preflight.
Two red-first regressions are green; all 162 postcommit emitter tests passed,
with scoped Ruff, strict source/test BasedPyright, and diff checks clean.
The guard is not isolation against concurrent filesystem writes or direct
trusted module-state mutation.

Emitter parent-directory staging now also pins the import-original
`reversed()` (`e7ec05dca`). A late replacement previously erased the parent
walk, silently leaving a nested output stage uncreated. One red-first
regression, all 163 postcommit emitter tests, scoped Ruff, strict source/test
BasedPyright, and diff checks passed. The complete shared diff suite passed
3,602 tests in 128.99 seconds after the fix, with concurrent peer changes
present. Host filesystem races and direct trusted module-state edits remain
outside this guard.

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

Follow-up `0f31ab19f` closes two further compiled-runtime admission bypasses:
a symlinked source root spelled with a trailing slash or `/.` previously made
`symlink_metadata` follow the link. The runtime now normalizes lexical path
components before its no-follow status query. Both variants failed red-first;
three linked-root rejection cases and two real-directory positive variants
passed, including their source/output integrity checks. All 137 emitter tests
passed postcommit; 2,850 integrated diff tests passed before commit. Scoped
Ruff, emitter-source BasedPyright, and diff checks passed. Parent-link aliases
and concurrent filesystem mutation remain outside this narrow root check.

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

Compatible materialization also pins `os.path.realpath`, `os.fspath`,
`os.lstat`, `os.readlink`, `os.getcwd`, `stat.S_ISLNK`, and original
`Path` construction/resolution hooks (`14d78e21b`). Checks occur before
converting requested paths and both before and after resolving source or
output roots and nested file paths. An import-late host realpath previously
admitted a destination inside the candidate tree. Ten new regressions
cover that containment forgery, four host helper substitutions, three path
factories, a symlink-classifier substitution, and mutation during resolution.
All 283 compatible tests passed postcommit; scoped Ruff, source-only strict
BasedPyright and diff checks passed. The broader shared suite reached 2,966
passes but stopped after three relocatable publication failures while another
agent's uncommitted `ctypes.CDLL.__new__` guard was in flight. This does not
constitute an integrated clean verdict or exclude external filesystem races.

Compatible output containment now pins import-original `builtins.any`,
`isinstance`, and `hasattr` along with the `PurePath` parent/equality hooks,
the `_PathParents` class alias, and its inherited membership/iteration
dispatch (`e778b06f9`). Original `Path.is_relative_to` still reads those
mutable dependencies. Seven red-first cases showed substituted path hooks
executing before rejection or forged `any()` causing false admission/denial;
two additional cases reject silently emptied parent ancestry. The materializer
checks the hook identities before and after containment. All 299 compatible
tests and 565 combined compatible/relocatable tests pass postcommit, with
scoped Ruff and diff checks clean. Strict BasedPyright still reports 14
older source and 106 older test diagnostics, none in the modified ranges;
there is no clean global Jig verdict. Direct trusted-state mutation and
concurrent host/filesystem races remain outside this guard.

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

Directory publication previously trusted `Path.__str__` through a captured
callable, which still dispatched late path cache and class getter hooks. Both
`Path.__getattribute__` and `os.fspath` could redirect a native destination
while preserving exact `Path` type. Signed `25c0a4d38` pins the native path
class dispatch chain; POSIX spelling derives from original raw-part storage,
not mutable path hooks. Windows uses the original cached-string slot and
fails closed when its uncached path formatting depends on a changed host hook.
Four red-first redirection cases and two platform-class hook cases now prove
rejection or unredirected publication. Fourteen lexical edge fixtures and
4,368 exhaustive small combinations agreed with native POSIX spelling. All
87 focused publication and 2,840 integrated diff tests passed postcommit,
with scoped Ruff, strict BasedPyright, and diff checks clean. Jig doctor was
degraded and a bounded 100-second `jig check` timed out during native
validation scheduling; no repository-wide clean verdict is asserted. Direct
private object mutation and concurrent external filesystem writers are not
isolated by this guard.

The Linux no-replace publisher also pins original `ctypes.CDLL` class dispatch
and the module's native `_dlopen`, `_CFuncPtr`, and function-pointer flag
bindings (`41c16504e`). A late symbol/getitem override or replaced pointer
base previously could call overwriting `os.rename` on an occupied empty
output directory, then satisfy the moved-inode attestation. Four red-first
overwrite cases and ten additional loader/ABI mutation cases now reject
changed dependencies with `ENOTSUP` before loading libc. All 101 publication
tests passed after commit; 3,102 integrated diff tests passed on the live
shared checkout before commit, with scoped Ruff and BasedPyright at zero
errors and clean diff checks. Jig doctor remained degraded (graph absent);
a bounded 105-second global check timed out at native-validator scheduling.
These in-process dispatch guards do not isolate direct module-private
mutation, malicious native code, or concurrent external filesystem writers.

A later Linux publisher audit found `ctypes.CDLL.__new__` missing from the
class-dispatch identity checks (`709f045e6`). Replacing this allocator with a
foreign library returning an overwriting `os.rename` shim could silently
replace an occupied empty destination. The guard now rejects this late
constructor substitution before native loading. One red-first reproduction,
102 postcommit publication tests, and 3,381 precommit integrated diff tests
passed; scoped Ruff, strict BasedPyright, and diff checks were clean. The
allocator regression runs in a child process because even a restored Python
3.14 class patch can corrupt subsequent native CDLL construction. Direct
private state mutation, malicious native code, and concurrent writers remain
out of scope.

The publisher's path-class and Linux `ctypes` loader-integrity guards now use
an import-pinned `builtins.any` (`22e34f392`). A late override returning
`False` previously hid a forged `renameat2` dispatcher and allowed it to be
called before final publication attestation rejected the incomplete move.
An override returning `True` could instead cause a spurious path rejection.
One red-first occupied-target case and three additional path/loader
regressions verify that the original aggregate is retained and hostile
callbacks are not invoked. All 106 postcommit publication tests and a
514-test postcommit publication/behavior/provenance run passed; scoped Ruff,
strict source/test BasedPyright, and diff checks were clean. A separate full
diff run exceeded its command-wrapper limit without a retrievable verdict;
the 3,560-test prior integrated result predates this publication change.
The global Jig gate remains unverified; direct trusted-state mutation,
malicious native code, and external filesystem races remain excluded.

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

Public anchor selection and coverage now also revalidate the original stored
`AnchorPolicy` and `StableAnchor` invariants (`e245d7ee3`), even for exact native
objects allocated without their constructors. Forged zero or boolean window
sizes, invalid selection moduli, malformed digests and offsets, and missing
native slots now fail with `FingerprintPolicyError` before selecting windows or
crediting lineage coverage. Fifteen red-first tests cover both reference and
candidate records. All 73 fingerprint tests and 2,953 integrated diff tests
passed before publication; 211 fingerprint/admission tests passed after commit,
with scoped Ruff, strict BasedPyright, and Git diff checks clean. This is input
admission, not protection against direct stored-instance mutation, arbitrary
consumer execution, or concurrent external writers. Jig doctor remains degraded
with no generated graph; a bounded 105-second `jig check` attempt timed out
(exit 124) at native-validator scheduling, without a clean Jig verdict.

### Implemented Tree-Level Admission

Source identity and source-binding share-envelope Windows filename checks now
pin the import-original `bool()` (`a74091b47`). Replacing `builtins.bool`
previously admitted reserved-character filenames or denied safe paths, altering
source lineage and distributable binding admission. Two red-first parameterized
cases per layer cover both directions, with three source-identity constructors
exercised in each admission case. All 362 combined admission/source-binding
tests passed postcommit; scoped Ruff, strict source/test BasedPyright and diff
checks were clean. This closes the tested late builtin hook, not direct trusted
module-state mutation or concurrent host filesystem changes.

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

Native source-lineage admission now also reruns the import-captured validators
on exact `IdentityTree`, nested `IdentityFile`, `AdmissionPolicy`, nested
`AnchorPolicy`, and `FileAdmissionEvidence` records (`4bf88a776`). This closes
constructor-bypass cases in which malformed paths, mutable bytes, invalid
thresholds, or missing native slots could reach lineage scoring. An exact
`TreeAdmissionEvidence` with only an empty reasons slot can no longer certify
`admitted=True` without revalidating the complete policy-bound receipt.
Twenty-four targeted regression cases include red-first reproductions and
valid direct evidence checks; 162 focused admission and 3,004 integrated diff
tests passed, with strict source BasedPyright at zero errors and no increase in
Ruff diagnostics. The check does not guard direct stored-instance mutation or
concurrent source writers; repository-wide Jig remains degraded with no clean
verdict after a bounded 105-second check timed out (exit 124).

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

Behavior profile and observation containers now validate each exact native
nested probe/observation with its captured original validator (`d87bd34c4`).
Public behavior evaluation and direct evidence construction also rerun the
original outer profile/observation validators, while direct reads of
`BehaviorEvidence.admitted` validate the entire receipt before trusting its
rejection reasons. This closes constructor-bypass paths that previously let
empty or foreign digest bytes, missing fields, and forged compatibility or
bug results count as passing behavior. Eighteen red-first nested, raw-outer,
and public-verdict cases pass. All 167 focused behavior and 3,033 integrated
diff tests passed; scoped Ruff, strict BasedPyright, and diff checks reported
zero errors. Direct mutation of trusted records after checks, trusted module
internals, and concurrent writers remain outside this process-level boundary;
the global Jig verdict remains unavailable.

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

The public transform gate now revalidates exact native source-lineage and
behavior receipts through captured original validators (`3e4a58b83`).
Constructor bypasses that install an empty `reasons` slot into otherwise
uninitialized or inconsistent evidence can no longer certify admission; the
gate reports a typed `AdmissionError`. Direct reads of
`TransformAdmissionEvidence.admitted` also rerun the original combined
validator (`451e81a09`), rejecting fabricated gate records and inconsistent
verdicts despite late class-validator substitutions. Nineteen red-first
regression cases cover both repairs; all 62 focused gate and 2,994 integrated
diff tests passed after implementation, with scoped Ruff, strict
BasedPyright, and Git diff checks clean. The repository-wide Jig check has
no new green verdict; direct mutation of trusted stored fields, trusted
module internals, and concurrent filesystem writers remain outside this
process-level guard.

The public `.admitted` verdicts of `TreeAdmissionEvidence`, `BehaviorEvidence`,
and `TransformAdmissionEvidence` now require the exact native receipt type
(`c868d4a8b`) before calling stored-slot validators. An inherited subclass
getter previously certified foreign receipt storage, while unbound getters
leaked a raw type error or misclassified the receiver. Six red-first cases now
fail with each boundary's typed admission error. All 397 focused
admission/behavior/gate tests, 3,340 integrated diff tests, and 670 postcommit
admission/behavior/gate/compatible tests passed. Scoped Ruff and strict
source/test BasedPyright were clean, as were diff checks. The unrelated
existing descriptor-hook test annotation was also made type-exact. Existing
formatting drift is untouched. `jig doctor` remained degraded with its graph
absent and a 105-second global check timed out, so there is no repository-wide
passing verdict. Trusted direct storage edits and external writers remain
outside these getter protections.

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
Public probe-batch admission now reruns import-captured validators on
`ProbeRunContext`, every `ProbeProgram`, and nested `ProbeCommand`, executable,
and structured path-argument records (`5d6a19de9`). Exact native instances
allocated without constructors previously entered host preflight with invalid
limits, digest selectors, roots, identifiers, or traversal paths; incomplete
program slots leaked raw `AttributeError`. Nine red-first regressions now fail
closed with `ProbeProgramError` before filesystem/process work. All 366 focused
probe tests and 3,201 integrated diff tests passed, with clean scoped Ruff,
strict source BasedPyright, and diff checks. This does not sandbox arbitrary
consumer commands, prevent direct stored-object mutation, or make filesystem
snapshots atomic against external writers. A repository-wide Jig pass remains
unverified.

The portable probe executor now verifies import-original `os.path.realpath`
identity before and after all five native path resolution sites (`802787e78`).
Previously a late replacement could redirect the probe source root or tool,
launder a rooted symlink escape, or hide a repository alias to the source.
Four post-import replacements and one mid-resolution mutation failed red-first
and now reject with `ProbeExecutionError`.

All 371 focused probe tests and 3,289 integrated diff tests passed. Scoped
Ruff and strict source BasedPyright were clean; the test file retains six
pre-existing type errors outside the new tests. Repository-wide Jig check
reported unrelated hard failures and remains unverified. The resolver identity
guard is not atomic against concurrent host mutation or filesystem writers.

Probe execution now also verifies the original native `pathlib` cache and
conversion hooks before trusting a path (`ff5391d09`). Captured
`Path.__str__` still read replaceable `_str` descriptors and
`__getattribute__` hooks; a forged getter could launder a NUL-bearing root
or substitute another executable for host status. Runtime preflight additionally
rejects late `Path.__str__` and `os.fspath` substitutions before resolutions
or executable admission. Exceptions raised by these guards retain their owned
probe type rather than triggering a later unsafe path formatter.
The original `Path.resolve` also delegates to replaceable `Path.with_segments`;
that dependency is now pinned (`17b56bba3`). Two red-first source-root/tool
redirections fail closed, with 379 focused and 3,340 integrated tests passing.

Four cache/getter cases and two late string-method cases failed red-first and
now pass without executing the substituted hooks. All 377 focused probe tests
and 3,324 integrated diff tests passed. Scoped Ruff and strict source typing
were clean; the six inherited test typing errors and broader Jig failures
remain outside the patch. Hook identity checks do not make external filesystem
or concurrent host-code mutations atomic.

The probe resolver also pins import-original `os.lstat`, `os.readlink`,
`os.getcwd`, and `stat.S_ISLNK` (`8edcd9f7b`), which original host realpath
still consults beneath `Path.resolve`. A substituted `os.lstat` was reproduced
returning a symlink alias rather than its real target, so later probe root or
tool containment could be laundered. Four late-hook replacements and one
mid-resolution replacement now fail closed. All 384 postcommit probe tests
and 3,391 precommit integrated diff tests passed. Strict probe-source typing
retains three unrelated existing errors; full Jig validation has no green
verdict. The identity checks remain non-atomic against external writers or
concurrent process-global mutation.

Probe structured relative paths now pin the import-original `Path.joinpath`
(`8df8dbbbb`) and use that original for rooted argument construction.
A late hook previously redirected a requested file to another, still-contained
file, defeating the selected-path identity without escaping the source,
repository, or scratch root. Six red-first cases cover those three roots with
both path arguments and rooted executables. All 390 focused probe tests passed
postcommit; the integrated diff run stopped after 525 passes and one failure
in concurrently uncommitted behavior-context tests, so no clean shared-suite
verdict is claimed for this revision. New probe lines introduce no additional
Ruff or strict BasedPyright diagnostics; existing file findings persist.
Path-hook identity remains non-atomic against host and filesystem races.

Native probe root and tool resolution also checks the original `Path.__new__`
and `PurePath.__init__`, plus `__new__`/`__init__` along the concrete native
path class hierarchy (`db51f0c54`). A replaced path constructor could have
returned an unrelated, still-native path after `Path.resolve`, bypassing exact
type admission. Four original base-hook cases and four newly reproduced
concrete-platform cases now reject before consulting the substituted hook.
All 398 probe tests passed after the code commit; a shared precommit diff run
passed 3,468 tests. Scoped Ruff and diff checks passed. Strict probe-source
typing still reports three findings on unchanged lines, while the test file
has pre-existing unrelated findings; no new constructor-test diagnostics were
observed. Jig doctor remains degraded and the global check has no passing
verdict. Process-global changes during a check and external filesystem races
remain outside this in-process identity guard.

Native probe resolution now snapshots the exact host platform `Path` type
at import time, rather than constructing a fresh `Path()` while validating
later untrusted root records (`08e6926e4`). A changed constructor previously
executed before the path-class check. The probe execution boundary separately
pins concrete-platform `__str__`, `with_segments`, and `joinpath` hooks before
resolving tools and roots without changing the original record-admission
semantics. Four constructor-before-admission and four concrete resolver-hook
cases reproduced the vulnerabilities. All 406 postcommit probe tests and
3,491 fresh integrated diff tests passed; scoped Ruff and diff checks were
clean. External races and in-process mutations of already trusted storage
remain outside this guarantee.

Probe rooted containment also now pins the original `parents` and equality
hooks of native `PurePath` classes and the alias and method-resolution chain
of the internal `_PathParents` sequence (`694a82678`). The original native
`relative_to` consulted those replaceable hooks even when the resolver and
`Path.relative_to` entry points were unchanged; late substitutions wrongly
admitted structured source paths escaping through directory symlinks. Four
base/concrete ancestry/equality and three parent-sequence/alias cases failed
red-first, while two additional tests exercise changes during containment.
Checks now also run after containment and around internal source overlap
checks. All 415 focused probe and 3,519 fresh integrated diff tests passed.
Scoped Ruff and diff checks were clean and no newly added test typing
errors were reported. Strict source typing still reports three unrelated
existing casts and the test file retains inherited diagnostics; Jig doctor
remains degraded and the global Jig check has no passing verdict. Hook
identity is not an atomic defense against concurrent host changes or external
filesystem writers, nor a replacement for sandboxing consumer executables.

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

Behavior context resolution now checks the import-original host
`os.fspath`, `os.lstat`, `os.readlink`, `os.getcwd`, and `stat.S_ISLNK`
helpers that are dynamically consulted by the captured `os.path.realpath`.
It also verifies the original `Path` and concrete-platform path allocation,
initialization, and attribute hooks before and after resolving each binding
(`8a506210b`). Ten red-first cases cover symlink target spoofing, forged
source/oracle equivalence, constructor redirects, and a resolver callback
replacing a helper mid-call. All 192 postcommit behavior tests and 3,414
precommit integrated diff tests passed; scoped Ruff and strict BasedPyright
reported zero errors. The guard cannot atomically pin external filesystem
state or block direct mutation of already trusted objects.

Source/oracle behavior authoring also compares repository and tool bindings
using the import-original stored `ProbeRunContext` slots rather than late
class descriptors or `__getattribute__`. Its initial source and corrected
oracle snapshots use the same native source-root storage (`eccf37e3d`).
Six red-first tests reject forged context equivalence and record a source
or oracle tree before an untrusted getter can redirect it. All 198 postcommit
behavior tests and 3,432 precommit integrated diff tests passed; scoped Ruff,
strict source/test BasedPyright, and diff checks were clean. These checks
address late class-hook substitution, not direct stored-object edits or
concurrent external writers. Repository-wide Jig validation is not yet green.

Exact `ProbeRunContext` records in behavior authoring now run their original
captured constructor validator before source/oracle context comparison or
source-tree snapshots (`729b53902`). An instance created without its
constructor can no longer supply missing native fields, a foreign source or
repository path, malformed tool bindings, or an invalid immutability flag
without raising `BehaviorProgramError`. Late overrides of `__post_init__`
do not bypass the original validator. Eleven red-first cases, 209 postcommit
focused behavior tests, and 3,447 precommit integrated diff tests passed;
scoped Ruff and strict source/test BasedPyright have zero errors. The bounded
130-second repository-wide Jig check did not complete and doctor remained
degraded with its compiled graph absent; there is no global green verdict.
Direct edits to already stored records and concurrent writers remain outside
this admission guarantee.

Behavior context resolution now also pins the original lazy `PurePath` string,
parser, and path-factory hooks along the native path class hierarchy
(`2dde5bc60`). A replaced `_tail` descriptor had redirected a fresh
repository binding to a different path despite using the captured native
`Path.__str__` method. One red-first redirection test and 21 additional
base/concrete-hook and mid-resolution cases now fail closed with
`BehaviorProgramError`; replacing the unused `Path.__str__` class method
remains safe and does not prevent preserving an original resolution error.
All 231 postcommit behavior tests and 3,560 precommit integrated diff tests
passed; scoped Ruff, strict source/test BasedPyright, and diff checks were
clean. Global Jig validation still has no passing verdict, and external
filesystem races and direct edits to trusted native objects remain out of
scope.

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

Identity and bug-program selector admission now reads original slotted
`ProbeProgram.commands` and `ProbeCommand.digest_stdout` /
`digest_exit_code` fields (`b87d42a9c`). Late class getters could
previously admit an unselected probe or falsely reject a selected one.
Twelve red-first getter cases and eleven expanded selector/invalid-slot
regressions now pass. All 182 focused behavior tests, scoped Ruff and
strict source/test BasedPyright pass. This validates selected-probe
metadata at the local authoring boundary; it does not isolate direct
mutable-state changes or concurrent process/filesystem interference.

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

Portable and authored behavior-bundle entry points now rerun pinned original
validators on exact native bug and aggregate receipts (`395616c75`). Native
slot absence raises `BehaviorProgramError` rather than `AttributeError`;
malformed nested correction/digest evidence and empty identity bundles are
rejected before source probe or observation access. Nine new scenarios failed
before the fix and one was already rejected. All ten new regressions and 159
postcommit behavior tests passed; the full diff suite passed 3,172 tests
before commit. Strict source BasedPyright is clean and pinned Ruff retained
its unchanged existing 54 source and 149 test findings. This does not isolate
direct stored-object mutation during concurrent execution.

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

Source-binding policy and envelope admission now authenticate the original
stored `AnchorPolicy` window and selection dimensions, rather than accepting
late class getters or incompletely initialized native records
(`04d9a6a3c`, `555aac9bf`). Malformed nested policies are rejected before
binding or recovery; missing binding, share, or source-identity slots fail
through typed domain errors rather than `AttributeError`. Twelve initial
anchor-policy and six incomplete-record red-first cases cover these changes.
All 180 postcommit source-binding tests passed, along with scoped Ruff and
strict BasedPyright at zero errors. Direct instance mutation and external
source writers remain outside this guard.

Source identity admission now also reruns import-pinned original
`IdentityTree` and `IdentityFile` validators at both key-binding and recovery
entry points (`09dec4c43`). Constructor-bypassing native records with an unsafe
relative path, unsorted file tree, foreign file, or mutable nested evidence
cannot reach anchor selection. Four red-first unsafe-path/tree cases and ten
additional shape/late-validator cases pass. The source-binding suite passed
194 tests postcommit and the integrated diff suite passed 2,938 tests before
commit; scoped Ruff, strict BasedPyright, and diff checks were clean. Jig
doctor remains degraded with a missing graph, and a bounded global check timed
out with no passing verdict. This is a record-admission boundary, not isolation
from deliberate direct instance mutation or concurrent filesystem writers.

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

Public AEAD decryption and direct record validation now translate absent raw
`AuthenticatedPayload` ciphertext/tag slots into the owned
`PayloadCryptoError` boundary (`521941869`). Four red-first
constructor-bypassed native-record cases pass along with 41 payload tests and
3,102 integrated diff tests. Strict payload source typing reports zero errors,
and pinned Ruff retains its 55 pre-existing diagnostics across the source and
test pair with no new findings. This does not isolate direct changes to valid
stored fields or process-global trusted internals.

Native protected-plan admission now reruns the original nested validators
at authenticated metadata and recovery boundaries (`fbbbe62ac`). Eighteen
new tests include ten red-first constructor-bypass cases; all 184 focused
protected tests passed postcommit, and 3,136 integrated diff tests passed
before the final three validator-hook cases. The Rust emitter separately
reruns the import-captured protected-plan validator before reading its runtime
template or staging output (`c02bb9626`). Four red-first malformed-plan
cases and thirteen new regressions cover missing slots, invalid binding,
metadata, context, nonce, and replaced class validators. All 150 emitter
tests passed postcommit; the integrated diff suite passed 3,145 tests before
commit and 3,148 on the live postcommit checkout. Scoped Ruff and strict
source BasedPyright reported zero errors. Both guards protect in-process
admission, not external filesystem races or direct trusted-state mutation.

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

Protected authoring also now reads native exact-plan, instruction, and literal
slots rather than mutable class getters (`1ceb9b305`, which includes a
concurrent protected-code contribution and documentation). Twenty-two red-first
descriptor/getattribute tests cover forged authoring metadata and source or
payload redirection. All 206 focused protected and 3,240 integrated diff tests
passed on the shared checkout. Direct stored-object mutation and filesystem
races remain outside the boundary.
Protected recovery now invokes original native exact-record allocation and
initialization helpers for recovered literals, instructions, and plans
(`be12bdbd5`). Six red-first constructor substitutions, 212 focused protected
and 3,254 integrated diff tests passed; direct stored-record mutation remains
outside this protection.

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

The relocatable materializer now pins the native host `os.path.realpath`,
`os.fspath`, `os.lstat`, `os.readlink`, `os.getcwd`, and `stat.S_ISLNK`
dependencies and original `Path` resolution/constructor hooks (`57870f21c`).
It checks these before path conversion and around each source or output
`Path.resolve`, including after the resolver returns. A forged host realpath
previously admitted an output inside the candidate tree; another late host
hook executed before path admission. Ten new tests cover the bypass, five
host dependencies, three path factories, and mid-resolution mutation.
All 229 focused relocatable tests passed postcommit. The shared diff suite
passed 3,357 tests before the final additional mutation test; scoped Ruff,
strict BasedPyright, and diff checks passed. Jig doctor was degraded because
the generated graph was absent, and a 120-second `jig check` timed out with
no clean verdict. External path races and direct trusted-state mutation
remain outside this guard.

The relocatable resolver also pins the original lazy `PurePath` pathname
parsing and string-formatting descriptors before and after resolution
(`a7906cdbe`). A late replacement of `_tail` previously redirected an
output located inside the candidate source to a different host path and
bypassed containment. Fifteen red-first inherited/concrete descriptor cases
now reject without consulting late hooks. All 244 focused relocatable and
3,483 integrated diff tests passed; scoped Ruff, source strict BasedPyright,
and diff checks were clean. The relocatable test file retains 35 older typing
diagnostics, with none introduced by this fix. Jig doctor remains degraded
with an absent graph, so this evidence does not assert a complete Jig gate.
External filesystem races and trusted object mutation remain out of scope.

Relocatable containment now also verifies original `PurePath.parents` and
`__eq__` path hooks, the native parent-sequence class alias and its inherited
iteration/membership methods, and the equality-related builtin hooks
(`d57dd2b6a`). Replacing `PurePath.parents` with an empty sequence previously
admitted an output nested inside the candidate tree. Nineteen new red-first
ancestry tests reject forged inherited/concrete hooks and aliases. All 263
postcommit focused relocatable tests passed; Ruff, strict source
BasedPyright, and diff checks passed, with the existing 35 test-file typing
diagnostics unchanged. The concurrent integrated diff run passed 3,510 tests
but had four failures in another agent's still-uncommitted probe ancestry
regressions, so that run is not claimed as green. After the probe work
stabilized, a separate later integrated diff run passed all 3,519 tests;
65 downstream DOOM generator tests also passed with one skip. The global
Jig graph and external filesystem race limitations remain open.

Relocatable native path-hook integrity now uses the import-captured
`builtins.any` (`4299dbd38`) for both the `PurePath` ancestry sequence and
the concrete path-hook comparisons. Two late global `any()` calls previously
allowed an untrusted `Path.with_segments` or parents membership hook to run
unchecked, or falsely rejected an external destination when replaced with
an always-true predicate. Three red-first regressions now pass without
consulting substituted hooks; all 266 postcommit relocatable tests, scoped
Ruff, strict source BasedPyright, and diff checks pass. The original 35
relocatable-test typing diagnostics are unchanged. A fresh integrated diff
run against the combined emitter, publisher, and relocatable fixes passed all
3,576 tests in 118.76 seconds. Host/filesystem races and direct trusted-state
mutation remain outside this guard; global Jig lacks a clean verdict due to
the degraded graph state.

Relocatable authoring now creates internal `RangeLocator`,
`RelocatableSourceRange`, `RelocatableInstruction`, and
`RelocatableAuthoringPlan` records using captured native allocation and the
original validation-backed initializers (`39c042c07`). Eight red-first
`__init__`/`__new__` regressions protect locator, segment, instruction, and
plan construction from late class hooks. All 201 focused relocatable tests
and 2,732 integrated diff tests passed; scoped Ruff and source BasedPyright
had zero errors. Direct stored-instance tampering and concurrent source
changes remain outside this boundary.

Native relocation record admission now reruns original validation of nested
`RangeLocator`, `RelocatableSourceRange`, and `OracleLiteral` segments, and
of `RelocatableInstruction` records inside plans (`f081f4fdc`). Public
materialization also rejects fabricated or incomplete exact native plans
before creating staging output. Twelve new regression cases include nine
red-first malformed-slot failures. All 213 focused relocatable and 3,074
integrated diff tests passed; source BasedPyright reported zero errors, with no
increase in existing Ruff diagnostics or Git diff whitespace errors.
This does not make external source-tree mutations atomic, provide compatible
transform admission, or establish a repository-wide Jig pass.

Relocatable authoring now import-pins the original `ExactAuthoringPlan`
validator before the first source snapshot or byte read (`bf576eaa8`). Exact
native plans created without their constructor previously reached source I/O
with modified target-only literal bytes, a missing target slot, reordered
instructions, or a boolean source slice. Four red-first cases now reject
those nested metadata violations before I/O; two additional tests preserve
valid native storage and reject late `__post_init__` replacement. All 219
focused relocatable and 3,192 integrated diff tests passed; strict source
BasedPyright reported zero errors, with no new test typing or Ruff diagnostics
and no Git whitespace errors. This protects structural plan admission, not
arbitrary valid plan authorship or concurrent filesystem writers. A global
Jig green result remains unverified.

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

Mapped-view admission now reruns the captured original `MappedUnit` validator on
nested exact native units, and `MappedView.canonical`/`MappedView.keys` rerun the
original view validator before exposing identity (`c409a1b0a`). Previously
`object.__new__` could bypass byte and coordinate checks or expose an empty
canonical identity; incomplete slots now raise typed `MappedViewError`. Fourteen
regressions reproduced this fail-open behavior, and one already rejected case
was retained. All 51 mapped tests and 3,048 integrated diff tests passed before
commit; 145 mapped/model tests passed after commit. Scoped Ruff, strict
BasedPyright, and diff checks were clean. Direct storage mutation and external
races are not prevented; the global Jig verdict remains unavailable.

The public `read_mapped_unit` and `read_mapped_view` accessors now revalidate
original native unit and view slots before exposing evidence to semantic
consumers (`528c112ba`). Internal constructors and property validators use
separate original-slot readers to avoid recursive validation. Ten red-first
forged-native reader cases and four late-hook/foreign-type cases now fail closed;
65 mapped and 472 mapped/semantic/compatible tests passed after the DCO commit.
The live integrated diff suite subsequently passed 3,172 tests. Scoped Ruff,
strict source/test BasedPyright, and diff checks had zero errors. The global Jig
doctor remains degraded because its graph is absent; no clean global verdict
was established.

Direct `MappedView.canonical` and `.keys` now also require exact native view
types (`ce6bd5f0c`), rather than accepting subclass storage or leaking a raw
`TypeError` for unbound foreign receivers. Four red-first regressions now raise
`MappedViewError`; 69 mapped, 484 postcommit mapped/semantic/compatible, and
3,304 precommit integrated diff tests passed. Scoped Ruff and strict source/test
BasedPyright had zero errors, and diff checks passed. Existing format drift
remains outside this change. Jig doctor was degraded (graph absent) and a
bounded 105-second global check timed out without a green verdict. Direct
storage mutation and external filesystem races remain outside this guard.

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

Public semantic readers now revalidate exact `SemanticLocator`, `SemanticEdit`,
and `SemanticAuthoringPlan` types and their nested stored evidence before
returning source-context digests, replacement bytes, or edit lists
(`9fb6430ec`). Private original-slot readers remain available only for
constructor validation, avoiding recursive validation. Ten red-first tests
reject forged native slots, inherited subclass records, and late validator
replacements. All 435 postcommit semantic/compatible tests and 3,457
precommit integrated diff tests passed, with scoped Ruff, strict BasedPyright,
and whitespace checks clean. This guards reader admission rather than direct
trusted instance mutation or concurrent external writes.

Compatible semantic instructions now unconditionally validate their native
`SemanticAuthoringPlan` and nested edits before accepting an instruction,
including when no named correction IDs are supplied (`d8a036fa6`). Invalid
semantic evidence raises the compatible API's `CompatiblePlanError`, preserving
the original semantic rejection as the cause instead of leaking a different
error family. Seven red-first cases cover mutable/missing plans, malformed
nested edits, and late validator replacement with and without correction IDs.
All 290 postcommit compatible tests and 3,468 precommit integrated diff tests
passed; scoped Ruff, strict source typing, and diff checks passed. The global
Jig check timed out after 145 seconds without a green verdict; Jig doctor
reported a degraded, absent graph. Direct trusted instance mutation and
concurrent filesystem writers remain outside this guard.

Semantic authoring now additionally constructs `SemanticLocator`,
`SemanticEdit`, `SemanticAuthoringPlan`, and `_SemanticBuildContext` with
captured native allocation and original initializer guards (`fa60753bb`).
Eight red-first `__init__`/`__new__` cases cover late class-hook substitutions
without altering mapped-source edits. All 127 focused tests passed after
commit and 2,724 integrated diff tests passed before publication; scoped Ruff
had no findings, and no new strict type diagnostics appeared. These are
class-hook guards, not isolation from trusted direct object mutation.

Semantic edit and plan admission now rerun the captured original nested
locator/edit validators and translate missing native slots to
`SemanticPlacementError` before public application (`07adc8f42`). Fifteen
red-first cases show that exact-class but constructor-bypassed records can
otherwise skip malformed digest checks, accept incomplete edit fields, or let
an empty forged plan return source unchanged. All 142 semantic tests passed
after commit, and 3,145 integrated diff tests passed before commit. Strict
semantic source BasedPyright is clean; pinned Ruff reports 84 existing
source/test findings versus 87 at baseline, with no new diagnostics. These
checks validate stored evidence on entry, not protection against direct
storage mutation during concurrent execution.

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

Compatible public authoring, correction binding, and materialization now
rerun import-captured validators on exact native request and plan slots,
including nested instructions and correction bindings (`9418fc2eb`). A
constructor-bypassed plan previously could drop a target path or replace
created-file bytes while publication still succeeded. Eight red-first tests
also cover malformed request fields, missing native slots, invalid literal
metadata, and negative correction indexes. All 273 compatible focused and
3,180 integrated diff tests passed; scoped Ruff, strict source BasedPyright,
and diff checks were clean. The source/target snapshot and output filesystem
still require protection against direct instance mutation and external writers;
no repository-wide Jig verdict is asserted by these tests.

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

Compatible authoring also reads original exact-plan source, target, and
instruction slots before invoking consumer mappers (`c720565eb`). It retains
those stored snapshots through final tree drift checks and plan construction,
so late exact-plan class getters cannot exchange or conceal source/target
identity. Eight red-first forged and valid-plan cases passed, with 241 selected
compatible tests and 2,916 integrated diff tests. Scoped Ruff, compatible
source BasedPyright, and diff checks were clean. Direct trusted storage edits
and external filesystem races are outside this process-hook boundary.

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

Relocatable, compatible, and source-pin exact-reader failure bridges now
retrieve native exception arguments and optional notes through original
`BaseException` access rather than late `ExactTreeError` class getters
(`6107beb77`, `1ced2caf2`). Before these guards, a consumer could replace
`ExactTreeError.__getattribute__` after import and execute it while a genuine
exact read failure was converted to the caller's typed failure. Native notes
are copied only from exact lists containing exact strings, through the base
exception note method. Four red-first relocation cases and eight compatible/
source-pin cases now pass; 270 relocation and 492 combined compatible/source-pin
focused tests passed postcommit, with scoped Ruff and diff checks clean.
Strict typing has 17 inherited compatible test diagnostics outside changed
lines; the relocation source/tests are clean. A complete diff run after
relocation passed 3,606 tests, and fresh validation with both bridge fixes and
peer domain safeguards passed 3,616 tests in 103.93 seconds. Downstream DOOM
generator tests passed 65 with one skip. Global Jig checks remain degraded or
failing on broader text/version rules; no clean repository-wide Jig verdict is
claimed. External filesystem races and trusted direct mutations remain open.

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
