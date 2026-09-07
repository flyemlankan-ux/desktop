#!/usr/bin/env node
/* MPL-2.0: wiring checks supplement, never replace, real app tests. */
import assert from "node:assert/strict";
import { readFileSync, existsSync, readdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
const read = (path) => readFileSync(path, "utf8");
const has = (path, text) =>
  assert.ok(read(path).includes(text), `${path}: missing ${text}`);
const no = (path, text) =>
  assert.ok(!read(path).includes(text), `${path}: obsolete ${text}`);
const dir = "src/zen/terminal/";
for (const file of readdirSync(dir).filter((name) => name.endsWith(".mjs"))) {
  assert.equal(
    spawnSync(process.execPath, ["--check", dir + file], { stdio: "inherit" })
      .status,
    0,
  );
}
for (const [path, text] of [
  ["src/zen/moz.build", '"terminal"'],
  [
    "src/browser/base/content/zen-assets.jar.inc.mn",
    "../../../zen/terminal/jar.inc.mn",
  ],
  ["src/zen/common/ZenPreloadedScripts.js", "ZenTerminalTabs.mjs"],
  [dir + "jar.inc.mn", "ZenTerminalSessionManager.mjs"],
  [dir + "jar.inc.mn", "ZenTerminalRecipeRunner.mjs"],
  [dir + "jar.inc.mn", "vendor/addon-fit.js"],
  [dir + "ZenTerminalPage.mjs", "zen-terminal-pty"],
  [dir + "ZenTerminalPage.mjs", "prepareTerminalTmuxSession"],
  [dir + "ZenTerminalTabs.mjs", "destroyTerminalSession"],
  [dir + "ZenTerminalTabs.mjs", "RunState.isQuitting"],
  [dir + "ZenTerminalTabs.mjs", "preserveExistingLabel"],
  [
    "src/browser/base/content/zen-panels/popups.inc",
    "gZenTerminalTabs.populateUnifiedContainerMenu(event)",
  ],
  [
    "src/browser/components/preferences/containers-js.patch",
    "destroyTerminalSessionsForUserContextId",
  ],
  [
    "src/browser/components/preferences/dialogs/containers-js.patch",
    "compileTerminalRecipeSteps",
  ],
  [
    "src/browser/components/preferences/dialogs/containers-js.patch",
    "Stop this container's terminals?",
  ],
  [".github/workflows/terminal-macos-dev-build.yml", "--disable-updater"],
])
  has(path, text);
for (const file of [
  "ZenTerminalContainers.mjs",
  "containers.xhtml",
  "zen-terminal-containers.css",
])
  assert.equal(existsSync(dir + file), false);
assert.equal(
  existsSync("scripts/terminal-tabs/patch-engine-newtab-menu.mjs"),
  false,
);
no(dir + "ZenTerminalPage.mjs", "shouldDropDuplicateInput");
no(dir + "ZenTerminalPage.mjs", "PYTHON_PTY_BRIDGE");
no("src/browser/base/content/zen-panels/popups.inc", 'label="Terminal Tab"');
console.log(
  "Terminal wiring and syntax checks passed (not a real-app acceptance test).",
);
