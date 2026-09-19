#!/usr/bin/env python3
"""Bounded raw-PTY receiver for synthetic native input proof; never executes input."""
import os, select, sys, termios, time, tty
from pathlib import Path
output=Path(sys.argv[1]);ready=Path(sys.argv[2])
if not output.is_absolute() or not ready.is_absolute():raise SystemExit('Synthetic absolute output paths required')
fd=sys.stdin.fileno();old=termios.tcgetattr(fd);data=bytearray()
try:
 tty.setraw(fd)
 output.write_bytes(b'')
 os.write(sys.stdout.fileno(),'SEARCH雪 one\r\nSEARCH雪 two\r\nINPUT_RECEIVER_READY\r\n'.encode())
 ready.write_text('ready')
 end=time.monotonic()+120
 while time.monotonic()<end:
  if not select.select([fd],[],[],.2)[0]:continue
  part=os.read(fd,4096)
  if not part or b'\x04' in part:break
  data.extend(part)
  if len(data)>65536:raise RuntimeError('Synthetic input limit exceeded')
  temporary=output.with_suffix('.pending');temporary.write_bytes(data);temporary.replace(output)
finally:
 termios.tcsetattr(fd,termios.TCSANOW,old)
