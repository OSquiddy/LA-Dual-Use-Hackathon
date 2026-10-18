"""Read-only Retell readiness check. Prints booleans only; never calls a phone or changes an agent.

Run from backend: PYTHONPATH=. .venv/bin/python scripts/check_retell_callback_config.py
Use --mode automatic to explicitly check an authorized automatic live configuration.
"""
import argparse
import json
from urllib.parse import quote, urlsplit

import httpx

from app import config
from app.engine.contact import valid_phone


def report(checks):
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


def main(expected_mode=None):
    if expected_mode is None:
        expected_mode = ('automatic' if config.LIVE_CALLBACKS_ENABLED else 'manual-live') if config.CALL_MODE == 'live' else 'simulate'
    if expected_mode == 'simulate':
        checks = {'simulate_mode': config.CALL_MODE == 'simulate', 'automatic_live_disabled': not config.LIVE_CALLBACKS_ENABLED}
    else:
        from app.engine.live_control import automatic_enabled
        checks = {'live_mode': config.CALL_MODE == 'live'}
        checks['automatic_live_enabled' if expected_mode == 'automatic' else 'automatic_live_disabled'] = (
            automatic_enabled(config.LIVE_CALLBACKS_ENABLED) if expected_mode == 'automatic' else not config.LIVE_CALLBACKS_ENABLED)
    checks.update({
        'api_key_present': bool(config.RETELL_API_KEY),
        'callback_agent_id_present': bool(config.RETELL_CALLBACK_AGENT_ID),
        'outbound_number_present': bool(config.RETELL_FROM_NUMBER.strip()),
        'outbound_number_valid_format': valid_phone(config.RETELL_FROM_NUMBER),
        'reviewer_key_present': bool(config.REVIEWER_API_KEY),
    })
    if not all(checks[k] for k in ('api_key_present', 'callback_agent_id_present')):
        return report(checks)
    with httpx.Client(base_url='https://api.retellai.com', headers={'Authorization': f'Bearer {config.RETELL_API_KEY}'},
                      timeout=8, trust_env=False, follow_redirects=False) as client:
        def get(path, **kwargs):
            try:
                response = client.get(path, **kwargs)
                checks['retell_api_reachable'] = True
                return response.json() if response.status_code == 200 else {}
            except (httpx.HTTPError, ValueError):
                return {}
        agent = get('/get-agent/' + quote(config.RETELL_CALLBACK_AGENT_ID, safe=''), params={'version': 'latest_published'})
        phone = get('/get-phone-number/' + quote(config.RETELL_FROM_NUMBER, safe='')) if valid_phone(config.RETELL_FROM_NUMBER) else {}
        checks['published_callback_agent_exists'] = bool(agent) and agent.get('is_published') is True
        checks['outbound_number_exists_in_account'] = bool(phone)
        webhook = agent.get('webhook_url') or ''
        checks['agent_webhook_present'] = bool(webhook)
        parsed = urlsplit(webhook)
        expected = config.PUBLIC_BASE_URL.rstrip('/') + '/retell/webhook' if config.PUBLIC_BASE_URL else ''
        checks['callback_webhook_https_and_correct_path'] = parsed.scheme == 'https' and bool(parsed.netloc) and parsed.path == '/retell/webhook'
        checks['callback_webhook_matches_configured_gateway'] = bool(expected) and webhook == expected
        events = agent.get('webhook_events')
        checks['callback_analysis_event_enabled'] = bool(agent) and (events is None or 'call_analyzed' in events)
        checks['dnc_detection_enabled'] = agent.get('enable_dnc_detection') is True
        fields = {f.get('name'): f for f in agent.get('post_call_analysis_data', [])}
        for name, kind in (('outcome', 'enum'), ('anyone_in_danger', 'boolean'), ('summary', 'string'),
                           ('callback_opt_out', 'boolean'), ('wrong_number', 'boolean')):
            checks['extraction_' + name + '_configured'] = fields.get(name, {}).get('type') == kind
        response_engine = agent.get('response_engine') or {}
        llm = get('/get-retell-llm/' + quote(response_engine['llm_id'], safe=''), params={'version': response_engine.get('version', 0)}) if response_engine.get('llm_id') else {}
        prompts = json.dumps(llm)
        checks['hazard_variable_present'] = '{{hazard}}' in prompts
        checks['location_variable_present'] = '{{location}}' in prompts
    return report(checks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Read-only Retell callback readiness check; no calls are placed.')
    parser.add_argument('--mode', choices=('simulate', 'manual-live', 'automatic'), help='Expected mode; defaults to the configured mode')
    raise SystemExit(main(parser.parse_args().mode))
