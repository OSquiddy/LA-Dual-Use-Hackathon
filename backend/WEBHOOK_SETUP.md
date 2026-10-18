# Secure Retell ingress — Phase 1

The public tunnel belongs on the separate gateway **8002**, never on the main backend **8001**. Retell credentials are loaded through `app.config` from the repository-root `.env`; no credential is hardcoded, written, or printed by this setup.

```text
Retell -> public HTTPS tunnel -> 127.0.0.1:8002/retell/webhook
                                      |
                         SDK signature verification
                                      |
                       fixed local request, unchanged bytes
                                      v
                          127.0.0.1:8001/retell/webhook
                            SDK verification + agent authorization
                                      |
                           existing engine / SQLite
```

## Start locally

Install the recorded dependencies once, from the repository root:

```sh
cd backend
.venv/bin/python -m pip install -r requirements.txt
```

Terminal 1, from `backend/`:

```sh
CALL_MODE=simulate .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001 --no-access-log
```

Terminal 2, also from `backend/`:

```sh
CALL_MODE=simulate .venv/bin/python -m uvicorn webhook_gateway:app --host 127.0.0.1 --port 8002 --no-access-log
```

Keep the backend at **one worker**, as required by the SQLite demo architecture. `--no-access-log` avoids recording attacker-supplied query strings; application code does not log payloads, keys, transcripts, or caller numbers. The forwarding client's destination is fixed, proxies from the environment are disabled, and redirects are not followed.

## Before opening a public tunnel

Check these existing root `.env` entries locally; do not paste their values into chat or commit the file:

- `RETELL_API_KEY`: the key marked with Retell's **webhook badge**; an arbitrary API key may not verify signatures.
- `RETELL_INTAKE_AGENT_ID` and `RETELL_CALLBACK_AGENT_ID`: the correct two distinct agent IDs.
- `CALL_MODE=simulate`: outbound Retell calls remain disabled.

Restart both processes after changing credentials. The gateway imports configuration and verification only; it does not initialize the database or run the ladder.

When ready for an authorized test, tunnel **8002**:

```sh
cloudflared tunnel --url http://127.0.0.1:8002
```

Or use an already authenticated ngrok account:

```sh
ngrok http 8002
```

Configure Retell with `https://<generated-gateway-host>/retell/webhook`, with `call_analyzed` enabled. Put the public base URL in the local `PUBLIC_BASE_URL` setting. All other public paths return 404, and other methods on the webhook return 405. The main dashboard remains local; the gateway does not serve it.

The previous direct-to-8001 tunnel instructions are superseded by this gateway setup. Do not leave an old tunnel forwarding to 8001 running.

## Behavior

- SDK verification uses original UTF-8 body bytes and `X-Retell-Signature` before JSON parsing or forwarding; missing/invalid/stale signatures return **401**.
- Main webhook malformed JSON or invalid required identifiers returns **400**. Unknown agents return **403**. Missing/ambiguous local agent configuration fails closed.
- Only the configured Intake agent can create an intake report. Only the Callback agent can supply callback metadata. Other signed event types are acknowledged without processing.
- Intake extraction names remain exactly `location_text`, `hazard_type`, `danger_words`, `anyone_in_danger`, `callback_ok`. Callback permission is true only for an explicit JSON boolean `true`; missing, false, strings or numeric values do not grant permission.
- Report and callback `call_id` values have database-level uniqueness. Intake retry races reuse the committed report ID; normal callback retry delivery is idempotent. The main app serializes webhook dispatch through commit within its single process.
- The gateway forwards unchanged bytes and signature to one fixed URL: `http://127.0.0.1:8001/retell/webhook`. Incoming Host, proxy headers and URL query parameters cannot choose another target.
- Forwarding has a five-second overall deadline, below Retell's ten-second webhook acknowledgment window. Connection failures return **503**, timeouts **504**, and unexpected backend errors/redirects **502**. Upstream error bodies are never exposed. Backend success acknowledgments are returned to Retell.

## Person B's approved migration

The user approved uniqueness constraints on report/callback call IDs. Startup checks both tables for duplicates and adds unique indexes to older databases without altering records. If duplicates exist, startup stops and preserves all data for Person B's review. Likewise, a stale column schema now stops instead of automatically wiping the database. Do not delete real records to work around a startup failure. New test/demo databases get the same constraints directly from the models.

`contracts.py`, frontend types and fixtures, and `.env.example` did not change for this integration. Existing callback consent remains stored in the existing Report model.

## Verification and limits

Run the full backend suite:

```sh
CALL_MODE=simulate .venv/bin/python -m pytest -q
```

Focused integration and migration checks:

```sh
CALL_MODE=simulate .venv/bin/python -m pytest -q tests/test_webhook_gateway.py tests/test_call_id_migration.py
```

Tests use synthetic signing keys and fictional data; they exercise the official SDK, gateway, actual main ASGI app, database persistence, concurrent duplicate intake, authorized callback routing, strict consent, blocked routes, timeout/error handling and log redaction. A restart test confirms duplicate protection persists in SQLite.

Still required before claiming genuine Retell integration: verify the webhook-enabled key and agent configuration in the account; use a working public tunnel to 8002; make a consenting prototype test call; confirm a real `call_analyzed` delivery is acknowledged and stored; save a redacted real payload with Person A/B. Local valid signatures cannot prove the provider's actual key or payload is configured correctly. Cloudflare tunnel network failures are outside these application changes. No public deployment or real outbound calls were performed.

Official references: [Retell signature verification](https://docs.retellai.com/features/secure-webhook), [Retell event delivery](https://docs.retellai.com/features/webhook-overview).

## Latest local results

- **223 backend tests passed**, zero failures/skips/XFAILs; one existing dependency deprecation warning.
- Valid signed intake/callback, invalid/missing signatures, unauthorized agents, bad JSON, gateway route isolation, strict consent, persistent/repeated/concurrent intake deduplication and non-destructive migration tests all passed.
- Both real local listeners were verified as **127.0.0.1:8001** and **127.0.0.1:8002**. Local HTTP probes returned signed acknowledgment **204**, unsigned **401**, malformed JSON **400**, unauthorized agent **403**, and private routes **404**. These runtime probes created no reports.
- Frontend production build and 11 static rendering checks passed; dependency consistency and `git diff --check` passed.
- Actual Retell account delivery and the public tunnel remain unverified. No public tunnel was opened by this implementation.
