import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.config import CALL_MODE, CORS_ORIGINS, LADDER_TICK_S, TIMING_PROFILE
from app.db import init_db
from app.engine import ladder
from app.voice.webhooks import router as retell_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("handoffproof")


async def ladder_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(ladder.tick)
        except Exception:
            log.exception("ladder tick failed")
        await asyncio.sleep(LADDER_TICK_S)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    log.info("HandoffProof up | CALL_MODE=%s | TIMING_PROFILE=%s", CALL_MODE, TIMING_PROFILE)
    task = asyncio.create_task(ladder_loop())
    yield
    task.cancel()


app = FastAPI(title="HandoffProof", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router)
app.include_router(retell_router)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "call_mode": CALL_MODE, "timing_profile": TIMING_PROFILE}
