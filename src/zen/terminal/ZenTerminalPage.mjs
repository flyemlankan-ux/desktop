/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import {
  getTerminalContainerRecipe,
  normalizeTerminalRecipe,
} from "chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs";
import { compileTerminalRecipeSteps } from "chrome://browser/content/zen-terminal/ZenTerminalRecipeRunner.mjs";
import {
  findTerminalTmuxCommand,
  getTerminalTmuxSessionName,
  normalizeTerminalSessionId,
  registerTerminalSession,
  resizeTerminalTmuxSession,
  prepareTerminalTmuxSession,
  terminalShellScript,
  getTerminalTmuxSocket,
} from "chrome://browser/content/zen-terminal/ZenTerminalSessionManager.mjs";

const { Subprocess } = ChromeUtils.importESModule(
  "resource://gre/modules/Subprocess.sys.mjs",
);

const surface = document.getElementById("zen-terminal-surface");
const output = document.getElementById("zen-terminal-output");
const terminalPrompt = document.getElementById("zen-terminal-prompt");
const statusText = document.getElementById("zen-terminal-status-text");

const pageState = (window.__zenTerminalPageState ||= {});
pageState.instanceId = (pageState.instanceId || 0) + 1;
if (pageState.onDataDisposable) {
  pageState.onDataDisposable.dispose?.();
  pageState.onDataDisposable = null;
}

let shellProcess = null;
let shellReady = false;
let stopping = false;
let terminal = null;
let fitAddon = null;
let resizeObserver = null;
let resizeAnimationFrame = 0;
let activeShellLaunch = null;
let activeTmuxCommand = "";
let activeTerminalSessionId = "";
let pendingTmuxResize = null;
let tmuxResizeTask = null;
let lastTmuxResize = "";
let inputQueue = Promise.resolve();
let queuedInputBytes = 0;
let pendingHighSurrogate = "";
let tmuxSessionWasNew = false;

const MACOS_SUBPROCESS_OPTIONS =
  Services.appinfo.OS === "Darwin" ? { disclaim: true } : {};

function getSearchParams() {
  return new URLSearchParams(window.location.search);
}

function getTerminalUserContextId() {
  return getSearchParams().get("userContextId");
}

function getTerminalContainerId() {
  return getSearchParams().get("container");
}

function getTerminalSessionId() {
  let sessionId = normalizeTerminalSessionId(getSearchParams().get("session"));
  if (sessionId) {
    return sessionId;
  }

  // One-time migration for terminal tabs created before persistent sessions.
  sessionId = Services.uuid
    .generateUUID()
    .toString()
    .slice(1, -1)
    .toLowerCase();
  const url = new URL(window.location.href);
  url.searchParams.set("session", sessionId);
  window.history.replaceState(null, "", url.href);
  return sessionId;
}

function getTerminalContainerName() {
  const params = getSearchParams();
  return params.get("name") || "Terminal";
}

function getStartupRecord() {
  const userContextId = getTerminalUserContextId();
  if (!userContextId) {
    return null;
  }

  return getTerminalContainerRecipe(userContextId);
}

function getStartupCommand() {
  const record = getStartupRecord();
  const recipe = normalizeTerminalRecipe(record?.recipe);
  return compileTerminalRecipeSteps(recipe.steps);
}

function shellQuote(value) {
  return `'${String(value).replaceAll("'", "'\\''")}'`;
}

function getHomeDirectory() {
  return Services.env.get("HOME") || "/";
}

function setStatus(text, isReady = false) {
  terminalPrompt.textContent = isReady ? "›_" : "…";
  statusText.textContent = text;
  surface.toggleAttribute("terminal-ready", isReady);
}

function getShellCommand() {
  const envShell = Services.env.get("SHELL");
  return envShell || "/bin/zsh";
}

function getShellLaunch({
  tmuxCommand = "",
  sessionId = "",
  startupCommand = "",
} = {}) {
  if (Services.appinfo.OS !== "Darwin") {
    throw new Error("This terminal build supports macOS only.");
  }
  const helper = Services.dirsvc.get("XREExeF", Ci.nsIFile).parent;
  helper.append("zen-terminal-pty");
  if (!helper.exists()) {
    throw new Error(
      "The terminal helper is missing. Reinstall Zen Terminal; your saved sessions have not been removed.",
    );
  }
  const shell = getShellCommand();
  const command = tmuxCommand || shell;
  const args = tmuxCommand
    ? [
        "-L",
        getTerminalTmuxSocket(),
        "-f",
        "/dev/null",
        "attach-session",
        "-t",
        `=${getTerminalTmuxSessionName(sessionId)}`,
      ]
    : ["-lic", terminalShellScript(shell, startupCommand)];
  return {
    command: helper.path,
    arguments: [
      "--rows",
      String(terminal.rows),
      "--cols",
      String(terminal.cols),
      "--",
      command,
      ...args,
    ],
    label: "native macOS pseudo-terminal",
    persistent: Boolean(tmuxCommand),
    resizable: true,
  };
}

function fitTerminalToSurface() {
  if (!terminal || !fitAddon || stopping) {
    return;
  }

  const bounds = output.getBoundingClientRect();
  if (bounds.width <= 0 || bounds.height <= 0) {
    return;
  }

  const dimensions = fitAddon.proposeDimensions();
  if (
    !dimensions ||
    !Number.isFinite(dimensions.cols) ||
    !Number.isFinite(dimensions.rows)
  ) {
    return;
  }

  fitAddon.fit();
  queueTerminalResize(terminal.rows, terminal.cols);
}

function scheduleTerminalFit() {
  if (!terminal || stopping || resizeAnimationFrame) {
    return;
  }

  resizeAnimationFrame = window.requestAnimationFrame(() => {
    resizeAnimationFrame = 0;
    fitTerminalToSurface();
  });
}

function initTerminal() {
  if (!window.Terminal) {
    throw new Error("xterm.js did not load");
  }
  if (!window.FitAddon?.FitAddon) {
    throw new Error("xterm.js FitAddon did not load");
  }

  terminal = new window.Terminal({
    allowProposedApi: false,
    convertEol: false,
    cursorBlink: true,
    cursorStyle: "bar",
    customGlyphs: false,
    disableStdin: true,
    screenReaderMode: Services.appinfo.accessibilityEnabled || false,
    drawBoldTextInBrightColors: false,
    fontFamily: "SFMono-Regular, Menlo, Monaco, Consolas, monospace",
    fontSize: 13,
    fontWeight: "400",
    fontWeightBold: "600",
    letterSpacing: 0,
    lineHeight: 1.18,
    macOptionIsMeta: true,
    scrollback: 10000,
    smoothScrollDuration: 80,
    theme: {
      background: "#050505",
      foreground: "#eeeeee",
      cursor: "#f5f5f5",
      selectionBackground: "#3a3a3a",
      black: "#000000",
      brightBlack: "#666666",
      red: "#ff6b6b",
      brightRed: "#ff8f8f",
      green: "#8fe769",
      brightGreen: "#b8ff9e",
      yellow: "#f4d35e",
      brightYellow: "#ffe98a",
      blue: "#6ea8fe",
      brightBlue: "#9cc4ff",
      magenta: "#d795ff",
      brightMagenta: "#e6b8ff",
      cyan: "#6fffe9",
      brightCyan: "#a4fff2",
      white: "#eeeeee",
      brightWhite: "#ffffff",
    },
  });

  fitAddon = new window.FitAddon.FitAddon();
  terminal.loadAddon(fitAddon);
  terminal.open(output);
  // One screen and one subscription per page; never suppress valid repeated keys.
  fitTerminalToSurface();
  terminal.focus();

  pageState.onDataDisposable = terminal.onData((data) => {
    writeToShell(data);
  });

  resizeObserver = new ResizeObserver(scheduleTerminalFit);
  resizeObserver.observe(output);
  window.addEventListener("resize", scheduleTerminalFit);
  document.fonts?.ready.then(scheduleTerminalFit).catch(() => {});
}

async function readPipe(pipe, className = "") {
  try {
    let chunk;
    while ((chunk = await pipe.readString())) {
      await new Promise((resolve) => terminal.write(chunk, resolve));
    }
  } catch (error) {
    if (!stopping) {
      terminal.writeln(`reader stopped: ${error.message}`);
    }
  }
}

async function startShell() {
  try {
    setStatus("starting terminal", false);
    initTerminal();
    if (!getStartupRecord()) {
      throw new Error(
        "Choose a terminal container from the new-tab menu to open a terminal.",
      );
    }
    // Validate before creating a session or launching any command.
    const startupCommand = getStartupCommand();
    const terminalSessionId = getTerminalSessionId();
    activeTerminalSessionId = terminalSessionId;
    if (
      !registerTerminalSession(terminalSessionId, {
        userContextId: getTerminalUserContextId(),
        terminalContainerId: getTerminalContainerId(),
      })
    ) {
      throw new Error(
        "This session is being closed. Open a new terminal tab instead.",
      );
    }
    const tmuxCommand = await findTerminalTmuxCommand();
    if (stopping) return;
    activeTmuxCommand = tmuxCommand;
    // Check the installation before any saved recipe can execute.
    activeShellLaunch = getShellLaunch({
      tmuxCommand,
      sessionId: terminalSessionId,
      startupCommand,
    });
    if (tmuxCommand) {
      const result = await prepareTerminalTmuxSession(
        tmuxCommand,
        terminalSessionId,
        {
          shell: getShellCommand(),
          home: getHomeDirectory(),
          startupCommand,
          rows: terminal.rows,
          columns: terminal.cols,
        },
      );
      if (stopping) return;
      tmuxSessionWasNew = result.created;
    }
    const createdProcess = await Subprocess.call({
      ...MACOS_SUBPROCESS_OPTIONS,
      command: activeShellLaunch.command,
      arguments: activeShellLaunch.arguments,
      workdir: getHomeDirectory(),
      environmentAppend: true,
      environment: {
        TERM: "xterm-256color",
        COLORTERM: "truecolor",
        ZEN_TERMINAL: "1",
        SHELL_SESSIONS_DISABLE: "1",
        ZEN_TERMINAL_SESSION_ID: terminalSessionId,
      },
      stderr: "pipe",
    });
    // A late subprocess result must not survive the page it belonged to.
    if (stopping) {
      createdProcess.kill(0);
      return;
    }
    shellProcess = createdProcess;
    shellReady = true;
    terminal.options.disableStdin = false;
    queueTerminalResize(terminal.rows, terminal.cols);
    setStatus(
      activeShellLaunch.persistent
        ? tmuxSessionWasNew
          ? "session saved · ready"
          : "saved session reconnected"
        : "not saved · install tmux to keep work after quitting",
      true,
    );
    terminal.focus();
    const readers = [readPipe(shellProcess.stdout)];
    if (shellProcess.stderr) readers.push(readPipe(shellProcess.stderr));
    const result = await shellProcess.wait();
    await Promise.all(readers);
    shellReady = false;
    terminal.options.disableStdin = true;
    if (!stopping) {
      terminal.writeln(`\r\nTerminal disconnected (exit ${result.exitCode}).`);
      setStatus("disconnected · saved work has not been deleted", false);
      document.getElementById("zen-terminal-reconnect").hidden = false;
    }
  } catch (error) {
    shellReady = false;
    if (stopping) return;
    if (terminal) terminal.options.disableStdin = true;
    terminal?.writeln(`Could not open terminal: ${error.message}`);
    setStatus("could not connect · saved work has not been deleted", false);
    document.getElementById("zen-terminal-reconnect").hidden = false;
  }
}

function queueTerminalResize(rows = terminal?.rows, columns = terminal?.cols) {
  rows = Number(rows);
  columns = Number(columns);
  if (
    !shellProcess ||
    !shellReady ||
    !Number.isInteger(rows) ||
    !Number.isInteger(columns) ||
    rows < 1 ||
    columns < 2
  ) {
    return;
  }

  if (activeShellLaunch?.resizable) {
    void writeFrame(`R${rows} ${columns}\n`);
    return;
  }

  pendingTmuxResize = { rows, columns };
  if (!tmuxResizeTask) {
    tmuxResizeTask = flushTmuxResizeQueue().finally(() => {
      tmuxResizeTask = null;
    });
  }
}

async function flushTmuxResizeQueue() {
  while (pendingTmuxResize && !stopping) {
    const dimensions = pendingTmuxResize;
    pendingTmuxResize = null;
    const resizeKey = `${dimensions.columns}x${dimensions.rows}`;
    if (resizeKey === lastTmuxResize) {
      continue;
    }

    const resized = await resizeTerminalTmuxSession(
      activeTmuxCommand,
      activeTerminalSessionId,
      dimensions,
    );
    if (resized) {
      lastTmuxResize = resizeKey;
    }
  }
}

function writeFrame(frame) {
  const bytes = new TextEncoder().encode(frame).length;
  if (!shellProcess || !shellReady || stopping) return Promise.resolve();
  if (queuedInputBytes + bytes > 4 * 1024 * 1024) {
    setStatus("input is busy · wait before pasting more", false);
    return Promise.resolve();
  }
  queuedInputBytes += bytes;
  const task = inputQueue.then(async () => {
    if (!stopping && shellReady) await shellProcess.stdin.write(frame);
  });
  inputQueue = task
    .catch((error) => {
      if (!stopping) setStatus(`input failed: ${error.message}`, false);
    })
    .finally(() => {
      queuedInputBytes -= bytes;
    });
  return inputQueue;
}

function writeToShell(text) {
  if (!text || !shellReady || stopping) return Promise.resolve();
  // Input methods and automation can deliver a UTF-16 pair in two events.
  // Keep the first half until its partner arrives instead of encoding two replacement glyphs.
  text = pendingHighSurrogate + text;
  pendingHighSurrogate = "";
  if (/[\uD800-\uDBFF]/u.test(text.at(-1))) {
    pendingHighSurrogate = text.at(-1);
    text = text.slice(0, -1);
  }
  if (!text) return Promise.resolve();
  const encoder = new TextEncoder();
  // Reject an oversized paste as a whole, never execute a truncated command.
  if (encoder.encode(text).length + queuedInputBytes > 4 * 1024 * 1024) {
    setStatus("paste too large · limit is 4 MB", false);
    return Promise.resolve();
  }
  let framed = "";
  for (let offset = 0; offset < text.length; ) {
    let end = Math.min(offset + 16384, text.length);
    if (end < text.length && /[\uD800-\uDBFF]/u.test(text[end - 1])) end--;
    const chunk = text.slice(offset, end);
    framed += `I${encoder.encode(chunk).length}\n${chunk}`;
    offset = end;
  }
  return writeFrame(framed);
}

surface.addEventListener("mousedown", (event) => {
  if (!event.target.closest("button")) terminal?.focus();
});
document
  .getElementById("zen-terminal-reconnect")
  .addEventListener("click", () => window.location.reload());
window.addEventListener("pagehide", stopShell, { once: true });
window.addEventListener("beforeunload", stopShell, { once: true });
window.addEventListener("pageshow", () => {
  scheduleTerminalFit();
  terminal?.focus();
});

async function stopShell() {
  stopping = true;
  shellReady = false;
  try {
    resizeObserver?.disconnect();
    resizeObserver = null;
    window.removeEventListener("resize", scheduleTerminalFit);
    if (resizeAnimationFrame) {
      window.cancelAnimationFrame(resizeAnimationFrame);
      resizeAnimationFrame = 0;
    }
    pendingTmuxResize = null;
    pageState.onDataDisposable?.dispose?.();
    pageState.onDataDisposable = null;
    if (shellProcess) {
      // Closing/reloading the page only detaches the terminal viewer. The
      // browser-level TabClose handler is the only place that destroys tmux.
      shellProcess.kill();
    }
  } catch (_) {
    // The process may already be gone. That is fine on tab close.
  }
}

startShell();
