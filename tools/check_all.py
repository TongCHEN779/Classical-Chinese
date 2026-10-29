#!/usr/bin/env python3
"""Run every audit script plus the unit tests; exits non-zero if any fails.

  python3 tools/check_all.py            # audit the already built site
  python3 tools/check_all.py --build    # run build.py first
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    ['tools/check_classics.py'],
    ['tools/check_site.py'],
    ['tools/check_four_classics.py'],
    ['tools/check_roupotuan.py'],
    ['tools/check_zuozhuan.py'],
    ['tools/check_xianqing.py'],
    ['tools/check_xiaochuang.py'],
    ['tools/check_canying.py'],
    ['tools/check_liaozhai.py'],
    ['tools/check_shangjunshu.py'],
    ['-m', 'unittest', 'discover', '-s', 'tests'],
]


def main():
    failed = []
    if '--build' in sys.argv:
        r = subprocess.run([sys.executable, 'build.py'], cwd=ROOT, capture_output=True, text=True)
        print('build.py', 'ok' if r.returncode == 0 else 'FAILED')
        if r.returncode:
            print(r.stdout[-800:], r.stderr[-800:])
            sys.exit(1)
    for step in STEPS:
        r = subprocess.run([sys.executable, *step], cwd=ROOT, capture_output=True, text=True)
        name = ' '.join(step)
        tail = (r.stdout.strip().splitlines() or [''])[-1][:110] if r.returncode == 0 else (r.stdout + r.stderr).strip()[-500:]
        print(('PASS ' if r.returncode == 0 else 'FAIL ') + name + (' — ' + tail if r.returncode == 0 else ''))
        if r.returncode:
            print(tail)
            failed.append(name)
    if failed:
        sys.exit(f'{len(failed)} check(s) failed: {failed}')
    print('ALL CHECKS PASSED')


if __name__ == '__main__':
    main()
