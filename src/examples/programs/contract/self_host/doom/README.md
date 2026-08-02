# Self-hosted DOOM target

This directory reserves the canonical destination for a future generated
`doom.malbolge`. Generated self-hosting products remain local and are ignored by
Git; no placeholder artifact is checked in.

The native `doom.c` debug path and its Windows host adapter are development
scaffolding only. The eventual artifact must execute the admitted guest program
under Malbolge semantics without linking the host adapter, host libc, or
platform
math libraries.
