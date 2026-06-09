"""
FastAPI Chess Game Server.

Serves the classical chess AI over a small JSON API with CORS for the Vite
frontend. The bot move is computed by `ai_engine` (pure-Python search, no torch).
"""

import logging
import os
import time
from collections import defaultdict, deque
from threading import Lock

import chess
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from ai_engine import DEFAULT_LEVEL, LEVELS, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Chess AI Bot API", version="2.0")

# ---- Rate limiter (sliding window, in-memory) ----
class _RateLimiter:
    """Thread-safe per-IP sliding window rate limiter."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._log: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            dq = self._log[key]
            while dq and dq[0] < now - self._window:
                dq.popleft()
            if len(dq) >= self._max:
                return False
            dq.append(now)
            return True


# 60 requests per minute per IP (generous for a chess game, blocks scrapers/bots)
_rate_limiter = _RateLimiter(max_requests=60, window_seconds=60)


# ---- Body-size limiter middleware ----
class _LimitBodySizeMiddleware(BaseHTTPMiddleware):
    _MAX_BYTES = 4096  # chess FEN + level is well under 1 KB

    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl and int(cl) > self._MAX_BYTES:
            return JSONResponse({"detail": "Request body too large."}, status_code=413)
        return await call_next(request)


app.add_middleware(_LimitBodySizeMiddleware)

# ---- CORS ----
_extra_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://localhost:3000",
        "http://127.0.0.1:5173", "http://127.0.0.1:3000",
        *_extra_origins,
    ],
    allow_credentials=False,          # no cookies/sessions needed
    allow_methods=["GET", "POST"],    # only what the API uses
    allow_headers=["Content-Type"],   # only what the frontend sends
)


# ---- Request / response models ----
_VALID_LEVEL_KEYS = set(LEVELS.keys())

class BotMoveRequest(BaseModel):
    # FEN for a standard position is ≤ 90 chars; 200 gives plenty of room
    current_fen: str = Field(..., min_length=10, max_length=200)
    level: str = Field(DEFAULT_LEVEL, max_length=32)


class BotMoveResponse(BaseModel):
    bot_move: str
    bot_move_san: str
    new_fen: str
    is_check: bool
    is_checkmate: bool
    is_draw: bool
    game_over: bool
    eval_cp: int
    depth: int
    nodes: int
    time_ms: int


# ---- Endpoints ----
@app.get("/")
def read_root():
    return {"message": "Chess AI Bot API is running", "version": "2.0"}


@app.get("/api/levels")
def get_levels():
    """List the available difficulty levels (for the frontend selector)."""
    return {
        "default": DEFAULT_LEVEL,
        "levels": [
            {"key": k, "name": v.name, "elo": v.approx_elo}
            for k, v in LEVELS.items()
        ],
    }


@app.post("/api/bot-move", response_model=BotMoveResponse)
def get_bot_move(request_data: BotMoveRequest, request: Request):
    """Calculate the best countermove for the AI bot."""

    # Rate-limit by client IP
    client_ip = (request.client.host if request.client else "unknown")
    if not _rate_limiter.is_allowed(client_ip):
        raise HTTPException(status_code=429, detail="Too many requests — please slow down.")

    # Whitelist the level (already defaulted, but be explicit)
    level = request_data.level if request_data.level in _VALID_LEVEL_KEYS else DEFAULT_LEVEL

    # Validate FEN — strip to prevent log-injection; chess.Board raises ValueError on bad input
    fen = request_data.current_fen.strip()
    try:
        board = chess.Board(fen)
    except ValueError as e:
        safe_fen = fen[:80].replace("\n", "\\n").replace("\r", "\\r")
        logger.warning("Invalid FEN from %s: %s (fen=%r)", client_ip, e, safe_fen)
        raise HTTPException(status_code=400, detail="Invalid FEN notation.")

    if board.is_game_over():
        raise HTTPException(status_code=400, detail="Game is already over.")

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        raise HTTPException(status_code=400, detail="No legal moves available.")

    try:
        result = engine.search(fen, level)
    except Exception as e:
        logger.exception("AI engine error for %s", client_ip)
        raise HTTPException(status_code=500, detail="AI engine error.")

    if result.move is None:
        raise HTTPException(status_code=500, detail="AI failed to find a valid move.")

    try:
        move = chess.Move.from_uci(result.move)
    except ValueError:
        logger.error("AI returned malformed UCI move: %r", result.move)
        raise HTTPException(status_code=500, detail="AI returned an invalid move.")

    if move not in legal_moves:
        logger.error("AI generated illegal move: %r for position %r", result.move, fen[:60])
        raise HTTPException(status_code=500, detail="AI generated an illegal move.")

    san = board.san(move)
    board.push(move)

    response = BotMoveResponse(
        bot_move=result.move,
        bot_move_san=san,
        new_fen=board.fen(),
        is_check=board.is_check(),
        is_checkmate=board.is_checkmate(),
        is_draw=(
            board.is_stalemate()
            or board.is_insufficient_material()
            or board.is_fifty_moves()
            or board.is_repetition()
        ),
        game_over=board.is_game_over(),
        eval_cp=result.score_cp,
        depth=result.depth,
        nodes=result.nodes,
        time_ms=result.time_ms,
    )
    logger.info(
        "[%s][%s] %s (%s) eval=%dcp depth=%d %dms",
        client_ip, level, san, result.move, result.score_cp, result.depth, result.time_ms,
    )
    return response


if __name__ == "__main__":
    import uvicorn
    # Bind to localhost only in direct-run mode; use a reverse proxy for production.
    uvicorn.run(app, host="127.0.0.1", port=8000)
