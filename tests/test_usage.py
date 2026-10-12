import json
from types import SimpleNamespace as NS

from care_ledger.benchmark import _extraction
from care_ledger.config import Settings
from care_ledger.extract import _extract_document, _record, CallResult
from care_ledger.db import open_db


def test_validation_failure_keeps_usage_and_repairs(tmp_path):
    settings = Settings(tmp_path / 'db.sqlite', 'gpt-5.4-mini', 'medium', 'test')
    valid = dict(patient=dict(mrn='X', name='Name', birth_date=None), encounters=[],
                 corrections=[], assessments=[], observations=[], plans=[])
    invalid = dict(valid, corrections=[dict(encounter_id='E', service_date='2026-01-01',
                  field='presence_end', replaced_time='10:45:00-11:00', replacement_time='11:00',
                  source_status='final', authored_on='2026-01-02', evidence_quotes=['quote'])])
    responses = iter([invalid, valid])
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return NS(_request_id='request', output_text=json.dumps(next(responses)), status='completed',
                  usage=NS(input_tokens=100, output_tokens=50, input_tokens_details=NS(cached_tokens=20),
                           output_tokens_details=NS(reasoning_tokens=30)))
    attempts = _extract_document(NS(responses=NS(create=create)), settings, 1, 'quote')
    assert len(attempts) == 2
    assert attempts[0].error and attempts[0].usage['output_tokens'] == 50
    assert attempts[0].request_id == 'request'
    assert attempts[1].envelope is not None and attempts[1].error is None
    assert calls[0]['text']['format']['strict'] is True


def test_missing_usage_and_unknown_model_do_not_report_zero_cost(tmp_path):
    db = open_db(tmp_path / 'db.sqlite')
    db.execute("INSERT INTO documents(sha256,content) VALUES (?, 'text')", ('a'*64,))
    settings = Settings(tmp_path / 'db.sqlite', 'gpt-5.4-mini', 'medium', 'test')
    result = CallResult(1, '2026-10-12T00:00:00+00:00', 100, None, 'timeout', None, {})
    _record(db, settings, result)
    report = _extraction(db, 'test')
    assert report['estimated_cost_usd'] is None and report['usage_missing_calls'] == 1
    result.error = None
    result.usage = dict(input_tokens=1000, cached_input_tokens=200, output_tokens=100, reasoning_tokens=50)
    _record(db, settings, result)
    other = Settings(settings.database_path, 'unknown-model', 'medium', 'test')
    _record(db, other, result)
    report = _extraction(db, 'test')
    assert report['unpriced_calls'] == 2
    assert report['known_cost_subtotal_usd'] == 0.001065
    assert report['tokens']['output_tokens'] == 200
    assert report['estimated_cost_usd'] is None
    db.close()
