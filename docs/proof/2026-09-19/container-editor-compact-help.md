# Compact native terminal setup help

Viewed `current156-overlay-container-dialog.png` before changing the source. The native form was tall, and the terminal explanation consumed several lines above the actual step fields.

Updated only the three help paragraphs in the shared ContainerEditor patch:

- “Blank uses home. Use a literal path starting with /; ~ and variables are not expanded.”
- “Changes affect new terminals only. Running work stays unchanged.”
- “Steps run in order; failure stops later steps. A simple SSH connection sends later steps to that computer.”

This reduces these paragraphs from 58 to 43 words. All semantic warnings remain visible rather than hiding critical information in collapsed help. No stock name/color/icon controls, accessible labels, input descriptions, dimensions, shell behavior or save behavior changed. Both native container-creation surfaces use the same editor; no duplicate copy changes were necessary.

Proof:
- Firefox156 Settings: 13 behavior tests pass, including new exact compact-copy and accessible-description checks. All five patches apply without fuzz to hash-verified pristine Firefox156 sources.
- Firefox155 compatibility Settings: 12 tests pass; all five strict patches apply.
- Asset verifier tests: 10 pass. Expected native assets are regenerated from pristine156 fixture bytes and the updated patch; the original upstream receipts were correctly left unchanged.
- No UI launched and no updated screenshot inspected. Reduced actual rendered height remains a parent screenshot check after rebuilding, not a claimed visual pass.

Recap: The editor explanation is shorter without losing warnings. This is a small part of making the normal Zen container form usable for terminal setups, not a redesign. The next likely slice is native screenshot review after rebuild. Recommended handoff: medium reasoning, strict patch/behavior proof plus one real screenshot. Drift check: no advanced UI was added simply to hide safety information.
