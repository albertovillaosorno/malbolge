# Historical Malbolge Interpreter

`main.c` is Ben Olmstead's original 1998 Malbolge interpreter retained as an
immutable compatibility oracle.

The upstream source explicitly places the interpreter in the public domain. The
repository keeps the file unchanged and does not relicense it under the project
MIT License. Project-authored wrappers, tests, harnesses, and documentation are
separate repository material.

Canonical upstream references:

- <https://www.lscheffer.com/malbolge_interp.html>
- <https://www.lscheffer.com/malbolge_spec.html>

The oracle exists to answer compatibility questions for behavior whose original
implementation is defined. Historical undefined behavior and implementation
defects are cataloged separately and are not copied into modern implementations
merely because they occur in this C program.

Do not modify `main.c` when adding sanitizer builds, differential tests, or
compatibility fixtures. Put repository-owned support beside or outside the
historical file and preserve the oracle bytes.
