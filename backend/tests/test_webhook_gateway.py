"""SDK-verified ingress forwards to the real backend while the rest of the app stays private."""
import asyncio
import hashlib
import hmac
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.contracts import ReportIn
from app.db import engine
from app.engine.ingest import ingest_report
from app.main import app as backend_app
from app.models import Report
from app.voice import security, webhooks
import webhook_gateway as gateway

KEY = 'synthetic-test-signing-key'


def payload(agent='synthetic-intake-agent', consent=True):
    return {'event': 'call_analyzed', 'call': {
        'call_id': 'gateway-call', 'agent_id': agent, 'from_number': '+13235550177',
        'transcript': 'SYNTHETIC information — water across Figueroa at Avenue 52.',
        'call_analysis': {'custom_analysis_data': {
            'location_text': 'Figueroa and Avenue 52', 'hazard_type': 'water_on_road',
            'danger_words': '', 'anyone_in_danger': False, 'callback_ok': consent,
        }},
    }}


def signed(raw):
    stamp = str(int(time.time() * 1000))
    digest = hmac.new(KEY.encode(), raw + stamp.encode(), hashlib.sha256).hexdigest()
    return {'Content-Type': 'application/json', 'X-Retell-Signature': f'v={stamp},d={digest}'}


@pytest.fixture
def public(client, monkeypatch):
    monkeypatch.setattr(webhooks, 'RETELL_API_KEY', KEY)
    monkeypatch.setattr(gateway, 'RETELL_API_KEY', KEY)
    seen = []
    async def forward(url, *, content, headers):
        seen.append((url, content, headers))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=backend_app), trust_env=False, follow_redirects=False) as upstream:
            return await upstream.post(url, content=content, headers=headers)
    with TestClient(gateway.app) as ingress:
        monkeypatch.setattr(gateway.app.state.backend_client, 'post', forward)
        yield ingress, seen


def send(public, data=None, raw=None):
    ingress, _ = public
    raw = raw if raw is not None else json.dumps(payload() if data is None else data, ensure_ascii=False, indent=2).encode()
    return ingress.post('/retell/webhook', content=raw, headers=signed(raw))


@pytest.mark.parametrize('signature', [None, '', 'invalid', 'v=1,d=' + '0' * 64])
def test_bad_signature_never_forwarded(public, signature):
    ingress, seen = public
    headers = {'X-Retell-Signature': signature} if signature is not None else {}
    assert ingress.post('/retell/webhook', json=payload(), headers=headers).status_code == 401
    assert seen == []


def test_valid_unicode_body_signature_forward_unchanged(public, client):
    _, seen = public
    response = send(public)
    assert response.status_code == 204 and response.content == b''
    url, raw, headers = seen[0]
    assert url == gateway.BACKEND_WEBHOOK
    assert raw == response.request.content
    assert headers['X-Retell-Signature'] == response.request.headers['x-retell-signature']
    assert sum(i['report_count'] for i in client.get('/api/state').json()['incidents']) == 4


def test_duplicate_intake_is_persistent_across_restart(public, client):
    assert send(public).status_code == 204
    before = client.get('/api/incidents/1').json()
    with TestClient(backend_app):
        assert send(public).status_code == 204
    assert client.get('/api/incidents/1').json() == before
    with Session(engine) as s:
        assert len(s.exec(select(Report).where(Report.call_id == 'gateway-call')).all()) == 1


@pytest.mark.parametrize('raw', [b'{', b'[]', b'{}', b'{"event":"call_analyzed","call":{}}'])
def test_malformed_payload_returns_400_preserving_data(public, client, raw):
    before = client.get('/api/incidents/1').json()
    assert send(public, raw=raw).status_code == 400
    assert client.get('/api/incidents/1').json() == before


@pytest.mark.parametrize('agent,code', [('unauthorized', 403), ('', 400), (None, 400)])
def test_agent_identity_checked(public, client, agent, code):
    assert send(public, payload(agent=agent)).status_code == code
    assert client.get('/api/state').json()['incidents'][0]['report_count'] == 3


@pytest.mark.parametrize('path', ['/', '/api/state', '/api/demo/reset', '/api/incidents', '/api/incidents/1', '/api/incidents/1/evidence', '/api/incidents/1/reassign', '/api/incidents/1/request-callback', '/api/reports/1/callback-opt-out', '/docs', '/redoc', '/openapi.json', '/retell/webhook/', '/retell/webhook/api/state'])
@pytest.mark.parametrize('method', ['GET', 'POST'])
def test_only_webhook_path_is_public(public, path, method):
    ingress, seen = public
    assert ingress.request(method, path, follow_redirects=False).status_code == 404
    assert seen == []


@pytest.mark.parametrize('method', ['GET', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def test_only_post_method_allowed(public, method):
    ingress, seen = public
    assert ingress.request(method, '/retell/webhook').status_code == 405
    assert seen == []


def test_gateway_registers_no_hidden_routes():
    assert [(r.path, r.methods) for r in gateway.app.routes] == [('/retell/webhook', {'POST'})]


@pytest.mark.parametrize('consent', [False, None, 'false', 'true', 'yes', 1, 0])
def test_consent_defaults_false(public, consent):
    data = payload(consent=consent)
    if consent is None:
        data['call']['call_analysis']['custom_analysis_data'].pop('callback_ok')
    assert send(public, data).status_code == 204
    with Session(engine) as s:
        assert s.exec(select(Report).where(Report.call_id == 'gateway-call')).one().callback_ok is False


def test_explicit_boolean_consent_preserved(public):
    assert send(public, payload(consent=True)).status_code == 204
    with Session(engine) as s:
        assert s.exec(select(Report).where(Report.call_id == 'gateway-call')).one().callback_ok is True


@pytest.mark.parametrize('exc,code', [(httpx.ConnectError('private diagnostic'), 503), (httpx.ReadTimeout('private diagnostic'), 504)])
def test_backend_unavailable_or_timeout_is_safe(public, monkeypatch, exc, code):
    async def fail(*args, **kwargs):
        raise exc
    monkeypatch.setattr(gateway.app.state.backend_client, 'post', fail)
    response = send(public)
    assert response.status_code == code and 'private diagnostic' not in response.text


def test_total_forward_deadline(public, monkeypatch):
    async def slow(*args, **kwargs):
        await asyncio.sleep(60)
    monkeypatch.setattr(gateway.app.state.backend_client, 'post', slow)
    monkeypatch.setattr(gateway, 'FORWARD_DEADLINE_S', 0.02)
    start = time.monotonic()
    assert send(public).status_code == 504
    assert time.monotonic() - start < 1


@pytest.mark.parametrize('status', [302, 500, 404])
def test_backend_errors_or_redirects_never_leak_or_redirect(public, monkeypatch, status):
    async def fail(*args, **kwargs):
        return httpx.Response(status, text='private diagnostic', headers={'Location': 'https://example.com'})
    monkeypatch.setattr(gateway.app.state.backend_client, 'post', fail)
    response = send(public)
    assert response.status_code == 502
    assert 'private diagnostic' not in response.text and 'location' not in response.headers


def test_url_query_and_host_cannot_change_upstream(public):
    ingress, seen = public
    raw = json.dumps(payload()).encode()
    headers = dict(signed(raw), Host='example.com', **{'X-Forwarded-Host': 'example.com'})
    assert ingress.post('/retell/webhook?url=https://example.com/api/state', content=raw, headers=headers).status_code == 204
    assert seen[0][0] == 'http://127.0.0.1:8001/retell/webhook'
    assert 'Host' not in seen[0][2] and 'X-Forwarded-Host' not in seen[0][2]


def test_callback_agent_requires_metadata(public):
    assert send(public, payload(agent='synthetic-callback-agent')).status_code == 400


def test_intake_agent_cannot_impersonate_callback(public):
    data = payload()
    data['call']['metadata'] = {'incident_id': 1, 'attempt_no': 1}
    assert send(public, data).status_code == 400


def test_callback_agent_routes_to_outcome_not_intake(public, client, dispatched_callback):
    dispatched_callback(1, 'gateway-call')
    data = payload(agent='synthetic-callback-agent')
    data['call']['metadata'] = {'incident_id': 1, 'attempt_no': 1}
    data['call']['call_analysis']['custom_analysis_data'] = {'outcome': 'worse', 'anyone_in_danger': False}
    assert send(public, data).status_code == 204
    before = client.get('/api/incidents/1').json()
    assert send(public, data).status_code == 204
    assert client.get('/api/incidents/1').json() == before
    assert before['report_count'] == 3 and before['callbacks'][0]['outcome'] == 'worse'


def test_verifies_with_sdk_at_both_layers(public, monkeypatch):
    sdk = security._retell_client(KEY)
    verify = sdk.verify
    bodies = []
    def spy(body, *, api_key, signature):
        bodies.append(body)
        return verify(body, api_key=api_key, signature=signature)
    monkeypatch.setattr(sdk, 'verify', spy)
    response = send(public)
    assert response.status_code == 204
    assert bodies == [response.request.content.decode()] * 2


def test_no_keys_phones_or_transcripts_in_logs(public, caplog):
    data = payload()
    assert send(public, data).status_code == 204
    for secret in (KEY, data['call']['from_number'], data['call']['transcript']):
        assert secret not in caplog.text


def test_concurrent_duplicate_source_inserts_one_row(client):
    report = ReportIn(source='retell', call_id='concurrent-provider-id', hazard_type='flood', location_text='Figueroa and Avenue 52', created_at=datetime.now(timezone.utc))
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(lambda _: ingest_report(report), range(8)))
    assert len(set(ids)) == 1
    with Session(engine) as s:
        assert len(s.exec(select(Report).where(Report.call_id == report.call_id)).all()) == 1


def test_gateway_missing_key_fails_closed(public, monkeypatch):
    _, seen = public
    monkeypatch.setattr(gateway, 'RETELL_API_KEY', '')
    assert send(public).status_code == 401
    assert seen == []


@pytest.mark.parametrize('setting', ['RETELL_INTAKE_AGENT_ID', 'RETELL_CALLBACK_AGENT_ID'])
def test_missing_agent_configuration_does_not_accept_analyzed_event(public, client, monkeypatch, setting):
    monkeypatch.setattr(webhooks, setting, '')
    before = client.get('/api/incidents/1').json()
    assert send(public).status_code == 502  # no acknowledgment from an unconfigured backend
    assert client.get('/api/incidents/1').json() == before


def test_non_analyzed_events_are_acknowledged_without_ingestion(public, client):
    before = client.get('/api/incidents/1').json()
    assert send(public, {'event':'call_started'}).status_code == 204
    assert client.get('/api/incidents/1').json() == before


def test_gateway_client_has_no_proxy_or_redirect_routing(public):
    backend_client = gateway.app.state.backend_client
    assert backend_client.follow_redirects is False
    assert backend_client.trust_env is False


@pytest.mark.parametrize('identifier', [True, 0, -1, 1.2, 'invalid', 2**80])
def test_invalid_callback_identifier_is_400_before_database_access(public, client, identifier):
    data = payload(agent='synthetic-callback-agent')
    data['call']['metadata'] = {'incident_id': identifier, 'attempt_no': 1}
    before = client.get('/api/incidents/1').json()
    assert send(public, data).status_code == 400
    assert client.get('/api/incidents/1').json() == before
