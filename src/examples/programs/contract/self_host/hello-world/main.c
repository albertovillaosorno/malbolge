// Copyright:
//   - Copyright (c) 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - A freestanding enterprise-critical Hello World demonstration.
// - Must-Not:
//   - Use hosted libc, threads, dynamic allocation, or host-side construction.
// - Allows:
//   - Inputs: no guest input.
//   - Outputs: the byte sequence "Hello, World!\n".
//   - Side effects: fundamental guest byte output only.
// - Split-When:
//   - Split when any demonstration layer gains independent conformance value.
// - Merge-When:
//   - Merge when another example owns the same absurd assurance exercise.
// - Summary:
//   - Emit Hello World through redundant safety and security theater.
// - Description:
//   - Demonstrates deterministic defenses without external dependencies.
// - Usage:
//   - Compile as one guest C translation unit without hosted services.
// - Defaults:
//   - Reject inconsistent state before authorizing irreversible output.
//

//! Enterprise-critical Hello World without libc, allocation, or hidden
//! services. The module is intentionally excessive so every layer must justify
//! its presence through a deterministic invariant rather than through
//! architectural fashion.

void __malbolge_output_byte(unsigned int value);

enum
{
    AUDIT_CAPACITY = 64,
    BYTE_CARDINALITY = 256,
    DIGEST_MODULUS = 59049,
    EVENT_CAPACITY = 4,
    INSTRUCTION_COUNT = 6,
    LATTICE_DIMENSION = 4,
    LATTICE_MODULUS = 257,
    MESSAGE_DIGEST = 4586,
    MESSAGE_LENGTH = 14,
    QUORUM_NODE_COUNT = 5,
    QUORUM_REQUIRED = 3,
    RESIDUE_MODULUS_A = 5,
    RESIDUE_MODULUS_B = 7,
    RESIDUE_MODULUS_C = 11,
    SEAL_MODULUS = 257,
    STATUS_FAILURE = 1,
    STATUS_SUCCESS = 0,
    VM_STEP_BUDGET = 256,
    VM_WORD_MASK = 134217727
};

/// A symbol carries overlapping representations because no single encoding is
/// trusted to diagnose both storage corruption and decoder mistakes.
typedef struct EncodedSymbol
{
        unsigned int low_codeword;
        unsigned int high_codeword;
        unsigned int residue_a;
        unsigned int residue_b;
        unsigned int residue_c;
        unsigned int seal;
} EncodedSymbol;

/// A replica returns evidence as well as a value so consensus cannot
/// accidentally optimize five identical calls into one unexamined opinion.
typedef struct ReplicaVote
{
        unsigned int valid;
        unsigned int value;
        unsigned int work_digest;
} ReplicaVote;

/// Phases exist because irreversible output must remain separated from every
/// operation that can still discover inconsistent state.
typedef enum TransactionPhase
{
    TRANSACTION_VALIDATE,
    TRANSACTION_ATTEST,
    TRANSACTION_COMMIT,
    TRANSACTION_FINISHED,
    TRANSACTION_REJECTED
} TransactionPhase;

/// A snapshot is deliberately small so rollback copies only authority-bearing
/// state and never copies telemetry into the semantic decision.
typedef struct Snapshot
{
        unsigned int cursor;
        unsigned int digest;
        TransactionPhase phase;
} Snapshot;

/// Telemetry is stored locally because observability must not create a new host
/// dependency or alter the externally visible byte stream.
typedef struct Telemetry
{
        unsigned int audit_records;
        unsigned int corrected_codewords;
        unsigned int consensus_rounds;
        unsigned int decode_candidates;
        unsigned int dispatched_events;
        unsigned int lattice_checks;
        unsigned int rollbacks;
} Telemetry;

/// Audit records are bounded because an assurance feature that can exhaust
/// memory would become a reliability defect in the program it claims to
/// observe.
typedef struct AuditRecord
{
        unsigned int event_kind;
        unsigned int position;
        unsigned int trace_id;
        unsigned int span_id;
        unsigned int state_digest;
} AuditRecord;

/// The proof object is intentionally explicit so the implementation cannot hide
/// a boolean named `secure` behind an undocumented helper.
typedef struct LatticeProof
{
        unsigned int challenge;
        unsigned int commitment[LATTICE_DIMENSION];
        unsigned int response[LATTICE_DIMENSION];
} LatticeProof;

/// Events permit producer, policy, and service roles to remain reviewable while
/// cooperative dispatch preserves Malbolge's deterministic sequential
/// semantics.
typedef enum EventKind
{
    EVENT_VALIDATE_SYMBOL,
    EVENT_COMMIT_SYMBOL
} EventKind;

/// Trace identifiers live beside the request because local observability should
/// survive refactoring without becoming part of the emitted protocol.
typedef struct Event
{
        EventKind kind;
        unsigned int position;
        unsigned int trace_id;
        unsigned int span_id;
} Event;

/// A fixed ring buffer models an internal broker without pretending that guest
/// threads or asynchronous completion exist where the target provides neither.
typedef struct EventBus
{
        Event queue[EVENT_CAPACITY];
        unsigned int count;
        unsigned int head;
        unsigned int tail;
} EventBus;

/// The transaction owns the staged bytes because validation must finish before
/// output authorization can begin.
typedef struct Transaction
{
        unsigned int cursor;
        unsigned int digest;
        unsigned int dispatch_lease;
        unsigned int staged[MESSAGE_LENGTH];
        TransactionPhase phase;
} Transaction;

/// A separate machine state makes the Harvard split visible: instructions
/// remain immutable while all mutable authority stays in the data context.
typedef struct VirtualMachine
{
        unsigned int faulted;
        unsigned int halted;
        unsigned int program_counter;
        unsigned int steps;
} VirtualMachine;

/// One context gathers assurance state so no service receives ambient authority
/// through globals or unspecified host runtime state.
typedef struct EnterpriseSystem
{
        AuditRecord audit[AUDIT_CAPACITY];
        EventBus bus;
        LatticeProof proof;
        Snapshot snapshots[MESSAGE_LENGTH + 1];
        Telemetry telemetry;
        Transaction transaction;
        VirtualMachine machine;
        unsigned int attested;
        unsigned int trace_id;
} EnterpriseSystem;

typedef enum VirtualOpcode
{
    VM_SCHEDULE_VALIDATE = 1,
    VM_DISPATCH_EVENT = 2,
    VM_BUILD_ATTESTATION = 3,
    VM_SCHEDULE_COMMIT = 4,
    VM_HALT = 5
} VirtualOpcode;

/// The repeated initializer is a source-level declaration that each voter owns
/// distinct storage even though all voters begin with the same encoded
/// evidence.
#define MESSAGE_REPLICA                                                        \
    {                                                                          \
        {75U, 170U, 2U, 2U, 6U, 117U},  {45U, 51U, 1U, 3U, 2U, 179U},          \
        {225U, 51U, 3U, 3U, 9U, 198U},  {225U, 51U, 3U, 3U, 9U, 215U},         \
        {255U, 51U, 1U, 6U, 1U, 86U},   {225U, 153U, 4U, 2U, 0U, 194U},        \
        {0U, 153U, 2U, 4U, 10U, 24U},   {180U, 45U, 2U, 3U, 10U, 20U},         \
        {255U, 51U, 1U, 6U, 1U, 154U},  {153U, 180U, 4U, 2U, 4U, 25U},         \
        {225U, 51U, 3U, 3U, 9U, 77U},   {170U, 51U, 0U, 2U, 1U, 55U},          \
        {135U, 153U, 3U, 5U, 0U, 163U}, {210U, 0U, 0U, 3U, 10U, 100U},         \
    }

/// Five physical copies are wasteful on purpose: a majority vote cannot
/// tolerate an isolated storage fault when every voter reads the same damaged
/// cell.
static const EncodedSymbol message_replicas[QUORUM_NODE_COUNT][MESSAGE_LENGTH] =
    {
        MESSAGE_REPLICA, MESSAGE_REPLICA, MESSAGE_REPLICA,
        MESSAGE_REPLICA, MESSAGE_REPLICA,
};

#undef MESSAGE_REPLICA

/// The matrix is tiny because it demonstrates an algebraic relation, not
/// because it offers meaningful cryptographic parameters against a quantum
/// adversary.
static const unsigned int lattice_matrix[LATTICE_DIMENSION][LATTICE_DIMENSION] =
    {
        {3U, 5U, 7U, 11U},
        {13U, 17U, 19U, 23U},
        {29U, 31U, 37U, 41U},
        {43U, 47U, 53U, 59U},
};

/// Keeping the toy witness obvious prevents the educational attestation from
/// being mistaken for secret material or deployable post-quantum cryptography.
static const unsigned int lattice_secret[LATTICE_DIMENSION] = {
    17U,
    29U,
    43U,
    71U,
};

/// The public vector binds the verifier to one relation while allowing the
/// proof generation and verification paths to remain mechanically different.
static const unsigned int lattice_public[LATTICE_DIMENSION] = {
    250U,
    80U,
    240U,
    81U,
};

/// Guarded instruction words catch accidental corruption before an opcode gains
/// authority over the transaction state.
static const unsigned int instruction_memory[INSTRUCTION_COUNT] = {
    20481U, 44034U, 67587U, 91140U, 58626U, 119557U,
};

/// Mixing is intentionally simple and deterministic because trace identity is
/// an observability aid, never a security boundary or a substitute for
/// equality.
static unsigned int mix(unsigned int state, unsigned int value)
{
    return (state * 109U + value * 31U + 17U) % DIGEST_MODULUS;
}

/// Bit extraction is centralized so the error-correction equations remain
/// reviewable and cannot drift between encoder positions.
static unsigned int code_bit(unsigned int codeword, unsigned int position)
{
    return (codeword >> (position - 1U)) & 1U;
}

/// SECDED exists because correcting one storage fault is more useful than
/// merely announcing that a cosmic ray has ruined a fourteen-byte mission.
static int decode_secded_nibble(unsigned int codeword, unsigned int *nibble,
                                unsigned int *corrected)
{
    unsigned int overall;
    unsigned int syndrome;
    unsigned int sanitized = codeword & 255U;

    syndrome = code_bit(sanitized, 1U) ^ code_bit(sanitized, 3U) ^
               code_bit(sanitized, 5U) ^ code_bit(sanitized, 7U);
    syndrome |= (code_bit(sanitized, 2U) ^ code_bit(sanitized, 3U) ^
                 code_bit(sanitized, 6U) ^ code_bit(sanitized, 7U))
                << 1U;
    syndrome |= (code_bit(sanitized, 4U) ^ code_bit(sanitized, 5U) ^
                 code_bit(sanitized, 6U) ^ code_bit(sanitized, 7U))
                << 2U;

    overall = code_bit(sanitized, 1U) ^ code_bit(sanitized, 2U) ^
              code_bit(sanitized, 3U) ^ code_bit(sanitized, 4U) ^
              code_bit(sanitized, 5U) ^ code_bit(sanitized, 6U) ^
              code_bit(sanitized, 7U) ^ code_bit(sanitized, 8U);
    *corrected = 0U;

    if (syndrome != 0U && overall == 0U)
    {
        return 0;
    }
    if (syndrome != 0U)
    {
        sanitized ^= 1U << (syndrome - 1U);
        *corrected = 1U;
    }
    else if (overall != 0U)
    {
        sanitized ^= 1U << 7U;
        *corrected = 1U;
    }

    *nibble = code_bit(sanitized, 3U) | (code_bit(sanitized, 5U) << 1U) |
              (code_bit(sanitized, 6U) << 2U) | (code_bit(sanitized, 7U) << 3U);
    return 1;
}

/// A positional seal prevents two valid symbols from being silently exchanged,
/// which residue and error-correction checks alone would not detect.
static unsigned int expected_seal(unsigned int position, unsigned int value)
{
    return (value * 37U + position * 17U + 23U) % SEAL_MODULUS;
}

/// Independent congruences make the decoded byte cross-check its own binary
/// representation through arithmetic that fails differently from SECDED.
static int residues_match(const EncodedSymbol *symbol, unsigned int candidate)
{
    return candidate % RESIDUE_MODULUS_A == symbol->residue_a &&
           candidate % RESIDUE_MODULUS_B == symbol->residue_b &&
           candidate % RESIDUE_MODULUS_C == symbol->residue_c;
}

/// Every replica evaluates all 256 candidates so source-level work does not
/// reveal where the matching byte occurs; this is not a certified timing claim.
static ReplicaVote decode_replica(unsigned int node, unsigned int position,
                                  Telemetry *telemetry)
{
    const EncodedSymbol *const symbol = &message_replicas[node][position];
    ReplicaVote vote = {0U, 0U, node + 1U};
    unsigned int candidate = 0U;
    unsigned int corrected_high = 0U;
    unsigned int corrected_low = 0U;
    unsigned int high = 0U;
    unsigned int low = 0U;
    unsigned int matches = 0U;
    unsigned int recovered = 0U;

    if (!decode_secded_nibble(symbol->low_codeword, &low, &corrected_low) ||
        !decode_secded_nibble(symbol->high_codeword, &high, &corrected_high))
    {
        return vote;
    }

    telemetry->corrected_codewords += corrected_low + corrected_high;
    while (candidate < BYTE_CARDINALITY)
    {
        const unsigned int ecc_value = low | (high << 4U);
        const unsigned int accepted =
            (unsigned int)(candidate == ecc_value &&
                           residues_match(symbol, candidate) &&
                           expected_seal(position, candidate) == symbol->seal);

        vote.work_digest = mix(vote.work_digest, candidate + accepted * 257U);
        recovered = accepted != 0U ? candidate : recovered;
        matches += accepted;
        ++candidate;
    }

    telemetry->decode_candidates += BYTE_CARDINALITY;
    vote.valid = (unsigned int)(matches == 1U);
    vote.value = recovered;
    return vote;
}

/// Majority selection scans the whole byte domain because choosing the first
/// vote would turn replica ordering into an undocumented source of authority.
static int consensus_decode(EnterpriseSystem *system, unsigned int position,
                            unsigned int *value)
{
    ReplicaVote votes[QUORUM_NODE_COUNT];
    unsigned int candidate = 0U;
    unsigned int node = 0U;
    unsigned int quorum_matches = 0U;
    unsigned int selected = 0U;
    unsigned int transcript = 0U;

    while (node < QUORUM_NODE_COUNT)
    {
        votes[node] = decode_replica(node, position, &system->telemetry);
        transcript = mix(transcript, votes[node].work_digest);
        ++node;
    }

    while (candidate < BYTE_CARDINALITY)
    {
        unsigned int votes_for_candidate = 0U;

        node = 0U;
        while (node < QUORUM_NODE_COUNT)
        {
            votes_for_candidate +=
                (unsigned int)(votes[node].valid != 0U &&
                               votes[node].value == candidate);
            ++node;
        }
        if (votes_for_candidate >= QUORUM_REQUIRED)
        {
            selected = candidate;
            ++quorum_matches;
        }
        ++candidate;
    }

    system->telemetry.consensus_rounds += 1U;
    if (quorum_matches != 1U || transcript == 0U)
    {
        return 0;
    }
    *value = selected;
    return 1;
}

/// The ternary-sized modulus keeps the integrity summary aligned with the
/// target machine's mathematical identity instead of borrowing a host checksum.
static unsigned int extend_digest(unsigned int digest, unsigned int position,
                                  unsigned int value)
{
    return (digest * 3U + value + position) % DIGEST_MODULUS;
}

/// Checkpoints are captured before each decision so failure handling can
/// restore the last state whose authority was already established.
static void save_checkpoint(EnterpriseSystem *system)
{
    const unsigned int slot = system->transaction.cursor;

    system->snapshots[slot].cursor = system->transaction.cursor;
    system->snapshots[slot].digest = system->transaction.digest;
    system->snapshots[slot].phase = system->transaction.phase;
}

/// Range verification supports fault localization without trusting the state
/// that reported the fault, even when immutable data makes repair impossible.
static int verify_range(EnterpriseSystem *system, unsigned int begin,
                        unsigned int end)
{
    unsigned int position = begin;
    unsigned int value = 0U;

    while (position < end)
    {
        if (!consensus_decode(system, position, &value))
        {
            return 0;
        }
        ++position;
    }
    return 1;
}

/// Binary search bounds reviewer effort after corruption; healthy execution
/// does not pay for theatrical incident response.
static unsigned int locate_first_invalid(EnterpriseSystem *system,
                                         unsigned int end)
{
    unsigned int high = end;
    unsigned int low = 0U;

    while (low < high)
    {
        const unsigned int middle = low + (high - low) / 2U;

        if (verify_range(system, low, middle + 1U))
        {
            low = middle + 1U;
        }
        else
        {
            high = middle;
        }
    }
    return low < MESSAGE_LENGTH ? low : MESSAGE_LENGTH;
}

/// Rollback rejects rather than inventing data because recovery without a valid
/// quorum would convert availability pressure into silent corruption.
static void rollback_and_reject(EnterpriseSystem *system)
{
    const unsigned int failed =
        locate_first_invalid(system, system->transaction.cursor + 1U);
    const unsigned int restore = failed < system->transaction.cursor
                                     ? failed
                                     : system->transaction.cursor;

    system->transaction.cursor = system->snapshots[restore].cursor;
    system->transaction.digest = system->snapshots[restore].digest;
    system->transaction.phase = TRANSACTION_REJECTED;
    system->telemetry.rollbacks += 1U;
}

/// Bounded audit storage favors deterministic loss accounting over unbounded
/// logs that could outlive the tiny payload by several orders of magnitude.
static void append_audit(EnterpriseSystem *system, const Event *event)
{
    const unsigned int slot = system->telemetry.audit_records % AUDIT_CAPACITY;

    system->audit[slot].event_kind = (unsigned int)event->kind;
    system->audit[slot].position = event->position;
    system->audit[slot].trace_id = event->trace_id;
    system->audit[slot].span_id = event->span_id;
    system->audit[slot].state_digest = system->transaction.digest;
    system->telemetry.audit_records += 1U;
}

/// The broker fails closed at capacity because dropping an authorization event
/// would be less observable and more dangerous than rejecting the transaction.
static int enqueue(EventBus *bus, Event event)
{
    if (bus->count == EVENT_CAPACITY)
    {
        return 0;
    }
    bus->queue[bus->tail] = event;
    bus->tail = (bus->tail + 1U) % EVENT_CAPACITY;
    bus->count += 1U;
    return 1;
}

/// Dequeue uses caller-owned storage so the bus never returns a pointer whose
/// lifetime could be invalidated by the next cooperative dispatch.
static int dequeue(EventBus *bus, Event *event)
{
    if (bus->count == 0U)
    {
        return 0;
    }
    *event = bus->queue[bus->head];
    bus->head = (bus->head + 1U) % EVENT_CAPACITY;
    bus->count -= 1U;
    return 1;
}

/// Matrix multiplication is separated so proof generation and verification
/// share arithmetic rules without sharing the claims they are expected to
/// prove.
static unsigned int
lattice_row_product(unsigned int row,
                    const unsigned int vector[LATTICE_DIMENSION])
{
    unsigned int column = 0U;
    unsigned int result = 0U;

    while (column < LATTICE_DIMENSION)
    {
        result = (result + lattice_matrix[row][column] * vector[column]) %
                 LATTICE_MODULUS;
        ++column;
    }
    return result;
}

/// The challenge binds the proof to the validated digest so a proof from
/// another payload cannot authorize this transaction.
static unsigned int proof_challenge(const LatticeProof *proof,
                                    unsigned int digest)
{
    unsigned int challenge = digest % LATTICE_MODULUS;
    unsigned int index = 0U;

    while (index < LATTICE_DIMENSION)
    {
        challenge = (challenge * 3U + proof->commitment[index] + index) %
                    LATTICE_MODULUS;
        ++index;
    }
    return challenge;
}

/// The toy prover constructs a real algebraic identity, while tiny public
/// parameters prevent the exercise from masquerading as real cryptography.
static void build_lattice_proof(unsigned int digest, LatticeProof *proof)
{
    unsigned int nonce[LATTICE_DIMENSION];
    unsigned int index = 0U;

    while (index < LATTICE_DIMENSION)
    {
        nonce[index] =
            (digest * (index + 3U) + index * index + 41U) % LATTICE_MODULUS;
        ++index;
    }

    index = 0U;
    while (index < LATTICE_DIMENSION)
    {
        proof->commitment[index] = lattice_row_product(index, nonce);
        ++index;
    }
    proof->challenge = proof_challenge(proof, digest);

    index = 0U;
    while (index < LATTICE_DIMENSION)
    {
        proof->response[index] =
            (nonce[index] + proof->challenge * lattice_secret[index]) %
            LATTICE_MODULUS;
        ++index;
    }
}

/// Verification recomputes both sides independently so construction cannot
/// grant itself authority merely by returning a favorable boolean.
static int verify_lattice_proof(unsigned int digest, const LatticeProof *proof)
{
    unsigned int row = 0U;

    if (proof->challenge != proof_challenge(proof, digest))
    {
        return 0;
    }

    while (row < LATTICE_DIMENSION)
    {
        const unsigned int left = lattice_row_product(row, proof->response);
        const unsigned int right =
            (proof->commitment[row] + proof->challenge * lattice_public[row]) %
            LATTICE_MODULUS;

        if (left != right)
        {
            return 0;
        }
        ++row;
    }
    return 1;
}

/// A dispatch lease binds proof, digest, and staged bytes so authorization
/// cannot survive a later mutation of the data it was meant to approve.
static unsigned int derive_dispatch_lease(const EnterpriseSystem *system)
{
    unsigned int lease = system->transaction.digest;
    unsigned int index = 0U;

    while (index < MESSAGE_LENGTH)
    {
        lease = mix(lease, system->transaction.staged[index] + index);
        ++index;
    }
    lease = mix(lease, system->proof.challenge);
    return lease;
}

/// Validation stages one quorum-approved byte at a time because bulk trust
/// would make fault location and audit attribution needlessly ambiguous.
static void validate_service(EnterpriseSystem *system, const Event *event)
{
    unsigned int value = 0U;

    save_checkpoint(system);
    if (event->position != system->transaction.cursor ||
        !consensus_decode(system, event->position, &value))
    {
        rollback_and_reject(system);
        return;
    }

    system->transaction.staged[event->position] = value;
    system->transaction.digest =
        extend_digest(system->transaction.digest, event->position, value);
    system->transaction.cursor += 1U;
    append_audit(system, event);

    if (system->transaction.cursor == MESSAGE_LENGTH)
    {
        system->transaction.phase = system->transaction.digest == MESSAGE_DIGEST
                                        ? TRANSACTION_ATTEST
                                        : TRANSACTION_REJECTED;
    }
}

/// Commit revalidates consensus and lease immediately before each irreversible
/// byte because a proof is useful only while its inputs remain unchanged.
static void commit_service(EnterpriseSystem *system, const Event *event)
{
    unsigned int value = 0U;

    if (event->position != system->transaction.cursor ||
        !consensus_decode(system, event->position, &value) ||
        value != system->transaction.staged[event->position] ||
        system->attested == 0U ||
        system->transaction.dispatch_lease != derive_dispatch_lease(system))
    {
        system->transaction.phase = TRANSACTION_REJECTED;
        return;
    }

    __malbolge_output_byte(value);
    system->transaction.cursor += 1U;
    append_audit(system, event);

    if (system->transaction.cursor == MESSAGE_LENGTH)
    {
        system->transaction.phase = TRANSACTION_FINISHED;
    }
}

/// One dispatcher owns service selection so an event kind cannot accidentally
/// call a more privileged path through an unrelated function pointer.
static void dispatch_one(EnterpriseSystem *system)
{
    Event event;

    if (!dequeue(&system->bus, &event))
    {
        system->transaction.phase = TRANSACTION_REJECTED;
        return;
    }

    system->telemetry.dispatched_events += 1U;
    if (event.kind == EVENT_VALIDATE_SYMBOL)
    {
        validate_service(system, &event);
    }
    else if (event.kind == EVENT_COMMIT_SYMBOL)
    {
        commit_service(system, &event);
    }
    else
    {
        system->transaction.phase = TRANSACTION_REJECTED;
    }
}

/// Event construction centralizes trace derivation so every service sees the
/// same causal identity without reading mutable telemetry counters.
static Event make_event(const EnterpriseSystem *system, EventKind kind)
{
    Event event;

    event.kind = kind;
    event.position = system->transaction.cursor;
    event.trace_id = system->trace_id;
    event.span_id =
        mix(system->trace_id, event.position + (unsigned int)kind * 257U);
    return event;
}

/// Instruction guards provide cheap control-flow integrity for the inner VM;
/// they diagnose corruption rather than claim resistance to active code
/// rewriting.
static int fetch_opcode(const VirtualMachine *machine, VirtualOpcode *opcode)
{
    unsigned int guard;
    unsigned int raw_opcode;
    unsigned int word;

    if (machine->program_counter >= INSTRUCTION_COUNT)
    {
        return 0;
    }

    word = instruction_memory[machine->program_counter] & VM_WORD_MASK;
    raw_opcode = word & 255U;
    guard = word >> 8U;
    if (guard !=
        (raw_opcode * 73U + machine->program_counter * 19U + 7U) % 65536U)
    {
        return 0;
    }
    *opcode = (VirtualOpcode)raw_opcode;
    return 1;
}

/// The VM step is intentionally small because virtualization should concentrate
/// authority, not bury it beneath a second accidental operating system.
static void execute_vm_step(EnterpriseSystem *system)
{
    VirtualOpcode opcode;

    if (!fetch_opcode(&system->machine, &opcode))
    {
        system->machine.faulted = 1U;
        return;
    }

    if (opcode == VM_SCHEDULE_VALIDATE)
    {
        if (system->transaction.phase != TRANSACTION_VALIDATE ||
            !enqueue(&system->bus, make_event(system, EVENT_VALIDATE_SYMBOL)))
        {
            system->machine.faulted = 1U;
            return;
        }
        system->machine.program_counter = 1U;
    }
    else if (opcode == VM_DISPATCH_EVENT)
    {
        dispatch_one(system);
        if (system->transaction.phase == TRANSACTION_REJECTED)
        {
            system->machine.faulted = 1U;
        }
        else if (system->transaction.phase == TRANSACTION_ATTEST)
        {
            system->machine.program_counter = 2U;
        }
        else if (system->transaction.phase == TRANSACTION_FINISHED)
        {
            system->machine.program_counter = 5U;
        }
        else if (system->transaction.phase == TRANSACTION_VALIDATE)
        {
            system->machine.program_counter = 0U;
        }
        else
        {
            system->machine.program_counter = 3U;
        }
    }
    else if (opcode == VM_BUILD_ATTESTATION)
    {
        build_lattice_proof(system->transaction.digest, &system->proof);
        system->telemetry.lattice_checks += 1U;
        if (!verify_lattice_proof(system->transaction.digest, &system->proof))
        {
            system->machine.faulted = 1U;
            return;
        }
        system->attested = 1U;
        system->transaction.dispatch_lease = derive_dispatch_lease(system);
        system->transaction.cursor = 0U;
        system->transaction.phase = TRANSACTION_COMMIT;
        system->machine.program_counter = 3U;
    }
    else if (opcode == VM_SCHEDULE_COMMIT)
    {
        if (system->transaction.phase != TRANSACTION_COMMIT ||
            !enqueue(&system->bus, make_event(system, EVENT_COMMIT_SYMBOL)))
        {
            system->machine.faulted = 1U;
            return;
        }
        system->machine.program_counter = 4U;
    }
    else if (opcode == VM_HALT)
    {
        system->machine.halted = 1U;
    }
    else
    {
        system->machine.faulted = 1U;
    }
}

/// Initialization uses an explicit routine so security-relevant starting values
/// remain reviewable even though zero initialization would produce most of
/// them.
static void initialize(EnterpriseSystem *system)
{
    system->trace_id = 271828U;
    system->transaction.phase = TRANSACTION_VALIDATE;
    system->machine.program_counter = 0U;
    save_checkpoint(system);
}

/// Static storage avoids compiler-synthesized `memset`, keeping the guest
/// object independent from libc while preserving C's guaranteed zero
/// initialization.
static EnterpriseSystem enterprise_system;

/// Main grants the inner machine a finite budget because a fail-closed system
/// must distinguish progress from an accidentally valid infinite control-flow
/// loop.
int main(void)
{
    initialize(&enterprise_system);
    while (enterprise_system.machine.halted == 0U &&
           enterprise_system.machine.faulted == 0U &&
           enterprise_system.machine.steps < VM_STEP_BUDGET)
    {
        execute_vm_step(&enterprise_system);
        enterprise_system.machine.steps += 1U;
    }

    return enterprise_system.machine.halted != 0U &&
                   enterprise_system.machine.faulted == 0U &&
                   enterprise_system.transaction.phase == TRANSACTION_FINISHED
               ? STATUS_SUCCESS
               : STATUS_FAILURE;
}
