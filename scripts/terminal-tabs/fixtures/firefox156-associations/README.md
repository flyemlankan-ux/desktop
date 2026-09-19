# Firefox156 website association boundary

Pristine files from mozilla-firefox/firefox tag FIREFOX_156_0_RELEASE, fetched via
GitHub contents API and checked against Git blob SHA1. receipt.json pins blob ids and
SHA256. test-terminal-associations156.mjs verifies both and applies production
patches with --fuzz=0 in a temporary folder.

Confirmed callers at this version:
- preferences/config/containers.mjs: site association list uses containerOptions;
  Add Site button now uses it too so terminal-only profiles cannot open an empty
  website-container picker. Main container manager deliberately still shows ALL
  saved setups, preserving the one shared manager requirement.
- preferences/dialogs/siteContainer.js: builds options via containerOptions, directly
  commits site association on dialog accept; now revalidates exact existing web id.
- contextualidentity/content/container-select.mjs: shared options + direct site
  binding on change. Filters terminal identities and revalidates stale selection.

GitHub code search was used only to discover caller candidates; those three actual
files were independently fetched at the pinned release. No broad claim that remote
search latest branch establishes all156 runtime entrypoint behavior.

Patch targets and actual browser/omni.ja paths:
- container-select.mjs -> chrome/browser/content/browser/usercontext/container-select.mjs
- siteContainer.js -> chrome/browser/content/browser/preferences/dialogs/siteContainer.js
- config/containers.mjs -> chrome/browser/content/browser/preferences/config/containers.mjs

21 synthetic real-source cases pass: web metadata unchanged, terminal-only list empty,
exact id parsing, missing/changed kind rejected at commit, visible invalid selection,
normal HTTPS site accepted, native Add Site disabled when no web identities remain.
12 settings156 editor cases remain passing. No UI was run for this slice; actual
association dialog and stale-setup journey still need parent-controlled native proof.
English fallback error wording is consistent with existing terminal controls, not
claimed complete localization. Terminal-only records must not be silently replaced
with a different cookie container.

No Firefox155 compatibility claim: these are new156 files/features; old155 fixtures
were not relabelled or modified. Updated config patch includes156-only Add Site code.

Additional read-only module audit against official1.22.2b app resources confirmed:
- root omni modules/Subprocess.sys.mjs, Timer.sys.mjs, PrivateBrowsingUtils.sys.mjs
- root omni moz-src/browser/components/sessionstore/RunState.sys.mjs
- root omni moz-src/toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs
- browser omni modules/BrowserWindowTracker.sys.mjs
All match currently referenced terminal module import URLs after parent's RunState fix.
