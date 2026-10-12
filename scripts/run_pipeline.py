"""Publish one complete fresh run. Use --live for model-derived artifacts."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    load_dotenv()
    if args.live and not os.getenv('OPENAI_API_KEY'):
        parser.error('Live extraction requires OPENAI_API_KEY in your environment or ignored .env file.')
    destination = ROOT / 'artifacts' / 'live' if args.live else ROOT / 'artifacts'
    version = 'llm-v2' if args.live else 'fixture'
    stem = 'live' if args.live else 'fixture'
    child_env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONUTF8='1')
    with tempfile.TemporaryDirectory(prefix='.care-ledger-run-', dir=ROOT) as scratch:
        staging = Path(scratch).resolve()
        if staging.parent != ROOT.resolve():
            raise RuntimeError("Run directory must stay within the repository")
        db_path = staging / f'{stem}.sqlite'
        transcript = []

        def run(*command):
            completed = subprocess.run([sys.executable, *command], text=True, encoding='utf-8',
                                       capture_output=True, env=child_env)
            transcript.append('$ python ' + ' '.join(command).replace(str(staging), '<run>') + '\n'
                              + completed.stdout.replace(str(staging), '<run>')
                              + completed.stderr.replace(str(staging), '<run>'))
            if completed.returncode:
                print(transcript[-1], file=sys.stderr)
                raise SystemExit(completed.returncode)

        run('-m', 'pytest', '-q')
        base = ('-m', 'care_ledger.cli', '--db', str(db_path), '--version', version)
        start = time.perf_counter()
        run(*base, 'ingest', 'documents')
        run(*base, 'extract' if args.live else 'load-fixtures')
        processing_s = time.perf_counter() - start
        run(*base, 'report', '--out', str(staging))
        run(*base, 'benchmark', '--patient', 'HG-M042', '--start', '2026-01-05', '--end', '2026-01-30',
            '--date', '2026-01-19', '--date', '2026-01-21', '--out', str(staging / 'benchmark.json'))
        # Separate CLI processes above verify that the abstraction survives restart.
        db = sqlite3.connect(db_path)
        try:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert not db.execute('PRAGMA foreign_key_check').fetchall()
            db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        finally:
            db.close()
        benchmark = json.loads((staging / 'benchmark.json').read_text(encoding='utf-8'))
        benchmark['fresh_processing_wall_s'] = round(processing_s, 3)
        benchmark['fresh_processing_scope'] = 'ingest + extraction/persist + reconciliation, including CLI startup'
        benchmark['database_bytes'] = db_path.stat().st_size
        benchmark['database_size_scope'] = 'checkpointed SQLite database after report and benchmark'
        (staging / 'benchmark.json').write_text(json.dumps(benchmark, indent=2) + '\n', encoding='utf-8')
        (staging / 'execution.log').write_text('\n'.join(transcript), encoding='utf-8')
        destination.mkdir(parents=True, exist_ok=True)
        for name in (f'{stem}.sqlite', 'answers.md', 'answers.json', 'benchmark.json', 'execution.log'):
            shutil.copy2(staging / name, destination / name)
    print(f'Fresh {version} results: {destination.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
