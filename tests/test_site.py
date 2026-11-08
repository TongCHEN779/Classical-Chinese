import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BuiltSiteTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / 'index.html').exists(), 'site not built')
    def test_site_audit_passes(self):
        r = subprocess.run([sys.executable, 'tools/check_site.py'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
