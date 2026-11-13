#!/usr/bin/env python3
"""Build one standalone CRV submission without modifying teammate-owned files."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/prowilly/Project-1-Verification-and-Validation-of-Digital-Systems/blob/main/'

MAKEFILE = '''# Standalone package layout; the CRV test and helpers are unchanged copies.
TOPLEVEL_LANG ?= verilog
SIM ?= icarus
DUT ?= $(CURDIR)/dut/fifo.sv
VERILOG_SOURCES = $(DUT)
TOPLEVEL = fifo
MODULE = test_fifo
SEED ?= 4701
N_CYCLES ?= 5000
STIM ?= biased
WIDTH ?= 8
DEPTH ?= 8
RANDOM_SEED ?= $(SEED)
PYTHONHASHSEED ?= 0
export SEED N_CYCLES STIM WIDTH DEPTH RANDOM_SEED PYTHONHASHSEED
export PYTHONPATH := $(CURDIR):$(CURDIR)/tb:$(CURDIR)/lib:$(CURDIR)/coverage:$(PYTHONPATH)
COMPILE_ARGS += -Pfifo.WIDTH=$(WIDTH) -Pfifo.DEPTH=$(DEPTH)
include $(shell cocotb-config --makefiles)/Makefile.sim
'''


def build():
    copied = {'test_fifo.py': 'crv/test_fifo.py', 'mutants_released.yaml': 'tb/mutants_released.yaml'}
    for name in ('vplan.md', 'closure.md', 'FINDINGS.md', 'CONTRIBUTIONS.md', 'ai_log.md',
                 'REPORT.pdf', 'requirements.txt', 'lib/models/fifo_model.py',
                 'coverage/fifo_coverage.py', 'coverage/coverage_report.yml',
                 'dut/fifo.sv', 'dut/specs/fifo.md'):
        copied[name] = name
    for file in sorted((ROOT / 'tb').glob('fifo_*.py')):
        name = file.relative_to(ROOT).as_posix()
        copied[name] = name
    for folder in ('evidence/current', 'evidence/diagnostics'):
        for file in sorted((ROOT / folder).rglob('*')):
            if file.is_file() and '__pycache__' not in file.parts:
                name = file.relative_to(ROOT).as_posix()
                copied[name] = name
    payload = {name: (ROOT / source).read_bytes() for name, source in copied.items()}
    source_hashes = {name: {'repository_path': source,
                           'sha256': hashlib.sha256(payload[name]).hexdigest()}
                     for name, source in copied.items()}
    demo = re.search(r'https://(?:www\.)?youtube\.com/watch\?v=[A-Za-z0-9_-]+',
                     (ROOT / 'README.md').read_text())
    if not demo:
        raise RuntimeError('README demo link not found; do not invent one')
    payload['Makefile'] = MAKEFILE.encode()
    payload['README.md'] = f'''# Project 1 submission

Team: William Garland, Banmeet Singh, Daniel Jo. Course: EEE 4701.

[Project report](REPORT.pdf) · [Demo]({demo[0]})

Run `make SIM=icarus SEED=4701 N_CYCLES=5000` from this extracted directory.
Prerequisites: Python 3.12, Icarus Verilog 12.0, and `python -m pip install -r requirements.txt` in your Python environment.

There is exactly one test module, `test_fifo.py`, containing `test_crv_seeded_regression`.
It is copied unchanged from Banmeet's `crv/test_fifo.py`. The driver/monitor/scoreboard helpers are in `tb/`, the reference queue is in `lib/`, and the unchanged coverage model is in `coverage/`.
The only Makefile is here at the root. `make DUT=/absolute/path/to/fifo.sv` supports a replacement RTL file; use a fresh build between variants. Do not count make's exit status alone as a test result: inspect `results.xml` and the simulation summary.

Required documents: [vplan.md](vplan.md), [closure.md](closure.md), [FINDINGS.md](FINDINGS.md), [CONTRIBUTIONS.md](CONTRIBUTIONS.md), [ai_log.md](ai_log.md), and [REPORT.pdf](REPORT.pdf).
The released pool is [mutants_released.yaml](mutants_released.yaml). Source-copy hashes and package adaptations are recorded in [source_manifest.json](source_manifest.json).

The repository's separate directed test module and runner unit tests are excluded from this upload to avoid ambiguous test-directory selection. Their prior evidence is retained and clearly distinguished from the submitted CRV test. Default coverage is complete; supplemental coverage and distribution limitations remain documented honestly.
'''.encode()
    adapted = []
    redirects = {'tb/mutants_released.yaml': 'mutants_released.yaml',
                 'crv/test_fifo.py': 'test_fifo.py', 'submission/README.md': 'README.md'}
    # Fix only links in the edited team deliverables; never transform ai_log.md.
    for name in ('vplan.md', 'closure.md', 'FINDINGS.md'):
        text = payload[name].decode()
        def link(match):
            target = match[1]
            if target.startswith(('http:', 'https:', '#')):
                return match[0]
            path, sep, anchor = target.partition('#')
            if path in redirects:
                return '](' + redirects[path] + (sep + anchor if sep else '') + ')'
            exists = path in payload or any(p.startswith(path.rstrip('/') + '/') for p in payload)
            return match[0] if exists else '](' + REPO + target + ')'
        updated = re.sub(r'\]\(([^)]+)\)', link, text).encode()
        if updated != payload[name]:
            adapted.append(name)
        payload[name] = updated
    manifest = {'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'test_entry_point': 'test_fifo.py:test_crv_seeded_regression',
                'source_files': source_hashes,
                'generated_files': ['Makefile', 'README.md', 'source_manifest.json'],
                'markdown_links_adapted': adapted,
                'packaged_sha256': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(payload.items())}}
    payload['source_manifest.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    assert [p for p in payload if Path(p).name.startswith('test_') and p.endswith('.py')] == ['test_fifo.py']
    assert [p for p in payload if Path(p).name == 'Makefile'] == ['Makefile']
    target = ROOT / 'submission/Project1_Submission.zip'
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(payload.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 13, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    print(f'{target}: {len(payload)} files, {target.stat().st_size} bytes; one Makefile and one test module')


if __name__ == '__main__':
    build()
