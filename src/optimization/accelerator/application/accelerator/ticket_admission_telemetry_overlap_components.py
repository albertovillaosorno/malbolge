# Copyright:
#   - Copyright © 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE-MIT
#
# Boundary-Contract:
# - Owns:
#   - Deterministic connected components over exact retained-overlap edges.
# - Must-Not:
#   - Infer recorder lineage, merge snapshots, load files, or change admission.
# - Allows:
#   - Inputs: one explicit bounded tuple of schema-v1 telemetry documents.
#   - Outputs: immutable compatibility edges and connected review components.
#   - Side effects: none.
# - Split-When:
#   - Split when asymmetric lineage or recommendation policy gains a
#     contract.
# - Merge-When:
#   - Merge when another module owns this exact compatibility-graph boundary.
# - Summary:
#   - Non-authoritative telemetry overlap components.
# - Description:
#   - Groups exact nonconflicting overlaps without claiming pairwise
#     equivalence.
# - Usage:
#   - Supply explicit documents and review isolated, clique, or bridged
#     components.
# - Defaults:
#   - Collection and pair bounds are inherited from the overlap index.
#

"""Connected review components over exact nonconflicting telemetry overlap."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from json import dumps
from typing import Final
from typing import Never
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from accelerator.ticket_admission_telemetry_overlap import (
        TicketAdmissionTelemetryDocumentOverlap,
    )
    from accelerator.ticket_admission_telemetry_overlap_index import (
        TicketAdmissionTelemetryOverlapIndex,
    )
    from accelerator.ticket_admission_telemetry_persistence import (
        TicketAdmissionTelemetryDocument,
    )

from accelerator.ticket_admission_telemetry_collection import (
    DEFAULT_MAX_TELEMETRY_COLLECTION_BYTES,
)
from accelerator.ticket_admission_telemetry_collection import (
    DEFAULT_MAX_TELEMETRY_DOCUMENTS,
)
from accelerator.ticket_admission_telemetry_overlap_index import (
    DEFAULT_MAX_TELEMETRY_OVERLAP_PAIRS,
)
from accelerator.ticket_admission_telemetry_overlap_index import (
    TicketAdmissionTelemetryOverlapIndexError,
)
from accelerator.ticket_admission_telemetry_overlap_index import (
    index_ticket_admission_telemetry_overlap,
)

TICKET_ADMISSION_TELEMETRY_OVERLAP_COMPONENTS_ID: Final = (
    "offline-ticket-admission-telemetry-overlap-components-v1"
)
TICKET_ADMISSION_TELEMETRY_OVERLAP_COMPONENT_FINGERPRINT_PREFIX: Final = (
    "ticket-admission-telemetry-overlap-component-v1:sha256:"
)


class TicketAdmissionTelemetryOverlapComponentsError(ValueError):
    """A bounded overlap index cannot produce unambiguous components."""


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryCompatibilityEdge:
    """One direct exact-match edge with no retained sequence conflict."""

    completed_matching_observation_count: int
    failed_matching_observation_count: int
    first_document_fingerprint: str
    matching_observation_count: int
    second_document_fingerprint: str


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryOverlapComponent:
    """One connected review component without lineage authority."""

    component_fingerprint: str
    direct_edge_count: int
    edges: tuple[TicketAdmissionTelemetryCompatibilityEdge, ...]
    is_clique: bool
    member_count: int
    member_fingerprints: tuple[str, ...]
    missing_direct_edge_count: int
    possible_edge_count: int


@dataclass(frozen=True, slots=True)
class TicketAdmissionTelemetryOverlapComponents:
    """Deterministic compatibility graph retaining isolated documents."""

    component_count: int
    components: tuple[TicketAdmissionTelemetryOverlapComponent, ...]
    components_id: str
    connected_component_count: int
    connected_document_count: int
    ignored_pair_count: int
    index: TicketAdmissionTelemetryOverlapIndex
    isolated_document_count: int
    selected_edge_count: int


def ticket_admission_telemetry_overlap_components_id() -> str:
    """Return the stable compatibility-component identity.

    Returns:
        Versioned non-authoritative component identity.

    """
    return TICKET_ADMISSION_TELEMETRY_OVERLAP_COMPONENTS_ID


def build_ticket_admission_telemetry_overlap_components(
    documents: tuple[TicketAdmissionTelemetryDocument, ...],
    *,
    max_documents: int = DEFAULT_MAX_TELEMETRY_DOCUMENTS,
    max_total_bytes: int = DEFAULT_MAX_TELEMETRY_COLLECTION_BYTES,
    max_pairs: int = DEFAULT_MAX_TELEMETRY_OVERLAP_PAIRS,
) -> TicketAdmissionTelemetryOverlapComponents:
    """Build components from exact nonconflicting retained overlap.

    Returns:
        Deterministic components retaining isolated unique documents.

    """
    index = _overlap_index(
        documents,
        max_documents=max_documents,
        max_total_bytes=max_total_bytes,
        max_pairs=max_pairs,
    )
    vertices = tuple(
        entry.document_fingerprint
        for entry in index.collection.unique_documents
    )
    edges = tuple(
        edge
        for pair in index.pairs
        if (edge := _compatibility_edge(pair)) is not None
    )
    components = _components(vertices, edges)
    isolated_count = sum(
        component.member_count == 1 for component in components
    )
    return TicketAdmissionTelemetryOverlapComponents(
        component_count=len(components),
        components=components,
        components_id=TICKET_ADMISSION_TELEMETRY_OVERLAP_COMPONENTS_ID,
        connected_component_count=sum(
            component.member_count > 1 for component in components
        ),
        connected_document_count=len(vertices) - isolated_count,
        ignored_pair_count=index.pair_count - len(edges),
        index=index,
        isolated_document_count=isolated_count,
        selected_edge_count=len(edges),
    )


def _overlap_index(
    documents: tuple[TicketAdmissionTelemetryDocument, ...],
    *,
    max_documents: int,
    max_total_bytes: int,
    max_pairs: int,
) -> TicketAdmissionTelemetryOverlapIndex:
    try:
        return index_ticket_admission_telemetry_overlap(
            documents,
            max_documents=max_documents,
            max_total_bytes=max_total_bytes,
            max_pairs=max_pairs,
        )
    except TicketAdmissionTelemetryOverlapIndexError as error:
        message = f"invalid telemetry overlap index: {error}"
        raise TicketAdmissionTelemetryOverlapComponentsError(message) from error


def _compatibility_edge(
    pair: TicketAdmissionTelemetryDocumentOverlap,
) -> TicketAdmissionTelemetryCompatibilityEdge | None:
    completed_count = pair.completed.matching_observation_count
    failed_count = pair.failed.matching_observation_count
    matching_count = completed_count + failed_count
    has_conflict = bool(
        pair.completed.conflicting_sequence_ids
        or pair.failed.conflicting_sequence_ids
    )
    if has_conflict or matching_count == 0:
        return None
    return TicketAdmissionTelemetryCompatibilityEdge(
        completed_matching_observation_count=completed_count,
        failed_matching_observation_count=failed_count,
        first_document_fingerprint=pair.first_document_fingerprint,
        matching_observation_count=matching_count,
        second_document_fingerprint=pair.second_document_fingerprint,
    )


def _components(
    vertices: tuple[str, ...],
    edges: tuple[TicketAdmissionTelemetryCompatibilityEdge, ...],
) -> tuple[TicketAdmissionTelemetryOverlapComponent, ...]:
    parents = {vertex: vertex for vertex in vertices}
    for edge in edges:
        _union(
            parents,
            edge.first_document_fingerprint,
            edge.second_document_fingerprint,
        )
    members_by_root: dict[str, list[str]] = {}
    for vertex in vertices:
        root = _find(parents, vertex)
        members_by_root.setdefault(root, []).append(vertex)
    edges_by_root: dict[
        str,
        list[TicketAdmissionTelemetryCompatibilityEdge],
    ] = {}
    for edge in edges:
        root = _find(parents, edge.first_document_fingerprint)
        edges_by_root.setdefault(root, []).append(edge)
    fingerprints: dict[str, bytes] = {}
    components = tuple(
        _component(
            tuple(sorted(members)),
            tuple(sorted(edges_by_root.get(root, ()), key=_edge_identity)),
            fingerprints,
        )
        for root, members in members_by_root.items()
    )
    return tuple(
        sorted(components, key=lambda component: component.member_fingerprints)
    )


def _find(parents: dict[str, str], vertex: str) -> str:
    root = vertex
    while parents[root] != root:
        root = parents[root]
    current = vertex
    while parents[current] != current:
        following = parents[current]
        parents[current] = root
        current = following
    return root


def _union(parents: dict[str, str], first: str, second: str) -> None:
    first_root = _find(parents, first)
    second_root = _find(parents, second)
    if first_root == second_root:
        return
    lower, upper = sorted((first_root, second_root))
    parents[upper] = lower


def _component(
    members: tuple[str, ...],
    edges: tuple[TicketAdmissionTelemetryCompatibilityEdge, ...],
    fingerprints: dict[str, bytes],
) -> TicketAdmissionTelemetryOverlapComponent:
    possible_edge_count = _possible_edge_count(len(members))
    payload = _component_payload(members, edges)
    fingerprint = _component_fingerprint(payload)
    existing = fingerprints.get(fingerprint)
    if existing is not None and existing != payload:
        _raise_components("component fingerprint collision detected")
    fingerprints[fingerprint] = payload
    return TicketAdmissionTelemetryOverlapComponent(
        component_fingerprint=fingerprint,
        direct_edge_count=len(edges),
        edges=edges,
        is_clique=len(edges) == possible_edge_count,
        member_count=len(members),
        member_fingerprints=members,
        missing_direct_edge_count=possible_edge_count - len(edges),
        possible_edge_count=possible_edge_count,
    )


def _possible_edge_count(member_count: int) -> int:
    return member_count * (member_count - 1) // 2


def _component_payload(
    members: tuple[str, ...],
    edges: tuple[TicketAdmissionTelemetryCompatibilityEdge, ...],
) -> bytes:
    payload = {
        "edges": tuple(
            (
                edge.first_document_fingerprint,
                edge.second_document_fingerprint,
                edge.completed_matching_observation_count,
                edge.failed_matching_observation_count,
            )
            for edge in edges
        ),
        "members": members,
    }
    return dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _component_fingerprint(payload: bytes) -> str:
    digest = sha256(payload).hexdigest()
    return (
        f"{TICKET_ADMISSION_TELEMETRY_OVERLAP_COMPONENT_FINGERPRINT_PREFIX}"
        f"{digest}"
    )


def _edge_identity(
    edge: TicketAdmissionTelemetryCompatibilityEdge,
) -> tuple[str, str]:
    return (
        edge.first_document_fingerprint,
        edge.second_document_fingerprint,
    )


def _raise_components(detail: str) -> Never:
    message = f"ticket admission telemetry overlap components {detail}"
    raise TicketAdmissionTelemetryOverlapComponentsError(message)
