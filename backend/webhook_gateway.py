"""Webhook-only public ingress. Tunnel this process on 127.0.0.1:8002, never the main app.

Imports configuration (root .env) and signature security only: no database, engine,
main router, or outbound Retell caller is loaded by this application.
"""
import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request, Response

from app.config import RETELL_API_KEY
from app.voice.security import verify_signature

BACKEND_WEBHOOK = "http://127.0.0.1:8001/retell/webhook"
FORWARD_DEADLINE_S = 5.0  # Overall forwarding deadline, below Retell's 10-second timeout.


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(4.0, connect=1.0), trust_env=False, follow_redirects=False,
    ) as client:
        app.state.backend_client = client
        yield


app = FastAPI(
    title="HandoffProof webhook gateway", docs_url=None, redoc_url=None,
    openapi_url=None, redirect_slashes=False, lifespan=lifespan,
)


@app.post("/retell/webhook")
async def receive_webhook(request: Request) -> Response:
    raw = await request.body()
    signature = request.headers.get("x-retell-signature", "")
    if not verify_signature(raw, signature, RETELL_API_KEY):
        raise HTTPException(401, "Invalid Retell signature")
    try:
        # The target is fixed. URL, Host, forwarding headers and query parameters
        # from the incoming request can never select another destination.
        upstream = await asyncio.wait_for(
            request.app.state.backend_client.post(
                BACKEND_WEBHOOK, content=raw,
                headers={"Content-Type": "application/json", "X-Retell-Signature": signature},
            ), timeout=FORWARD_DEADLINE_S,
        )
    except (asyncio.TimeoutError, httpx.TimeoutException):
        raise HTTPException(504, "Webhook backend timed out") from None
    except httpx.RequestError:
        raise HTTPException(503, "Webhook backend unavailable") from None
    if 200 <= upstream.status_code < 300:
        return Response(content=upstream.content, status_code=upstream.status_code)
    if upstream.status_code in (400, 401, 403):
        # Keep rejection semantics, but never echo a local server's response body.
        raise HTTPException(upstream.status_code, "Webhook rejected")
    raise HTTPException(502, "Webhook backend did not acknowledge")
