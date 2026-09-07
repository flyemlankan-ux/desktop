/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/** Small durable reconnect records; tmux, not the browser, owns live shells. */
export const ZEN_TERMINAL_SESSIONS_PREF = "zen.terminal.sessions";
export const ZEN_TERMINAL_TMUX_SOCKET = "zen-terminal";
export const ZEN_TERMINAL_TMUX_SESSION_PREFIX = "zt_";
const operations = new Map();

function getSubprocess() {
  return ChromeUtils.importESModule("resource://gre/modules/Subprocess.sys.mjs")
    .Subprocess;
}
function macOptions() {
  return Services.appinfo?.OS === "Darwin" ? { disclaim: true } : {};
}
function timers() {
  return ChromeUtils.importESModule("resource://gre/modules/Timer.sys.mjs");
}
export function normalizeTerminalSessionId(value) {
  const id = String(value || "")
    .trim()
    .toLowerCase();
  return /^[a-z0-9][a-z0-9-]{0,95}$/.test(id) &&
    !["constructor", "prototype"].includes(id)
    ? id
    : "";
}
export function getTerminalTmuxSessionName(id) {
  const clean = normalizeTerminalSessionId(id);
  return clean ? `${ZEN_TERMINAL_TMUX_SESSION_PREFIX}${clean}` : "";
}
export function readTerminalSessionRecords() {
  const records = Object.create(null);
  try {
    const parsed = JSON.parse(
      Services.prefs.getStringPref(ZEN_TERMINAL_SESSIONS_PREF, "{}"),
    );
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return records;
    }
    for (const [id, record] of Object.entries(parsed)) {
      if (
        normalizeTerminalSessionId(id) !== id ||
        !record ||
        typeof record !== "object" ||
        Array.isArray(record)
      ) {
        continue;
      }
      records[id] = {
        ...record,
        id,
        tmuxSessionName: getTerminalTmuxSessionName(id),
      };
    }
  } catch (_) {
    // A broken record is not permission to kill a process.
  }
  return records;
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
  if (!id) return null;
  const records = readTerminalSessionRecords();
  const previous = records[id] || {};
  // A reload/late startup cannot cancel an explicit deletion request.
  if (previous.pendingDelete) return null;
  const now = Date.now();
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
export function getTerminalSessionRecord(id) {
  const clean = normalizeTerminalSessionId(id);
  return clean ? readTerminalSessionRecords()[clean] || null : null;
}
export function listTerminalSessionsForUserContextId(userContextId) {
  const wanted = String(userContextId || "");
  return wanted
    ? Object.values(readTerminalSessionRecords()).filter(
        (record) => String(record.userContextId || "") === wanted,
      )
    : [];
}
function markPending(sessionId) {
  const id = normalizeTerminalSessionId(sessionId);
  if (!id) return null;
  const records = readTerminalSessionRecords();
  records[id] = {
    ...(records[id] || {}),
    id,
    tmuxSessionName: getTerminalTmuxSessionName(id),
    pendingDelete: true,
    deleteRequestedAt: Date.now(),
  };
  writeTerminalSessionRecords(records);
  // Write the intent now, before asynchronous cleanup or a fast app quit.
  Services.prefs.savePrefFile?.(null);
  return records[id];
}
function removeRecord(id) {
  const records = readTerminalSessionRecords();
  delete records[id];
  writeTerminalSessionRecords(records);
}
function serial(id, action) {
  const previous = operations.get(id) || Promise.resolve();
  const task = previous.catch(() => {}).then(action);
  operations.set(id, task);
  const clear = () => {
    if (operations.get(id) === task) operations.delete(id);
  };
  task.then(clear, clear);
  return task;
}

/** Drain both pipes concurrently. A broken/hung tool is unknown, never absent. */
async function runCommand(options, timeoutMs = 8000) {
  const process = await getSubprocess().call({
    ...macOptions(),
    environmentAppend: true,
    ...options,
    stderr: "pipe",
  });
  const { setTimeout, clearTimeout } = timers();
  let timedOut = false;
  let truncated = false;
  const timer = setTimeout(() => {
    timedOut = true;
    try {
      process.kill(0);
    } catch (_) {}
  }, timeoutMs);
  async function drain(pipe) {
    let result = "";
    let chunk;
    while (pipe && (chunk = await pipe.readString())) {
      if (result.length + chunk.length > 65536) truncated = true;
      if (result.length < 65536)
        result += chunk.slice(0, 65536 - result.length);
    }
    return result.trim();
  }
  try {
    const [output, error, result] = await Promise.all([
      drain(process.stdout),
      drain(process.stderr),
      process.wait(),
    ]);
    if (timedOut) throw new Error("Terminal helper timed out");
    return { output, error, exitCode: result.exitCode, truncated };
  } catch (error) {
    if (!timedOut) {
      try {
        process.kill(0);
      } catch (_) {}
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
export async function findTerminalTmuxCommand() {
  try {
    const result = await runCommand(
      { command: "/bin/zsh", arguments: ["-lc", "command -v tmux"] },
      5000,
    );
    if (result.exitCode === 0) {
      return (
        result.output
          .split(/\r?\n/)
          .map((line) => line.trim())
          .find((line) => /^\/[^\r\n]*\/tmux$/u.test(line)) || ""
      );
    }
  } catch (_) {}
  return "";
}
function callTmux(command, args) {
  return runCommand({
    command,
    arguments: ["-L", ZEN_TERMINAL_TMUX_SOCKET, "-f", "/dev/null", ...args],
    environment: {
      LC_ALL: "C",
      TERM: "xterm-256color",
      SHELL_SESSIONS_DISABLE: "1",
    },
  });
}
/** Exact inventory distinguishes a missing session from inaccessible tmux. */
export async function terminalTmuxSessionState(command, id) {
  const name = getTerminalTmuxSessionName(id);
  if (!command || !name) return "unknown";
  try {
    const result = await callTmux(command, [
      "list-sessions",
      "-F",
      "#{session_name}",
    ]);
    if (result.truncated) return "unknown";
    if (result.exitCode === 0)
      return result.output.split(/\r?\n/).includes(name) ? "present" : "absent";
    if (
      result.exitCode === 1 &&
      /^(?:no server running on |error connecting to [^\n]+ \(No such file or directory\))/u.test(
        result.error,
      )
    )
      return "absent";
  } catch (_) {}
  return "unknown";
}
export async function terminalTmuxSessionExists(command, id) {
  return (await terminalTmuxSessionState(command, id)) === "present";
}
function quote(value) {
  return `'${String(value).replaceAll("'", "'\\''")}'`;
}
export function terminalShellScript(shell, command = "") {
  // Recipe is passed as a command argument, never typed into an unready prompt.
  // An interactive login shell loads the same user tools as a normal terminal.
  return command
    ? `${command}\nzen_terminal_exit=$?\nif [ "$zen_terminal_exit" -ne 0 ]; then printf '\\nStartup steps stopped (exit %s).\\n' "$zen_terminal_exit"; fi\nexec ${quote(shell)} -l`
    : `exec ${quote(shell)} -l`;
}
export async function prepareTerminalTmuxSession(
  command,
  id,
  { shell, home, startupCommand = "", rows = 24, columns = 80 },
) {
  const name = getTerminalTmuxSessionName(id);
  if (!command || !name || !shell?.startsWith("/") || !home?.startsWith("/"))
    throw new Error("Invalid terminal startup settings");
  return serial(id, async () => {
    if (
      !getTerminalSessionRecord(id) ||
      getTerminalSessionRecord(id).pendingDelete
    )
      throw new Error("This terminal was closed");
    let state = await terminalTmuxSessionState(command, id);
    if (state === "unknown")
      throw new Error(
        "Cannot check the saved session. It has not been replaced.",
      );
    if (state === "present") return { created: false };
    if (getTerminalSessionRecord(id)?.pendingDelete)
      throw new Error("This terminal was closed");
    const result = await callTmux(command, [
      "new-session",
      "-d",
      "-s",
      name,
      "-x",
      String(Math.max(2, Math.min(1000, columns))),
      "-y",
      String(Math.max(1, Math.min(1000, rows))),
      "-c",
      home,
      shell,
      "-lic",
      terminalShellScript(shell, startupCommand),
    ]);
    state = await terminalTmuxSessionState(command, id);
    if (state !== "present")
      throw new Error(result.error || "The saved terminal could not start");
    // A competing browser process may have created it first; only tmux's winner ran the recipe.
    for (const [option, value] of [
      ["status", "off"],
      ["prefix", "None"],
      ["prefix2", "None"],
      ["mouse", "on"],
    ]) {
      const configured = await callTmux(command, [
        "set-option",
        "-t",
        name,
        option,
        value,
      ]);
      if (configured.exitCode !== 0)
        throw new Error(
          configured.error || "Could not configure the saved terminal",
        );
    }
    return { created: result.exitCode === 0 };
  });
}
export async function resizeTerminalTmuxSession(
  command,
  id,
  { rows, columns } = {},
) {
  const name = getTerminalTmuxSessionName(id);
  if (
    !command ||
    !name ||
    !Number.isInteger(rows) ||
    !Number.isInteger(columns) ||
    rows < 1 ||
    rows > 1000 ||
    columns < 2 ||
    columns > 1000
  )
    return false;
  try {
    return (
      (
        await callTmux(command, [
          "resize-window",
          "-t",
          `=${name}`,
          "-x",
          String(columns),
          "-y",
          String(rows),
        ])
      ).exitCode === 0
    );
  } catch (_) {
    return false;
  }
}
export async function destroyTerminalSession(id, { tmuxCommand = "" } = {}) {
  const record = markPending(id);
  if (!record) return true;
  return serial(record.id, async () => {
    const command = tmuxCommand || (await findTerminalTmuxCommand());
    if (!command) return false;
    let state = await terminalTmuxSessionState(command, record.id);
    if (state === "unknown") return false;
    if (state === "present") {
      try {
        await callTmux(command, [
          "kill-session",
          "-t",
          `=${getTerminalTmuxSessionName(record.id)}`,
        ]);
      } catch (_) {
        return false;
      }
      state = await terminalTmuxSessionState(command, record.id);
    }
    if (state !== "absent") return false;
    removeRecord(record.id);
    return true;
  });
}
export async function retryPendingTerminalSessionDeletes() {
  const pending = Object.values(readTerminalSessionRecords()).filter(
    (record) => record.pendingDelete,
  );
  if (!pending.length) return [];
  const tmuxCommand = await findTerminalTmuxCommand();
  if (!tmuxCommand)
    return pending.map((record) => ({ id: record.id, deleted: false }));
  return Promise.all(
    pending.map(async (record) => ({
      id: record.id,
      deleted: await destroyTerminalSession(record.id, { tmuxCommand }),
    })),
  );
}
export async function destroyTerminalSessionsForUserContextId(userContextId) {
  const records = listTerminalSessionsForUserContextId(userContextId);
  for (const record of records) markPending(record.id);
  return Promise.all(
    records.map((record) => destroyTerminalSession(record.id)),
  );
}
