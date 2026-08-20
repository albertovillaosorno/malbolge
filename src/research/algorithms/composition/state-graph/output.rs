// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - Persistent append-only committed-output storage for state-graph research.
// - Must-Not:
//   - Drop historical output from observable state or trust digest equality
//   - alone.
// - Allows:
//   - Inputs: validated initial output bytes and committed output-byte appends.
//   - Outputs: shared output histories, exact equality, digest,
//   - materialization.
//   - Side effects: process-local allocation only.
// - Split-When:
//   - Split when chunked/interened output storage needs independent evidence.
// - Merge-When:
//   - Merge when production graph state owns the same output-history contract.
// - Summary:
//   - Replaces per-state output-vector copying with immutable append nodes.
// - Description:
//   - Exact equality uses shared-tail shortcuts and byte comparison on
//   - fallback.
// - Usage:
//   - Consumed by incremental state identity in `state.rs`.
// - Defaults:
//   - Digest is an acceleration hint; complete output bytes remain
//   - authoritative.
//

//! Persistent append-only committed output for exact state identity.

use std::sync::Arc;

const FNV_OFFSET: u64 = 14_695_981_039_346_656_037;
const FNV_PRIME: u64 = 1_099_511_628_211;

/// One persistent committed-output history.
#[derive(Clone, Debug)]
pub struct PersistentOutput {
    base: Arc<[u8]>,
    digest: u64,
    len: usize,
    tail: Option<Arc<OutputNode>>,
}

#[derive(Debug)]
struct OutputNode {
    byte: u8,
    parent: Option<Arc<Self>>,
}

impl PersistentOutput {
    /// Returns a new history with one committed byte appended in constant work.
    #[must_use]
    pub fn append(&self, byte: u8) -> Self {
        Self {
            base: Arc::clone(&self.base),
            digest: hash_byte(self.digest, byte),
            len: self.len.saturating_add(1),
            tail: Some(Arc::new(OutputNode {
                byte,
                parent: self.tail.clone(),
            })),
        }
    }

    /// Returns the deterministic incremental digest of complete output bytes.
    #[must_use]
    pub const fn digest(&self) -> u64 {
        self.digest
    }

    /// Returns exact output equality inside one shared immutable base lineage.
    #[must_use]
    pub fn exact_output_eq(&self, other: &Self) -> bool {
        if !Arc::ptr_eq(&self.base, &other.base)
            || self.len != other.len
            || self.digest != other.digest
        {
            return false;
        }
        tails_equal(self.tail.as_ref(), other.tail.as_ref())
    }

    /// Constructs one immutable output lineage from existing committed bytes.
    #[must_use]
    pub fn from_bytes(bytes: &[u8]) -> Self {
        Self {
            base: Arc::from(bytes),
            digest: hash_bytes(FNV_OFFSET, bytes),
            len: bytes.len(),
            tail: None,
        }
    }

    /// Returns whether this output history contains no committed bytes.
    #[must_use]
    pub const fn is_empty(&self) -> bool {
        self.len == 0
    }

    /// Returns the exact number of committed output bytes.
    #[must_use]
    pub const fn len(&self) -> usize {
        self.len
    }

    /// Materializes all committed output bytes in original order.
    #[must_use]
    pub fn materialize(&self) -> Vec<u8> {
        let appended = self.len.saturating_sub(self.base.len());
        let mut suffix = Vec::with_capacity(appended);
        let mut node = self.tail.as_deref();
        while let Some(current) = node {
            suffix.push(current.byte);
            node = current.parent.as_deref();
        }
        suffix.reverse();
        let mut output = Vec::with_capacity(self.len);
        output.extend_from_slice(&self.base);
        output.extend_from_slice(&suffix);
        output
    }
}

impl Drop for PersistentOutput {
    fn drop(&mut self) {
        let mut current = self.tail.take();
        while let Some(node) = current {
            match Arc::try_unwrap(node) {
                Ok(mut owned) => {
                    current = owned.parent.take();
                },
                Err(_shared) => break,
            }
        }
    }
}

fn hash_byte(hash: u64, value: u8) -> u64 {
    (hash ^ u64::from(value)).wrapping_mul(FNV_PRIME)
}

fn hash_bytes(mut hash: u64, values: &[u8]) -> u64 {
    for value in values {
        hash = hash_byte(hash, *value);
    }
    hash
}

fn tails_equal(
    left: Option<&Arc<OutputNode>>,
    right: Option<&Arc<OutputNode>>,
) -> bool {
    let mut left_node = left;
    let mut right_node = right;
    loop {
        match (left_node, right_node) {
            (None, None) => return true,
            (Some(left_arc), Some(right_arc)) => {
                if Arc::ptr_eq(left_arc, right_arc) {
                    return true;
                }
                if left_arc.byte != right_arc.byte {
                    return false;
                }
                left_node = left_arc.parent.as_ref();
                right_node = right_arc.parent.as_ref();
            },
            (None, Some(_node)) | (Some(_node), None) => return false,
        }
    }
}
