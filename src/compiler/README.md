# Compiler

## Purpose

Guest-language parsing, normalization, typed IR, lowering, and target encoding.

## Ownership

This boundary is owned by `repository:malbolge`.

## Prohibitions

It must not collapse frontend, portable IR, lowering, or runtime ownership.

## Navigation

- [`c-frontend/`](c-frontend/): governed function `c-frontend`.
