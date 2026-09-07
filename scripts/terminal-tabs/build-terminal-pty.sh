#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
OUT=${1:-"$ROOT/build/terminal-native/zen-terminal-pty"}
mkdir -p "$(dirname -- "$OUT")"
case "${ZEN_TERMINAL_ARCH:-$(uname -m)}" in
  aarch64|arm64) ARCH=arm64 ;;
  x86_64) ARCH=x86_64 ;;
  *) echo "Unsupported terminal helper architecture" >&2; exit 1 ;;
esac
case "$(uname -s)" in
  Darwin) exec clang -arch "$ARCH" -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror "$ROOT/src/zen/terminal/native/zen-terminal-pty.c" -o "$OUT" ;;
  *) echo 'zen-terminal-pty release builds require macOS.' >&2; exit 1 ;;
esac
