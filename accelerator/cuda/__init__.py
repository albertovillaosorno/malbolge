# File:
#   - __init__.py
# Path:
#   - accelerator/cuda/__init__.py
#
# Copyright:
#   - Copyright (c) 2026 Alberto Villa Osorno.
# SPDX-License-Identifier:
#   - MIT
# Confidential:
#   - false
# License-File:
#   - LICENSE
# Path-Rule:
#   - All paths in this header are repository-root relative.
#
# Boundary-Contract:
# - Owns:
#   - The repository behavior implemented by this source file.
# - Must-Not:
#   - Bypass the contracts or authority boundaries of its owning package.
# - Allows:
#   - Inputs: values admitted by the file's public or internal interface.
#   - Outputs: deterministic values or effects declared by that interface.
#   - Side effects: only those explicitly owned by the implementation.
# - Split-When:
#   - Split when one responsibility gains an independent lifecycle.
# - Merge-When:
#   - Merge when another file owns the exact same responsibility.
# - Summary:
#   - Optional NVIDIA CUDA accelerator adapter.
# - Description:
#   - Implements the responsibility summarized by this module.
# - Usage:
#   - Used through the owning package, executable, or document boundary.
# - Defaults:
#   - Invalid inputs or broken invariants fail closed.
#
# Related documents:
# - None.
#
# Large file:
#   - false
#

"""Optional NVIDIA CUDA accelerator adapter."""

from accelerator.cuda.exact_primitives import CudaExactPrimitiveAdapter
from accelerator.cuda.exact_primitives import CudaPreparedPrimitivePhaseProfile
from accelerator.cuda.exact_primitives import CudaPreparedPrimitiveStats
from accelerator.cuda.exact_primitives import CudaPrimitiveEvaluationTicket
from accelerator.cuda.exact_primitives import CudaPrimitiveTicketTimeline
from accelerator.cuda.exact_primitives import CudaPrimitiveTicketTimelineFactory
from accelerator.cuda.exact_primitives import CudaPrimitiveTicketTransferFactory
from accelerator.cuda.profile_run import CudaProfileSnapshotOverlapWorkspace
from accelerator.cuda.profile_run import CudaProfileSnapshotStreamWorkspace
from accelerator.cuda.profile_run import CudaProfileSnapshotWorkspace
from accelerator.cuda.profile_run import ProfileSnapshotHostRegistration
from accelerator.cuda.profile_run import ProfileSnapshotOverlapAdmission
from accelerator.cuda.profile_run import ProfileSnapshotOverlapCapacity
from accelerator.cuda.profile_run import ProfileSnapshotOverlapSummary
from accelerator.cuda.profile_run import ProfileSnapshotPhaseProfile
from accelerator.cuda.profile_run import ProfileSnapshotStreamCapacity
from accelerator.cuda.profile_run import ProfileSnapshotStreamSummary
from accelerator.cuda.profile_run import ProfileSnapshotWindow
from accelerator.cuda.profile_run import profile_snapshot_host_registration_id
from accelerator.cuda.profile_run import profile_snapshot_overlap_workspace_id
from accelerator.cuda.profile_run import profile_snapshot_stream_workspace_id
from accelerator.cuda.profile_run import profile_snapshot_workspace_id
from accelerator.cuda.runtime import CudaDeviceToHostTransfer
from accelerator.cuda.runtime import CudaHostToDeviceTransfer
from accelerator.cuda.runtime import CudaIndependentKernelLaunch
from accelerator.cuda.runtime import CudaIndependentKernelTimeline
from accelerator.cuda.runtime import CudaIndependentKernelTimelineSample
from accelerator.cuda.runtime import CudaIndependentTransferSubmission
from accelerator.cuda.runtime import CudaKernelLaunch
from accelerator.cuda.runtime import CudaOrderedDtoHStream
from accelerator.cuda.runtime import CudaOrderedTransferBatch
from accelerator.cuda.runtime import create_independent_kernel_timeline
from accelerator.cuda.runtime import create_ordered_dtoh_stream
from accelerator.cuda.runtime import cuda_independent_kernel_launch_id
from accelerator.cuda.runtime import cuda_independent_kernel_timeline_id
from accelerator.cuda.runtime import cuda_independent_ticket_transfer_id
from accelerator.cuda.runtime import cuda_kernel_launch_id
from accelerator.cuda.runtime import cuda_ordered_dtoh_stream_id
from accelerator.cuda.submission import CudaPrimitiveCandidateSubmissionAdapter
from accelerator.cuda.submission import CudaPrimitiveCandidateTicket

__all__ = [
    "CudaDeviceToHostTransfer",
    "CudaExactPrimitiveAdapter",
    "CudaHostToDeviceTransfer",
    "CudaIndependentKernelLaunch",
    "CudaIndependentKernelTimeline",
    "CudaIndependentKernelTimelineSample",
    "CudaIndependentTransferSubmission",
    "CudaKernelLaunch",
    "CudaOrderedDtoHStream",
    "CudaOrderedTransferBatch",
    "CudaPreparedPrimitivePhaseProfile",
    "CudaPreparedPrimitiveStats",
    "CudaPrimitiveCandidateSubmissionAdapter",
    "CudaPrimitiveCandidateTicket",
    "CudaPrimitiveEvaluationTicket",
    "CudaPrimitiveTicketTimeline",
    "CudaPrimitiveTicketTimelineFactory",
    "CudaPrimitiveTicketTransferFactory",
    "CudaProfileSnapshotOverlapWorkspace",
    "CudaProfileSnapshotStreamWorkspace",
    "CudaProfileSnapshotWorkspace",
    "ProfileSnapshotHostRegistration",
    "ProfileSnapshotOverlapAdmission",
    "ProfileSnapshotOverlapCapacity",
    "ProfileSnapshotOverlapSummary",
    "ProfileSnapshotPhaseProfile",
    "ProfileSnapshotStreamCapacity",
    "ProfileSnapshotStreamSummary",
    "ProfileSnapshotWindow",
    "create_independent_kernel_timeline",
    "create_ordered_dtoh_stream",
    "cuda_independent_kernel_launch_id",
    "cuda_independent_kernel_timeline_id",
    "cuda_independent_ticket_transfer_id",
    "cuda_kernel_launch_id",
    "cuda_ordered_dtoh_stream_id",
    "profile_snapshot_host_registration_id",
    "profile_snapshot_overlap_workspace_id",
    "profile_snapshot_stream_workspace_id",
    "profile_snapshot_workspace_id",
]
