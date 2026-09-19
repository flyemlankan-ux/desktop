# Starting folder implementation handoff

Status: production implemented, focused source/process tests pass; actual Mac UI/chooser and packaged acceptance remain pending. No commit created. Canonical whole-product plan remains on Chubs.

## What changed

- Saved recipes now use version 4, with optional literal `recipe.startingDirectory`. Old command and ordered-step data retain their meaning; missing folder means home. Explicit malformed folder values survive normalization so validation rejects them rather than silently running elsewhere.
- Native container editor has a labelled Starting folder input, Choose folder button using the macOS folder picker, blank/home explanation, and notice that edits apply only to new terminals.
- Picker cancellation leaves input unchanged. Picker results never save by themselves. Failure leaves manual entry available. Results are ignored if the editor closed.
- Syntax and native filesystem checks reject relative paths, control characters, non-string values, nonexistent folders, files, inaccessible folders and access errors. No tilde or environment expansion. Legal spaces, Unicode and shell punctuation are retained exactly.
- New shells receive cwd as a distinct process/tmux argument and a safely quoted shell `cd` guard before configured startup commands. If the folder disappears during launch, no configured startup command runs in a fallback location.
- Existing tmux sessions bypass newly edited folder and command validation: the manager invokes a settings callback only after confirming the old session is absent. Existing processes are not modified by setup editing.

## Files owned and changed

- `src/zen/terminal/ZenTerminalContainerStore.mjs`
- `src/zen/terminal/ZenTerminalRecipeRunner.mjs`
- `src/zen/terminal/ZenTerminalPage.mjs` — subsequently released to security worker.
- `src/zen/terminal/ZenTerminalSessionManager.mjs` — subsequently released to security worker.
- `src/browser/components/contextualidentity/content/ContainerEditor-mjs.patch`
- `scripts/terminal-tabs/test-terminal-recipes.mjs`
- `scripts/terminal-tabs/test-terminal-settings155.mjs`
- `scripts/terminal-tabs/test-terminal-session-persistence.mjs` — released.
- `scripts/terminal-tabs/test-terminal-browser.mjs` — released to security worker.

No new runtime module or packaging manifest needed.

## Proof run

- `node scripts/terminal-tabs/test-terminal-recipes.mjs`: **27 pass**. Includes preserved old recipes, literal paths, malformed values, missing/non-directory/unreadable/throwing file checks.
- `node scripts/terminal-tabs/test-terminal-session-persistence.mjs`: **16 pass**, including real isolated tmux. Added live reconnect ignoring invalid edited setup, new-job validation before creation, and real shell quote/missing-folder guard checks.
- `node scripts/terminal-tabs/test-terminal-settings155.mjs`: **12 pass**, plus five hash-verified pristine Firefox 155 source patch checks. Added folder choose/save/reopen/cancel, invalid save writes nothing, and picker failure fallback.
- `node scripts/terminal-tabs/test-terminal-polish.mjs`: pass.
- `node scripts/terminal-tabs/check-terminal-tabs.mjs`: pass.
- `node --check scripts/terminal-tabs/test-terminal-browser.mjs`: pass. Added literal-folder real helper workflow and existing-session versus new-session edited-folder failure check; **not run** because parent owns UI execution.

## Limits / next checks

- Settings tests use synthetic DOM and picker callbacks. They do not establish native sheet behavior, final appearance or actual keyboard accessibility.
- Parent must test installed/overlaid native Settings input, native picker acceptance and cancellation, small-window/light/dark layout, save/reopen and actual cwd before acceptance.
- Shell initialization files remain user-owned executable configuration, as in a normal terminal. The no-command guarantee here is specifically about configured startup steps not running in the wrong folder, not a promise that login shell initialization files cannot run.
- When a configured recipe intentionally changes directory, its final directory is preserved. No forced post-recipe directory reset was introduced.
- No UI launched, original browser/profile data touched, remote command launched, personal data copied or broad product plan recreated locally.

Reasoning for next handoff: high. Proof: focused actual Mac saved-setup journey plus native chooser and rendered-page tests, not unrelated repository regressions. Production UI completion is not yet claimed.
