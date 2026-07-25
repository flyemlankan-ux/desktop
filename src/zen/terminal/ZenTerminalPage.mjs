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
  terminalTmuxSessionExists,
  ZEN_TERMINAL_TMUX_SOCKET,
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
let lastInputWrite = "";
let lastInputWriteTime = 0;
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

const PYTHON_RESIZE_PREFIX = "\x1b]777;resize;";
const PYTHON_RESIZE_SUFFIX = "\x07";
const PYTHON_PTY_BRIDGE = String.raw`
import errno
import fcntl
import os
import pty
import select
import signal
import struct
import sys
import termios

rows = max(6, int(sys.argv[1]))
cols = max(20, int(sys.argv[2]))
shell = sys.argv[3]
home = os.path.expanduser("~")

def set_size(fd, new_rows, new_cols):
    data = struct.pack("HHHH", max(6, new_rows), max(20, new_cols), 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, data)

pid, fd = pty.fork()
if pid == 0:
    try:
        os.chdir(home)
    except Exception:
        pass
    os.environ["TERM"] = "xterm-256color"
    os.environ["COLORTERM"] = "truecolor"
    os.environ["ZEN_TERMINAL"] = "1"
    os.environ["SHELL_SESSIONS_DISABLE"] = "1"
    os.environ["COLUMNS"] = str(cols)
    os.environ["LINES"] = str(rows)
    os.execv(shell, [shell, "-l"])

set_size(fd, rows, cols)
os.set_blocking(fd, False)
os.set_blocking(sys.stdin.fileno(), False)
stdin_open = True

prefix = b"\x1b]777;resize;"
suffix = b"\x07"

def handle_input(data):
    global rows, cols
    if data.startswith(prefix) and data.endswith(suffix):
        try:
            payload = data[len(prefix):-len(suffix)].decode("ascii")
            new_rows, new_cols = [int(part) for part in payload.split(";", 1)]
            rows, cols = new_rows, new_cols
            set_size(fd, rows, cols)
            os.kill(pid, signal.SIGWINCH)
            return
        except Exception:
            return
    os.write(fd, data)

while True:
    read_targets = [fd]
    if stdin_open:
        read_targets.append(sys.stdin.fileno())
    try:
        readable, _, _ = select.select(read_targets, [], [])
    except OSError:
        break

    if fd in readable:
        try:
            data = os.read(fd, 65536)
        except OSError as error:
            if error.errno in (errno.EIO, errno.EBADF):
                break
            raise
        if not data:
            break
        os.write(sys.stdout.fileno(), data)

    if stdin_open and sys.stdin.fileno() in readable:
        try:
            data = os.read(sys.stdin.fileno(), 65536)
        except BlockingIOError:
            data = b""
        if not data:
            stdin_open = False
        else:
            handle_input(data)

try:
    os.kill(pid, signal.SIGHUP)
except Exception:
    pass
`;

function setStatus(text, isReady = false) {
  terminalPrompt.textContent = isReady ? "›_" : "…";
  statusText.textContent = text;
  surface.toggleAttribute("terminal-ready", isReady);
}

function getShellCommand() {
  const envShell = Services.env.get("SHELL");
  return envShell || "/bin/zsh";
}

function getShellLaunches({ tmuxCommand = "", sessionId = "" } = {}) {
  const shell = getShellCommand();
  const rows = String(terminal.rows);
  const columns = String(terminal.cols);
  const shellLoginCommand = `exec ${shellQuote(shell)} -l`;
  const tmuxSessionName = getTerminalTmuxSessionName(sessionId);
  const tmuxLoginCommand =
    tmuxCommand && tmuxSessionName
      ? `exec ${shellQuote(tmuxCommand)} -L ${shellQuote(
          ZEN_TERMINAL_TMUX_SOCKET,
        )} new-session -A -s ${shellQuote(tmuxSessionName)}`
      : "";
  const makeLoginCommand = (finalCommand) =>
    `cd ${shellQuote(
      getHomeDirectory(),
    )}; export SHELL_SESSIONS_DISABLE=1; stty rows ${rows} cols ${columns} 2>/dev/null; ${finalCommand}`;

  const launches = [];

  if (Services.appinfo.OS === "Darwin") {
    if (tmuxLoginCommand) {
      launches.push({
        command: "/usr/bin/script",
        arguments: [
          "-q",
          "/dev/null",
          "/bin/zsh",
          "-lc",
          makeLoginCommand(tmuxLoginCommand),
        ],
        label: "persistent tmux session through the macOS pseudo-terminal",
        persistent: true,
        resizable: false,
      });
    }

    launches.push({
      command: "/usr/bin/script",
      arguments: [
        "-q",
        "/dev/null",
        "/bin/zsh",
        "-lc",
        makeLoginCommand(shellLoginCommand),
      ],
      label: "macOS script pseudo-terminal with initial size",
      persistent: false,
      resizable: false,
    });

    if (
      Services.prefs.getBoolPref(
        "zen.terminal.experimentalPythonPtyBridge",
        false,
      )
    ) {
      launches.push({
        command: "/usr/bin/python3",
        arguments: ["-u", "-c", PYTHON_PTY_BRIDGE, rows, columns, shell],
        label: "experimental resizable PTY bridge",
        persistent: false,
        resizable: true,
      });
    }
  } else {
    if (tmuxLoginCommand) {
      launches.push({
        command: shell,
        arguments: ["-lc", makeLoginCommand(tmuxLoginCommand)],
        label: "persistent tmux session",
        persistent: true,
        resizable: false,
      });
    }
    launches.push({
      command: shell,
      arguments: ["-lc", makeLoginCommand(shellLoginCommand)],
      label: shell,
      persistent: false,
      resizable: false,
    });
  }

  return launches;
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
    disableStdin: false,
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
  setStatus("starting shell", false);
  initTerminal();
  const terminalSessionId = getTerminalSessionId();
  activeTerminalSessionId = terminalSessionId;
  registerTerminalSession(terminalSessionId, {
    userContextId: getTerminalUserContextId(),
    terminalContainerId: getTerminalContainerId(),
  });
  const tmuxCommand = await findTerminalTmuxCommand();
  activeTmuxCommand = tmuxCommand;
  if (tmuxCommand) {
    tmuxSessionWasNew = !(await terminalTmuxSessionExists(
      tmuxCommand,
      terminalSessionId,
    ));
  }
  const env = {
    TERM: "xterm-256color",
    COLORTERM: "truecolor",
    ZEN_TERMINAL: "1",
    SHELL_SESSIONS_DISABLE: "1",
    COLUMNS: String(terminal.cols),
    LINES: String(terminal.rows),
    ZEN_TERMINAL_SESSION_ID: terminalSessionId,
  };

  try {
    let lastError = null;
    for (const launch of getShellLaunches({
      tmuxCommand,
      sessionId: terminalSessionId,
    })) {
      try {
        shellProcess = await Subprocess.call({
          ...MACOS_SUBPROCESS_OPTIONS,
          command: launch.command,
          arguments: launch.arguments,
          environmentAppend: true,
          environment: env,
          stderr: "pipe",
        });
        activeShellLaunch = launch;
        break;
      } catch (error) {
        lastError = error;
      }
    }

    if (!shellProcess) {
      throw lastError || new Error("No shell launcher worked");
    }

    shellReady = true;
    queueTerminalResize(terminal.rows, terminal.cols);
    if (activeShellLaunch.persistent) {
      setStatus(
        tmuxSessionWasNew ? "ready · session saved" : "ready · reattached",
        true,
      );
    } else {
      setStatus("ready · session saving unavailable", true);
      terminal.writeln(
        "\x1b[33mSession saving is unavailable because tmux was not found or could not start.\x1b[0m",
      );
    }
    terminal.focus();

    readPipe(shellProcess.stdout);
    if (shellProcess.stderr) {
      readPipe(shellProcess.stderr, "terminal-error");
    }

    if (!activeShellLaunch.persistent || tmuxSessionWasNew) {
      await runStartupCommands();
    }

    const result = await shellProcess.wait();
    shellReady = false;
    if (!stopping) {
      terminal.writeln(`Shell exited with code ${result.exitCode}`);
      setStatus("shell exited", false);
    }
  } catch (error) {
    shellReady = false;
    terminal?.writeln(`Could not start shell: ${error.message}`);
    setStatus("shell failed", false);
  }
}

async function runStartupCommands() {
  try {
    const command = getStartupCommand();
    if (command) {
      await writeToShell(`${command}\n`);
    }
  } catch (error) {
    const step =
      Number.isInteger(error.stepIndex) && error.stepIndex >= 0
        ? ` in step ${error.stepIndex + 1}`
        : "";
    terminal?.writeln(`Startup recipe stopped${step}: ${error.message}`);
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

  if (!activeShellLaunch?.persistent) {
    if (activeShellLaunch?.resizable) {
      void writeToShell(
        `${PYTHON_RESIZE_PREFIX}${rows};${columns}${PYTHON_RESIZE_SUFFIX}`,
      );
    }
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

function shouldDropDuplicateInput(text) {
  if (typeof text !== "string" || text.length !== 1) {
    return false;
  }

  const now = performance.now();
  const isDuplicate = text === lastInputWrite && now - lastInputWriteTime < 25;
  lastInputWrite = text;
  lastInputWriteTime = now;
  return isDuplicate;
}

async function writeToShell(text) {
  if (shouldDropDuplicateInput(text)) {
    return;
  }

  if (!shellProcess || !shellReady) {
    return;
  }

  try {
    await shellProcess.stdin.write(text);
  } catch (error) {
    terminal?.writeln(`Could not write to shell: ${error.message}`);
  }
}

surface.addEventListener("mousedown", () => terminal?.focus());
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
