# Zen Terminal — recovered decisions

Canonical root: `/Users/ar/zen-terminal-research/desktop`. Host: standalone macOS Zen fork, not Empire Core.

This is recovery of the existing handoffs, not an invented interview. No new numbered Q&A pairs were asked. On September 7 the founder authorized autonomous completion and self-testing. Existing product choices remain in force.

Sources: `terminal-tabs-step-one-handoff.md`, `terminal-tabs-phase2-handoff.md`, `terminal-tabs-test-plan.md`, current code at `38718ac`. Earlier notes about a primitive terminal are superseded by the xterm implementation. Phase 2 explicitly supersedes the earlier suggestion that closing a tab keeps its session: explicit close destroys it; quitting the app preserves it.

## Recovered rules

### R01
Keep real Zen navigation, browser tabs, folders and workspaces; terminal tabs belong to native containers.
Source: step-one handoff: product and mental model. Enforced by C01, tested by B01.

### R02
Native Settings is the single place to create web or terminal containers; mixed launch list, no duplicate terminal menus.
Source: phase2 B. Enforced by C02, tested by B02.

### R03
A terminal accepts every keystroke exactly once, Unicode and paste; Ctrl-C, arrows and fullscreen programs work.
Source: test plan: keyboard and shell; July 4 input fix. Enforced by C03, tested by B03.

### R04
A running session survives reload, app quit/relaunch and app crash; recipes do not rerun on reattachment.
Source: phase2 A1. Enforced by C04, tested by B04.

### R05
Explicit tab close or container deletion destroys only the matching session; failed cleanup remains retryable.
Source: phase2 A1; existing SessionManager. Enforced by C05, tested by B05.

### R06
Missing tmux permits a plain shell but visibly says session saving is unavailable; full Mac reboot recovery is deferred.
Source: phase2 A1. Enforced by C06, tested by B06.

### R07
Startup steps can be added, removed and reordered; local commands run in sequence; SSH must connect before remote commands run.
Source: phase2 A2. Enforced by C07, tested by B07.

### R08
Reject ambiguous connection steps rather than running remote commands locally; preserve old recipes.
Source: step-one recipe execution; current recipe tests. Enforced by C08, tested by B08.

### R09
Smooth bounded output rendering, correct terminal size on resize, usable copy and paste.
Source: phase2 D; build path. Enforced by C09, tested by B09.

### R10
Custom app has a distinct identity and no stock auto-updater; no global security weakening or changes to normal Zen.
Source: phase2 C; current packaging inspector; Sept 7 user autonomy. Enforced by C10, tested by B10.

### R11
Test the actual installed test app, not only file contents or mocked tests. Use isolated profiles and disposable sessions.
Source: test plan proof levels; Sept 7 request to test everything. Enforced by C11, tested by B11.

### R12
Keep original product scope. No Core integration, agent decision engine, isolated agent accounts, recipe recording, auto labelling, or forced remote permission bypass.
Source: step-one deferred scope; standalone project. Enforced by C12, tested by B12.

## Remaining founder decisions
None needed to harden the agreed Mac development app. Public release signing/notarization requires an Apple Developer identity and is not assumed. Security freshness of the inherited Firefox version must be reported; passing terminal tests does not certify an old browser engine safe for general browsing.

## R13 — direct founder extension, September 7
The founder explicitly requests all existing Zen logins, profiles and metadata copied to their own installation. The general app remains blank. Personal experience should match ordinary Zen with working terminal tabs added. This is a supplied requirement, not a fabricated interview answer.

Implementation boundary: copy full profile data into an isolated app root, retain source and profile names, exclude only rebuildable caches/locks. Do not export credentials, print secrets, commit personal data, share live profile directories, or disable profile downgrade protection. Source Zen is currently running: final consistent copying waits for it to close; do not interrupt it silently. The terminal build must be at least compatible with the source Firefox engine.
