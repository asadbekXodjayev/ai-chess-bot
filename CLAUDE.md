# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A web app to play chess against a custom AI. Python/FastAPI backend computes bot
moves; a React/Vite frontend renders the board and game flow. Backend and
frontend are deployed/run separately and talk over a small JSON API.

## Commands

Backend (run from `backend/`, Windows venv shown):
```powershell
venv\Scripts\python.exe -m uvicorn main:app --reload   # dev server on :8000
venv\Scripts\python.exe ai_engine.py                   # engine self-test (mate/tactics/timing)
venv\Scripts\python.exe -m pytest                      # (no test suite yet)
```

Frontend (run from `frontend/`):
```bash
npm run dev       # Vite dev server on :5173 (proxies nothing; calls :8000 directly)
npm run build     # production build -> dist/
npm run lint      # eslint, --max-warnings 0
```

Quick engine/API sanity without a browser:
```bash
# Engine in-process (fast, no server):
venv\Scripts\python.exe -c "from ai_engine import get_best_move; print(get_best_move('<FEN>', 'hard'))"
# Live API:
curl -X POST http://127.0.0.1:8000/api/bot-move -H "Content-Type: application/json" \
  -d '{"current_fen":"<FEN>","level":"expert"}'
```

There is no test runner wired up; `ai_engine.py`'s `__main__` block is the de-facto
regression check (mate-in-1, free-piece tactic, per-position timing).

## Architecture

Request flow: frontend (`chess.js` validates the player's move locally) → POST
`/api/bot-move` with the current FEN + difficulty `level` → `main.py` validates,
calls `ai_engine.engine.search(fen, level)`, re-validates the returned move, applies
it, and returns the new FEN + SAN + eval + game-state flags. The frontend renders
the new FEN. **The board's source of truth is the FEN passed back and forth** — the
backend never holds game state between requests (the engine is stateless per call;
its transposition table is rebuilt each `search`).

### `backend/ai_engine.py` — the engine (this is where strength/speed lives)
Pure-Python classical engine. **It deliberately does NOT import torch** — torch
import alone took >60s in this environment and the old NN was only trained to mimic
a material heuristic, so it was removed from the request path. Key pieces:
- `ChessEngine.search(fen, level)` — iterative-deepening root; returns a
  `SearchResult` (uci move, score_cp from side-to-move, depth, nodes, time_ms).
- `_negamax` — alpha-beta with transposition table, null-move pruning, late-move
  reductions, check extensions, killer/history move ordering.
- `_quiescence` — capture/check search to kill the horizon effect (has its own
  time check — important: without it, tactical positions blow past the time budget).
- `evaluate` — tapered (midgame↔endgame) eval over **raw integer bitboards**
  (`board.pieces_mask`, `chess.scan_forward`); material + PSTs + bishop pair +
  pawn structure (doubled/isolated/passed) + rook files + tempo. This is the
  hottest function — keep it allocation-free (no `piece_map()`/`SquareSet`).
- `OPENING_BOOK` — small FEN→moves dict for sane, varied openings.
- `LEVELS` / `DEFAULT_LEVEL` — difficulty presets controlling time budget, max
  depth, softmax `temperature` (weakening via Boltzmann sampling over root scores)
  and `blunder` probability. **Sampled levels (temperature>0) require exact root
  scores, so `search` skips alpha-beta window-narrowing at the root for them**;
  strong levels (`hard`+) keep narrowing and always play the best move.

Conventions: PST tables are written a8-first; White indexes `sq ^ 56`, Black `sq`.
Mate scores are `±MATE_SCORE` adjusted by ply; anything above `MATE_THRESHOLD` is
"mate in n". The TT key is `board._transposition_key()` (fast, incremental) — not
`polyglot.zobrist_hash` (recomputed from scratch, was a measured bottleneck).

### `backend/main.py` — FastAPI server
`POST /api/bot-move` (body: `current_fen`, optional `level`) and `GET /api/levels`.
CORS is locked to localhost:5173/3000. SAN is computed **before** pushing the move.
Move legality is double-checked even though the engine only returns legal moves.

### `frontend/src/App.jsx` — single-file React app (no router/state lib)
React 18 + Vite + Tailwind v3 (not Next.js — global stack defaults don't apply).
Holds all state with hooks. Notable: `difficultyRef` mirrors `difficulty` so the
async `makeBotMove` closure isn't stale; `tryMove` is shared by drag (`onPieceDrop`)
and click-to-move (`onSquareClick`); the eval bar converts the bot-perspective
`eval_cp` to White's perspective (`whiteEval = turn()==='b' ? eval_cp : -eval_cp`).
`SoundController` synthesizes all sounds via the Web Audio API (no audio assets).

### Legacy / not in the request path
`train_ai*.py`, `train_model.py`, `chess_model*.pth` are the obsolete NN training
artifacts. They still reference torch; the live app ignores them. `BUG_FIXES.md`,
`UPDATES.md`, `TRAINING.md` describe the older NN-based design and are stale w.r.t.
the current classical engine.

## Gotchas
- `chess.Board.pieces(...)` returns a `SquareSet`, not an int — use `len(...)` for
  popcount or `board.pieces_mask(...)` for a raw int bitboard.
- Keep `level` keys identical between `ai_engine.LEVELS` and `frontend` `DIFFICULTIES`.
- The frontend hardcodes `http://localhost:8000`; change `API_URL` in `App.jsx` if
  the backend host/port moves.
