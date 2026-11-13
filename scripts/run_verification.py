#!/usr/bin/env python3
"""Reproducible Project 1 checks. Exit nonzero on missing evidence or failures."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[1]


def read_results(path, expected=None):
    """Do not trust make's exit code: cocotb 1.x may return zero on a failure."""
    path = Path(path)
    if not path.is_file():
        raise RuntimeError(f"Missing simulation results: {path}")
    tests = ET.parse(path).getroot().findall('.//testcase')
    if not tests or (expected is not None and len(tests) != expected):
        raise RuntimeError(f"Unexpected test count in {path}: {len(tests)}")
    return {"tests": len(tests),
            "failed": sum(t.find('failure') is not None or t.find('error') is not None for t in tests),
            "skipped": sum(t.find('skipped') is not None for t in tests)}


def source_snapshot():
    paths = [ROOT / 'requirements.txt']
    for folder in ('tb', 'crv', 'coverage', 'lib', 'dut', 'scripts', 'tests'):
        paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file()
                     and ('sim_build' not in p.parts and '__pycache__' not in p.parts)
                     and (p.suffix in ('.py', '.sv') or p.name == 'Makefile'))
    paths.append(ROOT / 'tb/mutants_released.yaml')
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    return {"files": hashes, "sha256": hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()}


def environment():
    versions = {name: importlib.metadata.version(name) for name in
                ('cocotb', 'cocotb-coverage', 'pyvsc', 'pyboolector', 'dv-solve', 'pyucis', 'PyYAML')}
    versions['python'] = platform.python_version()
    version = subprocess.run(['iverilog', '-V'], text=True, capture_output=True, check=True)
    versions['iverilog'] = version.stdout.splitlines()[0]
    return versions


class Runs:
    def __init__(self, output):
        self.output = Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.rows = []
        self.manifest = {"base_commit": subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                         "source": source_snapshot(), "environment": environment(), "runs": self.rows}

    def save(self):
        (self.output / 'summary.json').write_text(json.dumps(self.manifest, indent=2, sort_keys=True) + '\n')

    def run(self, name, suite='crv', *, rtl=None, seed=4701, cycles=5000, width=8,
            depth=8, stimulus='biased', reset_denominator=200, closure=True, allow_failure=False):
        case = self.output / name
        case.mkdir(parents=True, exist_ok=True)
        # Each run starts from a fresh build and cannot consume an old XML/report.
        shutil.rmtree(case / 'sim_build', ignore_errors=True)
        for generated in ('results.xml', 'coverage.json', 'coverage.yml'):
            (case / generated).unlink(missing_ok=True)
        cmd = ['make', '-C', suite, 'SIM=icarus', f'SIM_BUILD={case / "sim_build"}',
               f'COCOTB_RESULTS_FILE={case / "results.xml"}']
        if rtl is not None:
            cmd.append(f'DUT={Path(rtl).resolve()}')
        if suite == 'crv':
            cmd.extend([f'SEED={seed}', f'N_CYCLES={cycles}', f'WIDTH={width}', f'DEPTH={depth}',
                        f'STIM={stimulus}', f'RESET_DENOMINATOR={reset_denominator}',
                        f'REQUIRE_CLOSURE={int(closure)}'])
        env = os.environ.copy()
        env['COVERAGE_DIR'] = str(case)
        with (case / 'run.log').open('w') as log:
            result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
        row = {"name": name, "command": cmd, "environment": {"COVERAGE_DIR": str(case)},
               "exit_code": result.returncode, **read_results(case / 'results.xml', 5 if suite == 'tb' else 1)}
        if row['skipped'] or result.returncode:
            raise RuntimeError(f"Infrastructure/skip failure in {name}; see {case / 'run.log'}")
        row['status'] = 'failed' if row['failed'] else 'passed'
        report = case / 'coverage.json'
        if report.is_file():
            c = json.loads(report.read_text())
            row['coverage'] = {key: c[key] for key in ('hit', 'total', 'closed_at', 'stimulus_sha256')}
        elif suite == 'crv' and not row['failed']:
            raise RuntimeError(f"Coverage missing from passing run {name}")
        self.rows.append(row)
        self.save()
        print(f"{name}: {row['status']} ({row['tests'] - row['failed']}/{row['tests']})", flush=True)
        if row['failed'] and not allow_failure:
            raise RuntimeError(f"Test failure in {name}")
        return row

    def regression(self):
        unit = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                              cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (self.output / 'unit-tests.log').write_text(unit.stdout)
        if unit.returncode:
            raise RuntimeError('Verification-tool unit checks failed')
        self.run('baseline', 'tb')
        for seed in (4701, 17, 4702):
            self.run(f'seed-{seed}', seed=seed)
        self.run('seed-4701-repeat', seed=4701)
        a = json.loads((self.output / 'seed-4701/coverage.json').read_text())
        b = json.loads((self.output / 'seed-4701-repeat/coverage.json').read_text())
        if a != b:
            raise RuntimeError('Same-seed reproduction differs in coverage or generated stimulus')
        self.run('width16-depth5', width=16, depth=5)
        self.run('width8-depth4', width=8, depth=4)
        self.manifest['repeat_identical'] = True
        self.save()

    def experiments(self):
        self.run('reset-weight-500', reset_denominator=500, closure=False)
        self.run('reset-weight-200', reset_denominator=200, closure=False)

    def mutants(self):
        pool = yaml.safe_load((ROOT / 'tb/mutants_released.yaml').read_text())['mutants']
        clean = (ROOT / 'dut/fifo.sv').read_text()
        scores = []
        for suite, stimulus in [('tb', 'biased'), ('crv', 'biased'), ('crv', 'restricted')]:
            prefix = f'{suite}-{stimulus}'
            self.run(f'{prefix}/clean', suite, stimulus=stimulus, closure=False)
            found, survivors = [], []
            for mutant in pool:
                name = mutant['id']
                if clean.count(mutant['find']) != 1:
                    raise RuntimeError(f'Mutation anchor is not unique: {name}')
                folder = self.output / prefix / name
                folder.mkdir(parents=True, exist_ok=True)
                rtl = folder / 'fifo.sv'
                rtl.write_text(clean.replace(mutant['find'], mutant['replace'], 1))
                row = self.run(f'{prefix}/{name}', suite, rtl=rtl, stimulus=stimulus,
                               closure=False, allow_failure=True)
                (found if row['failed'] else survivors).append(name)
            score = {"suite": suite, "stimulus": stimulus, "found": len(found), "total": len(pool),
                     "detected": found, "survivors": survivors}
            scores.append(score)
            expected = {'ignore_full', 'ignore_empty'} if stimulus == 'restricted' else set()
            if set(survivors) != expected:
                raise RuntimeError(f'Unexpected survivor set: {score}')
            self.manifest['mutation_scores'] = scores
            self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=('all', 'regression', 'experiments', 'mutations'), default='all')
    parser.add_argument('--output', default='evidence/generated')
    args = parser.parse_args()
    base = Path(args.output).resolve()
    names = ('regression', 'experiments', 'mutations') if args.suite == 'all' else (args.suite,)
    for name in names:
        runs = Runs(base / name)
        getattr(runs, 'mutants' if name == 'mutations' else name)()
        if runs.manifest['source'] != source_snapshot():
            raise RuntimeError('Verification source changed while the regression was running')
    print('All requested checks passed.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, subprocess.SubprocessError, OSError, ET.ParseError) as error:
        print(f'VERIFICATION FAILED: {error}', file=sys.stderr)
        sys.exit(1)
