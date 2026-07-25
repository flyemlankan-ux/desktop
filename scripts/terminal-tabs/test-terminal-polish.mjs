#!/usr/bin/env node
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const read = (path) => readFileSync(path, "utf8");
const page = read("src/zen/terminal/ZenTerminalPage.mjs");
const managerSource = read("src/zen/terminal/ZenTerminalSessionManager.mjs");
const markup = read("src/zen/terminal/terminal.xhtml");
const css = read("src/zen/terminal/zen-terminal-page.css");
const jar = read("src/zen/terminal/jar.inc.mn");

assert.match(page, /new ResizeObserver\(scheduleTerminalFit\)/);
assert.match(page, /fitAddon\.proposeDimensions\(\)/);
assert.doesNotMatch(page, /characterWidth|characterHeight/);
assert.match(page, /terminal\.write\(chunk, resolve\)/);
assert.match(page, /smoothScrollDuration: 80/);
assert.match(page, /resizeTerminalTmuxSession\(/);
assert.match(page, /\.\.\.MACOS_SUBPROCESS_OPTIONS/);
assert.match(managerSource, /disclaim: true/);

assert.match(markup, /vendor\/xterm\.js[\s\S]*vendor\/addon-fit\.js/);
assert.match(jar, /vendor\/addon-fit\.js/);
assert.match(css, /#zen-terminal-output \.xterm \{[\s\S]*height: 100%/);
assert.match(css, /#zen-terminal-surface \{[\s\S]*height: 100%/);
assert.doesNotMatch(css, /padding: 18px|calc\(100vh - 36px\)/);

function sha256(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

// xterm 6.0.0 and addon-fit 0.11.0 were published from the exact same
// upstream commit (f447274f430fd22513f6adbf9862d19524471c04).
assert.equal(
  sha256("src/zen/terminal/vendor/xterm.js"),
  "14903579ff54664cd72f8e8699e6961a6272c21863ec1c3b118cdc8af5d4a972",
);
assert.equal(
  sha256("src/zen/terminal/vendor/addon-fit.js"),
  "ba3ea256ce0620a0992a197d6c9baea64823fc93d8da07a9e366ca9943c18527",
);

const subprocessCalls = [];
const prefValues = new Map();
globalThis.Services = {
  appinfo: { OS: "Darwin" },
  prefs: {
    getStringPref(name, fallback = "") {
      return prefValues.get(name) ?? fallback;
    },
    setStringPref(name, value) {
      prefValues.set(name, value);
    },
  },
};
globalThis.ChromeUtils = {
  importESModule() {
    return {
      Subprocess: {
        async call(options) {
          subprocessCalls.push(options);
          return {
            stdout: {
              async readString() {
                return "";
              },
            },
            async wait() {
              return { exitCode: 0 };
            },
          };
        },
      },
    };
  },
};

const manager =
  await import("../../src/zen/terminal/ZenTerminalSessionManager.mjs");
const resized = await manager.resizeTerminalTmuxSession(
  "/opt/homebrew/bin/tmux",
  "11111111-1111-4111-8111-111111111111",
  { rows: 31, columns: 101 },
);
assert.equal(resized, true);
assert.equal(subprocessCalls.length, 1);
assert.equal(subprocessCalls[0].disclaim, true);
assert.deepEqual(subprocessCalls[0].arguments, [
  "-L",
  "zen-terminal",
  "resize-window",
  "-t",
  "=zt_11111111-1111-4111-8111-111111111111",
  "-x",
  "101",
  "-y",
  "31",
]);

console.log("Terminal polish tests passed.");
