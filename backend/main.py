"""
FastAPI Chess Game Server.

Serves the classical chess AI over a small JSON API with CORS for the Vite
frontend. The bot move is computed by `ai_engine` (pure-Python search, no torch).
"""

import logging
from typing import Optional

import chess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai_engine import DEFAULT_LEVEL, LEVELS, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Chess AI Bot API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://localhost:3000",
        "http://127.0.0.1:5173", "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BotMoveRequest(BaseModel):
    current_fen: str
    level: str = DEFAULT_LEVEL


class BotMoveResponse(BaseModel):
    bot_move: str          # UCI, e.g. "e2e4"
    bot_move_san: str      # human notation, e.g. "e4" / "Nxf7+"
    new_fen: str
    is_check: bool
    is_checkmate: bool
    is_draw: bool
    game_over: bool
    eval_cp: int           # evaluation (centipawns, +ve = bot is better)
    depth: int             # search depth reached
    nodes: int             # nodes searched
    time_ms: int           # think time


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
def get_bot_move(request: BotMoveRequest):
    """Calculate the best countermove for the AI bot."""
    try:
        board = chess.Board(request.current_fen)
    except ValueError as e:
        logger.warning(f"Invalid FEN: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid FEN notation: {e}")

    if board.is_game_over():
        raise HTTPException(status_code=400, detail="Game is already over")

    legal_moves = list(board.legal_moves)
    if not legal_moves:
        raise HTTPException(status_code=400, detail="No legal moves available")

    level = request.level if request.level in LEVELS else DEFAULT_LEVEL

    try:
        result = engine.search(request.current_fen, level)
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("AI engine error")
        raise HTTPException(status_code=500, detail=f"AI engine error: {e}")

    if result.move is None:
        raise HTTPException(status_code=500, detail="AI failed to find a valid move")

    try:
        move = chess.Move.from_uci(result.move)
    except ValueError:
        raise HTTPException(status_code=500, detail=f"Invalid move from AI: {result.move}")

    if move not in legal_moves:
        logger.error(f"AI generated illegal move: {result.move}")
        raise HTTPException(status_code=500, detail="AI generated illegal move")

    # SAN must be computed BEFORE pushing the move.
    san = board.san(move)
    board.push(move)

    # eval_cp is from the side that just moved (the bot). search() returns the
    # score from the moving side's perspective already.
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
        f"[{level}] {san} ({result.move}) "
        f"eval={result.score_cp}cp depth={result.depth} {result.time_ms}ms"
    )
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
