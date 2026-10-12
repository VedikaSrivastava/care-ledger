import importlib.util
import json
from pathlib import Path
import sqlite3

import pytest


@pytest.fixture
def runner(tmp_path, monkeypatch):
    path = Path(__file__).parents[1] / 'scripts' / 'run_pipeline.py'
    spec = importlib.util.spec_from_file_location('runner_under_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setenv('OPENAI_API_KEY', 'test-key-not-used')
    monkeypatch.chdir(tmp_path)
    (tmp_path/'documents').mkdir()
    (tmp_path/'documents'/'one.txt').write_text('Source')
    return module


def test_runner_preserves_failed_run_then_publishes_after_resume(runner, tmp_path, monkeypatch):
    destination = tmp_path/'artifacts'/'live'
    destination.mkdir(parents=True)
    (destination/'answers.md').write_text('Previous verified answers')
    checkpoint = tmp_path/'.care-ledger-run-live'
    def fail(command, **kwargs):
        if 'extract' in command:
            db = sqlite3.connect(checkpoint/'live.sqlite')
            db.execute('CREATE TABLE saved(value TEXT)')
            db.execute("INSERT INTO saved VALUES ('successful paid work')")
            db.commit()
            db.close()
            (checkpoint/'execution.log').write_text('First attempt\n')
            raise SystemExit(1)
    monkeypatch.setattr(runner, '_run', fail)
    with pytest.raises(SystemExit):
        runner.main(['--live'])
    assert (checkpoint/'live.sqlite').exists()
    assert (destination/'answers.md').read_text() == 'Previous verified answers'
    # Starting fresh must not overwrite paid checkpoint work.
    with pytest.raises(SystemExit):
        runner.main(['--live'])
    def complete(command, **kwargs):
        db = sqlite3.connect(checkpoint/'live.sqlite')
        assert db.execute('SELECT value FROM saved').fetchone()[0] == 'successful paid work'
        db.close()
        if 'report' in command:
            (checkpoint/'answers.md').write_text('Complete answers')
            (checkpoint/'answers.json').write_text('{}')
        if 'benchmark' in command:
            (checkpoint/'benchmark.json').write_text('{}')
    monkeypatch.setattr(runner, '_run', complete)
    runner.main(['--live', '--resume'])
    assert not checkpoint.exists()
    assert (destination/'answers.md').read_text() == 'Complete answers'
    assert (destination/'live.sqlite').exists()
    assert json.loads((destination/'benchmark.json').read_text())['resumptions'] == 1
