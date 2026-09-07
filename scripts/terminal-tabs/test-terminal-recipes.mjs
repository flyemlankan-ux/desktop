#!/usr/bin/env node
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

import assert from "node:assert/strict";
import { execFileSync, execSync, spawnSync } from "node:child_process";
import {
  chmodSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

import {
  ZEN_TERMINAL_RECIPE_VERSION,
  normalizeTerminalRecipe,
  normalizeTerminalContainerRecord,
  setTerminalContainerRecipe,
} from "../../src/zen/terminal/ZenTerminalContainerStore.mjs";
import {
  TerminalRecipeError,
  compileTerminalRecipeSteps,
  parseSshConnectionStep,
} from "../../src/zen/terminal/ZenTerminalRecipeRunner.mjs";

const tests = [];

function test(name, callback) {
  tests.push([name, callback]);
}

function expectRecipeError(callback, messagePattern) {
  assert.throws(callback, (error) => {
    assert.ok(error instanceof TerminalRecipeError);
    assert.match(error.message, messagePattern);
    return true;
  });
}

test("recipe data version is 3", () => {
  assert.equal(ZEN_TERMINAL_RECIPE_VERSION, 3);
});

test("legacy string becomes one ordered step", () => {
  assert.deepEqual(normalizeTerminalRecipe("claude"), {
    type: "ordered-steps",
    command: "claude",
    steps: [{ id: "step-1", command: "claude" }],
  });
});

test("legacy v2 command becomes one ordered step", () => {
  assert.deepEqual(
    normalizeTerminalRecipe({
      type: "single-command",
      command: " cd ~/work && codex ",
      steps: [],
    }),
    {
      type: "ordered-steps",
      command: "cd ~/work && codex",
      steps: [{ id: "step-1", command: "cd ~/work && codex" }],
    },
  );
});

test("a normalised legacy container reports the current v3 shape", () => {
  assert.deepEqual(
    normalizeTerminalContainerRecord({
      version: 2,
      kind: "terminal",
      recipe: { type: "single-command", command: "codex", steps: [] },
    }),
    {
      version: 3,
      kind: "terminal",
      recipe: {
        type: "ordered-steps",
        command: "codex",
        steps: [{ id: "step-1", command: "codex" }],
      },
    },
  );
});

test("saving writes v3 while keeping one-command backwards compatibility", () => {
  let saved = "{}";
  globalThis.Services = {
    prefs: {
      getStringPref: () => saved,
      setStringPref: (_name, value) => {
        saved = value;
      },
    },
  };

  setTerminalContainerRecipe(7, {
    recipe: {
      steps: [{ id: "launch", command: "claude" }],
    },
  });

  assert.deepEqual(JSON.parse(saved)["7"], {
    version: 3,
    kind: "terminal",
    recipe: {
      type: "ordered-steps",
      command: "claude",
      steps: [{ id: "launch", command: "claude" }],
    },
  });
  delete globalThis.Services;
});

test("stored ordered steps win over the legacy command", () => {
  assert.deepEqual(
    normalizeTerminalRecipe({
      type: "ordered-steps",
      command: "old command",
      steps: [
        { id: "connect", command: " ssh chubs " },
        " claude ",
        { id: "blank", command: " " },
      ],
    }),
    {
      type: "ordered-steps",
      command: "",
      steps: [
        { id: "connect", command: "ssh chubs" },
        { id: "step-2", command: "claude" },
      ],
    },
  );
});

test("blank and malformed recipes become a plain shell", () => {
  assert.deepEqual(normalizeTerminalRecipe(null), {
    type: "ordered-steps",
    command: "",
    steps: [],
  });
  assert.deepEqual(
    normalizeTerminalRecipe({ command: "", steps: [null, {}, " "] }),
    {
      type: "ordered-steps",
      command: "",
      steps: [],
    },
  );
});

test("duplicate step ids are repaired without changing order", () => {
  assert.deepEqual(
    normalizeTerminalRecipe({
      steps: [
        { id: "same", command: "one" },
        { id: "same", command: "two" },
        { id: "same", command: "three" },
      ],
    }).steps,
    [
      { id: "same", command: "one" },
      { id: "same-2", command: "two" },
      { id: "same-3", command: "three" },
    ],
  );
});

test("ordinary local steps run in order and stop on failure", () => {
  const command = compileTerminalRecipeSteps([
    "printf first",
    "false",
    "printf never",
  ]);
  assert.equal(
    command,
    "eval 'printf first' && eval 'false' && eval 'printf never'",
  );
  assert.throws(() =>
    execFileSync("/bin/sh", ["-c", command], { encoding: "utf8" }),
  );
  const output = execFileSync("/bin/sh", ["-c", `${command} || true`], {
    encoding: "utf8",
  });
  assert.equal(output, "first");
});

test("SSH options and destination are parsed without a remote command", () => {
  assert.deepEqual(
    parseSshConnectionStep(
      "ssh -p 2222 -i '~/.ssh/work key' person@example.test",
    ),
    {
      executable: "ssh",
      argumentsBeforeDestination: ["-p", "2222", "-i", "~/.ssh/work key"],
      destination: "person@example.test",
    },
  );
});

test("SSH plus Claude is compiled as one remote SSH command", () => {
  const command = compileTerminalRecipeSteps([
    "ssh chubs@100.92.30.93",
    "claude --dangerously-skip-permissions",
  ]);
  assert.match(command, /^'ssh' '-tt' 'chubs@100\.92\.30\.93' /u);
  assert.match(command, /SHELL:-\/bin\/sh/u);
  assert.match(command, /claude --dangerously-skip-permissions/u);
  execFileSync("/bin/sh", ["-n", "-c", command]);
});

test("forced tty is inserted before SSH options and the -- marker", () => {
  const command = compileTerminalRecipeSteps([
    "ssh -p 2222 -- person@example.test",
    "claude",
  ]);
  assert.match(
    command,
    /^'ssh' '-tt' '-p' '2222' '--' 'person@example\.test' /u,
  );
});

test("a connection step that already has a remote command is rejected", () => {
  expectRecipeError(
    () =>
      compileTerminalRecipeSteps([
        "ssh chubs hostname",
        "claude --dangerously-skip-permissions",
      ]),
    /Put the remote command in the next startup step/u,
  );
});

test("SSH shell operators and substitutions are rejected", () => {
  for (const command of [
    "ssh chubs; touch /tmp/no",
    "ssh $(printf chubs)",
    'ssh "$HOST"',
    "ssh chubs | cat",
  ]) {
    expectRecipeError(
      () => compileTerminalRecipeSteps([command, "claude"]),
      /SSH|remote command/u,
    );
  }
});

test("conflicting SSH modes are rejected before later steps", () => {
  for (const option of [
    "-T",
    "-N",
    "-s",
    "-G",
    "-V",
    "-f",
    "-n",
    "-vvN",
    "-vT",
    "-vfn",
  ]) {
    expectRecipeError(
      () => compileTerminalRecipeSteps([`ssh ${option} chubs`, "claude"]),
      /cannot be used/u,
    );
  }
});

test("SSH config that conflicts with a remote recipe is rejected", () => {
  for (const command of [
    "ssh -o RemoteCommand=hostname chubs",
    "ssh -oRemoteCommand=hostname chubs",
    "ssh -o SessionType=none chubs",
    "ssh -o RequestTTY=no chubs",
    "ssh -o 'RemoteCommand hostname' chubs",
    "ssh -voRemoteCommand=hostname chubs",
    "ssh -o 'SessionType subsystem' chubs",
    "ssh -o 'RequestTTY = no' chubs",
    "ssh -o 'StdinNull yes' chubs",
    "ssh -oForkAfterAuthentication=yes chubs",
  ]) {
    expectRecipeError(
      () => compileTerminalRecipeSteps([command, "claude"]),
      /conflicts with later startup steps/u,
    );
  }
});

test("remote command text cannot escape and execute on the local machine", () => {
  const directory = mkdtempSync(path.join(tmpdir(), "zen-recipe-"));
  const fakeSsh = path.join(directory, "ssh");
  const argumentsFile = path.join(directory, "arguments.txt");
  const escapedFile = path.join(directory, "escaped-locally");
  writeFileSync(
    fakeSsh,
    `#!/bin/sh\nprintf '%s\\n' \"$@\" > ${JSON.stringify(argumentsFile)}\n`,
  );
  chmodSync(fakeSsh, 0o755);

  const remoteStep = `printf safe; touch ${escapedFile}`;
  const command = compileTerminalRecipeSteps(["ssh chubs", remoteStep]);
  execSync(command, {
    env: { ...process.env, PATH: `${directory}:${process.env.PATH}` },
    stdio: "pipe",
  });

  assert.equal(
    readFileSync(argumentsFile, "utf8").split("\n").filter(Boolean)[0],
    "-tt",
  );
  assert.match(readFileSync(argumentsFile, "utf8"), /printf safe; touch/u);
  assert.throws(() => readFileSync(escapedFile));
});

test("an SSH connection failure cannot run the following step locally", () => {
  const directory = mkdtempSync(path.join(tmpdir(), "zen-recipe-failure-"));
  const fakeSsh = path.join(directory, "ssh");
  const localMarker = path.join(directory, "must-not-exist");
  writeFileSync(fakeSsh, "#!/bin/sh\nexit 255\n");
  chmodSync(fakeSsh, 0o755);

  const command = compileTerminalRecipeSteps([
    "ssh unavailable.example",
    `touch ${localMarker}`,
  ]);
  assert.throws(() =>
    execSync(command, {
      env: { ...process.env, PATH: `${directory}:${process.env.PATH}` },
      stdio: "pipe",
    }),
  );
  assert.throws(() => readFileSync(localMarker));
});

test("a final SSH step remains an ordinary interactive connection", () => {
  assert.equal(compileTerminalRecipeSteps(["ssh chubs"]), "ssh chubs");
});

test("empty rows are ignored and multi-line rows are rejected", () => {
  assert.equal(
    compileTerminalRecipeSteps(["", { command: "pwd" }, "   "]),
    "pwd",
  );
  expectRecipeError(
    () => compileTerminalRecipeSteps(["pwd\nwhoami"]),
    /one command on one line/u,
  );
});

test("each row keeps semicolons, OR operators and comments inside its boundary", () => {
  for (const shell of ["/bin/sh", "/bin/zsh", "/bin/bash"]) {
    for (const laterStep of [
      "printf first; printf escaped",
      "false || printf escaped",
    ]) {
      const result = spawnSync(
        shell,
        ["-c", compileTerminalRecipeSteps(["false", laterStep])],
        { encoding: "utf8" },
      );
      assert.notEqual(result.status, 0, shell);
      assert.equal(result.stdout, "", shell);
    }
    const command = compileTerminalRecipeSteps([
      "printf first # this comment must not swallow the next row",
      "printf second",
      "false # neither may this comment swallow failure handling",
      "printf never",
    ]);
    const result = spawnSync(shell, ["-c", command], { encoding: "utf8" });
    assert.notEqual(result.status, 0, shell);
    assert.equal(result.stdout, "firstsecond", shell);
  }
});

test("rows preserve working directory, exports, quotes and shell variables", () => {
  const directory = mkdtempSync(path.join(tmpdir(), "zen-recipe-state-"));
  try {
    for (const shell of ["/bin/sh", "/bin/zsh", "/bin/bash"]) {
      const command = compileTerminalRecipeSteps([
        `cd '${directory}'`,
        "export ZEN_RECIPE_TEST='hello world'",
        'printf \'%s:%s\' "$PWD" "$ZEN_RECIPE_TEST"',
      ]);
      assert.equal(
        execFileSync(shell, ["-c", command], { encoding: "utf8" }),
        `${directory}:hello world`,
      );
    }
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("safe combined SSH flags and attached values are preserved", () => {
  assert.deepEqual(
    parseSshConnectionStep("ssh -vvAp2222 -o 'RequestTTY force' host"),
    {
      executable: "ssh",
      argumentsBeforeDestination: ["-vvAp2222", "-o", "RequestTTY force"],
      destination: "host",
    },
  );
  for (const command of [
    "ssh ''",
    'ssh "   "',
    "ssh -p",
    "ssh -vZ host",
    "ssh -vWtarget host",
  ]) {
    expectRecipeError(
      () => compileTerminalRecipeSteps([command, "printf never"]),
      /needs|Unsupported|cannot/u,
    );
  }
});

test("fake SSH executes following rows only in the remote shell, including nested connections", () => {
  const directory = mkdtempSync(path.join(tmpdir(), "zen-recipe-remote-"));
  try {
    const fakeSsh = path.join(directory, "ssh");
    // The fixture supports the compiler's simple -tt host remote-command form.
    // It replaces the remote login-shell wrapper with a disposable local shell,
    // avoiding all real network connections and user login configuration.
    writeFileSync(
      fakeSsh,
      `#!/bin/sh
[ "$1" = "-tt" ] || exit 90
shift
host=$1
shift
export ZEN_FAKE_HOST="$host"
exec "$ZEN_FAKE_SHELL" -c "$1"
`,
    );
    chmodSync(fakeSsh, 0o755);
    const fakeShell = path.join(directory, "remote-shell");
    writeFileSync(
      fakeShell,
      '#!/bin/sh\n[ "$1" = "-lic" ] && shift\nexec /bin/sh -c "$1"\n',
    );
    chmodSync(fakeShell, 0o755);
    const env = {
      ...process.env,
      PATH: `${directory}:${process.env.PATH}`,
      SHELL: fakeShell,
      ZEN_FAKE_SHELL: "/bin/sh",
    };
    const command = compileTerminalRecipeSteps([
      "ssh outer",
      "printf '%s:' \"$ZEN_FAKE_HOST\" # remote comment",
      "ssh inner",
      "export ZEN_REMOTE_VALUE=kept",
      'printf \'%s:%s\' "$ZEN_FAKE_HOST" "$ZEN_REMOTE_VALUE"',
    ]);
    assert.equal(
      execFileSync("/bin/sh", ["-c", command], { env, encoding: "utf8" }),
      "outer:inner:kept",
    );
    const failed = spawnSync(
      "/bin/sh",
      [
        "-c",
        compileTerminalRecipeSteps([
          "ssh outer",
          "false",
          "printf never; printf escaped",
        ]),
      ],
      { env, encoding: "utf8" },
    );
    assert.notEqual(failed.status, 0);
    assert.equal(failed.stdout, "");
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

let failures = 0;
for (const [name, callback] of tests) {
  try {
    await callback();
    console.log(`✓ ${name}`);
  } catch (error) {
    failures++;
    console.error(`✗ ${name}`);
    console.error(error);
  }
}

if (failures) {
  console.error(`\n${failures} terminal recipe test(s) failed.`);
  process.exit(1);
}

console.log(`\n${tests.length} terminal recipe tests passed.`);
