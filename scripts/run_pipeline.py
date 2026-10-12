"""Build a fresh run, retain interrupted work, and publish only complete results."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def _run(command, *, staging: Path, env: dict):
    completed = subprocess.run([sys.executable, *command], text=True, encoding='utf-8',
                               capture_output=True, env=env)
    entry = ('$ python ' + ' '.join(command).replace(str(staging), '<run>') + '\n'
             + completed.stdout.replace(str(staging), '<run>')
             + completed.stderr.replace(str(staging), '<run>'))
    with (staging / 'execution.log').open('a', encoding='utf-8') as log:
        log.write(entry.rstrip() + '\n')
    if completed.returncode:
        print(entry, file=sys.stderr)
        raise SystemExit(completed.returncode)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--resume', action='store_true', help='reuse this incomplete run; extract only pending documents')
    args = parser.parse_args(argv)
    os.chdir(ROOT)
    load_dotenv(ROOT / '.env')
    if args.live and not os.getenv('OPENAI_API_KEY'):
        parser.error('Live extraction requires OPENAI_API_KEY in your environment or ignored .env file.')
    destination = ROOT / 'artifacts' / 'live' if args.live else ROOT / 'artifacts'
    version = 'llm-v2' if args.live else 'fixture'
    stem = 'live' if args.live else 'fixture'
    staging = (ROOT / f'.care-ledger-run-{stem}').resolve()
    if staging.parent != ROOT.resolve():
        raise RuntimeError('Run directory must stay within the repository')
    resume_command = 'python scripts/run_pipeline.py' + (' --live' if args.live else '') + ' --resume'
    if staging.exists() and not args.resume:
        parser.error(f'An incomplete run already exists. Resume it with: {resume_command}')
    if args.resume and not staging.exists():
        parser.error('No retained run exists to resume. Omit --resume to start fresh.')
    identity = {
        'version': version,
        'model': os.getenv('CARE_LEDGER_MODEL', 'gpt-5.4-mini') if args.live else 'fixture',
        'reasoning_effort': os.getenv('CARE_LEDGER_REASONING_EFFORT', 'medium') if args.live else None,
        'documents': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted((ROOT / 'documents').glob('*.txt'))},
    }
    state_path = staging / 'run.json'
    if args.resume:
        state = json.loads(state_path.read_text(encoding='utf-8'))
        if state['identity'] != identity:
            parser.error('Documents or model settings changed since this run; restore them before resuming.')
    else:
        staging.mkdir()
        state = {'identity': identity, 'processing_wall_s': 0.0, 'resumptions': 0}
        state_path.write_text(json.dumps(state, indent=2), encoding='utf-8')
    state['resumptions'] += int(args.resume)
    db_path = staging / f'{stem}.sqlite'
    child_env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONUTF8='1')
    run = lambda *command: _run(command, staging=staging, env=child_env)
    print(f'Run checkpoint: {staging.name}', flush=True)
    try:
        run('-m', 'pytest', '-q')
        base = ('-m', 'care_ledger.cli', '--db', str(db_path), '--version', version)
        start = time.perf_counter()
        try:
            run(*base, 'ingest', 'documents')
            run(*base, 'extract' if args.live else 'load-fixtures')
            # Also covers resuming after extraction succeeded but reconciliation was interrupted.
            run(*base, 'reconcile')
        finally:
            state['processing_wall_s'] += time.perf_counter() - start
            state_path.write_text(json.dumps(state, indent=2), encoding='utf-8')
        run(*base, 'report', '--out', str(staging))
        run(*base, 'benchmark', '--patient', 'HG-M042', '--start', '2026-01-05', '--end', '2026-01-30',
            '--date', '2026-01-19', '--date', '2026-01-21', '--out', str(staging / 'benchmark.json'))
        db = sqlite3.connect(db_path)
        try:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert not db.execute('PRAGMA foreign_key_check').fetchall()
            db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        finally:
            db.close()
        benchmark = json.loads((staging / 'benchmark.json').read_text(encoding='utf-8'))
        benchmark['fresh_processing_wall_s'] = round(state['processing_wall_s'], 3)
        benchmark['fresh_processing_scope'] = 'active ingest/extract/reconcile invocations including CLI startup; excludes time between resumptions'
        benchmark['resumptions'] = state['resumptions']
        benchmark['database_bytes'] = db_path.stat().st_size
        benchmark['database_size_scope'] = 'checkpointed SQLite database after report and benchmark'
        (staging / 'benchmark.json').write_text(json.dumps(benchmark, indent=2) + '\n', encoding='utf-8')
        destination.mkdir(parents=True, exist_ok=True)
        for name in (f'{stem}.sqlite', 'answers.md', 'answers.json', 'benchmark.json', 'execution.log'):
            shutil.copy2(staging / name, destination / name)
    except (Exception, SystemExit, KeyboardInterrupt):
        print(f'Run retained at {staging.name}. Successful extractions and usage are saved.\nResume: {resume_command}',
              file=sys.stderr)
        raise
    # Delete only this verified checkpoint, after every final artifact is published.
    if staging.parent != ROOT.resolve():
        raise RuntimeError('Refusing to remove a checkpoint outside the repository')
    shutil.rmtree(staging)
    print(f'Complete {version} results: {destination.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
