> Historical record. Current build rules and acceptance checks are in `zen-terminal-contract.md` and `zen-terminal-backtests.md`. Later phase-two and September hardening decisions supersede conflicting text here.

# Step-one handoff: one house (unified browser + terminal containers)

This is a coordinator → build-tab handoff. Build in slices, prove each on a real Mac
DMG, report back with proof before moving on. Do not run ahead to later slices.

## The product, in one line

Keep Zen exactly as it is (workspaces, folders, renamable/draggable tabs, the whole
feel). Make a **terminal a first-class tab** that you open by choosing a **terminal
container**. Positioning: the beautiful cockpit for supervising AI coding agents.

## The mental model (do not drift from this)

- A **container** already exists in Zen = a Firefox contextual identity = an isolated
  cookie jar. Same container shares cookies/logins; different containers are separate.
- We add a **kind** to a container: **web** or **terminal**.
  - **Web container** = a saved login (unchanged from today).
  - **Terminal container** = a saved **startup recipe**: name/colour/icon + a folder to
    start in + a launch recipe (commands). Opening it spawns a terminal tab that runs
    the recipe.
- **Plain New Tab → a browser tab** (normal). The ONLY way to get a terminal is to
  intentionally open a **terminal container**. Even a plain blank terminal is a
  terminal container with an empty recipe. No terminal exists outside a container.
- Everything lives in ONE place: the native container list + `about:preferences#containers`.
  No separate terminal menu, no separate terminal-containers page, no second list.

## Recipe execution — the one hard part

A recipe is NOT a set of lines blind-fired into the shell. That races: `claude` would
be typed locally before `ssh` connects. It must **self-sequence**. Use forms where each
tool does its own waiting, e.g.:

```
ssh -t chubs 'tmux new -A -s claude "claude --dangerously-skip-permissions"'
```

`ssh -t` allocates a tty and only runs the remote command AFTER connecting; `tmux new -A`
attaches-or-creates so the session survives closing/reopening the tab. The container is a
**doorway that reconnects you to where the state already lives** (your local home where
Claude is already logged in; or a tmux session on the server) — not a vault that stores
state. Per-container isolated logins are a LATER concern; running the recipe in the normal
Mac home already yields a logged-in Claude for step one.

**Proving test case (Slice 2): "Claude on Chubs".** Open the container → land in a live,
persistent Claude-on-Chubs tmux session, reliably every time; reopen later → resume the
same session. If that one works, the terminal-container idea is proven on the hardest real
case. ("Record-it-once" — do the setup live and have the app capture it as the recipe — is
polish for later; start with a typed/stored recipe.)

## Audit: keep / rework / delete (vs this model)

KEEP (the good core):
- `src/zen/terminal/ZenTerminalPage.mjs`, `terminal.xhtml`, `vendor/xterm.*`,
  `zen-terminal-page.css` — the actual terminal (real shell via Subprocess + xterm).
- Build wiring: `jar.inc.mn` (now fixed), `moz.build`, preload, CI workflow.

REWORK:
- `src/zen/terminal/ZenTerminalTabs.mjs` — keep "open a terminal tab"; rip out the
  separate-menu / terminal-container-picker / manage-page bridging.
- `src/zen/common/zen-sets.js` — keep the plain open command; drop the container-menu one.
- `scripts/terminal-tabs/check-terminal-tabs.mjs` — rewrite to assert the new structure.

DELETE (the tacky parallel system):
- `src/zen/terminal/ZenTerminalContainers.mjs`, `containers.xhtml`,
  `zen-terminal-containers.css` (separate manage page).
- `popups.inc` additions: "Terminal Tab", "Terminal Container Tab" submenu.
- `scripts/terminal-tabs/patch-engine-newtab-menu.mjs` (injects terminal choices into the
  native container menu) + its step in the CI workflow.
- the separate `zen.terminal.containers` pref concept (replace with a per-container record
  keyed by userContextId — see below).

## Technical crux to investigate FIRST (report before deep build)

Containers are Firefox contextual identities, shown in the native list and managed at
`about:preferences#containers` (Firefox's own page; Zen patches it via
`preferences-xhtml.patch`). To make terminal containers live in that same area and be
creatable there with a Web/Terminal fork, investigate the cleanest approach and report:
- Option A: patch the native container preference pane + "Add New Container" dialog to add
  the kind fork + recipe fields, and keep a Zen-side map `userContextId → {kind, folder,
  recipe}`. Container stays a real contextual identity (native list/colour/icon/name for
  free); Zen remembers which are terminals + their recipe.
- Option B: Zen-native container objects rendered into the same list/pane.

Recommend A unless you find a blocker. Report the chosen approach + why before building it.

## Slice plan (prove foundation before rebuilding on top)

**Slice 0 — get a working DMG at all (do this first).**
The core tech has never been seen working end-to-end in a packaged app.
- Commit the staged `jar.inc.mn` fix (all source paths now use the `../../zen/terminal/`
  prefix; this was why Jun-30 builds failed at packaging on `containers.xhtml`).
- Push branch `terminal-tabs-zen-source` to `fork` (`flyemlankan-ux/desktop`).
- Run the "Terminal macOS Dev Build" GitHub Action (aarch64).
- Download the DMG. Human proof: open the app, open a terminal (current UI is fine for
  now), confirm a real shell runs (`pwd`, `echo hello`, `whoami`). Report result. There may
  be a second build error hiding behind the first — surface it.
Acceptance: a real Mac app exists and runs a shell in a terminal tab.

**Slice 1 — one house (the unification).**
- Delete the parallel system (see DELETE list).
- Add container kind (web/terminal) + the "Add New Container" fork (ask kind BEFORE
  name/colour/icon). Web branch unchanged. Terminal branch adds folder + recipe fields.
- Plain New Tab → browser tab. Opening a terminal container → terminal tab running its
  recipe (start folder + a simple single command for this slice).
- Terminal tabs behave like real Zen tabs: rename, drag, folders, workspaces, session
  restore. This can only be proven by running the DMG and watching — do it.
Acceptance (human, on DMG): make a terminal container in the same place as web ones; open
it → terminal tab in the right folder; move it into a folder / rename it / switch
workspaces / restart → it behaves like any Zen tab. No separate terminal menu or page
remains.

**Slice 2 — reliable multi-step recipe, proven on "Claude on Chubs".**
- Store + run a self-sequencing recipe. Prove the "Claude on Chubs" case: open → live
  persistent Claude-on-Chubs tmux session; reopen → same session.
Acceptance (human, on DMG): the Claude-on-Chubs container lands you in a working Claude
session every time, and resumes after closing the tab.

DEFERRED beyond step one: clickable terminal links → open a web tab in the same window;
"record-it-once" recipe capture; per-container isolated logins/home dirs; terminal look
personalisation; auto-labelling tabs by status.

## Build/proof mechanics

- Local code proof: `node scripts/terminal-tabs/check-terminal-tabs.mjs` (rewrite it as
  the structure changes; passing it is necessary but NOT sufficient).
- No full local build (this Mac lacks disk). Real proof = the cloud DMG from the GitHub
  Action, opened and used by hand.
- Report each slice back to the coordinator with: what changed, backend/data-model changes
  in plain words, and the human-proof result. Wait for coordinator sign-off before the
  next slice.
