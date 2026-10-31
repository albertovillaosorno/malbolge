# Resumable compilation progress sidecars

## Status

Active contract and durable generation reference

## Purpose

Preserve objective timing and resumable state for long-running compilation,
layout, block synthesis, optimization, verification, and accelerator jobs. A
power loss, process crash, cancellation, or planned pause must lose at most the
work performed since the last durable checkpoint rather than the whole job.

## Scope

The contract applies to public commands and internal services that can spend
material time converting source files, compiler IR, link plans, or reusable
blocks into verified Malbolge artifacts. It covers CPU and accelerator paths on
Windows and Linux. Short operations may omit checkpoint creation, but any job
that advertises resumability or crosses the configured checkpoint interval must
maintain the sidecar.

For an intended output named `program.malbolge`, the canonical progress path is
`program.malbolge.progress.json`. Durable generations use immutable paths such
as `program.malbolge.checkpoint.00000000000000000001` and
`program.malbolge.partial.00000000000000000001`. The sidecar is the only mutable
pointer to the latest committed generation. A persistent
`program.malbolge.progress.json.lock` file coordinates sidecar writers; its
contents carry no recovery semantics and the operating-system lock is released
when the owning process exits. The final requested path is never replaced until

the artifact is complete and independently verified.

## Current Behavior

Checkpoint operator metadata is a single newline-terminated key/value record.
Direct `render_checkpoint_metadata()` callers are admitted through the same
positive sequence, nonnegative units, stable stage/codec identifiers, and
SHA-256 digest *format* validation as parsed checkpoint envelopes. Forged
metadata fields cannot inject newlines or noncanonical operator output.
Durable payload-digest verification remains the responsibility of
`read_portable_checkpoint_metadata()`, not the direct text renderer.

The repository now exposes a reference `malbolge-progress-v1` validator and
durable generation writer in `scripts/progress_sidecar.py`. It defines canonical
sequence-addressed paths, backend-neutral resume identity, exact timing and
lifecycle invariants, monotonic transition validation, duplicate-key rejection,
canonical JSON, immutable checkpoint/partial persistence, and atomic sidecar
replacement after generation payloads are durable.

Both immutable payload and
mutable pointer writes require an exact integer byte count before sync or
publication. Boolean reports, including `True` for a single byte and `False`
for an empty checkpoint, cannot be mistaken for completed payload writes.

Regular-file and POSIX parent-directory `fsync` calls likewise require the
native `None` success receipt. Foreign boolean or integer responses cannot
certify durable synchronization: a payload-file response rejects before
publication, while an invalid post-publication directory response reports
uncertain durability and preserves the exact committed path. As with OS lock
receipts, this check does not authenticate a deliberately forged `None`.
Staged payload streams must likewise return the native `None` flush completion
before any file synchronization. A boolean or integer flush receipt rejects
prepublication for either mutable progress JSON or immutable checkpoint bytes.
The staged stream must also expose the exact native integer descriptor created
for that stage at file sync; synchronizing an unrelated, valid regular-file
descriptor cannot certify the staged pointer or checkpoint payload as durable.
Malformed non-integer write results are rejected before diagnostic formatting,
so an unexpected result object cannot invoke foreign string methods or mask the
typed prepublication failure. Mutable pointer updates are serialized across
processes from prior-sidecar validation through replacement, so a stale writer
cannot overwrite a generation committed concurrently.

Public progress path helpers and readers accept only exact native platform
`pathlib.Path` values (or exact strings for output path helpers), rejecting
foreign subclasses before their overridden filesystem or rendering methods can
run. Direct progress and portable-checkpoint JSON parsing similarly requires an
exact native mapping before traversing its items, rather than dispatching a
foreign mapping subclass's methods. Only a native `FileNotFoundError` may prove
an absent progress pointer during preflight; only a native `FileExistsError`
may authorize an immutable-generation no-replace collision and its subsequent
byte-verified reuse. Foreign subclasses of either exception fail closed, even
when a matching generation inode already exists.

Process-shared progress writer locks now reject nonnative stat metadata on
pre-existing lock pathname preflight, the opened lock descriptor, and both
pathname/descriptor identity checks after lock acquisition. A foreign receipt
fails before its attributes can run or the lock can authorize publication;
positive native lock ownership and post-staging rechecks remain mandatory.

POSIX `flock` and Windows `locking` acquisition and release must also return
the native `None` success receipt. A foreign boolean or integer response cannot
certify that the writer lock was acquired: it rejects before the body and
pointer publication. A foreign release response is a teardown error and retains
exact committed-pointer evidence if publication already completed. These
receipt checks cannot prove a deliberately forged `None` is backed by an OS
lock; they supplement the independent inode and path checks. In addition,
lock-stream seeks must report the exact integer position zero, before the
initial lock and before Windows byte-range release. Boolean or nonzero receipts
cannot certify that the intended region is protected or unlocked. Lock-stream
file-descriptor receipts also require a native nonnegative C-`int`-bounded
integer at acquisition and post-acquisition identity admission; boolean,
overflowed or foreign descriptor objects
must not reach an OS lock or stat primitive. A forged release callback return
cannot certify successful teardown without the native `None` receipt, and a
late failure retains committed-path evidence. These checks cannot prove that a
forged valid integer describes the same file across separate observations.
The post-lock inode receipt must also still describe a regular descriptor,
independently of the regular path, even if a forged native `stat_result`
claims identical device and inode values for a directory or special file.
Both the opened and nonfollowing pathname lock inode must also have exactly
one hard link. An externally named alias rejects publication at acquisition
or the post-staging recheck, while preserving the persistent lock inode and
unrelated alias. A late alias can still race after the final observation;
these checks do not establish atomic isolation from hostile directory writers.

Progress writers also require native `os.stat_result` for the initially
created staging descriptor and each staged pathname/descriptor size and inode
check. Foreign receipts reject before property access and before mutable or
immutable publication. A failed first-descriptor admission keeps the stage
pathname untouched because its inode ownership was never established; later
stage validation still closes and cleans up its own verified staging member.

Temporary payload writers retain raw-descriptor ownership until Python stream
construction succeeds. Unexpected non-`OSError` construction failures still
close the descriptor before propagating their primary error, while any raw
close failure is attached as a secondary diagnostic rather than masking it.
The same precedence applies to non-`OSError` stream-close failures after a
write or sync error; an isolated close failure still propagates unchanged.

Canonical progress-pointer JSON has a 1,048,576-byte inclusive limit.
Publication checks that limit before acquiring a writer lock or creating
immutable checkpoint members; reads reject oversized regular files before
stream allocation and use a bounded read to catch concurrent growth. The
limit applies only to mutable metadata, not to immutable checkpoint and
partial payload bytes.

Direct `loads()` parsing enforces the same UTF-8 input budget before invoking
the JSON decoder, including multibyte input. Decoded sidecars also have their
canonical serialized size admitted, since a shorter noncanonical UTF-8 spelling
can expand beyond the canonical limit. The inclusive ceiling remains accepted;
immutable checkpoint state is outside this pointer-only budget.

Caller-constructed metadata integers must also be representable in the host's
decimal conversion before canonical JSON, checkpoint-generation filenames, or
operator-facing records are rendered. A host digit-limit rejection returns a
typed `ProgressSidecarError`, not an escaping Python `ValueError`. This adds no
fixed digit cap to opaque checkpoint bytes or standalone timer arithmetic.

Reads and immutable-generation collision checks reject pre-existing nonregular
filesystem entries, including named pipes, before attempting blocking payload
reads. The opened file descriptor is independently checked against the regular-
file requirement. Where available, POSIX nonblocking and no-follow flags
prevent a FIFO or leaf symlink substituted during path admission from becoming
trusted progress input.

Progress-pointer and immutable checkpoint reads now require exact native
`os.stat_result` metadata from every descriptor and pathname probe before
accessing its fields. This applies to pre-open path admission, both descriptor
identity checks, the initial/final read-size and timestamp checks, and the
immutable member's single-link admission. A substituted foreign receipt fails
with a typed sidecar error before its attributes can execute. These checks
cannot authenticate a deliberately forged native result or prevent later
filesystem changes.

The open descriptor's device and inode must still match
the no-follow pathname immediately after opening; detached or replaced regular
files fail closed at that point. All path components are also rechecked for
links after opening: replacing a parent with a symlink could otherwise direct
the open to a different regular inode that still matches its new pathname.

Publication durability admission now requires exact native directory-stat
receipts both before and after the parent-directory fsync. A foreign descriptor
or no-follow pathname receipt fails before any metadata field access. Pointer
and checkpoint publishers retain their precise committed-path evidence and
report uncertain durability instead of claiming a successful publication;
these checks do not prevent races after the final admission.

On Linux, admission also compares the opened descriptor's `/proc/self/fd`
pathname to the lexically normalized requested path. A transient parent link
that directs the open to a separate hard link of the *same inode* therefore
rejects, even when the parent has been restored before metadata admission.
Missing descriptor-path evidence fails closed on Linux; non-Linux platforms
retain the device/inode and post-open redirect checks but not this stronger
hard-link-path guarantee. A check cannot prevent a later filesystem rewrite.

Identity and path-link admission are repeated after the full payload has
been read and before the admitted descriptor is closed. Concurrent pathname
replacement during the read cannot turn a stale regular-file snapshot into
trusted progress evidence, even when the replacement has identical bytes.
File size and nanosecond modification/change times are also checked before
and after reading to reject observed in-place same-inode rewrites.

Bounded raw reads continue after a short chunk, staying within the admitted
byte budget,
and reject premature EOF before the opened inode's recorded size. Raw stream
results must be exact bytes, cannot exceed the requested size, and must match
the initially admitted inode length. Even a valid JSON prefix cannot stand in
for unread file bytes. These are metadata-based checks and do not establish an
atomic filesystem snapshot.

Both pointer and opaque checkpoint reads are bounded by the opened inode's
observed byte length plus one sentinel byte, never a fabricated global limit
on state size. Each raw `FileIO.read()` request is additionally bounded to
65,536 bytes, so a giant sparse inode cannot force a giant single allocation
before EOF, size or digest admission. Repeated small chunks accumulate in a
compact byte buffer instead of retaining a separate Python list entry per read.
The total validated opaque state is still returned in RAM; this is a per-read
allocation bound, not a total-memory cap or streaming checkpoint codec.

These are bounded admission checks, not a promise of immunity to subsequent
filesystem mutation after the stream closes. The immutable checkpoint and
partial-generation readers additionally require a regular single-hard-link
inode at the canonical generation pathname before and after the bounded raw
read, with the same device/inode identity. Foreign aliases present at entry or
introduced after byte collection reject even when the SHA-256 would match;
replacing the generation inode with a byte-identical file after the raw read
also rejects.

Immutable checkpoint publication now rejects nonnative stat receipts at
initial collision admission, single-link collision rechecks, and the first
post-link inode check before durability can be certified. A newly linked
member with untrusted post-link evidence reports committed-path uncertainty;
collisions cannot be reused on forged metadata even when their bytes match.
Retained-alias recovery also admits exact native directory-entry metadata,
collision inode rechecks and alias-path receipts before considering a stale
staging alias for cleanup. Foreign entry receipts do not establish candidates,
and foreign later receipts abort recovery without unlinking the alias. The
mutable and immutable staging cleanup paths likewise reject foreign pathname
metadata, preserving the original write failure and leaving the unproved stage
untouched.

The mutable progress-pointer reader is not subject to this
immutable-generation link-count policy. These checks cannot prevent writes
through an already-open descriptor or filesystem changes after final admission.
Descriptor read errors remain primary if stream close also fails; close-only
failures reject the read.

Read-stream cleanup likewise preserves an earlier read error when `close()`
raises a non-`OSError` exception. The cleanup failure is attached as a
secondary diagnostic, and descriptor close does not replace the primary read
failure.

An unexpected `ValueError` or `RuntimeError` raised by a close-only read
failure is translated to `ProgressSidecarError` for both mutable pointer and
immutable checkpoint-payload reads. The published read API does not leak the
stream implementation's raw exception or accept incomplete admission.

When wrapping unexpected I/O errors, the typed reader retains the original
exception as its cause and propagates attached secondary cleanup notes.
Descriptor cleanup diagnostics remain inspectable without replacing the
stable public failure category.

Raw-descriptor cleanup during failed read-stream or writer-lock stream
construction follows the same precedence, including `ValueError` or
`RuntimeError` from `os.close`. Exact stream-construction errors remain
primary even after the failed raw close; writer locks cannot enter the
serialization region on that path.
Deterministic parent and regular-inode substitutions cover both progress-pointer
and immutable checkpoint reads, including descriptor cleanup. A further
read-completion regression replaces the progress parent with a linked directory
before the second admission check and proves the original descriptor closes.

Mutable pointer publication rechecks the destination and its parent after
creating the parent directory and before opening a temporary file. This closes
the directory-creation substitution window in which a newly linked parent
could redirect the mutable write before the already-enforced replace guard.
It complements the equivalent post-`mkdir` check for immutable generations;
concurrent mutation after either check still requires filesystem protection.

Deterministic directory-swap regressions cover both mutable pointer and
immutable checkpoint publication at the post-creation boundary. The destination
is also readmitted after temporary bytes are fully written and before atomic
publication. Parent-directory substitution during either mutable or immutable
staging therefore fails closed before committing a redirected generation.

Mutable and immutable writers now capture the device and inode of the fresh
`mkstemp` descriptor before transferring it to the payload stream. After file
sync and stream close, and before pointer replacement or immutable linking,
they require the temporary pathname to remain a regular, non-symlink entry
with the same device, inode, exact expected byte length, and **one hard link**.
This prevents a staged inode already accessible through another pathname from
becoming a published pointer or checkpoint that can later be mutated through
its alias.

Both writers reopen that temporary through a nonfollowing,
nonblocking descriptor, check stable pathname/inode and modification timestamps,
and independently SHA-256
compare the complete staged bytes against the original payload using raw reads
capped at 64 KiB each. This catches a same-inode, same-length rewrite that
previously passed inode/size admission, while keeping opaque checkpoint size
unbounded and peak *additional* verification buffering independent of payload
length.

A short read or a changed inode/time also rejects. Substituting a
regular file, a symlink, or truncating the original inode still fails before
publication in both paths.

On rejection, cleanup removes only the original
staging inode once its identity has been admitted. If another regular file or
symlink replaces the staging pathname, the foreign entry survives rather than
being unlinked by a failed publication.

A failed initial descriptor admission closes the raw descriptor but does not
unlink the unadmitted pathname: no verified inode has been captured, so the
path might now refer to an unrelated regular file or symlink. The unverified
staging entry may therefore remain for explicit operator review. Once inode
identity is admitted, cleanup still uses a pathname identity recheck and unlink,
which are not one atomic filesystem operation. Neither publication path claims
protection from a substitution precisely between its final cleanup identity
check and unlink.

Regular-inode and single-hard-link admission is repeated before reopening,
after hashing on the open descriptor, and after reader closure. Deterministic
POSIX tests insert a hard-link alias at each boundary, including between hash
completion and the final pathname check; none may publish the aliased inode.

After mutable pointer replacement and durability sync, the writer also checks
that its committed path still resolves to the previously staged regular inode,
with the expected size and exactly one hard link. The pointer additionally
receives a bounded post-publication raw read against its exact canonical bytes,
with device/inode and link-count re-admission after that read. This closes the
observed same-inode, same-size byte-rewrite window between staging verification
and atomic replacement/durability confirmation, including a rewrite to a
*different but still valid* progress JSON object.

A late alias, identical-byte inode replacement, or changed pointer content no
longer reports success: the writer returns the exact path with
`ProgressSidecarCommittedError`. This costs
an extra read of at most the already enforced 1 MiB pointer wire budget. It is
a diagnostic admission rather than rollback, and cannot prevent filesystem
mutation after its final check.

The immutable POSIX publisher's intentional no-replace hard link happens only
after these staging checks and is cleaned up when staging completes. After
successfully confirming directory durability and removing the temporary entry,
the immutable writer now re-admits the published path as a regular single-link
inode and compares its device/inode with the one recorded directly after the
no-replace publication or collision reuse. It additionally repeats the staged
content SHA-256 comparison using the existing 64 KiB raw-read chunk budget,
without a second checkpoint-sized allocation.

A foreign alias, byte-identical inode replacement, or same-inode/same-length
*content* rewrite after staging
now fails before a successful return. Because this occurs after the committed
generation, any rejection reports `ProgressSidecarCommittedError` with its exact
published member path, never claiming that a filesystem change was undone.
Generation publication stops before the mutable pointer on that failure.

The additional verification costs another complete opaque checkpoint read;
this is still a bounded observation, not protection against writes after the
final check or via another open descriptor.

If descriptor identity admission fails before ownership transfer, the raw
descriptor is closed with cleanup exceptions kept secondary to the primary
error. The temporary checks constrain the observed prepublication window;
they do not claim an atomic filesystem snapshot or protection against
concurrent rewriting after the final comparison (a pathname race remains).
This check incurs an additional full staged-file read and hashing pass per
publication, and does not by itself authenticate the original caller payload.
Failures already classified as `ProgressSidecarError` by the staged reader
retain their original exception cause and secondary descriptor-close notes
through the mutable pointer publisher; unclassified raw writer and filesystem
errors still receive the pointer-publication error boundary.

The persistent writer-lock file also receives regular-descriptor admission and
nonblocking/no-follow opens where available. Its lock-path recheck after
creating the parent directory rejects a parent-link substitution before the
writer-lock file is opened.

Unexpected `ValueError` and `RuntimeError` from writer-lock stream opening,
including filesystem admission and raw descriptor construction, now receive
the same typed prepublication classification as `OSError`. The primary
stream error remains the cause, and any secondary descriptor-cleanup notes
remain inspectable on the typed error. No pointer update can be admitted
after a failed lock-open operation.

New persistent lock inodes are explicitly created with requested owner-only
`0o600` permissions before applying the process umask. Existing lock inodes
retain their permissions; acquisition still validates regular-file identity.
POSIX regression evidence checks the requested mode and absence of group,
world, and executable access bits on newly created lock files.

After acquiring the process lock,
the publisher rechecks every path component for links and confirms that the
lock pathname still identifies the acquired descriptor's device and inode.
A same-inode parent symlink or substituted/detached lock fails closed before
the publication body can execute.

The pointer writer also retains its acquired lock descriptor across transition
and referenced-generation validation. Immediately before mutable staging, it
rechecks the current lock-path device and inode against that held descriptor.
A real-directory replacement after pointer preflight cannot redirect a stale
writer into a new directory where it holds no serialization lock.

After the mutable temporary payload is flushed, a third held-lock identity
check runs immediately before atomic pointer replacement. Replacing the
persisted lock with an unrelated regular inode during staging therefore fails
before pointer commit, and the uncommitted temporary is reclaimed. These checks
narrow the race windows; they do not make external filesystem renames atomic.

Canonical output-path helpers reject empty or directory-only output names
instead of deriving hidden progress members in a working directory. Helpers
and direct sidecar reads reject embedded NUL and ill-formed or host-unencodable
Unicode filenames before storage access.

On POSIX, valid byte-oriented filenames represented through Python's
`surrogateescape` mechanism remain usable and round-trip through durable
sidecar publication and inspection. Immutable checkpoint/partial members and
the product checkpoint extractor also recover using those original byte paths.
Malformed output paths cannot create sidecar pointers or sibling writer locks.

Source provenance paths also reject NULs, unencodable surrogate text,
and directory-only names before publication. Valid POSIX byte-backed and
relative filenames remain allowed without filesystem existence checks.

Direct API admission is fail-closed as well as JSON admission. Runtime callers
must supply exact sidecar/resume-identity enums, strings, integers, and
immutable records. Direct resume identity schema admission also requires an
exact string before any comparison, rejecting arbitrary equality hooks and
string subclasses without leaking serializer/type exceptions.

Booleans cannot alias counters or sequence numbers, foreign objects do not leak
decoder/type exceptions, and direct JSON parsing requires an exact string
instead of accepting byte/bytearray aliases or leaking decoder `TypeError`.
Excessively nested JSON values that exhaust the parser stack are also reported
as typed progress or portable checkpoint failures, including CLI inspection.

Oversized JSON integer literals that hit the interpreter conversion
limit remain inside the stable sidecar error boundary, and impossible UTC
calendar timestamps are reported the same way. UTC timestamp ordering retains
all admitted fractional-second digits rather than relying on the six-digit
microsecond precision of Python `datetime`. Publication transitions, observed
follow transitions, and completion ordering therefore reject submicrosecond
regressions while treating trailing-zero representations as equal.

`ProgressTimer` validates every phase and monotonic-clock sample before mutating

timing evidence. Non-callable clocks and callback failures remain inside the
stable sidecar error boundary. Snapshotting also revalidates its internal
anchors and accumulated phase partition, so directly constructed or corrupted
timer state cannot be misclassified as verification time.

Both the phase timer and routine publication limiter retain their last
successful clock sample,
rejecting regressions between snapshots or suppressed writes even when the
new reading remains above the original phase or last-commit anchor. A failed
clock sample does not replace a prior accepted observation, and directly
constructed observation state must not predate its segment or last commit.
Neither mutable timer nor limiter state permits its accepted observation to be
reset to `None`: that would otherwise allow a later backward clock sample to
be accepted against only the weaker phase-start or previous-commit anchor.

Public path helpers
reject foreign objects instead of stringifying them, and direct reads require a
real `pathlib.Path` before filesystem inspection.

`write_atomic()` also validates every referenced checkpoint and partial payload
before moving the mutable pointer: the files must exist, hashes must match, and
partial byte counts must agree. Direct generation publication requires exact
immutable `bytes`; mutable or foreign aliases fail before hashing or creating a
generation file. Its read-transition-validation-replacement
transaction is serialized by a process-shared sibling `.lock` file so two
writers cannot both validate against one stale predecessor and then race the
mutable pointer backward. A caller therefore cannot publish a syntactically
valid sidecar that points at absent or corrupted generation bytes.

Partial-output reads admit at most the sidecar-declared byte count before
checking the complete payload hash and length. Direct generation publication
also rejects a mismatched declared partial length before hashing caller-owned
bytes; a malformed large partial cannot consume its full digest cost.
Immutable-generation collisions similarly read at most the proposed
immutable payload length, preventing oversized pre-existing files from forcing
unbounded reads. Opaque checkpoint bytes retain their existing unrestricted
payload contract.

Bounded reads also use the opened inode's observed size to keep untrusted
arbitrarily large declared counters from overflowing the host read-size API.
Ordinary hash and exact byte-count checks still decide final admission.

Atomic publication and directory durability confirmation are distinct commit
phases. `ProgressSidecarCommittedError` carries the exact `published_path` when
a failure is reported only after publication crossed its commit point. Its
`ProgressSidecarDurabilityError` subtype means parent-directory synchronization
failed after publication, so durability is unconfirmed rather than rolled back.

A directory-descriptor close failure after successful directory sync reports the
broader committed error because durability is already confirmed. If sync and
close both fail, the sync failure remains primary and close failure is secondary
evidence.

This ordering also applies when directory close raises `ValueError` or
`RuntimeError` rather than `OSError`. Confirmed sync retains the exact
committed path; failed sync retains typed uncertain-durability evidence and
records the close error as a secondary note.

Directory `fsync` failures of types `OSError`, `ValueError`, and
`RuntimeError` all retain uncertain-durability path evidence. A non-OS sync
failure remains primary even if the subsequent directory close also fails.

POSIX durability confirmation requires a directory descriptor rather than
accepting a regular file's successful `fsync`. The parent is opened with
`O_DIRECTORY` and `O_NOFOLLOW` where supported, and its path is checked for
symlink or junction components before opening and before and after sync.
Platforms without `O_DIRECTORY` check the opened descriptor's directory type.

A linked parent or a parent replaced with a link during directory sync thus
fails closed with the original committed path recorded as uncertain durability.
Tests cover regular-file substitution, a linked parent, and a live parent swap
after sync.

The opened directory descriptor must also match the current nonfollowing
pathname's device and inode before and after `fsync`. This rejects a different
regular directory substituted after opening or during synchronization, for both
mutable sidecars and immutable checkpoint members. Such failures retain the
exact published path but do not claim durability; external swaps outside the
two checks remain a filesystem race rather than an atomicity guarantee.

Writer-lock release/close and immutable temporary-file cleanup failure after
durable publication follow the same committed-evidence principle. If a durable
checkpoint member commits before a later partial member fails prepublication,
the failure reports the checkpoint as the exact last committed path. After all
generation members commit, a mutable sidecar prepublication failure likewise
reports the last committed member until the pointer itself crosses commit.

During lock unwinding, a later release or close failure is secondary evidence
when an acquisition, body, or release failure is already active. This
precedence also applies when an injected cleanup operation raises
`ValueError` or `RuntimeError` rather than a typed sidecar error. If cleanup
fails after durable pointer publication, those same unexpected error classes
retain the exact committed path via `ProgressSidecarCommittedError`.

Writer-lock release and close helpers also type unexpected `ValueError` and
`RuntimeError` with their original cause, without rewrapping an existing
`ProgressSidecarError`. When the failure follows a durable pointer commit,
the committed-error cause still identifies the original raw cleanup fault
rather than losing it inside the helper's typed wrapper.

An existing `ProgressSidecarError` raised by a lock-open or lock-acquire
operation passes through unchanged, including its original identity and
attached diagnostic notes. Raw host exceptions still receive the typed
prepublication error boundary and preserve their underlying cause.

Unexpected `ValueError` and `RuntimeError` from lock acquisition or the
post-acquisition inode identity probe become typed prepublication failures.
Neither failure authorizes entry to the lock body, and stream teardown keeps
the acquisition or identity error primary.

Mutable replacement does not unlink the moved temporary pathname after
commit. Before replacement, mutable temporary-cleanup failure is retained
as secondary evidence
and cannot mask the primary publication failure.

Unexpected `ValueError` or `RuntimeError` from mutable temporary cleanup also
remains secondary to an active prepublication failure. For immutable generation
members, those errors preserve typed committed-path evidence after durability
confirmation, rather than hiding a previously published member.

Failures before publication retain ordinary `ProgressSidecarError` behavior
and do not gain committed-path evidence.

Failed payload-stream ownership transfer closes the raw temporary descriptor,
while cleanup failure remains secondary to the stream-open failure.
The same precedence applies when raw descriptor cleanup raises `ValueError` or
`RuntimeError`, not only `OSError`.

Read stream setup failures retain their primary error even when raw descriptor
cleanup fails; the cleanup exception is attached as secondary evidence.

Temporary payload-stream teardown likewise keeps an
earlier write, flush, or file-sync failure primary when close also fails.

A crash after writing a later generation but before replacing the sidecar leaves
the previously referenced generation intact and resumable. Unreferenced newer
generations are ignored until a valid sidecar publishes them. `ProgressTimer`
uses an injectable monotonic nanosecond clock and exclusive active, paused,
verification, serialization, and checkpoint phases to construct the exact timing
fields without UTC arithmetic.

`ProgressWriteLimiter` accepts one explicit positive monotonic interval.
Repeated valid queued/running updates may be suppressed until it passes. The
first queued-to-running transition is always published, because eliding it
would prevent a strict queued-to-completed or queued-to-checkpointed writer
transition. Any checkpoint-generation advance bypasses suppression even if
its status is still `running`, as do checkpointed and terminal snapshots.

The limiter retains the last committed immutable sidecar, including after a
post-commit durability failure, so a routine candidate that violates its
monotonic transition rules cannot be silently discarded. Instead, the
serialized durable writer checks the current pointer and decides admissibility:
other processes may have advanced the job since the local last commit. Valid
routine updates remain rate-limited; status, sequence, partial-reference, or
counter regressions never receive false success from the suppression path.

The interval begins at the post-publication monotonic sample, not at the start
of a potentially slow write. Only successful or post-commit-failing writes
consume the limiter window, so a prepublication failure can retry immediately.
A limiter is caller-local to one job: after its first committed sidecar, its
output progress path, operation ID, and job start timestamp stay fixed. Reusing
it for a second job fails before rate suppression can hide a missing first
publication; a separate job must create a separate limiter.

Directly constructed limiter state also requires every prior-commit timestamp
to have a matching, fully validated committed sidecar; an orphan timestamp or
malformed cached record cannot suppress a new job or authorize a write. Cached
schema and timing corruption fail before sampling the clock or publishing.

A failed post-commit clock sample retains committed-path evidence, falls back to
the pre-write sample for throttling, and cannot mask an earlier durability
failure.

`malbolge-checkpoint-v1` now supplies a canonical backend-neutral envelope for
opaque resumable state. The envelope binds the sidecar compatibility
fingerprint, checkpoint sequence, stage, completed-unit count, caller-owned
versioned state codec, payload SHA-256, and canonical base64 payload while
intentionally omitting CPU/CUDA backend identity. Decoding first requires the
envelope bytes to match the sidecar checkpoint digest, then revalidates all of
those fields and rejects malformed, noncanonical, or differently identified
state. Metadata discovery validates the stored codec identifier before decoding
the opaque state bytes, even when no expected codec was supplied by the caller.

The complete envelope's exact canonical JSON spelling is now admitted before
base64 decoding, rejecting alternate whitespace, escaped-key aliases, and
missing line termination without interpreting opaque state.

The envelope does not define compiler-stage semantics; concrete compiler/search
state codecs remain owned by their producing subsystems.

The accelerator application now supplies one concrete search codec,
`evaluated-search-prefix-evidence-v1`. It canonically binds the exact
`SearchRequest`, a fingerprint over evaluator identity plus every candidate
identity/payload byte, total candidate count, and an immutable request-order
prefix of completed `CandidateEvidence`. Backend and device identity are
omitted, so byte-identical CPU/CUDA evidence has one durable representation.
Restore requires the current request and batch to match exactly.

Restore preflights exact-typed search identity, declared total and completed
counts, and the requested evidence-list length before decoding opaque payloads.
All candidate identities and payload header types are checked in request
order before decoding the first base64 payload. The normalized JSON
spelling is checked against the exact checkpoint bytes before base64 decoding;
missing line termination and whitespace aliases are rejected early. Malformed
counts, boolean aliases, and later nonprefix evidence also fail without
consuming untrusted evidence payload bytes.

The search codec also wraps JSON parser-stack exhaustion as a stable typed
checkpoint error instead of leaking `RecursionError` to resume callers.

`evaluated-search-prefix-resume-v1` now consumes that codec for ordinary
evaluated search. It rebuilds and validates the exact candidate batch, evaluates
only the unfinished request-order suffix through the selected backend, combines
restored and fresh evidence, reruns the ordinary selector, and checks proposal
membership. Fixed-width indexed candidate storage remains packed across suffix
projection. Restored evidence remains untrusted and does not bypass independent
verification.

`prepared-evaluated-search-prefix-resume-v1` applies the same evidence codec to
prepared search without downgrading to ordinary evaluation. Resume reconstructs
the strategy-owned prepared projection, requires the checkpoint to match that
exact evaluation batch, re-prepares only the unfinished projected suffix, and
then reruns prepared proposal selection against the original full candidate
batch. Ordinary batch preparers are reusable for suffix state automatically;
selection-aware strategies must declare an explicit `resume_preparer`. Rotate
and crazy target strategies bind their primitive suffix preparers explicitly.

Rotate-target and crazy-target expose target-owned resume factories that reuse
the exact ordinary strategy definitions rather than reconstructing selection
behavior at the call site.

Focused differential evidence now covers both accelerator-backed search
strategies. Rotate-target and crazy-target each produce byte-identical CPU/CUDA
checkpoint payloads, resume CPU-produced state on CUDA, resume CUDA-produced
state on CPU, and match uninterrupted CPU proposals. Prepared resume now proves
the same bidirectional backend neutrality: crazy-target carries a non-empty
partial prefix across CPU-to-CUDA and CUDA-to-CPU execution, while rotate-target
proves its one-item completed projection is byte-identical and accepted by both
backend consumers. Later compiler-execution CPU/CUDA resume equivalence remains
open.

Canonical typed-IR durable state is already backend-identity neutral.

The external optimizer runner now accepts `--resume-checkpoint PATH` for
rotate-target and crazy-target evaluated-search checkpoint payloads. It
preserves
configured-versus-actual backend identity, retries accelerator execution failure
through the CPU reference route, rejects unsupported algorithms and incompatible
checkpoint state, and records checkpoint SHA-256 plus
`evaluated-search-prefix-resume-v1` in resumed JSON output. Fresh-search JSON is
unchanged.

Direct Python `read()` permits copies of sidecar records used as crash
fixture inputs, preserving the original declared progress path without
publishing state. Operator CLI inspection instead requires the supplied file
to occupy its declared canonical `progress_path`. Relative filenames are
admitted when they refer to the same lexically normalized absolute path,
including `..` segments, without following symlinks. Relocated pointers
cannot impersonate another live job during
summary, follow, checkpoint discovery, or binary state extraction.

Operator text output for summary, checkpoint discovery, and follow status now
uses a shared typed stdout boundary. Unexpected `OSError`, `ValueError`, or
`RuntimeError` during writing returns the command's stable failure status;
follow additionally rejects a failed flush instead of accepting an incomplete
terminal record. An output stream must report the exact integer character count;
boolean, missing, short, negative, and exaggerated counts are rejected even
without a raised write exception.

Each operator record must flush successfully
before the command reports success; neither a rejected count nor a failed flush
can authorize follow completion or a one-shot inspection result. No partially
emitted text becomes recovery authority. The `--help` usage record obeys the
same exact-write and flush admission; incomplete or unflushed help returns a
nonzero status with a stable diagnostic rather than falsely claiming success.

Error reporting is best-effort: a broken, closed, or invalid stderr stream may
prevent diagnostic delivery but cannot convert a rejected inspection,
extraction, follow, help, or usage operation into an uncaught stream exception
or successful exit. The original error status remains authoritative.

Diagnostics are flushed on the best-effort path; errors during the flush
also preserve the original failure status. Absent standard streams and
noncallable output methods follow the same rule,
including failures to acquire a usable binary stdout stream before extraction.

Binary checkpoint extraction requires an exact integer stdout write count
and a successful flush after full state validation. A short, invalid, or
failed write returns failure; callers must ignore any bytes received from a
failed invocation instead of treating partial stdout as recoverable state.

Unexpected `OSError`, `ValueError`, or `RuntimeError` from binary stdout write
or flush also produce a typed extraction failure and a nonzero operator exit
status.
The original output error is retained as the cause, without making any
partially emitted bytes authoritative checkpoint data.

The progress-sidecar inspector provides two verified portable-checkpoint views.
`--checkpoint-info PROGRESS.json` validates the mutable sidecar, immutable
generation bytes, outer checkpoint digest, resume identity and position,
canonical envelope, and inner payload digest before reporting only checkpoint
sequence, stage, completed units, state codec, and payload SHA-256.
`--extract-checkpoint STATE_CODEC PROGRESS.json` performs the same durable-state
admission, additionally requires the caller's expected codec, and emits exact
opaque state bytes to binary stdout. Together these provide an operator bridge
from `malbolge-progress-v1` into codec-aware consumers without allowing unknown
checkpoint state to execute automatically.

`--follow PROGRESS.json` adds continuous read-only inspection over the same
validated sidecar summary. It emits the initial state, suppresses unchanged
polls, emits each later sampled change, and exits after emitting a terminal
cancelled/completed/failed state. Observed transitions retain stable job
identity, monotonic timing/unit evidence, immutable same-generation payload
references, and nondecreasing checkpoint sequence.

Polling may skip intermediate checkpoint generations or the transient
`running` publication between `queued` and `checkpointed`/`completed`. The
observer admits these reachable sampled states, but the writer still requires
each immediate lifecycle transition to be valid. Sequence, elapsed-time, and
identity regression remain rejected. The reference poll interval is one second.

The optimizer still consumes an explicit extracted file. Typed-IR compiler
composition now has `resume_typed_ir_from_progress()`, a composition bridge that
invokes the verified extractor for `malbolge-typed-ir-v1` and immediately reruns
complete typed-IR checkpoint admission.

The typed-IR bridge now owns one bounded inspector child transport: a
60-second direct-child deadline, a 64 MiB opaque-state stdout budget, and an
8 KiB diagnostic stderr budget. Both pipes are drained concurrently to avoid
blocking a valid state larger than the operating-system pipe buffer. Timeout,
truncated output, excessive output, diagnostics, and child failure are rejected;
spawn failure retains its separate launch error.

These resource limits apply to the typed-IR Rust bridge and, separately,
to the ternary Rust bridge; they do not constrain the Python sidecar service.
The ternary bridge now uses its own bounded channel-driven transport with the
same 60-second direct-child deadline, 64 MiB state budget, and 8 KiB stderr
budget. Concurrent readers emit one bounded completion each, and neither stage
accepts partial output from an inspector failing resource or status admission.
Timeouts and output overruns terminate and reap the direct inspector child;
a Linux regression independently verifies that a timed-out PID disappears.

Typed-IR extraction rejects a direct inspector's nonzero exit immediately
without waiting for pipe holders to close. The Linux regression launches a
three-second inherited-pipe descendant from a failing inspector and confirms
that rejection occurs before the descendant's natural exit.

Both compiler inspector transports now also reject a completed nonempty
stderr stream immediately, even when a successful direct child leaves stdout
open in an inherited-pipe descendant. Linux regressions use a three-second
stdout holder and require prompt failure without waiting for natural EOF.
Additional marker fixtures prove that rejected diagnostics also terminate the
ordinary descendants before they can perform delayed filesystem writes.

Linux startup-isolation fixture wrappers are published by a short-lived
`/usr/bin/install` child from non-executable source files, rather than being
written as executable inodes by the multithreaded test process. This keeps
writable wrapper descriptors out of unrelated concurrent test forks and
prevents spurious `ETXTBSY` launch failures. The inspector launch policy,
Python isolated startup requirement, and poison-marker checks remain
unchanged. Repeating the default-threaded compiler-IR suite 50 times passed
after this fixture isolation; two of 25 runs had failed before the change.

Both Rust compiler-stage inspector transports now require explicit
directory-qualified interpreter paths. Bare executable names are rejected as
launch failures before host PATH lookup, rather than admitting an unrelated
zero-exit executable and empty checkpoint state. Their existing bounded pipe
and deadline semantics remain unchanged. Linux positive fixtures also verify
successful checkpoint extraction through directory-qualified relative Python
interpreter paths in both compiler stages.

Inspector script arguments now follow Python's `--` option terminator.
A dash-prefixed script name cannot turn the interpreter into a version/option
command; the special lone `-` stdin-script argument is rejected before spawn.
Typed-IR and ternary regressions reproduce the former misclassification
and require transport rejection rather than accepting empty stdout.

Both stage transports invoke their configured Python interpreters in isolated
mode before the option terminator. This ignores inherited Python import-path
and startup environment variables while preserving explicit inspector paths.
Focused stage regressions require the child to report isolated mode; the
production resume bridges still independently validate restored IR bytes.

Linux subprocess fixtures further poison both PYTHONPATH with a side-effect
sitecustomize module and PYTHONHOME with an invalid root, then require exact
checkpoint bytes without the injected marker. Both compiler stages use
separate temporary fixture namespaces for parallel-suite isolation.

On Linux, both transports isolate each inspector in a new process group and
terminate ordinary descendants after both successful and rejected extraction,
including those that redirected all standard streams before the parent exited.
Regression fixtures verify that inherited-pipe holders and redirected-pipe
children cannot write delayed markers after a deadline or successful return.
Other platforms retain direct-child termination, and deliberately detached
Linux sessions are outside this bounded process-group claim.

The product `malbolge` CLI now exposes
`--checkpoint-info PROGRESS.json`,
`--extract-checkpoint STATE_CODEC PROGRESS.json`, and
`--follow-progress PROGRESS.json`. Command-line composition selects the
repository-pinned Python 3.14.7 interpreter plus this trusted inspector and
delegates metadata validation, binary-safe extraction, or continuous
validated summary streaming without parsing sidecar JSON in Rust.

The product CLI now launches that pinned interpreter with Python isolated
mode, so ambient PYTHONPATH, PYTHONHOME and user-site modules cannot
redirect startup or inject sitecustomize before the trusted inspector starts.
End-to-end evidence
provides an intentionally hostile module path and requires no marker write
for checkpoint inspection, checkpoint extraction, or progress following.
All three missing-pointer diagnostics still come from the verified inspector.
A separate positive extraction fixture under the same poisoned Python startup
environment also requires exact verified binary state, including NUL and 0xFF,
without importing the hostile module.

Product compiler resume selection/wiring remains
open because no product compilation command yet consumes restored typed IR.

Compiler integration tests now publish real canonical typed-IR generations
through the production Python sidecar writer, inject process death at every
checkpoint/pointer publication boundary relevant when no partial artifact is
present, and resume through the Rust composition bridge plus production
inspector. Before pointer replacement, resume restores the previous committed
generation; after pointer replacement, it restores the new generation. The
fixture deliberately moves from a CPU sidecar to a CUDA sidecar at generation
two, so the same matrix also exercises backend-neutral compiler-state handoff.

Child-process crash fixtures now terminate after temporary bytes are flushed but
before file synchronization for checkpoint, partial, and sidecar writes;
immediately before or after checkpoint/partial atomic publication; after
checkpoint/partial directory durability confirmation but before immutable
temporary cleanup; after a durable checkpoint; immediately before sidecar
publication; after the mutable sidecar temporary file is durable but before
atomic pointer replacement; after replacement but before directory durability
confirmation; and immediately after sidecar directory durability confirmation.

The same 14 child-process crash boundaries now cover two successive
`running`-status portable checkpoints with real partial payloads. Each recovery
accepts only the state and partial bytes from the last committed pointer,
including when the new immutable generation exists but is not yet referenced.

Canonical typed IR now supplies one concrete compiler-state codec,
`malbolge-typed-ir-v1`: validation-gated canonical bytes can be restored through
`canonical_module()` with exact-tag, bounded-length, UTF-8, trailing-byte, full
IR-validation, and byte-for-byte re-encode checks. The typed-IR stage now has
a single `enter_typed_ir_stage()` handoff that accepts either normalized
frontend evidence or canonical checkpoint bytes and returns the same admitted
module type. Compiler composition can now directly consume a progress-sidecar
path through the explicit verified composition bridge; it still does not
publish
that state itself. Generic checkpoint metadata discovery remains available
through the progress inspector.

Pre-layout ternary IR now provides the next compiler-state resume stage. Its
`malbolge-ternary-ir-v1` codec is admitted through a single fresh-or-checkpoint
`enter_ternary_stage()` handoff, and `resume_ternary_from_progress()`
delegates durable envelope and codec validation to the trusted inspector before
revalidating the extracted program bytes. Integration evidence publishes two
real canonical ternary generations with the production writer and injects
process death at ten checkpoint/pointer boundaries. Pre-pointer crashes
restore the prior CPU-labelled generation; post-replacement crashes restore
the new CUDA-labelled generation through the production inspector.

Product CLI metadata inspection, explicit-codec binary checkpoint extraction,
and continuous validated progress following are now wired through the trusted
inspector. Product compiler resume selection/wiring and compiler-stage codecs
beyond ternary lowering, crash injection beyond the ternary stage and final-
artifact publication, and later compiler-execution CPU/CUDA resume equivalence
remain unimplemented.

### Sidecar Schema

The first accepted schema is identified by `malbolge-progress-v1`. The JSON
object must contain at least:

- `schema`, `operation_id`, and `status`;
- requested output path and canonical sidecar/checkpoint paths;
- source path plus cryptographic source identity;
- target profile ID and fingerprint;
- exact lowercase 40-hex Git `repository_revision`, toolchain fingerprint,
  algorithm ID/version, and seed when applicable;
- backend kind plus device identity when an accelerator is used;
- current pipeline stage, checkpoint sequence, completed units, and total units
  when the total is knowable;
- UTC `started_at`, `updated_at`, and optional `completed_at` timestamps;
- persisted `active_elapsed_ns`, `wall_elapsed_ns`, verification time,
  serialization time, and checkpoint overhead;
- checkpoint compatibility fingerprint and checkpoint SHA-256;
- partial-output byte count/hash when a partial artifact exists;
- stable diagnostic code and message for failed or cancelled jobs.

Percent completion is emitted only when the denominator is stable and known.
Unknown totals remain `null`; the tool reports counters and stage identity
instead of inventing a percentage.

### Operator inspection

The reference inspector prints one exact key/value summary without rounding
scientific timing:

```powershell
.dependencies/python/3.14.7/Scripts/python-jig.cmd `
  src/automation/repository/composition/scripts/progress_sidecar.py `
  output.malbolge.progress.json
```

The summary includes status, stage, completed/total units, active/wall/paused
nanoseconds, verification/serialization/checkpoint nanoseconds, and canonical
progress/checkpoint/partial paths. The JSON sidecar remains the machine-readable
authority; this line is an operator view over the same validated record.

Path values in the summary use percent-encoded filesystem bytes with `/`
separators preserved, keeping each progress update on one line even if the
original filename contains spaces, tabs, newlines, or non-UTF-8 POSIX bytes.
Decode a displayed path with URL percent-decoding to bytes, followed by the
host's filesystem decoding; `none` denotes an absent checkpoint or partial.
The durable sidecar JSON retains its original canonical path spellings.
Invalid UTF-8 is converted to the same stable inspection failure as malformed
schema or missing storage rather than escaping as a decoder exception.

A verified inner checkpoint payload can be extracted without trusting the
mutable pointer or outer envelope directly:

```powershell
.dependencies/python/3.14.7/Scripts/python-jig.cmd `
  src/automation/repository/composition/scripts/progress_sidecar.py `
  --extract-checkpoint evaluated-search-prefix-evidence-v1 `
  output.malbolge.progress.json > search.resume.json
```

The output bytes are exact and binary-safe. Extraction emits nothing when the
sidecar, referenced generation, outer digest, resume position, state codec,
canonical encoding, or inner payload digest is invalid.


Compiler composition now provides an explicit Fresh-versus-Progress selector
for both implemented resumable stages. Typed IR chooses normalized frontend
evidence or verified typed-IR progress extraction; ternary lowering chooses an
admitted typed-IR projection or verified ternary progress extraction. The
selectors preserve route-specific failure identity and do not parse sidecar
JSON, portable checkpoint envelopes, or payload bytes outside each stage's
existing admission boundary. The future top-level compiler/CLI must compose
these selectors once a product C-to-Malbolge pipeline exists.

## Invariants

- Checkpoint and partial generations are immutable and sequence-addressed.
- Generation payloads use write-to-temporary, flush, and atomic no-replace
  publication before the canonical sidecar pointer is replaced. Windows uses a
  same-directory no-replace rename instead of requiring hard-link support;
  POSIX uses a same-filesystem hard link. A collided destination is re-read to
  prove byte identity; collision admission also requires a regular single-link
  inode before and after this read, with stable device/inode identity. This
  rejects pre-existing or newly linked foreign aliases even when bytes match,
  so byte-identical collision reuse cannot certify externally mutable state.

  The immutable publisher also retains the exact fsynced staging inode on a
  new no-replace publication, or the admitted collision inode on reuse. Its
  first post-publication pathname stat must still identify that inode; an
  intervening byte-identical pathname replacement cannot silently become the
  durability or final-verification baseline. An observed swap fails with
  committed-path evidence and cannot publish a new progress pointer. This
  check does not promise an atomic snapshot against adversarial later writes.

  One narrow recovery case preserves post-commit cleanup failure semantics: if
  the collision has exactly two links, and the extra link is the sole
  same-inode sibling matching the writer's temporary naming convention, the
  retry first validates the collided bytes through a bounded, stable-inode
  read against the proposed generation. It then rechecks the collided inode,
  link count, timestamps, and alias identity before unlinking that staging
  entry and rechecking single-link identity. Recovery repeats nonfollowing
  regular-inode admission immediately before unlink to reject an unrelated
  replacement inserted after the full alias check, leaving that foreign entry
  untouched; this remains subject to a final pathname check-to-unlink race.

  A mismatched, oversized, or concurrently rewritten collision leaves the
  suspected alias untouched; a
  foreign alias without that narrow recovery path remains rejected. Recovery
  inventories at most 4,096 physical directory entries, counting unrelated
  siblings; a larger inventory fails closed without unlinking a retained alias.
  For ordinary basenames the staging prefix retains the destination's
  literal filename and exact suffix: `?`, `*`, and `[` in a valid POSIX
  filename are never treated as wildcards. When the filesystem-encoded
  direct prefix would exceed 128 bytes, mutable pointer and immutable
  generation writers instead use the reproducible compact prefix
  `.progress-` followed by 24 lowercase SHA-256 hex digits and a period,
  derived from the full destination basename.
  Both writers use this prefix for exclusive temporary creation; immutable
  recovery searches the identical prefix. The digest is a naming hint,
  never an identity authority: retained aliases still require the original
  regular inode, exact content, link count and eight-character stage token.
  Valid long target names no longer fail solely because their temporary
  name would exceed the filesystem's per-component length limit; target
  and writer-lock filenames must still be individually representable.

  Furthermore, recovery accepts only the eight-character
  lowercase/digit/underscore temporary token
  format emitted by the pinned Python 3.14 `mkstemp`, not arbitrary
  temporary-looking suffixes. Legitimate retained aliases for these literal
  filenames remain recoverable. The token is only an accidental-match guard,
  not proof that a same-pattern entry was created by this writer; an adversary
  with directory-write access and the expected spelling can still forge it.

  If the destination disappears or becomes unreadable during the collision
  check, publication fails with the stable sidecar error rather than leaking
  a raw filesystem exception. These checks remain subject to post-admission
  filesystem races. Canonical sidecar,
  writer-lock, checkpoint, and partial-generation paths reject symlink or
  junction components
  from the leaf through the ancestor chain; a byte-identical redirected target
  is not accepted as mutable or immutable state.
- A rejected transition, malformed direct API value, missing generation, or
  payload/hash/length mismatch never replaces the last valid sidecar. Concurrent
  writers serialize transition validation and pointer replacement through the
  same persistent sibling lock path.
- Publication commit and parent-directory durability confirmation are separate.
  A synchronization failure after atomic replacement or immutable publication
  reports the exact committed path and never claims that the prior state was
  restored.
- The final `.malbolge` path is published atomically only after independent
  verification succeeds.
- Resume compatibility binds source identity, target profile, exact repository
  revision, toolchain fingerprint, algorithm version, seed, and checkpoint
  schema.
  Any mismatch is rejected unless an explicit reviewed migration exists.
- Device-local memory is never the only copy of resumable state. GPU jobs emit a
  backend-neutral durable checkpoint sufficient for CPU inspection and exact
  compatibility checks. `malbolge-checkpoint-v1` carries no backend or device
  identity; backend-specific state must be normalized by the owning state codec
  before publication.
- `active_elapsed_ns` is accumulated from monotonic clock segments. UTC wall
  timestamps provide chronology but never replace monotonic duration
  measurement.
- Paused time, checkpoint overhead, verification, serialization, and active
  compute/search time remain distinguishable for scientific analysis. Their
  exclusive nanosecond counters exactly partition `wall_elapsed_ns`.
- The sidecar is evidence and recovery state, not semantic authority. Source,
  target profile, compiler, verifier, and accepted artifact determine meaning.
- Routine progress writes are rate-limited by an explicit positive monotonic
  interval so checkpointing does not become an unmeasured dominant cost. The
  first routine write is eligible immediately; queued-to-running, any
  checkpoint-sequence advance, checkpointed, and terminal states bypass
  suppression.
- A suspicious transition compared with the last committed sidecar reaches
  the authoritative writer instead of being ignored, even when another
  process has since advanced the pointer.
- Only attempts that cross publication commit start a new rate window.
  Suppressed writes still advance the limiter's monotonic observation floor;
  a later regressed sample is rejected without permitting an unnecessary
  write. Mandatory checkpoint and terminal publications also require
  nonregressed clock samples, even though they bypass rate suppression.

## Failure Behavior

On orderly cancellation or a handled failure, the job writes one final sidecar
state and preserves the most recent valid generation. On abrupt process or host
failure, restart follows only the last atomically committed sidecar pointer.
Later unreferenced generation files cannot invalidate that pointer. Missing,
stale, overwritten, or incompatible generation data is rejected with a stable
diagnostic and never guessed into validity.

Sidecar reads, writer-lock lifecycle, and mutable or immutable pre-publication
failures are likewise translated into the stable sidecar error boundary rather
than leaking host filesystem exceptions. Both direct pointer updates and
checkpoint generation publication use a non-following metadata probe: only
an absent pointer is accepted as new, while permission and other metadata
errors produce a typed failure before any durable generation is published.

Unexpected `ValueError` and `RuntimeError` faults during temporary
checkpoint, partial, or sidecar file synchronization remain in the typed
publication boundary. A partial-write failure after a durable checkpoint
retains the checkpoint as last committed path, and a sidecar-write failure
after both immutable members retain the partial as last committed path.
An earlier failure before the first checkpoint commit remains a typed ordinary
publication error without inventing committed evidence.

Post-commit failures preserve the
committed path through `ProgressSidecarCommittedError`; directory-sync failures
use its `ProgressSidecarDurabilityError` subtype, while later lock cleanup
failures report that the pointer committed durably before cleanup failed.

If checkpoint persistence fails, the job may continue only when the caller
explicitly accepts non-resumable execution. Public CLI defaults fail closed for
jobs that requested resumability.

## Verification

- Schema tests validate every required field, status transition, and unknown-
  total representation.
- Crash fixtures terminate a child process after temporary bytes are flushed but
  before file synchronization for checkpoint, partial, and sidecar writes;
  immediately before or after checkpoint/partial atomic publication; after
  checkpoint/partial directory sync but before immutable temporary cleanup;
  after a durable checkpoint; immediately before sidecar publication; after the
  mutable sidecar temporary file is durable but before atomic pointer
  replacement; after replacement but before directory durability confirmation;
  and immediately after sidecar directory durability confirmation. Restart
  observes the last pointer
  that actually crossed atomic replacement at each boundary.
- Prepublication durability tests inject temporary-file synchronization failure
  for immutable checkpoint and mutable sidecar writes, prove no canonical path
  crosses commit, clean the temporary pathname, and preserve any prior pointer.
- Durability-failure tests inject parent-directory synchronization failure
  after checkpoint, partial, and mutable sidecar publication and retain the
  exact committed path as evidence.
- Resume tests cover unchanged jobs, monotonic transitions, exact repository
  revision and source/profile/toolchain mismatch, overwritten or missing
  generations, durable cancellation/failure/completion publication, and
  rejected terminal-job reopening. Two-process fixtures prove both lock
  exclusion and
  post-lock revalidation: a stale candidate that
  waited behind a newer commit is rejected before mutable-pointer replacement.
- Portable-checkpoint tests prove that identical opaque state produces
  byte-exact checkpoint envelopes for CPU and CUDA sidecars and that identity,
  position, codec, payload, and canonical-encoding drift fail closed.
- Evaluated-search checkpoint tests cover empty and partial prefixes, packed
  candidate storage, exact request/batch drift, malformed/noncanonical JSON,
  mutable aliases, and explicit absence of backend/device identity.
- Resumed-search tests compare interrupted and uninterrupted execution, preserve
  indexed suffix storage, materialize packed suffix evidence safely, reject
  backend/proposal drift, and exercise CPU-to-CUDA plus CUDA-to-CPU rotate and
  crazy-target resume with byte-identical checkpoints and matching proposals.
- Typed-IR compiler tests round-trip canonical and extended semantic modules,
  reject every truncated canonical prefix, unknown tags, wrong magic/version,
  invalid UTF-8, trailing bytes, and semantically invalid restored modules. They
  also prove fresh normalized frontend entry and resumed canonical entry
  converge on the same admitted typed-IR module while preserving failure
  categories. Progress-adapter tests cover exact codec extraction arguments,
  launch/rejection/diagnostic failures, malformed extracted bytes, and
  successful restoration of the tracked canonical typed-IR golden. A
  cross-language crash matrix additionally publishes real typed-IR generations,
  kills publication at ten checkpoint/pointer boundaries, and proves the Rust
  resume bridge restores exactly the last committed generation.
- Ternary compiler tests now publish two canonical `malbolge-ternary-ir-v1`
  generations through the production sidecar writer, inject process death at
  the same ten checkpoint/pointer boundaries, and resume through the Rust
  ternary bridge plus production inspector. The first generation is CPU-labelled
  and the second CUDA-labelled; recovery follows only the last committed sidecar
  pointer, proving backend identity does not become ternary checkpoint state.
- Prepared-search resume tests cover partial and completed projected prefixes,
  empty rotate prefixes, exact projected-batch binding, uninterrupted prepared
  equivalence, and live bidirectional CPU/CUDA resume for rotate and crazy
  targets with byte-identical backend-neutral checkpoint state.
- Search CLI tests cover CPU resume, unavailable-CUDA fallback, live CUDA
  resume, unsupported-algorithm rejection, checkpoint file loading,
  malformed-state rejection, resumed JSON checkpoint/executor provenance, and
  the sidecar-extraction-to-optimizer subprocess bridge.
- Progress-sidecar recovery tests inject every publication crash boundary using
  real portable checkpoint envelopes and prove that recovery decodes only the
  last sidecar-committed inner state. The same matrix now carries tracked
  canonical `malbolge-typed-ir-v1` modules before and after each crash, proving
  byte-exact non-search compiler-state recovery at the generic sidecar boundary.
  Operator inspection tests also prove verified typed-IR codec/payload-digest
  discovery and fail-closed outer-digest drift. Extraction tests prove exact
  binary stdout, help discovery, and fail-closed state-codec mismatch handling.
- The tracked canonical `malbolge-typed-ir-v1` fixture produces byte-identical
  envelopes under CPU and CUDA sidecar identities, with identical verified
  metadata and byte-exact decoded compiler state. Backend/device identity is not
  part of portable typed-IR checkpoint compatibility.
- Timing tests use an injected monotonic clock, exercise every exclusive
  phase, reject foreign phases, corrupt direct timer state, boolean/negative/
  backward samples, and prove
  active, paused, wall, verification, serialization, and checkpoint durations
  are not conflated.
- Direct-construction tests mutate resume identity and sidecar fields, reject
  boolean sequence aliases and impossible UTC dates, and prove pointer
  publication validates the referenced checkpoint/partial generation first.
- Continuous sidecar inspection is implemented by the reference `--follow` mode
  and product `--follow-progress` delegation. Tests cover unchanged-poll
  suppression, sampled checkpoint-generation jumps, backward-state rejection,
  terminal exit, missing storage, and exact one-line terminal product output.
- Final `.malbolge` artifact publication remains an open verification item.
  No current compiler backend emits that artifact, so atomic final publication
  is not yet claimed as implemented evidence.

## References

<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- [Compiler Pipeline And Guest Runtime](../adr/compiler-pipeline-and-guest-runtime.md)
- [Verification Trust Boundary](../adr/verification-trust-boundary.md)
<!-- jig-ignore-next-line: canonical path or identifier is indivisible -->
- [Parametric Multi Objective Algorithm Evaluation](../../research/adr/parametric-multi-objective-algorithm-evaluation.md)
