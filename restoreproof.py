"""RestoreProof 0.1: file-level ZIP recovery verification; Python 3.10+."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
import time
import zipfile

MAX_FILES = 10000
MAX_BYTES = 256 * 1024 * 1024

def safe_name(name):
    if not isinstance(name, str) or not name or '\\' in name or '\x00' in name:
        raise ValueError('Invalid path')
    p = PurePosixPath(name)
    if p.is_absolute() or any(x in ('', '.', '..') for x in name.split('/')) or ':' in name:
        raise ValueError('Unsafe or noncanonical path: ' + name)
    return name

def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def manifest(root):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Source must be a real directory')
    entries = []
    total = 0
    for base, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            p = Path(base) / name
            if p.is_symlink():
                raise ValueError('Symbolic links are not supported')
        for name in sorted(files):
            p = Path(base) / name
            if not stat.S_ISREG(p.stat().st_mode):
                raise ValueError('Only regular files are supported')
            size = p.stat().st_size
            total += size
            if total > MAX_BYTES or len(entries) >= MAX_FILES:
                raise ValueError('Source exceeds size or file limit')
            entries.append({'path': safe_name(p.relative_to(root).as_posix()), 'size': size, 'sha256': digest(p)})
    if not entries:
        raise ValueError('Source contains no files')
    return {'schema': 'restoreproof-manifest-v1', 'files': sorted(entries, key=lambda x: x['path'])}

def validate(m):
    if not isinstance(m, dict) or m.get('schema') != 'restoreproof-manifest-v1':
        raise ValueError('Unsupported manifest')
    fs = m.get('files')
    if not isinstance(fs, list) or not 0 < len(fs) <= MAX_FILES:
        raise ValueError('Invalid manifest file count')
    seen, total = set(), 0
    for e in fs:
        if not isinstance(e, dict):
            raise ValueError('Invalid file entry')
        name = safe_name(e.get('path'))
        if name in seen:
            raise ValueError('Duplicate manifest path')
        seen.add(name)
        if type(e.get('size')) is not int or e['size'] < 0:
            raise ValueError('Invalid size')
        if not isinstance(e.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', e['sha256']):
            raise ValueError('Invalid SHA-256')
        total += e['size']
    if total > MAX_BYTES:
        raise ValueError('Manifest exceeds size limit')
    return fs

def verify(m, archive):
    expected = validate(m)
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='restoreproof-') as temp:
        target = Path(temp)
        with zipfile.ZipFile(archive) as z:
            infos = z.infolist()
            if len(infos) > MAX_FILES:
                raise ValueError('Archive exceeds entry limit')
            seen, total = set(), 0
            for i in infos:
                name = safe_name(i.filename[:-1] if i.is_dir() else i.filename)
                if name in seen:
                    raise ValueError('Duplicate archive path')
                seen.add(name)
                mode = i.external_attr >> 16
                kind = stat.S_IFMT(mode)
                if kind not in (0, stat.S_IFREG, stat.S_IFDIR) or stat.S_ISLNK(mode):
                    raise ValueError('Special archive files are not supported')
                if i.flag_bits & 1:
                    raise ValueError('Encrypted ZIP files are not supported')
                total += i.file_size
                if total > MAX_BYTES:
                    raise ValueError('Archive exceeds uncompressed size limit')
            # Extract only into a newly-created temporary directory. Never execute files.
            for i in infos:
                dest = target.joinpath(*PurePosixPath(i.filename).parts)
                if i.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(i) as src, dest.open('xb') as out:
                    written = 0
                    for block in iter(lambda: src.read(1024 * 1024), b''):
                        written += len(block)
                        if written > i.file_size:
                            raise ValueError('Archive size mismatch')
                        out.write(block)
        restore_seconds = time.perf_counter() - start
        rows = []
        for e in expected:
            p = target.joinpath(*PurePosixPath(e['path']).parts)
            actual = digest(p) if p.is_file() else None
            status = 'MISSING' if actual is None else ('VERIFIED' if actual == e['sha256'] and p.stat().st_size == e['size'] else 'MODIFIED')
            rows.append({**e, 'actual_sha256': actual, 'status': status})
        expected_paths = {e['path'] for e in expected}
        extra = sorted(p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file() and p.relative_to(target).as_posix() not in expected_paths)
        counts = {s.lower(): sum(r['status'] == s for r in rows) for s in ('VERIFIED','MISSING','MODIFIED')}
        good_bytes = sum(r['size'] for r in rows if r['status'] == 'VERIFIED')
        all_bytes = sum(r['size'] for r in rows)
        result = {'schema': 'restoreproof-report-v1', 'scope': 'File-level bytes and paths only; no malware or application recovery assessment.',
                  'verdict': 'PASS' if counts['verified'] == len(rows) and not extra else 'FAIL',
                  'expected_files': len(rows), **counts, 'unexpected_files': extra,
                  'file_completeness_pct': round(100 * counts['verified']/len(rows), 2),
                  'verified_bytes': good_bytes, 'expected_bytes': all_bytes,
                  'byte_completeness_pct': round(100*good_bytes/all_bytes,2) if all_bytes else None,
                  'restore_seconds': round(restore_seconds, 6), 'total_seconds': round(time.perf_counter()-start,6), 'files': rows}
        return result

def report_html(r):
    esc = html.escape
    rows = ''.join('<tr><td>'+esc(x['path'])+'</td><td>'+x['status']+'</td><td>'+str(x['size'])+'</td></tr>' for x in r['files'])
    return '<!doctype html><meta charset="utf-8"><title>RestoreProof report</title><style>body{font:17px system-ui;max-width:1000px;margin:50px auto;color:#172b4d}td,th{padding:12px;border-bottom:1px solid #ddd;text-align:left}table{width:100%}</style><h1>RestoreProof | '+r['verdict']+'</h1><p>'+esc(r['scope'])+'</p><p>Verified: '+str(r['verified'])+' / '+str(r['expected_files'])+' · Completeness: '+str(r['file_completeness_pct'])+'% · Total time: '+str(r['total_seconds'])+' s</p><p>Unexpected: '+esc(', '.join(r['unexpected_files']) or 'None')+'</p><table><tr><th>File</th><th>Status</th><th>Expected bytes</th></tr>'+rows+'</table><p>Reference manifest must be trusted and stored independently. This report is not a security certification.</p>'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('manifest'); p.add_argument('directory'); p.add_argument('output')
    p = sub.add_parser('verify'); p.add_argument('manifest'); p.add_argument('archive'); p.add_argument('--output',default='report.json')
    a = parser.parse_args()
    try:
        if a.command == 'manifest':
            data = manifest(a.directory)
            if Path(a.output).resolve().is_relative_to(Path(a.directory).resolve()):
                raise ValueError('Store manifest outside the source directory')
        else:
            data = verify(json.loads(Path(a.manifest).read_text()), a.archive)
        with open(a.output, 'x') as f:
            json.dump(data, f, indent=2)
        if a.command == 'verify':
            print(data['verdict'], data['file_completeness_pct'], '%')
            return 0 if data['verdict'] == 'PASS' else 2
        return 0
    except (ValueError, OSError, zipfile.BadZipFile, RuntimeError) as e:
        parser.exit(1, 'Error: '+str(e)+'\n')

if __name__ == '__main__':
    raise SystemExit(main())
