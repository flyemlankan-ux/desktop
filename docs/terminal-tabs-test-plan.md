# Zen Terminal tabs: real test plan

## Simple idea

There are three proof levels.

1. **Code proof** — checks the files are wired correctly.
2. **Build proof** — checks GitHub can build a real Mac app.
3. **Human app proof** — opens the Mac app and checks it feels right.

Code proof is not enough. The final test is opening the app and using it like a normal terminal.

## Code proof

Run locally:

```bash
node scripts/terminal-tabs/check-terminal-tabs.mjs
```

This checks:

- New Terminal Tab is wired into Zen.
- The terminal page is packaged into Zen.
- The terminal shell code exists.
- Mac pseudo-terminal support is wired.
- key input and paste are wired.
- terminal closes when the tab closes.

## Cloud proof

GitHub PR proof must pass:

```text
https://github.com/flyemlankan-ux/desktop/pull/1
```

This checks:

- Firefox source downloads.
- Zen imports our source into Firefox.
- Zen lint accepts the files.

## Real app proof

After the Mac DMG is built, open the app and test this checklist.

### Terminal tab opens

- Open the Zen-based app.
- Use **New Terminal Tab**.
- Expected: a new tab opens with terminal content.

### Shell starts

- The terminal should show that it connected to `/bin/zsh` or the user's shell.
- Expected: no crash, no blank page.

### Basic commands

Type:

```bash
pwd
```

Expected: it prints the current folder.

Type:

```bash
echo hello
```

Expected: it prints `hello`.

Type:

```bash
whoami
```

Expected: it prints the Mac username.

### Keyboard handling

- Backspace deletes correctly.
- Arrow up recalls previous command.
- Ctrl-C interrupts a running command.
- Paste sends text into the terminal.

### SSH test

Type:

```bash
ssh -o ConnectTimeout=40 -o ServerAliveInterval=15 -o ServerAliveCountMax=6 chubs@100.92.30.93 'hostname'
```

Expected: Chubs replies with its hostname.

### Agent launch smoke test

Type:

```bash
claude --version
```

and:

```bash
codex --version
```

Expected: installed tools print their versions, or the shell says they are missing.

### Close cleanup

- Open a terminal tab.
- Run a long command like:

```bash
sleep 60
```

- Close the tab.

Expected: the shell process should close with the tab.

## Known weakness in this slice

This is not a full xterm-level terminal yet.

That means rich full-screen terminal apps may not draw perfectly yet.

The next stronger version should use a true terminal grid, which means a proper screen model like Terminal.app uses.
