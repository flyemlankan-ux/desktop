# Small native-consistent polish review

Read-only review. Screenshot inspected: `project-review-project-workflows.png` (1800×1200). No UI launch or production edits during this review.

## Visible findings

1. Address field shows a clipped internal query containing `userContextId` and session details, with an unrelated robot icon. This reads like a developer tool rather than a normal saved terminal setup.
2. Selected terminal tab displays BOTH the ordinary placeholder square and a small `›_` glyph below it. This is an alignment bug, not a subjective preference. Source hides `list-style-image` but inserts a pseudo-element without replacing native icon layout.
3. An **Update Complete!** notification appears in this manual-update fork. It suggests an updater ran when it did not. Source `ZenUpdates.mjs` triggers this on changed `Services.appinfo.version`, including a new profile.
4. Large persistent bottom strip says **session saved · ready**. Its body/UI text is visibly larger than terminal content and contains a green prompt glyph. This overstates disk/reboot durability and creates another decorative terminal identity beside the real shell prompt.
5. Core Zen geometry looks retained: rounded content frame, shared sidebar folder, native selected-tab/container accent. Preserve these rather than designing a new sidebar/header.

## Smallest changes, in priority order

### A. Fix the tab icon, not Zen's tab layout

Use the already shipped native icon `src/browser/themes/shared/zen-icons/common/selectable/terminal.svg` (verify its final chrome resource URI in the packaged jar before referencing). Set it through the ordinary tab image surface or replace the one native icon slot with a 16px context-fill image. Remove the `::before` text glyph entirely. Do not suppress the independent audio/sharing/status overlay, container accent, custom user icon, or native close button. Test normal, pinned, essential, folder, compact, split-view and selected/unselected states. Existing user custom icons should take precedence.

### B. Friendly terminal identification in the address field at rest

Show **Terminal · saved setup name** when viewing an owned terminal instead of its implementation query. Preserve the real browser URI and all principal/container checks; never rewrite it to a fake website URL or trust a text label to decide whether a tab is a terminal.

Safest bounded approach is a presentation-only label while this exact terminal page is selected and the address field is not being edited; remove it when focusing/typing, selecting a web tab or leaving the terminal URI. Keep normal Cmd+L, typing/navigation, copy semantics and Escape restoration intact. Use the existing address field rather than adding another top bar. If achieving this requires invasive native address editing changes, stage it separately and test those transitions before shipping. A globally monkeypatched URL getter or repeated timer to overwrite input text is not acceptable.

Source integration point for inspection: existing `src/browser/components/urlbar/content/UrlbarInput-mjs.patch`; `ZenUIManager.mjs` already calls `gURLBar.setURI` and `handleRevert` during native focus/restore. Must integrate with that flow, not fight it on TabSelect alone.

### C. Stop the false updater message at its source

`src/zen/common/modules/ZenUpdates.mjs` has `zen.updates.show-update-notification`. For this fork's manual-update configuration disable the stock update-complete prompt as a deliberate fork default (not a test-only pref). Do not disable real future security/update notices globally or mark the upstream welcome screen seen just to hide it. Normal Zen UI stays unchanged outside the inaccurate notification. A separate honest update/About message can say this is a development build that needs manual updates.

### D. Make terminal state quiet and truthful

Use the browser UI font and a compact neutral status strip; remove duplicate green prompt ornament. **Running** and **Reconnected** are enough for steady state. Keep actionable errors/disconnect/restart controls visible and accessible, with the existing live-region announcement. Explain background-session behavior and reboot limitations through a compact discoverable hint, not the word **saved** alone. Do not auto-hide failure states or hide keyboard focus.

Keep shell text monospace and the current native content margins. Remove decorative green gradients in favor of plain high-contrast terminal background. A full light-theme/xterm palette switch needs its own contrast/state proof; this review does not claim it is solved by changing one background color.

## Native editor review

Follow-up report `saved-setups-native-test-handoff.md` records source-only issues: tall prose plus steps needs short-window proof; shared alert below long step list needs visibility/focus; row rebuild can lose keyboard focus; custom strings remain English. New folder field's label, typed path and browse alternative are good. Do not replace Zen name/color/icon pickers with another form.

## Acceptance required

Inspect actual before/after screenshots in light/dark, compact and narrow windows. Test native address focus/typing/Escape/website switch, custom tab rename/icon, pin/folder/split states, error recovery, and keyboard-only saved-setup editing. Changes to appearance are not accepted merely because styles apply.

Recommended reasoning: medium for icon/style-only work, high for address-bar semantics and status truthfulness. Proof: focused native interaction plus visual inspection; no unrelated Core regressions.
