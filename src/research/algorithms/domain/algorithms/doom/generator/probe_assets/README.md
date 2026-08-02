# DOOM Behavior Probe Assets

These files are repository-owned MIT harnesses and minimal freestanding header
shims used to observe behavior of a **user-supplied** DOOM source mirror. They
do
not contain copied DOOM implementation source and must never be replaced with
files from the ignored `doom/` tree or the local quality oracle.

`fixed_point/` is the first executable identity probe profile. On Windows x86-64
it uses pinned LLVM 22.1.8 to compile the candidate mirror's `m_fixed.c`, link a
no-CRT PE, execute a private entry point, and record only its exit code. The
source and local oracle are read-only inputs; generic probe execution provides a
temporary source mirror for compilation.
