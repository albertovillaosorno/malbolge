// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - Apache-2.0
// Confidential:
//   - false
// License-File:
//   - LICENSE
//
// Boundary-Contract:
// - Owns:
//   - Source-authenticated straight-line C input-to-output lowering.
// - Must-Not:
//   - Fold runtime input, claim EOF behavior or accept hidden C effects.
// - Allows:
//   - Inputs: exact pinned Clang call ancestry and source locations.
//   - Outputs: validated typed SSA byte input/output effect pairs.
//   - Side effects: none.
// - Split-When:
//   - General source-C guest runtime I/O replaces this bounded grammar.
// - Merge-When:
//   - Source control-flow lowering proves the same call composition.
// - Summary:
//   - Retains live successful guest input instead of host-time projection.
// - Description:
//   - Authenticates pinned Clang and C byte-input/output expressions.
// - Usage:
//   - Invoked by the normalized JSON-to-typed projection gate.
// - Defaults:
//   - Rejects unrecognized source effects and stale C byte values.

//! Closed dynamic-byte input provenance from normalized source C to typed IR.

#[cfg(test)]
#[path = "../../../../tests/compiler/discarded_getchar.rs"]
mod discarded_getchar_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/guarded_byte_output.rs"]
mod guarded_byte_output_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/nested_guarded_byte_output.rs"]
mod nested_guarded_byte_output_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/unbraced_guarded_byte_output.rs"]
mod unbraced_guarded_byte_output_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/else_if_guarded_byte_output.rs"]
mod else_if_guarded_byte_output_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/multiple_guarded_byte_output.rs"]
mod multiple_guarded_byte_output_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/narrowed_byte_output.rs"]
mod narrowed_byte_output_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/switch_guarded_byte_output.rs"]
mod switch_guarded_byte_output_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/unsigned_input_loop.rs"]
mod unsigned_input_loop_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/lazy_byte_predicate.rs"]
mod lazy_byte_predicate_tests;

#[cfg(test)]
#[path = "../../../../tests/compiler/induction_lazy_predicate.rs"]
mod induction_lazy_predicate_tests;

use std::collections::{HashMap, HashSet};

use super::typed::{
    BasicBlock, BasicBlockSpec, FrontendArtifact, FrontendArtifactSpec,
    FrontendFallthroughVoidFunctionSpec, FrontendReturnVoidFunction, Function,
    FunctionSpec, Instruction, LocatedInstruction, Module, ModuleSpec, TypeDef,
    TypeEntry, TypeId, ValueId,
};
use super::{
    Artifact, FrontendGuestMode, FrontendJsonError, Node, canonical_bytes,
    canonical_module, lower_frontend_artifact, source_digest, span, typed_span,
};

const MAX_ECHO_CALLS: usize = 128;
const CALL_NODE_COUNT: usize = 6;
const MAX_SOURCE_OUTPUTS: usize = 256;
const MAX_BYTE_IDENTITY_DEPTH: usize = 12;
const MAX_BYTE_IDENTITY_LENGTH: usize = 160;
const MAX_NESTED_LOCAL_DEPTH: usize = 16;
const MAX_STATIC_IF_DEPTH: usize = 4;
const MAX_STATIC_FOR_DEPTH: usize = 3;
const MAX_STATIC_PREDICATE_DEPTH: usize = 8;
const MAX_STATIC_PREDICATE_NODES: usize = 31;

/// The exact source-local input initializer, with no intervening effects.
#[derive(Clone)]
struct LocalDeclaration<'node> {
    declaration_end: u32,
    input: &'node Node,
    line: u32,
    name: &'node str,
    variable_reference: String,
}

// A comma operand selects the latest live input or consumes a fresh one.
// Source extent differs from the input when a local value is read without I/O.
struct CommaEffect<'node> {
    input: &'node Node,
    extent: &'node Node,
    // Outer-to-inner preorder, emitted in inner-to-outer C evaluation order.
    outputs: Vec<&'node Node>,
    // Only source-proven local reads may reuse the resident guest SSA byte.
    reads_local: bool,
    // A fresh input assigned inside a comma keeps this C local resident.
    assigns_local: bool,
}

type OutputCallProof<'node> = (usize, Vec<&'node Node>);
type PureTernaryArmProof = (usize, String, String);
// Exact signed C values for every successful resident guest byte, 0..=255.
// Keeping values rather than truthiness is essential for integer XOR/AND:
// distinct nonzero masks may cancel or have no bits in common.
// None marks undefined arithmetic for one candidate byte; lazy C operators
// may discard it, but an observed None always refuses final admission.
// Heap storage keeps recursive source proofs below the bounded C compiler's
// stack-frame budget, even when nested conditional subtrees overlap.
type BytePredicateValues = Box<[Option<i32>; 256]>;
type TotalByteGuardProof = (usize, String, BytePredicateValues);
type InductionArmProof = (usize, Option<bool>, u32);

// The nested successful-byte return is not recomputed: every write uses the
// same already-read guest SSA identity, in innermost-first C evaluation order.
fn emit_comma_outputs(
    effect: &CommaEffect<'_>,
    value: ValueId,
    instructions: &mut Vec<LocatedInstruction>,
) {
    for write in effect.outputs.iter().rev() {
        instructions.push(LocatedInstruction::new(
            Instruction::ByteOutput { value },
            typed_span(&write.span),
        ));
    }
}

// A comma operand proven to read the current local is a reuse of its live
// guest SSA byte, not a second input. Once any operand reads new stdin, that
// old local can no longer be materialized by this accumulator-only backend.
fn emit_comma_effects(
    effects: &[CommaEffect<'_>],
    local: Option<&(LocalDeclaration<'_>, ValueId)>,
    inputs: &mut usize,
    outputs: &mut usize,
    instructions: &mut Vec<LocatedInstruction>,
) -> Option<(ValueId, bool, bool)> {
    let mut selected = None;
    let mut resident = local.map(|(_, value)| *value);
    let mut read_new_input = false;
    for effect in effects {
        let value = if effect.reads_local {
            resident?
        } else {
            if *inputs == MAX_ECHO_CALLS {
                return None;
            }
            let value = ValueId::new(u32::try_from(*inputs).ok()?);
            instructions.push(LocatedInstruction::new(
                Instruction::ByteInput {
                    result: value,
                    type_id: TypeId::new(0),
                },
                typed_span(&effect.input.span),
            ));
            *inputs = inputs.checked_add(1)?;
            read_new_input = true;
            // A fresh read clobbers the accumulator's old byte. Only an
            // authenticated assignment makes that new byte a C local value.
            resident = effect.assigns_local.then_some(value);
            value
        };
        *outputs = outputs.checked_add(effect.outputs.len())?;
        if *outputs > MAX_SOURCE_OUTPUTS {
            return None;
        }
        emit_comma_outputs(effect, value, instructions);
        selected = Some(value);
    }
    Some((selected?, read_new_input, resident.is_some()))
}

const fn metadata_except_integer_constant_empty(node: &Node) -> bool {
    node.name.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
        && node.literal.is_none()
}

const fn metadata_empty(node: &Node) -> bool {
    metadata_except_integer_constant_empty(node)
        && node.constant_integer.is_none()
}

// Exact spelling boundaries of `putchar(getchar())` as Clang 22.1.8
// normalizes it, with no wrappers, alternate evaluation or hidden calls.
#[expect(
    clippy::too_many_arguments,
    reason = "a source word has four independent checked Clang coordinates"
)]
const fn source_word(
    node: &Node,
    start: u32,
    end: u32,
    line: u32,
    column: u32,
) -> bool {
    node.span.begin.byte == start
        && node.span.end.byte == end
        && node.span.begin.line == line
        && node.span.end.line == line
        && node.span.begin.column == column
        && node.span.end.column
            == column.saturating_add(end.saturating_sub(start))
}

#[expect(
    clippy::too_many_lines,
    reason = "full six-node Clang call ancestry is checked as one closed unit"
)]
fn prove_call<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    parent: u32,
) -> Option<(&'node Node, &'node Node)> {
    let [
        output,
        output_cast,
        output_callee,
        input,
        input_cast,
        input_callee,
    ] = nodes
    else {
        return None;
    };
    let base = output.id;
    let start = output.span.begin.byte;
    let line = output.span.begin.line;
    let column = output.span.begin.column;
    let well_formed = start > previous
        && start > body.span.begin.byte
        && start.checked_add(18)? < body.span.end.byte
        && line > 0
        && column > 0
        && output.parent == parent
        && output.kind == "call-expression"
        && output.type_name.as_deref() == Some("i32")
        && output.reference.as_deref() == Some("external:putchar")
        && output.operation.is_none()
        && source_word(output, start, start.checked_add(18)?, line, column)
        && output_cast.id == base.checked_add(1)?
        && output_cast.parent == base
        && output_cast.kind == "cast-expression"
        && output_cast.type_name.as_deref() == Some("ptr(fn(i32)->i32)")
        && output_cast.operation.as_deref() == Some("function-to-pointer")
        && output_cast.reference.is_none()
        && source_word(output_cast, start, start.checked_add(7)?, line, column)
        && output_callee.id == base.checked_add(2)?
        && output_callee.parent == output_cast.id
        && output_callee.kind == "declaration-reference-expression"
        && output_callee.type_name.as_deref() == Some("fn(i32)->i32")
        && output_callee.reference.as_deref() == Some("external:putchar")
        && output_callee.operation.is_none()
        && source_word(
            output_callee,
            start,
            start.checked_add(7)?,
            line,
            column,
        )
        && input.id == base.checked_add(3)?
        && input.parent == base
        && input.kind == "call-expression"
        && input.type_name.as_deref() == Some("i32")
        && input.reference.as_deref() == Some("external:getchar")
        && input.operation.is_none()
        && source_word(
            input,
            start.checked_add(8)?,
            start.checked_add(17)?,
            line,
            column.checked_add(8)?,
        )
        && input_cast.id == base.checked_add(4)?
        && input_cast.parent == input.id
        && input_cast.kind == "cast-expression"
        && input_cast.type_name.as_deref() == Some("ptr(fn()->i32)")
        && input_cast.operation.as_deref() == Some("function-to-pointer")
        && input_cast.reference.is_none()
        && source_word(
            input_cast,
            start.checked_add(8)?,
            start.checked_add(15)?,
            line,
            column.checked_add(8)?,
        )
        && input_callee.id == base.checked_add(5)?
        && input_callee.parent == input_cast.id
        && input_callee.kind == "declaration-reference-expression"
        && input_callee.type_name.as_deref() == Some("fn()->i32")
        && input_callee.reference.as_deref() == Some("external:getchar")
        && input_callee.operation.is_none()
        && source_word(
            input_callee,
            start.checked_add(8)?,
            start.checked_add(15)?,
            line,
            column.checked_add(8)?,
        )
        && [
            output,
            output_cast,
            output_callee,
            input,
            input_cast,
            input_callee,
        ]
        .iter()
        .all(|node| metadata_empty(node));
    well_formed.then_some((input, output))
}

// A whole-function direct putchar(getchar()) has an observable EOF output.
// The successful-u8 bridge would emit the profile EOF accumulator's low byte
// instead of C's unsigned-char conversion of -1 (0xff). This exact standalone
// source cannot be published until a signed-EOF output projection is real.
// Test *before* trying other frontend projection grammars: otherwise a
// fallback could accidentally re-admit this unsupported operation.
// A straight-line output of a signed getchar result is unsafe at EOF even
// after pure arithmetic, parentheses, discarded reads or a trailing return.
// This gate bounds discarded reads to 128 and never treats exhaustion as a
// byte. Reject a direct top-level putchar whose argument contains a signed
// getchar call, regardless of pure parentheses/arithmetic around that input.
// The successful-byte backend only knows the 0..255 input domain; it cannot
// reproduce putchar's defined EOF conversion from C's -1 result. Find the
// complete preorder subtree by parent identity, without assuming its width
// or its expression spelling. This only *rejects* a source shape; it never
// authorizes lowering from unauthenticated nodes.
fn unchecked_direct_signed_output_width(
    nodes: &[Node],
    body: &Node,
    previous: u32,
) -> Option<usize> {
    let output = nodes.first()?;
    if output.kind != "call-expression"
        || output.reference.as_deref() != Some("external:putchar")
        || output.parent != body.id
        || output.span.begin.byte <= previous
    {
        return None;
    }
    let mut descendants = HashSet::from([output.id]);
    let mut width = 1;
    let mut signed_input = false;
    for child in nodes.iter().skip(1) {
        if !descendants.contains(&child.parent) {
            break;
        }
        if child.span.begin.byte < output.span.begin.byte
            || child.span.end.byte > output.span.end.byte
        {
            return None;
        }
        signed_input |= child.kind == "call-expression"
            && child.reference.as_deref() == Some("external:getchar");
        if !descendants.insert(child.id) {
            return None;
        }
        width += 1;
    }
    signed_input.then_some(width)
}

pub(super) fn is_unchecked_direct_eof_echo(bytes: &[u8]) -> bool {
    let Ok(artifact) = serde_json::from_slice::<Artifact>(bytes) else {
        return false;
    };
    let [function, body, nodes @ ..] = artifact.nodes.as_slice() else {
        return false;
    };
    if function.kind != "function-declaration"
        || body.kind != "compound-statement"
        || body.parent != function.id
    {
        return false;
    }
    let mut remaining = nodes;
    let mut previous = body.span.begin.byte;
    let mut discarded_reads = 0;
    let mut signed_outputs = 0;
    // Every independent signed getchar-to-putchar output observes C's EOF
    // conversion. A finite series of such calls is no safer than one call:
    // after input exhaustion every additional output must be 0xff, not the
    // guest profile EOF word's low byte. Discarded reads may occur anywhere.
    while !remaining.is_empty() {
        if signed_outputs < MAX_ECHO_CALLS
            && let Some(width) =
                unchecked_direct_signed_output_width(remaining, body, previous)
        {
            previous = remaining[0].span.end.byte;
            remaining = &remaining[width..];
            signed_outputs += 1;
            continue;
        }
        // A trailing `return;` changes neither the signed getchar result
        // nor putchar's EOF conversion. Without this explicit refusal the
        // successful-byte backend can publish 0x6a instead of C's 0xff.
        // Only reject the proven direct-echo prefix; a return by itself is
        // not evidence of an observable EOF output.
        if signed_outputs > 0
            && let [last] = remaining
            && last.kind == "return-statement"
            && last.parent == body.id
            && last.span.begin.byte > previous
        {
            return true;
        }
        if discarded_reads == MAX_ECHO_CALLS {
            return false;
        }
        let Some((head, tail)) = remaining.split_first_chunk::<3>() else {
            return false;
        };
        let input = &head[0];
        if prove_input_call(head, body, previous, (input.id, body.id)).is_none()
        {
            return false;
        }
        previous = input.span.end.byte;
        remaining = tail;
        discarded_reads += 1;
    }
    signed_outputs > 0
}

// Unrolling a bounded for loop cannot remove the observable EOF result of
// putchar(getchar()). Even though every successful read is a guest byte,
// exhausted C23 stdin makes getchar return -1 and putchar write 0xff.
// Reject a signed input nested inside an output directly in a for-loop body
// before the successful-u8 projection can publish a false executable.
// This is a conservative refusal only: it cannot authorize a C lowering.
pub(super) fn is_unchecked_direct_loop_eof_echo(bytes: &[u8]) -> bool {
    let Ok(artifact) = serde_json::from_slice::<Artifact>(bytes) else {
        return false;
    };
    let nodes = &artifact.nodes;
    let by_id: HashMap<u32, &Node> =
        nodes.iter().map(|node| (node.id, node)).collect();
    nodes.iter().any(|output| {
        if output.kind != "call-expression"
            || output.reference.as_deref() != Some("external:putchar")
        {
            return false;
        }
        // An if/switch or a nested brace does not guard a freshly read
        // getchar inside putchar: the input has not occurred until output
        // evaluation. Walk the original Clang parent identities to include
        // braced, unbraced and conditionally selected loop outputs.
        let mut parent = output.parent;
        let enclosed_by_for = (0..MAX_NESTED_LOCAL_DEPTH).any(|_| {
            let Some(ancestor) = by_id.get(&parent) else {
                return false;
            };
            parent = ancestor.parent;
            ancestor.kind == "for-statement"
        });
        if !enclosed_by_for {
            return false;
        }
        nodes.iter().any(|input| {
            if input.kind != "call-expression"
                || input.reference.as_deref() != Some("external:getchar")
                || input.type_name.as_deref() != Some("i32")
                || input.span.begin.byte < output.span.begin.byte
                || input.span.end.byte > output.span.end.byte
            {
                return false;
            }
            let mut parent = input.parent;
            for _ in 0..MAX_BYTE_IDENTITY_DEPTH {
                if parent == output.id {
                    return true;
                }
                let Some(ancestor) = by_id.get(&parent) else {
                    break;
                };
                if ancestor.span.begin.byte < output.span.begin.byte
                    || ancestor.span.end.byte > output.span.end.byte
                {
                    break;
                }
                parent = ancestor.parent;
            }
            false
        })
    })
}

// No induction step or bounded static unrolling proves signed getchar EOF.
// A statically unrolled loop does not prove its signed getchar values are
// successful bytes. Even a single counter-selected output of an unguarded
// signed local writes 0xff at EOF in C, but the current
// byte-only guest writes the profile's low EOF residue. This is a refusal
// proof, never permission to lower an unauthenticated source. Keep parent
// identities explicit so forged descendant calls cannot imply C behavior.
pub(super) fn is_unchecked_counter_loop_signed_eof_output(
    bytes: &[u8],
) -> bool {
    let Ok(artifact) = serde_json::from_slice::<Artifact>(bytes) else {
        return false;
    };
    let nodes = &artifact.nodes;
    let by_id: HashMap<u32, &Node> =
        nodes.iter().map(|node| (node.id, node)).collect();
    let mut signed_inputs = HashSet::new();
    for input in nodes.iter().filter(|node| {
        node.kind == "call-expression"
            && node.reference.as_deref() == Some("external:getchar")
            && node.type_name.as_deref() == Some("i32")
    }) {
        let Some(local) = by_id.get(&input.parent) else {
            continue;
        };
        let Some(declaration) = by_id.get(&local.parent) else {
            continue;
        };
        let Some(loop_body) = by_id.get(&declaration.parent) else {
            continue;
        };
        let Some(owner) = by_id.get(&loop_body.parent) else {
            continue;
        };
        if local.kind == "variable-declaration"
            && local.type_name.as_deref() == Some("i32")
            && declaration.kind == "declaration-statement"
            && loop_body.kind == "compound-statement"
            && (owner.kind == "for-statement"
                || owner.kind == "function-declaration")
            && let Some(reference) = local.reference.as_deref()
        {
            let _ = signed_inputs.insert((loop_body.id, reference));
        }
    }
    for read in nodes.iter().filter(|node| {
        node.kind == "declaration-reference-expression"
            && node.type_name.as_deref() == Some("i32")
    }) {
        let Some(reference) = read.reference.as_deref() else {
            continue;
        };
        // A signed C local read used by any descendant putchar is unsafe
        // at EOF unless the output expression has been independently proved
        // on the signed -1 domain. Branches, nested calls, casts, and modular
        // arithmetic cannot turn a successful-byte proof into that evidence.
        // Follow exact Clang parents and spans through the output to the
        // specific loop body that owns this local declaration. This proof
        // refuses a publication; it never authorizes a lowering.
        let mut ancestor_id = read.parent;
        let mut output = None;
        for _ in 0..MAX_NESTED_LOCAL_DEPTH {
            let Some(ancestor) = by_id.get(&ancestor_id) else {
                break;
            };
            if ancestor.kind == "call-expression"
                && ancestor.reference.as_deref() == Some("external:putchar")
                && ancestor.span.begin.byte <= read.span.begin.byte
                && read.span.end.byte <= ancestor.span.end.byte
            {
                output = Some(*ancestor);
                break;
            }
            ancestor_id = ancestor.parent;
        }
        if let Some(output) = output {
            let mut ancestor_id = output.parent;
            for _ in 0..MAX_NESTED_LOCAL_DEPTH {
                let Some(ancestor) = by_id.get(&ancestor_id) else {
                    break;
                };
                if ancestor.kind == "compound-statement"
                    && signed_inputs.contains(&(ancestor.id, reference))
                {
                    return true;
                }
                ancestor_id = ancestor.parent;
            }
        }
    }
    false
}

// A straight-line signed int local is just as EOF-sensitive as a direct
// putchar(getchar()). The byte-only projection can preserve an alias on the
// successful-byte domain, but it cannot convert a returned -1 to C's 0xff.
// Require pinned declaration/output ancestry; a copied alias is admitted
// only with exact original source bytes. This is a rejection proof, never a
// reason to accept a source or replace a genuine EOF guard.
pub(super) fn is_unchecked_local_eof_echo(
    bytes: &[u8],
    source: Option<&[u8]>,
) -> bool {
    let Ok(artifact) = serde_json::from_slice::<Artifact>(bytes) else {
        return false;
    };
    let [function, body, nodes @ ..] = artifact.nodes.as_slice() else {
        return false;
    };
    if function.kind != "function-declaration"
        || body.kind != "compound-statement"
        || body.parent != function.id
    {
        return false;
    }
    // The signed local may follow source-ordered discarded getchar calls.
    // Those real guest reads do not make the later signed EOF observable
    // through the successful-u8 projection. Authenticate each complete
    // three-node Clang call before locating the declaration.
    let mut remaining = nodes;
    let mut previous = body.span.begin.byte;
    let mut discarded = 0usize;
    while discarded < MAX_ECHO_CALLS {
        let Some((head, tail)) = remaining.split_first_chunk::<3>() else {
            break;
        };
        let Some(call) =
            prove_input_call(head, body, previous, (head[0].id, body.id))
        else {
            break;
        };
        previous = call.span.end.byte;
        remaining = tail;
        discarded += 1;
    }
    let Some(mut local) = remaining.get(..5).and_then(|declaration| {
        prove_local_declaration(declaration, body, previous, body.id)
    }) else {
        return false;
    };
    let mut expected_id = remaining[4].id.saturating_add(1);
    remaining = &remaining[5..];
    previous = local.declaration_end;
    let mut outputs = 0usize;
    while let Some(first) = remaining.first() {
        // A fresh, unguarded putchar(getchar()) after local reads still
        // observes signed EOF. The independent direct-output ancestry
        // proof must reject it before the successful-byte projection.
        if unchecked_direct_signed_output_width(remaining, body, previous)
            .is_some()
        {
            return true;
        }
        // A later statement cannot undo an already emitted wrong EOF byte.
        if outputs > 0 {
            return true;
        }
        if outputs < MAX_ECHO_CALLS
            && let Some((width, calls)) = prove_local_output_chain(
                remaining,
                body,
                &local,
                expected_id,
                previous,
                body.id,
                source,
            )
            && outputs
                .checked_add(calls.len())
                .is_some_and(|total| total <= MAX_ECHO_CALLS)
        {
            outputs += calls.len();
            previous = calls[0].span.end.byte;
            remaining = &remaining[width..];
            let Ok(width_id) = u32::try_from(width) else {
                return false;
            };
            expected_id = expected_id.saturating_add(width_id);
            continue;
        }
        // Reassigning the signed local from another getchar does not make
        // its next observed value an unsigned byte at EOF. Each reassignment
        // must have exact Clang ancestry and source spelling; it can occur
        // only before any output in this bounded refusal proof.
        if outputs == 0
            && let Some(witness) = source
            && remaining
                .get(..5)
                .and_then(|assignment| {
                    prove_local_input_reassignment(
                        assignment,
                        (body, previous, body.id),
                        &local,
                        witness,
                        b';',
                    )
                })
                .is_some()
        {
            previous = remaining[0].span.end.byte;
            remaining = &remaining[5..];
            expected_id = expected_id.saturating_add(5);
            continue;
        }
        if outputs == 0
            && let Some(witness) = source
            && let Some(alias) = remaining.get(..4).and_then(|declaration| {
                prove_local_alias(
                    declaration,
                    (body, previous, body.id),
                    &local,
                    witness,
                )
            })
        {
            previous = alias.declaration_end;
            local = alias;
            remaining = &remaining[4..];
            expected_id = expected_id.saturating_add(4);
            continue;
        }
        if outputs > 0
            && remaining.len() == 1
            && first.kind == "return-statement"
            && first.parent == body.id
            && first.id == expected_id
            && first.span.begin.byte > previous
        {
            return true;
        }
        return false;
    }
    outputs > 0
}

// A source-proven getchar() is a guest effect even when its result
// is discarded. Both standalone and comma-child calls use the same exact
// three-node proof to preserve input ordering and prevent hidden effects.
fn prove_input_call<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    identity: (u32, u32),
) -> Option<&'node Node> {
    let [call, cast, callee] = nodes else {
        return None;
    };
    let start = call.span.begin.byte;
    let line = call.span.begin.line;
    let column = call.span.begin.column;
    let end = start.checked_add(9)?;
    let source_ok = start > previous
        && start > body.span.begin.byte
        && end < body.span.end.byte
        && line > 0
        && column > 0
        && call.id == identity.0
        && call.parent == identity.1
        && call.kind == "call-expression"
        && call.type_name.as_deref() == Some("i32")
        && call.reference.as_deref() == Some("external:getchar")
        && call.operation.is_none()
        && metadata_empty(call)
        && source_word(call, start, end, line, column)
        && cast.id == call.id.checked_add(1)?
        && cast.parent == call.id
        && cast.kind == "cast-expression"
        && cast.type_name.as_deref() == Some("ptr(fn()->i32)")
        && cast.operation.as_deref() == Some("function-to-pointer")
        && cast.reference.is_none()
        && metadata_empty(cast)
        && source_word(cast, start, start.checked_add(7)?, line, column)
        && callee.id == cast.id.checked_add(1)?
        && callee.parent == cast.id
        && callee.kind == "declaration-reference-expression"
        && callee.type_name.as_deref() == Some("fn()->i32")
        && callee.reference.as_deref() == Some("external:getchar")
        && callee.operation.is_none()
        && metadata_empty(callee)
        && source_word(callee, start, start.checked_add(7)?, line, column);
    source_ok.then_some(call)
}

// The value of an entire comma expression is its rightmost successful
// input or putchar return. Every earlier operand is evaluated in the guest,
// and the enclosing putchar writes the last live byte one more time.
#[expect(
    clippy::too_many_lines,
    reason = "authenticate the complete comma-argument source and ancestry"
)]
fn prove_comma_output_effects<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    parent: u32,
    local: Option<&LocalDeclaration<'node>>,
    source: Option<&[u8]>,
) -> Option<(usize, Vec<CommaEffect<'node>>, &'node Node)> {
    let [output, cast, callee, paren, comma, ..] = nodes else {
        return None;
    };
    let start = output.span.begin.byte;
    let line = output.span.begin.line;
    let column = output.span.begin.column;
    if start <= previous
        || start <= body.span.begin.byte
        || line == 0
        || column == 0
        || output.id != expected_id
        || output.parent != parent
        || output.kind != "call-expression"
        || output.type_name.as_deref() != Some("i32")
        || output.reference.as_deref() != Some("external:putchar")
        || output.operation.is_some()
        || !metadata_empty(output)
        || cast.id != output.id.checked_add(1)?
        || cast.parent != output.id
        || cast.kind != "cast-expression"
        || cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
        || cast.operation.as_deref() != Some("function-to-pointer")
        || cast.reference.is_some()
        || !metadata_empty(cast)
        || callee.id != cast.id.checked_add(1)?
        || callee.parent != cast.id
        || callee.kind != "declaration-reference-expression"
        || callee.type_name.as_deref() != Some("fn(i32)->i32")
        || callee.reference.as_deref() != Some("external:putchar")
        || callee.operation.is_some()
        || !metadata_empty(callee)
        || paren.id != callee.id.checked_add(1)?
        || paren.parent != output.id
        || paren.kind != "parenthesized-expression"
        || paren.type_name.as_deref() != Some("i32")
        || paren.reference.is_some()
        || paren.operation.is_some()
        || !metadata_empty(paren)
        || comma.id != paren.id.checked_add(1)?
    {
        return None;
    }
    let (comma_width, effects, last_end) = prove_discarded_comma_effects(
        nodes.get(4..)?,
        body,
        previous,
        comma.id,
        paren.id,
        local,
        source,
    )?;
    let end = last_end.checked_add(2)?;
    let width = 4usize.checked_add(comma_width)?;
    if let Some(witness) = source {
        let begin = usize::try_from(start).ok()?;
        let close = usize::try_from(end).ok()?;
        if witness.get(begin..begin.checked_add(9)?) != Some(b"putchar((")
            || witness.get(close.checked_sub(2)?..close) != Some(b"))")
        {
            return None;
        }
    }
    if end >= body.span.end.byte
        || !source_word(output, start, end, line, column)
        || !source_word(cast, start, start.checked_add(7)?, line, column)
        || !source_word(callee, start, start.checked_add(7)?, line, column)
        || !source_word(
            paren,
            start.checked_add(8)?,
            last_end.checked_add(1)?,
            line,
            column.checked_add(8)?,
        )
        || comma.span.begin.byte != start.checked_add(9)?
    {
        return None;
    }
    Some((width, effects, output))
}

// C evaluates the left operand of this comma before reading the right.
// A successful `NAME = getchar()` rebinds the same source local that the
// outer putchar then reads. The target can replay this with one guest input
// and one output without ever recovering the overwritten prior byte.
#[expect(
    clippy::too_many_lines,
    reason = "the full comma assignment and output ancestry is one source proof"
)]
fn prove_comma_assigned_output<'node>(
    nodes: &'node [Node],
    scope: (&Node, u32, u32),
    local: &LocalDeclaration<'_>,
    source: &[u8],
) -> Option<(&'node Node, &'node Node)> {
    let (body, previous, parent) = scope;
    let [
        output,
        output_cast,
        output_callee,
        paren,
        comma,
        assignment,
        _,
        _,
        _,
        input_callee,
        local_cast,
        _,
        ..,
    ] = nodes
    else {
        return None;
    };
    let start = output.span.begin.byte;
    let line = output.span.begin.line;
    let column = output.span.begin.column;
    let name_width = u32::try_from(local.name.len()).ok()?;
    let assign_start = start.checked_add(9)?;
    let assign_end = assign_start.checked_add(name_width)?.checked_add(12)?;
    let read_start = assign_end.checked_add(2)?;
    let read_end = read_start.checked_add(name_width)?;
    let end = read_end.checked_add(2)?;
    let spelling =
        format!("putchar(({} = getchar(), {}));", local.name, local.name);
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
        || start <= previous
        || start <= local.declaration_end
        || end >= body.span.end.byte
        || line <= local.line
        || column == 0
        || output.parent != parent
        || output.kind != "call-expression"
        || output.type_name.as_deref() != Some("i32")
        || output.reference.as_deref() != Some("external:putchar")
        || output.operation.is_some()
        || !metadata_empty(output)
        || !source_word(output, start, end, line, column)
        || output_cast.id != output.id.checked_add(1)?
        || output_cast.parent != output.id
        || output_cast.kind != "cast-expression"
        || output_cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
        || output_cast.operation.as_deref() != Some("function-to-pointer")
        || output_cast.reference.is_some()
        || !metadata_empty(output_cast)
        || !source_word(output_cast, start, start.checked_add(7)?, line, column)
        || output_callee.id != output_cast.id.checked_add(1)?
        || output_callee.parent != output_cast.id
        || output_callee.kind != "declaration-reference-expression"
        || output_callee.type_name.as_deref() != Some("fn(i32)->i32")
        || output_callee.reference.as_deref() != Some("external:putchar")
        || output_callee.operation.is_some()
        || !metadata_empty(output_callee)
        || !source_word(
            output_callee,
            start,
            start.checked_add(7)?,
            line,
            column,
        )
        || paren.id != output_callee.id.checked_add(1)?
        || paren.parent != output.id
        || paren.kind != "parenthesized-expression"
        || paren.type_name.as_deref() != Some("i32")
        || paren.reference.is_some()
        || paren.operation.is_some()
        || !metadata_empty(paren)
        || !source_word(
            paren,
            start.checked_add(8)?,
            end.checked_sub(1)?,
            line,
            column.checked_add(8)?,
        )
        || comma.id != paren.id.checked_add(1)?
        || comma.parent != paren.id
        || comma.kind != "binary-expression"
        || comma.type_name.as_deref() != Some("i32")
        || comma.operation.as_deref() != Some(",")
        || comma.reference.is_some()
        || !metadata_empty(comma)
        || !source_word(
            comma,
            assign_start,
            read_end,
            line,
            column.checked_add(9)?,
        )
        || assignment.id != comma.id.checked_add(1)?
        || input_callee.id != assignment.id.checked_add(4)?
        || local_cast.id != input_callee.id.checked_add(1)?
    {
        return None;
    }
    let read = prove_local_input_reassignment(
        nodes.get(5..10)?,
        (body, previous, comma.id),
        local,
        source,
        b',',
    )?;
    if assignment.span.begin.byte != assign_start
        || assignment.span.end.byte != assign_end
        || prove_comma_local_value(
            nodes.get(10..12)?,
            body,
            local,
            assign_end,
            local_cast.id,
            comma.id,
        )?
        .span
        .end
        .byte
            != read_end
    {
        return None;
    }
    Some((read, output))
}

// Pure local operands have no new guest input or output effect. Both Clang
// nodes must denote the current source-proven local and the same C extent.
fn prove_comma_local_value<'node>(
    nodes: &'node [Node],
    body: &Node,
    local: &LocalDeclaration<'_>,
    previous: u32,
    expected_id: u32,
    parent: u32,
) -> Option<&'node Node> {
    let [cast, reference] = nodes else {
        return None;
    };
    let start = cast.span.begin.byte;
    let end = start.checked_add(u32::try_from(local.name.len()).ok()?)?;
    let line = cast.span.begin.line;
    let column = cast.span.begin.column;
    (start > previous
        && start > local.declaration_end
        && end < body.span.end.byte
        && line > local.line
        && cast.id == expected_id
        && cast.parent == parent
        && cast.kind == "cast-expression"
        && cast.type_name.as_deref() == Some("i32")
        && cast.operation.as_deref() == Some("lvalue-to-rvalue")
        && cast.reference.is_none()
        && metadata_empty(cast)
        && source_word(cast, start, end, line, column)
        && reference.id == cast.id.checked_add(1)?
        && reference.parent == cast.id
        && reference.kind == "declaration-reference-expression"
        && reference.type_name.as_deref() == Some("i32")
        && reference.reference.as_deref()
            == Some(local.variable_reference.as_str())
        && reference.operation.is_none()
        && metadata_empty(reference)
        && source_word(reference, start, end, line, column))
    .then_some(cast)
}

// A left-associative C comma chain executes every operand, including
// discarded putchar(getchar()) results. The bounded grammar checks every
// call, source byte and Clang ancestor before admitting its guest effects.
#[expect(
    clippy::too_many_lines,
    reason = "verify each comma operand and Clang source coordinate"
)]
fn prove_discarded_comma_effects<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    first_parent: u32,
    local: Option<&LocalDeclaration<'node>>,
    source: Option<&[u8]>,
) -> Option<(usize, Vec<CommaEffect<'node>>, u32)> {
    let binary_count = nodes
        .iter()
        .take(16)
        .take_while(|node| {
            node.kind == "binary-expression"
                && node.operation.as_deref() == Some(",")
        })
        .count();
    if binary_count == 0 || binary_count >= 16 {
        return None;
    }
    let operand_count = binary_count.checked_add(1)?;
    let binary_nodes = nodes.get(..binary_count)?;
    let first = binary_nodes.first()?;
    let start = first.span.begin.byte;
    let line = first.span.begin.line;
    let column = first.span.begin.column;
    if start <= previous
        || start <= body.span.begin.byte
        || line == 0
        || column == 0
    {
        return None;
    }
    for (index, node) in binary_nodes.iter().enumerate() {
        let parent = if index == 0 {
            first_parent
        } else {
            binary_nodes.get(index.checked_sub(1)?)?.id
        };
        if node.id != expected_id.checked_add(u32::try_from(index).ok()?)?
            || node.parent != parent
            || node.kind != "binary-expression"
            || node.type_name.as_deref() != Some("i32")
            || node.operation.as_deref() != Some(",")
            || node.reference.is_some()
            || !metadata_empty(node)
        {
            return None;
        }
    }
    let mut effects = Vec::with_capacity(operand_count);
    let mut cursor = binary_count;
    let mut last_end = previous;
    let mut local_is_live = local.is_some();
    for index in 0..operand_count {
        let parent = if index < 2 {
            binary_nodes.last()?.id
        } else {
            binary_nodes.get(binary_count.checked_sub(index)?)?.id
        };
        let expected_leaf_id =
            expected_id.checked_add(u32::try_from(cursor).ok()?)?;
        let leaf = nodes.get(cursor)?;
        let (width, input, outputs, extent, reads_local, assigns_local) =
            if leaf.kind == "binary-expression"
                && leaf.operation.as_deref() == Some("=")
            {
                let current_local = local?;
                let witness = source?;
                // The final comma assignment is followed by the surrounding
                // parenthesis or statement semicolon, not another comma.
                // Authenticate the exact separator and pinned Clang tree.
                let terminator = if index.checked_add(1)? == operand_count {
                    match witness
                        .get(usize::try_from(leaf.span.end.byte).ok()?)?
                    {
                        b')' => b')',
                        b';' => b';',
                        _ => return None,
                    }
                } else {
                    b','
                };
                // A fresh input may bind directly or through successful
                // outputs; a resident output-return is a separate no-read
                // proof.
                let (width, input, outputs, reads_local) = if let Some(read) =
                    prove_local_input_reassignment(
                        nodes.get(cursor..cursor.checked_add(5)?)?,
                        (body, last_end, parent),
                        current_local,
                        witness,
                        terminator,
                    ) {
                    (5, read, Vec::new(), false)
                } else if let Some((width, read, outputs)) =
                    prove_output_return_reassignment(
                        nodes.get(cursor..)?,
                        (body, last_end, parent),
                        current_local,
                        witness,
                        terminator,
                    )
                {
                    (width, read, outputs, false)
                } else {
                    // putchar(LIVE) returns the current guest byte. A stale
                    // C local cannot be recovered by reassigning its output.
                    local_is_live.then_some(())?;
                    let (width, outputs) =
                        prove_resident_output_return_reassignment(
                            nodes.get(cursor..)?,
                            (body, last_end, parent),
                            current_local,
                            (witness, terminator),
                        )?;
                    (width, current_local.input, outputs, true)
                };
                local_is_live = true;
                (width, input, outputs, leaf, reads_local, true)
            } else if leaf.reference.as_deref() == Some("external:putchar") {
                if let Some(current_local) = local
                    && let Some(witness) = source
                    && let Some(slice) =
                        nodes.get(cursor..cursor.checked_add(8)?)
                    && let Some((read, output)) = prove_output_input_assignment(
                        slice,
                        (body, last_end, parent),
                        current_local,
                        witness,
                        if index.checked_add(1)? == operand_count {
                            b')'
                        } else {
                            b','
                        },
                    )
                {
                    // This putchar consumes a fresh byte via assignment,
                    // writes it, and rebinds the C local for later operands.
                    local_is_live = true;
                    (8, read, vec![output], output, false, true)
                } else if local_is_live
                    && let Some(current_local) = local
                    && let Some((width, calls)) = prove_local_output_chain(
                        nodes.get(cursor..)?,
                        body,
                        current_local,
                        expected_leaf_id,
                        last_end,
                        parent,
                        source,
                    )
                {
                    let extent = *calls.first()?;
                    (width, current_local.input, calls, extent, true, false)
                } else {
                    let (width, input, calls) =
                        super::nested_byte_echo::nested_call_in_parent(
                            nodes.get(cursor..)?,
                            body,
                            last_end,
                            expected_leaf_id,
                            parent,
                        )?;
                    local_is_live = false;
                    let extent = *calls.first()?;
                    (width, input, calls, extent, false, false)
                }
            } else if leaf.kind == "cast-expression" {
                let current_local = local.filter(|_| local_is_live)?;
                let extent = prove_comma_local_value(
                    nodes.get(cursor..cursor.checked_add(2)?)?,
                    body,
                    current_local,
                    last_end,
                    expected_leaf_id,
                    parent,
                )?;
                (2, current_local.input, Vec::new(), extent, true, false)
            } else {
                let input = prove_input_call(
                    nodes.get(cursor..cursor.checked_add(3)?)?,
                    body,
                    last_end,
                    (expected_leaf_id, parent),
                )?;
                local_is_live = false;
                (3, input, Vec::new(), input, false, false)
            };
        // A valid Clang comma subtree and SHA-matching bytes alone do not
        // prove the source operator; reject a changed `,` to `+` or `-`.
        if index > 0
            && let Some(witness) = source
        {
            let begin = usize::try_from(last_end).ok()?;
            let end = usize::try_from(extent.span.begin.byte).ok()?;
            if !matches!(witness.get(begin..end), Some(b",") | Some(b", ")) {
                return None;
            }
        }
        if extent.id != expected_leaf_id
            || extent.span.begin.line != line
            || extent.span.end.line != line
            || extent.span.begin.column
                != column
                    .checked_add(extent.span.begin.byte.checked_sub(start)?)?
            || (index > 0
                && !matches!(
                    extent.span.begin.byte.checked_sub(last_end)?,
                    1 | 2
                ))
        {
            return None;
        }
        cursor = cursor.checked_add(width)?;
        last_end = extent.span.end.byte;
        effects.push(CommaEffect {
            input,
            extent,
            outputs,
            reads_local,
            assigns_local,
        });
    }
    for (index, binary) in binary_nodes.iter().enumerate() {
        let right = effects.get(binary_count.checked_sub(index)?)?;
        let right_span = right.extent;
        if !source_word(binary, start, right_span.span.end.byte, line, column) {
            return None;
        }
    }
    // Clang node positions and the source hash alone cannot prove that
    // a borrowed C name still appears at its advertised byte position.
    // Compare every admitted function/local reference with the real source.
    if let Some(witness) = source
        && !source_identifiers_match(nodes.get(..cursor)?, witness)
    {
        return None;
    }
    Some((cursor, effects, last_end))
}

fn valid_local_variable(
    variable: &Node,
    declaration: &Node,
    reference: &str,
    input_end: u32,
) -> bool {
    variable.id == declaration.id.saturating_add(1)
        && variable.parent == declaration.id
        && variable.kind == "variable-declaration"
        && variable.type_name.as_deref() == Some("i32")
        && variable.reference.as_deref() == Some(reference)
        && variable.definition.as_deref() == Some("definition")
        && variable.linkage.as_deref() == Some("none")
        && variable.storage_class.as_deref() == Some("none")
        && matches!(
            variable.storage_duration,
            Some(super::StorageDuration::Automatic)
        )
        && variable.inline_specified.is_none()
        && variable.operation.is_none()
        && variable.literal.is_none()
        && variable.constant_integer.is_none()
        && source_word(
            variable,
            declaration.span.begin.byte,
            input_end,
            declaration.span.begin.line,
            declaration.span.begin.column,
        )
}

fn valid_local_name(name: &str) -> bool {
    !name.is_empty()
        && name.len() <= 64
        && name
            .bytes()
            .next()
            .is_some_and(|byte| byte.is_ascii_alphabetic() || byte == b'_')
        && name
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || byte == b'_')
}

// A borrowed outer byte has no local initializer inside the counted loop.
// Verify that each Clang name reference actually occurs in the caller-checked
// original C source, not just at a compatible normalized AST byte extent.
fn source_identifiers_match(nodes: &[Node], source: &[u8]) -> bool {
    nodes
        .iter()
        .filter(|node| node.kind == "declaration-reference-expression")
        .all(|node| {
            let Some(reference) = node.reference.as_deref() else {
                return false;
            };
            let name = reference.strip_prefix("external:").or_else(|| {
                reference.split_once('@').map(|(name, _offset)| name)
            });
            let Some(name) = name else {
                return false;
            };
            let (Ok(start), Ok(end)) = (
                usize::try_from(node.span.begin.byte),
                usize::try_from(node.span.end.byte),
            ) else {
                return false;
            };
            valid_local_name(name)
                && source.get(start..end) == Some(name.as_bytes())
        })
}

#[expect(
    clippy::too_many_lines,
    reason = "check all five pinned Clang declaration nodes atomically"
)]
fn prove_local_declaration<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    parent: u32,
) -> Option<LocalDeclaration<'node>> {
    let [declaration, variable, input, input_cast, input_callee] = nodes else {
        return None;
    };
    let start = declaration.span.begin.byte;
    let line = declaration.span.begin.line;
    let column = declaration.span.begin.column;
    let name = variable.name.as_deref()?;
    if !valid_local_name(name) {
        return None;
    }
    let name_len = u32::try_from(name.len()).ok()?;
    let name_start = start.checked_add(4)?;
    let input_start = name_start.checked_add(name_len)?.checked_add(3)?;
    let input_end = input_start.checked_add(9)?;
    let variable_reference = format!("{name}@{name_start}");
    let source_ok = start > previous
        && start > body.span.begin.byte
        && input_end < body.span.end.byte
        && declaration.parent == parent
        && declaration.kind == "declaration-statement"
        && declaration.type_name.is_none()
        && declaration.reference.is_none()
        && declaration.operation.is_none()
        && metadata_empty(declaration)
        && source_word(
            declaration,
            start,
            input_end.checked_add(1)?,
            line,
            column,
        )
        && valid_local_variable(
            variable,
            declaration,
            &variable_reference,
            input_end,
        )
        && input.id == variable.id.checked_add(1)?
        && input.parent == variable.id
        && input.kind == "call-expression"
        && input.type_name.as_deref() == Some("i32")
        && input.reference.as_deref() == Some("external:getchar")
        && input.operation.is_none()
        && metadata_empty(input)
        && source_word(
            input,
            input_start,
            input_end,
            line,
            column.checked_add(input_start.checked_sub(start)?)?,
        )
        && input_cast.id == input.id.checked_add(1)?
        && input_cast.parent == input.id
        && input_cast.kind == "cast-expression"
        && input_cast.type_name.as_deref() == Some("ptr(fn()->i32)")
        && input_cast.operation.as_deref() == Some("function-to-pointer")
        && input_cast.reference.is_none()
        && metadata_empty(input_cast)
        && source_word(
            input_cast,
            input_start,
            input_start.checked_add(7)?,
            line,
            column.checked_add(input_start.checked_sub(start)?)?,
        )
        && input_callee.id == input_cast.id.checked_add(1)?
        && input_callee.parent == input_cast.id
        && input_callee.kind == "declaration-reference-expression"
        && input_callee.type_name.as_deref() == Some("fn()->i32")
        && input_callee.reference.as_deref() == Some("external:getchar")
        && input_callee.operation.is_none()
        && metadata_empty(input_callee)
        && source_word(
            input_callee,
            input_start,
            input_start.checked_add(7)?,
            line,
            column.checked_add(input_start.checked_sub(start)?)?,
        );
    source_ok.then_some(LocalDeclaration {
        declaration_end: declaration.span.end.byte,
        input,
        line,
        name,
        variable_reference,
    })
}

// A successful output-call return can initialize a new C local, not only
// reassign an existing one. Prove the full source declaration and every
// normalized nested call before emitting a guest input and its writes.
// The fresh byte becomes the resident local; no older byte is restored.
#[expect(
    clippy::too_many_lines,
    reason = "the source declaration and nested call ancestry form one proof"
)]
fn prove_output_return_declaration<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    parent: u32,
    source: &[u8],
) -> Option<(LocalDeclaration<'node>, usize, Vec<&'node Node>)> {
    let [declaration, variable, output, ..] = nodes else {
        return None;
    };
    let name = variable.name.as_deref()?;
    if !valid_local_name(name) {
        return None;
    }
    let start = declaration.span.begin.byte;
    let line = declaration.span.begin.line;
    let column = declaration.span.begin.column;
    let name_start = start.checked_add(4)?;
    let output_start = name_start
        .checked_add(u32::try_from(name.len()).ok()?)?
        .checked_add(3)?;
    let local_reference = format!("{name}@{name_start}");
    let (call_width, read, calls) =
        super::nested_byte_echo::nested_call_in_parent(
            nodes.get(2..)?,
            body,
            previous,
            output.id,
            variable.id,
        )?;
    let depth = u32::try_from(calls.len()).ok()?;
    let end = output_start
        .checked_add(9)?
        .checked_add(depth.checked_mul(9)?)?;
    let spelling = format!(
        "int {name} = {}getchar(){};",
        "putchar(".repeat(calls.len()),
        ")".repeat(calls.len())
    );
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
        || start <= previous
        || start <= body.span.begin.byte
        || end >= body.span.end.byte
        || line == 0
        || column == 0
        || declaration.parent != parent
        || declaration.kind != "declaration-statement"
        || declaration.type_name.is_some()
        || declaration.reference.is_some()
        || declaration.operation.is_some()
        || !metadata_empty(declaration)
        || !source_word(declaration, start, end.checked_add(1)?, line, column)
        || !valid_local_variable(variable, declaration, &local_reference, end)
        || output.id != variable.id.checked_add(1)?
        || output.span.begin.byte != output_start
        || output.span.end.byte != end
        || output.span.begin.line != line
        || output.span.begin.column
            != column.checked_add(output_start.checked_sub(start)?)?
    {
        return None;
    }
    Some((
        LocalDeclaration {
            declaration_end: declaration.span.end.byte,
            input: read,
            line,
            name,
            variable_reference: local_reference,
        },
        call_width.checked_add(2)?,
        calls,
    ))
}

// A comma initializer is a C sequence: each left operand has its own guest
// effects and only the rightmost result initializes the new source local.
// This grammar deliberately accepts only fresh getchar() inputs, optionally
// wrapped in successful putchar() calls. Reading a stale C local would require
// storage this accumulator-only backend cannot provide.
#[expect(
    clippy::too_many_lines,
    reason = "authenticate full Clang comma ancestry and original C spelling"
)]
fn prove_comma_local_declaration<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    parent: u32,
    source: &[u8],
) -> Option<(LocalDeclaration<'node>, usize, Vec<CommaEffect<'node>>)> {
    let [declaration, variable, paren, comma, ..] = nodes else {
        return None;
    };
    let name = variable.name.as_deref()?;
    if !valid_local_name(name) {
        return None;
    }
    let start = declaration.span.begin.byte;
    let line = declaration.span.begin.line;
    let column = declaration.span.begin.column;
    let name_start = start.checked_add(4)?;
    let expression_start = name_start
        .checked_add(u32::try_from(name.len()).ok()?)?
        .checked_add(3)?;
    let local_reference = format!("{name}@{name_start}");
    if start <= previous
        || start <= body.span.begin.byte
        || line == 0
        || column == 0
        || declaration.parent != parent
        || declaration.kind != "declaration-statement"
        || declaration.type_name.is_some()
        || declaration.reference.is_some()
        || declaration.operation.is_some()
        || !metadata_empty(declaration)
        || paren.id != variable.id.checked_add(1)?
        || paren.parent != variable.id
        || paren.kind != "parenthesized-expression"
        || paren.type_name.as_deref() != Some("i32")
        || paren.reference.is_some()
        || paren.operation.is_some()
        || !metadata_empty(paren)
        || comma.id != paren.id.checked_add(1)?
    {
        return None;
    }
    let (comma_width, effects, last_end) = prove_discarded_comma_effects(
        nodes.get(3..)?,
        body,
        previous,
        comma.id,
        paren.id,
        None,
        Some(source),
    )?;
    let end = last_end.checked_add(1)?;
    if end >= body.span.end.byte
        || !source_word(declaration, start, end.checked_add(1)?, line, column)
        || !valid_local_variable(variable, declaration, &local_reference, end)
        || !source_word(
            paren,
            expression_start,
            end,
            line,
            column.checked_add(expression_start.checked_sub(start)?)?,
        )
        || comma.span.begin.byte != expression_start.checked_add(1)?
        || comma.span.end.byte != last_end
    {
        return None;
    }
    // The verified source hash alone does not bind a normalized call to the
    // corresponding C token. Require every comma operand and separator to
    // have the exact effectful C spelling asserted by the Clang subtree.
    let operands = effects
        .iter()
        .map(|effect| {
            format!(
                "{}getchar(){}",
                "putchar(".repeat(effect.outputs.len()),
                ")".repeat(effect.outputs.len())
            )
        })
        .collect::<Vec<_>>();
    let spelling = format!("int {name} = ({});", operands.join(", "));
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
    {
        return None;
    }
    let input = effects.last()?.input;
    Some((
        LocalDeclaration {
            declaration_end: declaration.span.end.byte,
            input,
            line,
            name,
            variable_reference: local_reference,
        },
        comma_width.checked_add(3)?,
        effects,
    ))
}

// An assignment into an already authenticated C local may discard several
// ordered guest inputs/writes before retaining only its last comma operand.
// Prove every node and the exact original C expression: a fresh guest read
// cannot reconstruct old C storage, and the destination may previously be
// stale.
#[expect(
    clippy::too_many_lines,
    reason = "authenticate the entire comma assignment and each guest effect"
)]
fn prove_comma_local_reassignment<'node>(
    nodes: &'node [Node],
    scope: (&Node, u32, u32),
    local: &LocalDeclaration<'_>,
    source: &[u8],
) -> Option<(usize, Vec<CommaEffect<'node>>, u32)> {
    let (body, previous, parent) = scope;
    let [assignment, destination, paren, comma, ..] = nodes else {
        return None;
    };
    let start = assignment.span.begin.byte;
    let line = assignment.span.begin.line;
    let column = assignment.span.begin.column;
    let name_end = start.checked_add(u32::try_from(local.name.len()).ok()?)?;
    let expression_start = name_end.checked_add(3)?;
    if start <= previous
        || start <= local.declaration_end
        || start <= body.span.begin.byte
        || line <= local.line
        || column == 0
        || assignment.parent != parent
        || assignment.kind != "binary-expression"
        || assignment.type_name.as_deref() != Some("i32")
        || assignment.operation.as_deref() != Some("=")
        || assignment.reference.is_some()
        || !metadata_empty(assignment)
        || destination.id != assignment.id.checked_add(1)?
        || destination.parent != assignment.id
        || destination.kind != "declaration-reference-expression"
        || destination.type_name.as_deref() != Some("i32")
        || destination.reference.as_deref()
            != Some(local.variable_reference.as_str())
        || destination.operation.is_some()
        || !metadata_empty(destination)
        || !source_word(destination, start, name_end, line, column)
        || paren.id != destination.id.checked_add(1)?
        || paren.parent != assignment.id
        || paren.kind != "parenthesized-expression"
        || paren.type_name.as_deref() != Some("i32")
        || paren.reference.is_some()
        || paren.operation.is_some()
        || !metadata_empty(paren)
        || comma.id != paren.id.checked_add(1)?
    {
        return None;
    }
    let (comma_width, effects, last_end) = prove_discarded_comma_effects(
        nodes.get(3..)?,
        body,
        previous,
        comma.id,
        paren.id,
        None,
        Some(source),
    )?;
    let end = last_end.checked_add(1)?;
    if end >= body.span.end.byte
        || !source_word(assignment, start, end, line, column)
        || !source_word(
            paren,
            expression_start,
            end,
            line,
            column.checked_add(expression_start.checked_sub(start)?)?,
        )
        || comma.span.begin.byte != expression_start.checked_add(1)?
        || comma.span.end.byte != last_end
    {
        return None;
    }
    let operands = effects
        .iter()
        .map(|effect| {
            format!(
                "{}getchar(){}",
                "putchar(".repeat(effect.outputs.len()),
                ")".repeat(effect.outputs.len())
            )
        })
        .collect::<Vec<_>>();
    let spelling = format!("{} = ({});", local.name, operands.join(", "));
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
    {
        return None;
    }
    Some((comma_width.checked_add(3)?, effects, end))
}

// A plain C `int alias = live;` copies the currently resident input byte.
// It creates a new source binding but no guest instruction or host-time byte.
// Requiring original source bytes prevents a forged normalized AST from
// asserting an identity copy where the C expression performs other work.
#[expect(
    clippy::too_many_lines,
    reason = "authenticate every bound C alias node and its source spelling"
)]
fn prove_local_alias<'node>(
    nodes: &'node [Node],
    scope: (&Node, u32, u32),
    bound_local: &LocalDeclaration<'node>,
    source: &[u8],
) -> Option<LocalDeclaration<'node>> {
    let (body, previous, parent) = scope;
    let [declaration, variable, cast, reference] = nodes else {
        return None;
    };
    let name = variable.name.as_deref()?;
    if !valid_local_name(name) || name == bound_local.name {
        return None;
    }
    let start = declaration.span.begin.byte;
    let line = declaration.span.begin.line;
    let column = declaration.span.begin.column;
    let name_start = start.checked_add(4)?;
    let value_start = name_start
        .checked_add(u32::try_from(name.len()).ok()?)?
        .checked_add(3)?;
    let end =
        value_start.checked_add(u32::try_from(bound_local.name.len()).ok()?)?;
    let alias_reference = format!("{name}@{name_start}");
    let spelling = format!("int {name} = {};", bound_local.name);
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
    {
        return None;
    }
    let verified = start > previous
        && start > bound_local.declaration_end
        && end < body.span.end.byte
        && line > bound_local.line
        && column > 0
        && declaration.parent == parent
        && declaration.kind == "declaration-statement"
        && declaration.type_name.is_none()
        && declaration.reference.is_none()
        && declaration.operation.is_none()
        && metadata_empty(declaration)
        && source_word(declaration, start, end.checked_add(1)?, line, column)
        && valid_local_variable(variable, declaration, &alias_reference, end)
        && cast.id == variable.id.checked_add(1)?
        && cast.parent == variable.id
        && cast.kind == "cast-expression"
        && cast.type_name.as_deref() == Some("i32")
        && cast.operation.as_deref() == Some("lvalue-to-rvalue")
        && cast.reference.is_none()
        && metadata_empty(cast)
        && source_word(
            cast,
            value_start,
            end,
            line,
            column.checked_add(value_start.checked_sub(start)?)?,
        )
        && reference.id == cast.id.checked_add(1)?
        && reference.parent == cast.id
        && reference.kind == "declaration-reference-expression"
        && reference.type_name.as_deref() == Some("i32")
        && reference.reference.as_deref()
            == Some(bound_local.variable_reference.as_str())
        && reference.operation.is_none()
        && metadata_empty(reference)
        && source_word(
            reference,
            value_start,
            end,
            line,
            column.checked_add(value_start.checked_sub(start)?)?,
        );
    verified.then_some(LocalDeclaration {
        declaration_end: declaration.span.end.byte,
        input: bound_local.input,
        line,
        name,
        variable_reference: alias_reference,
    })
}

// A source-local `name = getchar();` overwrites the live byte with a fresh
// *guest* input. The destination can have a stale previous value because
// reading a new byte never needs that old value. This is not general storage:
// prove all five pinned Clang nodes and the exact C bytes before emitting.
fn prove_local_input_reassignment<'node>(
    nodes: &'node [Node],
    scope: (&Node, u32, u32),
    local: &LocalDeclaration<'_>,
    source: &[u8],
    terminator: u8,
) -> Option<&'node Node> {
    if !matches!(terminator, b';' | b',' | b')') {
        return None;
    }
    let (body, previous, parent) = scope;
    let [assignment, destination, input, _, _] = nodes else {
        return None;
    };
    let start = assignment.span.begin.byte;
    let line = assignment.span.begin.line;
    let column = assignment.span.begin.column;
    let input_start = start
        .checked_add(u32::try_from(local.name.len()).ok()?)?
        .checked_add(3)?;
    let end = input_start.checked_add(9)?;
    let spelling =
        format!("{} = getchar(){}", local.name, char::from(terminator));
    // A later byte offset is sufficient even on the initializer's line.
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
        || start <= previous
        || start <= local.declaration_end
        || end >= body.span.end.byte
        || line < local.line
        || column == 0
        || assignment.parent != parent
        || assignment.kind != "binary-expression"
        || assignment.type_name.as_deref() != Some("i32")
        || assignment.operation.as_deref() != Some("=")
        || assignment.reference.is_some()
        || !metadata_empty(assignment)
        || !source_word(assignment, start, end, line, column)
        || destination.id != assignment.id.checked_add(1)?
        || destination.parent != assignment.id
        || destination.kind != "declaration-reference-expression"
        || destination.type_name.as_deref() != Some("i32")
        || destination.reference.as_deref()
            != Some(local.variable_reference.as_str())
        || destination.operation.is_some()
        || !metadata_empty(destination)
        || !source_word(
            destination,
            start,
            input_start.checked_sub(3)?,
            line,
            column,
        )
        || input.id != destination.id.checked_add(1)?
        || prove_input_call(
            nodes.get(2..5)?,
            body,
            destination.span.end.byte,
            (input.id, assignment.id),
        )
        .is_none()
        || input.span.begin.byte != input_start
        || input.span.begin.line != line
        || input.span.begin.column
            != column.checked_add(input_start.checked_sub(start)?)?
    {
        return None;
    }
    Some(input)
}

// The return of each successful nested putchar is the same guest byte.
// Assigning that result rebinds only the authenticated C destination.
// Each call must have canonical Clang ancestry and original source spelling.
#[expect(
    clippy::too_many_lines,
    reason = "nested output-return assignment is one closed source proof"
)]
fn prove_output_return_reassignment<'node>(
    nodes: &'node [Node],
    scope: (&Node, u32, u32),
    local: &LocalDeclaration<'_>,
    source: &[u8],
    terminator: u8,
) -> Option<(usize, &'node Node, Vec<&'node Node>)> {
    if !matches!(terminator, b';' | b')' | b',') {
        return None;
    }
    let (body, previous, parent) = scope;
    let [assignment, destination, output, ..] = nodes else {
        return None;
    };
    let start = assignment.span.begin.byte;
    let line = assignment.span.begin.line;
    let column = assignment.span.begin.column;
    let name_end = start.checked_add(u32::try_from(local.name.len()).ok()?)?;
    let output_start = name_end.checked_add(3)?;
    let depth = (0..MAX_NESTED_LOCAL_DEPTH)
        .take_while(|level| {
            nodes
                .get(2usize.saturating_add(level.saturating_mul(3)))
                .is_some_and(|node| {
                    node.kind == "call-expression"
                        && node.reference.as_deref() == Some("external:putchar")
                })
        })
        .count();
    let prefix_depth = depth.checked_sub(1)?;
    let inner_offset = prefix_depth.checked_mul(3)?.checked_add(2)?;
    let width = inner_offset.checked_add(6)?;
    let end = output_start
        .checked_add(18)?
        .checked_add(u32::try_from(prefix_depth.checked_mul(9)?).ok()?)?;
    let spelling = format!(
        "{} = {}getchar(){}{}",
        local.name,
        "putchar(".repeat(depth),
        ")".repeat(depth),
        char::from(terminator)
    );
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
        || start <= previous
        || start <= local.declaration_end
        || end >= body.span.end.byte
        || line <= local.line
        || column == 0
        || assignment.parent != parent
        || assignment.kind != "binary-expression"
        || assignment.type_name.as_deref() != Some("i32")
        || assignment.operation.as_deref() != Some("=")
        || assignment.reference.is_some()
        || !metadata_empty(assignment)
        || !source_word(assignment, start, end, line, column)
        || destination.id != assignment.id.checked_add(1)?
        || destination.parent != assignment.id
        || destination.kind != "declaration-reference-expression"
        || destination.type_name.as_deref() != Some("i32")
        || destination.reference.as_deref()
            != Some(local.variable_reference.as_str())
        || destination.operation.is_some()
        || !metadata_empty(destination)
        || !source_word(destination, start, name_end, line, column)
        || output.id != destination.id.checked_add(1)?
        || output.span.begin.byte != output_start
        || output.span.begin.line != line
        || output.span.begin.column
            != column.checked_add(output_start.checked_sub(start)?)?
    {
        return None;
    }
    let mut call_parent = assignment.id;
    let mut calls = Vec::with_capacity(depth);
    for level in 0..prefix_depth {
        let offset = level.checked_mul(3)?.checked_add(2)?;
        let [call, cast, callee] = nodes.get(offset..offset.checked_add(3)?)?
        else {
            return None;
        };
        let level_u32 = u32::try_from(level).ok()?;
        let call_start = output_start.checked_add(level_u32.checked_mul(8)?)?;
        let call_column = column.checked_add(call_start.checked_sub(start)?)?;
        if call.id != assignment.id.checked_add(u32::try_from(offset).ok()?)?
            || call.parent != call_parent
            || call.kind != "call-expression"
            || call.type_name.as_deref() != Some("i32")
            || call.reference.as_deref() != Some("external:putchar")
            || call.operation.is_some()
            || !metadata_empty(call)
            || !source_word(
                call,
                call_start,
                end.checked_sub(level_u32)?,
                line,
                call_column,
            )
            || cast.id != call.id.checked_add(1)?
            || cast.parent != call.id
            || cast.kind != "cast-expression"
            || cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
            || cast.operation.as_deref() != Some("function-to-pointer")
            || cast.reference.is_some()
            || !metadata_empty(cast)
            || !source_word(
                cast,
                call_start,
                call_start.checked_add(7)?,
                line,
                call_column,
            )
            || callee.id != cast.id.checked_add(1)?
            || callee.parent != cast.id
            || callee.kind != "declaration-reference-expression"
            || callee.type_name.as_deref() != Some("fn(i32)->i32")
            || callee.reference.as_deref() != Some("external:putchar")
            || callee.operation.is_some()
            || !metadata_empty(callee)
            || !source_word(
                callee,
                call_start,
                call_start.checked_add(7)?,
                line,
                call_column,
            )
        {
            return None;
        }
        calls.push(call);
        call_parent = call.id;
    }
    let inner = nodes.get(inner_offset..width)?;
    if inner.first()?.id
        != assignment
            .id
            .checked_add(u32::try_from(inner_offset).ok()?)?
    {
        return None;
    }
    let (read, innermost) =
        prove_call(inner, body, destination.span.end.byte, call_parent)?;
    calls.push(innermost);
    Some((width, read, calls))
}

// Assigning the successful return of putchar(LIVE) does not consume a second
// guest byte. Authenticate the C destination, all nested output calls, and
// the exact source tokens before reusing the accumulator's resident value.
#[expect(
    clippy::too_many_lines,
    reason = "source and nested Clang ancestry are one closed assignment proof"
)]
fn prove_resident_output_return_reassignment<'node>(
    nodes: &'node [Node],
    scope: (&Node, u32, u32),
    local: &LocalDeclaration<'_>,
    witness: (&[u8], u8),
) -> Option<OutputCallProof<'node>> {
    let (source, terminator) = witness;
    if !matches!(terminator, b';' | b')' | b',') {
        return None;
    }
    let (body, previous, parent) = scope;
    let [assignment, destination, call, ..] = nodes else {
        return None;
    };
    let start = assignment.span.begin.byte;
    let line = assignment.span.begin.line;
    let column = assignment.span.begin.column;
    let name_end = start.checked_add(u32::try_from(local.name.len()).ok()?)?;
    let call_start = name_end.checked_add(3)?;
    let (call_width, calls) = prove_local_output_chain(
        nodes.get(2..)?,
        body,
        local,
        assignment.id.checked_add(2)?,
        name_end,
        assignment.id,
        Some(source),
    )?;
    let end = calls.first()?.span.end.byte;
    let depth = calls.len();
    let spelling = format!(
        "{} = {}{}{}{}",
        local.name,
        "putchar(".repeat(depth),
        local.name,
        ")".repeat(depth),
        char::from(terminator),
    );
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
        || start <= previous
        || start <= local.declaration_end
        || end >= body.span.end.byte
        || line <= local.line
        || column == 0
        || assignment.parent != parent
        || assignment.kind != "binary-expression"
        || assignment.type_name.as_deref() != Some("i32")
        || assignment.operation.as_deref() != Some("=")
        || assignment.reference.is_some()
        || !metadata_empty(assignment)
        || !source_word(assignment, start, end, line, column)
        || destination.id != assignment.id.checked_add(1)?
        || destination.parent != assignment.id
        || destination.kind != "declaration-reference-expression"
        || destination.type_name.as_deref() != Some("i32")
        || destination.reference.as_deref()
            != Some(local.variable_reference.as_str())
        || destination.operation.is_some()
        || !metadata_empty(destination)
        || !source_word(destination, start, name_end, line, column)
        || call.id != destination.id.checked_add(1)?
        || call.span.begin.byte != call_start
        || call.span.begin.line != line
        || call.span.begin.column
            != column.checked_add(call_start.checked_sub(start)?)?
    {
        return None;
    }
    Some((call_width.checked_add(2)?, calls))
}

// Output calls may surround an assignment whose value is itself a
// successful inner output return. Authenticate both call chains, the Clang
// ancestry and the original C spelling before binding the guest byte.
#[expect(
    clippy::too_many_lines,
    reason = "both output-call ancestries are one closed source proof"
)]
fn prove_wrapped_output_return_reassignment<'node>(
    nodes: &'node [Node],
    scope: (&Node, u32, u32),
    local: &LocalDeclaration<'_>,
    source: &[u8],
) -> Option<(usize, &'node Node, Vec<&'node Node>)> {
    let (body, previous, first_parent) = scope;
    let outer = nodes.first()?;
    let start = outer.span.begin.byte;
    let line = outer.span.begin.line;
    let column = outer.span.begin.column;
    let depth = (0..MAX_NESTED_LOCAL_DEPTH)
        .take_while(|level| {
            nodes.get(level.saturating_mul(3)).is_some_and(|node| {
                node.kind == "call-expression"
                    && node.reference.as_deref() == Some("external:putchar")
            })
        })
        .count();
    if depth == 0
        || start <= previous
        || start <= local.declaration_end
        || line <= local.line
        || column == 0
    {
        return None;
    }
    let offset = depth.checked_mul(3)?;
    let mut parent = first_parent;
    let mut outer_calls = Vec::with_capacity(depth);
    for level in 0..depth {
        let index = level.checked_mul(3)?;
        let [call, cast, reference] =
            nodes.get(index..index.checked_add(3)?)?
        else {
            return None;
        };
        let level_u32 = u32::try_from(level).ok()?;
        let call_start = start.checked_add(level_u32.checked_mul(8)?)?;
        let call_column = column.checked_add(level_u32.checked_mul(8)?)?;
        if call.id != outer.id.checked_add(u32::try_from(index).ok()?)?
            || call.parent != parent
            || call.kind != "call-expression"
            || call.type_name.as_deref() != Some("i32")
            || call.reference.as_deref() != Some("external:putchar")
            || call.operation.is_some()
            || !metadata_empty(call)
            || cast.id != call.id.checked_add(1)?
            || cast.parent != call.id
            || cast.kind != "cast-expression"
            || cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
            || cast.operation.as_deref() != Some("function-to-pointer")
            || cast.reference.is_some()
            || !metadata_empty(cast)
            || !source_word(
                cast,
                call_start,
                call_start.checked_add(7)?,
                line,
                call_column,
            )
            || reference.id != cast.id.checked_add(1)?
            || reference.parent != cast.id
            || reference.kind != "declaration-reference-expression"
            || reference.type_name.as_deref() != Some("fn(i32)->i32")
            || reference.reference.as_deref() != Some("external:putchar")
            || reference.operation.is_some()
            || !metadata_empty(reference)
            || !source_word(
                reference,
                call_start,
                call_start.checked_add(7)?,
                line,
                call_column,
            )
        {
            return None;
        }
        outer_calls.push(call);
        parent = call.id;
    }
    let inner = nodes.get(offset..)?;
    let (inner_width, read, mut inner_calls) =
        prove_output_return_reassignment(
            inner,
            (body, previous, parent),
            local,
            source,
            b')',
        )?;
    if inner_calls.len().checked_add(depth)? > MAX_NESTED_LOCAL_DEPTH {
        return None;
    }
    let assignment = inner.first()?;
    if assignment.id != outer.id.checked_add(u32::try_from(offset).ok()?)? {
        return None;
    }
    let end = assignment
        .span
        .end
        .byte
        .checked_add(u32::try_from(depth).ok()?)?;
    if end >= body.span.end.byte {
        return None;
    }
    for (level, call) in outer_calls.iter().enumerate() {
        let level_u32 = u32::try_from(level).ok()?;
        if !source_word(
            call,
            start.checked_add(level_u32.checked_mul(8)?)?,
            end.checked_sub(level_u32)?,
            line,
            column.checked_add(level_u32.checked_mul(8)?)?,
        ) {
            return None;
        }
    }
    let spelling = format!(
        "{}{} = {}getchar(){}{};",
        "putchar(".repeat(depth),
        local.name,
        "putchar(".repeat(inner_calls.len()),
        ")".repeat(inner_calls.len()),
        ")".repeat(depth),
    );
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
    {
        return None;
    }
    outer_calls.append(&mut inner_calls);
    Some((offset.checked_add(inner_width)?, read, outer_calls))
}

// `putchar(name = getchar());` returns and writes the fresh guest byte,
// *and* rebinds the source-C destination for subsequent source reads. The
// assignment is an expression inside the output call, not an independent
// statement: authenticate all eight pinned nodes and the actual source token.
#[expect(
    clippy::too_many_lines,
    reason = "the nested output/assignment/input ancestry is one proof"
)]
fn prove_output_input_assignment<'node>(
    nodes: &'node [Node],
    scope: (&Node, u32, u32),
    local: &LocalDeclaration<'_>,
    source: &[u8],
    terminator: u8,
) -> Option<(&'node Node, &'node Node)> {
    let (body, previous, parent) = scope;
    if !matches!(terminator, b';' | b')' | b',') {
        return None;
    }
    let [
        output,
        output_cast,
        output_callee,
        assignment,
        destination,
        input,
        input_cast,
        input_callee,
    ] = nodes
    else {
        return None;
    };
    let start = output.span.begin.byte;
    let line = output.span.begin.line;
    let column = output.span.begin.column;
    let destination_start = start.checked_add(8)?;
    let destination_end =
        destination_start.checked_add(u32::try_from(local.name.len()).ok()?)?;
    let input_start = destination_end.checked_add(3)?;
    let input_end = input_start.checked_add(9)?;
    let end = input_end.checked_add(1)?;
    let spelling = format!(
        "putchar({} = getchar()){}",
        local.name,
        char::from(terminator)
    );
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
    {
        return None;
    }
    let verified = start > previous
        && start > local.declaration_end
        && end < body.span.end.byte
        && line > local.line
        && column > 0
        && output.parent == parent
        && output.kind == "call-expression"
        && output.type_name.as_deref() == Some("i32")
        && output.reference.as_deref() == Some("external:putchar")
        && output.operation.is_none()
        && metadata_empty(output)
        && source_word(output, start, end, line, column)
        && output_cast.id == output.id.checked_add(1)?
        && output_cast.parent == output.id
        && output_cast.kind == "cast-expression"
        && output_cast.type_name.as_deref() == Some("ptr(fn(i32)->i32)")
        && output_cast.operation.as_deref() == Some("function-to-pointer")
        && output_cast.reference.is_none()
        && metadata_empty(output_cast)
        && source_word(output_cast, start, start.checked_add(7)?, line, column)
        && output_callee.id == output_cast.id.checked_add(1)?
        && output_callee.parent == output_cast.id
        && output_callee.kind == "declaration-reference-expression"
        && output_callee.type_name.as_deref() == Some("fn(i32)->i32")
        && output_callee.reference.as_deref() == Some("external:putchar")
        && output_callee.operation.is_none()
        && metadata_empty(output_callee)
        && source_word(
            output_callee,
            start,
            start.checked_add(7)?,
            line,
            column,
        )
        && assignment.id == output_callee.id.checked_add(1)?
        && assignment.parent == output.id
        && assignment.kind == "binary-expression"
        && assignment.type_name.as_deref() == Some("i32")
        && assignment.operation.as_deref() == Some("=")
        && assignment.reference.is_none()
        && metadata_empty(assignment)
        && source_word(
            assignment,
            destination_start,
            input_end,
            line,
            column.checked_add(8)?,
        )
        && destination.id == assignment.id.checked_add(1)?
        && destination.parent == assignment.id
        && destination.kind == "declaration-reference-expression"
        && destination.type_name.as_deref() == Some("i32")
        && destination.reference.as_deref()
            == Some(local.variable_reference.as_str())
        && destination.operation.is_none()
        && metadata_empty(destination)
        && source_word(
            destination,
            destination_start,
            destination_end,
            line,
            column.checked_add(8)?,
        )
        && input.id == destination.id.checked_add(1)?
        && input_cast.id == input.id.checked_add(1)?
        && input_callee.id == input_cast.id.checked_add(1)?
        && prove_input_call(
            nodes.get(5..8)?,
            body,
            destination_end,
            (input.id, assignment.id),
        )
        .is_some()
        && input.span.begin.byte == input_start
        && input.span.end.byte == input_end
        && input.span.begin.line == line
        && input.span.begin.column
            == column.checked_add(input_start.checked_sub(start)?)?;
    verified.then_some((input, output))
}

// A nested successful putchar returns the same byte through each enclosing
// call. The inner assignment is authenticated against the original C, and
// every outer call independently proves its precise Clang parent and span.
// Only the final source-proven destination remains bound after the read.
#[expect(
    clippy::too_many_lines,
    reason = "prove nested call ancestry and the inner assignment together"
)]
fn prove_nested_output_input_assignment<'node>(
    nodes: &'node [Node],
    scope: (&Node, u32, u32),
    local: &LocalDeclaration<'_>,
    source: &[u8],
) -> Option<(usize, &'node Node, Vec<&'node Node>)> {
    let (body, previous, first_parent) = scope;
    let outer = nodes.first()?;
    let start = outer.span.begin.byte;
    let line = outer.span.begin.line;
    let column = outer.span.begin.column;
    let depth = (0..MAX_NESTED_LOCAL_DEPTH)
        .take_while(|level| {
            nodes.get(level.saturating_mul(3)).is_some_and(|node| {
                node.kind == "call-expression"
                    && node.reference.as_deref() == Some("external:putchar")
            })
        })
        .count();
    if depth < 2 || start <= previous || start <= local.declaration_end {
        return None;
    }
    let prefix_depth = depth.checked_sub(1)?;
    let inner_offset = prefix_depth.checked_mul(3)?;
    let mut parent = first_parent;
    let mut calls = Vec::with_capacity(depth);
    for level in 0..prefix_depth {
        let offset = level.checked_mul(3)?;
        let [call, cast, reference] =
            nodes.get(offset..offset.checked_add(3)?)?
        else {
            return None;
        };
        let level_u32 = u32::try_from(level).ok()?;
        let call_start = start.checked_add(level_u32.checked_mul(8)?)?;
        let call_column = column.checked_add(level_u32.checked_mul(8)?)?;
        if call.id != outer.id.checked_add(u32::try_from(offset).ok()?)?
            || call.parent != parent
            || call.kind != "call-expression"
            || call.type_name.as_deref() != Some("i32")
            || call.reference.as_deref() != Some("external:putchar")
            || call.operation.is_some()
            || !metadata_empty(call)
            || cast.id != call.id.checked_add(1)?
            || cast.parent != call.id
            || cast.kind != "cast-expression"
            || cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
            || cast.operation.as_deref() != Some("function-to-pointer")
            || cast.reference.is_some()
            || !metadata_empty(cast)
            || !source_word(
                cast,
                call_start,
                call_start.checked_add(7)?,
                line,
                call_column,
            )
            || reference.id != cast.id.checked_add(1)?
            || reference.parent != cast.id
            || reference.kind != "declaration-reference-expression"
            || reference.type_name.as_deref() != Some("fn(i32)->i32")
            || reference.reference.as_deref() != Some("external:putchar")
            || reference.operation.is_some()
            || !metadata_empty(reference)
            || !source_word(
                reference,
                call_start,
                call_start.checked_add(7)?,
                line,
                call_column,
            )
        {
            return None;
        }
        calls.push(call);
        parent = call.id;
    }
    let (read, inner) = prove_output_input_assignment(
        nodes.get(inner_offset..inner_offset.checked_add(8)?)?,
        (body, previous, parent),
        local,
        source,
        b')',
    )?;
    calls.push(inner);
    let expected_end = inner
        .span
        .end
        .byte
        .checked_add(u32::try_from(prefix_depth).ok()?)?;
    if expected_end >= body.span.end.byte {
        return None;
    }
    for (level, call) in calls.iter().take(prefix_depth).enumerate() {
        let level_u32 = u32::try_from(level).ok()?;
        if !source_word(
            call,
            start.checked_add(level_u32.checked_mul(8)?)?,
            expected_end.checked_sub(level_u32)?,
            line,
            column.checked_add(level_u32.checked_mul(8)?)?,
        ) {
            return None;
        }
    }
    let spelling = format!(
        "{}putchar({} = getchar()){};",
        "putchar(".repeat(prefix_depth),
        local.name,
        ")".repeat(prefix_depth)
    );
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(expected_end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
    {
        return None;
    }
    Some((inner_offset.checked_add(8)?, read, calls))
}

// Copy a currently resident guest byte into an already declared C local.
// The destination may hold a stale byte: a successful identity assignment
// rebinds that C name without reading input or materializing another value.
// Both sides must come from independently authenticated declarations and
// exactly match the caller-verified original source bytes.
#[expect(
    clippy::too_many_lines,
    reason = "authenticate both C assignment bindings and their original bytes"
)]
fn prove_local_copy_assignment(
    nodes: &[Node],
    scope: (&Node, u32, u32),
    destination: &LocalDeclaration<'_>,
    source_local: &LocalDeclaration<'_>,
    source: &[u8],
) -> Option<()> {
    let (body, previous, parent) = scope;
    let [assignment, destination_ref, read, source_ref] = nodes else {
        return None;
    };
    let start = assignment.span.begin.byte;
    let line = assignment.span.begin.line;
    let column = assignment.span.begin.column;
    let destination_end =
        start.checked_add(u32::try_from(destination.name.len()).ok()?)?;
    let source_start = destination_end.checked_add(3)?;
    let end = source_start
        .checked_add(u32::try_from(source_local.name.len()).ok()?)?;
    let spelling = format!("{} = {};", destination.name, source_local.name);
    if source.get(
        usize::try_from(start).ok()?
            ..usize::try_from(end.checked_add(1)?).ok()?,
    ) != Some(spelling.as_bytes())
    {
        return None;
    }
    let verified = start > previous
        && start > destination.declaration_end
        && start > source_local.declaration_end
        && end < body.span.end.byte
        && line > destination.line
        && line > source_local.line
        && column > 0
        && assignment.parent == parent
        && assignment.kind == "binary-expression"
        && assignment.type_name.as_deref() == Some("i32")
        && assignment.operation.as_deref() == Some("=")
        && assignment.reference.is_none()
        && metadata_empty(assignment)
        && source_word(assignment, start, end, line, column)
        && destination_ref.id == assignment.id.checked_add(1)?
        && destination_ref.parent == assignment.id
        && destination_ref.kind == "declaration-reference-expression"
        && destination_ref.type_name.as_deref() == Some("i32")
        && destination_ref.reference.as_deref()
            == Some(destination.variable_reference.as_str())
        && destination_ref.operation.is_none()
        && metadata_empty(destination_ref)
        && source_word(destination_ref, start, destination_end, line, column)
        && read.id == destination_ref.id.checked_add(1)?
        && read.parent == assignment.id
        && read.kind == "cast-expression"
        && read.type_name.as_deref() == Some("i32")
        && read.operation.as_deref() == Some("lvalue-to-rvalue")
        && read.reference.is_none()
        && metadata_empty(read)
        && source_word(
            read,
            source_start,
            end,
            line,
            column.checked_add(source_start.checked_sub(start)?)?,
        )
        && source_ref.id == read.id.checked_add(1)?
        && source_ref.parent == read.id
        && source_ref.kind == "declaration-reference-expression"
        && source_ref.type_name.as_deref() == Some("i32")
        && source_ref.reference.as_deref()
            == Some(source_local.variable_reference.as_str())
        && source_ref.operation.is_none()
        && metadata_empty(source_ref)
        && source_word(
            source_ref,
            source_start,
            end,
            line,
            column.checked_add(source_start.checked_sub(start)?)?,
        );
    verified.then_some(())
}

/// The exact read of the source-local value in the following output call.
#[expect(
    clippy::too_many_lines,
    reason = "check all five pinned Clang output nodes atomically"
)]
fn prove_local_output<'node>(
    nodes: &'node [Node],
    body: &Node,
    local: &LocalDeclaration<'_>,
    expected_id: u32,
    previous: u32,
    parent: u32,
) -> Option<&'node Node> {
    let [
        output,
        output_cast,
        output_callee,
        value_cast,
        value_reference,
    ] = nodes
    else {
        return None;
    };
    let name_len = u32::try_from(local.name.len()).ok()?;
    let output_start = output.span.begin.byte;
    let output_line = output.span.begin.line;
    let output_column = output.span.begin.column;
    let output_end = output_start.checked_add(9)?.checked_add(name_len)?;
    let arg_start = output_start.checked_add(8)?;
    let arg_end = arg_start.checked_add(name_len)?;
    let argument_column = output_column.checked_add(8)?;
    let source_ok = output_end < body.span.end.byte
        && output.id == expected_id
        && output.parent == parent
        && output.kind == "call-expression"
        && output.type_name.as_deref() == Some("i32")
        && output.reference.as_deref() == Some("external:putchar")
        && output.operation.is_none()
        && metadata_empty(output)
        && output_start > local.declaration_end
        && output_start > previous
        && output_line > local.line
        && source_word(
            output,
            output_start,
            output_end,
            output_line,
            output_column,
        )
        && output_cast.id == output.id.checked_add(1)?
        && output_cast.parent == output.id
        && output_cast.kind == "cast-expression"
        && output_cast.type_name.as_deref() == Some("ptr(fn(i32)->i32)")
        && output_cast.operation.as_deref() == Some("function-to-pointer")
        && output_cast.reference.is_none()
        && metadata_empty(output_cast)
        && source_word(
            output_cast,
            output_start,
            output_start.checked_add(7)?,
            output_line,
            output_column,
        )
        && output_callee.id == output_cast.id.checked_add(1)?
        && output_callee.parent == output_cast.id
        && output_callee.kind == "declaration-reference-expression"
        && output_callee.type_name.as_deref() == Some("fn(i32)->i32")
        && output_callee.reference.as_deref() == Some("external:putchar")
        && output_callee.operation.is_none()
        && metadata_empty(output_callee)
        && source_word(
            output_callee,
            output_start,
            output_start.checked_add(7)?,
            output_line,
            output_column,
        )
        && value_cast.id == output_callee.id.checked_add(1)?
        && value_cast.parent == output.id
        && value_cast.kind == "cast-expression"
        && value_cast.type_name.as_deref() == Some("i32")
        && value_cast.operation.as_deref() == Some("lvalue-to-rvalue")
        && value_cast.reference.is_none()
        && metadata_empty(value_cast)
        && source_word(
            value_cast,
            arg_start,
            arg_end,
            output_line,
            argument_column,
        )
        && value_reference.id == value_cast.id.checked_add(1)?
        && value_reference.parent == value_cast.id
        && value_reference.kind == "declaration-reference-expression"
        && value_reference.type_name.as_deref() == Some("i32")
        && value_reference.reference.as_deref()
            == Some(local.variable_reference.as_str())
        && value_reference.operation.is_none()
        && metadata_empty(value_reference)
        && source_word(
            value_reference,
            arg_start,
            arg_end,
            output_line,
            argument_column,
        );
    source_ok.then_some(output)
}

// A successful getchar() returns a byte in [0, 255]. C's explicit
// `(unsigned char)` narrowing and integer promotion therefore preserve the
// exact runtime byte: the guest must not synthesize a second read or
// arithmetic. Authenticate both conversion nodes and the underlying live local
// read.
#[expect(
    clippy::too_many_lines,
    reason = "seven source-ordered Clang nodes constitute one cast proof"
)]
fn prove_unsigned_cast_local_output<'node>(
    nodes: &'node [Node],
    body: &Node,
    local: &LocalDeclaration<'_>,
    expected_id: u32,
    previous: u32,
    parent: u32,
) -> Option<&'node Node> {
    let [
        output,
        output_cast,
        output_callee,
        promoted,
        narrowed,
        value_cast,
        value_reference,
    ] = nodes
    else {
        return None;
    };
    let name_len = u32::try_from(local.name.len()).ok()?;
    let start = output.span.begin.byte;
    let line = output.span.begin.line;
    let column = output.span.begin.column;
    let argument_start = start.checked_add(8)?;
    let value_start = argument_start.checked_add(15)?;
    let argument_end = value_start.checked_add(name_len)?;
    let end = argument_end.checked_add(1)?;
    if start <= previous
        || start <= local.declaration_end
        || line <= local.line
        || end >= body.span.end.byte
        || output.id != expected_id
        || output.parent != parent
        || output.kind != "call-expression"
        || output.type_name.as_deref() != Some("i32")
        || output.reference.as_deref() != Some("external:putchar")
        || output.operation.is_some()
        || !metadata_empty(output)
        || !source_word(output, start, end, line, column)
        || output_cast.id != output.id.checked_add(1)?
        || output_cast.parent != output.id
        || output_cast.kind != "cast-expression"
        || output_cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
        || output_cast.operation.as_deref() != Some("function-to-pointer")
        || output_cast.reference.is_some()
        || !metadata_empty(output_cast)
        || !source_word(output_cast, start, start.checked_add(7)?, line, column)
        || output_callee.id != output_cast.id.checked_add(1)?
        || output_callee.parent != output_cast.id
        || output_callee.kind != "declaration-reference-expression"
        || output_callee.type_name.as_deref() != Some("fn(i32)->i32")
        || output_callee.reference.as_deref() != Some("external:putchar")
        || output_callee.operation.is_some()
        || !metadata_empty(output_callee)
        || !source_word(
            output_callee,
            start,
            start.checked_add(7)?,
            line,
            column,
        )
        || promoted.id != output_callee.id.checked_add(1)?
        || promoted.parent != output.id
        || promoted.kind != "cast-expression"
        || promoted.type_name.as_deref() != Some("i32")
        || promoted.operation.as_deref() != Some("integral-cast")
        || promoted.reference.is_some()
        || !metadata_empty(promoted)
        || !source_word(
            promoted,
            argument_start,
            argument_end,
            line,
            column.checked_add(8)?,
        )
        || narrowed.id != promoted.id.checked_add(1)?
        || narrowed.parent != promoted.id
        || narrowed.kind != "cast-expression"
        || narrowed.type_name.as_deref() != Some("u8")
        || narrowed.operation.as_deref() != Some("integral-cast")
        || narrowed.reference.is_some()
        || !metadata_empty(narrowed)
        || !source_word(
            narrowed,
            argument_start,
            argument_end,
            line,
            column.checked_add(8)?,
        )
        || value_cast.id != narrowed.id.checked_add(1)?
        || value_cast.parent != narrowed.id
        || value_cast.kind != "cast-expression"
        || value_cast.type_name.as_deref() != Some("i32")
        || value_cast.operation.as_deref() != Some("lvalue-to-rvalue")
        || value_cast.reference.is_some()
        || !metadata_empty(value_cast)
        || !source_word(
            value_cast,
            value_start,
            argument_end,
            line,
            column.checked_add(23)?,
        )
        || value_reference.id != value_cast.id.checked_add(1)?
        || value_reference.parent != value_cast.id
        || value_reference.kind != "declaration-reference-expression"
        || value_reference.type_name.as_deref() != Some("i32")
        || value_reference.reference.as_deref()
            != Some(local.variable_reference.as_str())
        || value_reference.operation.is_some()
        || !metadata_empty(value_reference)
        || !source_word(
            value_reference,
            value_start,
            argument_end,
            line,
            column.checked_add(23)?,
        )
    {
        return None;
    }
    Some(output)
}

// Every admitted operator is an exact integer identity on a successful
// `getchar()` result in [0, 255]. That range is preserved after *each* step,
// so finite compositions can reuse the same guest SSA byte without host-time
// evaluation. Other C operators and effects do not enter this proof.
fn byte_identity_operator(
    operation: Option<&str>,
) -> Option<(&'static str, &'static str)> {
    match operation? {
        "&" => Some(("&", "255")),
        "%" => Some(("%", "256")),
        "|" => Some(("|", "0")),
        "^" => Some(("^", "0")),
        "+" => Some(("+", "0")),
        "-" => Some(("-", "0")),
        "*" => Some(("*", "1")),
        "/" => Some(("/", "1")),
        "<<" => Some(("<<", "0")),
        ">>" => Some((">>", "0")),
        _ => None,
    }
}

// A C zero token must be both the exact source character and the exact
// normalized Clang integer value. No effectful expression can masquerade as
// the inactive branch of a guest-dependent byte identity.
#[expect(
    clippy::too_many_arguments,
    reason = "verify all source coordinates and normalized node identity"
)]
fn prove_byte_zero_literal(
    node: &Node,
    expected_id: u32,
    parent: u32,
    start: u32,
    line: u32,
    column: u32,
) -> Option<()> {
    (node.id == expected_id
        && node.parent == parent
        && node.kind == "integer-literal"
        && node.type_name.as_deref() == Some("i32")
        && node.reference.is_none()
        && node.operation.is_none()
        && node.name.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
        && node.literal.as_deref() == Some("0")
        && node.constant_integer.as_deref() == Some("0")
        && source_word(node, start, start.checked_add(1)?, line, column))
    .then_some(())
}

// Authenticate a pure C test equivalent to (b != 0) or (b == 0) for the
// one proven, successful resident byte. Strict source spelling rules out
// changing the tested byte, hiding guest I/O, or forging Clang parentage.
#[expect(
    clippy::too_many_arguments,
    clippy::too_many_lines,
    reason = "a zero test combines a source proof and Clang preorder proof"
)]
fn prove_byte_zero_guard(
    nodes: &[Node],
    local: Option<&LocalDeclaration<'_>>,
    body: &Node,
    previous: u32,
    parent: u32,
    expected_id: u32,
    depth: usize,
    source: &[u8],
) -> Option<(usize, String, bool)> {
    let root = nodes.first()?;
    if root.id != expected_id
        || root.parent != parent
        || root.type_name.as_deref() != Some("i32")
        || root.reference.is_some()
        || !metadata_empty(root)
    {
        return None;
    }
    let (width, spelling, nonzero) = if root.kind == "unary-expression"
        && root.operation.as_deref() == Some("!")
    {
        let (width, operand, read, calls) = prove_byte_identity_expression(
            nodes.get(1..)?,
            local,
            body,
            previous,
            root.id,
            root.id.checked_add(1)?,
            depth.checked_add(1)?,
            source,
        )?;
        if read.is_some() || !calls.is_empty() {
            return None;
        }
        (width.checked_add(1)?, format!("!{operand}"), false)
    } else if root.kind == "binary-expression"
        && matches!(root.operation.as_deref(), Some("==" | "!="))
    {
        let (width, operand, read, calls) = prove_byte_identity_expression(
            nodes.get(1..)?,
            local,
            body,
            previous,
            root.id,
            root.id.checked_add(1)?,
            depth.checked_add(1)?,
            source,
        )?;
        if read.is_some() || !calls.is_empty() {
            return None;
        }
        let literal_index = width.checked_add(1)?;
        let literal = nodes.get(literal_index)?;
        let start =
            root.span.begin.byte.checked_add(
                u32::try_from(operand.len().checked_add(4)?).ok()?,
            )?;
        prove_byte_zero_literal(
            literal,
            root.id.checked_add(u32::try_from(literal_index).ok()?)?,
            root.id,
            start,
            root.span.begin.line,
            root.span
                .begin
                .column
                .checked_add(start.checked_sub(root.span.begin.byte)?)?,
        )?;
        let operator = root.operation.as_deref()?;
        (
            literal_index.checked_add(1)?,
            format!("{operand} {operator} 0"),
            operator == "!=",
        )
    } else {
        let (width, operand, read, calls) = prove_byte_identity_expression(
            nodes,
            local,
            body,
            previous,
            parent,
            expected_id,
            depth,
            source,
        )?;
        if read.is_some() || !calls.is_empty() {
            return None;
        }
        (width, operand, true)
    };
    let start = root.span.begin.byte;
    let end = start.checked_add(u32::try_from(spelling.len()).ok()?)?;
    (source_word(
        root,
        start,
        end,
        root.span.begin.line,
        root.span.begin.column,
    ) && source.get(usize::try_from(start).ok()?..usize::try_from(end).ok()?)
        == Some(spelling.as_bytes()))
    .then_some((width, spelling, nonzero))
}

// Shared exact root contract for pure C integer expressions in the pinned
// normalized Clang preorder. Leaf/node checks remain independent below.
fn pure_integer_root(
    root: &Node,
    kind: &str,
    parent: u32,
    expected_id: u32,
) -> bool {
    root.id == expected_id
        && root.parent == parent
        && root.kind == kind
        && root.type_name.as_deref() == Some("i32")
        && root.reference.is_none()
        && (metadata_empty(root)
            || (kind == "unary-expression"
                && metadata_except_integer_constant_empty(root)))
}

// Independently bind a reconstructed pure expression to the same C source
// bytes and pinned Clang span. This is shared by the guard and full ternary.
fn pure_expression_source(
    root: &Node,
    spelling: &str,
    source: &[u8],
) -> Option<()> {
    let end = root
        .span
        .begin
        .byte
        .checked_add(u32::try_from(spelling.len()).ok()?)?;
    (spelling.len() <= MAX_BYTE_IDENTITY_LENGTH
        && source_word(
            root,
            root.span.begin.byte,
            end,
            root.span.begin.line,
            root.span.begin.column,
        )
        && source.get(
            usize::try_from(root.span.begin.byte).ok()?
                ..usize::try_from(end).ok()?,
        ) == Some(spelling.as_bytes()))
    .then_some(())
}

// A predicate literal is a nonnegative, source-backed signed C integer.
// This allows proving comparisons with thresholds outside the guest byte
// interval; the Clang coordinate and value must still agree exactly.
fn pure_guard_decimal_literal<'node>(
    literal: &'node Node,
    root: &Node,
    index: usize,
    prefix_len: usize,
) -> Option<&'node str> {
    let digits = literal.literal.as_deref()?;
    let value = digits.parse::<i32>().ok()?;
    if value.to_string() != digits {
        return None;
    }
    let start = root
        .span
        .begin
        .byte
        .checked_add(u32::try_from(prefix_len).ok()?)?;
    let end = start.checked_add(u32::try_from(digits.len()).ok()?)?;
    (literal.id == root.id.checked_add(u32::try_from(index).ok()?)?
        && literal.parent == root.id
        && literal.kind == "integer-literal"
        && literal.type_name.as_deref() == Some("i32")
        && literal.reference.is_none()
        && literal.operation.is_none()
        && literal.name.is_none()
        && literal.definition.is_none()
        && literal.inline_specified.is_none()
        && literal.linkage.is_none()
        && literal.storage_class.is_none()
        && literal.storage_duration.is_none()
        && literal.constant_integer.as_deref() == Some(digits)
        && source_word(
            literal,
            start,
            end,
            root.span.begin.line,
            root.span
                .begin
                .column
                .checked_add(start.checked_sub(root.span.begin.byte)?)?,
        ))
    .then_some(digits)
}

// A pure comparison or mask of the resident byte may choose either branch,
// provided both branches independently prove the same successful guest byte.
// This proves a conditional *result*, not guest-side control flow.
#[expect(
    clippy::too_many_arguments,
    reason = "cross-check the pure predicate against original C and Clang"
)]
fn prove_pure_byte_guard(
    nodes: &[Node],
    local: Option<&LocalDeclaration<'_>>,
    body: &Node,
    previous: u32,
    parent: u32,
    expected_id: u32,
    depth: usize,
    source: &[u8],
) -> Option<(usize, String)> {
    if let Some((width, spelling, _)) = prove_byte_zero_guard(
        nodes,
        local,
        body,
        previous,
        parent,
        expected_id,
        depth,
        source,
    ) {
        return Some((width, spelling));
    }
    let root = nodes.first()?;
    let operator = root.operation.as_deref()?;
    if !pure_integer_root(root, "binary-expression", parent, expected_id)
        || !matches!(operator, "<" | "<=" | ">" | ">=" | "==" | "!=" | "&")
    {
        return None;
    }
    let (left_width, left, input, outputs) = prove_byte_identity_expression(
        nodes.get(1..)?,
        local,
        body,
        previous,
        root.id,
        root.id.checked_add(1)?,
        depth.checked_add(1)?,
        source,
    )?;
    if input.is_some() || !outputs.is_empty() {
        return None;
    }
    let index = left_width.checked_add(1)?;
    let digits = pure_guard_decimal_literal(
        nodes.get(index)?,
        root,
        index,
        left.len().checked_add(operator.len())?.checked_add(2)?,
    )?;
    let spelling = format!("{left} {operator} {digits}");
    pure_expression_source(root, &spelling, source)?;
    Some((index.checked_add(1)?, spelling))
}

// Both operands must be pure and each must independently retain the same
// resident guest byte; a nested read or output can never be skipped.
#[expect(
    clippy::too_many_arguments,
    reason = "preserve independently checked nested Clang ancestry"
)]
fn pure_identity_arm(
    nodes: &[Node],
    local: Option<&LocalDeclaration<'_>>,
    body: &Node,
    previous: u32,
    parent: u32,
    expected_id: u32,
    depth: usize,
    source: &[u8],
) -> Option<(usize, String)> {
    let (width, spelling, input, outputs) = prove_byte_identity_expression(
        nodes,
        local,
        body,
        previous,
        parent,
        expected_id,
        depth,
        source,
    )?;
    (input.is_none() && outputs.is_empty()).then_some((width, spelling))
}

// Keep the source-ordered two-arm proof separate from the guard and outer
// source span: both byte identities must be established independently.
#[expect(
    clippy::too_many_arguments,
    reason = "retain parent IDs and limits for each Clang child proof"
)]
fn pure_ternary_arms(
    nodes: &[Node],
    local: Option<&LocalDeclaration<'_>>,
    body: &Node,
    previous: u32,
    root: &Node,
    guard_width: usize,
    depth: usize,
    source: &[u8],
) -> Option<PureTernaryArmProof> {
    let then_index = guard_width.checked_add(1)?;
    let (then_width, then_spelling) = pure_identity_arm(
        nodes.get(then_index..)?,
        local,
        body,
        previous,
        root.id,
        root.id.checked_add(u32::try_from(then_index).ok()?)?,
        depth.checked_add(1)?,
        source,
    )?;
    let else_index = then_index.checked_add(then_width)?;
    let (else_width, else_spelling) = pure_identity_arm(
        nodes.get(else_index..)?,
        local,
        body,
        previous,
        root.id,
        root.id.checked_add(u32::try_from(else_index).ok()?)?,
        depth.checked_add(1)?,
        source,
    )?;
    Some((
        else_index.checked_add(else_width)?,
        then_spelling,
        else_spelling,
    ))
}

#[expect(
    clippy::too_many_arguments,
    reason = "prove both ternary branches and the original source geometry"
)]
fn prove_equivalent_byte_arms(
    nodes: &[Node],
    local: Option<&LocalDeclaration<'_>>,
    body: &Node,
    previous: u32,
    parent: u32,
    expected_id: u32,
    depth: usize,
    source: &[u8],
) -> Option<(usize, String)> {
    let root = nodes.first().filter(|root| {
        pure_integer_root(root, "conditional-expression", parent, expected_id)
            && root.operation.is_none()
    })?;
    let (guard_width, guard) = prove_pure_byte_guard(
        nodes.get(1..)?,
        local,
        body,
        previous,
        root.id,
        root.id.checked_add(1)?,
        depth.checked_add(1)?,
        source,
    )?;
    let (width, then_spelling, else_spelling) = pure_ternary_arms(
        nodes,
        local,
        body,
        previous,
        root,
        guard_width,
        depth,
        source,
    )?;
    let spelling = format!("{guard} ? {then_spelling} : {else_spelling}");
    pure_expression_source(root, &spelling, source)?;
    Some((width, spelling))
}

// The selected pure identity must win on every *positive* successful byte.
// At zero, either the identity or the literal-zero arm produces the same 0.
// The caller already proved the entire pure C/Clang guard and both arm trees.
fn proven_positive_byte_range_truth(
    nodes: &[Node],
    width: usize,
) -> Option<bool> {
    let root = nodes.first()?;
    if root.kind != "binary-expression" {
        return None;
    }
    let value = nodes
        .get(width.checked_sub(1)?)?
        .literal
        .as_deref()?
        .parse::<i32>()
        .ok()?;
    match (root.operation.as_deref()?, value) {
        ("<", 0 | 1) | ("<=", 0) | (">", 255..) => Some(false),
        ("<", 256..) | ("<=", 255..) | (">", 0) => Some(true),
        (">=", 0 | 1) => Some(true),
        (">=", 256..) => Some(false),
        ("==", 0 | 256..) => Some(false),
        ("!=", 0 | 256..) => Some(true),
        ("&", value) if value & 255 == 0 => Some(false),
        ("&", value) if value & 255 == 255 => Some(true),
        _ => None,
    }
}

// Both C arms are authenticated even when one is unreachable for a successful
// byte: the selected arm is a pure identity and the other must be literal zero.
// No otherwise unreachable I/O or unproved arithmetic may be silently erased.
#[expect(
    clippy::too_many_arguments,
    reason = "retain the Clang parent, source span and pure selected C arm"
)]
fn prove_range_ternary_arm(
    nodes: &[Node],
    local: Option<&LocalDeclaration<'_>>,
    body: &Node,
    previous: u32,
    root: &Node,
    index: usize,
    depth: usize,
    source: &[u8],
    start: u32,
    selected: bool,
) -> Option<(usize, String)> {
    let expected_id = root.id.checked_add(u32::try_from(index).ok()?)?;
    if selected {
        return pure_identity_arm(
            nodes.get(index..)?,
            local,
            body,
            previous,
            root.id,
            expected_id,
            depth.checked_add(1)?,
            source,
        );
    }
    prove_byte_zero_literal(
        nodes.get(index)?,
        expected_id,
        root.id,
        start,
        root.span.begin.line,
        root.span
            .begin
            .column
            .checked_add(start.checked_sub(root.span.begin.byte)?)?,
    )?;
    Some((1, String::from("0")))
}

// The byte-bound guard is proven separately; this verifies source order and
// the full Clang child ancestry of both pure arms, regardless of selection.
#[expect(
    clippy::too_many_arguments,
    reason = "bind two C arm proofs to the exact parent and source context"
)]
fn prove_range_ternary_arms(
    nodes: &[Node],
    local: Option<&LocalDeclaration<'_>>,
    body: &Node,
    previous: u32,
    root: &Node,
    condition: &str,
    condition_width: usize,
    condition_value: bool,
    depth: usize,
    source: &[u8],
) -> Option<PureTernaryArmProof> {
    let then_index = condition_width.checked_add(1)?;
    let then_start =
        root.span.begin.byte.checked_add(
            u32::try_from(condition.len().checked_add(3)?).ok()?,
        )?;
    let (then_width, then_spelling) = prove_range_ternary_arm(
        nodes,
        local,
        body,
        previous,
        root,
        then_index,
        depth,
        source,
        then_start,
        condition_value,
    )?;
    let else_index = then_index.checked_add(then_width)?;
    let else_start = then_start.checked_add(
        u32::try_from(then_spelling.len().checked_add(3)?).ok()?,
    )?;
    let (else_width, else_spelling) = prove_range_ternary_arm(
        nodes,
        local,
        body,
        previous,
        root,
        else_index,
        depth,
        source,
        else_start,
        !condition_value,
    )?;
    Some((
        else_index.checked_add(else_width)?,
        then_spelling,
        else_spelling,
    ))
}

// The selected pure byte identity must execute for all successful positive
// bytes; zero may choose either pure arm since both produce zero at zero.
// The proof never inspects guest input or invents dynamic guest control.
#[expect(
    clippy::too_many_arguments,
    reason = "prove the original source, the guard and both C arm witnesses"
)]
fn prove_range_selected_byte_identity(
    nodes: &[Node],
    local: Option<&LocalDeclaration<'_>>,
    body: &Node,
    previous: u32,
    parent: u32,
    expected_id: u32,
    depth: usize,
    source: &[u8],
) -> Option<(usize, String)> {
    let root = nodes.first().filter(|root| {
        pure_integer_root(root, "conditional-expression", parent, expected_id)
            && root.operation.is_none()
    })?;
    let condition_nodes = nodes.get(1..)?;
    let (condition_width, condition) = prove_pure_byte_guard(
        condition_nodes,
        local,
        body,
        previous,
        root.id,
        root.id.checked_add(1)?,
        depth.checked_add(1)?,
        source,
    )?;
    let condition_value =
        proven_positive_byte_range_truth(condition_nodes, condition_width)?;
    let (width, then_spelling, else_spelling) = prove_range_ternary_arms(
        nodes,
        local,
        body,
        previous,
        root,
        &condition,
        condition_width,
        condition_value,
        depth,
        source,
    )?;
    let spelling = format!("{condition} ? {then_spelling} : {else_spelling}");
    pure_expression_source(root, &spelling, source)?;
    Some((width, spelling))
}

// Match the entire Clang preorder and original C bytes for exact identities.
// A leaf is either a proven live local or a source-proven input/output call
// that returns the same successful byte. Preserve the leaf's actual guest
// effects; arithmetic never evaluates the input on the host.
#[expect(
    clippy::cognitive_complexity,
    clippy::too_many_arguments,
    clippy::too_many_lines,
    reason = "check every Clang node and source byte as one proof"
)]
fn prove_byte_identity_expression<'node>(
    nodes: &'node [Node],
    local: Option<&LocalDeclaration<'_>>,
    body: &Node,
    previous: u32,
    parent: u32,
    expected_id: u32,
    depth: usize,
    source: &[u8],
) -> Option<(usize, String, Option<&'node Node>, Vec<&'node Node>)> {
    let root = nodes.first()?;
    if depth > MAX_BYTE_IDENTITY_DEPTH
        || root.id != expected_id
        || root.parent != parent
        || root.type_name.as_deref() != Some("i32")
        || !metadata_empty(root)
    {
        return None;
    }
    let (width, spelling, input, outputs) = match root.kind.as_str() {
        "cast-expression"
            if root.operation.as_deref() == Some("lvalue-to-rvalue")
                && root.reference.is_none() =>
        {
            let local = local?;
            let reference = nodes.get(1)?;
            if reference.id != root.id.checked_add(1)?
                || reference.parent != root.id
                || reference.kind != "declaration-reference-expression"
                || reference.type_name.as_deref() != Some("i32")
                || reference.reference.as_deref()
                    != Some(local.variable_reference.as_str())
                || reference.operation.is_some()
                || !metadata_empty(reference)
                || reference.span != root.span
            {
                return None;
            }
            (2, local.name.to_owned(), None, Vec::new())
        },
        "parenthesized-expression"
            if root.operation.is_none() && root.reference.is_none() =>
        {
            let (child_width, child, input, outputs) =
                prove_byte_identity_expression(
                    nodes.get(1..)?,
                    local,
                    body,
                    previous,
                    root.id,
                    root.id.checked_add(1)?,
                    depth.checked_add(1)?,
                    source,
                )?;
            (
                child_width.checked_add(1)?,
                format!("({child})"),
                input,
                outputs,
            )
        },
        "call-expression"
            if root.reference.as_deref() == Some("external:getchar")
                && root.operation.is_none() =>
        {
            let read = prove_input_call(
                nodes.get(..3)?,
                body,
                previous,
                (root.id, root.parent),
            )?;
            (3, String::from("getchar()"), Some(read), Vec::new())
        },
        "call-expression"
            if root.reference.as_deref() == Some("external:putchar")
                && root.operation.is_none() =>
        {
            let (width, read, calls) =
                super::nested_byte_echo::nested_call_in_parent(
                    nodes,
                    body,
                    previous,
                    root.id,
                    root.parent,
                )?;
            let spelling = format!(
                "{}getchar(){}",
                "putchar(".repeat(calls.len()),
                ")".repeat(calls.len()),
            );
            (width, spelling, Some(read), calls)
        },
        // Both directions of a source-proven zero test select the same
        // successful guest byte: b ? b : 0, b != 0 ? b : 0,
        // b == 0 ? 0 : b and !b ? 0 : b. No guest branch executes because
        // the two pure C arms agree on the byte for every b in [0, 255].
        "conditional-expression"
            if root.reference.is_none() && root.operation.is_none() =>
        {
            if let Some((width, spelling)) = prove_equivalent_byte_arms(
                nodes,
                local,
                body,
                previous,
                parent,
                expected_id,
                depth,
                source,
            ) {
                return Some((width, spelling, None, Vec::new()));
            }
            if let Some((width, spelling)) = prove_range_selected_byte_identity(
                nodes,
                local,
                body,
                previous,
                parent,
                expected_id,
                depth,
                source,
            ) {
                return Some((width, spelling, None, Vec::new()));
            }
            let _ = local?;
            let (condition_width, condition, nonzero) = prove_byte_zero_guard(
                nodes.get(1..)?,
                local,
                body,
                previous,
                root.id,
                root.id.checked_add(1)?,
                depth.checked_add(1)?,
                source,
            )?;
            let true_index = condition_width.checked_add(1)?;
            let (true_width, true_spelling) = if nonzero {
                let (width, spelling, input, outputs) =
                    prove_byte_identity_expression(
                        nodes.get(true_index..)?,
                        local,
                        body,
                        previous,
                        root.id,
                        root.id.checked_add(u32::try_from(true_index).ok()?)?,
                        depth.checked_add(1)?,
                        source,
                    )?;
                if input.is_some() || !outputs.is_empty() {
                    return None;
                }
                (width, spelling)
            } else {
                let true_start = root.span.begin.byte.checked_add(
                    u32::try_from(condition.len().checked_add(3)?).ok()?,
                )?;
                prove_byte_zero_literal(
                    nodes.get(true_index)?,
                    root.id.checked_add(u32::try_from(true_index).ok()?)?,
                    root.id,
                    true_start,
                    root.span.begin.line,
                    root.span.begin.column.checked_add(
                        true_start.checked_sub(root.span.begin.byte)?,
                    )?,
                )?;
                (1, String::from("0"))
            };
            let false_index = true_index.checked_add(true_width)?;
            let (false_width, false_spelling) = if nonzero {
                let false_start = root.span.begin.byte.checked_add(
                    u32::try_from(
                        condition
                            .len()
                            .checked_add(true_spelling.len())?
                            .checked_add(6)?,
                    )
                    .ok()?,
                )?;
                prove_byte_zero_literal(
                    nodes.get(false_index)?,
                    root.id.checked_add(u32::try_from(false_index).ok()?)?,
                    root.id,
                    false_start,
                    root.span.begin.line,
                    root.span.begin.column.checked_add(
                        false_start.checked_sub(root.span.begin.byte)?,
                    )?,
                )?;
                (1, String::from("0"))
            } else {
                let (width, spelling, input, outputs) =
                    prove_byte_identity_expression(
                        nodes.get(false_index..)?,
                        local,
                        body,
                        previous,
                        root.id,
                        root.id
                            .checked_add(u32::try_from(false_index).ok()?)?,
                        depth.checked_add(1)?,
                        source,
                    )?;
                if input.is_some() || !outputs.is_empty() {
                    return None;
                }
                (width, spelling)
            };
            (
                false_index.checked_add(false_width)?,
                format!("{condition} ? {true_spelling} : {false_spelling}"),
                None,
                Vec::new(),
            )
        },
        "binary-expression" if root.reference.is_none() => {
            let (operator, value) =
                byte_identity_operator(root.operation.as_deref())?;
            let (left_width, left, input, outputs) =
                prove_byte_identity_expression(
                    nodes.get(1..)?,
                    local,
                    body,
                    previous,
                    root.id,
                    root.id.checked_add(1)?,
                    depth.checked_add(1)?,
                    source,
                )?;
            let literal = nodes.get(left_width.checked_add(1)?)?;
            if literal.id
                != root
                    .id
                    .checked_add(u32::try_from(left_width).ok()?)?
                    .checked_add(1)?
                || literal.parent != root.id
                || literal.kind != "integer-literal"
                || literal.type_name.as_deref() != Some("i32")
                || literal.reference.is_some()
                || literal.operation.is_some()
                || literal.name.is_some()
                || literal.definition.is_some()
                || literal.inline_specified.is_some()
                || literal.linkage.is_some()
                || literal.storage_class.is_some()
                || literal.storage_duration.is_some()
                || literal.literal.as_deref() != Some(value)
                || literal.constant_integer.as_deref() != Some(value)
            {
                return None;
            }
            let literal_start = root.span.begin.byte.checked_add(
                u32::try_from(
                    left.len().checked_add(operator.len())?.checked_add(2)?,
                )
                .ok()?,
            )?;
            if !source_word(
                literal,
                literal_start,
                literal_start.checked_add(u32::try_from(value.len()).ok()?)?,
                root.span.begin.line,
                root.span.begin.column.checked_add(
                    literal_start.checked_sub(root.span.begin.byte)?,
                )?,
            ) {
                return None;
            }
            (
                left_width.checked_add(2)?,
                format!("{left} {operator} {value}"),
                input,
                outputs,
            )
        },
        _ => return None,
    };
    if spelling.len() > MAX_BYTE_IDENTITY_LENGTH {
        return None;
    }
    let start = root.span.begin.byte;
    let end = start.checked_add(u32::try_from(spelling.len()).ok()?)?;
    let source_start = usize::try_from(start).ok()?;
    let source_end = usize::try_from(end).ok()?;
    (source_word(
        root,
        start,
        end,
        root.span.begin.line,
        root.span.begin.column,
    ) && source.get(source_start..source_end) == Some(spelling.as_bytes()))
    .then_some((width, spelling, input, outputs))
}

// The call itself is checked separately from the recursive C expression:
// all argument nodes must belong to this output, and no unproven output or
// input can be hidden between its callee and the successful-byte expression.
#[expect(
    clippy::too_many_arguments,
    reason = "source proof requires independent Clang and call coordinates"
)]
fn prove_identity_byte_output<'node>(
    nodes: &'node [Node],
    body: &Node,
    local: Option<&LocalDeclaration<'_>>,
    expected_id: u32,
    previous: u32,
    parent: u32,
    source: &[u8],
    active_domain: Option<&[bool; 256]>,
) -> Option<(usize, &'node Node, Option<&'node Node>, Vec<&'node Node>)> {
    let [output, callee_cast, callee, rest @ ..] = nodes else {
        return None;
    };
    let (expression_width, argument, input, outputs) =
        prove_byte_identity_expression(
            rest,
            local,
            body,
            previous,
            output.id,
            output.id.checked_add(3)?,
            0,
            source,
        )
        .or_else(|| {
            // A standalone putchar converts its int argument to an unsigned
            // char. Authenticate the entire pure C expression and preserve
            // the resident byte only if every successful stdin value emits
            // that same byte after the conversion. Do not use this for
            // nested calls, assignments or EOF-dependent control flow.
            let bound = local?;
            let (width, argument, values) = prove_total_byte_guard(
                rest,
                body,
                previous,
                output.id,
                output.id.checked_add(3)?,
                Some(bound),
                0,
                source,
            )?;
            values
                .iter()
                .enumerate()
                .all(|(byte, value)| {
                    // Require defined C arithmetic on all 256 successful
                    // guest bytes, and byte identity on the active branch.
                    let same_byte = value.is_some_and(|actual| {
                        i32::try_from(byte).ok() == Some(actual.rem_euclid(256))
                    });
                    value.is_some()
                        && active_domain.map_or(same_byte, |active| {
                            !active[byte] || same_byte
                        })
                })
                .then_some((width, argument, None, Vec::new()))
        })?;
    let start = output.span.begin.byte;
    let line = output.span.begin.line;
    let column = output.span.begin.column;
    let end = start
        .checked_add(u32::try_from(argument.len()).ok()?)?
        .checked_add(9)?;
    let spelling = format!("putchar({argument})");
    if start <= previous
        || local.is_some_and(|local| {
            start <= local.declaration_end || line <= local.line
        })
        || end >= body.span.end.byte
        || source.get(usize::try_from(start).ok()?..usize::try_from(end).ok()?)
            != Some(spelling.as_bytes())
        || output.id != expected_id
        || output.parent != parent
        || output.kind != "call-expression"
        || output.type_name.as_deref() != Some("i32")
        || output.reference.as_deref() != Some("external:putchar")
        || output.operation.is_some()
        || !metadata_empty(output)
        || !source_word(output, start, end, line, column)
        || callee_cast.id != output.id.checked_add(1)?
        || callee_cast.parent != output.id
        || callee_cast.kind != "cast-expression"
        || callee_cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
        || callee_cast.operation.as_deref() != Some("function-to-pointer")
        || callee_cast.reference.is_some()
        || !metadata_empty(callee_cast)
        || !source_word(callee_cast, start, start.checked_add(7)?, line, column)
        || callee.id != callee_cast.id.checked_add(1)?
        || callee.parent != callee_cast.id
        || callee.kind != "declaration-reference-expression"
        || callee.type_name.as_deref() != Some("fn(i32)->i32")
        || callee.reference.as_deref() != Some("external:putchar")
        || callee.operation.is_some()
        || !metadata_empty(callee)
        || !source_word(callee, start, start.checked_add(7)?, line, column)
    {
        return None;
    }
    Some((expression_width.checked_add(3)?, output, input, outputs))
}

// The local-only output path may borrow the existing guest accumulator but
// must never silently discard fresh input or nested output effects.
#[expect(
    clippy::too_many_arguments,
    reason = "source proof requires independent Clang and call coordinates"
)]
fn prove_identity_binary_local_output<'node>(
    nodes: &'node [Node],
    body: &Node,
    local: &LocalDeclaration<'_>,
    expected_id: u32,
    previous: u32,
    parent: u32,
    source: &[u8],
) -> Option<(usize, &'node Node)> {
    let (width, call, input, outputs) = prove_identity_byte_output(
        nodes,
        body,
        Some(local),
        expected_id,
        previous,
        parent,
        source,
        None,
    )?;
    (input.is_none() && outputs.is_empty()).then_some((width, call))
}

#[expect(
    clippy::too_many_lines,
    reason = "check nested source coordinates and ancestry together"
)]
fn prove_nested_local_output<'node>(
    nodes: &'node [Node],
    body: &Node,
    local: &LocalDeclaration<'_>,
    expected_id: u32,
    previous: u32,
    first_parent: u32,
) -> Option<OutputCallProof<'node>> {
    let outer = nodes.first()?;
    let start = outer.span.begin.byte;
    let line = outer.span.begin.line;
    let column = outer.span.begin.column;
    if start <= previous
        || start <= local.declaration_end
        || line <= local.line
        || start <= body.span.begin.byte
        || line == 0
        || column == 0
    {
        return None;
    }
    let depth = (0..MAX_NESTED_LOCAL_DEPTH)
        .take_while(|level| {
            nodes.get(level.saturating_mul(3)).is_some_and(|node| {
                node.kind == "call-expression"
                    && node.reference.as_deref() == Some("external:putchar")
            })
        })
        .count();
    if depth < 2 {
        return None;
    }
    let depth_u32 = u32::try_from(depth).ok()?;
    let name_len = u32::try_from(local.name.len()).ok()?;
    let argument_start = start.checked_add(depth_u32.checked_mul(8)?)?;
    let argument_end = argument_start.checked_add(name_len)?;
    let output_end = argument_end.checked_add(depth_u32)?;
    if output_end >= body.span.end.byte {
        return None;
    }
    let mut calls = Vec::with_capacity(depth);
    let mut parent = first_parent;
    for level in 0..depth {
        let offset = level.checked_mul(3)?;
        let [call, cast, reference] =
            nodes.get(offset..offset.checked_add(3)?)?
        else {
            return None;
        };
        let level_u32 = u32::try_from(level).ok()?;
        let call_start = start.checked_add(level_u32.checked_mul(8)?)?;
        let call_end = output_end.checked_sub(level_u32)?;
        let call_column = column.checked_add(level_u32.checked_mul(8)?)?;
        if call.id != expected_id.checked_add(u32::try_from(offset).ok()?)?
            || call.parent != parent
            || call.kind != "call-expression"
            || call.type_name.as_deref() != Some("i32")
            || call.reference.as_deref() != Some("external:putchar")
            || call.operation.is_some()
            || !metadata_empty(call)
            || !source_word(call, call_start, call_end, line, call_column)
            || cast.id != call.id.checked_add(1)?
            || cast.parent != call.id
            || cast.kind != "cast-expression"
            || cast.type_name.as_deref() != Some("ptr(fn(i32)->i32)")
            || cast.operation.as_deref() != Some("function-to-pointer")
            || cast.reference.is_some()
            || !metadata_empty(cast)
            || !source_word(
                cast,
                call_start,
                call_start.checked_add(7)?,
                line,
                call_column,
            )
            || reference.id != cast.id.checked_add(1)?
            || reference.parent != cast.id
            || reference.kind != "declaration-reference-expression"
            || reference.type_name.as_deref() != Some("fn(i32)->i32")
            || reference.reference.as_deref() != Some("external:putchar")
            || reference.operation.is_some()
            || !metadata_empty(reference)
            || !source_word(
                reference,
                call_start,
                call_start.checked_add(7)?,
                line,
                call_column,
            )
        {
            return None;
        }
        calls.push(call);
        parent = call.id;
    }
    let offset = depth.checked_mul(3)?;
    let [value_cast, value_reference] =
        nodes.get(offset..offset.checked_add(2)?)?
    else {
        return None;
    };
    let argument_column = column.checked_add(depth_u32.checked_mul(8)?)?;
    if value_cast.id != expected_id.checked_add(u32::try_from(offset).ok()?)?
        || value_cast.parent != parent
        || value_cast.kind != "cast-expression"
        || value_cast.type_name.as_deref() != Some("i32")
        || value_cast.operation.as_deref() != Some("lvalue-to-rvalue")
        || value_cast.reference.is_some()
        || !metadata_empty(value_cast)
        || !source_word(
            value_cast,
            argument_start,
            argument_end,
            line,
            argument_column,
        )
        || value_reference.id != value_cast.id.checked_add(1)?
        || value_reference.parent != value_cast.id
        || value_reference.kind != "declaration-reference-expression"
        || value_reference.type_name.as_deref() != Some("i32")
        || value_reference.reference.as_deref()
            != Some(local.variable_reference.as_str())
        || value_reference.operation.is_some()
        || !metadata_empty(value_reference)
        || !source_word(
            value_reference,
            argument_start,
            argument_end,
            line,
            argument_column,
        )
    {
        return None;
    }
    Some((offset.checked_add(2)?, calls))
}

fn prove_local_output_chain<'node>(
    nodes: &'node [Node],
    body: &Node,
    local: &LocalDeclaration<'_>,
    expected_id: u32,
    previous: u32,
    parent: u32,
    source: Option<&[u8]>,
) -> Option<OutputCallProof<'node>> {
    if let Some(first) = nodes.get(..5)
        && let Some(call) = prove_local_output(
            first,
            body,
            local,
            expected_id,
            previous,
            parent,
        )
    {
        return Some((5, vec![call]));
    }
    if let Some(first) = nodes.get(..7)
        && let Some(call) = prove_unsigned_cast_local_output(
            first,
            body,
            local,
            expected_id,
            previous,
            parent,
        )
    {
        return Some((7, vec![call]));
    }
    if let Some(source) = source
        && let Some((width, call)) = prove_identity_binary_local_output(
            nodes,
            body,
            local,
            expected_id,
            previous,
            parent,
            source,
        )
    {
        return Some((width, vec![call]));
    }
    prove_nested_local_output(nodes, body, local, expected_id, previous, parent)
}

// A constant arm can contain several ordered, independently authenticated
// byte effects. A successful read invalidates any preceding guest-local alias.
#[derive(Clone, Copy)]
struct StaticCounter<'name> {
    reference: &'name str,
    name: &'name str,
    unsigned: bool,
    value: i32,
}

#[derive(Clone, Copy)]
struct StaticInduction<'name> {
    reference: &'name str,
    name: &'name str,
    source: Option<&'name [u8]>,
    unsigned: bool,
    value: i32,
    // Source-proven enclosing scopes, nearest first, never guest stdin.
    outer: Option<StaticCounter<'name>>,
    outermost: Option<StaticCounter<'name>>,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum StaticLoopExit {
    Break,
    Continue,
    Return,
}

#[derive(Clone)]
struct StaticIfEffect<'node> {
    input: Option<&'node Node>,
    // A proven assignment targets this source C local. A call or a scoped
    // declaration has no outer-scope identity after the enclosing branch.
    assigned_local: Option<String>,
    // Outer-to-inner Clang preorder; reverse to emit successful call returns.
    outputs: Vec<&'node Node>,
    // Return propagates to the function; break/continue stop at the inner
    // loop.
    loop_exit: Option<StaticLoopExit>,
}

struct StaticIfArm<'node> {
    width: usize,
    effects: Vec<StaticIfEffect<'node>>,
    begin: u32,
    begin_line: u32,
    begin_column: u32,
    end: u32,
    end_line: u32,
    end_column: u32,
    braced: bool,
}

// Both discarded comma statements and comma-argument calls use the same
// verified operand trace. Only the latter adds one final outer output.
fn static_comma_effects<'node>(
    comma_effects: Vec<CommaEffect<'node>>,
    outer_output: Option<&'node Node>,
    local: Option<&LocalDeclaration<'node>>,
) -> Option<Vec<StaticIfEffect<'node>>> {
    let last = comma_effects.len().checked_sub(1)?;
    Some(
        comma_effects
            .into_iter()
            .enumerate()
            .map(|(index, effect)| {
                let input = (!effect.reads_local).then_some(effect.input);
                let assigned_local = local
                    .filter(|_| effect.assigns_local)
                    .map(|declaration| declaration.variable_reference.clone());
                let mut outputs = effect.outputs;
                if index == last
                    && let Some(output) = outer_output
                {
                    outputs.insert(0, output);
                }
                StaticIfEffect {
                    input,
                    assigned_local,
                    outputs,
                    loop_exit: None,
                }
            })
            .collect(),
    )
}

// Borrowed C storage is represented by exactly one resident guest byte.
// A discarded input may overwrite that byte temporarily, but a later output
// of the outer local needs a proven rebind first. Check the ordered, already
// source-authenticated effect trace, not just each input in isolation.
fn outer_loop_byte_after_effects(
    effects: &[StaticIfEffect<'_>],
    reference: &str,
    mut available: bool,
) -> Option<bool> {
    for effect in effects {
        if effect.input.is_some() {
            available = effect.assigned_local.as_deref() == Some(reference);
        } else if !available && !effect.outputs.is_empty() {
            return None;
        }
    }
    Some(available)
}

// A switch over the resident byte needs no guest branch if both source
// arms write that byte on their own reachable case domains. This narrow
// grammar requires exactly one integer case and a default, each with one
// source-proven putchar and an explicit break. No switch fallthrough, extra
// effects, or sampled guest values can disappear from the accepted trace.
#[expect(
    clippy::too_many_lines,
    reason = "authenticate the complete case/default AST and original source"
)]
fn prove_guarded_byte_switch<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    parent: u32,
    local: Option<&LocalDeclaration<'node>>,
    source: Option<&[u8]>,
) -> Option<(usize, Vec<StaticIfEffect<'node>>, u32)> {
    let source = source?;
    let local = local?;
    let switch = nodes.first()?;
    let start = switch.span.begin.byte;
    let line = switch.span.begin.line;
    let column = switch.span.begin.column;
    if start <= previous
        || start <= body.span.begin.byte
        || switch.span.end.byte >= body.span.end.byte
        || switch.id != expected_id
        || switch.parent != parent
        || switch.kind != "switch-statement"
        || switch.type_name.is_some()
        || switch.operation.is_some()
        || switch.reference.is_some()
        || !metadata_empty(switch)
        || line == 0
        || column == 0
    {
        return None;
    }
    let (condition_width, condition, values) = prove_total_byte_guard(
        nodes.get(1..)?,
        body,
        previous,
        switch.id,
        switch.id.checked_add(1)?,
        Some(local),
        0,
        source,
    )?;
    if values.iter().any(Option::is_none) {
        return None;
    }
    let scope_index = condition_width.checked_add(1)?;
    let scope = nodes.get(scope_index)?;
    let case = nodes.get(scope_index.checked_add(1)?)?;
    let constant = nodes.get(scope_index.checked_add(2)?)?;
    let literal = nodes.get(scope_index.checked_add(3)?)?;
    let (case_value, case_token) = source_proven_byte_guard_literal(
        literal,
        constant.id.checked_add(1)?,
        constant.id,
        source,
    )?;
    // The accepted case must be a real single C integer label; a forged
    // Clang ConstantExpr cannot redirect guest effects.
    if case_value > 255
        || scope.id
            != switch.id.checked_add(u32::try_from(scope_index).ok()?)?
        || scope.parent != switch.id
        || scope.kind != "compound-statement"
        || scope.type_name.is_some()
        || scope.operation.is_some()
        || scope.reference.is_some()
        || !metadata_empty(scope)
        || scope.span.end != switch.span.end
        || case.id != scope.id.checked_add(1)?
        || case.parent != scope.id
        || case.kind != "case-statement"
        || case.type_name.is_some()
        || case.operation.is_some()
        || case.reference.is_some()
        || !metadata_empty(case)
        || constant.id != case.id.checked_add(1)?
        || constant.parent != case.id
        || constant.kind != "constant-expression"
        || constant.type_name.as_deref() != Some("i32")
        || constant.operation.is_some()
        || constant.reference.is_some()
        || !metadata_except_integer_constant_empty(constant)
        || constant.constant_integer.as_deref()
            != Some(case_value.to_string().as_str())
        || constant.span != literal.span
    {
        return None;
    }
    let mut case_domain = [false; 256];
    let mut default_domain = [false; 256];
    for (byte, result) in values.iter().enumerate() {
        let selected = *result == Some(case_value);
        case_domain[byte] = selected;
        default_domain[byte] = !selected;
    }
    let call_index = scope_index.checked_add(4)?;
    let (case_width, case_call, None, case_nested) =
        prove_identity_byte_output(
            nodes.get(call_index..)?,
            body,
            Some(local),
            switch.id.checked_add(u32::try_from(call_index).ok()?)?,
            case.span.begin.byte,
            case.id,
            source,
            Some(&case_domain),
        )?
    else {
        return None;
    };
    if !case_nested.is_empty() || case.span.end != case_call.span.end {
        return None;
    }
    let case_break_index = call_index.checked_add(case_width)?;
    let case_break = nodes.get(case_break_index)?;
    let default_index = case_break_index.checked_add(1)?;
    let default = nodes.get(default_index)?;
    let default_call_index = default_index.checked_add(1)?;
    let (default_width, default_call, None, default_nested) =
        prove_identity_byte_output(
            nodes.get(default_call_index..)?,
            body,
            Some(local),
            switch
                .id
                .checked_add(u32::try_from(default_call_index).ok()?)?,
            default.span.begin.byte,
            default.id,
            source,
            Some(&default_domain),
        )?
    else {
        return None;
    };
    let default_break_index = default_call_index.checked_add(default_width)?;
    let default_break = nodes.get(default_break_index)?;
    let end_index = default_break_index.checked_add(1)?;
    if !default_nested.is_empty()
        || default.span.end != default_call.span.end
        || default.id
            != switch.id.checked_add(u32::try_from(default_index).ok()?)?
        || default.parent != scope.id
        || default.kind != "default-statement"
        || default.type_name.is_some()
        || default.operation.is_some()
        || default.reference.is_some()
        || !metadata_empty(default)
    {
        return None;
    }
    for (index, jump) in [
        (case_break_index, case_break),
        (default_break_index, default_break),
    ] {
        if jump.id != switch.id.checked_add(u32::try_from(index).ok()?)?
            || jump.parent != scope.id
            || jump.kind != "break-statement"
            || jump.type_name.is_some()
            || jump.operation.is_some()
            || jump.reference.is_some()
            || !metadata_empty(jump)
            || jump.span.end.byte != jump.span.begin.byte.checked_add(5)?
        {
            return None;
        }
    }

    // Verify every byte between the switch keyword and its closing brace.
    // The original source must have exactly these labels, calls and breaks.
    // This also verifies Clang's node positions and prohibits hidden code.
    let indent = usize::try_from(column.checked_sub(1)?).ok()?;
    if indent > 128
        || switch.span.begin.line != case.span.begin.line.checked_sub(1)?
        || switch.span.begin.line != scope.span.begin.line
        || scope.span.begin.column
            != column.checked_add(
                u32::try_from("switch (".len() + condition.len() + ") ".len())
                    .ok()?,
            )?
    {
        return None;
    }
    let extract_call = |node: &Node| -> Option<&str> {
        str::from_utf8(source.get(
            usize::try_from(node.span.begin.byte).ok()?
                ..usize::try_from(node.span.end.byte).ok()?,
        )?)
        .ok()
    };
    let case_text = extract_call(case_call)?;
    let default_text = extract_call(default_call)?;
    let label_indent = " ".repeat(indent);
    let statement_indent = " ".repeat(indent.checked_add(4)?);
    let expected = format!(
        "switch ({condition}) {{\n{label_indent}case {case_token}:\n\
         {statement_indent}{case_text};\n{statement_indent}break;\n\
         {label_indent}default:\n{statement_indent}{default_text};\n\
         {statement_indent}break;\n{label_indent}}}"
    );
    let end = switch.span.end.byte;
    // A forged preorder can keep the bytes unchanged but move a case label
    // or a break's source location. Authenticate those positions too.
    let relative = |needle: &str| expected.find(needle);
    let source_position =
        |offset: usize| start.checked_add(u32::try_from(offset).ok()?);
    let case_at = source_position(relative("case ")?)?;
    let default_at = source_position(relative("default:")?)?;
    let scope_at = source_position(relative("{")?)?;
    let first_call_at = source_position(
        relative("case ")?.checked_add(
            expected
                .get(relative("case ")?..relative("default:")?)?
                .find(case_text)?,
        )?,
    )?;
    let second_call_at = source_position(relative("default:")?.checked_add(
        expected.get(relative("default:")?..)?.find(default_text)?,
    )?)?;
    let mut breaks = expected.match_indices("break;").map(|(at, _)| at);
    let first_break_at = source_position(breaks.next()?)?;
    let second_break_at = source_position(breaks.next()?)?;
    if breaks.next().is_some()
        || scope.span.begin.byte != scope_at
        || case.span.begin.byte != case_at
        || default.span.begin.byte != default_at
        || case_call.span.begin.byte != first_call_at
        || default_call.span.begin.byte != second_call_at
        || literal.span.begin.byte != case_at.checked_add(5)?
        || literal.span.begin.line != line.checked_add(1)?
        || literal.span.begin.column != column.checked_add(5)?
        || !source_word(
            case_break,
            first_break_at,
            first_break_at.checked_add(5)?,
            line.checked_add(3)?,
            column.checked_add(4)?,
        )
        || !source_word(
            default_break,
            second_break_at,
            second_break_at.checked_add(5)?,
            line.checked_add(6)?,
            column.checked_add(4)?,
        )
        || default.span.begin.line != line.checked_add(4)?
        || case_call.span.begin.line != line.checked_add(2)?
        || default_call.span.begin.line != line.checked_add(5)?
        || source.get(usize::try_from(start).ok()?..usize::try_from(end).ok()?)
            != Some(expected.as_bytes())
        || source.get(usize::try_from(case_break.span.end.byte).ok()?)
            != Some(&b';')
        || source.get(usize::try_from(default_break.span.end.byte).ok()?)
            != Some(&b';')
        || switch.span.end.line != default_break.span.end.line.checked_add(1)?
        || switch.span.end.column != column.checked_add(1)?
        || case.span.begin.column != column
        || default.span.begin.column != column
        || case_call.span.begin.column != column.checked_add(4)?
        || default_call.span.begin.column != column.checked_add(4)?
    {
        return None;
    }
    Some((
        end_index,
        vec![StaticIfEffect {
            input: None,
            assigned_local: None,
            outputs: vec![case_call],
            loop_exit: None,
        }],
        end,
    ))
}

fn prove_static_if_statement<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    parent: u32,
    local: Option<&LocalDeclaration<'node>>,
    outer_aliases: &[LocalDeclaration<'node>],
    depth: usize,
    allow_new_local: bool,
    for_depth: usize,
    induction: Option<StaticInduction<'_>>,
    source: Option<&[u8]>,
) -> Option<(usize, Vec<StaticIfEffect<'node>>, u32)> {
    let child = nodes.first()?;
    if child.kind == "for-statement" {
        if for_depth >= MAX_STATIC_FOR_DEPTH {
            return None;
        }
        let proof = prove_static_for(
            nodes,
            body,
            previous,
            expected_id,
            parent,
            None,
            &[],
            for_depth.checked_add(1)?,
            induction,
            source,
        )
        .or_else(|| {
            // Only an input-free loop can safely reuse a byte bound before
            // the loop. A fresh read in one trip would make it stale in the
            // next trip; do not project that lost C storage into the guest.
            let live = local?;
            let witness = source?;
            let proof = prove_static_for(
                nodes,
                body,
                previous,
                expected_id,
                parent,
                Some(live),
                outer_aliases,
                for_depth.checked_add(1)?,
                induction,
                source,
            )?;
            (outer_loop_byte_after_effects(
                &proof.effects,
                &live.variable_reference,
                true,
            )
            .is_some()
                && source_identifiers_match(nodes.get(..proof.width)?, witness))
            .then_some(proof)
        })?;
        if proof.effects.len() > 16 {
            return None;
        }
        return Some((proof.width, proof.effects, proof.end));
    }
    if matches!(
        child.kind.as_str(),
        "break-statement" | "continue-statement" | "return-statement"
    ) {
        // The semicolon lies outside the Clang keyword extent. Only a
        // void `return;` can terminate the containing function from any depth.
        let (keyword, exit) = match child.kind.as_str() {
            "break-statement" => ("break", StaticLoopExit::Break),
            "continue-statement" => ("continue", StaticLoopExit::Continue),
            "return-statement" => ("return", StaticLoopExit::Return),
            _ => return None,
        };
        let start = child.span.begin.byte;
        let end = start.checked_add(u32::try_from(keyword.len()).ok()?)?;
        // A same-width C statement may be effect-free even if an untrusted
        // Clang JSON node claims it is a control-flow exit. With a source
        // witness, authenticate the actual keyword before selecting an exit.
        let source_keyword_matches = source.is_none_or(|witness| {
            usize::try_from(start).ok().and_then(|begin| {
                witness.get(begin..begin.checked_add(keyword.len())?)
            }) == Some(keyword.as_bytes())
        });
        if !source_keyword_matches
            || (for_depth == 0 && exit != StaticLoopExit::Return)
            || start <= previous
            || end >= body.span.end.byte
            || child.id != expected_id
            || child.parent != parent
            || child.type_name.is_some()
            || child.reference.is_some()
            || child.operation.is_some()
            || !metadata_empty(child)
            || !source_word(
                child,
                start,
                end,
                child.span.begin.line,
                child.span.begin.column,
            )
        {
            return None;
        }
        return Some((
            1,
            vec![StaticIfEffect {
                input: None,
                assigned_local: None,
                outputs: Vec::new(),
                loop_exit: Some(exit),
            }],
            end,
        ));
    }
    if child.kind == "switch-statement" {
        return prove_guarded_byte_switch(
            nodes,
            body,
            previous,
            expected_id,
            parent,
            local,
            source,
        );
    }
    if child.kind == "if-statement" {
        let proof = prove_static_if(
            nodes,
            body,
            previous,
            expected_id,
            parent,
            local,
            outer_aliases,
            depth.checked_add(1)?,
            allow_new_local,
            for_depth,
            induction,
            None,
            source,
        )?;
        return Some((
            proof.width,
            if proof.selected {
                proof.effects
            } else {
                Vec::new()
            },
            proof.end,
        ));
    }
    // A normal five-node putchar(local) can be the final statement in an
    // arm. Missing assignment nodes must fall through to its own proof.
    if child.kind == "call-expression"
        && child.reference.as_deref() == Some("external:putchar")
        && let Some(local) = local
        && let Some(candidate) = nodes.get(..8)
        && let Some(witness) = source
        && let Some((read, output)) = prove_output_input_assignment(
            candidate,
            (body, previous, parent),
            local,
            witness,
            b';',
        )
    {
        return (child.id == expected_id).then_some((
            8,
            vec![StaticIfEffect {
                input: Some(read),
                assigned_local: Some(local.variable_reference.clone()),
                outputs: vec![output],
                loop_exit: None,
            }],
            output.span.end.byte,
        ));
    }
    if child.kind == "call-expression"
        && child.reference.as_deref() == Some("external:putchar")
        && let Some(local) = local
        && let Some(witness) = source
        && let Some((width, read, outputs)) =
            prove_wrapped_output_return_reassignment(
                nodes,
                (body, previous, parent),
                local,
                witness,
            )
            .or_else(|| {
                prove_nested_output_input_assignment(
                    nodes,
                    (body, previous, parent),
                    local,
                    witness,
                )
            })
    {
        let end = outputs.first()?.span.end.byte;
        return (child.id == expected_id).then_some((
            width,
            vec![StaticIfEffect {
                input: Some(read),
                assigned_local: Some(local.variable_reference.clone()),
                outputs,
                loop_exit: None,
            }],
            end,
        ));
    }
    if child.kind == "call-expression"
        && child.reference.as_deref() == Some("external:putchar")
        && let Some(bound) = local
        && let Some(witness) = source
        && let Some((read, output)) = prove_comma_assigned_output(
            nodes,
            (body, previous, parent),
            bound,
            witness,
        )
    {
        return (child.id == expected_id).then_some((
            12,
            vec![StaticIfEffect {
                input: Some(read),
                assigned_local: Some(bound.variable_reference.clone()),
                outputs: vec![output],
                loop_exit: None,
            }],
            output.span.end.byte,
        ));
    }
    // Authenticate a complete comma argument in the same branch parent as
    // ordinary calls; materialize each operand in C evaluation order.
    let comma_proof = if child.kind == "call-expression"
        && child.reference.as_deref() == Some("external:putchar")
    {
        prove_comma_output_effects(
            nodes,
            body,
            previous,
            expected_id,
            parent,
            local,
            source,
        )
    } else {
        None
    };
    if let Some((width, comma_effects, output)) = comma_proof {
        let effects = static_comma_effects(comma_effects, Some(output), local)?;
        return Some((width, effects, output.span.end.byte));
    }
    // The final read of a proven comma assignment rebinds this C local.
    // Earlier comma reads/writes still occur, but cannot export an old alias.
    if child.kind == "binary-expression"
        && child.operation.as_deref() == Some("=")
        && let Some(bound) = local
        && let Some(witness) = source
        && let Some((width, effects, end)) = prove_comma_local_reassignment(
            nodes,
            (body, previous, parent),
            bound,
            witness,
        )
    {
        let mut ordered = static_comma_effects(effects, None, None)?;
        ordered.last_mut()?.assigned_local =
            Some(bound.variable_reference.clone());
        return (child.id == expected_id).then_some((width, ordered, end));
    }
    if child.kind == "binary-expression"
        && child.operation.as_deref() == Some("=")
        && let Some(bound) = local
        && let Some(witness) = source
        && let Some((width, read, outputs)) = prove_output_return_reassignment(
            nodes,
            (body, previous, parent),
            bound,
            witness,
            b';',
        )
    {
        return (child.id == expected_id).then_some((
            width,
            vec![StaticIfEffect {
                input: Some(read),
                assigned_local: Some(bound.variable_reference.clone()),
                outputs,
                loop_exit: None,
            }],
            child.span.end.byte,
        ));
    }
    if child.kind == "binary-expression"
        && child.operation.as_deref() == Some("=")
    {
        let read = prove_local_input_reassignment(
            nodes.get(..5)?,
            (body, previous, parent),
            local?,
            source?,
            b';',
        )?;
        return (child.id == expected_id).then_some((
            5,
            vec![StaticIfEffect {
                input: Some(read),
                assigned_local: Some(local?.variable_reference.clone()),
                outputs: Vec::new(),
                loop_exit: None,
            }],
            child.span.end.byte,
        ));
    }
    if child.kind == "binary-expression" {
        let (width, comma_effects, end) = prove_discarded_comma_effects(
            nodes,
            body,
            previous,
            expected_id,
            parent,
            local,
            source,
        )?;
        return Some((
            width,
            static_comma_effects(comma_effects, None, local)?,
            end,
        ));
    }
    let (width, input, outputs) = if child.kind == "call-expression"
        && child.reference.as_deref() == Some("external:putchar")
    {
        if let Some(local) = local
            && let Some((width, calls)) = prove_local_output_chain(
                nodes,
                body,
                local,
                expected_id,
                previous,
                parent,
                source,
            )
        {
            (width, None, calls)
        } else {
            let (width, input, calls) =
                super::nested_byte_echo::nested_call_in_parent(
                    nodes,
                    body,
                    previous,
                    expected_id,
                    parent,
                )?;
            (width, Some(input), calls)
        }
    } else {
        let read = prove_input_call(
            nodes.get(..3)?,
            body,
            previous,
            (expected_id, parent),
        )?;
        (3, Some(read), Vec::new())
    };
    let end = outputs.first().copied().or(input)?.span.end.byte;
    (child.id == expected_id).then_some((
        width,
        vec![StaticIfEffect {
            input,
            assigned_local: None,
            outputs,
            loop_exit: None,
        }],
        end,
    ))
}

// An unreachable pure output expression remains a source-C effect. Prove
// every operand against the pinned Clang tree and original source bytes, and
// reject any undefined arithmetic over the successful guest-byte domain.
// Only a separately proven unreachable arm may drop the call; no guest
// arithmetic is evaluated or substituted for a reachable output.
fn prove_unreachable_pure_output(
    nodes: &[Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    parent: u32,
    local: Option<&LocalDeclaration<'_>>,
    source: &[u8],
) -> Option<(usize, u32)> {
    let [call, cast, callee, argument, ..] = nodes else {
        return None;
    };
    let start = call.span.begin.byte;
    let line = call.span.begin.line;
    let column = call.span.begin.column;
    let (argument_width, expression, values) = prove_total_byte_guard(
        nodes.get(3..)?,
        body,
        previous,
        call.id,
        expected_id.checked_add(3)?,
        local,
        0,
        source,
    )?;
    values.iter().all(Option::is_some).then_some(())?;
    let spelling = format!("putchar({expression});");
    let end = start
        .checked_add(u32::try_from(spelling.len().checked_sub(1)?).ok()?)?;
    let from = usize::try_from(start).ok()?;
    let to = from.checked_add(spelling.len())?;
    (start > previous
        && start > body.span.begin.byte
        && end < body.span.end.byte
        && source.get(from..to) == Some(spelling.as_bytes())
        && call.id == expected_id
        && call.parent == parent
        && call.kind == "call-expression"
        && call.type_name.as_deref() == Some("i32")
        && call.reference.as_deref() == Some("external:putchar")
        && call.operation.is_none()
        && metadata_empty(call)
        && source_word(call, start, end, line, column)
        && cast.id == expected_id.checked_add(1)?
        && cast.parent == call.id
        && cast.kind == "cast-expression"
        && cast.type_name.as_deref() == Some("ptr(fn(i32)->i32)")
        && cast.operation.as_deref() == Some("function-to-pointer")
        && cast.reference.is_none()
        && metadata_empty(cast)
        && source_word(cast, start, start.checked_add(7)?, line, column)
        && callee.id == expected_id.checked_add(2)?
        && callee.parent == cast.id
        && callee.kind == "declaration-reference-expression"
        && callee.type_name.as_deref() == Some("fn(i32)->i32")
        && callee.reference.as_deref() == Some("external:putchar")
        && callee.operation.is_none()
        && metadata_empty(callee)
        && argument.id == expected_id.checked_add(3)?
        && argument.parent == call.id
        && argument.type_name.as_deref() == Some("i32")
        && source_word(callee, start, start.checked_add(7)?, line, column)
        && source_word(
            argument,
            start.checked_add(8)?,
            end.checked_sub(1)?,
            line,
            column.checked_add(8)?,
        ))
    .then_some((3usize.checked_add(argument_width)?, end))
}

// Source-authenticate both one-line and canonical one-statement-per-line
// compound arms, including the unselected branch. Each effect must have an
// exact byte gap, line, column, ID and parent; no other C statement is erased.
fn prove_static_if_arm<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    parent: u32,
    local: Option<&LocalDeclaration<'node>>,
    outer_aliases: &[LocalDeclaration<'node>],
    depth: usize,
    conditional_column: u32,
    allow_new_local: bool,
    for_depth: usize,
    induction: Option<StaticInduction<'_>>,
    allow_unreachable_pure: bool,
    active_domain: Option<&[bool; 256]>,
    source: Option<&[u8]>,
) -> Option<StaticIfArm<'node>> {
    let child = nodes.first()?;
    if child.kind == "if-statement" {
        let proof = prove_static_if(
            nodes,
            body,
            previous,
            expected_id,
            parent,
            local,
            outer_aliases,
            depth.checked_add(1)?,
            allow_new_local,
            for_depth,
            induction,
            active_domain,
            source,
        )?;
        return Some(StaticIfArm {
            width: proof.width,
            effects: if proof.selected {
                proof.effects
            } else {
                Vec::new()
            },
            begin: child.span.begin.byte,
            begin_line: child.span.begin.line,
            begin_column: child.span.begin.column,
            end: proof.end,
            end_line: child.span.end.line,
            end_column: child.span.end.column,
            braced: false,
        });
    }
    if child.kind != "compound-statement" {
        // A C if arm need not contain braces. Prove the exact call and its
        // signed arithmetic under this source-authenticated byte domain;
        // neither the predicate nor the output may sample stdin at compile
        // time. Other direct statement forms retain their existing proofs.
        if child.kind == "call-expression"
            && let Some(domain) = active_domain
            && let Some(bound) = local
            && let Some(witness) = source
            && let Some((width, call, None, nested)) =
                prove_identity_byte_output(
                    nodes,
                    body,
                    Some(bound),
                    expected_id,
                    previous,
                    parent,
                    witness,
                    Some(domain),
                )
            && nested.is_empty()
            && witness.get(usize::try_from(call.span.end.byte).ok()?)
                == Some(&b';')
        {
            return Some(StaticIfArm {
                width,
                effects: vec![StaticIfEffect {
                    input: None,
                    assigned_local: None,
                    outputs: vec![call],
                    loop_exit: None,
                }],
                begin: child.span.begin.byte,
                begin_line: child.span.begin.line,
                begin_column: child.span.begin.column,
                end: call.span.end.byte,
                end_line: child.span.end.line,
                end_column: child.span.end.column,
                braced: false,
            });
        }
        if allow_unreachable_pure
            && let Some((width, end)) = source.and_then(|witness| {
                prove_unreachable_pure_output(
                    nodes,
                    body,
                    previous,
                    expected_id,
                    parent,
                    local,
                    witness,
                )
            })
        {
            return Some(StaticIfArm {
                width,
                effects: Vec::new(),
                begin: child.span.begin.byte,
                begin_line: child.span.begin.line,
                begin_column: child.span.begin.column,
                end,
                end_line: child.span.end.line,
                end_column: child.span.end.column,
                braced: false,
            });
        }
        let (width, effects, end) = prove_static_if_statement(
            nodes,
            body,
            previous,
            expected_id,
            parent,
            local,
            outer_aliases,
            depth,
            allow_new_local,
            for_depth,
            induction,
            source,
        )?;
        return Some(StaticIfArm {
            width,
            effects,
            begin: child.span.begin.byte,
            begin_line: child.span.begin.line,
            begin_column: child.span.begin.column,
            end,
            end_line: child.span.end.line,
            end_column: child.span.end.column,
            braced: false,
        });
    }
    let begin = child.span.begin.byte;
    let end = child.span.end.byte;
    let line = child.span.begin.line;
    let column = child.span.begin.column;
    let multiline = child.span.end.line > line;
    let span_is_canonical = if multiline {
        child.span.end.column == conditional_column.checked_add(1)?
    } else {
        source_word(child, begin, end, line, column)
    };
    if begin <= previous
        || end >= body.span.end.byte
        || line == 0
        || column == 0
        || child.id != expected_id
        || child.parent != parent
        || child.type_name.is_some()
        || child.reference.is_some()
        || child.operation.is_some()
        || !metadata_empty(child)
        || !span_is_canonical
    {
        return None;
    }
    let mut cursor = 1usize;
    let mut effect_end = begin;
    let mut effects = Vec::new();
    let mut statement_count = 0usize;
    let mut expected_line = line.checked_add(1)?;
    let mut previous_includes_terminator = false;
    let mut local_is_live = local.is_some();
    let mut declared_local: Option<LocalDeclaration<'node>> = None;
    // Within this exact C block, identity copies keep all their prior
    // source names until a fresh guest input replaces the resident byte.
    let mut equivalent_locals: Vec<LocalDeclaration<'node>> = Vec::new();
    // Outer identity aliases are valid only while the entry byte is resident.
    let mut outer_aliases_live = true;
    loop {
        if statement_count >= 16 || effects.len() >= 16 {
            return None;
        }
        let statement = nodes.get(cursor)?;
        let gap = if multiline {
            conditional_column
                .checked_add(5)?
                .checked_sub(u32::from(previous_includes_terminator))?
        } else {
            2
        };
        if statement.span.begin.byte != effect_end.checked_add(gap)?
            || (multiline
                && (statement.span.begin.line != expected_line
                    || statement.span.begin.column
                        != conditional_column.checked_add(4)?))
        {
            return None;
        }
        let declares_local =
            allow_new_local && statement.kind == "declaration-statement";
        let alias = if declares_local && local_is_live {
            declared_local.as_ref().or(local).and_then(|live| {
                let witness = source?;
                let nodes = nodes.get(cursor..cursor.checked_add(4)?)?;
                std::iter::once(live)
                    .chain(equivalent_locals.iter())
                    .find_map(|candidate| {
                        prove_local_alias(
                            nodes,
                            (body, effect_end, child.id),
                            candidate,
                            witness,
                        )
                    })
            })
        } else {
            None
        };
        let unreachable_pure =
            allow_unreachable_pure.then_some(()).and_then(|()| {
                prove_unreachable_pure_output(
                    nodes.get(cursor..)?,
                    body,
                    effect_end,
                    expected_id.checked_add(u32::try_from(cursor).ok()?)?,
                    child.id,
                    declared_local.as_ref().or(local),
                    source?,
                )
            });
        // Never remove dynamic guest control based on sampled input:
        // each original output expression must preserve its resident byte
        // on the active source/Clang guard domain. Multiple ordered writes
        // are safe only when every preceding statement is another pure
        // write of the same byte: any read, assignment or exit invalidates
        // the argument's proven resident-byte identity.
        let prior_outputs_preserve_byte = statement_count == 0
            || (statement_count == effects.len()
                && effects.iter().all(|effect: &StaticIfEffect<'_>| {
                    effect.input.is_none()
                        && effect.assigned_local.is_none()
                        && effect.loop_exit.is_none()
                        && !effect.outputs.is_empty()
                }));
        let guarded_output = if prior_outputs_preserve_byte
            && statement.kind == "call-expression"
            && let Some(domain) = active_domain
            && let Some(bound) = declared_local.as_ref().or(local)
            && local_is_live
            && let Some(witness) = source
            && let Some((width, call, None, nested)) =
                prove_identity_byte_output(
                    nodes.get(cursor..)?,
                    body,
                    Some(bound),
                    expected_id.checked_add(u32::try_from(cursor).ok()?)?,
                    effect_end,
                    child.id,
                    witness,
                    Some(domain),
                )
            && nested.is_empty()
        {
            // Every C call ends before its semicolon. The enclosing
            // statement loop separately checks each source/Clang gap and
            // the eventual closing brace; do not require this particular
            // write to be the last statement in the compound block.
            witness
                .get(usize::try_from(call.span.end.byte).ok()?)
                .filter(|byte| **byte == b';')
                .map(|_| (width, call))
        } else {
            None
        };
        let nested_if = if statement.kind == "if-statement"
            && let Some(domain) = active_domain
        {
            prove_static_if(
                nodes.get(cursor..)?,
                body,
                effect_end,
                expected_id.checked_add(u32::try_from(cursor).ok()?)?,
                child.id,
                declared_local.as_ref().or(local),
                outer_aliases,
                depth.checked_add(1)?,
                allow_new_local,
                for_depth,
                induction,
                Some(domain),
                source,
            )
        } else {
            None
        };
        let (width, statement_effects, statement_end) = if let Some(proof) =
            nested_if
        {
            (
                proof.width,
                if proof.selected {
                    proof.effects
                } else {
                    Vec::new()
                },
                proof.end,
            )
        } else if let Some(alias) = alias {
            let end = alias.declaration_end;
            if let Some(live) = declared_local.as_ref().or(local) {
                equivalent_locals.push(live.clone());
            }
            declared_local = Some(alias);
            (4, Vec::new(), end)
        } else if declares_local
            && let Some((declaration, width, comma_effects)) =
                source.and_then(|witness| {
                    prove_comma_local_declaration(
                        nodes.get(cursor..)?,
                        body,
                        effect_end,
                        child.id,
                        witness,
                    )
                })
        {
            // A comma declaration can consume several independently ordered
            // guest inputs before exporting only its last value in this scope.
            let end = declaration.declaration_end;
            equivalent_locals.clear();
            declared_local = Some(declaration);
            local_is_live = true;
            (width, static_comma_effects(comma_effects, None, None)?, end)
        } else if declares_local {
            // Each source-proven declaration reads a fresh guest byte.
            // Several sequential locals may share this lexical block, but
            // only the latest byte remains resident in the accumulator.
            // Never recover an older, overwritten C value from a stale name.
            // Clang-shaped nodes cannot manufacture a guest read or output
            // from a different C initializer. Both declaration forms require
            // the exact original source spelling, including every call.
            let witness = source?;
            let (declaration, width, calls) = if let Some(proof) =
                prove_output_return_declaration(
                    nodes.get(cursor..)?,
                    body,
                    effect_end,
                    child.id,
                    witness,
                ) {
                proof
            } else {
                let declaration = prove_local_declaration(
                    nodes.get(cursor..cursor.checked_add(5)?)?,
                    body,
                    effect_end,
                    child.id,
                )?;
                let begin = usize::try_from(statement.span.begin.byte).ok()?;
                let end = usize::try_from(declaration.declaration_end).ok()?;
                let spelling = format!("int {} = getchar();", declaration.name);
                if witness.get(begin..end) != Some(spelling.as_bytes())
                    || declaration.input.id != statement.id.checked_add(2)?
                {
                    return None;
                }
                (declaration, 5, Vec::new())
            };
            let end = declaration.declaration_end;
            let read = declaration.input;
            equivalent_locals.clear();
            declared_local = Some(declaration);
            local_is_live = true;
            (
                width,
                vec![StaticIfEffect {
                    input: Some(read),
                    assigned_local: None,
                    outputs: calls,
                    loop_exit: None,
                }],
                end,
            )
        } else if let Some((width, end)) = unreachable_pure {
            (width, Vec::new(), end)
        } else if let Some((width, call)) = guarded_output {
            (
                width,
                vec![StaticIfEffect {
                    input: None,
                    assigned_local: None,
                    outputs: vec![call],
                    loop_exit: None,
                }],
                call.span.end.byte,
            )
        } else {
            // Every candidate is tied to this same live guest SSA
            // byte. Try the most recent C binding, then earlier exact
            // aliases; no input may have intervened.
            let active =
                declared_local.as_ref().or(local).filter(|_| local_is_live);
            active
                .into_iter()
                .chain(equivalent_locals.iter().filter(|_| {
                    local_is_live && statement.kind == "call-expression"
                }))
                .chain(outer_aliases.iter().filter(|_| {
                    outer_aliases_live
                        && local_is_live
                        && statement.kind == "call-expression"
                }))
                .find_map(|candidate| {
                    prove_static_if_statement(
                        nodes.get(cursor..)?,
                        body,
                        effect_end,
                        expected_id.checked_add(u32::try_from(cursor).ok()?)?,
                        child.id,
                        Some(candidate),
                        outer_aliases,
                        depth,
                        allow_new_local,
                        for_depth,
                        induction,
                        source,
                    )
                })
                .or_else(|| {
                    (!local_is_live).then(|| {
                        prove_static_if_statement(
                            nodes.get(cursor..)?,
                            body,
                            effect_end,
                            expected_id
                                .checked_add(u32::try_from(cursor).ok()?)?,
                            child.id,
                            None,
                            &[],
                            depth,
                            allow_new_local,
                            for_depth,
                            induction,
                            source,
                        )
                    })?
                })?
        };
        if statement_end >= end {
            return None;
        }
        // Declarations include their trailing `;` in the Clang extent;
        // braced nested ifs end at `}`. Both leave one less separator byte
        // than an expression whose terminating `;` is outside its span.
        previous_includes_terminator = statement.kind
            == "declaration-statement"
            || (matches!(
                statement.kind.as_str(),
                "if-statement" | "for-statement" | "switch-statement"
            ) && statement.span.end.line > statement.span.begin.line
                && source.is_none_or(|witness| {
                    usize::try_from(statement_end)
                        .ok()
                        .and_then(|end| end.checked_sub(1))
                        .and_then(|at| witness.get(at))
                        == Some(&b'}')
                }));
        expected_line = statement.span.end.line.checked_add(1)?;
        if statement_effects
            .iter()
            .any(|effect| effect.input.is_some())
        {
            outer_aliases_live = false;
        }
        if !declares_local {
            if statement_effects
                .iter()
                .any(|effect| effect.input.is_some())
            {
                equivalent_locals.clear();
            }
            if let Some(bound) = declared_local.as_ref().or(local) {
                local_is_live = outer_loop_byte_after_effects(
                    &statement_effects,
                    &bound.variable_reference,
                    local_is_live,
                )?;
            }
        }
        effects.extend(statement_effects);
        statement_count = statement_count.checked_add(1)?;
        if effects.len() > 16 {
            return None;
        }
        cursor = cursor.checked_add(width)?;
        effect_end = statement_end;
        let end_gap = if multiline {
            conditional_column
                .checked_add(2)?
                .checked_sub(u32::from(previous_includes_terminator))?
        } else {
            3
        };
        if effect_end.checked_add(end_gap)? == end {
            if multiline && child.span.end.line != expected_line {
                return None;
            }
            break;
        }
    }
    Some(StaticIfArm {
        width: cursor,
        effects,
        begin,
        begin_line: line,
        begin_column: column,
        end,
        end_line: child.span.end.line,
        end_column: child.span.end.column,
        braced: true,
    })
}

// Authenticate an exact C identifier, not a prefix inside a longer token.
fn source_counter_identifier(
    source: &[u8],
    start: u32,
    name: &str,
) -> Option<bool> {
    let begin = usize::try_from(start).ok()?;
    let end = begin.checked_add(name.len())?;
    let identifier_byte =
        |byte: &u8| byte.is_ascii_alphanumeric() || *byte == b'_';
    Some(
        source.get(begin..end)? == name.as_bytes()
            && (begin == 0
                || !source.get(begin - 1).is_some_and(identifier_byte))
            && !source.get(end).is_some_and(identifier_byte),
    )
}

// The induction value is statically proven for a canonical finite C loop.
// Only the loop body effects are repeated: guest input and output still run
// at execution time, with no host-side byte computation or replay.
struct StaticForProof<'node> {
    width: usize,
    effects: Vec<StaticIfEffect<'node>>,
    end: u32,
}

// A closed, finite one- or two-digit-step for loop with a verified i32 counter:
//     for (int i = 0; i < N; ++i) {
//     for (int i = 1; i <= N; i++) {
//     for (int i = 4; i >= 1; i--) {
//     for (int i = 4; i > 0; --i) {
//     for (int i = 4; i >= 1; i -= 1) {
//         <source-proven byte-effect statements>
//     }
// Ascending starts may be 0–99; descending starts remain 1–99.
// Both directions admit 0–16 finite trips.
// Source-spelled `!=` is safe only when the exact step reaches the bound
// before signed overflow; the original source must authenticate its operator.
// Both the induction arithmetic and all body statements are authenticated
// against the pinned Clang preorder before any target instructions exist.
#[expect(
    clippy::too_many_lines,
    reason = "the complete Clang induction and body ancestry is one proof"
)]
fn prove_static_for<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    parent: u32,
    outer_local: Option<&LocalDeclaration<'node>>,
    outer_aliases: &[LocalDeclaration<'node>],
    for_depth: usize,
    outer_induction: Option<StaticInduction<'_>>,
    source: Option<&[u8]>,
) -> Option<StaticForProof<'node>> {
    let [
        loop_node,
        declaration,
        variable,
        initial,
        condition,
        read_cast,
        read_variable,
        bound,
        increment,
        increment_variable,
        rest @ ..,
    ] = nodes
    else {
        return None;
    };
    let start = loop_node.span.begin.byte;
    let line = loop_node.span.begin.line;
    let column = loop_node.span.begin.column;
    let declaration_start = start.checked_add(5)?;
    let unsigned = variable.type_name.as_deref() == Some("u32");
    let counter_type = if unsigned {
        "u32"
    } else {
        "i32"
    };
    let prefix = if unsigned {
        b"unsigned ".as_slice()
    } else {
        b"int ".as_slice()
    };
    let prefix_width = u32::try_from(prefix.len()).ok()?;
    let counter_start = declaration_start.checked_add(prefix_width)?;
    if unsigned {
        let witness = source?;
        let begin = usize::try_from(declaration_start).ok()?;
        if witness.get(begin..begin.checked_add(prefix.len())?) != Some(prefix)
        {
            return None;
        }
    }
    // Authenticate the C identifier against the original source and Clang
    // declaration binding instead of assuming the spelling `i`.
    let name = variable.name.as_deref()?;
    let name_bytes = name.as_bytes();
    let (first, tail) = name_bytes.split_first()?;
    if name_bytes.len() > 32
        || (!first.is_ascii_alphabetic() && *first != b'_')
        || !tail
            .iter()
            .all(|byte| byte.is_ascii_alphanumeric() || *byte == b'_')
        || (source.is_none() && name != "i")
    {
        return None;
    }
    let name_width = u32::try_from(name_bytes.len()).ok()?;
    let initial_width =
        initial.span.end.byte.checked_sub(initial.span.begin.byte)?;
    if !(1..=9).contains(&initial_width) {
        return None;
    }
    let initial_start = start
        .checked_add(8)?
        .checked_add(prefix_width)?
        .checked_add(name_width)?;
    let declaration_end =
        initial_start.checked_add(initial_width)?.checked_add(1)?;
    let variable_end = declaration_end.checked_sub(1)?;
    let condition_start = declaration_end.checked_add(1)?;
    let condition_column =
        column.checked_add(condition_start.checked_sub(start)?)?;
    let condition_operator = condition.operation.as_deref()?;
    let (ascending, inclusive, operator_width, inequality) =
        match condition_operator {
            "<" => (true, false, 1u32, false),
            "<=" => (true, true, 2u32, false),
            ">" => (false, false, 1u32, false),
            ">=" => (false, true, 2u32, false),
            "!=" => {
                // For equality termination, direction comes from the
                // independently authenticated step, not the comparator.
                let step = if increment.operation.as_deref() == Some("=") {
                    nodes.get(10)?.operation.as_deref()?
                } else {
                    increment.operation.as_deref()?
                };
                let ascending = match step {
                    "++" | "+=" | "+" => true,
                    "--" | "-=" | "-" => false,
                    _ => return None,
                };
                (ascending, false, 2u32, true)
            },
            _ => return None,
        };
    // Even a same-width forged `<=` AST must not reinterpret source `!=`.
    // Require original C bytes for the inequality case; also check any
    // supplied source for other comparison operators.
    let operator_start = usize::try_from(
        condition_start.checked_add(name_width)?.checked_add(1)?,
    )
    .ok()?;
    let operator_end = operator_start.checked_add(condition_operator.len())?;
    if inequality && source.is_none()
        || source.is_some_and(|witness| {
            witness.get(operator_start..operator_end)
                != Some(condition_operator.as_bytes())
        })
    {
        return None;
    }
    let bound_start = condition_start
        .checked_add(name_width)?
        .checked_add(2 + operator_width)?;
    let increment_start = bound.span.end.byte.checked_add(2)?;
    let compound_increment = increment.kind == "compound-assignment-expression";
    let assigned_increment = increment.kind == "binary-expression";
    // Admit unsigned compound or assignment strides only through the exact
    // same source-backed counter identity and verified integer suffix.
    // The pinned Clang preorder supplies the increment literal at a fixed
    // child offset. Its source width extends the exact header geometry; the
    // later leaf proof binds every digit to the original C and its parent.
    let stride_leaf = if assigned_increment {
        Some(rest.get(3)?)
    } else if compound_increment {
        Some(rest.first()?)
    } else {
        None
    };
    let stride_width = if let Some(leaf) = stride_leaf {
        leaf.span.end.byte.checked_sub(leaf.span.begin.byte)?
    } else {
        1
    };
    if !(1..=9).contains(&stride_width) {
        return None;
    }
    let increment_length = (if assigned_increment {
        name_width.checked_mul(2)?.checked_add(7)?
    } else if compound_increment {
        name_width.checked_add(5)?
    } else {
        name_width.checked_add(2)?
    })
    .checked_add(stride_width.checked_sub(1)?)?;
    let increment_end = increment_start.checked_add(increment_length)?;
    let arm_start = increment_end.checked_add(2)?;
    let variable_reference = format!("{name}@{counter_start}");
    if let Some(witness) = source {
        if !source_counter_identifier(witness, counter_start, name)?
            || !source_counter_identifier(witness, condition_start, name)?
        {
            return None;
        }
    }
    let initial_value = prove_for_literal_operand(
        initial,
        expected_id.checked_add(3)?,
        variable.id,
        initial_start,
        line,
        column.checked_add(initial_start.checked_sub(start)?)?,
        unsigned,
        source,
    )?;
    // Only source-authenticated steps in the comparison's direction are
    // admitted: unary unit steps or 1–99 compound/assigned strides.
    if start <= previous
        || start <= body.span.begin.byte
        || line == 0
        || column == 0
        || loop_node.id != expected_id
        || loop_node.parent != parent
        || for_depth == 0
        || for_depth > MAX_STATIC_FOR_DEPTH
        || loop_node.kind != "for-statement"
        || loop_node.type_name.is_some()
        || loop_node.reference.is_some()
        || loop_node.operation.is_some()
        || !metadata_empty(loop_node)
        || declaration.id != expected_id.checked_add(1)?
        || declaration.parent != loop_node.id
        || declaration.kind != "declaration-statement"
        || declaration.type_name.is_some()
        || declaration.reference.is_some()
        || declaration.operation.is_some()
        || !metadata_empty(declaration)
        || !source_word(
            declaration,
            declaration_start,
            declaration_end,
            line,
            column.checked_add(5)?,
        )
        || variable.id != expected_id.checked_add(2)?
        || variable.parent != declaration.id
        || variable.kind != "variable-declaration"
        || variable.name.as_deref() != Some(name)
        || variable.type_name.as_deref() != Some(counter_type)
        || variable.reference.as_deref() != Some(variable_reference.as_str())
        || variable.definition.as_deref() != Some("definition")
        || variable.linkage.as_deref() != Some("none")
        || variable.storage_class.as_deref() != Some("none")
        || !matches!(
            variable.storage_duration,
            Some(super::StorageDuration::Automatic)
        )
        || variable.operation.is_some()
        || variable.literal.is_some()
        || variable.constant_integer.is_some()
        || variable.inline_specified.is_some()
        || !source_word(
            variable,
            declaration_start,
            variable_end,
            line,
            column.checked_add(5)?,
        )
        || if ascending {
            !(0..=99).contains(&initial_value)
        } else {
            !(1..=99).contains(&initial_value)
        }
        || condition.id != expected_id.checked_add(4)?
        || condition.parent != loop_node.id
        || condition.kind != "binary-expression"
        || condition.type_name.as_deref() != Some("i32")
        || !metadata_empty(condition)
        || !source_word(
            condition,
            condition_start,
            bound.span.end.byte,
            line,
            condition_column,
        )
        || read_cast.id != expected_id.checked_add(5)?
        || read_cast.parent != condition.id
        || read_cast.kind != "cast-expression"
        || read_cast.type_name.as_deref() != Some(counter_type)
        || read_cast.operation.as_deref() != Some("lvalue-to-rvalue")
        || !metadata_empty(read_cast)
        || !source_word(
            read_cast,
            condition_start,
            condition_start.checked_add(name_width)?,
            line,
            condition_column,
        )
        || read_variable.id != expected_id.checked_add(6)?
        || read_variable.parent != read_cast.id
        || read_variable.kind != "declaration-reference-expression"
        || read_variable.type_name.as_deref() != Some(counter_type)
        || read_variable.reference.as_deref()
            != Some(variable_reference.as_str())
        || read_variable.operation.is_some()
        || !metadata_empty(read_variable)
        || read_variable.span != read_cast.span
        || bound.span.begin.byte != bound_start
        || bound.span.begin.column
            != condition_column
                .checked_add(name_width)?
                .checked_add(2 + operator_width)?
        || increment.id != expected_id.checked_add(8)?
        || increment.parent != loop_node.id
        || increment.kind
            != if assigned_increment {
                "binary-expression"
            } else if compound_increment {
                "compound-assignment-expression"
            } else {
                "unary-expression"
            }
        || increment.type_name.as_deref() != Some(counter_type)
        || increment.operation.as_deref()
            != Some(if assigned_increment {
                "="
            } else {
                match (ascending, compound_increment) {
                    (true, true) => "+=",
                    (true, false) => "++",
                    (false, true) => "-=",
                    (false, false) => "--",
                }
            })
        || !metadata_empty(increment)
        || !source_word(
            increment,
            increment_start,
            increment_end,
            line,
            bound.span.end.column.checked_add(2)?,
        )
        || increment_variable.id != expected_id.checked_add(9)?
        || increment_variable.parent != increment.id
        || increment_variable.kind != "declaration-reference-expression"
        || increment_variable.type_name.as_deref() != Some(counter_type)
        || increment_variable.reference.as_deref()
            != Some(variable_reference.as_str())
        || increment_variable.operation.is_some()
        || !metadata_empty(increment_variable)
        || !(source_word(
            increment_variable,
            increment_start,
            increment_start.checked_add(name_width)?,
            line,
            bound.span.end.column.checked_add(2)?,
        ) || (!compound_increment
            && source_word(
                increment_variable,
                increment_start.checked_add(2)?,
                increment_start.checked_add(2)?.checked_add(name_width)?,
                line,
                bound.span.end.column.checked_add(4)?,
            )))
    {
        return None;
    }
    // For `i = i + 1`, authenticate every child of the assignment and
    // arithmetic subtree: neither an unrelated local nor a hidden effect
    // can supply the right-hand side. Guest values remain runtime bytes.
    let (rest, arm_id_offset, stride) = if assigned_increment {
        let [arithmetic, read, variable, one, tail @ ..] = rest else {
            return None;
        };
        let rhs_start =
            increment_start.checked_add(name_width)?.checked_add(3)?;
        let rhs_column = bound
            .span
            .end
            .column
            .checked_add(name_width)?
            .checked_add(5)?;
        if arithmetic.id != expected_id.checked_add(10)?
            || arithmetic.parent != increment.id
            || arithmetic.kind != "binary-expression"
            || arithmetic.type_name.as_deref() != Some(counter_type)
            || arithmetic.operation.as_deref()
                != Some(if ascending {
                    "+"
                } else {
                    "-"
                })
            || arithmetic.reference.is_some()
            || !metadata_empty(arithmetic)
            || !source_word(
                arithmetic,
                rhs_start,
                increment_end,
                line,
                rhs_column,
            )
            || read.id != expected_id.checked_add(11)?
            || read.parent != arithmetic.id
            || read.kind != "cast-expression"
            || read.type_name.as_deref() != Some(counter_type)
            || read.operation.as_deref() != Some("lvalue-to-rvalue")
            || read.reference.is_some()
            || !metadata_empty(read)
            || !source_word(
                read,
                rhs_start,
                rhs_start.checked_add(name_width)?,
                line,
                rhs_column,
            )
            || variable.id != expected_id.checked_add(12)?
            || variable.parent != read.id
            || variable.kind != "declaration-reference-expression"
            || variable.type_name.as_deref() != Some(counter_type)
            || variable.reference.as_deref()
                != Some(variable_reference.as_str())
            || variable.operation.is_some()
            || !metadata_empty(variable)
            || variable.span != read.span
        {
            return None;
        }
        let stride = prove_for_literal_operand(
            one,
            expected_id.checked_add(13)?,
            arithmetic.id,
            increment_start
                .checked_add(name_width.checked_mul(2)?)?
                .checked_add(6)?,
            line,
            bound
                .span
                .end
                .column
                .checked_add(name_width.checked_mul(2)?)?
                .checked_add(8)?,
            unsigned,
            source,
        )?;
        (tail, 14, stride)
    } else if compound_increment {
        // The additional compound-assignment child must be exactly one.
        let (one, tail) = rest.split_first()?;
        let stride = prove_for_literal_operand(
            one,
            expected_id.checked_add(10)?,
            increment.id,
            increment_start.checked_add(name_width)?.checked_add(4)?,
            line,
            bound
                .span
                .end
                .column
                .checked_add(name_width)?
                .checked_add(6)?,
            unsigned,
            source,
        )?;
        (tail, 11, stride)
    } else {
        (rest, 10, 1)
    };
    // Reject noncanonical or out-of-range steps before calculating trips.
    // Never trust an unverified Clang numeric annotation for a non-unit step.
    if !(1..=99).contains(&stride) || (stride != 1 && source.is_none()) {
        return None;
    }
    let bound_value = prove_for_literal_operand(
        bound,
        expected_id.checked_add(7)?,
        condition.id,
        bound_start,
        line,
        condition_column
            .checked_add(name_width)?
            .checked_add(2 + operator_width)?,
        unsigned,
        source,
    )?;
    // Same-width numeric forgeries can otherwise turn a terminating loop
    // into a different number of guest effects. Compare both Clang decimal
    // leaves with their original source, not only each node's own metadata.
    if !unsigned && let Some(witness) = source {
        for literal in [initial, bound] {
            let begin = usize::try_from(literal.span.begin.byte).ok()?;
            let text = literal.literal.as_deref()?;
            if witness.get(begin..begin.checked_add(text.len())?)
                != Some(text.as_bytes())
            {
                return None;
            }
        }
    }
    // An inequality condition does not become false merely because the
    // iteration moves past its bound. Refuse the divergent direction, even
    // if a source break might happen to terminate earlier.
    if inequality
        && (ascending && bound_value < initial_value
            || !ascending && bound_value > initial_value)
    {
        return None;
    }
    // Authentication of the `!=` branch requires the original C step too:
    // forged plus/minus arithmetic nodes could otherwise reverse an actual
    // divergent loop. Re-check the same fixed-shape source step for every
    // loop whose original bytes are available.
    if let Some(witness) = source {
        // The leaf proof has already authenticated this exact spelling and
        // value. Preserve the source token in the surrounding step grammar
        // rather than silently replacing `0x2U` with decimal `2U`.
        let stride_spelling = if unsigned && let Some(leaf) = stride_leaf {
            let begin = usize::try_from(leaf.span.begin.byte).ok()?;
            let end = usize::try_from(leaf.span.end.byte).ok()?;
            std::str::from_utf8(witness.get(begin..end)?)
                .ok()?
                .to_owned()
        } else {
            format!(
                "{stride}{}",
                if unsigned {
                    "U"
                } else {
                    ""
                }
            )
        };
        let spelling = if assigned_increment {
            format!(
                "{name} = {name} {} {stride_spelling}",
                if ascending {
                    "+"
                } else {
                    "-"
                }
            )
        } else if compound_increment {
            format!(
                "{name} {}= {stride_spelling}",
                if ascending {
                    "+"
                } else {
                    "-"
                }
            )
        } else if increment_variable.span.begin.byte == increment_start {
            if ascending {
                format!("{name}++")
            } else {
                format!("{name}--")
            }
        } else if ascending {
            format!("++{name}")
        } else {
            format!("--{name}")
        };
        let begin = usize::try_from(increment_start).ok()?;
        if witness.get(begin..begin.checked_add(spelling.len())?)
            != Some(spelling.as_bytes())
        {
            return None;
        }
    }
    // `i >= 0U` alone is unbounded, but a selected break/return at zero
    // may make it finite. The loop below must prove that the final step is
    // skipped; otherwise the per-trip unsigned wrap check still rejects.
    // Include the bound on either signed direction only for <= or >=.
    // A false initial condition is a real, finite zero-trip loop.
    let distance = if ascending {
        bound_value.checked_sub(initial_value)?
    } else {
        initial_value.checked_sub(bound_value)?
    };
    let trip_count = if inequality {
        // Crossing the endpoint is not equivalent to reaching it in C.
        if distance < 0 || distance % stride != 0 {
            return None;
        }
        distance / stride
    } else if inclusive {
        if distance < 0 {
            0
        } else {
            distance / stride + 1
        }
    } else if distance <= 0 {
        0
    } else {
        (distance - 1) / stride + 1
    };
    // The final unsigned update may wrap even when a signed distance
    // calculation predicts termination. Verify it only after selecting the
    // source-proven body exit: a break/return skips that update entirely.
    let iterations = usize::try_from(trip_count).ok()?;
    if iterations > 16 {
        return None;
    }
    // Authenticate the whole body even when the source condition is false
    // initially. Its Clang nodes cannot be skipped as an untrusted island;
    // only zero guest effects may be emitted for that validation pass.
    let mut effects = Vec::new();
    let mut arm_width = None;
    let mut arm_end = None;
    for iteration in 0..iterations.max(1) {
        let counter_value = if ascending {
            initial_value.checked_add(
                stride.checked_mul(i32::try_from(iteration).ok()?)?,
            )?
        } else {
            initial_value.checked_sub(
                stride.checked_mul(i32::try_from(iteration).ok()?)?,
            )?
        };
        let arm = prove_static_if_arm(
            rest,
            body,
            increment_end,
            expected_id.checked_add(arm_id_offset)?,
            loop_node.id,
            outer_local,
            outer_aliases,
            0,
            column,
            true,
            for_depth,
            Some(StaticInduction {
                reference: &variable_reference,
                name,
                source,
                unsigned,
                value: counter_value,
                outer: outer_induction.map(|enclosing| StaticCounter {
                    reference: enclosing.reference,
                    name: enclosing.name,
                    unsigned: enclosing.unsigned,
                    value: enclosing.value,
                }),
                outermost: outer_induction
                    .and_then(|enclosing| enclosing.outer),
            }),
            false,
            None,
            source,
        )?;
        if !arm.braced
            || arm.begin != arm_start
            || arm.begin_line != line
            || arm.begin_column
                != bound.span.end.column.checked_add(increment_length + 4)?
            || loop_node.span.end.byte != arm.end
            || loop_node.span.end.line != arm.end_line
            || loop_node.span.end.column != arm.end_column
            || arm.end >= body.span.end.byte
        {
            return None;
        }
        arm_width = Some(arm.width);
        arm_end = Some(arm.end);
        if iterations == 0 {
            continue;
        }
        // The nearest selected exit decides this trip. A continue skips
        // only this trip's suffix; a break stops all later trips.
        let mut trip = arm.effects;
        let exit = trip.iter().position(|effect| effect.loop_exit.is_some());
        let exit_kind = if let Some(index) = exit {
            let exit = trip[index].clone();
            let kind = exit.loop_exit;
            trip.truncate(index);
            // A selected return must survive inner loops to stop the entire
            // function. Break and continue are consumed at this loop level.
            if exit.loop_exit == Some(StaticLoopExit::Return) {
                trip.push(exit);
            }
            kind
        } else {
            None
        };
        effects.extend(trip);
        if effects.len() > MAX_SOURCE_OUTPUTS {
            return None;
        }
        if matches!(
            exit_kind,
            Some(StaticLoopExit::Break | StaticLoopExit::Return)
        ) {
            break;
        }
        // C executes the increment after a normal trip and after continue,
        // including the final trip whose following guard would be false.
        // A selected break/return above skips the increment. Never admit
        // unsigned wrap as if the mathematical negative counter terminated.
        if unsigned && !ascending && counter_value.checked_sub(stride)? < 0 {
            return None;
        }
    }
    // A prior source-local alias cannot survive an accumulator-clobbering
    // input in any selected trip. Do not infer generic guest C storage.
    if !outer_aliases.is_empty()
        && effects.iter().any(|effect| effect.input.is_some())
    {
        return None;
    }
    Some(StaticForProof {
        width: usize::try_from(arm_id_offset)
            .ok()?
            .checked_add(arm_width?)?,
        effects,
        end: arm_end?,
    })
}

struct StaticIfProof<'node> {
    width: usize,
    selected: bool,
    effects: Vec<StaticIfEffect<'node>>,
    end: u32,
}

// Signed induction retains the existing decimal AST-only witness. Unsigned
// induction must authenticate the complete C23 token against its normalized
// decimal Clang value, including radix and an exact `u`/`U` suffix. Reuse the
// shared lexer rather than inventing a second integer spelling authority.
fn prove_for_literal_operand(
    node: &Node,
    expected_id: u32,
    parent: u32,
    start: u32,
    line: u32,
    column: u32,
    unsigned: bool,
    source: Option<&[u8]>,
) -> Option<i32> {
    if !unsigned {
        return prove_decimal_condition_operand(
            node,
            expected_id,
            parent,
            start,
            line,
            column,
        );
    }
    let digits = node.literal.as_deref()?;
    let value = digits.parse::<i32>().ok()?;
    let end = node.span.end.byte;
    let width = end.checked_sub(start)?;
    if !(2..=9).contains(&width) {
        return None;
    }
    let witness = source?;
    let begin = usize::try_from(start).ok()?;
    let source_end = usize::try_from(end).ok()?;
    let token = witness.get(begin..source_end)?;
    let (suffix, _) = token.split_last()?;
    let spelled_value = super::source_integer_token_value(token)?;
    (value >= 0
        && value.to_string() == digits
        && matches!(*suffix, b'U' | b'u')
        && spelled_value == u64::try_from(value).ok()?
        && node.id == expected_id
        && node.parent == parent
        && node.kind == "integer-literal"
        && node.type_name.as_deref() == Some("u32")
        && node.operation.is_none()
        && node.reference.is_none()
        && node.name.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
        && node.constant_integer.as_deref() == Some(digits)
        && source_word(node, start, end, line, column))
    .then_some(value)
}

// Match a source-spelled nonnegative decimal i32 operand, rather than
// accepting an evaluated constant divorced from its source coordinates.
fn prove_decimal_condition_operand(
    node: &Node,
    expected_id: u32,
    parent: u32,
    start: u32,
    line: u32,
    column: u32,
) -> Option<i32> {
    let spelling = node.literal.as_deref()?;
    let value = spelling.parse::<i32>().ok()?;
    let end = start.checked_add(u32::try_from(spelling.len()).ok()?)?;
    (value >= 0
        && value.to_string() == spelling
        && node.id == expected_id
        && node.parent == parent
        && node.kind == "integer-literal"
        && node.type_name.as_deref() == Some("i32")
        && node.operation.is_none()
        && node.reference.is_none()
        && node.name.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
        && node.constant_integer.as_deref() == Some(spelling)
        && source_word(node, start, end, line, column))
    .then_some(value)
}

// A recursive C predicate is bound to both its Clang ancestry and exact
// source coordinates. No interpreter reads source bytes or guest input.
#[derive(Clone, Copy)]
struct StaticValueLocation {
    id: u32,
    parent: u32,
    start: u32,
    line: u32,
    column: u32,
    depth: usize,
}

impl StaticValueLocation {
    fn child(self, id: u32, start: u32, column: u32) -> Option<Self> {
        Some(Self {
            id,
            parent: self.id,
            start,
            column,
            depth: self.depth.checked_add(1)?,
            ..self
        })
    }
}

// The source extent of a parenthesized value differs from its final leaf.
fn prove_static_prefix(
    nodes: &[Node],
    at: StaticValueLocation,
) -> Option<(usize, i32, u32)> {
    let node = nodes.first()?;
    let parenthesized = node.kind == "parenthesized-expression";
    if !parenthesized
        && (node.kind != "unary-expression"
            || node.operation.as_deref() != Some("!"))
    {
        return None;
    }
    if parenthesized && node.operation.is_some() {
        return None;
    }
    let child = at.child(
        at.id.checked_add(1)?,
        at.start.checked_add(1)?,
        at.column.checked_add(1)?,
    )?;
    let (inner_width, inner_value) =
        prove_static_value(nodes.get(1..)?, child)?;
    let value = if parenthesized {
        inner_value
    } else {
        i32::from(inner_value == 0i32)
    };
    let end = nodes.get(1)?.span.end.byte;
    Some((
        inner_width.checked_add(1)?,
        value,
        if parenthesized {
            end.checked_add(1)?
        } else {
            end
        },
    ))
}

// Reconstruct both branches of a pure binary predicate, even when C would
// short-circuit the second value. Unknown/effectful operands reject.
fn prove_static_binary(
    nodes: &[Node],
    at: StaticValueLocation,
) -> Option<(usize, i32, u32)> {
    let node = nodes.first()?;
    if node.kind != "binary-expression" {
        return None;
    }
    let operator = node.operation.as_deref()?;
    if !matches!(
        operator,
        "==" | "!=" | "<" | "<=" | ">" | ">=" | "&&" | "||"
    ) {
        return None;
    }
    let left_at = at.child(at.id.checked_add(1)?, at.start, at.column)?;
    let (left_width, left) = prove_static_value(nodes.get(1..)?, left_at)?;
    let right_index = left_width.checked_add(1)?;
    let left_root = nodes.get(1)?;
    let gap = u32::try_from(operator.len()).ok()?.checked_add(2)?;
    let right_at = at.child(
        at.id.checked_add(u32::try_from(right_index).ok()?)?,
        left_root.span.end.byte.checked_add(gap)?,
        left_root.span.end.column.checked_add(gap)?,
    )?;
    let (right_width, right) =
        prove_static_value(nodes.get(right_index..)?, right_at)?;
    let value = match operator {
        "==" => left == right,
        "!=" => left != right,
        "<" => left < right,
        "<=" => left <= right,
        ">" => left > right,
        ">=" => left >= right,
        "&&" => left != 0i32 && right != 0i32,
        "||" => left != 0i32 || right != 0i32,
        _ => return None,
    };
    Some((
        right_index.checked_add(right_width)?,
        i32::from(value),
        nodes.get(right_index)?.span.end.byte,
    ))
}

// Only bound, pure, pinned Clang expressions can select guest branch effects.
fn prove_static_value(
    nodes: &[Node],
    at: StaticValueLocation,
) -> Option<(usize, i32)> {
    if at.depth >= MAX_STATIC_PREDICATE_DEPTH {
        return None;
    }
    let node = nodes.first()?;
    if node.kind == "integer-literal" {
        return prove_decimal_condition_operand(
            node, at.id, at.parent, at.start, at.line, at.column,
        )
        .map(|value| (1, value));
    }
    if node.id != at.id
        || node.parent != at.parent
        || node.type_name.as_deref() != Some("i32")
        || node.reference.is_some()
        || node.literal.is_some()
        || node.name.is_some()
        || node.definition.is_some()
        || node.inline_specified.is_some()
        || node.linkage.is_some()
        || node.storage_class.is_some()
        || node.storage_duration.is_some()
    {
        return None;
    }
    let (width, value, end) = if node.kind == "binary-expression" {
        prove_static_binary(nodes, at)?
    } else {
        prove_static_prefix(nodes, at)?
    };
    (width <= MAX_STATIC_PREDICATE_NODES
        && node.constant_integer.as_deref() == Some(value.to_string().as_str())
        && source_word(node, at.start, end, at.line, at.column))
    .then_some((width, value))
}

// Normalized declaration references alone cannot authenticate the original
// source token. Require the bound name at each proven induction use.
fn induction_identifier_end(
    induction: StaticInduction<'_>,
    at: StaticValueLocation,
) -> Option<u32> {
    let end = at
        .start
        .checked_add(u32::try_from(induction.name.len()).ok()?)?;
    if let Some(witness) = induction.source {
        if !source_counter_identifier(witness, at.start, induction.name)? {
            return None;
        }
    } else if induction.name != "i" {
        return None;
    }
    Some(end)
}

// C signed induction arithmetic is checked only on a selected evaluation
// path. A separate source-shape proof can authenticate an unexecuted path.
fn checked_induction_arithmetic(
    operator: &str,
    counter: i32,
    operand: i32,
    unsigned: bool,
) -> Option<i64> {
    if unsigned {
        // A finite u32 loop counter is known before guest execution, but C
        // arithmetic on it still wraps modulo 2^32. Retain the full unsigned
        // result for a later comparison rather than using signed overflow.
        let counter = u32::try_from(counter).ok()?;
        let operand = u32::try_from(operand).ok()?;
        let value = match operator {
            "%" => counter.checked_rem(operand)?,
            "/" => counter.checked_div(operand)?,
            "+" => counter.wrapping_add(operand),
            "-" => counter.wrapping_sub(operand),
            "*" => counter.wrapping_mul(operand),
            "&" => counter & operand,
            "^" => counter ^ operand,
            "|" => counter | operand,
            _ => return None,
        };
        return Some(i64::from(value));
    }
    let value = match operator {
        "%" => counter.checked_rem(operand),
        "/" => counter.checked_div(operand),
        "+" => counter.checked_add(operand),
        "-" => counter.checked_sub(operand),
        "*" => counter.checked_mul(operand),
        _ => None,
    }?;
    Some(i64::from(value))
}

// Pure arithmetic on a protected induction counter is a source-time value.
// Authenticate the complete `name op N` Clang subtree, source operator and
// canonical decimal operand; a live guest byte never enters this proof.
fn prove_induction_arithmetic_shape(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, Option<i64>, u32)> {
    let [remainder, cast, variable, divisor, ..] = nodes else {
        return None;
    };
    let name_end = induction_identifier_end(induction, at)?;
    let rhs_start = name_end.checked_add(3)?;
    let rhs_column = at.column.checked_add(rhs_start.checked_sub(at.start)?)?;
    let operator = remainder.operation.as_deref()?;
    let counter_type = if induction.unsigned {
        "u32"
    } else {
        "i32"
    };
    let operator_start = usize::try_from(name_end.checked_add(1)?).ok()?;
    let operator_end = operator_start.checked_add(operator.len())?;
    if !matches!(operator, "%" | "/" | "+" | "-" | "*" | "&" | "^" | "|")
        || (matches!(operator, "&" | "^" | "|") && !induction.unsigned)
        || (induction.source.is_none() && operator != "%")
        || induction.source.is_some_and(|witness| {
            witness.get(operator_start..operator_end)
                != Some(operator.as_bytes())
        })
        || remainder.id != at.id
        || remainder.parent != at.parent
        || remainder.kind != "binary-expression"
        || remainder.type_name.as_deref() != Some(counter_type)
        || remainder.reference.is_some()
        || !metadata_empty(remainder)
        || cast.id != remainder.id.checked_add(1)?
        || cast.parent != remainder.id
        || cast.kind != "cast-expression"
        || cast.type_name.as_deref() != Some(counter_type)
        || cast.operation.as_deref() != Some("lvalue-to-rvalue")
        || cast.reference.is_some()
        || !metadata_empty(cast)
        || !source_word(cast, at.start, name_end, at.line, at.column)
        || variable.id != cast.id.checked_add(1)?
        || variable.parent != cast.id
        || variable.kind != "declaration-reference-expression"
        || variable.type_name.as_deref() != Some(counter_type)
        || variable.reference.as_deref() != Some(induction.reference)
        || variable.operation.is_some()
        || !metadata_empty(variable)
        || variable.span != cast.span
    {
        return None;
    }
    let divisor_value = prove_for_literal_operand(
        divisor,
        variable.id.checked_add(1)?,
        remainder.id,
        rhs_start,
        at.line,
        rhs_column,
        induction.unsigned,
        induction.source,
    )?;
    let end = divisor.span.end.byte;
    if !source_word(remainder, at.start, end, at.line, at.column) {
        return None;
    }
    let value = checked_induction_arithmetic(
        operator,
        induction.value,
        divisor_value,
        induction.unsigned,
    );
    Some((4, value, end))
}

// Require the actual C value for an evaluated induction expression. The
// shape-only verifier above also serves unexecuted pure C operands, where a
// division by zero or signed overflow has no observable C effect.
fn prove_induction_arithmetic(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, i64, u32)> {
    let (width, value, end) =
        prove_induction_arithmetic_shape(nodes, at, induction)?;
    Some((width, value?, end))
}

// Compare source-proven induction arithmetic with a canonical decimal value.
// Every child, offset, type and declaration binding is checked before its
// source-time result selects genuine guest I/O effects.
fn prove_induction_arithmetic_comparison_shape(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, Option<bool>, u32)> {
    let comparison = nodes.first()?;
    let operator = comparison.operation.as_deref()?;
    if !matches!(operator, "==" | "!=" | "<" | "<=" | ">" | ">=")
        || comparison.id != at.id
        || comparison.parent != at.parent
        || comparison.kind != "binary-expression"
        || comparison.type_name.as_deref() != Some("i32")
        || comparison.reference.is_some()
        || !metadata_empty(comparison)
    {
        return None;
    }
    let remainder_at = at.child(at.id.checked_add(1)?, at.start, at.column)?;
    let (left_width, value, left_end) = prove_induction_arithmetic_shape(
        nodes.get(1..)?,
        remainder_at,
        induction,
    )?;
    let right_index = left_width.checked_add(1)?;
    let right = nodes.get(right_index)?;
    let right_offset = u32::try_from(operator.len()).ok()?.checked_add(2)?;
    let rhs = i64::from(prove_for_literal_operand(
        right,
        at.id.checked_add(u32::try_from(right_index).ok()?)?,
        comparison.id,
        left_end.checked_add(right_offset)?,
        at.line,
        at.column
            .checked_add(left_end.checked_sub(at.start)?)?
            .checked_add(right_offset)?,
        induction.unsigned,
        induction.source,
    )?);
    let comparison_operator = usize::try_from(left_end.checked_add(1)?).ok()?;
    let comparison_operator_end =
        comparison_operator.checked_add(operator.len())?;
    if induction.source.is_some_and(|witness| {
        witness.get(comparison_operator..comparison_operator_end)
            != Some(operator.as_bytes())
    }) || !source_word(
        comparison,
        at.start,
        right.span.end.byte,
        at.line,
        at.column,
    ) {
        return None;
    }
    let selected = match operator {
        "==" => value.map(|actual| actual == rhs),
        "!=" => value.map(|actual| actual != rhs),
        "<" => value.map(|actual| actual < rhs),
        "<=" => value.map(|actual| actual <= rhs),
        ">" => value.map(|actual| actual > rhs),
        ">=" => value.map(|actual| actual >= rhs),
        _ => return None,
    };
    Some((right_index.checked_add(1)?, selected, right.span.end.byte))
}

// An evaluated C comparison must have a defined arithmetic operand. Unselected
// expressions use only the authenticated shape, never this missing value.
fn prove_induction_arithmetic_comparison(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool, u32)> {
    let (width, selected, end) =
        prove_induction_arithmetic_comparison_shape(nodes, at, induction)?;
    Some((width, selected?, end))
}

// This is source-time C induction, not a guest read. A leaf comparison
// must prove the same loop-local declaration, canonical token geometry and
// Clang ancestry on every unrolled trip. No C storage is projected.
fn prove_induction_comparison(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool, u32)> {
    let [comparison, cast, variable, bound, ..] = nodes else {
        return None;
    };
    let operator = comparison.operation.as_deref()?;
    if !matches!(operator, "==" | "!=" | "<" | "<=" | ">" | ">=") {
        return None;
    }
    let name_end = induction_identifier_end(induction, at)?;
    let counter_type = if induction.unsigned {
        "u32"
    } else {
        "i32"
    };
    let right_offset = u32::try_from(induction.name.len())
        .ok()?
        .checked_add(2 + u32::try_from(operator.len()).ok()?)?;
    let right_start = at.start.checked_add(right_offset)?;
    let right_column = at.column.checked_add(right_offset)?;
    if comparison.id != at.id
        || comparison.parent != at.parent
        || comparison.kind != "binary-expression"
        || comparison.type_name.as_deref() != Some("i32")
        || comparison.reference.is_some()
        || !metadata_empty(comparison)
        || cast.id != comparison.id.checked_add(1)?
        || cast.parent != comparison.id
        || cast.kind != "cast-expression"
        || cast.type_name.as_deref() != Some(counter_type)
        || cast.operation.as_deref() != Some("lvalue-to-rvalue")
        || cast.reference.is_some()
        || !metadata_empty(cast)
        || !source_word(cast, at.start, name_end, at.line, at.column)
        || variable.id != cast.id.checked_add(1)?
        || variable.parent != cast.id
        || variable.kind != "declaration-reference-expression"
        || variable.type_name.as_deref() != Some(counter_type)
        || variable.operation.is_some()
        || variable.reference.as_deref() != Some(induction.reference)
        || !metadata_empty(variable)
        || variable.span != cast.span
    {
        return None;
    }
    let rhs = prove_for_literal_operand(
        bound,
        variable.id.checked_add(1)?,
        comparison.id,
        right_start,
        at.line,
        right_column,
        induction.unsigned,
        induction.source,
    )?;
    let operator_start = usize::try_from(name_end.checked_add(1)?).ok()?;
    let operator_end = operator_start.checked_add(operator.len())?;
    if induction.source.is_some_and(|witness| {
        witness.get(operator_start..operator_end) != Some(operator.as_bytes())
    }) || !source_word(
        comparison,
        at.start,
        bound.span.end.byte,
        at.line,
        at.column,
    ) {
        return None;
    }
    let selected = match operator {
        "==" => induction.value == rhs,
        "!=" => induction.value != rhs,
        "<" => induction.value < rhs,
        "<=" => induction.value <= rhs,
        ">" => induction.value > rhs,
        ">=" => induction.value >= rhs,
        _ => return None,
    };
    Some((4, selected, bound.span.end.byte))
}

// A C scalar test of the protected loop counter is pure even without an
// explicit comparison. Only the authenticated induction declaration is known;
// the latest byte read from the guest is never available to this proof.
fn prove_induction_truth(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool, u32)> {
    let [read, variable, ..] = nodes else {
        return None;
    };
    let end = induction_identifier_end(induction, at)?;
    // C lvalue-to-rvalue reads retain the protected declaration's scalar
    // type; truth conversion itself does not change that Clang annotation.
    let counter_type = if induction.unsigned {
        "u32"
    } else {
        "i32"
    };
    if read.id != at.id
        || read.parent != at.parent
        || read.kind != "cast-expression"
        || read.type_name.as_deref() != Some(counter_type)
        || read.operation.as_deref() != Some("lvalue-to-rvalue")
        || read.reference.is_some()
        || !metadata_empty(read)
        || !source_word(read, at.start, end, at.line, at.column)
        || variable.id != read.id.checked_add(1)?
        || variable.parent != read.id
        || variable.kind != "declaration-reference-expression"
        || variable.type_name.as_deref() != Some(counter_type)
        || variable.reference.as_deref() != Some(induction.reference)
        || variable.operation.is_some()
        || !metadata_empty(variable)
        || !source_word(variable, at.start, end, at.line, at.column)
    {
        return None;
    }
    Some((2, induction.value != 0, end))
}

// Parentheses and Boolean negation are checked against their exact Clang
// child and source extent. Their operand can itself contain induction
// comparisons; a runtime guest value is never evaluated at compile time.
fn prove_induction_prefix(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool, u32)> {
    let node = nodes.first()?;
    let parenthesized = node.kind == "parenthesized-expression";
    if !parenthesized
        && (node.kind != "unary-expression"
            || node.operation.as_deref() != Some("!"))
    {
        return None;
    }
    if node.id != at.id
        || node.parent != at.parent
        || node.type_name.as_deref() != Some("i32")
        || node.reference.is_some()
        || !metadata_empty(node)
        || (parenthesized && node.operation.is_some())
    {
        return None;
    }
    source_induction_bytes(
        induction,
        at.start,
        if parenthesized {
            "("
        } else {
            "!"
        },
    )?;
    let child_at = at.child(
        at.id.checked_add(1)?,
        at.start.checked_add(1)?,
        at.column.checked_add(1)?,
    )?;
    let (inner_width, inner_value, inner_end) =
        prove_induction_value(nodes.get(1..)?, child_at, induction)?;
    if parenthesized {
        source_induction_bytes(induction, inner_end, ")")?;
    }
    let width = inner_width.checked_add(1)?;
    let end = if parenthesized {
        inner_end.checked_add(1)?
    } else {
        inner_end
    };
    (width <= MAX_STATIC_PREDICATE_NODES
        && source_word(node, at.start, end, at.line, at.column))
    .then_some((
        width,
        if parenthesized {
            inner_value
        } else {
            !inner_value
        },
        end,
    ))
}

// The original C spelling must bind every induction predicate operator and
// grouping delimiter. Span length cannot distinguish && from || or ! from +.
fn source_induction_bytes(
    induction: StaticInduction<'_>,
    start: u32,
    spelling: &str,
) -> Option<()> {
    if let Some(source) = induction.source {
        let start = usize::try_from(start).ok()?;
        (source.get(start..start.checked_add(spelling.len())?)
            == Some(spelling.as_bytes()))
        .then_some(())?;
    }
    Some(())
}

fn source_induction_operator(
    induction: StaticInduction<'_>,
    preceding_end: u32,
    spelling: &str,
) -> Option<()> {
    source_induction_bytes(induction, preceding_end.checked_add(1)?, spelling)
}

// Grouping and logical negation remain pure when the child is pure, even if
// the child's evaluation would be undefined. Verify original punctuation,
// preorder, source coordinates and the entire skipped child before accepting
// the shape. No unchecked value may escape this proof.
fn prove_skipped_induction_prefix_shape(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, u32)> {
    let node = nodes.first()?;
    let grouped = node.kind == "parenthesized-expression";
    if !grouped
        && (node.kind != "unary-expression"
            || node.operation.as_deref() != Some("!"))
    {
        return None;
    }
    if node.id != at.id
        || node.parent != at.parent
        || node.type_name.as_deref() != Some("i32")
        || node.reference.is_some()
        || !metadata_empty(node)
        || (grouped && node.operation.is_some())
    {
        return None;
    }
    source_induction_bytes(
        induction,
        at.start,
        if grouped {
            "("
        } else {
            "!"
        },
    )?;
    let inner_at = at.child(
        at.id.checked_add(1)?,
        at.start.checked_add(1)?,
        at.column.checked_add(1)?,
    )?;
    let (inner_width, inner_end) =
        prove_skipped_induction_shape(nodes.get(1..)?, inner_at, induction)?;
    if grouped {
        source_induction_bytes(induction, inner_end, ")")?;
    }
    let end = if grouped {
        inner_end.checked_add(1)?
    } else {
        inner_end
    };
    let width = inner_width.checked_add(1)?;
    (width <= MAX_STATIC_PREDICATE_NODES
        && source_word(node, at.start, end, at.line, at.column))
    .then_some((width, end))
}

// Every skipped C expression must retain pure source/Clang ancestry. Basic
// arithmetic, comparisons and grouping have direct shape-only proofs. Other
// supported expressions may use a different defined counter witness, but
// that witness value is always discarded, never used to select guest effects.
// Unsupported or effectful expressions still refuse conservatively.
fn prove_skipped_induction_shape(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, u32)> {
    (at.depth < MAX_STATIC_PREDICATE_DEPTH && induction.source.is_some())
        .then_some(())?;
    // The same source- and Clang-authenticated primitive induction arithmetic
    // remains pure even if its actual evaluation would be undefined. Do not
    // invent a substitute value: the caller can use this shape only for a C
    // operand proven not to execute.
    if let Some((width, _, end)) =
        prove_induction_arithmetic_shape(nodes, at, induction)
    {
        return Some((width, end));
    }
    if let Some((width, _, end)) =
        prove_induction_arithmetic_comparison_shape(nodes, at, induction)
    {
        return Some((width, end));
    }
    if let Some((width, end)) =
        prove_skipped_induction_prefix_shape(nodes, at, induction)
    {
        return Some((width, end));
    }
    [0i32, 1i32, -1i32].into_iter().find_map(|value| {
        prove_induction_value(nodes, at, StaticInduction { value, ..induction })
            .map(|(width, _, end)| (width, end))
    })
}

// Validate source punctuation recursively; complete node shape and values
// have already passed the independent bounded static-expression evaluator.
fn authenticate_induction_static_prefix(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
    width: usize,
) -> Option<()> {
    let grouped = nodes.first()?.kind == "parenthesized-expression";
    source_induction_bytes(
        induction,
        at.start,
        if grouped {
            "("
        } else {
            "!"
        },
    )?;
    let child_at = at.child(
        at.id.checked_add(1)?,
        at.start.checked_add(1)?,
        at.column.checked_add(1)?,
    )?;
    let (child_width, _) =
        prove_induction_static_value(nodes.get(1..)?, child_at, induction)?;
    if grouped {
        source_induction_bytes(induction, nodes.get(1)?.span.end.byte, ")")?;
    }
    (child_width.checked_add(1)? == width).then_some(())
}

fn induction_static_binary_right_location(
    at: StaticValueLocation,
    left: &Node,
    operator: &str,
    right_index: usize,
) -> Option<StaticValueLocation> {
    let gap = u32::try_from(operator.len()).ok()?.checked_add(2)?;
    at.child(
        at.id.checked_add(u32::try_from(right_index).ok()?)?,
        left.span.end.byte.checked_add(gap)?,
        left.span.end.column.checked_add(gap)?,
    )
}

fn authenticate_induction_static_binary(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
    width: usize,
) -> Option<()> {
    let left_at = at.child(at.id.checked_add(1)?, at.start, at.column)?;
    let (left_width, _) =
        prove_induction_static_value(nodes.get(1..)?, left_at, induction)?;
    let left = nodes.get(1)?;
    let operator = nodes.first()?.operation.as_deref()?;
    source_induction_operator(induction, left.span.end.byte, operator)?;
    let right_index = left_width.checked_add(1)?;
    let right_at = induction_static_binary_right_location(
        at,
        left,
        operator,
        right_index,
    )?;
    let (right_width, _) = prove_induction_static_value(
        nodes.get(right_index..)?,
        right_at,
        induction,
    )?;
    (right_index.checked_add(right_width)? == width).then_some(())
}

// Static constants inside source-backed induction predicates must have the
// same spelling as their original C tokens, not just plausible Clang spans.
// A forged constant-only subtree can otherwise change a compile-time branch
// decision while passing the normalized source digest check.
fn prove_induction_static_value(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, i32)> {
    let (width, value) = prove_static_value(nodes, at)?;
    if induction.source.is_none() {
        return Some((width, value));
    }
    let node = nodes.first()?;
    match node.kind.as_str() {
        "integer-literal" => {
            source_induction_bytes(
                induction,
                at.start,
                node.literal.as_deref()?,
            )?;
        },
        "unary-expression" | "parenthesized-expression" => {
            authenticate_induction_static_prefix(nodes, at, induction, width)?;
        },
        "binary-expression" => {
            authenticate_induction_static_binary(nodes, at, induction, width)?;
        },
        _ => return None,
    }
    Some((width, value))
}

// A selected C operand needs its actual value. An unselected operand still
// needs a complete independent pure/source/Clang proof, but its actual C
// arithmetic may be undefined without affecting the enclosing expression.
fn prove_induction_arm(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
    selected: bool,
) -> Option<InductionArmProof> {
    match prove_induction_value(nodes, at, induction) {
        Some((width, value, end)) => {
            Some((width, selected.then_some(value), end))
        },
        None if !selected => {
            prove_skipped_induction_shape(nodes, at, induction)
                .map(|(width, end)| (width, None, end))
        },
        None => None,
    }
}

// Clang's conditional-expression has three direct subtrees in preorder.
// Every arm must be independently source-proven even if that arm is never
// selected by the finite induction value. ` ? ` and ` : ` are exact token
// gaps; guest input and side effects cannot participate in these branches.
fn prove_induction_ternary(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool, u32)> {
    let ternary = nodes.first()?;
    if ternary.id != at.id
        || ternary.parent != at.parent
        || ternary.kind != "conditional-expression"
        || ternary.type_name.as_deref() != Some("i32")
        || ternary.operation.is_some()
        || ternary.reference.is_some()
        || !metadata_empty(ternary)
    {
        return None;
    }
    let condition_at = at.child(at.id.checked_add(1)?, at.start, at.column)?;
    let (condition_width, condition, condition_end) =
        prove_induction_value(nodes.get(1..)?, condition_at, induction)?;
    source_induction_operator(induction, condition_end, "?")?;
    let true_index = condition_width.checked_add(1)?;
    let true_start = condition_end.checked_add(3)?;
    let true_at = at.child(
        at.id.checked_add(u32::try_from(true_index).ok()?)?,
        true_start,
        at.column.checked_add(true_start.checked_sub(at.start)?)?,
    )?;
    let (true_width, true_value, true_end) = prove_induction_arm(
        nodes.get(true_index..)?,
        true_at,
        induction,
        condition,
    )?;
    source_induction_operator(induction, true_end, ":")?;
    let false_index = true_index.checked_add(true_width)?;
    let false_start = true_end.checked_add(3)?;
    let false_at = at.child(
        at.id.checked_add(u32::try_from(false_index).ok()?)?,
        false_start,
        at.column.checked_add(false_start.checked_sub(at.start)?)?,
    )?;
    let (false_width, false_value, false_end) = prove_induction_arm(
        nodes.get(false_index..)?,
        false_at,
        induction,
        !condition,
    )?;
    let width = false_index.checked_add(false_width)?;
    (width <= MAX_STATIC_PREDICATE_NODES
        && source_word(ternary, at.start, false_end, at.line, at.column))
    .then_some((
        width,
        if condition {
            true_value?
        } else {
            false_value?
        },
        false_end,
    ))
}

// Short-circuit only the integer value: validate the entire C source and
// pinned AST, even for a branch whose arithmetic need not be defined.
fn prove_induction_logical(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool, u32)> {
    let node = nodes.first()?;
    if node.id != at.id
        || node.parent != at.parent
        || node.type_name.as_deref() != Some("i32")
        || node.reference.is_some()
        || !metadata_empty(node)
    {
        return None;
    }
    let operator = node.operation.as_deref()?;
    let left_at = at.child(at.id.checked_add(1)?, at.start, at.column)?;
    let (left_width, left, left_end) =
        prove_induction_value(nodes.get(1..)?, left_at, induction)?;
    let right_index = left_width.checked_add(1)?;
    source_induction_operator(induction, left_end, operator)?;
    let right_start = left_end.checked_add(4)?;
    let right_at = at.child(
        at.id.checked_add(u32::try_from(right_index).ok()?)?,
        right_start,
        at.column
            .checked_add(left_end.checked_sub(at.start)?)?
            .checked_add(4)?,
    )?;
    let short_circuited = if operator == "&&" {
        !left
    } else {
        left
    };
    let (right_width, right, right_end) = prove_induction_arm(
        nodes.get(right_index..)?,
        right_at,
        induction,
        !short_circuited,
    )?;
    let width = right_index.checked_add(right_width)?;
    if width > MAX_STATIC_PREDICATE_NODES
        || !source_word(node, at.start, right_end, at.line, at.column)
    {
        return None;
    }
    let selected = if short_circuited {
        left
    } else {
        right?
    };
    Some((width, selected, right_end))
}

// Each selected enclosing counter retains its source token, Clang declaration
// binding and value, including when the intermediate loop has a different name.
fn enclosing_induction(
    induction: StaticInduction<'_>,
) -> Option<StaticInduction<'_>> {
    let counter = induction.outer?;
    Some(StaticInduction {
        reference: counter.reference,
        name: counter.name,
        source: induction.source,
        unsigned: counter.unsigned,
        value: counter.value,
        outer: induction.outermost,
        outermost: None,
    })
}

fn induction_scopes<'name>(
    induction: StaticInduction<'name>,
) -> impl Iterator<Item = StaticInduction<'name>> {
    std::iter::successors(Some(induction), |scope| enclosing_induction(*scope))
}

// Admit only fully proven, pure logical combinations of exact induction
// comparisons or already-proven source constants. Both sides are authenticated
// regardless of short-circuit selection, so no effect can hide on an arm.
fn prove_induction_value(
    nodes: &[Node],
    at: StaticValueLocation,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool, u32)> {
    if at.depth >= MAX_STATIC_PREDICATE_DEPTH {
        return None;
    }
    let node = nodes.first()?;
    if node.kind == "binary-expression"
        && matches!(node.operation.as_deref(), Some("&&" | "||"))
    {
        return prove_induction_logical(nodes, at, induction);
    }
    if node.kind == "conditional-expression" {
        return prove_induction_ternary(nodes, at, induction);
    }
    if node.kind == "cast-expression" {
        return induction_scopes(induction)
            .find_map(|counter| prove_induction_truth(nodes, at, counter));
    }
    if node.kind == "binary-expression"
        && matches!(
            node.operation.as_deref(),
            Some("%" | "/" | "+" | "-" | "*" | "&" | "^" | "|")
        )
    {
        let (width, value, end) =
            induction_scopes(induction).find_map(|counter| {
                prove_induction_arithmetic(nodes, at, counter)
            })?;
        return Some((width, value != 0, end));
    }
    if let Some((width, value)) =
        prove_induction_static_value(nodes, at, induction)
    {
        return Some((width, value != 0, node.span.end.byte));
    }
    if matches!(
        node.kind.as_str(),
        "unary-expression" | "parenthesized-expression"
    ) {
        return prove_induction_prefix(nodes, at, induction);
    }
    induction_scopes(induction).find_map(|counter| {
        prove_induction_arithmetic_comparison(nodes, at, counter)
            .or_else(|| prove_induction_comparison(nodes, at, counter))
    })
}

fn prove_induction_predicate(
    nodes: &[Node],
    conditional: &Node,
    induction: StaticInduction<'_>,
) -> Option<(usize, bool)> {
    let begin = &conditional.span.begin;
    let (width, selected, _) = prove_induction_value(
        nodes,
        StaticValueLocation {
            id: conditional.id.checked_add(1)?,
            parent: conditional.id,
            start: begin.byte.checked_add(4)?,
            line: begin.line,
            column: begin.column.checked_add(4)?,
            depth: 0,
        },
        induction,
    )?;
    Some((width, selected))
}

// All static predicates are pure, bounded expression trees. Prove every
// operand even for `&&` and `||`: skipping an unknown side effect is unsafe.
fn prove_static_predicate(
    nodes: &[Node],
    conditional: &Node,
    induction: Option<StaticInduction<'_>>,
) -> Option<(usize, bool)> {
    if let Some(static_induction) = induction {
        // An entire branch can use only an enclosing counter. Retain every
        // complete source/Clang proof instead of guessing a counter value.
        if let Some(result) =
            induction_scopes(static_induction).find_map(|counter| {
                prove_induction_predicate(nodes, conditional, counter)
            })
        {
            return Some(result);
        }
        // Preserve fully constant predicates that the induction-specific
        // logical grammar does not admit, but never reenter the AST-only
        // projector after a source-backed proof fails.
        if static_induction.source.is_some() {
            let begin = &conditional.span.begin;
            let (width, value) = prove_induction_static_value(
                nodes,
                StaticValueLocation {
                    id: conditional.id.checked_add(1)?,
                    parent: conditional.id,
                    start: begin.byte.checked_add(4)?,
                    line: begin.line,
                    column: begin.column.checked_add(4)?,
                    depth: 0,
                },
                static_induction,
            )?;
            return Some((width, value != 0));
        }
    }
    let begin = &conditional.span.begin;
    let (width, value) = prove_static_value(nodes, StaticValueLocation {
        id: conditional.id.checked_add(1)?,
        parent: conditional.id,
        start: begin.byte.checked_add(4)?,
        line: begin.line,
        column: begin.column.checked_add(4)?,
        depth: 0,
    })?;
    Some((width, value != 0))
}

// C converts a signed int to unsigned char modulo 256, then promotes the
// resulting u8 back to signed int at putchar's call boundary. The two cast
// nodes must cover the *same* original `(unsigned char)` source expression;
// no source-independent AST cast annotation is sufficient. The nested
// expression may perform checked signed arithmetic, but never guest I/O.
#[expect(
    clippy::too_many_arguments,
    reason = "authenticate both Clang casts and the nested C byte expression"
)]
fn prove_total_byte_narrowing(
    nodes: &[Node],
    body: &Node,
    previous: u32,
    parent: u32,
    expected_id: u32,
    local: Option<&LocalDeclaration<'_>>,
    depth: usize,
    source: &[u8],
) -> Option<TotalByteGuardProof> {
    let [promoted, narrowed, rest @ ..] = nodes else {
        return None;
    };
    if !pure_integer_root(promoted, "cast-expression", parent, expected_id)
        || promoted.operation.as_deref() != Some("integral-cast")
        || narrowed.id != promoted.id.checked_add(1)?
        || narrowed.parent != promoted.id
        || narrowed.kind != "cast-expression"
        || narrowed.type_name.as_deref() != Some("u8")
        || narrowed.operation.as_deref() != Some("integral-cast")
        || narrowed.reference.is_some()
        || !metadata_empty(narrowed)
        || narrowed.span != promoted.span
    {
        return None;
    }
    let (child_width, child, values) = prove_total_byte_guard(
        rest,
        body,
        previous,
        narrowed.id,
        narrowed.id.checked_add(1)?,
        local,
        depth.checked_add(1)?,
        source,
    )?;
    let spelling = format!("(unsigned char){child}");
    pure_expression_source(promoted, &spelling, source)?;
    pure_expression_source(narrowed, &spelling, source)?;
    let mut narrowed_values = Box::new([None; 256]);
    for (result, value) in narrowed_values.iter_mut().zip(values.iter()) {
        *result = value.map(|signed| signed.rem_euclid(256));
    }
    let width = child_width.checked_add(2)?;
    (width <= MAX_STATIC_PREDICATE_NODES).then_some((
        width,
        spelling,
        narrowed_values,
    ))
}

// Successful getchar/putchar returns are in [0, 255]. Prove a pure
// predicate's complete truth set over that finite domain, then select a
// statement only if all bytes agree. This includes tautologies whose leaves
// individually depend on the guest input. Neither the byte's actual value
// nor a guest conditional is predicted at compile time. Every operand must
// be pure and source-authenticated; only executed operands must be defined.
#[expect(
    clippy::too_many_arguments,
    reason = "verify each Clang parent and source-backed byte-range predicate"
)]
fn prove_total_byte_guard(
    nodes: &[Node],
    body: &Node,
    previous: u32,
    parent: u32,
    expected_id: u32,
    local: Option<&LocalDeclaration<'_>>,
    depth: usize,
    source: &[u8],
) -> Option<TotalByteGuardProof> {
    (depth < MAX_STATIC_PREDICATE_DEPTH).then_some(())?;
    let root = nodes.first()?;
    // Grouping preserves an exact i32 value. Signed unary +, -, bitwise ~
    // and logical ! must also preserve the C integer result, not merely
    // truthiness. Checked negation rejects INT_MIN at any possible byte.
    // Neither effects nor source/Clang evidence can be skipped.
    if root.kind == "parenthesized-expression"
        || (root.kind == "unary-expression"
            && matches!(root.operation.as_deref(), Some("!" | "+" | "-" | "~")))
    {
        if !pure_integer_root(root, &root.kind, parent, expected_id)
            || (root.kind == "parenthesized-expression"
                && root.operation.is_some())
        {
            return None;
        }
        let (child_width, child, child_values) = prove_total_byte_guard(
            nodes.get(1..)?,
            body,
            previous,
            root.id,
            root.id.checked_add(1)?,
            local,
            depth.checked_add(1)?,
            source,
        )?;
        let operator = root.operation.as_deref();
        let spelling = if root.kind == "parenthesized-expression" {
            format!("({child})")
        } else {
            format!("{}{child}", operator?)
        };
        pure_expression_source(root, &spelling, source)?;
        let values = if root.kind == "parenthesized-expression" {
            child_values
        } else {
            let mut results = Box::new([None; 256]);
            for (result, possible_operand) in
                results.iter_mut().zip(child_values.iter().copied())
            {
                *result =
                    possible_operand.and_then(|operand| match operator? {
                        "!" => Some(i32::from(operand == 0i32)),
                        "+" => Some(operand),
                        "-" => operand.checked_neg(),
                        "~" => Some(!operand),
                        _ => None,
                    });
            }
            results
        };
        // Clang folds a literal unary expression such as `-1` into an
        // annotated constant. Treat the annotation as another checkable
        // claim, never as authority to replace actual guest-byte values.
        if let Some(annotation) = root.constant_integer.as_deref() {
            let constant = annotation.parse::<i32>().ok()?;
            (constant.to_string() == annotation
                && values.iter().all(|value| {
                    value.is_none_or(|actual| actual == constant)
                }))
            .then_some(())?;
        }
        let width = child_width.checked_add(1)?;
        return (width <= MAX_STATIC_PREDICATE_NODES)
            .then_some((width, spelling, values));
    }
    if root.kind == "cast-expression"
        && root.operation.as_deref() == Some("integral-cast")
    {
        return prove_total_byte_narrowing(
            nodes,
            body,
            previous,
            parent,
            expected_id,
            local,
            depth,
            source,
        );
    }
    if root.kind == "conditional-expression" {
        return prove_total_byte_ternary(
            nodes,
            body,
            previous,
            parent,
            expected_id,
            local,
            depth,
            source,
        );
    }
    if root.kind == "binary-expression"
        && matches!(
            root.operation.as_deref(),
            Some(
                "&&" | "||"
                    | "^"
                    | "&"
                    | "|"
                    | "+"
                    | "-"
                    | "*"
                    | "/"
                    | "%"
                    | "<<"
                    | ">>"
                    | "=="
                    | "!="
                    | "<"
                    | "<="
                    | ">"
                    | ">="
            )
        )
    {
        let compound = prove_total_byte_binary(
            nodes,
            body,
            previous,
            parent,
            expected_id,
            local,
            depth,
            source,
        );
        if compound.is_some() {
            return compound;
        }
        // Keep the older source-checked byte/mask and zero-test leaf path;
        // arithmetic remains closed if its complete proof cannot be made.
    }
    if matches!(root.operation.as_deref(), Some("==" | "!="))
        && let Some(proof) = prove_total_byte_zero_comparison(
            nodes,
            body,
            previous,
            parent,
            expected_id,
            local,
            depth,
            source,
        )
    {
        return Some(proof);
    }
    prove_total_byte_leaf(
        nodes,
        body,
        previous,
        parent,
        expected_id,
        local,
        depth,
        source,
    )
}

// Source-checked comparison with zero converts any proven pure integer
// predicate into an exact 0/1 C result. The proof does not require the
// underlying mask's value to be Boolean (e.g. `current & 2`).
#[expect(
    clippy::too_many_arguments,
    reason = "preserve source and Clang ancestry for the zero comparison"
)]
fn prove_total_byte_zero_comparison(
    nodes: &[Node],
    body: &Node,
    previous: u32,
    parent: u32,
    expected_id: u32,
    local: Option<&LocalDeclaration<'_>>,
    depth: usize,
    source: &[u8],
) -> Option<TotalByteGuardProof> {
    let root = nodes.first()?;
    let operator = root.operation.as_deref()?;
    pure_integer_root(root, "binary-expression", parent, expected_id)
        .then_some(())?;
    let (left_width, left, left_values) = prove_total_byte_guard(
        nodes.get(1..)?,
        body,
        previous,
        root.id,
        root.id.checked_add(1)?,
        local,
        depth.checked_add(1)?,
        source,
    )?;
    let index = left_width.checked_add(1)?;
    let digits = pure_guard_decimal_literal(
        nodes.get(index)?,
        root,
        index,
        left.len().checked_add(operator.len())?.checked_add(2)?,
    )?;
    (digits == "0").then_some(())?;
    let spelling = format!("{left} {operator} 0");
    pure_expression_source(root, &spelling, source)?;
    let values = match operator {
        "==" => Box::new(
            (*left_values)
                .map(|value| value.map(|actual| i32::from(actual == 0i32))),
        ),
        "!=" => Box::new(
            (*left_values)
                .map(|value| value.map(|actual| i32::from(actual != 0i32))),
        ),
        _ => return None,
    };
    let width = index.checked_add(1)?;
    (width <= MAX_STATIC_PREDICATE_NODES).then_some((width, spelling, values))
}

// Reconstruct both pure integer operands in Clang preorder, then verify the
// original C spelling and i32 parent. Every successful byte must have a
// well-defined result; overflow, invalid shifts and zero divisors reject.
fn checked_c_byte_guard_binary(
    operator: &str,
    left: i32,
    right: i32,
) -> Option<i32> {
    match operator {
        "+" => left.checked_add(right),
        "-" => left.checked_sub(right),
        "*" => left.checked_mul(right),
        "/" => left.checked_div(right),
        "%" => left.checked_rem(right),
        "<<" => {
            // Signed left shifts must have a nonnegative operand and a
            // representable result in signed 32-bit C int.
            (left >= 0).then_some(())?;
            let shift = u32::try_from(right).ok()?;
            (shift < 32).then_some(())?;
            i32::try_from(i64::from(left).checked_shl(shift)?).ok()
        },
        ">>" => {
            // Right shift of a negative signed value is implementation-
            // defined; this proof only admits portable positive shifts.
            (left >= 0).then_some(())?;
            let shift = u32::try_from(right).ok()?;
            (shift < 32).then_some(left >> shift)
        },
        "^" => Some(left ^ right),
        "&" => Some(left & right),
        "|" => Some(left | right),
        "==" => Some(i32::from(left == right)),
        "!=" => Some(i32::from(left != right)),
        "<" => Some(i32::from(left < right)),
        "<=" => Some(i32::from(left <= right)),
        ">" => Some(i32::from(left > right)),
        ">=" => Some(i32::from(left >= right)),
        "&&" => Some(i32::from(left != 0 && right != 0)),
        "||" => Some(i32::from(left != 0 || right != 0)),
        _ => None,
    }
}

// Reconstruct both pure operands in Clang preorder, then verify the exact
// original C spelling and i32 parent before selecting either statement arm.
#[expect(
    clippy::too_many_arguments,
    reason = "retain both operand contexts and exact parent/source evidence"
)]
fn prove_total_byte_binary(
    nodes: &[Node],
    body: &Node,
    previous: u32,
    parent: u32,
    expected_id: u32,
    local: Option<&LocalDeclaration<'_>>,
    depth: usize,
    source: &[u8],
) -> Option<TotalByteGuardProof> {
    let root = nodes.first()?;
    let operator = root.operation.as_deref()?;
    pure_integer_root(root, "binary-expression", parent, expected_id)
        .then_some(())?;
    let (left_width, left, left_values) = prove_total_byte_guard(
        nodes.get(1..)?,
        body,
        previous,
        root.id,
        root.id.checked_add(1)?,
        local,
        depth.checked_add(1)?,
        source,
    )?;
    let right_index = left_width.checked_add(1)?;
    let (right_width, right, right_values) = prove_total_byte_guard(
        nodes.get(right_index..)?,
        body,
        previous,
        root.id,
        root.id.checked_add(u32::try_from(right_index).ok()?)?,
        local,
        depth.checked_add(1)?,
        source,
    )?;
    let width = right_index.checked_add(right_width)?;
    (width <= MAX_STATIC_PREDICATE_NODES).then_some(())?;
    let spelling = format!("{left} {operator} {right}");
    pure_expression_source(root, &spelling, source)?;
    let mut values = Box::new([None; 256]);
    for ((result, left_operand), right_operand) in values
        .iter_mut()
        .zip(left_values.iter().copied())
        .zip(right_values.iter().copied())
    {
        *result = match left_operand {
            None => None,
            Some(0i32) if operator == "&&" => Some(0i32),
            Some(lhs) if operator == "||" && lhs != 0i32 => Some(1i32),
            Some(lhs) => right_operand.and_then(|rhs| {
                checked_c_byte_guard_binary(operator, lhs, rhs)
            }),
        };
    }
    Some((width, spelling, values))
}

// C's conditional expression chooses its second or third operand separately
// for every successful guest byte. Each subtree must be pure and independently
// source-proven, including the arm that a particular byte would not execute.
// The compiler only folds the finite predicate truth set, never a guest value.
#[expect(
    clippy::too_many_arguments,
    reason = "verify each conditional subtree against its source and parent"
)]
fn prove_total_byte_ternary(
    nodes: &[Node],
    body: &Node,
    previous: u32,
    parent: u32,
    expected_id: u32,
    local: Option<&LocalDeclaration<'_>>,
    depth: usize,
    source: &[u8],
) -> Option<TotalByteGuardProof> {
    let root = nodes.first()?;
    (pure_integer_root(root, "conditional-expression", parent, expected_id)
        && root.operation.is_none())
    .then_some(())?;
    let (condition_width, condition, condition_values) =
        prove_total_byte_guard(
            nodes.get(1..)?,
            body,
            previous,
            root.id,
            root.id.checked_add(1)?,
            local,
            depth.checked_add(1)?,
            source,
        )?;
    let true_index = condition_width.checked_add(1)?;
    let (true_width, when_true, true_values) = prove_total_byte_guard(
        nodes.get(true_index..)?,
        body,
        previous,
        root.id,
        root.id.checked_add(u32::try_from(true_index).ok()?)?,
        local,
        depth.checked_add(1)?,
        source,
    )?;
    let false_index = true_index.checked_add(true_width)?;
    let (false_width, when_false, false_values) = prove_total_byte_guard(
        nodes.get(false_index..)?,
        body,
        previous,
        root.id,
        root.id.checked_add(u32::try_from(false_index).ok()?)?,
        local,
        depth.checked_add(1)?,
        source,
    )?;
    let width = false_index.checked_add(false_width)?;
    (width <= MAX_STATIC_PREDICATE_NODES).then_some(())?;
    let spelling = format!("{condition} ? {when_true} : {when_false}");
    pure_expression_source(root, &spelling, source)?;
    let mut values = Box::new([None; 256]);
    for (((result, condition_value), true_value), false_value) in values
        .iter_mut()
        .zip(condition_values.iter().copied())
        .zip(true_values.iter().copied())
        .zip(false_values.iter().copied())
    {
        *result = match condition_value {
            Some(0i32) => false_value,
            Some(_) => true_value,
            None => None,
        };
    }
    Some((width, spelling, values))
}

// Bind a pure i32 predicate literal to its exact C23 token and Clang value.
// The normalized node holds a decimal value, but its source may be radix-
// spelled; the token parser is shared with the frontend source identity gate.
fn source_proven_byte_guard_literal(
    node: &Node,
    expected_id: u32,
    parent: u32,
    source: &[u8],
) -> Option<(i32, String)> {
    let canonical = node.literal.as_deref()?;
    let value = canonical.parse::<i32>().ok()?;
    let start = node.span.begin.byte;
    let end = node.span.end.byte;
    let token =
        source.get(usize::try_from(start).ok()?..usize::try_from(end).ok()?)?;
    if !(value >= 0
        && canonical == value.to_string()
        && super::source_integer_token_value(token)?
            == u64::try_from(value).ok()?
        && node.id == expected_id
        && node.parent == parent
        && node.kind == "integer-literal"
        && node.type_name.as_deref() == Some("i32")
        && node.operation.is_none()
        && node.reference.is_none()
        && node.name.is_none()
        && node.definition.is_none()
        && node.inline_specified.is_none()
        && node.linkage.is_none()
        && node.storage_class.is_none()
        && node.storage_duration.is_none()
        && node.constant_integer.as_deref() == Some(canonical)
        && source_word(
            node,
            start,
            end,
            node.span.begin.line,
            node.span.begin.column,
        ))
    {
        return None;
    }
    Some((value, str::from_utf8(token).ok()?.to_owned()))
}

// Every leaf is an exact pure Clang/source predicate of the same resident
// byte. Enumerate the entire 256-value successful-input domain, rather than
// approximating with independently constant leaves. A bitmap keeps logical
// composition exact even when each leaf changes truth over that domain.
#[expect(
    clippy::too_many_arguments,
    reason = "bind the leaf's source, operand and Clang parent provenance"
)]
fn prove_total_byte_leaf(
    nodes: &[Node],
    body: &Node,
    previous: u32,
    parent: u32,
    expected_id: u32,
    local: Option<&LocalDeclaration<'_>>,
    depth: usize,
    source: &[u8],
) -> Option<TotalByteGuardProof> {
    // A canonical C integer literal has one truth value for every successful
    // guest byte. Recover its exact original spelling and pinned Clang node,
    // rather than trusting a host-calculated constant detached from source.
    let root = nodes.first()?;
    if root.kind == "integer-literal" {
        let (value, spelling) = source_proven_byte_guard_literal(
            root,
            expected_id,
            parent,
            source,
        )?;
        pure_expression_source(root, &spelling, source)?;
        return Some((1, spelling, Box::new([Some(value); 256])));
    }
    // A source-authenticated identity is true for precisely the nonzero
    // successful bytes. Its proven zero test has the complementary set.
    // This admits `current || !current` without inventing guest control.
    if let Some((width, spelling, nonzero)) = prove_byte_zero_guard(
        nodes,
        local,
        body,
        previous,
        parent,
        expected_id,
        depth.checked_add(1)?,
        source,
    ) {
        let mut values = Box::new([None; 256]);
        for (byte, value) in values.iter_mut().enumerate() {
            let signed_byte = i32::try_from(byte).ok()?;
            *value = Some(if root.operation.as_deref() == Some("!=") {
                i32::from(signed_byte != 0)
            } else if nonzero {
                signed_byte
            } else {
                i32::from(signed_byte == 0)
            });
        }
        return (width <= MAX_STATIC_PREDICATE_NODES)
            .then_some((width, spelling, values));
    }
    let root = nodes.first()?;
    let (width, spelling) = prove_pure_byte_guard(
        nodes,
        local,
        body,
        previous,
        parent,
        expected_id,
        depth.checked_add(1)?,
        source,
    )?;
    let literal = nodes
        .get(width.checked_sub(1)?)?
        .literal
        .as_deref()?
        .parse::<i32>()
        .ok()?;
    let operation = root.operation.as_deref()?;
    let mut values = Box::new([None; 256]);
    for byte in 0i32..=255 {
        let value = match operation {
            "<" => i32::from(byte < literal),
            "<=" => i32::from(byte <= literal),
            ">" => i32::from(byte > literal),
            ">=" => i32::from(byte >= literal),
            "==" => i32::from(byte == literal),
            "!=" => i32::from(byte != literal),
            "&" => byte & literal,
            _ => return None,
        };
        values[usize::try_from(byte).ok()?] = Some(value);
    }
    (width <= MAX_STATIC_PREDICATE_NODES).then_some((width, spelling, values))
}

#[expect(
    clippy::too_many_arguments,
    reason = "retain the source and Clang predicate envelope context"
)]
fn prove_total_byte_if_predicate(
    nodes: &[Node],
    body: &Node,
    previous: u32,
    conditional: &Node,
    local: Option<&LocalDeclaration<'_>>,
    source: Option<&[u8]>,
) -> Option<(usize, Option<bool>, Box<[Option<i32>; 256]>)> {
    let (width, _, values) = prove_total_byte_guard(
        nodes,
        body,
        previous,
        conditional.id,
        conditional.id.checked_add(1)?,
        local,
        0,
        source?,
    )?;
    // No successful guest byte may execute an undefined integer operation.
    // Undefined values in unselected &&, || and ?: arms are harmless only
    // after the complete source/AST expression has been authenticated.
    if values.iter().any(Option::is_none) {
        return None;
    }
    let selected = if values
        .iter()
        .all(|value| value.is_some_and(|actual| actual != 0_i32))
    {
        Some(true)
    } else if values.iter().all(|value| *value == Some(0_i32)) {
        Some(false)
    } else {
        None
    };
    Some((width, selected, values))
}

// Two arms can be folded without predicting the guest byte only when their
// source-proven traces write that same resident byte the same number of times.
// No input, assignment, local storage update, or control exit is erased. The
// output nodes remain source-authenticated even though their spans differ.
fn equivalent_pure_byte_outputs(
    then_effects: &[StaticIfEffect<'_>],
    else_effects: &[StaticIfEffect<'_>],
) -> bool {
    !then_effects.is_empty()
        && then_effects.len() == else_effects.len()
        && then_effects.iter().zip(else_effects).all(|(left, right)| {
            left.input.is_none()
                && right.input.is_none()
                && left.assigned_local.is_none()
                && right.assigned_local.is_none()
                && left.loop_exit.is_none()
                && right.loop_exit.is_none()
                && !left.outputs.is_empty()
                && left.outputs.len() == right.outputs.len()
        })
}

// Preserve the complete authenticated output trace only when its contents
// cannot depend on a source-C branch that is still variable at guest runtime.
fn select_byte_if_effects<'node>(
    condition_true: Option<bool>,
    then_effects: Vec<StaticIfEffect<'node>>,
    else_effects: Vec<StaticIfEffect<'node>>,
) -> Option<Vec<StaticIfEffect<'node>>> {
    match condition_true {
        Some(true) => Some(then_effects),
        Some(false) => Some(else_effects),
        None if equivalent_pure_byte_outputs(&then_effects, &else_effects) => {
            Some(then_effects)
        },
        None => None,
    }
}

// Exact folded source-C predicates. Each bounded C call in both arms
// is authenticated before selecting guest effects. Invariant predicates
// over a successful guest byte also select an entire statement arm.

#[expect(
    clippy::too_many_lines,
    reason = "prove literal condition, both branch children and source spans"
)]
fn prove_static_if<'node>(
    nodes: &'node [Node],
    body: &Node,
    previous: u32,
    expected_id: u32,
    parent: u32,
    local: Option<&LocalDeclaration<'node>>,
    outer_aliases: &[LocalDeclaration<'node>],
    depth: usize,
    allow_new_local: bool,
    for_depth: usize,
    induction: Option<StaticInduction<'_>>,
    active_domain: Option<&[bool; 256]>,
    source: Option<&[u8]>,
) -> Option<StaticIfProof<'node>> {
    let [conditional, ..] = nodes else {
        return None;
    };
    let start = conditional.span.begin.byte;
    let line = conditional.span.begin.line;
    let column = conditional.span.begin.column;
    if depth >= MAX_STATIC_IF_DEPTH
        || start <= previous
        || start <= body.span.begin.byte
        || line == 0
        || column == 0
        || conditional.id != expected_id
        || conditional.parent != parent
        || conditional.kind != "if-statement"
        || conditional.type_name.is_some()
        || conditional.reference.is_some()
        || conditional.operation.is_some()
        || !metadata_empty(conditional)
    {
        return None;
    }
    // Clang locates an `else if` at its `if`, five columns after the
    // source's `else `. The nested unbraced calls and final `else` align
    // with the outer `else`, not with that inner `if` token. Accept the
    // deduction only from the original source bytes and exact coordinates.
    let alignment_column = if source.is_some_and(|witness| {
        let Ok(at) = usize::try_from(start) else {
            return false;
        };
        at.checked_sub(5).and_then(|begin| witness.get(begin..at))
            == Some(b"else ")
    }) {
        column.checked_sub(5)?
    } else {
        column
    };
    let (predicate_width, condition_true, domain) =
        prove_static_predicate(nodes.get(1..)?, conditional, induction)
            .map(|(width, selected)| (width, Some(selected), None))
            .or_else(|| {
                prove_total_byte_if_predicate(
                    nodes.get(1..)?,
                    body,
                    previous,
                    conditional,
                    local,
                    source,
                )
                .map(|(width, selected, values)| {
                    (width, selected, Some(values))
                })
            })?;
    // Each C arm inherits its enclosing byte constraints. Evaluating the
    // authenticated predicate for all 256 successful inputs prevents an
    // inactive nested arm from proving arithmetic on a reachable byte.
    let mut then_domain = [false; 256];
    let mut else_domain = [false; 256];
    for byte in 0..256 {
        if active_domain.is_none_or(|active| active[byte]) {
            let truth = match &domain {
                Some(values) => values[byte].is_some_and(|value| value != 0),
                None => condition_true?,
            };
            then_domain[byte] = truth;
            else_domain[byte] = !truth;
        }
    }
    let restricted = active_domain.is_some() || domain.is_some();
    let predicate_root = nodes.get(1)?;
    let predicate_last = nodes.get(predicate_width)?;
    let arm_offset = 1usize.checked_add(predicate_width)?;
    let rest = nodes.get(arm_offset..)?;
    let then_arm = prove_static_if_arm(
        rest,
        body,
        previous,
        predicate_last.id.checked_add(1)?,
        conditional.id,
        local,
        outer_aliases,
        depth,
        column,
        allow_new_local,
        for_depth,
        induction,
        condition_true == Some(false),
        restricted.then_some(&then_domain),
        source,
    )?;
    let then_inline = then_arm.begin
        == predicate_root.span.end.byte.checked_add(2)?
        && then_arm.begin_line == line
        && then_arm.begin_column
            == predicate_root.span.end.column.checked_add(2)?;
    // A direct (unbraced) C statement may follow on the next indented
    // line. The original bytes must be precisely `)`, LF and the four-space
    // deeper statement indentation; AST coordinates alone are insufficient.
    let then_multiline = !then_arm.braced
        && then_arm.begin_line == line.checked_add(1)?
        && then_arm.begin_column == alignment_column.checked_add(4)?
        && source.is_some_and(|witness| {
            let Some(indent) =
                usize::try_from(alignment_column.checked_add(3).unwrap_or(0))
                    .ok()
                    .filter(|amount| *amount <= 256)
            else {
                return false;
            };
            let expected = format!(")\n{}", " ".repeat(indent));
            match (
                usize::try_from(predicate_root.span.end.byte),
                usize::try_from(then_arm.begin),
            ) {
                (Ok(from), Ok(to)) => {
                    witness.get(from..to) == Some(expected.as_bytes())
                },
                _ => false,
            }
        });
    if !then_inline && !then_multiline {
        return None;
    }
    let mut width = arm_offset.checked_add(then_arm.width)?;
    let mut end = then_arm.end;
    let mut end_line = then_arm.end_line;
    let mut end_column = then_arm.end_column;
    let mut selected = condition_true.unwrap_or(false);
    let mut effects = then_arm.effects;
    if conditional.span.end.byte != then_arm.end {
        let else_arm = prove_static_if_arm(
            nodes.get(width..)?,
            body,
            then_arm.end,
            expected_id.checked_add(u32::try_from(width).ok()?)?,
            conditional.id,
            local,
            outer_aliases,
            depth,
            column,
            allow_new_local,
            for_depth,
            induction,
            condition_true == Some(true),
            restricted.then_some(&else_domain),
            source,
        )?;
        let else_gap = if then_arm.braced {
            6
        } else {
            7
        };
        let else_inline =
            else_arm.begin == then_arm.end.checked_add(else_gap)?;
        // The canonical unbraced multi-line spelling includes the first
        // call's semicolon, a same-indent `else`, and the indented call.
        // No unexamined C statement or token may hide between these spans.
        let else_if_multiline = !then_arm.braced
            && nodes.get(width)?.kind == "if-statement"
            && else_arm.begin_line == then_arm.end_line.checked_add(1)?
            && else_arm.begin_column == alignment_column.checked_add(5)?
            && source.is_some_and(|witness| {
                let Some(indent) = alignment_column
                    .checked_sub(1)
                    .and_then(|column| usize::try_from(column).ok())
                    .filter(|amount| *amount <= 256)
                else {
                    return false;
                };
                let expected = format!(";\n{}else ", " ".repeat(indent));
                match (
                    usize::try_from(then_arm.end),
                    usize::try_from(else_arm.begin),
                ) {
                    (Ok(from), Ok(to)) => {
                        witness.get(from..to) == Some(expected.as_bytes())
                    },
                    _ => false,
                }
            });
        let else_multiline = !then_arm.braced
            && else_arm.begin_line == then_arm.end_line.checked_add(2)?
            && else_arm.begin_column == alignment_column.checked_add(4)?
            && source.is_some_and(|witness| {
                let Some(indent) = alignment_column
                    .checked_sub(1)
                    .and_then(|column| usize::try_from(column).ok())
                    .filter(|amount| *amount <= 256)
                else {
                    return false;
                };
                let Some(call_indent) = indent.checked_add(4) else {
                    return false;
                };
                let expected = format!(
                    ";\n{}else\n{}",
                    " ".repeat(indent),
                    " ".repeat(call_indent),
                );
                match (
                    usize::try_from(then_arm.end),
                    usize::try_from(else_arm.begin),
                ) {
                    (Ok(from), Ok(to)) => {
                        witness.get(from..to) == Some(expected.as_bytes())
                    },
                    _ => false,
                }
            });
        if !else_inline && !else_if_multiline && !else_multiline {
            return None;
        }
        width = width.checked_add(else_arm.width)?;
        end = else_arm.end;
        end_line = else_arm.end_line;
        end_column = else_arm.end_column;
        selected = true;
        effects =
            select_byte_if_effects(condition_true, effects, else_arm.effects)?;
    } else if condition_true.is_none() {
        // A non-total guard without an else would skip these effects.
        return None;
    }
    let span_is_canonical = if end_line == line {
        source_word(conditional, start, end, line, column)
    } else {
        conditional.span.end.byte == end
            && conditional.span.end.line == end_line
            && conditional.span.end.column == end_column
    };
    if end >= body.span.end.byte || !span_is_canonical {
        return None;
    }
    Some(StaticIfProof {
        width,
        selected,
        effects,
        end,
    })
}

fn valid_envelope(input: &Artifact, function: &Node, body: &Node) -> bool {
    input.schema_version == 1
        && input.identity == super::EXPECTED_ARTIFACT
        && input.profile.abi_id == super::EXPECTED_ABI
        && input.profile.target_profile == super::EXPECTED_PROFILE
        && input.clang.version == "22.1.8"
        && input.clang.target == "wasm32-unknown-unknown"
        && input.clang.language == "c23"
        && !input.source.id.is_empty()
        && function.id == 1
        && function.parent == 0
        && function.kind == "function-declaration"
        && function
            .name
            .as_deref()
            .is_some_and(|name| !name.is_empty())
        && function.type_name.as_deref() == Some("fn()->void")
        && function.definition.as_deref() == Some("definition")
        && function.inline_specified == Some(false)
        && function.linkage.as_deref() == Some("external")
        && function.storage_class.as_deref() == Some("none")
        && function.storage_duration.is_none()
        && function.reference.is_none()
        && function.operation.is_none()
        && function.literal.is_none()
        && function.constant_integer.is_none()
        && body.id == 2
        && body.parent == 1
        && body.kind == "compound-statement"
        && body.type_name.is_none()
        && body.reference.is_none()
        && body.operation.is_none()
        && metadata_empty(body)
        && function.span.begin.byte < body.span.begin.byte
        && function.span.end == body.span.end
        && body.span.begin.line > 0
        && body.span.begin.column > 0
        && body.span.begin.byte < body.span.end.byte
}

/// Admit a source-authenticated successful-byte input/output trace.
///
/// Repeated local outputs do not read input again, but a discarded read
/// and the left operand of a comma expression consume input without writing
/// output. A later input invalidates any earlier live SSA identity. No
/// other guest effects or EOF behavior are admitted.
///
/// # Errors
///
/// Rejects missing source ancestry, noncanonical LLVM metadata, extra effects,
/// invalid source bounds and malformed canonical typed IR.
#[expect(
    clippy::redundant_pub_crate,
    clippy::too_many_lines,
    reason = "private source-checked typed SSA proof remains a single gate"
)]
pub(super) fn canonical_source_byte_echo(
    bytes: &[u8],
    source: Option<&[u8]>,
) -> Result<super::CanonicalGuestProjection, FrontendJsonError> {
    if bytes.is_empty() || bytes.len() > super::MAX_FRONTEND_JSON_BYTES {
        return Err(FrontendJsonError::Malformed);
    }
    let input: Artifact = serde_json::from_slice(bytes)
        .map_err(|_error| FrontendJsonError::Malformed)?;
    let [function, body, rest @ ..] = input.nodes.as_slice() else {
        return Err(FrontendJsonError::Unsupported);
    };
    if !valid_envelope(&input, function, body) || rest.is_empty() {
        return Err(FrontendJsonError::Unsupported);
    }
    // A forged signed-char Clang node can have exactly the same extent as
    // `(unsigned char)`. The typed AST alone cannot prove the source token.
    // Require an explicitly supplied source witness for every narrowed u8
    // cast, and verify its literal spelling at the actual byte offset.
    let casts = input.nodes.iter().filter(|node| {
        node.kind == "cast-expression"
            && node.type_name.as_deref() == Some("u8")
    });
    for cast in casts {
        let start = usize::try_from(cast.span.begin.byte)
            .map_err(|_| FrontendJsonError::Unsupported)?;
        let end = start
            .checked_add(15)
            .ok_or(FrontendJsonError::Unsupported)?;
        if source.and_then(|bytes| bytes.get(start..end))
            != Some(b"(unsigned char)")
        {
            return Err(FrontendJsonError::Unsupported);
        }
    }
    let mut previous = body.span.begin.byte;
    let mut next_id = 3u32;
    let mut consumed = 0usize;
    let mut inputs = 0usize;
    let mut outputs = 0usize;
    let mut requires_latest = false;
    let mut local_names = HashSet::new();
    let mut declared_locals: Vec<LocalDeclaration<'_>> = Vec::new();
    let mut latest_local: Option<(LocalDeclaration<'_>, ValueId)> = None;
    // Identity copies keep their old C names while sharing the current
    // accumulator byte. A new guest read invalidates all of these names.
    let mut equivalent_locals: Vec<LocalDeclaration<'_>> = Vec::new();
    let mut instructions = Vec::new();
    let mut terminated = false;
    while consumed < rest.len() {
        let first = rest.get(consumed).ok_or(FrontendJsonError::Unsupported)?;
        if outputs == MAX_SOURCE_OUTPUTS || first.id != next_id {
            return Err(FrontendJsonError::Unsupported);
        }
        if terminated || first.kind == "return-statement" {
            // Still authenticate every dead suffix node. Do not publish its
            // guest effects or treat an unverified effect as harmless.
            let (width, effects, end) = prove_static_if_statement(
                rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?,
                body,
                previous,
                next_id,
                body.id,
                None,
                &[],
                0,
                false,
                0,
                None,
                source,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
            if !terminated
                && (effects.len() != 1
                    || effects[0].loop_exit != Some(StaticLoopExit::Return))
            {
                return Err(FrontendJsonError::Unsupported);
            }
            terminated = true;
            previous = end;
            consumed = consumed
                .checked_add(width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            continue;
        }
        if first.kind == "for-statement" {
            let remaining =
                rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?;
            let proof = prove_static_for(
                remaining,
                body,
                previous,
                next_id,
                body.id,
                None,
                &[],
                1,
                None,
                source,
            )
            .or_else(|| {
                // The selected trace may have discarded inputs, but the outer
                // C local must be rebound before its next observed use.
                let (live, _) = latest_local.as_ref()?;
                let witness = source?;
                std::iter::once(live)
                    .chain(equivalent_locals.iter())
                    .find_map(|candidate| {
                        let proof = prove_static_for(
                            remaining,
                            body,
                            previous,
                            next_id,
                            body.id,
                            Some(candidate),
                            &equivalent_locals,
                            1,
                            None,
                            source,
                        )?;
                        (outer_loop_byte_after_effects(
                            &proof.effects,
                            &candidate.variable_reference,
                            true,
                        )
                        .is_some()
                            && source_identifiers_match(
                                remaining.get(..proof.width)?,
                                witness,
                            ))
                        .then_some(proof)
                    })
            })
            .ok_or(FrontendJsonError::Unsupported)?;
            // Each static trip has already been source-proven with its
            // induction value; the ordered trace still reads from the guest.
            let mut iteration_byte =
                latest_local.as_ref().map(|(_, value)| *value);
            for effect in &proof.effects {
                if let Some(exit) = effect.loop_exit {
                    if exit != StaticLoopExit::Return {
                        return Err(FrontendJsonError::Unsupported);
                    }
                    terminated = true;
                    break;
                }
                if inputs
                    .checked_add(usize::from(effect.input.is_some()))
                    .is_none_or(|count| count > MAX_ECHO_CALLS)
                    || outputs
                        .checked_add(effect.outputs.len())
                        .is_none_or(|total| total > MAX_SOURCE_OUTPUTS)
                {
                    return Err(FrontendJsonError::Unsupported);
                }
                let value = if let Some(input) = effect.input {
                    let value = ValueId::new(
                        u32::try_from(inputs)
                            .map_err(|_| FrontendJsonError::Unsupported)?,
                    );
                    instructions.push(LocatedInstruction::new(
                        Instruction::ByteInput {
                            result: value,
                            type_id: TypeId::new(0),
                        },
                        typed_span(&input.span),
                    ));
                    inputs += 1;
                    iteration_byte = Some(value);
                    // Fresh guest input invalidates earlier C identities.
                    // A source-proven assignment to an enclosing C local
                    // can replace it; a loop-local declaration cannot escape.
                    latest_local =
                        effect.assigned_local.as_ref().and_then(|reference| {
                            declared_locals
                                .iter()
                                .find(|local| {
                                    &local.variable_reference == reference
                                })
                                .cloned()
                                .map(|local| (local, value))
                        });
                    equivalent_locals.clear();
                    value
                } else {
                    iteration_byte.ok_or(FrontendJsonError::Unsupported)?
                };
                for output in effect.outputs.iter().rev() {
                    instructions.push(LocatedInstruction::new(
                        Instruction::ByteOutput { value },
                        typed_span(&output.span),
                    ));
                }
                outputs += effect.outputs.len();
                requires_latest = true;
            }
            previous = proof.end;
            consumed = consumed
                .checked_add(proof.width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(proof.width)
                        .map_err(|_| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            continue;
        }
        if first.kind == "if-statement" {
            let proof = prove_static_if(
                rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?,
                body,
                previous,
                next_id,
                body.id,
                latest_local.as_ref().map(|(local, _)| local),
                &equivalent_locals,
                0,
                // Block-local identity aliases cannot leave this C arm.
                // Each declaration is still bound to source-proven live SSA.
                true,
                0,
                None,
                None,
                source,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
            if proof.selected {
                // A selected branch may contain a counted loop whose local
                // initializer reads a fresh byte on *each* unrolled pass.
                // Keep the latest guest SSA value inside this effect trace;
                // an outer-scope local is not its identity.
                let mut branch_byte =
                    latest_local.as_ref().map(|(_, value)| *value);
                for effect in &proof.effects {
                    if let Some(exit) = effect.loop_exit {
                        if exit != StaticLoopExit::Return {
                            return Err(FrontendJsonError::Unsupported);
                        }
                        terminated = true;
                        break;
                    }
                    if inputs + usize::from(effect.input.is_some())
                        > MAX_ECHO_CALLS
                        || outputs + effect.outputs.len() > MAX_SOURCE_OUTPUTS
                    {
                        return Err(FrontendJsonError::Unsupported);
                    }
                    let value = if let Some(input) = effect.input {
                        let value = ValueId::new(
                            u32::try_from(inputs)
                                .map_err(|_| FrontendJsonError::Unsupported)?,
                        );
                        instructions.push(LocatedInstruction::new(
                            Instruction::ByteInput {
                                result: value,
                                type_id: TypeId::new(0),
                            },
                            typed_span(&input.span),
                        ));
                        inputs += 1;
                        // A source-authenticated assignment to an existing
                        // C local remains live after a statically selected
                        // branch. An ordinary read or scoped declaration
                        // cannot export that identity to the outer scope.
                        latest_local = effect.assigned_local.as_ref().and_then(
                            |reference| {
                                declared_locals
                                    .iter()
                                    .find(|local| {
                                        &local.variable_reference == reference
                                    })
                                    .cloned()
                                    .map(|local| (local, value))
                            },
                        );
                        equivalent_locals.clear();
                        branch_byte = Some(value);
                        value
                    } else {
                        branch_byte.ok_or(FrontendJsonError::Unsupported)?
                    };
                    for output in effect.outputs.iter().rev() {
                        instructions.push(LocatedInstruction::new(
                            Instruction::ByteOutput { value },
                            typed_span(&output.span),
                        ));
                    }
                    outputs += effect.outputs.len();
                    requires_latest = true;
                }
            }
            previous = proof.end;
            consumed = consumed
                .checked_add(proof.width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(proof.width)
                        .map_err(|_| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            continue;
        }
        if first.kind == "call-expression"
            && first.reference.as_deref() == Some("external:putchar")
            && let Some((destination, width, read, calls)) =
                source.and_then(|witness| {
                    let nodes = rest.get(consumed..)?;
                    declared_locals.iter().find_map(|candidate| {
                        let proof = prove_wrapped_output_return_reassignment(
                            nodes,
                            (body, previous, body.id),
                            candidate,
                            witness,
                        )
                        .or_else(|| {
                            prove_nested_output_input_assignment(
                                nodes,
                                (body, previous, body.id),
                                candidate,
                                witness,
                            )
                        })
                        .or_else(|| {
                            prove_output_input_assignment(
                                nodes.get(..8)?,
                                (body, previous, body.id),
                                candidate,
                                witness,
                                b';',
                            )
                            .map(|(read, output)| (8, read, vec![output]))
                        })?;
                        Some((candidate.clone(), proof.0, proof.1, proof.2))
                    })
                })
        {
            if inputs == MAX_ECHO_CALLS
                || outputs
                    .checked_add(calls.len())
                    .is_none_or(|count| count > MAX_SOURCE_OUTPUTS)
            {
                return Err(FrontendJsonError::Unsupported);
            }
            let value = ValueId::new(
                u32::try_from(inputs)
                    .map_err(|_| FrontendJsonError::Unsupported)?,
            );
            instructions.push(LocatedInstruction::new(
                Instruction::ByteInput {
                    result: value,
                    type_id: TypeId::new(0),
                },
                typed_span(&read.span),
            ));
            for output in calls.iter().rev() {
                instructions.push(LocatedInstruction::new(
                    Instruction::ByteOutput { value },
                    typed_span(&output.span),
                ));
            }
            latest_local = Some((destination, value));
            equivalent_locals.clear();
            inputs += 1;
            outputs += calls.len();
            previous = calls
                .first()
                .ok_or(FrontendJsonError::Unsupported)?
                .span
                .end
                .byte;
            consumed += width;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            requires_latest = true;
            continue;
        }
        if first.kind == "call-expression"
            && first.reference.as_deref() == Some("external:putchar")
            && let Some((destination, read, output)) =
                source.and_then(|witness| {
                    declared_locals.iter().find_map(|candidate| {
                        let (read, output) = prove_comma_assigned_output(
                            rest.get(consumed..)?,
                            (body, previous, body.id),
                            candidate,
                            witness,
                        )?;
                        Some((candidate.clone(), read, output))
                    })
                })
        {
            if inputs == MAX_ECHO_CALLS || outputs == MAX_SOURCE_OUTPUTS {
                return Err(FrontendJsonError::Unsupported);
            }
            let value = ValueId::new(
                u32::try_from(inputs)
                    .map_err(|_| FrontendJsonError::Unsupported)?,
            );
            instructions.push(LocatedInstruction::new(
                Instruction::ByteInput {
                    result: value,
                    type_id: TypeId::new(0),
                },
                typed_span(&read.span),
            ));
            instructions.push(LocatedInstruction::new(
                Instruction::ByteOutput { value },
                typed_span(&output.span),
            ));
            latest_local = Some((destination, value));
            equivalent_locals.clear();
            inputs += 1;
            outputs += 1;
            previous = output.span.end.byte;
            consumed += 12;
            next_id = next_id
                .checked_add(12)
                .ok_or(FrontendJsonError::Unsupported)?;
            requires_latest = true;
            continue;
        }
        if first.kind == "call-expression"
            && first.reference.as_deref() == Some("external:putchar")
            && let Some((width, outer, Some(read), inner)) =
                source.and_then(|witness| {
                    prove_identity_byte_output(
                        rest.get(consumed..)?,
                        body,
                        None,
                        next_id,
                        previous,
                        body.id,
                        witness,
                        None,
                    )
                })
        {
            if inputs == MAX_ECHO_CALLS
                || outputs
                    .checked_add(inner.len())
                    .and_then(|count| count.checked_add(1))
                    .is_none_or(|count| count > MAX_SOURCE_OUTPUTS)
            {
                return Err(FrontendJsonError::Unsupported);
            }
            let value = ValueId::new(
                u32::try_from(inputs)
                    .map_err(|_| FrontendJsonError::Unsupported)?,
            );
            instructions.push(LocatedInstruction::new(
                Instruction::ByteInput {
                    result: value,
                    type_id: TypeId::new(0),
                },
                typed_span(&read.span),
            ));
            for call in inner.iter().rev().chain(std::iter::once(&outer)) {
                instructions.push(LocatedInstruction::new(
                    Instruction::ByteOutput { value },
                    typed_span(&call.span),
                ));
            }
            // The new read invalidates every preceding source-C local.
            latest_local = None;
            equivalent_locals.clear();
            previous = outer.span.end.byte;
            consumed = consumed
                .checked_add(width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            inputs += 1;
            outputs += inner.len() + 1;
            requires_latest = true;
            continue;
        }
        if first.kind == "call-expression"
            && let Some((local, value)) = latest_local.as_ref()
            && let Some((width, calls)) = std::iter::once(local)
                .chain(equivalent_locals.iter())
                .find_map(|candidate| {
                    prove_local_output_chain(
                        rest.get(consumed..)?,
                        body,
                        candidate,
                        next_id,
                        previous,
                        body.id,
                        source,
                    )
                })
        {
            if outputs
                .checked_add(calls.len())
                .is_none_or(|total| total > MAX_SOURCE_OUTPUTS)
            {
                return Err(FrontendJsonError::Unsupported);
            }
            // Reuse the same live input SSA, with no new guest read.
            for call in calls.iter().rev() {
                instructions.push(LocatedInstruction::new(
                    Instruction::ByteOutput { value: *value },
                    typed_span(&call.span),
                ));
            }
            requires_latest = true;
            outputs = outputs
                .checked_add(calls.len())
                .ok_or(FrontendJsonError::Unsupported)?;
            previous = calls
                .first()
                .ok_or(FrontendJsonError::Unsupported)?
                .span
                .end
                .byte;
            consumed = consumed
                .checked_add(width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_error| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            continue;
        }
        if first.kind == "call-expression"
            && first.reference.as_deref() == Some("external:putchar")
            && let Some((width, effects, output)) = prove_comma_output_effects(
                rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?,
                body,
                previous,
                next_id,
                body.id,
                latest_local.as_ref().map(|(local, _value)| local),
                source,
            )
        {
            let inner_outputs =
                effects.iter().map(|e| e.outputs.len()).sum::<usize>();
            if inputs
                .checked_add(effects.len())
                .is_none_or(|count| count > MAX_ECHO_CALLS)
                || outputs
                    .checked_add(inner_outputs)
                    .and_then(|count| count.checked_add(1))
                    .is_none_or(|count| count > MAX_SOURCE_OUTPUTS)
            {
                return Err(FrontendJsonError::Unsupported);
            }
            let (selected, read_new_input, retains_local) = emit_comma_effects(
                &effects,
                latest_local.as_ref(),
                &mut inputs,
                &mut outputs,
                &mut instructions,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
            instructions.push(LocatedInstruction::new(
                Instruction::ByteOutput { value: selected },
                typed_span(&output.span),
            ));
            if read_new_input {
                latest_local = if retains_local {
                    latest_local.map(|(local, _)| (local, selected))
                } else {
                    None
                };
                equivalent_locals.clear();
            }
            previous = output.span.end.byte;
            consumed = consumed
                .checked_add(width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_error| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            outputs = outputs
                .checked_add(1)
                .ok_or(FrontendJsonError::Unsupported)?;
            requires_latest = true;
            continue;
        }
        if first.kind == "binary-expression"
            && first.operation.as_deref() == Some("=")
            && let Some((destination, width, effects, end)) =
                source.and_then(|witness| {
                    let nodes = rest.get(consumed..)?;
                    declared_locals.iter().find_map(|candidate| {
                        let (width, effects, end) =
                            prove_comma_local_reassignment(
                                nodes,
                                (body, previous, body.id),
                                candidate,
                                witness,
                            )?;
                        Some((candidate.clone(), width, effects, end))
                    })
                })
        {
            let (value, read_new_input, _retains_local) = emit_comma_effects(
                &effects,
                None,
                &mut inputs,
                &mut outputs,
                &mut instructions,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
            if !read_new_input {
                return Err(FrontendJsonError::Unsupported);
            }
            latest_local = Some((destination, value));
            equivalent_locals.clear();
            previous = end;
            consumed = consumed
                .checked_add(width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            requires_latest = true;
            continue;
        }
        if first.kind == "binary-expression"
            && first.operation.as_deref() == Some("=")
            && let Some((destination, width, read, calls)) =
                source.and_then(|witness| {
                    let nodes = rest.get(consumed..)?;
                    declared_locals.iter().find_map(|candidate| {
                        let (width, read, calls) =
                            prove_output_return_reassignment(
                                nodes,
                                (body, previous, body.id),
                                candidate,
                                witness,
                                b';',
                            )?;
                        Some((candidate.clone(), width, read, calls))
                    })
                })
        {
            if inputs == MAX_ECHO_CALLS
                || outputs
                    .checked_add(calls.len())
                    .is_none_or(|count| count > MAX_SOURCE_OUTPUTS)
            {
                return Err(FrontendJsonError::Unsupported);
            }
            let value = ValueId::new(
                u32::try_from(inputs)
                    .map_err(|_error| FrontendJsonError::Unsupported)?,
            );
            instructions.push(LocatedInstruction::new(
                Instruction::ByteInput {
                    result: value,
                    type_id: TypeId::new(0),
                },
                typed_span(&read.span),
            ));
            for call in calls.iter().rev() {
                instructions.push(LocatedInstruction::new(
                    Instruction::ByteOutput { value },
                    typed_span(&call.span),
                ));
            }
            latest_local = Some((destination, value));
            equivalent_locals.clear();
            inputs = inputs
                .checked_add(1)
                .ok_or(FrontendJsonError::Unsupported)?;
            outputs = outputs
                .checked_add(calls.len())
                .ok_or(FrontendJsonError::Unsupported)?;
            previous = first.span.end.byte;
            consumed = consumed
                .checked_add(width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            requires_latest = true;
            continue;
        }
        if first.kind == "binary-expression"
            && first.operation.as_deref() == Some("=")
            && let Some((live, value)) = latest_local.as_ref()
            && let Some(destination) = source.and_then(|witness| {
                let nodes = rest.get(consumed..consumed.saturating_add(4))?;
                declared_locals.iter().find(|destination| {
                    std::iter::once(live).chain(equivalent_locals.iter()).any(
                        |candidate| {
                            prove_local_copy_assignment(
                                nodes,
                                (body, previous, body.id),
                                destination,
                                candidate,
                                witness,
                            )
                            .is_some()
                        },
                    )
                })
            })
        {
            let destination = destination.clone();
            let value = *value;
            let previous_latest = live.clone();
            equivalent_locals.retain(|candidate| {
                candidate.variable_reference != destination.variable_reference
            });
            if previous_latest.variable_reference
                != destination.variable_reference
                && !equivalent_locals.iter().any(|candidate| {
                    candidate.variable_reference
                        == previous_latest.variable_reference
                })
            {
                equivalent_locals.push(previous_latest);
            }
            latest_local = Some((destination, value));
            previous = first.span.end.byte;
            consumed += 4;
            next_id = next_id
                .checked_add(4)
                .ok_or(FrontendJsonError::Unsupported)?;
            continue;
        }
        if first.kind == "binary-expression"
            && first.operation.as_deref() == Some("=")
            && let Some((destination, read)) = source.and_then(|witness| {
                let nodes = rest.get(consumed..consumed.saturating_add(5))?;
                declared_locals.iter().find_map(|candidate| {
                    prove_local_input_reassignment(
                        nodes,
                        (body, previous, body.id),
                        candidate,
                        witness,
                        b';',
                    )
                    .map(|read| (candidate.clone(), read))
                })
            })
        {
            if inputs == MAX_ECHO_CALLS {
                return Err(FrontendJsonError::Unsupported);
            }
            let id = ValueId::new(
                u32::try_from(inputs)
                    .map_err(|_| FrontendJsonError::Unsupported)?,
            );
            instructions.push(LocatedInstruction::new(
                Instruction::ByteInput {
                    result: id,
                    type_id: TypeId::new(0),
                },
                typed_span(&read.span),
            ));
            // This fresh read makes its verified destination resident even
            // when it previously held a stale byte. All other C names keep
            // their old values, which this accumulator backend cannot recall.
            latest_local = Some((destination, id));
            equivalent_locals.clear();
            inputs += 1;
            previous = first.span.end.byte;
            consumed += 5;
            next_id = next_id
                .checked_add(5)
                .ok_or(FrontendJsonError::Unsupported)?;
            requires_latest = true;
            continue;
        }
        if first.kind == "binary-expression"
            && let Some((width, effects, end)) = prove_discarded_comma_effects(
                rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?,
                body,
                previous,
                next_id,
                body.id,
                latest_local.as_ref().map(|(local, _value)| local),
                source,
            )
        {
            if inputs
                .checked_add(effects.len())
                .is_none_or(|count| count > MAX_ECHO_CALLS)
                || outputs
                    .checked_add(
                        effects.iter().map(|e| e.outputs.len()).sum::<usize>(),
                    )
                    .is_none_or(|count| count > MAX_SOURCE_OUTPUTS)
            {
                return Err(FrontendJsonError::Unsupported);
            }
            let (selected, read_new_input, retains_local) = emit_comma_effects(
                &effects,
                latest_local.as_ref(),
                &mut inputs,
                &mut outputs,
                &mut instructions,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
            // Only a fresh input clobbers the live accumulator-local value.
            if read_new_input {
                latest_local = if retains_local {
                    latest_local.map(|(local, _)| (local, selected))
                } else {
                    None
                };
                equivalent_locals.clear();
            }
            previous = end;
            consumed = consumed
                .checked_add(width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_error| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            requires_latest = true;
            continue;
        }
        if first.kind == "declaration-statement"
            && let Some((live, value)) = latest_local.as_ref()
            && let Some(alias) = source.and_then(|witness| {
                let nodes = rest.get(consumed..consumed.saturating_add(4))?;
                std::iter::once(live)
                    .chain(equivalent_locals.iter())
                    .find_map(|candidate| {
                        prove_local_alias(
                            nodes,
                            (body, previous, body.id),
                            candidate,
                            witness,
                        )
                    })
            })
        {
            if declared_locals.len() >= MAX_SOURCE_OUTPUTS
                || !local_names.insert(alias.name)
            {
                return Err(FrontendJsonError::Unsupported);
            }
            previous = alias.declaration_end;
            declared_locals.push(alias.clone());
            equivalent_locals.push(live.clone());
            latest_local = Some((alias, *value));
            consumed = consumed
                .checked_add(4)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(4)
                .ok_or(FrontendJsonError::Unsupported)?;
            continue;
        }
        if first.kind == "declaration-statement"
            && let Some((local, width, effects)) = source.and_then(|witness| {
                prove_comma_local_declaration(
                    rest.get(consumed..)?,
                    body,
                    previous,
                    body.id,
                    witness,
                )
            })
        {
            let new_reads = effects.len();
            let new_writes = effects
                .iter()
                .map(|effect| effect.outputs.len())
                .sum::<usize>();
            if inputs
                .checked_add(new_reads)
                .is_none_or(|total| total > MAX_ECHO_CALLS)
                || outputs
                    .checked_add(new_writes)
                    .is_none_or(|total| total > MAX_SOURCE_OUTPUTS)
                || declared_locals.len() >= MAX_SOURCE_OUTPUTS
                || !local_names.insert(local.name)
            {
                return Err(FrontendJsonError::Unsupported);
            }
            let (value, read_new_input, _retains_local) = emit_comma_effects(
                &effects,
                None,
                &mut inputs,
                &mut outputs,
                &mut instructions,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
            if !read_new_input {
                return Err(FrontendJsonError::Unsupported);
            }
            previous = local.declaration_end;
            declared_locals.push(local.clone());
            latest_local = Some((local, value));
            equivalent_locals.clear();
            consumed = consumed
                .checked_add(width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            requires_latest = true;
            continue;
        }
        if first.kind == "declaration-statement"
            && let Some((local, width, calls)) = source.and_then(|witness| {
                prove_output_return_declaration(
                    rest.get(consumed..)?,
                    body,
                    previous,
                    body.id,
                    witness,
                )
            })
        {
            if inputs == MAX_ECHO_CALLS
                || declared_locals.len() >= MAX_SOURCE_OUTPUTS
                || outputs
                    .checked_add(calls.len())
                    .is_none_or(|total| total > MAX_SOURCE_OUTPUTS)
                || !local_names.insert(local.name)
            {
                return Err(FrontendJsonError::Unsupported);
            }
            let value = ValueId::new(
                u32::try_from(inputs)
                    .map_err(|_| FrontendJsonError::Unsupported)?,
            );
            instructions.push(LocatedInstruction::new(
                Instruction::ByteInput {
                    result: value,
                    type_id: TypeId::new(0),
                },
                typed_span(&local.input.span),
            ));
            for call in calls.iter().rev() {
                instructions.push(LocatedInstruction::new(
                    Instruction::ByteOutput { value },
                    typed_span(&call.span),
                ));
            }
            previous = local.declaration_end;
            declared_locals.push(local.clone());
            latest_local = Some((local, value));
            equivalent_locals.clear();
            consumed = consumed
                .checked_add(width)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(
                    u32::try_from(width)
                        .map_err(|_| FrontendJsonError::Unsupported)?,
                )
                .ok_or(FrontendJsonError::Unsupported)?;
            inputs += 1;
            outputs += calls.len();
            requires_latest = true;
            continue;
        }
        if inputs == MAX_ECHO_CALLS {
            return Err(FrontendJsonError::Unsupported);
        }
        let id = ValueId::new(
            u32::try_from(inputs)
                .map_err(|_error| FrontendJsonError::Unsupported)?,
        );
        if first.kind == "call-expression"
            && first.reference.as_deref() == Some("external:getchar")
            && let Some(read) = rest
                .get(consumed..consumed.saturating_add(3))
                .and_then(|nodes| {
                    prove_input_call(nodes, body, previous, (next_id, body.id))
                })
        {
            instructions.push(LocatedInstruction::new(
                Instruction::ByteInput {
                    result: id,
                    type_id: TypeId::new(0),
                },
                typed_span(&read.span),
            ));
            // This input overwrites the accumulator, so any preceding
            // local can no longer be materialized by the guest.
            latest_local = None;
            equivalent_locals.clear();
            previous = read.span.end.byte;
            consumed = consumed
                .checked_add(3)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(3)
                .ok_or(FrontendJsonError::Unsupported)?;
            inputs = inputs
                .checked_add(1)
                .ok_or(FrontendJsonError::Unsupported)?;
            // Adjacent echo cannot represent an input without output.
            requires_latest = true;
            continue;
        }
        // A declaration is an input effect, not a declaration/output pair.
        // Keep its live byte until a genuinely newer input overwrites A;
        // the next source statement can be any separately proven consumer.
        if first.kind == "declaration-statement" {
            let declaration_nodes = rest
                .get(consumed..consumed.saturating_add(5))
                .ok_or(FrontendJsonError::Unsupported)?;
            let local = prove_local_declaration(
                declaration_nodes,
                body,
                previous,
                body.id,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
            if declared_locals.len() >= MAX_SOURCE_OUTPUTS
                || !local_names.insert(local.name)
            {
                return Err(FrontendJsonError::Unsupported);
            }
            instructions.push(LocatedInstruction::new(
                Instruction::ByteInput {
                    result: id,
                    type_id: TypeId::new(0),
                },
                typed_span(&local.input.span),
            ));
            previous = local.declaration_end;
            declared_locals.push(local.clone());
            equivalent_locals.clear();
            latest_local = Some((local, id));
            consumed = consumed
                .checked_add(5)
                .ok_or(FrontendJsonError::Unsupported)?;
            next_id = next_id
                .checked_add(5)
                .ok_or(FrontendJsonError::Unsupported)?;
            inputs = inputs
                .checked_add(1)
                .ok_or(FrontendJsonError::Unsupported)?;
            requires_latest = true;
            continue;
        }
        let nodes =
            rest.get(consumed..).ok_or(FrontendJsonError::Unsupported)?;
        let (width, input_call, output_calls) = if let Some((read, write)) =
            nodes
                .get(..CALL_NODE_COUNT)
                .and_then(|slice| prove_call(slice, body, previous, body.id))
        {
            (CALL_NODE_COUNT, read, vec![write])
        } else {
            super::nested_byte_echo::nested_call(nodes, body, previous, next_id)
                .ok_or(FrontendJsonError::Unsupported)?
        };
        // A newer input destroys the previous live accumulator value.
        latest_local = None;
        equivalent_locals.clear();
        if outputs
            .checked_add(output_calls.len())
            .is_none_or(|total| total > MAX_SOURCE_OUTPUTS)
        {
            return Err(FrontendJsonError::Unsupported);
        }
        instructions.push(LocatedInstruction::new(
            Instruction::ByteInput {
                result: id,
                type_id: TypeId::new(0),
            },
            typed_span(&input_call.span),
        ));
        for call in output_calls.iter().rev() {
            instructions.push(LocatedInstruction::new(
                Instruction::ByteOutput { value: id },
                typed_span(&call.span),
            ));
        }
        requires_latest |= output_calls.len() > 1;
        previous = output_calls
            .first()
            .ok_or(FrontendJsonError::Unsupported)?
            .span
            .end
            .byte;
        consumed = consumed.saturating_add(width);
        next_id = next_id
            .checked_add(
                u32::try_from(width)
                    .map_err(|_error| FrontendJsonError::Unsupported)?,
            )
            .ok_or(FrontendJsonError::Unsupported)?;
        inputs = inputs.saturating_add(1);
        outputs = outputs
            .checked_add(output_calls.len())
            .ok_or(FrontendJsonError::Unsupported)?;
    }
    if previous >= body.span.end.byte {
        return Err(FrontendJsonError::Unsupported);
    }
    let void_function = FrontendReturnVoidFunction::new_fallthrough(
        FrontendFallthroughVoidFunctionSpec {
            body_span: span(&body.span),
            definition: String::from("definition"),
            function_span: span(&function.span),
            inline_specified: false,
            linkage: String::from("external"),
            name: function
                .name
                .clone()
                .ok_or(FrontendJsonError::Unsupported)?,
            signature: String::from("fn()->void"),
            storage_class: String::from("none"),
        },
    );
    let artifact = FrontendArtifact::new_void(
        FrontendArtifactSpec {
            abi_id: input.profile.abi_id,
            artifact_id: input.identity,
            clang_target: input.clang.target,
            clang_version: input.clang.version,
            functions: Vec::new(),
            language: input.clang.language,
            schema_version: input.schema_version,
            source_id: input.source.id,
            source_sha256: source_digest(&input.source.sha256)?,
            target_profile: input.profile.target_profile,
        },
        void_function,
    );
    let base = lower_frontend_artifact(&artifact)
        .map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    let original = base
        .functions()
        .first()
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    let block = original
        .blocks()
        .first()
        .ok_or(FrontendJsonError::InvalidTypedIr)?;
    // A discarded C getchar is defined even at EOF. Preserve its signed i32
    // identity, rather than projecting an unconditionally successful u8 read.
    // This exact mode has no output and cannot observe the returned value.
    let discarded_getchar = inputs > 0
        && outputs == 0
        && instructions.iter().all(|entry| {
            matches!(entry.instruction(), Instruction::ByteInput { .. })
        });
    if discarded_getchar {
        instructions = instructions
            .into_iter()
            .map(|entry| {
                let Instruction::ByteInput { result, type_id } =
                    entry.instruction()
                else {
                    unreachable!("discarded read mode preflighted")
                };
                LocatedInstruction::new(
                    Instruction::Getchar {
                        result: *result,
                        type_id: *type_id,
                    },
                    entry.span(),
                )
            })
            .collect();
    }
    let mut types = base.types().to_vec();
    if discarded_getchar {
        types[0] = TypeEntry::new(TypeId::new(0), TypeDef::I32);
    }
    let compiled = Function::new(FunctionSpec {
        blocks: vec![BasicBlock::new(BasicBlockSpec {
            id: block.id(),
            instructions,
            phis: block.phis().to_vec(),
            span: block.span(),
            terminator: block.terminator().clone(),
            terminator_span: block.terminator_span(),
        })],
        entry: original.entry(),
        id: original.id(),
        name: String::from(original.name()),
        parameters: original.parameters().to_vec(),
        signature: original.signature(),
        span: original.span(),
    });
    let module = Module::new(ModuleSpec {
        abi_id: String::from(base.abi_id()),
        format_version: base.format_version(),
        functions: vec![compiled],
        globals: base.globals().to_vec(),
        proof_obligations: base.proof_obligations().to_vec(),
        source_id: String::from(base.source_id()),
        source_sha256: *base.source_sha256(),
        target_profile: String::from(base.target_profile()),
        types,
    });
    let wire = canonical_bytes(&module)
        .map_err(|_error| FrontendJsonError::InvalidTypedIr)?;
    if canonical_module(&wire)
        .map_err(|_error| FrontendJsonError::InvalidTypedIr)?
        != module
    {
        return Err(FrontendJsonError::InvalidTypedIr);
    }
    Ok((
        wire,
        if discarded_getchar {
            FrontendGuestMode::DiscardedGetchar
        } else if requires_latest {
            FrontendGuestMode::LatestRead
        } else {
            FrontendGuestMode::AdjacentEcho
        },
    ))
}
