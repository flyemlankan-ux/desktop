#!/usr/bin/env python3
"""Real disposable PTY tests. Python is test-only, never shipped in the app."""
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = Path(os.environ.get('ZEN_TERMINAL_PTY', ROOT / 'build/terminal-native/zen-terminal-pty'))


class Bridge:
    def __init__(self, code, read_delay=0):
        self.p = subprocess.Popen([str(HELPER), '--rows', '24', '--cols', '80', '--',
                                   sys.executable, '-u', '-c', code],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.data = bytearray()
        self.read_delay = read_delay
        self.reader = threading.Thread(target=self.read, daemon=True)
        self.reader.start()

    def read(self):
        time.sleep(self.read_delay)
        while True:
            chunk = os.read(self.p.stdout.fileno(), 65536)
            if not chunk:
                return
            self.data.extend(chunk)

    def send(self, data):
        self.p.stdin.write(data)
        self.p.stdin.flush()

    def input(self, data):
        self.send(b'I%d\n' % len(data) + data)

    def expect(self, data, timeout=10):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if data in self.data:
                return
            if self.p.poll() is not None:
                self.reader.join(1)
                if data in self.data:
                    return
                break
            time.sleep(.01)
        raise AssertionError('Missing %r; output tail: %r' % (data, self.data[-1000:]))

    def finish(self, timeout=8):
        result = self.p.wait(timeout)
        self.reader.join(2)
        return result

    def close(self):
        if self.p.poll() is None:
            self.p.terminate()
            self.p.wait(8)
        self.reader.join(2)
        self.p.stdin.close()
        self.p.stdout.close()
        self.p.stderr.close()


class Tests(unittest.TestCase):
    def bridge(self, code):
        b = Bridge(code)
        self.addCleanup(b.close)
        return b

    def test_repeated_unicode_and_split_frames(self):
        payload = ('hello café 世界 🙂\r\n' * 500).encode()
        b = self.bridge('import os,tty,hashlib; tty.setraw(0); print("READY",flush=True); '
                        'data=b""\nwhile len(data)<%d: data+=os.read(0,%d-len(data))\n'
                        'print(hashlib.sha256(data).hexdigest(),flush=True)' % (len(payload), len(payload)))
        b.expect(b'READY')
        for offset in range(0, len(payload), 31):
            chunk = payload[offset:offset + 31]
            frame = b'I%d\n' % len(chunk) + chunk
            for j in range(0, len(frame), 3):
                b.send(frame[j:j + 3])
        b.expect(hashlib.sha256(payload).hexdigest().encode())
        self.assertEqual(b.finish(), 0)

    def test_resize_without_tmux(self):
        b = self.bridge('import os,tty; tty.setraw(0); print("READY",flush=True)\n'
                        'for i in range(3):\n os.read(0,1); s=os.get_terminal_size(0); '
                        'print("SIZE:%d:%d"%(s.lines,s.columns),flush=True)')
        b.expect(b'READY')
        for rows, cols in [(24, 80), (42, 132), (1, 1000)]:
            b.send(b'R%d %d\n' % (rows, cols))
            b.input(b'x')
            b.expect(b'SIZE:%d:%d' % (rows, cols))
        self.assertEqual(b.finish(), 0)

    def test_real_shell_stty_resize(self):
        b = self.bridge('import os; os.execv("/bin/sh", ["/bin/sh", "-c", "printf READY; read ignored; stty size"])')
        b.expect(b"READY")
        b.send(b"R45 111\n")
        b.input(b"x\n")
        b.expect(b"45 111")
        self.assertEqual(b.finish(), 0)

    def test_large_bidirectional_stream(self):
        size = 2 * 1024 * 1024
        payload = (b'0123456789abcdef' * (size // 16))
        b = self.bridge('import os,tty,hashlib; tty.setraw(0); print("READY",flush=True); '
                        'data=b""\nwhile len(data)<%d:\n chunk=os.read(0,min(65536,%d-len(data))); '
                        'data+=chunk; view=memoryview(chunk)\n while view: view=view[os.write(1,view):]\n'
                        'print(hashlib.sha256(data).hexdigest(),flush=True)' % (size, size))
        b.expect(b'READY')
        for offset in range(0, size, 256 * 1024):
            b.input(payload[offset:offset + 256 * 1024])
        digest = hashlib.sha256(payload).hexdigest().encode()
        b.expect(digest, 20)
        self.assertEqual(b.finish(), 0)
        self.assertEqual(bytes(b.data), b'READY\n' + payload + digest + b'\n')

    def test_slow_output_consumer(self):
        b = Bridge('import os; data=b"x"*3145728; view=memoryview(data)\nwhile view: view=view[os.write(1,view):]', read_delay=.4)
        self.addCleanup(b.close)
        time.sleep(.2)
        self.assertIsNone(b.p.poll(), "Producer must wait, not drop output")
        self.assertEqual(b.finish(), 0)
        self.assertEqual(bytes(b.data), b"x" * 3145728)

    def test_ctrl_c(self):
        b = self.bridge('import os,signal,time; signal.signal(signal.SIGINT, signal.SIG_DFL); '
                        'print("READY",flush=True); time.sleep(60)')
        b.expect(b'READY')
        b.input(b'\x03')
        self.assertEqual(b.finish(), 128 + signal.SIGINT)

    def assert_child_gone(self, b):
        pid = int(bytes(b.data).split(b'PID:')[1].split()[0])
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_eof_and_signal_cleanup(self):
        for ending in ('eof', signal.SIGHUP, signal.SIGTERM):
            with self.subTest(ending=ending):
                b = self.bridge('import os,time; print("PID:%d"%os.getpid(),flush=True); time.sleep(60)')
                b.expect(b'PID:')
                if ending == 'eof':
                    b.p.stdin.close()
                else:
                    b.p.send_signal(ending)
                b.finish()
                self.assert_child_gone(b)

    def test_malformed_and_truncated_frames(self):
        for frame in [b'I262145\n', b'I-1\n', b'R0 80\n', b'R24 1001\n', b'R24 80 junk\n',
                      b'X1\n', b'I1\x00\n', b'I' + b'0' * 64, b'I10\nabc', b'R2']:
            with self.subTest(frame=frame):
                b = self.bridge('import time; print("READY",flush=True); time.sleep(60)')
                b.expect(b'READY')
                b.send(frame)
                b.p.stdin.close()
                self.assertEqual(b.finish(), 65)
                self.assertIn(b'malformed', b.p.stderr.read())

    def test_exec_failure_and_cli_validation(self):
        r = subprocess.run([str(HELPER), '--rows', '24', '--cols', '80', '--', '/not/a/program'],
                           capture_output=True, timeout=8)
        self.assertEqual(r.returncode, 127)
        self.assertIn(b'exec /not/a/program', r.stderr)
        for rows, cols, program in [('0', '80', '/bin/sh'), ('24', '1001', '/bin/sh'),
                                    ('-1', '80', '/bin/sh'), ('24', '80', 'sh')]:
            r = subprocess.run([str(HELPER), '--rows', rows, '--cols', cols, '--', program],
                               capture_output=True, timeout=8)
            self.assertEqual(r.returncode, 64)

    def test_child_exit_code_and_trailing_output(self):
        b = self.bridge('import os; os.write(1,b"END"*100000); raise SystemExit(23)')
        self.assertEqual(b.finish(), 23)
        self.assertEqual(bytes(b.data), b'END' * 100000)


if __name__ == '__main__':
    if not HELPER.is_file():
        subprocess.run([str(ROOT / 'scripts/terminal-tabs/build-terminal-pty.sh'), str(HELPER)], check=True)
    unittest.main(verbosity=2)
