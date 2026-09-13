# Tiered monotonic clock adapter

## Purpose

Bind tiered-execution interval timing to the standard-library monotonic clock
without exposing wall-clock time or granting timing code telemetry authority.

## Owns

- opaque `Instant` start evidence;
- process-local monotonic interval completion;
- exact conversion of elapsed duration into `u64` nanoseconds.

## Does Not Own

- wall-clock epochs or calendar time;
- sleep, timers, scheduling, or asynchronous wakeups;
- cached-retry execution, histogram mutation, persistence, or policy selection;
- cross-process clock correlation.

## Failure semantics

Starting an interval only observes `Instant::now()`. Finishing consumes the
opaque start and converts its elapsed duration exactly. If the duration cannot
fit the canonical `u64` nanosecond sample representation, the adapter fails
closed instead of saturating or truncating.
