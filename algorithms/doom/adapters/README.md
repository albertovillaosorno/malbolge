# DOOM Capability Adapter Scaffold

This directory reserves DOOM application-side adapter work that must stay
outside the guest source. The guest itself depends only on the semantic
`DoomHost_*` capability ABI.

Expected adapter domains include video, input, timing, audio, and data access.
Native implementations belong to the appropriate runtime/runner responsibility;
this directory must not become a second platform-specific DOOM port.
