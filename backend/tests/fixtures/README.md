A5: save the first real Retell `call_analyzed` webhook body here as `retell_call_analyzed.json`
(and a callback one as `retell_callback_analyzed.json`), then fix the mapping in
`app/voice/webhooks.py` and add a test that replays it. Strip real phone numbers first.
