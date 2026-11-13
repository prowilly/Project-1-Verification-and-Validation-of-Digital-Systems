#!/usr/bin/env python3
"""Run FIFO checks in temporary copies, preserving teammate-owned sources/reports."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[1]


def read_results(path, expected=None):
    path = Path(path)
    if not path.is_file():
        raise RuntimeError(f'Missing simulation results: {path}')
    tests = ET.parse(path).getroot().findall('.//testcase')
    if not tests or (expected is not None and len(tests) != expected):
        raise RuntimeError(f'Unexpected test count in {path}: {len(tests)}')
    return {'tests': len(tests),
            'failed': sum(t.find('failure') is not None or t.find('error') is not None for t in tests),
            'skipped': sum(t.find('skipped') is not None for t in tests)}


def source_files():
    paths = [ROOT / 'requirements.txt', ROOT / 'tb/mutants_released.yaml']
    for folder in ('tb', 'crv', 'coverage', 'lib', 'dut', 'scripts', 'tests'):
        paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file()
                     and not {'sim_build', '__pycache__'}.intersection(p.parts)
                     and (p.suffix in ('.py', '.sv') or p.name == 'Makefile'))
    return sorted(set(paths))


def source_snapshot():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source_files()}


def protected_snapshot():
    paths = [ROOT / 'ai_log.md']
    for folder in ('crv', 'coverage'):
        names = subprocess.check_output(['git', 'ls-files', folder], cwd=ROOT, text=True).splitlines()
        paths.extend(ROOT / name for name in names)
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def summarize_trace(path, cycles, depth):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    # Three initial reset edges precede the CRV loop. Exclude its final drain.
    if len(rows) < cycles + 3 or any(r['rst_n'] for r in rows[:3]):
        raise RuntimeError('Trace does not contain the expected CRV reset and cycle sequence')
    phase = 'fill'
    groups = {}
    occupancy = {str(n): 0 for n in range(depth + 1)}
    previous = rows[2]['count']
    stimulus = []
    for row in rows[3:3 + cycles]:
        region = ('near_empty' if previous <= 1 else 'near_full' if previous >= depth - 1
                  else 'middle_' + phase)
        counts = groups.setdefault(region, dict(draws=0, writes=0, reads=0, resets=0))
        counts['draws'] += 1
        counts['writes'] += row['wr_en']
        counts['reads'] += row['rd_en']
        counts['resets'] += 1 - row['rst_n']
        occupancy[str(previous)] += 1
        stimulus.append([previous, row['wr_en'], row['rd_en'], row['wr_data'], row['rst_n']])
        if phase == 'fill' and row['count'] == depth:
            phase = 'drain'
        elif phase == 'drain' and row['count'] == 0:
            phase = 'fill'
        previous = row['count']
    return {'cycles': cycles, 'occupancy': occupancy, 'groups': groups,
            'stimulus_sha256': hashlib.sha256(json.dumps(stimulus).encode()).hexdigest()}


class Runs:
    def __init__(self, output):
        self.output = Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        versions = {name: importlib.metadata.version(name) for name in
                    ('cocotb', 'cocotb-coverage', 'pyvsc', 'pyboolector', 'dv-solve', 'pyucis', 'PyYAML')}
        versions['python'] = platform.python_version()
        versions['iverilog'] = subprocess.check_output(['iverilog', '-V'], stderr=subprocess.DEVNULL,
                                                       text=True).splitlines()[0]
        self.manifest = {'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'],
                          cwd=ROOT, text=True).strip(), 'source_sha256': source_snapshot(),
                         'protected_sha256': protected_snapshot(), 'environment': versions, 'runs': []}

    def save(self):
        (self.output / 'summary.json').write_text(json.dumps(self.manifest, indent=2, sort_keys=True) + '\n')

    def run(self, name, suite='crv', *, mutant=None, seed=4701, cycles=5000,
            width=8, depth=8, stimulus='biased', closure=True):
        case = self.output / name
        case.mkdir(parents=True, exist_ok=True)
        for filename in ('results.xml', 'coverage.yml', 'stimulus.json'):
            (case / filename).unlink(missing_ok=True)
        with tempfile.TemporaryDirectory(prefix='project1-') as folder:
            work = Path(folder)
            for source in source_files():
                target = work / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            if mutant:
                rtl = work / 'dut/fifo.sv'
                clean = rtl.read_text()
                if clean.count(mutant['find']) != 1:
                    raise RuntimeError(f"Nonunique mutation anchor: {mutant['id']}")
                rtl.write_text(clean.replace(mutant['find'], mutant['replace'], 1))
            cmd = ['make', '-C', suite, 'SIM=icarus']
            env = os.environ.copy()
            # Seed cocotb before pyvsc imports; seed the original test via SEED as well.
            env.update(RANDOM_SEED=str(seed), PYTHONHASHSEED='0', WIDTH=str(width), DEPTH=str(depth),
                       FIFO_TRACE_FILE=str(work / 'trace.jsonl'))
            if suite == 'crv':
                cmd.extend([f'SEED={seed}', f'N_CYCLES={cycles}', f'STIM={stimulus}'])
                # Environment assignment permits cocotb to append its timescale file.
                env['COMPILE_ARGS'] = f'-Pfifo.WIDTH={width} -Pfifo.DEPTH={depth}'
            with (case / 'run.log').open('w') as log:
                result = subprocess.run(cmd, cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT,
                                        timeout=240)
            result_file = work / suite / 'results.xml'
            if result_file.is_file():
                shutil.copyfile(result_file, case / 'results.xml')
            row = {'name': name, 'suite': suite, 'seed': seed, 'cycles': cycles if suite == 'crv' else None,
                   'width': width, 'depth': depth, 'command': cmd,
                   'environment': {k: env[k] for k in ('RANDOM_SEED', 'PYTHONHASHSEED', 'WIDTH', 'DEPTH', 'COMPILE_ARGS') if k in env},
                   'passive_trace': 'FIFO_TRACE_FILE=<temporary directory>/trace.jsonl',
                   'require_coverage_closure': closure if suite == 'crv' else False,
                   'isolated_copy': True, 'mutation': mutant['id'] if mutant else None,
                   'exit_code': result.returncode, **read_results(case / 'results.xml', 5 if suite == 'tb' else 1)}
            if result.returncode or row['skipped']:
                raise RuntimeError(f'Infrastructure failure/skip in {name}; see run.log')
            row['status'] = 'failed' if row['failed'] else 'passed'
            # Only assertion failures qualify as detections, not import/API errors.
            if mutant and row['failed'] and 'AssertionError' not in (case / 'run.log').read_text():
                raise RuntimeError(f'Mutation failed without a verified assertion: {name}')
            if suite == 'crv' and not row['failed']:
                report = work / 'coverage/coverage_report.yml'
                if not report.is_file():
                    raise RuntimeError(f'Missing coverage report: {name}')
                shutil.copyfile(report, case / 'coverage.yml')
                coverage = yaml.safe_load(report.read_text())
                top = coverage['fifo']
                log_text = (case / 'run.log').read_text()
                closed = re.search(r'COV CLOSED_AT cycle=(\d+|None)', log_text)
                row['coverage'] = {'hit': top['coverage'], 'total': top['size'],
                                   'closed_at': None if not closed or closed[1] == 'None' else int(closed[1]),
                                   'holes': [f'{name}:{b}' for name, cp in coverage.items()
                                             for b, hits in cp.get('bins:_hits', {}).items() if not hits]}
                measured = summarize_trace(work / 'trace.jsonl', cycles, depth)
                (case / 'stimulus.json').write_text(json.dumps(measured, indent=2, sort_keys=True) + '\n')
                row['stimulus_sha256'] = measured['stimulus_sha256']
                if closure and (top['coverage'] != 70 or top['size'] != 70):
                    raise RuntimeError(f'Coverage is not 70/70: {name}')
            self.manifest['runs'].append(row)
            self.save()
            print(f"{name}: {row['status']} ({row['tests']-row['failed']}/{row['tests']})", flush=True)
            if not mutant and row['failed']:
                raise RuntimeError(f'Clean test failed: {name}')
            return row

    def regression(self):
        unit = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                              cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (self.output / 'unit-tests.log').write_text(unit.stdout)
        if unit.returncode:
            raise RuntimeError('Verification-tool checks failed')
        self.run('baseline', 'tb')
        for seed in (4701, 17, 4702):
            self.run(f'seed-{seed}', seed=seed)
        self.run('seed-4701-repeat', seed=4701)
        for filename in ('coverage.yml', 'stimulus.json'):
            if (self.output / 'seed-4701' / filename).read_bytes() != (self.output / 'seed-4701-repeat' / filename).read_bytes():
                raise RuntimeError(f'Same-seed reproduction differs: {filename}')
        self.manifest['repeat_identical'] = True
        self.save()
        # Supplemental configurations measure holes; mandatory closure is 8x8.
        self.run('width16-depth5', width=16, depth=5, closure=False)
        self.run('width8-depth4', width=8, depth=4, closure=False)

    def convergence(self):
        # Existing public STIM switch only; no edits to teammate-owned constraints.
        self.run('uniform-5000', stimulus='uniform', closure=False)
        self.run('biased-3000', cycles=3000, closure=False)
        self.run('biased-5000', closure=True)

    def mutations(self):
        pool = yaml.safe_load((ROOT / 'tb/mutants_released.yaml').read_text())['mutants']
        self.manifest['mutation_scores'] = []
        for suite in ('tb', 'crv'):
            self.run(f'{suite}/clean', suite)
            found, survivors = [], []
            for mutant in pool:
                row = self.run(f"{suite}/{mutant['id']}", suite, mutant=mutant, closure=False)
                (found if row['failed'] else survivors).append(mutant['id'])
            score = dict(suite=suite, found=len(found), total=len(pool), detected=found, survivors=survivors)
            self.manifest['mutation_scores'].append(score)
            self.save()
            if len(found) / len(pool) < .9:
                raise RuntimeError(f'Released mutation target missed: {score}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=('all', 'regression', 'convergence', 'mutations'), default='all')
    parser.add_argument('--output', default='evidence/generated')
    args = parser.parse_args()
    sources, protected = source_snapshot(), protected_snapshot()
    names = ('regression', 'convergence', 'mutations') if args.suite == 'all' else (args.suite,)
    try:
        for name in names:
            runs = Runs(Path(args.output) / name)
            getattr(runs, name)()
    finally:
        if source_snapshot() != sources or protected_snapshot() != protected:
            raise RuntimeError('Repository sources or protected teammate files changed during verification')
    print('All requested checks passed; protected files unchanged.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.SubprocessError, OSError, ET.ParseError) as error:
        print(f'VERIFICATION FAILED: {error}', file=sys.stderr)
        sys.exit(1)
