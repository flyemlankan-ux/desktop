#!/usr/bin/env node
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";

const checks = new Map([
  ["terminal dir registered", ["src/zen/moz.build", '"terminal"']],
  ["terminal jar included", ["src/browser/base/content/zen-assets.jar.inc.mn", "../../../zen/terminal/jar.inc.mn"]],
  ["terminal command declared", ["src/browser/base/content/zen-commands.inc.xhtml", "cmd_zenNewTerminalTab"]],
  ["terminal menu item present", ["src/browser/base/content/zen-panels/popups.inc", "New Terminal Tab"]],
  ["terminal module preloaded", ["src/zen/common/ZenPreloadedScripts.js", "ZenTerminalTabs.mjs"]],
  ["terminal command handled", ["src/zen/common/zen-sets.js", "gZenTerminalTabs.openTerminalTab"]],
  ["terminal tab opens chrome page", ["src/zen/terminal/ZenTerminalTabs.mjs", "chrome://browser/content/zen-terminal/terminal.xhtml"]],
  ["terminal page jarred", ["src/zen/terminal/jar.inc.mn", "content/browser/zen-terminal/terminal.xhtml"]],
  ["terminal page script jarred", ["src/zen/terminal/jar.inc.mn", "ZenTerminalPage.mjs"]],
  ["terminal page css jarred", ["src/zen/terminal/jar.inc.mn", "zen-terminal-page.css"]],
  ["subprocess shell wired", ["src/zen/terminal/ZenTerminalPage.mjs", "Subprocess.call"]],
  ["mac pseudo-terminal helper wired", ["src/zen/terminal/ZenTerminalPage.mjs", "/usr/bin/script"]],
  ["raw key handling wired", ["src/zen/terminal/ZenTerminalPage.mjs", "terminalSequenceFor"]],
  ["paste handling wired", ["src/zen/terminal/ZenTerminalPage.mjs", "paste"]],
  ["shell writes input", ["src/zen/terminal/ZenTerminalPage.mjs", "shellProcess.stdin.write"]],
  ["shell reads stdout", ["src/zen/terminal/ZenTerminalPage.mjs", "shellProcess.stdout"]],
  ["output cleaner used", ["src/zen/terminal/ZenTerminalPage.mjs", "const cleaned = cleanTerminalText(text);"]],
  ["shell closes on tab close", ["src/zen/terminal/ZenTerminalPage.mjs", "pagehide"]],
  ["manual mac workflow added", [".github/workflows/terminal-macos-dev-build.yml", "Terminal macOS Dev Build"]],
  ["build note updated", ["docs/terminal-tabs-build.md", "sends keystrokes directly"]],
]);

const syntaxFiles = [
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
