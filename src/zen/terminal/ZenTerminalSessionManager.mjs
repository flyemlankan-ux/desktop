/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Keeps the small amount of information needed to reconnect a browser tab to
 * its tmux session.
 *
 * The tmux session itself is the live process keeper. This pref is only a
 * directory: terminal tab id -> tmux name + Firefox container id. A pending
 * deletion is written before tmux is called so a fast browser quit cannot turn
 * an explicitly closed tab into an abandoned background session.
 */

export const ZEN_TERMINAL_SESSIONS_PREF = "zen.terminal.sessions";
export const ZEN_TERMINAL_TMUX_SOCKET = "zen-terminal";
export const ZEN_TERMINAL_TMUX_SESSION_PREFIX = "zt_";

function getSubprocess() {
  return ChromeUtils.importESModule("resource://gre/modules/Subprocess.sys.mjs")
    .Subprocess;
}

function getMacSubprocessOptions() {
  return Services.appinfo?.OS === "Darwin" ? { disclaim: true } : {};
}

export function normalizeTerminalSessionId(value) {
  const clean = String(value || "")
    .trim()
    .toLowerCase();
  if (!/^[a-z0-9][a-z0-9-]{0,95}$/.test(clean)) {
    return "";
  }
  return clean;
}

export function getTerminalTmuxSessionName(sessionId) {
  const clean = normalizeTerminalSessionId(sessionId);
  return clean ? `${ZEN_TERMINAL_TMUX_SESSION_PREFIX}${clean}` : "";
}

export function readTerminalSessionRecords() {
  try {
    const parsed = JSON.parse(
      Services.prefs.getStringPref(ZEN_TERMINAL_SESSIONS_PREF, "{}"),
    );
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed;
    }
  } catch (_) {
    // A damaged preference must not stop the browser from opening a terminal.
  }
  return {};
}

export function writeTerminalSessionRecords(records) {
  Services.prefs.setStringPref(
    ZEN_TERMINAL_SESSIONS_PREF,
    JSON.stringify(records || {}),
  );
}

export function registerTerminalSession(
  sessionId,
  { userContextId = "", terminalContainerId = "" } = {},
) {
  const id = normalizeTerminalSessionId(sessionId);
  if (!id) {
    return null;
  }

  const now = Date.now();
  const records = readTerminalSessionRecords();
  const previous = records[id] || {};
  records[id] = {
    version: 1,
    id,
    tmuxSessionName: getTerminalTmuxSessionName(id),
    userContextId: String(userContextId || previous.userContextId || ""),
    terminalContainerId: String(
      terminalContainerId || previous.terminalContainerId || "",
    ),
    createdAt: Number(previous.createdAt || now),
    lastSeenAt: now,
    pendingDelete: false,
  };
  writeTerminalSessionRecords(records);
  return records[id];
}

export function getTerminalSessionRecord(sessionId) {
  const id = normalizeTerminalSessionId(sessionId);
  return id ? readTerminalSessionRecords()[id] || null : null;
}

export function listTerminalSessionsForUserContextId(userContextId) {
  const wanted = String(userContextId || "");
  if (!wanted) {
    return [];
  }
  return Object.values(readTerminalSessionRecords()).filter(
    (record) => String(record?.userContextId || "") === wanted,
  );
}

function markTerminalSessionPendingDelete(sessionId) {
  const id = normalizeTerminalSessionId(sessionId);
  if (!id) {
    return null;
  }

  const records = readTerminalSessionRecords();
  const previous = records[id] || {
    version: 1,
    id,
    tmuxSessionName: getTerminalTmuxSessionName(id),
    userContextId: "",
    terminalContainerId: "",
    createdAt: Date.now(),
    lastSeenAt: Date.now(),
  };
  records[id] = {
    ...previous,
    pendingDelete: true,
    deleteRequestedAt: Date.now(),
  };
  writeTerminalSessionRecords(records);
  return records[id];
}

function removeTerminalSessionRecord(sessionId) {
  const id = normalizeTerminalSessionId(sessionId);
  const records = readTerminalSessionRecords();
  if (id && Object.hasOwn(records, id)) {
    delete records[id];
    writeTerminalSessionRecords(records);
  }
}

async function readProcessOutput(process) {
  let output = "";
  try {
    let chunk;
    while ((chunk = await process.stdout?.readString())) {
      output += chunk;
    }
  } catch (_) {
    // The exit code below remains the source of truth.
  }
  const result = await process.wait();
  return { output: output.trim(), exitCode: result.exitCode };
}

/**
 * Finds tmux through the user's login shell. Apps opened from Finder often do
 * not inherit Homebrew's PATH, while a login shell normally does.
 */
export async function findTerminalTmuxCommand() {
  try {
    const process = await getSubprocess().call({
      ...getMacSubprocessOptions(),
      command: "/bin/zsh",
      arguments: ["-lc", "command -v tmux"],
      environmentAppend: true,
      stderr: "pipe",
    });
    const result = await readProcessOutput(process);
    if (result.exitCode === 0) {
      const command = result.output
        .split(/\r?\n/)
        .find((line) => /^\/\S*\/tmux$/u.test(line.trim()));
      if (command) {
        return command.trim();
      }
    }
  } catch (_) {
    // The caller will use the honest non-persistent fallback.
  }
  return "";
}

async function callTmux(tmuxCommand, argumentsList) {
  const process = await getSubprocess().call({
    ...getMacSubprocessOptions(),
    command: tmuxCommand,
    arguments: ["-L", ZEN_TERMINAL_TMUX_SOCKET, ...argumentsList],
    environmentAppend: true,
    stderr: "pipe",
  });
  return readProcessOutput(process);
}

/**
 * Resizes the saved tmux window through tmux itself. This deliberately avoids
 * writing resize control text into the interactive shell or a running CLI.
 */
export async function resizeTerminalTmuxSession(
  tmuxCommand,
  sessionId,
  { rows, columns } = {},
) {
  const name = getTerminalTmuxSessionName(sessionId);
  rows = Number(rows);
  columns = Number(columns);
  if (
    !tmuxCommand ||
    !name ||
    !Number.isInteger(rows) ||
    !Number.isInteger(columns) ||
    rows < 1 ||
    columns < 2
  ) {
    return false;
  }

  try {
    const result = await callTmux(tmuxCommand, [
      "resize-window",
      "-t",
      `=${name}`,
      "-x",
      String(columns),
      "-y",
      String(rows),
    ]);
    return result.exitCode === 0;
  } catch (_) {
    return false;
  }
}

export async function terminalTmuxSessionExists(tmuxCommand, sessionId) {
  const name = getTerminalTmuxSessionName(sessionId);
  if (!tmuxCommand || !name) {
    return false;
  }
  try {
    const result = await callTmux(tmuxCommand, [
      "has-session",
      "-t",
      `=${name}`,
    ]);
    return result.exitCode === 0;
  } catch (_) {
    return false;
  }
}

/**
 * Destroys one terminal session after an explicit user action.
 *
 * Missing tmux sessions count as already destroyed. If tmux itself cannot be
 * found, the pending record remains and retryPendingTerminalSessionDeletes()
 * will try again on the next browser start.
 */
export async function destroyTerminalSession(
  sessionId,
  { tmuxCommand = "" } = {},
) {
  const record = markTerminalSessionPendingDelete(sessionId);
  if (!record) {
    return true;
  }

  const command = tmuxCommand || (await findTerminalTmuxCommand());
  if (!command) {
    return false;
  }

  const exists = await terminalTmuxSessionExists(command, record.id);
  if (!exists) {
    removeTerminalSessionRecord(record.id);
    return true;
  }

  try {
    await callTmux(command, [
      "kill-session",
      "-t",
      `=${record.tmuxSessionName}`,
    ]);
  } catch (_) {
    // Verify below. A raced session exit is also a successful cleanup.
  }

  if (await terminalTmuxSessionExists(command, record.id)) {
    return false;
  }
  removeTerminalSessionRecord(record.id);
  return true;
}

export async function retryPendingTerminalSessionDeletes() {
  const pending = Object.values(readTerminalSessionRecords()).filter(
    (record) => record?.pendingDelete,
  );
  if (!pending.length) {
    return [];
  }

  const tmuxCommand = await findTerminalTmuxCommand();
  if (!tmuxCommand) {
    return pending.map((record) => ({ id: record.id, deleted: false }));
  }

  return Promise.all(
    pending.map(async (record) => ({
      id: record.id,
      deleted: await destroyTerminalSession(record.id, { tmuxCommand }),
    })),
  );
}

/**
 * Settings/container deletion can call this before removing the recipe.
 * Keeping this function here avoids making the Settings code understand tmux.
 */
export async function destroyTerminalSessionsForUserContextId(userContextId) {
  const records = listTerminalSessionsForUserContextId(userContextId);
  for (const record of records) {
    markTerminalSessionPendingDelete(record.id);
  }
  return Promise.all(
    records.map((record) => destroyTerminalSession(record.id)),
  );
}
