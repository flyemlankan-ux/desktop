#!/usr/bin/env node
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import vm from "node:vm";

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
  importESModule(name) {
    if (name.endsWith("/Timer.sys.mjs")) return { setTimeout, clearTimeout };
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
  "-f",
  "/dev/null",
  "resize-window",
  "-t",
  "=zt_11111111-1111-4111-8111-111111111111",
  "-x",
  "101",
  "-y",
  "31",
]);

for (const dimensions of [
  { rows: 0, columns: 80 },
  { rows: 24, columns: 1 },
  { rows: 1001, columns: 80 },
  { rows: 24, columns: 1001 },
  { rows: 2.5, columns: 80 },
  { rows: NaN, columns: 80 },
]) {
  assert.equal(
    await manager.resizeTerminalTmuxSession("/mock/tmux", "test", dimensions),
    false,
  );
}
assert.equal(
  subprocessCalls.length,
  1,
  "invalid dimensions must never invoke a process",
);

// Execute the actual page functions in a small fake page, rather than just
// searching source text. No browser or shell is opened by these checks.
const written = [];
const statuses = [];
let helperExists = true;
const helper = {
  path: "/Applications/Zen Terminal.app/Contents/MacOS",
  append(name) {
    this.path += `/${name}`;
  },
  exists() {
    return helperExists;
  },
};
const context = vm.createContext({
  Services: {
    appinfo: { OS: "Darwin" },
    env: { get: () => "/bin/zsh" },
    dirsvc: { get: () => ({ parent: { ...helper } }) },
  },
  Ci: { nsIFile: {} },
  terminal: { rows: 24, cols: 80 },
  getTerminalTmuxSessionName: manager.getTerminalTmuxSessionName,
  terminalShellScript: manager.terminalShellScript,
  ZEN_TERMINAL_TMUX_SOCKET: manager.ZEN_TERMINAL_TMUX_SOCKET,
  TextEncoder,
  shellReady: true,
  stopping: false,
  queuedInputBytes: 0,
  pendingHighSurrogate: "",
  inputQueue: Promise.resolve(),
  activeShellLaunch: { resizable: true },
  shellProcess: {
    stdin: {
      async write(frame) {
        written.push(frame);
      },
    },
  },
  setStatus: (text) => statuses.push(text),
});
const section = (start, end) =>
  page.slice(page.indexOf(start), page.indexOf(end));
vm.runInContext(
  section("function getShellCommand()", "function fitTerminalToSurface()"),
  context,
);
vm.runInContext(
  section("function writeFrame(", "surface.addEventListener("),
  context,
);
vm.runInContext(
  section(
    "function queueTerminalResize(",
    "async function flushTmuxResizeQueue(",
  ),
  context,
);
const launch = vm.runInContext(
  'getShellLaunch({ tmuxCommand: "/opt/homebrew/bin/tmux", sessionId: "test" })',
  context,
);
assert.equal(
  launch.command,
  "/Applications/Zen Terminal.app/Contents/MacOS/zen-terminal-pty",
);
assert.deepEqual(Array.from(launch.arguments), [
  "--rows",
  "24",
  "--cols",
  "80",
  "--",
  "/opt/homebrew/bin/tmux",
  "-L",
  "zen-terminal",
  "-f",
  "/dev/null",
  "attach-session",
  "-t",
  "=zt_test",
]);
assert.equal(launch.resizable, true);
helperExists = false;
assert.throws(
  () => vm.runInContext("getShellLaunch()", context),
  /helper is missing/,
);
helperExists = true;
const fallback = vm.runInContext(
  'getShellLaunch({ startupCommand: "printf safe" })',
  context,
);
assert.equal(fallback.persistent, false);
assert.ok(fallback.arguments.includes("-lic"));
assert.ok(fallback.arguments.some((arg) => arg.includes("printf safe")));

await vm.runInContext(
  'writeToShell("a"); writeToShell("a"); inputQueue',
  context,
);
assert.deepEqual(
  written.splice(0),
  ["I1\na", "I1\na"],
  "rapid equal keystrokes are not discarded",
);
await vm.runInContext('writeToShell("😀é")', context);
assert.deepEqual(
  written.splice(0),
  ["I6\n😀é"],
  "length is UTF-8 bytes, not JavaScript characters",
);
vm.runInContext("queueTerminalResize(31, 101)", context);
await context.inputQueue;
assert.deepEqual(
  written.splice(0),
  ["R31 101\n"],
  "resize is a separate helper frame, never shell text",
);
await vm.runInContext('writeToShell("x".repeat(4 * 1024 * 1024 + 1))', context);
assert.equal(written.length, 0, "oversized paste is rejected whole");
assert.match(statuses.at(-1), /paste too large/);
const beforeSplitPair = written.length;
await vm.runInContext(
  'writeToShell("\\ud83d"); writeToShell("\\ude00"); inputQueue',
  context,
);
assert.equal(written.length, beforeSplitPair + 1);
assert.equal(written.pop(), "I4\n😀");

context.stopping = true;
await vm.runInContext('writeToShell("must not reach a closed shell")', context);
assert.equal(written.length, 0);
console.log(
  "Terminal polish tests passed: vendor integrity, native helper launch, resize, Unicode input, repeated keys and whole-paste limits.",
);
