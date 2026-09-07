# Phase 2 handoff: persistence, ordered recipes, cleanup, safety, polish

Coordinator → build-tab. The core is PROVEN (terminal-as-tab, containers, Claude Code runs
and responds inside a terminal tab, folders/workspaces/rename/restore all work). This phase
is one batched build covering everything found in a full live test pass. Build it all, then
one DMG. Order below is by priority.

## A. HEADLINE FEATURES

### A1. Persistent terminal sessions (tmux-backed) — TOP PRIORITY
Today a session respawns FRESH on app restart — context lost. Requirement: a terminal
session (the shell + whatever runs in it: Claude, codex, a job) must SURVIVE app
quit/restart/crash. The ONLY thing that may destroy it is the user explicitly closing that
tab (or deleting its container).
- Run every terminal inside a background session-keeper: `tmux new -A -s <stable-tab-id>`
  (attach-or-create). Use a stable id per tab so restore re-attaches the SAME session.
- The tmux server outlives the app, so on relaunch the tab RE-ATTACHES with full context
  (Claude conversation intact, running job still running), instead of spawning fresh.
- On explicit tab-close OR container-delete: `tmux kill-session -t <id>` (this is the only
  time context is lost).
- Requires tmux present; if missing, fall back to current respawn behaviour and note it.
- Acceptance (human, DMG): open Claude container, have a conversation, ⌘Q, relaunch →
  the SAME Claude conversation is still there (not a fresh start). Close the tab → gone.
- Edge (defer, just note): a full macOS reboot kills the tmux server; out of scope now.

### A2. Ordered step recipes (the "+" builder)
Replace the single recipe command box with an ORDERED LIST OF STEPS the user builds with a
+ button. Each step = one plain command. Steps run IN ORDER, each firing only once the
previous is READY.
- UI in the container Settings dialog: a list of step rows + an "Add step" (+) button;
  remove/reorder steps.
- Example "Claude on Chubs": step1 `ssh chubs@100.92.30.93`, step2
  `claude --dangerously-skip-permissions`. Open container → SSH connects, THEN Claude runs
  on the remote.
- DO NOT expose `ssh -t host '...'` syntax to the user — the user just lists plain steps;
  the runner handles sequencing.
- The hard part = "wait until ready before next step". Investigate + pick the robust
  approach (idle-output detection, prompt detection, or compile-to-self-sequencing under the
  hood). Report the approach.
- Store already reserves `steps: []`. Blank steps = plain shell in home.
- Acceptance (human, DMG): a container with steps [ssh chubs, claude] lands the user in
  Claude ON the server, reliably.

## B. CLEANUP (delete the old bolted-on system — now safe, native flow proven)
- The native Settings → Container Tabs → "Add New Container" (Web/Terminal fork) is the ONLY
  way to add a container. Delete the old standalone "Terminal Containers" page
  (ZenTerminalContainers.mjs, containers.xhtml, zen-terminal-containers.css) + its sidebar
  entry + patch-engine-newtab-menu.mjs.
- The New Tab / create menu must show ONLY: the user's containers (web AND terminal, mixed
  in one list — click to launch) + one native "Manage containers". DELETE the duplicate
  items: "Terminal Tab", "Terminal Container Tab", "New Terminal Tab", "New Terminal
  Container Tab", "Manage Terminal Containers…". A plain terminal = the default terminal
  container in the list.
- Cosmetic: remove the "Back to pinned url" sublabel under terminal tabs; fix the doubled
  "Claude Claude" tab hover badge; ensure single "Terminal" kind label.
- Acceptance: one unified container list, one manage entry, no old page, no duplicate menu
  items.

## C. SAFETY (kill the unsigned-build friction family)
- DISABLE the Zen auto-updater in our build. It offered "Twilight 1.22t" and "Restart
  Twilight" would OVERWRITE our custom build with stock Zen — dangerous. Turn it off
  entirely (app.update.* prefs / updater config).
- The recurring macOS security popups — `.node` "can't be opened", "would like to access
  data from other apps", the install nag — all stem from the app being an unsigned,
  sandboxed dev build that quarantines/claims responsibility for files its child processes
  write, blocking agents' native modules on every launch. Fix direction: (1) disclaim
  quarantine/TCC responsibility when spawning the terminal shell so its files aren't flagged
  (e.g. responsibility_spawnattrs_setdisclaim on the posix_spawn, or spawn outside the app's
  quarantine domain); and/or ad-hoc codesign the build. Goal: no security popup on normal
  Claude/codex launch. Report what you did.
- Acceptance (human, DMG): launch Claude container repeatedly → NO Gatekeeper/update/install
  popups.

## D. POLISH (terminal feel)
- Scrolling is glitchy/janky — make it smooth.
- Terminal doesn't fill the whole tab (dead margins) — size the xterm grid to fill the
  content area; reflow on window resize.
- Streaming output is janky/not-smooth as an agent types — improve render performance so
  live output is smooth.
- (Note, not a code fix: general browser sluggishness = PGO disabled in this dev build; a
  proper release build closes most of it. Keep dev build for now; flag when we want a
  release build.)
- Acceptance (human, DMG): scroll a long output smoothly; terminal fills the tab; Claude
  streaming looks smooth.

## Build/proof mechanics
- Local code proof: rewrite `scripts/terminal-tabs/check-terminal-tabs.mjs` for the new
  structure (delete old-page checks, add persistence/steps/menu checks). Passing it is
  necessary not sufficient.
- Real proof = cloud DMG, opened and driven by hand (coordinator guides founder).
- Report back per section with plain-English "Backend changes", which items landed, and the
  DMG link. Keep the report short.
