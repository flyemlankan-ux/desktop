#!/usr/bin/env node
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
import assert from "node:assert/strict";
const prefs = new Map();
let writes = 0;
globalThis.Services = {
  prefs: {
    getStringPref: (key, fallback) => prefs.get(key) ?? fallback,
    setStringPref: (key, value) => { writes++; prefs.set(key, value); },
  },
};
globalThis.ChromeUtils = {
  importESModule() { throw new Error("Ownership validation must not start a tool"); },
};
const manager = await import("../../src/zen/terminal/ZenTerminalSessionManager.mjs");
const tests = [];
const test = (name, run) => tests.push([name, run]);

test("same setup may register another view without changing creation time", () => {
  const first = manager.registerTerminalSession("shared", {userContextId: "10"});
  const next = manager.registerTerminalSession("shared", {userContextId: 10});
  assert.equal(next.userContextId, "10");
  assert.equal(next.createdAt, first.createdAt);
});
test("different setup is refused before any preference write", () => {
  manager.registerTerminalSession("shared", {userContextId: "10"});
  const before = prefs.get(manager.ZEN_TERMINAL_SESSIONS_PREF);
  const count = writes;
  assert.equal(manager.registerTerminalSession("shared", {userContextId: "20"}), null);
  assert.equal(writes, count);
  assert.equal(prefs.get(manager.ZEN_TERMINAL_SESSIONS_PREF), before);
  assert.equal(manager.listTerminalSessionsForUserContextId("10").length, 1);
  assert.equal(manager.listTerminalSessionsForUserContextId("20").length, 0);
});
test("omitted owner preserves existing owner rather than clearing it", () => {
  manager.registerTerminalSession("shared", {userContextId: "10"});
  assert.equal(manager.registerTerminalSession("shared").userContextId, "10");
});
test("legacy container owner cannot be reassigned", () => {
  manager.registerTerminalSession("legacy", {terminalContainerId: "old"});
  const before = prefs.get(manager.ZEN_TERMINAL_SESSIONS_PREF);
  assert.equal(manager.registerTerminalSession("legacy", {terminalContainerId: "other"}), null);
  assert.equal(prefs.get(manager.ZEN_TERMINAL_SESSIONS_PREF), before);
});
test("an existing ownerless record cannot be silently claimed by another setup", () => {
  manager.registerTerminalSession("unowned");
  assert.equal(manager.registerTerminalSession("unowned", {userContextId: "20"}), null);
  assert.equal(manager.getTerminalSessionRecord("unowned").userContextId, "");
});
test("pending deletion cannot be cancelled by same-owner registration", () => {
  manager.registerTerminalSession("closing", {userContextId: "10"});
  const records = manager.readTerminalSessionRecords();
  records.closing.pendingDelete = true;
  manager.writeTerminalSessionRecords(records);
  const before = prefs.get(manager.ZEN_TERMINAL_SESSIONS_PREF);
  assert.equal(manager.registerTerminalSession("closing", {userContextId: "10"}), null);
  assert.equal(prefs.get(manager.ZEN_TERMINAL_SESSIONS_PREF), before);
});
for (const [name, run] of tests) {
  prefs.clear(); writes = 0;
  run(); console.log(`✓ ${name}`);
}
console.log(`${tests.length} terminal ownership tests passed; no subprocesses or browser profiles used.`);
