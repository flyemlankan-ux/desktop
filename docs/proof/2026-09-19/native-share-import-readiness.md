# Native sharing import: faithful local-transport test ready

## What changed / current state
New `test-terminal-share-import-macos.py`; Python syntax checked, not executed. No product changes or native UI launched.

## Why this can test the real UI without an external share
Actual156 `ZenShareManager` registers its real location listener, creates its real preview overlay, calls the real `ZenShareClient.fetchSharePreview`, validates the whole document, and its actual Add button invokes the private importer. Client already supports `zen.share.base-url` as its server address.

The test runs a loopback-only HTTP fixture server and sets that preference only in the synthetic profile. This is a transport fixture, not a mocked manager/fetch/validator/importer method. Schema comes from the packaged resource URL as normal. The server never logs request headers. It rejects every POST, exposes no account/upload operation, and serves only local safe HTML and six fixed share responses. No external website or sharing service is contacted by the journey.

## Actual acceptance checks parent will run
- Own PID/profile/data confirmed; real share manager loaded.
- Navigate a real tab to the local share URL, wait for visible enabled native preview Add button; preview must not create tabs/folders/workspaces or alter terminal records/recipes.
- Click the actual rendered button through Marionette, require original preview tab to close, exactly one new real folder, two pinned ordinary web tabs, no terminal attributes/container IDs, no new workspace/session/recipe changes. Select each imported page and confirm its exact loopback URL really fetches.
- Fetch malformed nested payloads with a safe first child followed by terminal chrome, javascript, file, or data URL. Real client/validator must display invalid-document feedback and keep Add hidden/disabled with no partial browser-state mutation.
- Fetch a safe web URL carrying extra terminal-session metadata; real packaged schema must reject it before mutation.
- Assert no upload/unexpected fixture request, then quit exact owned process and stop loopback server. No tmux session is expected or created.

The snapshots allow the intentional navigation of the existing preview-host tab but hold its identity, all other tab IDs, folder IDs, workspace IDs, terminal sessions and recipes fixed. They do not mistake opening a preview host tab for an import mutation.

## Not proved
External service availability, authentication, upload, account permissions, or server-side storage. These are explicitly not_run in the receipt. A local fixture can prove unmodified browser validation/confirmation/import behavior, not the external service.

## Parent command / next
`/Users/ar/zen-terminal-research/desktop/.terminal-test/venv/bin/python3 scripts/terminal-tabs/test-terminal-share-import-macos.py --app '.terminal-test/Zen Terminal Test 156.app' --label share-import156`

Parent runs when UI ownership is free. High reasoning for schema/import mutation issues; proof must be actual overlay button plus native folders/tabs, not private-method extraction. Full project remains normal Zen with deliberate terminal behavior; this slice does not add a sharing feature or send any personal data.

## First execution / readiness correction
Parent's `share-import156` attempt reached the real preview, then Marionette correctly refused the Add click because `#zen-update-animation-border` covered its center. Original failure receipt/log remain unchanged.

Source inspection: `ZenUpdates.mjs::playWindowSweepAnimation` inserts the border in `requestIdleCallback`; a350ms animation with80ms delay removes both sweep nodes when its Promise completes. The border CSS covers the window and does not disable pointer events. This establishes an expected transient interception path, not proof that a permanently stuck animation is harmless.

The test now waits for both actual sweep nodes to disappear AND for the visible enabled button's center hit-test to resolve to that button/descendant. It then uses the same real Marionette click. A narrowly bounded retry (max3) handles only the named sweep appearing between the hit-test and click; other interception errors fail immediately. Each readiness wait is capped20seconds. No node deletion, altered CSS, preference disabling, event dispatch, JS `.click()`, or force-click introduced. Persistent animation remains a failure. Python compilation/diff checks pass; no UI launched by this worker. Parent should use a new label, e.g. `share-import156-v2`, preserving the original failed receipt.

## Actual parent execution accepted for the bounded folder journey
Inspected `share-import156-v2-share-import.json`: failure=null, seven PASS records, one explicit external-service not_run, and no unexpected requests. It proves the unmodified production preview/confirmation/importer created a safe real folder, while four unsafe schemes and extra metadata were rejected before mutation. This is actual native import UI with loopback transport, not merely validator-unit proof. External service/authentication/upload remains unproved. The earlier intercepted-click failure is retained.

## Optional extended cases prepared, not executed
`--extended` adds three bounded records without changing the original default journey:
1. Actual stored terminal-key names `zenTerminalSessionId` and `zenTerminalOwnership` on a safe web entry must be rejected with no mutation.
2. Dismiss a valid preview using real Cmd+W (production overlay has no Cancel button); browser state must exactly match before opening it.
3. Real workspace preview containing an ordinary web tab and two levels of folders; actual rapid two-click W3C input on Add must create exactly one workspace, both genuine nested folders, and exactly two normal website tabs, with unchanged terminal recipes/session records. Uses actual production workspace/folder creation, not a mocked importer. Existing hit-test/readiness guard retained.

Metadata scope: v2's `zenTerminalSession` was an arbitrary unsupported property. Its rejection proves packaged schema additionalProperties=false for that tab entry; it did not specifically exercise the real stored key names or prove export redaction. New optional case covers representative actual key names. Source separately shows export excludes any terminal-marked tab, including one currently displaying a website. This native import test still does NOT establish export-to-server privacy; no upload is performed.

Next parent command: same script with a new label and `--extended`. Python syntax and scoped whitespace checks pass. No UI launch. High reasoning for mutation/reentrancy issues; count exact post-click workspaces/folders rather than claiming an attempted double click alone proves idempotence against arbitrary programmatic handler calls.

## Extended native acceptance result
Inspected `share-import156-extended-share-import.json`: **10 PASS**, failure=null, no unexpected fixture requests, and external-service/account/upload remains explicitly not_run. Parent ran the real native UI; this documentation update did not launch it.

The added actual stored terminal session/ownership key names were rejected before mutation. Real Cmd+W dismissed a valid preview without creating imported state. Rapid actual repeated Add activation created exactly one workspace with the genuine nested-folder structure and two ordinary website tabs; terminal recipes/session records remained unchanged. The original safe-folder import and unsafe-scheme rejection checks also passed in this run.

This closes the prepared local-transport native import journey, including confirmation/cancel/repeated activation and representative unsafe metadata. It does not claim external sharing authentication, upload/export privacy, arbitrary programmatic reentrancy, or final compiled-package acceptance. No further tests or production changes were added in this update.
