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


def test_repeated_break_quote_repair_uses_matching_context(tmp_path):
    from test_ledger import GOLD, DOCUMENTS, envelope
    from care_ledger.persist import locate_quote
    name = 'BH-D107_group_activity_records_2026-01-22_and_29.txt'
    content = (DOCUMENTS / name).read_text(encoding='utf-8')
    bad = envelope(GOLD[name]).model_dump(mode='json')
    repeated = bad['encounters'][0]['breaks'][0]['evidence_quotes'][0].split('\n', 1)[1]
    for section in bad['encounters']:
        section['breaks'][0]['evidence_quotes'] = [repeated]
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        output = bad
        if len(calls) == 2:
            message = kwargs['input'][-1]['content']
            assert 'HG-E113' in message and 'HG-E118' in message
            assert 'January 22' in message and 'January 29' in message
            output = envelope(GOLD[name]).model_dump(mode='json')
        return NS(_request_id='r', output_text=json.dumps(output), status='completed', usage=None)
    attempts = _extract_document(NS(responses=NS(create=create)),
                                 Settings(tmp_path/'db', 'gpt-5.4-mini', 'medium', 'test'), 7, content)
    assert len(attempts) == 2 and attempts[0].evidence_rejected
    feedback = json.loads(attempts[0].repair_feedback)
    assert len(feedback) == 1 and len(feedback[0]['candidates']) == 2
    for candidate in feedback[0]['candidates']:
        locate_quote(content, candidate['unique_context'])
    assert attempts[1].envelope is not None
    assert len(attempts[1].envelope.encounters) == 2


def test_resume_extracts_only_failed_document_and_keeps_attempt_costs(tmp_path, monkeypatch):
    from care_ledger import extract
    from care_ledger.db import ingest_directory
    from test_ledger import envelope
    docs = tmp_path/'docs'
    docs.mkdir()
    (docs/'one.txt').write_text('First note')
    (docs/'two.txt').write_text('Second note')
    path = tmp_path/'resume.sqlite'
    db = open_db(path)
    ingest_directory(db, docs)
    settings = Settings(path, 'gpt-5.4-mini', 'medium', 'test')
    monkeypatch.setattr(extract, 'OpenAI', lambda **kwargs: object())
    requested = []
    def first(client, settings, doc, content):
        requested.append(doc)
        return [CallResult(doc, '2026-10-12T00:00:00+00:00', 1,
                           envelope({}) if doc == 1 else None,
                           None if doc == 1 else 'ambiguous evidence', None,
                           dict(input_tokens=100, cached_input_tokens=0, output_tokens=50, reasoning_tokens=10))]
    monkeypatch.setattr(extract, '_extract_document', first)
    summary = extract.extract_pending(db, settings, 1)
    assert summary.succeeded == 1 and set(summary.failed) == {2}
    db.close()
    db = open_db(path)
    requested.clear()
    def second(client, settings, doc, content):
        requested.append(doc)
        return [CallResult(doc, '2026-10-12T00:01:00+00:00', 1, envelope({}), None, None,
                           dict(input_tokens=100, cached_input_tokens=0, output_tokens=50, reasoning_tokens=10))]
    monkeypatch.setattr(extract, '_extract_document', second)
    summary = extract.extract_pending(db, settings, 1)
    assert requested == [2] and summary.succeeded == 1 and not summary.failed
    assert db.execute('SELECT count(*) FROM model_calls').fetchone()[0] == 3
    assert db.execute('SELECT count(*) FROM extractions').fetchone()[0] == 2
    assert _extraction(db, 'test')['tokens']['input_tokens'] == 300
    db.close()
