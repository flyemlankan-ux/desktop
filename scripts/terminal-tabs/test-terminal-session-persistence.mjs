#!/usr/bin/env node
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";

const prefValues = new Map();
globalThis.Services = {
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
        async call() {
          return {
            stdout: {
              async readString() {
                return "";
              },
            },
            async wait() {
              return { exitCode: 1 };
            },
          };
        },
      },
    };
  },
};

const manager =
  await import("../../src/zen/terminal/ZenTerminalSessionManager.mjs");

const sessionA = "11111111-1111-4111-8111-111111111111";
const sessionB = "22222222-2222-4222-8222-222222222222";

assert.equal(
  manager.normalizeTerminalSessionId(` ${sessionA.toUpperCase()} `),
  sessionA,
);
assert.equal(manager.normalizeTerminalSessionId("../../unsafe"), "");
assert.equal(manager.getTerminalTmuxSessionName(sessionA), `zt_${sessionA}`);

manager.registerTerminalSession(sessionA, { userContextId: "7" });
manager.registerTerminalSession(sessionB, { userContextId: "8" });
manager.registerTerminalSession(sessionA, { userContextId: "7" });

assert.equal(manager.listTerminalSessionsForUserContextId("7").length, 1);
assert.equal(manager.listTerminalSessionsForUserContextId("8").length, 1);
assert.equal(manager.getTerminalSessionRecord(sessionA).pendingDelete, false);

assert.equal(
  await manager.destroyTerminalSession(sessionA),
  false,
  "a missing tmux command must leave cleanup queued for retry",
);
assert.equal(manager.getTerminalSessionRecord(sessionA).pendingDelete, true);
manager.registerTerminalSession(sessionA, { userContextId: "7" });
assert.equal(manager.getTerminalSessionRecord(sessionA).pendingDelete, false);

function findTmuxForLocalTest() {
  for (const command of [
    "/opt/homebrew/bin/tmux",
    "/usr/local/bin/tmux",
    "tmux",
  ]) {
    const result = spawnSync(command, ["-V"], { encoding: "utf8" });
    if (result.status === 0) {
      return command;
    }
  }
  return "";
}

async function runRealTmuxDetachTest() {
  const tmuxCommand = findTmuxForLocalTest();
  if (!tmuxCommand || process.platform !== "darwin") {
    console.log("Real tmux detach test skipped: macOS tmux was not found.");
    return;
  }

  // macOS /usr/bin/script needs ordinary POSIX pipes. Node implements child
  // pipes with sockets on macOS, so this Python harness supplies the same pipe
  // shape Firefox Subprocess uses.
  const pythonTest = String.raw`
import os
import subprocess
import sys
import time

tmux = sys.argv[1]
socket = "zen-terminal-test-" + str(os.getpid())
session = "zt_test_" + str(os.getpid())
environment = os.environ.copy()
environment["TERM"] = "xterm-256color"
command = [
    "/usr/bin/script", "-q", "/dev/null", "/bin/zsh", "-lc",
    "export TERM=xterm-256color; exec '{}' -L '{}' new-session -A -s '{}'".format(
        tmux, socket, session
    )
]
viewers = []

def call(*arguments):
    return subprocess.run(
        [tmux, "-L", socket, *arguments],
        capture_output=True,
        text=True,
    )

def wait_for(check, description):
    deadline = time.time() + 5
    while time.time() < deadline:
        value = check()
        if value:
            return value
        time.sleep(0.05)
    raise RuntimeError("Timed out waiting for " + description)

try:
    first = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )
    viewers.append(first)
    wait_for(
        lambda: call("has-session", "-t", "=" + session).returncode == 0,
        "the first tmux session",
    )
    first_pid = call(
        "display-message", "-p", "-t", session, "#{pane_pid}"
    ).stdout.strip()
    assert first_pid.isdigit()

    first.kill()
    first.wait(timeout=3)
    assert call("has-session", "-t", "=" + session).returncode == 0

    second = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )
    viewers.append(second)
    wait_for(
        lambda: int(
            call(
                "display-message",
                "-p",
                "-t",
                session,
                "#{session_attached}",
            ).stdout.strip()
            or "0"
        )
        > 0,
        "the second tmux viewer",
    )
    second_pid = call(
        "display-message", "-p", "-t", session, "#{pane_pid}"
    ).stdout.strip()
    assert second_pid == first_pid, (first_pid, second_pid)
finally:
    for viewer in viewers:
        if viewer.poll() is None:
            viewer.kill()
    call("kill-server")
`;

  const result = spawnSync("python3", ["-c", pythonTest, tmuxCommand], {
    encoding: "utf8",
  });
  assert.equal(
    result.status,
    0,
    `real tmux detach test failed:\n${result.stdout}\n${result.stderr}`,
  );
}

await runRealTmuxDetachTest();
console.log("Terminal session persistence tests passed.");
