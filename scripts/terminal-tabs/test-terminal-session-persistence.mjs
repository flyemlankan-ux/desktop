#!/usr/bin/env node
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import {
  mkdtempSync,
  readFileSync,
  writeFileSync,
  chmodSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const prefs = new Map();
let calls = [];
let handler;
let saved = 0;
let timerDelay;
globalThis.Services = {
  appinfo: { OS: "Darwin" },
  prefs: {
    getStringPref: (name, fallback) => prefs.get(name) ?? fallback,
    setStringPref: (name, value) => prefs.set(name, value),
    savePrefFile: () => saved++,
  },
};
globalThis.ChromeUtils = {
  importESModule(name) {
    if (name.endsWith("/Timer.sys.mjs"))
      return {
        setTimeout: (callback, delay) =>
          setTimeout(callback, timerDelay ?? delay),
        clearTimeout,
      };
    return {
      Subprocess: {
        async call(options) {
          calls.push(options);
          return handler(options);
        },
      },
    };
  },
};
const manager =
  await import("../../src/zen/terminal/ZenTerminalSessionManager.mjs");
const command = "/mock/tmux";
const settings = {
  shell: "/bin/sh",
  home: "/tmp",
  startupCommand: "printf once",
};
function processResult(output = "", error = "", exitCode = 0) {
  const pipe = (value) => ({
    async readString() {
      const chunk = value;
      value = "";
      return chunk;
    },
  });
  return {
    stdout: pipe(output),
    stderr: pipe(error),
    wait: async () => ({ exitCode }),
    kill() {},
  };
}
function mockServer() {
  const sessions = new Set();
  handler = (options) => {
    assert.equal(options.disclaim, true);
    const args = options.arguments;
    if (options.command === "/bin/zsh") return processResult(command);
    assert.deepEqual(args.slice(0, 4), [
      "-L",
      "zen-terminal",
      "-f",
      "/dev/null",
    ]);
    const operation = args[4];
    if (operation === "list-sessions")
      return processResult([...sessions].join("\n"));
    if (operation === "new-session") sessions.add(args[args.indexOf("-s") + 1]);
    if (operation === "kill-session")
      sessions.delete(args[args.indexOf("-t") + 1].slice(1));
    return processResult();
  };
  return sessions;
}
const tests = [];
const test = (name, run) => tests.push([name, run]);

test("validates identifiers and repairs stored target names", () => {
  for (const id of [
    "../bad",
    "constructor",
    "prototype",
    "__proto__",
    "a".repeat(97),
  ])
    assert.equal(manager.normalizeTerminalSessionId(id), "");
  assert.equal(manager.normalizeTerminalSessionId(" AUDIT-1 "), "audit-1");
  prefs.set(
    manager.ZEN_TERMINAL_SESSIONS_PREF,
    JSON.stringify({
      "audit-1": { tmuxSessionName: "other-work" },
      bad: [],
      constructor: {},
    }),
  );
  assert.equal(
    manager.getTerminalSessionRecord("audit-1").tmuxSessionName,
    "zt_audit-1",
  );
  assert.equal(manager.getTerminalSessionRecord("bad"), null);
});

test("failed tool probes remain unknown and keep deletion pending", async () => {
  manager.registerTerminalSession("probe-failure");
  handler = () => {
    throw new Error("simulated permission failure");
  };
  assert.equal(
    await manager.terminalTmuxSessionState(command, "probe-failure"),
    "unknown",
  );
  assert.equal(
    await manager.destroyTerminalSession("probe-failure", {
      tmuxCommand: command,
    }),
    false,
  );
  assert.equal(
    manager.getTerminalSessionRecord("probe-failure").pendingDelete,
    true,
  );
  assert.equal(manager.registerTerminalSession("probe-failure"), null);
  assert.ok(saved > 0);
});

test("failed deletion preserves its retry request; confirmed absence clears it", async () => {
  const sessions = mockServer();
  sessions.add("zt_failed-delete");
  manager.registerTerminalSession("failed-delete");
  const normal = handler;
  handler = (options) =>
    options.arguments.includes("kill-session")
      ? processResult("", "permission denied", 1)
      : normal(options);
  assert.equal(
    await manager.destroyTerminalSession("failed-delete", {
      tmuxCommand: command,
    }),
    false,
  );
  assert.equal(
    manager.getTerminalSessionRecord("failed-delete").pendingDelete,
    true,
  );
  sessions.delete("zt_failed-delete");
  assert.equal(
    await manager.destroyTerminalSession("failed-delete", {
      tmuxCommand: command,
    }),
    true,
  );
  assert.equal(manager.getTerminalSessionRecord("failed-delete"), null);
});

test("only explicit missing-server errors mean absence", async () => {
  for (const error of [
    "permission denied",
    "error connecting to /tmp/socket (Permission denied)",
    "unknown error",
  ]) {
    handler = () => processResult("", error, 1);
    assert.equal(
      await manager.terminalTmuxSessionState(command, "inventory"),
      "unknown",
    );
  }
  for (const error of [
    "no server running on /tmp/socket",
    "error connecting to /tmp/socket (No such file or directory)",
  ]) {
    handler = () => processResult("", error, 1);
    assert.equal(
      await manager.terminalTmuxSessionState(command, "inventory"),
      "absent",
    );
  }
});

test("two simultaneous prepares create and launch the recipe once", async () => {
  mockServer();
  manager.registerTerminalSession("duplicate");
  const results = await Promise.all([
    manager.prepareTerminalTmuxSession(command, "duplicate", settings),
    manager.prepareTerminalTmuxSession(command, "duplicate", settings),
  ]);
  assert.deepEqual(results, [{ created: true }, { created: false }]);
  assert.equal(
    calls.filter((call) => call.arguments.includes("new-session")).length,
    1,
  );
});

test("deletion waits for in-flight creation and prevents later recreation", async () => {
  const sessions = mockServer();
  manager.registerTerminalSession("closing");
  const normal = handler;
  let release;
  let entered;
  const started = new Promise((resolve) => (entered = resolve));
  const paused = new Promise((resolve) => (release = resolve));
  handler = async (options) => {
    if (options.arguments.includes("new-session")) {
      entered();
      await paused;
    }
    return normal(options);
  };
  const preparing = manager.prepareTerminalTmuxSession(
    command,
    "closing",
    settings,
  );
  await started;
  const deleting = manager.destroyTerminalSession("closing", {
    tmuxCommand: command,
  });
  assert.equal(manager.getTerminalSessionRecord("closing").pendingDelete, true);
  assert.equal(manager.registerTerminalSession("closing"), null);
  assert.equal(
    calls.filter((call) => call.arguments.includes("kill-session")).length,
    0,
  );
  release();
  await preparing;
  assert.equal(await deleting, true);
  assert.equal(sessions.has("zt_closing"), false);
  await assert.rejects(
    manager.prepareTerminalTmuxSession(command, "closing", settings),
    /closed/,
  );
});

test("unknown inventory never creates a replacement", async () => {
  manager.registerTerminalSession("unknown");
  handler = () => processResult("", "permission denied", 1);
  await assert.rejects(
    manager.prepareTerminalTmuxSession(command, "unknown", settings),
    /not been replaced/,
  );
  assert.equal(
    calls.some((call) => call.arguments.includes("new-session")),
    false,
  );
});

test("container cleanup kills only matching records", async () => {
  const sessions = mockServer();
  for (const [id, userContextId] of [
    ["container-a", "7"],
    ["container-b", "8"],
  ]) {
    manager.registerTerminalSession(id, { userContextId });
    sessions.add(`zt_${id}`);
  }
  assert.deepEqual(await manager.destroyTerminalSessionsForUserContextId("7"), [
    true,
  ]);
  assert.deepEqual([...sessions], ["zt_container-b"]);
  assert.ok(manager.getTerminalSessionRecord("container-b"));
});

test("startup retry processes saved deletion requests only", async () => {
  const sessions = mockServer();
  manager.registerTerminalSession("retry-target");
  manager.registerTerminalSession("retry-neighbor");
  sessions.add("zt_retry-target");
  sessions.add("zt_retry-neighbor");
  const normal = handler;
  handler = () => {
    throw new Error("temporarily unavailable");
  };
  await manager.destroyTerminalSession("retry-target", {
    tmuxCommand: command,
  });
  handler = normal;
  assert.deepEqual(await manager.retryPendingTerminalSessionDeletes(), [
    { id: "retry-target", deleted: true },
  ]);
  assert.deepEqual([...sessions], ["zt_retry-neighbor"]);
});

test("both output pipes are drained concurrently", async () => {
  let resolveError;
  const errorRead = new Promise((resolve) => (resolveError = resolve));
  let reads = 0;
  handler = () => ({
    stdout: {
      async readString() {
        await errorRead;
        return reads++ ? "" : "zt_concurrent";
      },
    },
    stderr: {
      async readString() {
        resolveError();
        return "";
      },
    },
    wait: async () => ({ exitCode: 0 }),
    kill() {},
  });
  assert.equal(
    await manager.terminalTmuxSessionState(command, "concurrent"),
    "present",
  );
});

test("hung tools time out as unknown and retain pending cleanup", async () => {
  timerDelay = 10;
  let kills = 0;
  handler = () => {
    let finish;
    const ended = new Promise((resolve) => (finish = resolve));
    return {
      stdout: {
        readString: async () => {
          await ended;
          return "";
        },
      },
      stderr: {
        readString: async () => {
          await ended;
          return "";
        },
      },
      wait: async () => {
        await ended;
        return { exitCode: 1 };
      },
      kill() {
        kills++;
        finish();
      },
    };
  };
  try {
    manager.registerTerminalSession("timeout");
    assert.equal(
      await manager.destroyTerminalSession("timeout", { tmuxCommand: command }),
      false,
    );
    assert.equal(
      manager.getTerminalSessionRecord("timeout").pendingDelete,
      true,
    );
    assert.equal(kills, 1);
  } finally {
    timerDelay = undefined;
  }
});

test("truncated inventory is unknown and cannot discard cleanup records", async () => {
  manager.registerTerminalSession("beyond-limit");
  handler = () =>
    processResult("zt_other\n".repeat(10000) + "zt_beyond-limit\n");
  assert.equal(
    await manager.terminalTmuxSessionState(command, "beyond-limit"),
    "unknown",
  );
  assert.equal(
    await manager.destroyTerminalSession("beyond-limit", {
      tmuxCommand: command,
    }),
    false,
  );
  assert.equal(
    manager.getTerminalSessionRecord("beyond-limit").pendingDelete,
    true,
  );
  assert.equal(
    calls.some((call) => call.arguments.includes("kill-session")),
    false,
  );
});

async function realTmuxTest() {
  const tmux = ["/opt/homebrew/bin/tmux", "/usr/local/bin/tmux"].find(
    (file) => spawnSync(file, ["-V"]).status === 0,
  );
  if (!tmux)
    throw new Error(
      "Real persistence proof requires installed tmux; not silently skipped.",
    );
  const directory = mkdtempSync(path.join(tmpdir(), "zen-session-proof-"));
  const socket = `zen-terminal-proof-${process.pid}-${Date.now()}`;
  const shell = path.join(directory, "clean-shell");
  const marker = path.join(directory, "startup.txt");
  // Do not load the user's login files or launch their normal work.
  writeFileSync(
    shell,
    '#!/bin/sh\nif [ "$1" = "-lic" ]; then shift; exec /bin/sh -c "$1"; fi\nexec /bin/sh\n',
  );
  chmodSync(shell, 0o755);
  const direct = (...args) =>
    spawnSync(tmux, ["-L", socket, "-f", "/dev/null", ...args], {
      encoding: "utf8",
    });
  handler = (options) => {
    assert.equal(
      options.command,
      tmux,
      "real adapter must never execute another program",
    );
    const args = [...options.arguments];
    assert.deepEqual(args.slice(0, 2), ["-L", "zen-terminal"]);
    args[1] = socket; // Always isolate the real test from every production session.
    const child = spawn(tmux, args, {
      env: { ...process.env, ...options.environment },
    });
    const done = new Promise((resolve, reject) => {
      child.on("error", reject);
      child.on("close", (code, signal) =>
        resolve({ exitCode: code ?? (signal ? 1 : 0) }),
      );
    });
    const pipe = (stream) => {
      const iterator = stream[Symbol.asyncIterator]();
      return {
        async readString() {
          const result = await iterator.next();
          return result.done ? "" : result.value.toString("utf8");
        },
      };
    };
    return {
      stdout: pipe(child.stdout),
      stderr: pipe(child.stderr),
      wait: () => done,
      kill: () => child.kill("SIGKILL"),
    };
  };
  try {
    const realSettings = {
      shell,
      home: directory,
      startupCommand: `printf '%s\\n' "$PWD" >> '${marker}'`,
    };
    manager.registerTerminalSession("real-target");
    manager.registerTerminalSession("real-neighbor");
    assert.deepEqual(
      await manager.prepareTerminalTmuxSession(
        tmux,
        "real-target",
        realSettings,
      ),
      { created: true },
    );
    await manager.prepareTerminalTmuxSession(tmux, "real-neighbor", {
      shell,
      home: directory,
    });
    for (let tries = 0; tries < 100; tries++) {
      try {
        if (readFileSync(marker, "utf8")) break;
      } catch (_) {}
      await new Promise((resolve) => setTimeout(resolve, 20));
    }
    assert.equal(readFileSync(marker, "utf8"), `${directory}\n`);
    const inspected = direct(
      "display-message",
      "-p",
      "-t",
      "=zt_real-target:",
      "#{pane_pid}",
    );
    assert.equal(inspected.status, 0, inspected.stderr);
    const pid = inspected.stdout.trim();
    assert.match(pid, /^\d+$/);
    assert.deepEqual(
      await manager.prepareTerminalTmuxSession(
        tmux,
        "real-target",
        realSettings,
      ),
      { created: false },
    );
    assert.equal(
      direct(
        "display-message",
        "-p",
        "-t",
        "=zt_real-target:",
        "#{pane_pid}",
      ).stdout.trim(),
      pid,
    );
    assert.equal(
      readFileSync(marker, "utf8"),
      `${directory}\n`,
      "reattach preparation cannot rerun startup",
    );
    assert.equal(
      await manager.resizeTerminalTmuxSession(tmux, "real-target", {
        rows: 31,
        columns: 101,
      }),
      true,
    );
    assert.equal(
      direct(
        "display-message",
        "-p",
        "-t",
        "=zt_real-target:",
        "#{window_width}x#{window_height}",
      ).stdout.trim(),
      "101x31",
    );
    assert.equal(
      await manager.destroyTerminalSession("real-target", {
        tmuxCommand: tmux,
      }),
      true,
    );
    assert.equal(
      await manager.terminalTmuxSessionState(tmux, "real-target"),
      "absent",
    );
    assert.equal(
      await manager.terminalTmuxSessionState(tmux, "real-neighbor"),
      "present",
    );
    assert.equal(
      await manager.destroyTerminalSession("real-neighbor", {
        tmuxCommand: tmux,
      }),
      true,
    );
  } finally {
    direct("kill-server"); // This unique test socket only.
    rmSync(directory, { recursive: true, force: true });
  }
}
test(
  "real module creates once, retains the process, resizes and deletes only its target",
  realTmuxTest,
);

for (const [name, run] of tests) {
  prefs.clear();
  calls = [];
  saved = 0;
  await run();
  console.log(`✓ ${name}`);
}
console.log(
  `\n${tests.length} terminal persistence tests passed (including isolated real tmux).`,
);
