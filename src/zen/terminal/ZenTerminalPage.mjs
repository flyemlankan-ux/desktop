/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

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

function getTerminalContainerName() {
  const params = new URLSearchParams(window.location.search);
  return params.get("name") || "Terminal";
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

function getShellLaunch() {
  const shell = getShellCommand();

  if (Services.appinfo.OS === "Darwin") {
    return {
      command: "/usr/bin/script",
      arguments: ["-q", "/dev/null", shell, "-l"],
      label: `${shell} through macOS pseudo-terminal`,
    };
  }

  return {
    command: shell,
    arguments: ["-l"],
    label: shell,
  };
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
  terminal.writeln(`Starting ${getTerminalContainerName()}…`);

  const launch = getShellLaunch();
  const env = {
    TERM: "xterm-256color",
    COLORTERM: "truecolor",
    ZEN_TERMINAL: "1",
    COLUMNS: String(terminal.cols),
    LINES: String(terminal.rows),
  };

  try {
    shellProcess = await Subprocess.call({
      command: launch.command,
      arguments: launch.arguments,
      environmentAppend: true,
      environment: env,
      stderr: "pipe",
    });

    shellReady = true;
    setStatus("ready — type directly into this terminal", true);
    terminal.writeln(
      `Connected to ${getTerminalContainerName()} (${launch.label})`,
    );
    terminal.focus();

    readPipe(shellProcess.stdout);
    if (shellProcess.stderr) {
      readPipe(shellProcess.stderr, "terminal-error");
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
