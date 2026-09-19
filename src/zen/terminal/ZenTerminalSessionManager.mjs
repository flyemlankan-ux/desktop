/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/** Small durable reconnect records; tmux, not the browser, owns live shells. */
export const ZEN_TERMINAL_SESSIONS_PREF = "zen.terminal.sessions";
// The directory, not a copied preference, owns the process namespace. Copying
// browser data must never grant access to another profile's live terminals.
export function terminalSocketForProfilePath(path) {
  if (typeof path !== "string" || !path.startsWith("/"))
    throw new Error("Missing terminal profile directory");
  let hash = 0xcbf29ce484222325n;
  for (const byte of new TextEncoder().encode(path)) {
    hash = BigInt.asUintN(64, (hash ^ BigInt(byte)) * 0x100000001b3n);
  }
  return `zen-terminal-p${hash.toString(16).padStart(16, "0")}`;
}
export function getTerminalTmuxSocket() {
  return terminalSocketForProfilePath(
    Services.dirsvc.get("ProfD", Ci.nsIFile).path,
  );
}
export const ZEN_TERMINAL_TMUX_SESSION_PREFIX = "zt_";
// The default ChromeUtils module loader owns this state once per profile.
// Window-scoped imports must never create separate operation queues/observers.
const coordinator = { operations: new Map(), containerCleanupObserver: null };
export function getTerminalSessionCoordinator() { return coordinator; }
function sharedCoordinator() {
  return ChromeUtils.importESModule(
    "chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs",
  ).getTerminalSessionCoordinator();
}
export const ZEN_TERMINAL_SESSION_DELETE_TOPIC = "zen-terminal-session-delete-requested";

function currentTerminalOwner(userContextId) {
  const owner = String(userContextId || "");
  if (!/^[1-9][0-9]*$/u.test(owner) || !Number.isSafeInteger(Number(owner))) return false;
  const { ContextualIdentityService } = ChromeUtils.importESModule(
    "moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs",
  );
  const { getTerminalContainerRecipe } = ChromeUtils.importESModule(
    "chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs",
  );
  return ContextualIdentityService.getPublicIdentities().some(identity => String(identity.userContextId) === owner) &&
    Boolean(getTerminalContainerRecipe(owner));
}

/** One ES-module observer per profile, shared by all browser windows. */
export function ensureTerminalContainerCleanupObserver() {
  if (!Services.obs?.addObserver) return;
  const shared = ChromeUtils.importESModule(
    "chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs",
  );
  // Create the long-lived observer in the shared module, not in the first
  // browser window's module global (which would retain a closed window).
  if (shared.ensureTerminalContainerCleanupObserver !== ensureTerminalContainerCleanupObserver) {
    return shared.ensureTerminalContainerCleanupObserver();
  }
  const state = sharedCoordinator();
  if (state.containerCleanupObserver) return;
  const observer = {
    observe(subject, topic) {
      if (topic !== "contextual-identity-deleted") return;
      const id = String(subject?.wrappedJSObject?.userContextId || "");
      if (!/^[1-9][0-9]*$/u.test(id) || !Number.isSafeInteger(Number(id))) return;
      try {
        const { removeTerminalContainerRecipe } = ChromeUtils.importESModule(
          "chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs",
        );
        removeTerminalContainerRecipe(id);
      } catch (error) {
        console.error("Could not remove deleted terminal setup", error);
      }
      // This call marks every matching record pending synchronously, before its
      // first await. A concurrent page cannot create a replacement for that ID.
      void destroyTerminalSessionsForUserContextId(id).catch(error =>
        console.error("Terminal cleanup remains pending", error));
    },
  };
  Services.obs.addObserver(observer, "contextual-identity-deleted");
  state.containerCleanupObserver = observer;
}

export function assertTerminalSessionCanStart(id) {
  const record = getTerminalSessionRecord(id);
  if (!record || record.pendingDelete) throw new Error("This terminal was closed");
  // Old ownerless records cannot acquire a new owner through page registration.
  // Retain their low-level cleanup compatibility, but validate every owned job.
  if (record.userContextId && !currentTerminalOwner(record.userContextId)) {
    throw new Error("This terminal setup was removed. Choose an existing setup from the new-tab menu.");
  }
  return record;
}


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
  ensureTerminalContainerCleanupObserver();
  const id = normalizeTerminalSessionId(sessionId);
  if (!id) return null;
  const records = readTerminalSessionRecords();
  const previous = records[id] || {};
  // A reload/late startup cannot cancel an explicit deletion request.
  if (previous.pendingDelete) return null;
  const owner = String(userContextId || previous.userContextId || "");
  const legacyOwner = String(
    terminalContainerId || previous.terminalContainerId || "",
  );
  // Another view can reconnect, but cannot transfer a live shell to a different
  // saved setup. Refuse before writes so cleanup still targets its true owner.
  // Old ownerless records are not permission to claim an existing shell either.
  if (
    records[id] &&
    (owner !== String(previous.userContextId || "") ||
      legacyOwner !== String(previous.terminalContainerId || ""))
  ) return null;
  const now = Date.now();
  records[id] = {
    version: 1,
    id,
    tmuxSessionName: getTerminalTmuxSessionName(id),
    userContextId: owner,
    terminalContainerId: legacyOwner,
    createdAt: Number(previous.createdAt || now),
    lastSeenAt: now,
    pendingDelete: false,
    startupAttempted: previous.startupAttempted === true,
    persistent: previous.persistent === true,
  };
  writeTerminalSessionRecords(records);
  return records[id];
}
export function markTerminalSessionStartupAttempt(id, { persistent = false } = {}) {
  const records = readTerminalSessionRecords();
  const record = records[normalizeTerminalSessionId(id)];
  if (!record || record.pendingDelete) throw new Error("This terminal was closed");
  record.startupAttempted = true;
  record.persistent = persistent;
  writeTerminalSessionRecords(records);
  Services.prefs.savePrefFile?.(null);
}
export function terminalSessionEndedError() {
  const error = new Error("This terminal ended. Its previous work cannot be restored. Start again to run the saved setup as a new job.");
  error.code = "ZEN_TERMINAL_SESSION_ENDED";
  return error;
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
  // Stop any attached local helper as well as background tmux work. Repeated
  // notifications are harmless; pages unregister their listener when stopped.
  Services.obs?.notifyObservers?.(null, ZEN_TERMINAL_SESSION_DELETE_TOPIC, id);
  return records[id];
}
function removeRecord(id) {
  const records = readTerminalSessionRecords();
  delete records[id];
  writeTerminalSessionRecords(records);
}
function serial(id, action) {
  const { operations } = sharedCoordinator();
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
    arguments: ["-L", getTerminalTmuxSocket(), "-f", "/dev/null", ...args],
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
export function terminalShellScript(shell, command = "", startingDirectory = "") {
  // Recipe is passed as a command argument, never typed into an unready prompt.
  // An interactive login shell loads the same user tools as a normal terminal.
  const folderGuard = startingDirectory
    ? `cd -- ${quote(startingDirectory)} || { printf '%s\\n' 'Starting folder is unavailable. No startup steps were run.' >&2; exit 1; }\n`
    : "";
  return folderGuard + (command
    ? `${command}\nzen_terminal_exit=$?\nif [ "$zen_terminal_exit" -ne 0 ]; then printf '\\nStartup steps stopped (exit %s).\\n' "$zen_terminal_exit"; fi\nexec ${quote(shell)} -l`
    : `exec ${quote(shell)} -l`);
}
export async function prepareTerminalTmuxSession(
  command,
  id,
  options,
  { allowRestart = false, previouslyStarted = false } = {},
) {
  const name = getTerminalTmuxSessionName(id);
  if (!command || !name)
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
    if (!allowRestart && (previouslyStarted || getTerminalSessionRecord(id)?.startupAttempted)) {
      throw terminalSessionEndedError();
    }
    // Edits apply only when creating a job, never when reconnecting existing work.
    const { shell, home, startupCommand = "", rows = 24, columns = 80 } =
      typeof options === "function" ? await options() : options;
    if (!shell?.startsWith("/") || !home?.startsWith("/") || /[\x00-\x1f\x7f]/u.test(home))
      throw new Error("Invalid terminal startup settings");
    if (getTerminalSessionRecord(id)?.pendingDelete)
      throw new Error("This terminal was closed");
    assertTerminalSessionCanStart(id);
    // Save before launch: a crash in the narrow launch window cannot silently
    // rerun commands whose side effects may already have happened.
    markTerminalSessionStartupAttempt(id, { persistent: true });
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
      terminalShellScript(shell, startupCommand, home),
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
  ensureTerminalContainerCleanupObserver();
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
