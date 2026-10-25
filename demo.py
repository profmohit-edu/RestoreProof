"""Generate synthetic fixtures and real verification reports, without modifying user data."""
import io
import json
from pathlib import Path
import tempfile
import zipfile
from restoreproof import manifest, verify, report_html

SCENARIOS = ['healthy', 'missing', 'modified', 'mixed', 'unexpected']

def fixtures():
    files = {
        'college/attendance.csv': b'student,attendance\nSYN001,92\nSYN002,88\n',
        'college/results.csv': b'student,marks\nSYN001,81\nSYN002,76\n',
        'finance/budget.json': b'{"synthetic":true,"budget":150000}',
        'research/experiment.txt': b'Synthetic experiment notes. No real participant data.\n',
        'research/sample.bin': bytes(range(256))*16,
        'policy/recovery.txt': b'Synthetic recovery plan for a controlled demonstration.\n',
        'unicode/caf\u00e9.txt': b'Unicode filename test\n',
        'empty.txt': b''
    }
    return files

def zip_bytes(files):
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return b.getvalue()

def get_demo(scenario):
    if scenario not in SCENARIOS:
        raise ValueError('Unknown scenario')
    files = fixtures()
    with tempfile.TemporaryDirectory() as d:
        for name, data in files.items():
            p = Path(d)/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(data)
        m = manifest(d)
    if scenario in ('missing','mixed'):
        del files['college/attendance.csv']
    if scenario in ('modified','mixed'):
        files['college/results.csv'] = b'student,marks\nSYN001,00\nSYN002,00\n'
    if scenario == 'unexpected':
        files['unexpected.txt'] = b'Unrecognised file; not executed.'
    archive = zip_bytes(files)
    return m, archive

def run(scenario):
    m, archive = get_demo(scenario)
    return verify(m, io.BytesIO(archive))

if __name__ == '__main__':
    out=Path('evidence'); out.mkdir(exist_ok=True)
    summary=[]
    for scenario in SCENARIOS:
        m, archive=get_demo(scenario)
        r=verify(m,io.BytesIO(archive))
        (out/(scenario+'-manifest.json')).write_text(json.dumps(m,indent=2))
        (out/(scenario+'.zip')).write_bytes(archive)
        (out/(scenario+'-report.json')).write_text(json.dumps(r,indent=2))
        (out/(scenario+'-report.html')).write_text(report_html(r))
        summary.append({'scenario':scenario,**{k:v for k,v in r.items() if k not in ('files','scope','schema')}})
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
