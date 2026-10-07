# Tiered relative-wait adapter

## Purpose

Bind tiered product-lifecycle relative waiting to the standard library without
changing the monotonic interval clock or granting cache policy authority.

## Owns

- positive relative durations expressed in canonical nanoseconds;
- blocking the current host thread with `std::thread::sleep`;
- completion after the standard-library wait returns.

## Does Not Own

- wall-clock epochs or elapsed-time measurement;
- trigger cadence, cache policy, retry decisions, or durable state;
- background threads, worker pools, cancellation, or async wake handles.

## Failure semantics

The standard-library adapter is infallible after construction because
`std::thread::sleep` exposes no recoverable error result. The transport-neutral
port still carries an adapter error type so another runtime can report explicit
wait failure without weakening lifecycle policy.
