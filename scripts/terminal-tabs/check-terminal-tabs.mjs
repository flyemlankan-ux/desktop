#!/usr/bin/env node
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";

const checks = new Map([
  ["terminal dir registered", ["src/zen/moz.build", '"terminal"']],
  [
    "terminal jar included",
    [
      "src/browser/base/content/zen-assets.jar.inc.mn",
      "../../../zen/terminal/jar.inc.mn",
    ],
  ],
  [
    "terminal module preloaded",
    ["src/zen/common/ZenPreloadedScripts.js", "ZenTerminalTabs.mjs"],
  ],
  // New Slice 1 native-container path.
  [
    "native terminal metadata store added",
    [
      "src/zen/terminal/ZenTerminalContainerStore.mjs",
      "zen.terminal.containerRecipes",
    ],
  ],
  [
    "store records real container kind",
    ["src/zen/terminal/ZenTerminalContainerStore.mjs", 'kind: "terminal"'],
  ],
  [
    "store keeps future recipe steps without a schema change",
    ["src/zen/terminal/ZenTerminalContainerStore.mjs", "steps"],
  ],
  [
    "metadata store jarred",
    ["src/zen/terminal/jar.inc.mn", "ZenTerminalContainerStore.mjs"],
  ],
  [
    "persistent terminal session manager added",
    ["src/zen/terminal/ZenTerminalSessionManager.mjs", "zen.terminal.sessions"],
  ],
  [
    "persistent session manager jarred",
    ["src/zen/terminal/jar.inc.mn", "ZenTerminalSessionManager.mjs"],
  ],
  [
    "container deletion destroys its persistent sessions",
    [
      "src/browser/components/preferences/containers-js.patch",
      "destroyTerminalSessionsForUserContextId(userContextId)",
    ],
  ],
  [
    "terminal to web change destroys its persistent sessions",
    [
      "src/browser/components/preferences/dialogs/containers-js.patch",
      "destroyTerminalSessionsForUserContextId(userContextId)",
    ],
  ],
  [
    "terminal tabs receive stable session ids",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "terminalSessionId"],
  ],
  [
    "explicit tab close destroys its persistent session",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "destroyTerminalSession"],
  ],
  [
    "page reattaches through dedicated tmux server",
    ["src/zen/terminal/ZenTerminalPage.mjs", "ZEN_TERMINAL_TMUX_SOCKET"],
  ],
  [
    "startup command is skipped on tmux reattach",
    ["src/zen/terminal/ZenTerminalPage.mjs", "tmuxSessionWasNew"],
  ],
  [
    "preferences container list knows terminal metadata",
    [
      "src/browser/components/preferences/containers-js.patch",
      "zen.terminal.containerRecipes",
    ],
  ],
  [
    "preferences delete removes terminal recipe",
    [
      "src/browser/components/preferences/containers-js.patch",
      "removeZenTerminalContainerRecipe(userContextId)",
    ],
  ],
  [
    "add container dialog asks web or terminal",
    [
      "src/browser/components/preferences/dialogs/containers-js.patch",
      "What kind of container is this?",
    ],
  ],
  [
    "terminal dialog has startup recipe field",
    [
      "src/browser/components/preferences/dialogs/containers-js.patch",
      "zen-terminal-recipe",
    ],
  ],
  [
    "new native container writes terminal recipe by userContextId",
    [
      "src/browser/components/preferences/dialogs/containers-js.patch",
      "setZenTerminalContainerRecipe(",
    ],
  ],
  [
    "switching back to web removes terminal recipe",
    [
      "src/browser/components/preferences/dialogs/containers-js.patch",
      "removeZenTerminalContainerRecipe(userContextId)",
    ],
  ],
  [
    "native menu rows route terminal containers",
    [
      "src/zen/terminal/ZenTerminalTabs.mjs",
      "#routeNativeTerminalContainerRows",
    ],
  ],
  [
    "one native menu populates mixed web and terminal containers",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "populateUnifiedContainerMenu"],
  ],
  [
    "unified container menu omits duplicate plain browser row",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "showDefaultTab: false"],
  ],
  [
    "create menu uses the unified native container list",
    [
      "src/browser/base/content/zen-panels/popups.inc",
      "gZenTerminalTabs.populateUnifiedContainerMenu(event)",
    ],
  ],
  [
    "terminal container row does not keep browser command",
    ["src/zen/terminal/ZenTerminalTabs.mjs", 'item.removeAttribute("command")'],
  ],
  [
    "terminal container row stops blank browser tab",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "stopImmediatePropagation"],
  ],
  [
    "native terminal tab passes userContextId",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "openTerminalContainerTab"],
  ],
  [
    "restored terminal tabs are re-marked",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "#markRestoredTerminalTabs"],
  ],
  [
    "terminal page reads native container recipe",
    ["src/zen/terminal/ZenTerminalPage.mjs", "getTerminalContainerRecipe"],
  ],
  [
    "terminal page starts in home by default",
    ["src/zen/terminal/ZenTerminalPage.mjs", "getHomeDirectory"],
  ],
  [
    "terminal page runs startup recipe silently",
    ["src/zen/terminal/ZenTerminalPage.mjs", "runStartupCommands"],
  ],
  [
    "known-good script launcher is default again",
    [
      "src/zen/terminal/ZenTerminalPage.mjs",
      "macOS script pseudo-terminal with initial size",
    ],
  ],
  [
    "script launcher sets initial terminal size for full-screen apps",
    ["src/zen/terminal/ZenTerminalPage.mjs", "stty rows"],
  ],
  [
    "experimental Python PTY is not default",
    [
      "src/zen/terminal/ZenTerminalPage.mjs",
      "zen.terminal.experimentalPythonPtyBridge",
    ],
  ],
  [
    "terminal disables macOS restored-session noise",
    ["src/zen/terminal/ZenTerminalPage.mjs", "SHELL_SESSIONS_DISABLE"],
  ],
  [
    "folder is now part of recipe text not separate storage",
    [
      "src/browser/components/preferences/dialogs/containers-js.patch",
      "cd ~/projects/app && claude",
    ],
  ],
  [
    "terminal tabs force normal Zen tabs",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "#forceNormalZenTab"],
  ],
  [
    "terminal tabs repeat normal-tab cleanup after Zen pin events",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "#forceNormalZenTabSoon"],
  ],
  [
    "terminal tab labels are stored as Zen static labels",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "tab.zenStaticLabel = label"],
  ],
  [
    "restored terminal tabs preserve user rename",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "preserveExistingLabel"],
  ],
  [
    "terminal rename commits on blur",
    ["src/zen/common/modules/ZenUIManager.mjs", "shouldSaveTerminalRename"],
  ],

  // Core terminal proof from Slice 0 must remain true.
  [
    "terminal tab opens chrome page",
    [
      "src/zen/terminal/ZenTerminalTabs.mjs",
      "chrome://browser/content/zen-terminal/terminal.xhtml",
    ],
  ],
  [
    "terminal page jarred",
    [
      "src/zen/terminal/jar.inc.mn",
      "content/browser/zen-terminal/terminal.xhtml",
    ],
  ],
  [
    "terminal page script jarred",
    ["src/zen/terminal/jar.inc.mn", "ZenTerminalPage.mjs"],
  ],
  [
    "terminal page css jarred",
    ["src/zen/terminal/jar.inc.mn", "zen-terminal-page.css"],
  ],
  [
    "subprocess shell wired",
    ["src/zen/terminal/ZenTerminalPage.mjs", "Subprocess.call"],
  ],
  [
    "mac pseudo-terminal helper wired",
    ["src/zen/terminal/ZenTerminalPage.mjs", "/usr/bin/script"],
  ],
  [
    "real terminal engine vendored",
    ["src/zen/terminal/vendor/xterm.js", "Terminal"],
  ],
  [
    "real terminal css vendored",
    ["src/zen/terminal/vendor/xterm.css", ".xterm"],
  ],
  [
    "terminal page loads xterm",
    ["src/zen/terminal/terminal.xhtml", "vendor/xterm.js"],
  ],
  [
    "terminal input handled by xterm",
    ["src/zen/terminal/ZenTerminalPage.mjs", "terminal.onData"],
  ],
  [
    "terminal input handler is singleton guarded",
    ["src/zen/terminal/ZenTerminalPage.mjs", "window.__zenTerminalPageState"],
  ],
  [
    "terminal duplicate input events are dropped before stdin",
    ["src/zen/terminal/ZenTerminalPage.mjs", "shouldDropDuplicateInput"],
  ],
  [
    "shell writes input",
    ["src/zen/terminal/ZenTerminalPage.mjs", "shellProcess.stdin.write"],
  ],
  [
    "shell reads stdout",
    ["src/zen/terminal/ZenTerminalPage.mjs", "shellProcess.stdout"],
  ],
  [
    "shell output written to xterm",
    ["src/zen/terminal/ZenTerminalPage.mjs", "terminal.write(chunk, resolve)"],
  ],
  [
    "shell closes on tab close",
    ["src/zen/terminal/ZenTerminalPage.mjs", "pagehide"],
  ],

  // Build wiring must still exist.
  [
    "manual mac workflow added",
    [
      ".github/workflows/terminal-macos-dev-build.yml",
      "Terminal macOS Dev Build",
    ],
  ],
  [
    "terminal fork identity patched",
    [".github/workflows/terminal-macos-dev-build.yml", "zen-terminal"],
  ],
]);

const forbidden = new Map([
  [
    "old terminal-only menu item removed",
    ["src/browser/base/content/zen-panels/popups.inc", 'label="Terminal Tab"'],
  ],
  [
    "old terminal-container submenu removed",
    [
      "src/browser/base/content/zen-panels/popups.inc",
      'label="Terminal Container Tab"',
    ],
  ],
  [
    "old default terminal menu row removed",
    ["src/browser/base/content/zen-panels/popups.inc", "Default Terminal"],
  ],
  [
    "old terminal commands removed",
    ["src/browser/base/content/zen-commands.inc.xhtml", "cmd_zenNewTerminal"],
  ],
  [
    "old terminal command handlers removed",
    ["src/zen/common/zen-sets.js", "cmd_zenNewTerminal"],
  ],
  [
    "old synthetic container preference removed",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "zen.terminal.containers"],
  ],
  [
    "old terminal menu injection removed",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "injectTerminalChoices"],
  ],
  [
    "old terminal manage page opener removed",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "openTerminalContainersPage"],
  ],
  [
    "old standalone page removed from jar",
    ["src/zen/terminal/jar.inc.mn", "containers.xhtml"],
  ],
  [
    "cloud build no longer patches a second terminal menu",
    [
      ".github/workflows/terminal-macos-dev-build.yml",
      "patch-engine-newtab-menu",
    ],
  ],
  [
    "separate start folder field removed from dialog",
    [
      "src/browser/components/preferences/dialogs/containers-js.patch",
      "zen-terminal-folder",
    ],
  ],
  [
    "separate folder removed from store writes",
    ["src/zen/terminal/ZenTerminalContainerStore.mjs", "folder:"],
  ],
  [
    "container list terminal badge removed to avoid TerminalTerminal",
    [
      "src/browser/components/preferences/containers-js.patch",
      "zen-terminal-container-badge",
    ],
  ],
]);

const syntaxFiles = [
  "src/zen/terminal/ZenTerminalContainerStore.mjs",
  "src/zen/terminal/ZenTerminalRecipeRunner.mjs",
  "src/zen/terminal/ZenTerminalSessionManager.mjs",
  "src/zen/terminal/ZenTerminalTabs.mjs",
  "src/zen/terminal/ZenTerminalPage.mjs",
  "src/zen/common/ZenPreloadedScripts.js",
  "src/zen/common/zen-sets.js",
  "src/zen/common/modules/ZenUIManager.mjs",
];

const removedFiles = [
  "src/zen/terminal/ZenTerminalContainers.mjs",
  "src/zen/terminal/containers.xhtml",
  "src/zen/terminal/zen-terminal-containers.css",
  "scripts/terminal-tabs/patch-engine-newtab-menu.mjs",
];

for (const file of syntaxFiles) {
  const result = spawnSync(process.execPath, ["--check", file], {
    stdio: "inherit",
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

const failed = [];
for (const file of removedFiles) {
  if (existsSync(file)) {
    failed.push(`old standalone terminal file still exists: ${file}`);
  }
}
for (const [name, [file, needle]] of checks) {
  const text = readFileSync(file, "utf8");
  if (!text.includes(needle)) {
    failed.push(`${name}: missing ${needle} in ${file}`);
  }
}

for (const [name, [file, needle]] of forbidden) {
  const text = readFileSync(file, "utf8");
  if (text.includes(needle)) {
    failed.push(`${name}: still contains ${needle} in ${file}`);
  }
}

if (failed.length) {
  console.error("Terminal tabs proof failed:");
  for (const failure of failed) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log("Terminal tabs proof passed.");
