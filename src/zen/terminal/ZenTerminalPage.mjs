/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import {
  getTerminalContainerRecipe,
  normalizeTerminalRecipe,
} from "chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs";

const { Subprocess } = ChromeUtils.importESModule(
  "resource://gre/modules/Subprocess.sys.mjs",
);

const surface = document.getElementById("zen-terminal-surface");
const output = document.getElementById("zen-terminal-output");
const terminalPrompt = document.getElementById("zen-terminal-prompt");
const statusText = document.getElementById("zen-terminal-status-text");

let shellProcess = null;
let shellReady = false;
let stopping = false;
let terminal = null;
let activeShellLaunch = null;

function getSearchParams() {
  return new URLSearchParams(window.location.search);
}

function getTerminalUserContextId() {
  return getSearchParams().get("userContextId");
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
  return normalizeTerminalRecipe(record?.recipe).command.trim();
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

function getShellLaunches() {
  const shell = getShellCommand();
  const rows = String(terminal.rows);
  const columns = String(terminal.cols);
  const loginCommand = `cd ${shellQuote(getHomeDirectory())}; export SHELL_SESSIONS_DISABLE=1; stty rows ${rows} cols ${columns} 2>/dev/null; exec ${shellQuote(shell)} -l`;

  const launches = [];

  if (Services.appinfo.OS === "Darwin") {
    launches.push({
      command: "/usr/bin/python3",
      arguments: ["-u", "-c", PYTHON_PTY_BRIDGE, rows, columns, shell],
      label: "resizable PTY bridge",
      resizable: true,
    });
    launches.push({
      command: "/usr/bin/script",
      arguments: ["-q", "/dev/null", "/bin/zsh", "-lc", loginCommand],
      label: "macOS script pseudo-terminal fallback",
      resizable: false,
    });
  } else {
    launches.push({
      command: shell,
      arguments: ["-lc", loginCommand],
      label: shell,
      resizable: false,
    });
  }

  return launches;
}

function fitTerminalToSurface() {
  if (!terminal) {
    return;
  }

  const fontSize = 14;
  const characterWidth = 8.4;
  const characterHeight = 19;
  const bounds = output.getBoundingClientRect();
  const columns = Math.max(20, Math.floor(bounds.width / characterWidth));
  const rows = Math.max(6, Math.floor(bounds.height / characterHeight));

  terminal.resize(columns, rows);
  sendTerminalResize(rows, columns);
}

function initTerminal() {
  if (!window.Terminal) {
    throw new Error("xterm.js did not load");
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

  terminal.open(output);
  fitTerminalToSurface();
  terminal.focus();

  terminal.onData(data => {
    writeToShell(data);
  });

  window.addEventListener("resize", fitTerminalToSurface);
}

async function readPipe(pipe, className = "") {
  try {
    let chunk;
    while ((chunk = await pipe.readString())) {
      terminal.write(chunk);
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
  const env = {
    TERM: "xterm-256color",
    COLORTERM: "truecolor",
    ZEN_TERMINAL: "1",
    SHELL_SESSIONS_DISABLE: "1",
    COLUMNS: String(terminal.cols),
    LINES: String(terminal.rows),
  };

  try {
    let lastError = null;
    for (const launch of getShellLaunches()) {
      try {
        shellProcess = await Subprocess.call({
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
    setStatus("ready", true);
    terminal.focus();

    readPipe(shellProcess.stdout);
    if (shellProcess.stderr) {
      readPipe(shellProcess.stderr, "terminal-error");
    }

    await runStartupCommands();

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
  const command = getStartupCommand();
  if (command) {
    await writeToShell(`${command}\n`);
  }
}

async function sendTerminalResize(rows = terminal?.rows, columns = terminal?.cols) {
  if (!shellProcess || !shellReady || !activeShellLaunch?.resizable) {
    return;
  }

  await writeToShell(
    `${PYTHON_RESIZE_PREFIX}${rows};${columns}${PYTHON_RESIZE_SUFFIX}`,
  );
}

async function writeToShell(text) {
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
window.addEventListener("pageshow", () => terminal?.focus());

async function stopShell() {
  stopping = true;
  shellReady = false;
  try {
    if (shellProcess) {
      await shellProcess.stdin.write("exit\n").catch(() => {});
      shellProcess.kill();
    }
  } catch (_) {
    // The process may already be gone. That is fine on tab close.
  }
}

startShell();
