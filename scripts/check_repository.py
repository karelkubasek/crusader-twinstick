#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check Git-visible files against the source distribution boundary."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.build_portable import source_files

allowed = {p.relative_to(ROOT).as_posix() for p in source_files()}
visible = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
unexpected = sorted(set(filter(None, visible)) - allowed)
if unexpected:
    raise SystemExit('Unexpected Git-visible files:\n' + '\n'.join(unexpected))
for relative in allowed:
    if (ROOT / relative).stat().st_size > 1024 * 1024:
        raise SystemExit('Unexpectedly large source file: ' + relative)
print(f'{len(allowed)} allowlisted source files; no game content, personal state or generated binaries visible to Git.')
