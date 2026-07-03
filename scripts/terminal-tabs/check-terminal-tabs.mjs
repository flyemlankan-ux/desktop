#!/usr/bin/env node
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { readFileSync } from "node:fs";
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
  [
    "terminal command handled",
    ["src/zen/common/zen-sets.js", "gZenTerminalTabs.openTerminalTab"],
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
    "terminal dialog has start folder field",
    [
      "src/browser/components/preferences/dialogs/containers-js.patch",
      "zen-terminal-folder",
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
    ["src/zen/terminal/ZenTerminalTabs.mjs", "#routeNativeTerminalContainerRows"],
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
    "terminal page cd's into start folder",
    ["src/zen/terminal/ZenTerminalPage.mjs", "cd ${shellQuote(folder)}"],
  ],
  [
    "terminal page runs startup recipe",
    ["src/zen/terminal/ZenTerminalPage.mjs", "Running startup recipe"],
  ],
  [
    "folder path is shell quoted",
    ["src/zen/terminal/ZenTerminalPage.mjs", "function shellQuote"],
  ],

  // Old fallback path must stay during this slice.
  [
    "plain terminal tab choice still present as fallback",
    ["src/browser/base/content/zen-panels/popups.inc", "Terminal Tab"],
  ],
  [
    "old terminal container choice still present as fallback",
    [
      "src/browser/base/content/zen-panels/popups.inc",
      "Terminal Container Tab",
    ],
  ],
  [
    "old fallback terminal containers pref still present",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "zen.terminal.containers"],
  ],
  [
    "old fallback terminal containers page still jarred",
    ["src/zen/terminal/jar.inc.mn", "containers.xhtml"],
  ],
  [
    "old fallback manage page still saves containers",
    ["src/zen/terminal/ZenTerminalContainers.mjs", "zen.terminal.containers"],
  ],
  [
    "old fallback manage page still opens",
    ["src/zen/terminal/ZenTerminalTabs.mjs", "openTerminalContainersPage"],
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
    "shell writes input",
    ["src/zen/terminal/ZenTerminalPage.mjs", "shellProcess.stdin.write"],
  ],
  [
    "shell reads stdout",
    ["src/zen/terminal/ZenTerminalPage.mjs", "shellProcess.stdout"],
  ],
  [
    "shell output written to xterm",
    ["src/zen/terminal/ZenTerminalPage.mjs", "terminal.write(chunk)"],
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

const syntaxFiles = [
  "src/zen/terminal/ZenTerminalContainerStore.mjs",
  "src/zen/terminal/ZenTerminalTabs.mjs",
  "src/zen/terminal/ZenTerminalPage.mjs",
  "src/zen/common/ZenPreloadedScripts.js",
  "src/zen/common/zen-sets.js",
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
for (const [name, [file, needle]] of checks) {
  const text = readFileSync(file, "utf8");
  if (!text.includes(needle)) {
    failed.push(`${name}: missing ${needle} in ${file}`);
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
