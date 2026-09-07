/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/**
 * Turns the simple ordered commands shown in Settings into one command that a
 * shell can execute safely. In particular, commands after an SSH connection
 * are handed to OpenSSH as its remote command. OpenSSH therefore decides when
 * the connection is ready; Zen never guesses from timers or prompt text.
 */

export class TerminalRecipeError extends Error {
  constructor(message, stepIndex = -1) {
    super(message);
    this.name = "TerminalRecipeError";
    this.stepIndex = stepIndex;
  }
}

const SSH_OPTIONS_WITH_VALUE = new Set([
  "-B",
  "-b",
  "-c",
  "-D",
  "-E",
  "-e",
  "-F",
  "-I",
  "-i",
  "-J",
  "-L",
  "-l",
  "-m",
  "-O",
  "-o",
  "-p",
  "-Q",
  "-R",
  "-S",
  "-W",
  "-w",
]);

function shellQuote(value) {
  return `'${String(value).replaceAll("'", "'\\''")}'`;
}

function commandFromStep(step) {
  if (typeof step === "string") {
    return step.trim();
  }
  if (step && typeof step === "object") {
    return String(step.command || "").trim();
  }
  return "";
}

export function cleanTerminalRecipeSteps(steps) {
  if (!Array.isArray(steps)) {
    return [];
  }

  return steps
    .map(commandFromStep)
    .filter(Boolean)
    .map((command, index) => {
      if (/[\r\n]/u.test(command)) {
        throw new TerminalRecipeError(
          "Each startup step must be one command on one line.",
          index,
        );
      }
      return command;
    });
}

function splitShellWords(command, stepIndex) {
  const words = [];
  let word = "";
  let quote = "";
  let escaping = false;
  let started = false;

  for (let index = 0; index < command.length; index++) {
    const character = command[index];

    if (escaping) {
      word += character;
      escaping = false;
      started = true;
      continue;
    }

    if (quote === "'") {
      if (character === "'") {
        quote = "";
      } else {
        word += character;
      }
      started = true;
      continue;
    }

    if (quote === '"') {
      if (character === '"') {
        quote = "";
      } else if (character === "\\") {
        escaping = true;
      } else if (character === "$" || character === "`") {
        throw new TerminalRecipeError(
          "SSH connection steps cannot contain shell substitutions.",
          stepIndex,
        );
      } else {
        word += character;
      }
      started = true;
      continue;
    }

    if (character === "\\") {
      escaping = true;
      started = true;
    } else if (character === "'" || character === '"') {
      quote = character;
      started = true;
    } else if (/\s/u.test(character)) {
      if (started) {
        words.push(word);
        word = "";
        started = false;
      }
    } else if (";&|<>`$(){}".includes(character)) {
      throw new TerminalRecipeError(
        "Keep SSH connection steps simple. Put the remote command in the next step.",
        stepIndex,
      );
    } else {
      word += character;
      started = true;
    }
  }

  if (escaping || quote) {
    throw new TerminalRecipeError(
      "The SSH connection step has an unfinished quote or escape.",
      stepIndex,
    );
  }
  if (started) {
    words.push(word);
  }
  return words;
}

function isSshExecutable(word) {
  return word === "ssh" || word === "/usr/bin/ssh";
}

function validateSshOptionValue(option, value, stepIndex) {
  if (["-O", "-Q", "-W"].includes(option)) {
    throw new TerminalRecipeError(
      `${option} cannot be used before later startup steps.`,
      stepIndex,
    );
  }
  if (option !== "-o") {
    return;
  }

  const setting = value.trim().toLowerCase();
  const match = /^([^\s=]+)(?:\s*=\s*|\s+)(.*)$/u.exec(setting);
  const key = match?.[1];
  const optionValue = match?.[2]?.trim();
  if (
    key === "remotecommand" ||
    (key === "sessiontype" && optionValue !== "default") ||
    (key === "requesttty" && optionValue === "no") ||
    (key === "stdinnull" && optionValue === "yes") ||
    (key === "forkafterauthentication" && optionValue === "yes")
  ) {
    throw new TerminalRecipeError(
      `${value} conflicts with later startup steps.`,
      stepIndex,
    );
  }
}

export function parseSshConnectionStep(command, stepIndex = -1) {
  if (!/^(?:ssh|\/usr\/bin\/ssh)(?:\s|$)/u.test(command.trim())) {
    return null;
  }

  const words = splitShellWords(command, stepIndex);
  if (!isSshExecutable(words[0])) {
    return null;
  }

  let destinationIndex = -1;
  let optionsEnded = false;
  for (let index = 1; index < words.length; index++) {
    const word = words[index];
    if (!optionsEnded && word === "--") {
      optionsEnded = true;
      continue;
    }
    if (!optionsEnded && word.startsWith("-") && word !== "-") {
      // OpenSSH accepts combined flags (for example -vvN) and attached
      // values (-vp2222). Walk the flags until a value-taking option consumes
      // the rest; never mistake its value for more flags.
      for (let offset = 1; offset < word.length; offset++) {
        const option = `-${word[offset]}`;
        if (
          ["-G", "-N", "-O", "-Q", "-T", "-V", "-W", "-s", "-f", "-n"].includes(
            option,
          )
        ) {
          throw new TerminalRecipeError(
            `${option} cannot be used before later startup steps.`,
            stepIndex,
          );
        }
        if (SSH_OPTIONS_WITH_VALUE.has(option)) {
          const attached = word.slice(offset + 1);
          const value = attached || words[++index];
          if (!value) {
            throw new TerminalRecipeError(
              `${option} needs a value in the SSH connection step.`,
              stepIndex,
            );
          }
          validateSshOptionValue(option, value, stepIndex);
          break;
        }
        if (!"46AaCgKkMqtvXxYy".includes(word[offset])) {
          throw new TerminalRecipeError(
            `Unsupported SSH option ${option}.`,
            stepIndex,
          );
        }
      }
      continue;
    }

    destinationIndex = index;
    break;
  }

  if (destinationIndex < 0 || !words[destinationIndex].trim()) {
    throw new TerminalRecipeError(
      "The SSH connection step needs a computer name or address.",
      stepIndex,
    );
  }
  if (destinationIndex !== words.length - 1) {
    throw new TerminalRecipeError(
      "Put the remote command in the next startup step.",
      stepIndex,
    );
  }

  return {
    executable: words[0],
    argumentsBeforeDestination: words.slice(1, destinationIndex),
    destination: words[destinationIndex],
  };
}

function compileFrom(commands, startIndex = 0) {
  const compiled = [];
  // Evaluate each row separately in the current shell. Quoting keeps comments
  // and operators inside their row; using the same shell preserves cd/export.
  // Keep a standalone command unchanged for existing one-command recipes.
  const localStep = (command) =>
    commands.length - startIndex === 1
      ? command
      : `eval ${shellQuote(command)}`;

  for (let index = startIndex; index < commands.length; index++) {
    const command = commands[index];
    if (index === commands.length - 1) {
      compiled.push(localStep(command));
      continue;
    }

    const ssh = parseSshConnectionStep(command, index);
    if (!ssh) {
      compiled.push(localStep(command));
      continue;
    }

    const remoteScript = compileFrom(commands, index + 1);
    const remoteShellCommand = `exec "\${SHELL:-/bin/sh}" -lic ${shellQuote(
      remoteScript,
    )}`;
    const sshCommand = [
      ssh.executable,
      "-tt",
      ...ssh.argumentsBeforeDestination,
      ssh.destination,
      remoteShellCommand,
    ]
      .map(shellQuote)
      .join(" ");
    compiled.push(sshCommand);
    break;
  }

  return compiled.join(" && ");
}

export function compileTerminalRecipeSteps(steps) {
  const commands = cleanTerminalRecipeSteps(steps);
  return commands.length ? compileFrom(commands) : "";
}
