import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import router as api_router
from app.config import CALL_MODE, CORS_ORIGINS, LADDER_ENABLED, LADDER_TICK_S, TIMING_PROFILE
from app.db import init_db
from app.engine import callback_jobs, ladder
from app.voice.webhooks import router as retell_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("handoffproof")


async def ladder_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(ladder.tick)
        except Exception as exc:
            log.error('Ladder tick failed (%s); no payload was logged', type(exc).__name__)
        await asyncio.sleep(LADDER_TICK_S)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    callback_jobs.recover_interrupted()
    log.info("HandoffProof up | CALL_MODE=%s | TIMING_PROFILE=%s", CALL_MODE, TIMING_PROFILE)
    task = asyncio.create_task(ladder_loop()) if LADDER_ENABLED else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="HandoffProof", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router)
app.include_router(retell_router)


@app.exception_handler(SQLAlchemyError)
async def database_unavailable(request, exc):
    log.error('Database operation failed (%s); sensitive parameters suppressed', type(exc).__name__)
    return JSONResponse(status_code=503, content={'detail': 'Local storage operation unavailable; no successful acknowledgment was issued'})


@app.get("/health")
def health() -> dict:
    return {"ok": True, "call_mode": CALL_MODE, "timing_profile": TIMING_PROFILE}
