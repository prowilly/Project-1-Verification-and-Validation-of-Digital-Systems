#!/usr/bin/env python3
"""Check the standalone ZIP layout/docs and run clean/released-mutant simulations."""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'submission/Project1_Submission.zip'
OUTPUT = ROOT / 'evidence/submission'


def main():
    protected = subprocess.check_output(['git', 'ls-files', 'crv', 'coverage', 'ai_log.md'], cwd=ROOT, text=True).splitlines()
    before = {p: (ROOT / p).read_bytes() for p in protected}
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert all(not n.startswith('/') and '..' not in Path(n).parts for n in names)
        assert [n for n in names if Path(n).name == 'Makefile'] == ['Makefile']
        assert [n for n in names if Path(n).name.startswith('test_') and n.endswith('.py')] == ['test_fifo.py']
        for name in ('vplan.md', 'closure.md', 'FINDINGS.md', 'CONTRIBUTIONS.md', 'ai_log.md', 'REPORT.pdf'):
            assert name in names, name
        for name, original in [('test_fifo.py', 'crv/test_fifo.py'), ('coverage/fifo_coverage.py', 'coverage/fifo_coverage.py'), ('ai_log.md', 'ai_log.md'), ('REPORT.pdf', 'REPORT.pdf')]:
            assert z.read(name) == (ROOT / original).read_bytes(), name
        manifest = json.loads(z.read('source_manifest.json'))
        for name, sha in manifest['packaged_sha256'].items():
            assert hashlib.sha256(z.read(name)).hexdigest() == sha, name
        plan = z.read('vplan.md').decode()
        headings = set(re.findall(r'^## (.+)$', plan, re.M))
        assert {'Feature list','Test matrix','Risk and spec ambiguity','Closure criteria'} <= headings
        assert re.search(r'^(?!#).*[Tt]his plan does not verify', plan, re.M)
        findings = z.read('FINDINGS.md').decode()
        assert {'Score','Survivors','Residual risk'} <= set(re.findall(r'^## (.+)$',findings,re.M))
        assert re.findall(r'\b(\d+)\s*/\s*(\d+)\b',findings) == [('8','8')]
        pool = yaml.safe_load(z.read('mutants_released.yaml'))['mutants']
        ids = {m['id'] for m in pool}
        assert len(ids) == len(pool) == 8
        section = findings.split('## Survivors\n',1)[1].split('\n## ',1)[0]
        rows = [line.split('|')[1].strip() for line in section.splitlines() if line.startswith('|')][2:]
        assert set(rows) == {'ignore_full','ignore_empty'} and set(rows) <= ids
        module = ast.parse(z.read('test_fifo.py'))
        assert any(isinstance(n,ast.AsyncFunctionDef) and n.name=='test_crv_seeded_regression' for n in module.body)
        OUTPUT.mkdir(parents=True,exist_ok=True)
        summary = {'archive_sha256':hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
                   'layout_checks':'passed', 'document_checks':'passed',
                   'grader_note':'Local checks match the screenshot requirements; the external course checker was not available.',
                   'test_module':'test_fifo.py','runs':[]}
        for mutant in [None] + pool:
            name = mutant['id'] if mutant else 'clean'
            dest = OUTPUT / name;dest.mkdir(exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='project1-submission-') as folder:
                work=Path(folder);z.extractall(work)
                if mutant:
                    p=work/'dut/fifo.sv';text=p.read_text()
                    assert text.count(mutant['find'])==1
                    p.write_text(text.replace(mutant['find'],mutant['replace'],1))
                cmd=['make','SIM=icarus','SEED=4701','N_CYCLES=5000']
                with (dest/'run.log').open('w') as log:
                    proc=subprocess.run(cmd,cwd=work,stdout=log,stderr=subprocess.STDOUT,timeout=240)
                result=work/'results.xml'
                assert result.is_file(),name
                (dest/'results.xml').write_bytes(result.read_bytes())
                tests=ET.parse(result).getroot().findall('.//testcase')
                assert len(tests)==1 and not any(t.find('skipped') is not None for t in tests),name
                failed=any(t.find('failure') is not None or t.find('error') is not None for t in tests)
                assert proc.returncode==0,(name,'build failure')
                assert failed == bool(mutant),(name,'unexpected test outcome')
                if mutant:
                    assert 'AssertionError' in (dest/'run.log').read_text(),(name,'non-assertion failure')
                else:
                    report=(work/'coverage/coverage_report.yml').read_bytes()
                    (dest/'coverage.yml').write_bytes(report)
                    top=yaml.safe_load(report)['fifo']
                    assert top['coverage']==top['size']==70
                row=dict(name=name,command=cmd,tests=1,failed=int(failed),status='detected' if mutant else 'passed')
                summary['runs'].append(row)
                (OUTPUT/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
                print(name+': '+row['status'],flush=True)
        summary['found']=8;summary['total']=8
        assert all((ROOT/p).read_bytes()==data for p,data in before.items())
        summary['protected_files_unchanged']=True
        (OUTPUT/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
        print('ZIP: one test directory; required headings/files present; clean pass, 70/70 bins, 8/8 detected.',flush=True)


if __name__=='__main__':
    main()
