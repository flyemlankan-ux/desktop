/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

const { Subprocess } = ChromeUtils.importESModule(
  "resource://gre/modules/Subprocess.sys.mjs"
);

const surface = document.getElementById("zen-terminal-surface");
const output = document.getElementById("zen-terminal-output");
const terminalPrompt = document.getElementById("zen-terminal-prompt");
const statusText = document.getElementById("zen-terminal-status-text");

let shellProcess = null;
let shellReady = false;
let stopping = false;

function appendLine(text = "", className = "") {
  const line = document.createElement("div");
  line.className = ["terminal-line", className].filter(Boolean).join(" ");
  line.textContent = text;
  output.appendChild(line);
  output.scrollTop = output.scrollHeight;
}

const ESC = String.fromCharCode(27);
const BEL = String.fromCharCode(7);
const BACKSPACE = String.fromCharCode(8);

function cleanTerminalText(text = "") {
  let cleaned = "";
  for (let index = 0; index < text.length; index++) {
    const char = text[index];

    if (char === BEL || char === BACKSPACE) {
      continue;
    }

    if (char !== ESC) {
      cleaned += char;
      continue;
    }

    const next = text[index + 1];
    if (next === "]") {
      index += 2;
      while (index < text.length && text[index] !== BEL) {
        if (text[index] === ESC && text[index + 1] === "\\") {
          index++;
          break;
        }
        index++;
      }
      continue;
    }

    if (next === "[") {
      index += 2;
      while (index < text.length && !/[A-Za-z@-~]/.test(text[index])) {
        index++;
      }
      continue;
    }

    if (next === "(" || next === ")") {
      index += 2;
      continue;
    }

    index++;
  }
  return cleaned;
}

function appendChunk(text = "", className = "") {
  const cleaned = cleanTerminalText(text);
  const lines = cleaned.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  for (const line of lines) {
    appendLine(line, className);
  }
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
      label: `${shell} through macOS pseudo-terminal`
    };
  }

  return {
    command: shell,
    arguments: ["-l"],
    label: shell
  };
}

async function readPipe(pipe, className = "") {
  try {
    let chunk;
    while ((chunk = await pipe.readString())) {
      appendChunk(chunk, className);
    }
  } catch (error) {
    if (!stopping) {
      appendLine(`reader stopped: ${error.message}`, "terminal-muted");
    }
  }
}

async function startShell() {
  setStatus("starting shell", false);
  appendLine("Starting local shell…", "terminal-muted");

  const launch = getShellLaunch();
  const env = {
    TERM: "xterm-256color",
    COLORTERM: "truecolor",
    ZEN_TERMINAL: "1"
  };

  try {
    shellProcess = await Subprocess.call({
      command: launch.command,
      arguments: launch.arguments,
      environmentAppend: true,
      environment: env,
      stderr: "pipe"
    });

    shellReady = true;
    setStatus("ready — type directly into this terminal", true);
    appendLine(`Connected to ${launch.label}`, "terminal-muted");
    surface.focus();

    readPipe(shellProcess.stdout);
    if (shellProcess.stderr) {
      readPipe(shellProcess.stderr, "terminal-error");
    }

    const result = await shellProcess.wait();
    shellReady = false;
    if (!stopping) {
      appendLine(`Shell exited with code ${result.exitCode}`, "terminal-muted");
      setStatus("shell exited", false);
    }
  } catch (error) {
    shellReady = false;
    appendLine(`Could not start shell: ${error.message}`, "terminal-error");
    setStatus("shell failed", false);
  }
}

async function writeToShell(text) {
  if (!shellProcess || !shellReady) {
    appendLine("Shell is not ready yet.", "terminal-muted");
    return;
  }

  try {
    await shellProcess.stdin.write(text);
  } catch (error) {
    appendLine(`Could not write to shell: ${error.message}`, "terminal-error");
  }
}

function controlKeyFor(event) {
  if (
    !event.ctrlKey ||
    event.metaKey ||
    event.altKey ||
    event.key.length !== 1
  ) {
    return null;
  }

  const code = event.key.toUpperCase().charCodeAt(0);
  if (code < 65 || code > 90) {
    return null;
  }

  return String.fromCharCode(code - 64);
}

function terminalSequenceFor(event) {
  const control = controlKeyFor(event);
  if (control) {
    return control;
  }

  switch (event.key) {
    case "Enter":
      return "\r";
    case "Backspace":
      return "\x7f";
    case "Tab":
      return "\t";
    case "Escape":
      return "\x1b";
    case "ArrowUp":
      return "\x1b[A";
    case "ArrowDown":
      return "\x1b[B";
    case "ArrowRight":
      return "\x1b[C";
    case "ArrowLeft":
      return "\x1b[D";
    case "Home":
      return "\x1b[H";
    case "End":
      return "\x1b[F";
    case "Delete":
      return "\x1b[3~";
    default:
      if (
        !event.metaKey &&
        !event.ctrlKey &&
        !event.altKey &&
        event.key.length === 1
      ) {
        return event.key;
      }
      return null;
  }
}

surface.addEventListener("keydown", async event => {
  const sequence = terminalSequenceFor(event);
  if (!sequence) {
    return;
  }

  event.preventDefault();

  if (event.ctrlKey && event.key.toLowerCase() === "l") {
    output.replaceChildren();
  }

  await writeToShell(sequence);
});

surface.addEventListener("paste", async event => {
  const text = event.clipboardData?.getData("text/plain");
  if (!text) {
    return;
  }

  event.preventDefault();
  await writeToShell(text);
});

surface.addEventListener("mousedown", () => surface.focus());
window.addEventListener("pagehide", stopShell, { once: true });
window.addEventListener("beforeunload", stopShell, { once: true });
window.addEventListener("pageshow", () => surface.focus());

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
