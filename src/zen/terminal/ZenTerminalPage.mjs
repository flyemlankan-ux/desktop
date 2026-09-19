/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import {
  getTerminalContainerRecipe,
  normalizeTerminalRecipe,
} from "chrome://browser/content/zen-terminal/ZenTerminalContainerStore.mjs";
import { compileTerminalRecipeSteps, validateTerminalStartingDirectory } from "chrome://browser/content/zen-terminal/ZenTerminalRecipeRunner.mjs";
import {
  findTerminalTmuxCommand,
  getTerminalTmuxSessionName,
  normalizeTerminalSessionId,
  registerTerminalSession,
  assertTerminalSessionCanStart,
  ZEN_TERMINAL_SESSION_DELETE_TOPIC,
  getTerminalSessionRecord,
  markTerminalSessionStartupAttempt,
  terminalSessionEndedError,
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
let restartOffered = false;
let readyStatusText = "";
let inputWarningActive = false;
let inputWarningVersion = 0;
let reducedMotionQuery = null;
let searchAddon = null;

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

function getNewSessionSettings() {
  validateTerminalPageContext();
  const record = getStartupRecord();
  if (!record) throw new Error("This terminal setup was removed. Choose an existing setup from the new-tab menu.");
  const recipe = normalizeTerminalRecipe(record?.recipe);
  const home = validateTerminalStartingDirectory(
    recipe.startingDirectory || (recipe.startingDirectory === "" ? getHomeDirectory() : recipe.startingDirectory),
    { checkExists: true },
  );
  return { shell: getShellCommand(), home, startupCommand: compileTerminalRecipeSteps(recipe.steps), rows: terminal.rows, columns: terminal.cols };
}

function shellQuote(value) {
  return `'${String(value).replaceAll("'", "'\\''")}'`;
}

function getHomeDirectory() {
  return Services.env.get("HOME") || "/";
}

function setStatus(text, isReady = false) {
  if (isReady) readyStatusText = text;
  inputWarningActive = false;
  surface.toggleAttribute("terminal-input-warning", false);
  terminalPrompt.textContent = isReady ? "›_" : "…";
  statusText.textContent = text;
  surface.toggleAttribute("terminal-ready", isReady);
}

function setInputWarning(text) {
  // Rejected input did not disconnect the shell. Keep its real ready state.
  inputWarningActive = true;
  inputWarningVersion++;
  statusText.textContent = text;
  surface.toggleAttribute("terminal-input-warning", true);
}

function updateTerminalMotion() {
  if (!terminal || stopping) return;
  const reduced = Boolean(reducedMotionQuery?.matches);
  terminal.options.cursorBlink = !reduced;
  terminal.options.smoothScrollDuration = reduced ? 0 : 80;
}

// Search only reads this viewer's bounded scrollback. It never writes shell input.
function runTerminalSearch(previous = false, incremental = false) {
  const input = document.getElementById("zen-terminal-find-input");
  const result = document.getElementById("zen-terminal-find-result");
  if (!searchAddon) return;
  if (!input.value) {
    searchAddon.clearDecorations();
    terminal.clearSelection();
    result.textContent = "";
    return;
  }
  const options = { regex: false, caseSensitive: false, incremental };
  const found = previous
    ? searchAddon.findPrevious(input.value, options)
    : searchAddon.findNext(input.value, options);
  result.textContent = found ? "Match found" : "No matches";
}

function openTerminalSearch() {
  if (!terminal || stopping) return;
  document.getElementById("zen-terminal-find").hidden = false;
  surface.toggleAttribute("terminal-search-open", true);
  const input = document.getElementById("zen-terminal-find-input");
  input.focus();
  input.select();
  scheduleTerminalFit();
}

function closeTerminalSearch() {
  document.getElementById("zen-terminal-find").hidden = true;
  surface.toggleAttribute("terminal-search-open", false);
  searchAddon?.clearDecorations();
  terminal?.clearSelection();
  scheduleTerminalFit();
  terminal?.focus();
}

function handleTerminalSearchKey(event) {
  const open = !document.getElementById("zen-terminal-find").hidden;
  const shortcut = (event.metaKey || event.ctrlKey) && !event.altKey &&
    !event.shiftKey && event.key.toLowerCase() === "f";
  if (shortcut || (open && !event.isComposing &&
      (event.key === "Escape" || event.key === "Enter"))) {
    event.preventDefault();
    event.stopImmediatePropagation();
    if (event.type !== "keydown") return;
    if (shortcut) openTerminalSearch();
    else if (event.key === "Escape") closeTerminalSearch();
    else runTerminalSearch(event.shiftKey);
  }
}

function getShellCommand() {
  const envShell = Services.env.get("SHELL");
  return envShell || "/bin/zsh";
}

function getShellLaunch({
  tmuxCommand = "",
  sessionId = "",
  startupCommand = "",
  home = "",
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
    : ["-lic", terminalShellScript(shell, startupCommand, home)];
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

  reducedMotionQuery = window.matchMedia?.("(prefers-reduced-motion: reduce)") || null;
  terminal = new window.Terminal({
    allowProposedApi: false,
    convertEol: false,
    cursorBlink: !reducedMotionQuery?.matches,
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
    smoothScrollDuration: reducedMotionQuery?.matches ? 0 : 80,
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
  searchAddon = new window.SearchAddon.SearchAddon({ highlightLimit: 100 });
  terminal.loadAddon(searchAddon);
  reducedMotionQuery?.addEventListener("change", updateTerminalMotion);
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

function validateTerminalPageContext() {
  const context = window.docShell.QueryInterface(Ci.nsILoadContext);
  if (context.usePrivateBrowsing) {
    throw new Error(
      "Terminals are unavailable in private windows because shell history and files are not private. Open a normal window instead.",
    );
  }
  const requested = getTerminalUserContextId();
  const actual = context.originAttributes.userContextId;
  if (!/^[1-9][0-9]*$/.test(requested || "") ||
      !Number.isSafeInteger(Number(requested)) || Number(requested) !== actual) {
    throw new Error("This terminal does not match its browser container. Open a new terminal from the New Tab menu.");
  }
  const { ContextualIdentityService } = ChromeUtils.importESModule(
    "moz-src:///toolkit/components/contextualidentity/ContextualIdentityService.sys.mjs",
  );
  if (!ContextualIdentityService.getPublicIdentities().some(
    identity => identity.userContextId === actual,
  )) {
    throw new Error("This saved terminal setup no longer exists. Choose another setup from the New Tab menu.");
  }
}

async function startShell({ allowRestart = false } = {}) {
  try {
    restartOffered = false;
    document.getElementById("zen-terminal-reconnect").hidden = true;
    setStatus("starting terminal", false);
    if (!terminal) initTerminal();
    validateTerminalPageContext();
    if (!getStartupRecord()) {
      throw new Error(
        "Choose a terminal container from the new-tab menu to open a terminal.",
      );
    }
    // Existing work ignores later setup edits; only a new shell reads settings.
    const terminalSessionId = getTerminalSessionId();
    activeTerminalSessionId = terminalSessionId;
    const oldRecord = getTerminalSessionRecord(terminalSessionId);
    // The URL keeps this marker when Undo Close restores a tab whose session
    // record was intentionally removed. It is never an automatic restart grant.
    const previouslyStarted = getSearchParams().get("started") === "1" ||
      oldRecord?.startupAttempted === true ||
      (oldRecord && !Object.hasOwn(oldRecord, "startupAttempted"));
    if (
      !registerTerminalSession(terminalSessionId, {
        userContextId: getTerminalUserContextId(),
        terminalContainerId: getTerminalContainerId(),
      })
    ) {
      throw new Error(
        "This session is closed or belongs to another setup. Open a new terminal tab instead.",
      );
    }
    const tmuxCommand = await findTerminalTmuxCommand();
    if (stopping) return;
    activeTmuxCommand = tmuxCommand;
    // Check the installation before any saved recipe can execute.
    if (!tmuxCommand && oldRecord?.persistent) {
      throw new Error("The saved terminal needs tmux, which is unavailable. Restore tmux and retry; the existing job has not been replaced.");
    }
    if (!tmuxCommand && previouslyStarted && !allowRestart) {
      throw terminalSessionEndedError();
    }
    const markTabStarted = () => {
      const url = new URL(window.location.href);
      url.searchParams.set("started", "1");
      window.history.replaceState(null, "", url.href);
    };
    const freshSettings = () => {
      const settings = getNewSessionSettings();
      markTabStarted();
      return settings;
    };
    const directSettings = tmuxCommand ? null : freshSettings();
    activeShellLaunch = getShellLaunch({
      ...directSettings,
      tmuxCommand,
      sessionId: terminalSessionId,
    });
    if (tmuxCommand) {
      const result = await prepareTerminalTmuxSession(
        tmuxCommand,
        terminalSessionId,
        freshSettings,
        { allowRestart, previouslyStarted: Boolean(previouslyStarted) },
      );
      if (stopping) return;
      tmuxSessionWasNew = result.created;
    }
    // Mark live reconnects too, so an old restored tab gains the Undo Close guard.
    markTabStarted();
    assertTerminalSessionCanStart(terminalSessionId);
    if (!tmuxCommand) markTerminalSessionStartupAttempt(terminalSessionId);
    const createdProcess = await Subprocess.call({
      ...MACOS_SUBPROCESS_OPTIONS,
      command: activeShellLaunch.command,
      arguments: activeShellLaunch.arguments,
      workdir: directSettings?.home || getHomeDirectory(),
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
      setStatus("terminal disconnected · check whether its job is still running", false);
      const button = document.getElementById("zen-terminal-reconnect");
      button.textContent = "Check session";
      button.hidden = false;
    }
  } catch (error) {
    shellReady = false;
    if (stopping) return;
    if (terminal) terminal.options.disableStdin = true;
    terminal?.writeln(`Could not open terminal: ${error.message}`);
    restartOffered = error.code === "ZEN_TERMINAL_SESSION_ENDED";
    setStatus(restartOffered
      ? "previous terminal ended · starting again runs your setup as a new job"
      : error.message, false);
    const button = document.getElementById("zen-terminal-reconnect");
    button.textContent = restartOffered ? "Start again" : "Retry check";
    button.hidden = false;
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

function writeFrame(frame, { isInput = false } = {}) {
  const bytes = new TextEncoder().encode(frame).length;
  if (!shellProcess || !shellReady || stopping) return Promise.resolve();
  if (queuedInputBytes + bytes > 4 * 1024 * 1024) {
    setInputWarning("input is busy · wait before pasting more");
    return Promise.resolve();
  }
  queuedInputBytes += bytes;
  const warningAtAcceptance = inputWarningVersion;
  const task = inputQueue.then(async () => {
    if (!stopping && shellReady) {
      await shellProcess.stdin.write(frame);
      // Only later successful user input clears feedback. An earlier queued
      // write or a resize must not erase a newly reported rejected paste.
      if (isInput && !stopping && shellReady && inputWarningActive &&
          warningAtAcceptance === inputWarningVersion) {
        setStatus(readyStatusText, true);
      }
    }
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
    setInputWarning("paste too large · limit is 4 MB");
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
  return writeFrame(framed, { isInput: true });
}

const sessionDeleteObserver = {
  observe(_subject, topic, id) {
    if (topic !== ZEN_TERMINAL_SESSION_DELETE_TOPIC || id !== activeTerminalSessionId) return;
    void stopShell();
    terminal?.writeln("\r\nThis terminal was closed. Cleanup of its running work was requested.");
    setStatus("terminal closed · cleanup requested", false);
    document.getElementById("zen-terminal-reconnect").hidden = true;
  },
};
Services.obs?.addObserver?.(sessionDeleteObserver, ZEN_TERMINAL_SESSION_DELETE_TOPIC);

surface.addEventListener("mousedown", (event) => {
  if (!event.target.closest("button, input, #zen-terminal-find")) terminal?.focus();
});
// Capture before xterm sees the shortcut; search input lives outside its textarea.
for (const type of ["keydown", "keypress", "keyup"]) {
  window.addEventListener(type, handleTerminalSearchKey, true);
}
document.getElementById("zen-terminal-find-input").addEventListener("input", () => runTerminalSearch(false, true));
document.getElementById("zen-terminal-find-previous").addEventListener("click", () => runTerminalSearch(true));
document.getElementById("zen-terminal-find-next").addEventListener("click", () => runTerminalSearch());
document.getElementById("zen-terminal-find-close").addEventListener("click", closeTerminalSearch);

document
  .getElementById("zen-terminal-reconnect")
  .addEventListener("click", () => void startShell({ allowRestart: restartOffered }));
window.addEventListener("pagehide", stopShell, { once: true });
window.addEventListener("beforeunload", stopShell, { once: true });
window.addEventListener("pageshow", () => {
  scheduleTerminalFit();
  terminal?.focus();
});

async function stopShell() {
  try { Services.obs?.removeObserver?.(sessionDeleteObserver, ZEN_TERMINAL_SESSION_DELETE_TOPIC); } catch (_) {}
  stopping = true;
  shellReady = false;
  for (const type of ["keydown", "keypress", "keyup"]) {
    window.removeEventListener(type, handleTerminalSearchKey, true);
  }
  searchAddon?.dispose();
  searchAddon = null;
  reducedMotionQuery?.removeEventListener("change", updateTerminalMotion);
  reducedMotionQuery = null;
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
