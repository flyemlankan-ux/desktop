#!/usr/bin/env node
// Rendered terminal-page proof, NOT native Zen chrome/menu or installed-app proof.
import assert from "node:assert/strict";
import { spawn, execFileSync } from "node:child_process";
import { createServer } from "node:http";
import { mkdtemp, readFile, writeFile, mkdir, rm } from "node:fs/promises";
import { existsSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
const assets = path.join(root, "src/zen/terminal");
const helper = path.resolve(
  process.env.ZEN_TERMINAL_PTY ||
    path.join(root, "build/terminal-native/zen-terminal-pty"),
);
const proof = path.join(root, "docs/proof/2026-09-07");
const home = await mkdtemp(path.join(tmpdir(), "zen-terminal-browser-"));
const socket = `zt-browser-proof-${process.pid}-${Date.now()}`;
const tmux = execFileSync("/bin/zsh", ["-lc", "command -v tmux"], {
  encoding: "utf8",
}).trim();
assert(tmux.startsWith("/") && tmux.endsWith("/tmux"), "Real tmux is required");
if (!existsSync(helper))
  execFileSync(path.join(root, "scripts/terminal-tabs/build-terminal-pty.sh"), [
    helper,
  ]);
await mkdir(proof, { recursive: true });
await writeFile(path.join(home, ".zshrc"), "PROMPT='proof> '\nRPROMPT=''\n");
await writeFile(
  path.join(home, ".zprofile"),
  'if [ "$ZEN_TEST_NO_TMUX" = 1 ]; then export PATH=/usr/bin:/bin:/usr/sbin:/sbin; fi\n',
);
const environment = {
  ...process.env,
  HOME: home,
  ZDOTDIR: home,
  SHELL: "/bin/zsh",
  PATH: `${path.dirname(tmux)}:/usr/bin:/bin:/usr/sbin:/sbin`,
  TERM: "xterm-256color",
  LANG: "en_US.UTF-8",
  LC_ALL: "en_US.UTF-8",
};
const processes = new Map();
const checks = [];
let nextId = 1;
let browser;
const errors = [];
const server = createServer(async (req, res) => {
  try {
    const pathname = new URL(req.url, "http://localhost").pathname;
    const name = pathname.replace(/^\//, "");
    if (
      !/^(?:[A-Za-z0-9_-]+\.(?:mjs|xhtml|css)|vendor\/[A-Za-z0-9_.-]+)$/.test(
        name,
      )
    ) {
      res.writeHead(404).end();
      return;
    }
    let source = await readFile(path.join(assets, name), "utf8");
    source = source
      .replaceAll("chrome://browser/content/zen-terminal/", "/")
      .replaceAll(
        "chrome://browser/content/zen-styles/zen-terminal-page.css",
        "/zen-terminal-page.css",
      );
    const type =
      name.endsWith(".mjs") || name.endsWith(".js")
        ? "text/javascript"
        : name.endsWith(".css")
          ? "text/css"
          : "text/html";
    res
      .writeHead(200, {
        "Content-Type": `${type}; charset=utf-8`,
        "Cache-Control": "no-store",
      })
      .end(source);
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
function mapArgs(args = []) {
  return args.map((value, i) =>
    i && args[i - 1] === "-L" && value === "zen-terminal" ? socket : value,
  );
}
// Drain immediately so short-lived command output survives exit. Pause at 192 KiB
// (one <=64 KiB stream chunk may remain) and resume only when the browser reads.
function boundedReader(stream) {
  const queue = [];
  let bytes = 0,
    ended = false,
    failure = null,
    wake;
  stream.on("data", (chunk) => {
    queue.push(chunk);
    bytes += Buffer.byteLength(chunk);
    if (bytes >= 192 * 1024) stream.pause();
    wake?.();
    wake = null;
  });
  const end = () => {
    ended = true;
    wake?.();
    wake = null;
  };
  stream.on("end", end);
  stream.on("close", end);
  stream.on("error", (error) => {
    failure = error;
    end();
  });
  return async () => {
    while (!queue.length && !ended)
      await new Promise((resolve) => {
        wake = resolve;
      });
    if (queue.length) {
      const chunk = queue.shift();
      bytes -= Buffer.byteLength(chunk);
      if (bytes < 192 * 1024) stream.resume();
      return chunk;
    }
    if (failure) throw failure;
    return "";
  };
}
function tmuxQuery(...args) {
  return execFileSync(tmux, ["-L", socket, "-f", "/dev/null", ...args], {
    env: environment,
    encoding: "utf8",
  }).trim();
}
try {
  browser = await chromium.launch({
    executablePath:
      process.env.CHROME_EXECUTABLE ||
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: true,
  });
  const context = await browser.newContext({
    viewport: { width: 1100, height: 760 },
  });
  await context.exposeBinding(
    "__native",
    async (_source, operation, options) => {
      if (operation === "call") {
        assert(
          [helper, "/bin/zsh", tmux].includes(options.command),
          `Unexpected command ${options.command}`,
        );
        const child = spawn(options.command, mapArgs(options.arguments), {
          cwd: options.workdir || home,
          env: {
            ...environment,
            ...options.environment,
            HOME: home,
            ZDOTDIR: home,
          },
          stdio: ["pipe", "pipe", "pipe"],
        });
        const id = nextId++;
        if (process.env.DEBUG_TERMINAL_PROOF)
          console.log("CALL", id, options.command, options.arguments);
        child.stdout.setEncoding("utf8");
        child.stderr.setEncoding("utf8");
        const result = new Promise((resolve, reject) => {
          child.once("error", reject);
          child.once("exit", (code, signal) =>
            resolve({ exitCode: code ?? (signal === "SIGTERM" ? 143 : 1) }),
          );
        });
        result.catch(() => {});
        processes.set(id, {
          child,
          result,
          command: options.command,
          readers: {
            stdout: boundedReader(child.stdout),
            stderr: boundedReader(child.stderr),
          },
        });
        await new Promise((resolve, reject) => {
          child.once("spawn", resolve);
          child.once("error", reject);
        });
        return id;
      }
      const item = processes.get(options.id);
      assert(item, "Unknown test process");
      if (operation === "read") {
        const data = await item.readers[options.pipe]();
        if (process.env.DEBUG_TERMINAL_PROOF)
          console.log(
            "READ",
            options.id,
            options.pipe,
            JSON.stringify(data.slice(0, 150)),
          );
        return data;
      }
      if (operation === "write")
        return new Promise((resolve, reject) =>
          item.child.stdin.write(options.data, (error) =>
            error ? reject(error) : resolve(),
          ),
        );
      if (operation === "wait") return item.result;
      if (operation === "kill") {
        item.child.kill("SIGTERM");
        return;
      }
      throw new Error("Unknown adapter operation");
    },
  );
  await context.addInitScript(
    ({ home, helper }) => {
      const prefs = {
        "zen.terminal.containerRecipes": JSON.stringify({
          1: {
            kind: "terminal",
            recipe: {
              steps: [
                {
                  id: "marker",
                  command: 'printf "startup\\n" >> "$HOME/startup-count"',
                },
              ],
            },
          },
        }),
      };
      window.Services = {
        appinfo: { OS: "Darwin", accessibilityEnabled: false },
        prefs: {
          getStringPref: (key, fallback) =>
            localStorage.getItem(key) ?? prefs[key] ?? fallback,
          setStringPref: (key, value) => localStorage.setItem(key, value),
          savePrefFile() {},
        },
        env: { get: (key) => ({ HOME: home, SHELL: "/bin/zsh" })[key] || "" },
        uuid: { generateUUID: () => `{${crypto.randomUUID()}}` },
        dirsvc: {
          get: () => ({
            parent: {
              path: helper,
              append() {},
              exists: () => !sessionStorage.getItem("testMissingHelper"),
            },
          }),
        },
      };
      window.Ci = { nsIFile: {} };
      const Subprocess = {
        call: async (options) => {
          if (
            sessionStorage.getItem("testNoTmux") &&
            options.command === "/bin/zsh" &&
            options.arguments?.[1] === "command -v tmux"
          ) {
            options = {
              ...options,
              environment: { ...options.environment, ZEN_TEST_NO_TMUX: "1" },
            };
          }
          const id = await window.__native("call", options);
          const pipe = (name) => ({
            readString: () => window.__native("read", { id, pipe: name }),
          });
          return {
            stdout: pipe("stdout"),
            stderr: pipe("stderr"),
            stdin: { write: (data) => window.__native("write", { id, data }) },
            wait: () => window.__native("wait", { id }),
            kill: () => {
              window.__native("kill", { id }).catch(() => {});
            },
          };
        },
      };
      window.ChromeUtils = {
        importESModule: (name) =>
          name.includes("Subprocess")
            ? { Subprocess }
            : {
                setTimeout: window.setTimeout.bind(window),
                clearTimeout: window.clearTimeout.bind(window),
              },
      };
      // Capture the unmodified xterm instance for buffer assertions, not input injection.
      let Terminal;
      Object.defineProperty(window, "Terminal", {
        configurable: true,
        get: () => Terminal,
        set: (value) => {
          Terminal = new Proxy(value, {
            construct(target, args) {
              const instance = Reflect.construct(target, args);
              window.__testTerminal = instance;
              return instance;
            },
          });
        },
      });
    },
    { home, helper },
  );
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(error.message));
  const session = "browser-proof";
  const url = `http://127.0.0.1:${server.address().port}/terminal.xhtml?userContextId=1&container=proof&session=${session}`;
  const status = () => page.locator("#zen-terminal-status-text").textContent();
  const ready = () =>
    page.waitForFunction(() =>
      document
        .getElementById("zen-terminal-surface")
        .hasAttribute("terminal-ready"),
    );
  const content = () =>
    page.evaluate(() => {
      const b = window.__testTerminal.buffer.active;
      return Array.from(
        { length: b.length },
        (_, i) => b.getLine(i)?.translateToString(true) || "",
      ).join("\n");
    });
  async function command(text) {
    await page.locator(".xterm-helper-textarea").focus();
    await page.keyboard.type(text);
    await page.keyboard.press("Enter");
  }
  async function file(name, expected) {
    let actual;
    for (let i = 0; i < 200; i++) {
      try {
        actual = await readFile(path.join(home, name), "utf8");
        if (actual === expected) return;
      } catch {}
      await new Promise((r) => setTimeout(r, 25));
    }
    assert.equal(actual, expected);
  }
  async function check(name, fn) {
    const started = Date.now();
    await fn();
    checks.push({ name, passed: true, durationMs: Date.now() - started });
    console.log(`PASS ${name}`);
  }
  await page.goto(url);
  await ready();
  await check(
    "Real helper and tmux start the rendered production terminal page",
    async () => {
      assert.match(await status(), /session saved/);
      await file("startup-count", "startup\n");
      assert(processes.size > 3);
    },
  );
  const panePid = tmuxQuery(
    "display-message",
    "-p",
    "-t",
    `=zt_${session}`,
    "#{pane_pid}",
  );
  await check(
    "Rapid repeated keyboard letters are delivered exactly once",
    async () => {
      const text = "aaaabbbbccccdddd".repeat(24);
      await command(`printf '%s\\n' '${text}' > "$HOME/keyboard-proof"`);
      await file("keyboard-proof", text + "\n");
    },
  );
  await check(
    "Unicode keyboard insertion and terminal paste preserve exact text",
    async () => {
      await page.keyboard.type("printf '%s\\n' '");
      await page.keyboard.insertText("café 世界 🙂");
      await page.keyboard.type('\' > "$HOME/unicode-proof"');
      await page.keyboard.press("Enter");
      await file("unicode-proof", "café 世界 🙂\n");
      const text = "paste café 世界 🙂 " + "z".repeat(4096);
      await page.evaluate((text) => {
        const data = new DataTransfer();
        data.setData(
          "text/plain",
          `printf '%s\\n' '${text}' > "$HOME/paste-proof"`,
        );
        document.querySelector(".xterm-helper-textarea").dispatchEvent(
          new ClipboardEvent("paste", {
            clipboardData: data,
            bubbles: true,
            cancelable: true,
          }),
        );
      }, text);
      await page.keyboard.press("Enter");
      await file("paste-proof", text + "\n");
    },
  );
  await check("Actual stty follows visible terminal resizing", async () => {
    await page.setViewportSize({ width: 840, height: 560 });
    await page.waitForTimeout(300);
    const dims = await page.evaluate(() => ({
      rows: __testTerminal.rows,
      cols: __testTerminal.cols,
    }));
    await command('stty size > "$HOME/size-proof"');
    await file("size-proof", `${dims.rows} ${dims.cols}\n`);
  });
  await check(
    "Large output stays bounded and the last rendered line is present",
    async () => {
      await command(
        '/usr/bin/jot -w LINE%05d 12050 0; printf "OUTPUT_FINISHED\\n"',
      );
      await page.waitForFunction(
        () => {
          const b = __testTerminal.buffer.active;
          return Array.from(
            { length: b.length },
            (_, i) => b.getLine(i)?.translateToString(true) || "",
          ).some((line) => line === "OUTPUT_FINISHED");
        },
        {},
        { timeout: 30000 },
      );
      assert((await content()).includes("LINE12049"));
      const size = await page.evaluate(() => ({
        length: __testTerminal.buffer.active.length,
        rows: __testTerminal.rows,
      }));
      assert(size.length <= 10000 + size.rows);
      await page.screenshot({
        path: path.join(proof, "terminal-page-output.png"),
      });
    },
  );
  await check(
    "Reload reconnects to the same shell and does not repeat startup",
    async () => {
      await page.reload();
      await ready();
      assert.match(await status(), /reconnected/);
      assert.equal(
        tmuxQuery(
          "display-message",
          "-p",
          "-t",
          `=zt_${session}`,
          "#{pane_pid}",
        ),
        panePid,
      );
      await file("startup-count", "startup\n");
      await command('printf "after-reload\\n" > "$HOME/reload-proof"');
      await file("reload-proof", "after-reload\n");
    },
  );
  await check(
    "Disconnect offers reconnect without deleting the saved shell",
    async () => {
      const active = [...processes.values()].filter(
        (p) =>
          p.command === helper &&
          p.child.exitCode === null &&
          p.child.signalCode === null,
      );
      assert.equal(active.length, 1, "Reload must detach its previous helper");
      active[0].child.kill("SIGTERM");
      await page.waitForFunction(() =>
        document
          .getElementById("zen-terminal-status-text")
          .textContent.includes("disconnected"),
      );
      await page.locator("#zen-terminal-reconnect").click();
      await ready();
      assert.match(await status(), /reconnected/);
      assert.equal(
        tmuxQuery(
          "display-message",
          "-p",
          "-t",
          `=zt_${session}`,
          "#{pane_pid}",
        ),
        panePid,
      );
      await file("startup-count", "startup\n");
    },
  );
  await check(
    "Missing helper shows a recoverable error and preserves saved work",
    async () => {
      await page.evaluate(() =>
        sessionStorage.setItem("testMissingHelper", "1"),
      );
      await page.reload();
      await page.waitForFunction(() =>
        document
          .getElementById("zen-terminal-status-text")
          .textContent.includes("could not connect"),
      );
      assert.equal(
        await page.locator("#zen-terminal-reconnect").isVisible(),
        true,
      );
      assert((await content()).includes("helper is missing"));
      await page.screenshot({
        path: path.join(proof, "terminal-page-recoverable-error.png"),
      });
      await page.evaluate(() => sessionStorage.removeItem("testMissingHelper"));
      await page.locator("#zen-terminal-reconnect").click();
      await ready();
      assert.equal(
        tmuxQuery(
          "display-message",
          "-p",
          "-t",
          `=zt_${session}`,
          "#{pane_pid}",
        ),
        panePid,
      );
    },
  );
  await page.screenshot({
    path: path.join(proof, "terminal-page-reconnected.png"),
  });
  await check(
    "Without tmux, live resizing and real scrollback remain usable and bounded",
    async () => {
      await page.evaluate(() => sessionStorage.setItem("testNoTmux", "1"));
      await page.goto(
        url.replace("session=browser-proof", "session=plain-proof"),
      );
      await ready();
      assert.match(await status(), /not saved/);
      await page.setViewportSize({ width: 960, height: 660 });
      await page.waitForTimeout(300);
      const dims = await page.evaluate(() => ({
        rows: __testTerminal.rows,
        cols: __testTerminal.cols,
      }));
      await command('stty size > "$HOME/plain-size-proof"');
      await file("plain-size-proof", `${dims.rows} ${dims.cols}\n`);
      await command(
        '/usr/bin/jot -w PLAIN%05d 12050 0; printf "PLAIN_FINISHED\\n"',
      );
      await page.waitForFunction(
        () => {
          const b = __testTerminal.buffer.active;
          return Array.from(
            { length: b.length },
            (_, i) => b.getLine(i)?.translateToString(true) || "",
          ).some((line) => line === "PLAIN_FINISHED");
        },
        {},
        { timeout: 30000 },
      );
      const before = await page.evaluate(() => ({
        length: __testTerminal.buffer.active.length,
        rows: __testTerminal.rows,
        y: __testTerminal.buffer.active.viewportY,
      }));
      assert(before.length > 10000);
      assert(before.length <= 10000 + before.rows);
      await page.locator("#zen-terminal-output").hover();
      await page.mouse.wheel(0, -1200);
      await page.waitForFunction(
        (y) => __testTerminal.buffer.active.viewportY < y,
        before.y,
      );
      await page.screenshot({
        path: path.join(proof, "terminal-page-plain-scrollback.png"),
      });
      await page.mouse.wheel(0, 100000);
      await command('printf "still-responsive\\n" > "$HOME/responsive-proof"');
      await file("responsive-proof", "still-responsive\n");
    },
  );
  assert.deepEqual(errors, []);
  await writeFile(
    path.join(proof, "terminal-page-results.json"),
    JSON.stringify(
      {
        scope:
          "Real production terminal page/xterm/CSS in Chromium with test-only Firefox service adapter; real native PTY helper and isolated tmux. NOT installed Zen/native menu proof.",
        date: new Date().toISOString(),
        checks,
        pageErrors: errors,
      },
      null,
      2,
    ) + "\n",
  );
  console.log(`PASS ${checks.length} rendered-page checks; evidence: ${proof}`);
} catch (error) {
  await writeFile(
    path.join(proof, "terminal-page-results.json"),
    JSON.stringify(
      {
        scope: "Terminal-page adapter test, not native Zen",
        date: new Date().toISOString(),
        checks,
        error: error.stack,
        pageErrors: errors,
      },
      null,
      2,
    ) + "\n",
  );
  throw error;
} finally {
  await browser?.close();
  for (const { child } of processes.values())
    if (child.exitCode === null && child.signalCode === null)
      child.kill("SIGTERM");
  try {
    execFileSync(tmux, ["-L", socket, "kill-server"], {
      env: environment,
      stdio: "ignore",
    });
  } catch {}
  await new Promise((resolve) => server.close(resolve));
  await Promise.allSettled([...processes.values()].map((item) => item.result));
  await rm(home, {
    recursive: true,
    force: true,
    maxRetries: 10,
    retryDelay: 100,
  });
}
