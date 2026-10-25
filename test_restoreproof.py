import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile
from demo import get_demo, run, zip_bytes
from restoreproof import manifest, verify

class RecoveryTests(unittest.TestCase):
    def test_healthy(self):
        r=run('healthy'); self.assertEqual((r['verdict'],r['verified']),('PASS',8))
    def test_missing(self):
        r=run('missing'); self.assertEqual((r['missing'],r['verified']),(1,7))
    def test_same_length_corruption(self):
        r=run('modified'); self.assertEqual((r['modified'],r['verified']),(1,7))
    def test_mixed(self):
        r=run('mixed'); self.assertEqual((r['missing'],r['modified'],r['file_completeness_pct']),(1,1,75.0))
    def test_unexpected(self):
        r=run('unexpected'); self.assertEqual(r['verdict'],'FAIL'); self.assertEqual(r['unexpected_files'],['unexpected.txt'])
    def test_traversal(self):
        m,_=get_demo('healthy')
        with self.assertRaises(ValueError): verify(m,io.BytesIO(zip_bytes({'../escape.txt':b'x'})))
    def test_absolute(self):
        m,_=get_demo('healthy')
        with self.assertRaises(ValueError): verify(m,io.BytesIO(zip_bytes({'/escape.txt':b'x'})))
    def test_backslash(self):
        m,_=get_demo('healthy')
        with self.assertRaises(ValueError): verify(m,io.BytesIO(zip_bytes({'a\\b':b'x'})))
    def test_symlink(self):
        m,_=get_demo('healthy'); b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            i=zipfile.ZipInfo('link'); i.external_attr=(stat.S_IFLNK|0o777)<<16; z.writestr(i,'/etc/passwd')
        with self.assertRaises(ValueError): verify(m,io.BytesIO(b.getvalue()))
    def test_duplicate_manifest(self):
        m,a=get_demo('healthy'); m['files'].append(m['files'][0])
        with self.assertRaises(ValueError): verify(m,io.BytesIO(a))
    def test_invalid_manifest(self):
        m,a=get_demo('healthy'); m['files'][0]['sha256']='bad'
        with self.assertRaises(ValueError): verify(m,io.BytesIO(a))
    def test_empty_manifest(self):
        with self.assertRaises(ValueError): verify({'schema':'restoreproof-manifest-v1','files':[]},io.BytesIO(zip_bytes({})))
    def test_invalid_zip(self):
        m,_=get_demo('healthy')
        with self.assertRaises(zipfile.BadZipFile): verify(m,io.BytesIO(b'not a zip'))
    def test_source_symlink(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/'file').write_text('x'); (p/'link').symlink_to(p/'file')
            with self.assertRaises(ValueError): manifest(p)
    def test_size_limit(self):
        m,a=get_demo('healthy'); m['files'][0]['size']=300*1024*1024
        with self.assertRaises(ValueError): verify(m,io.BytesIO(a))
    def test_empty_file_verified(self):
        r=run('healthy'); self.assertEqual(next(x for x in r['files'] if x['path']=='empty.txt')['status'],'VERIFIED')
    def test_unicode(self):
        r=run('healthy'); self.assertEqual(next(x for x in r['files'] if 'caf' in x['path'])['status'],'VERIFIED')

if __name__=='__main__': unittest.main(verbosity=2)
