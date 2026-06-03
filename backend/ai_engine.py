"""
Chess AI Engine - fast, pure-Python classical engine.

Design goals (replacing the previous torch-based NN engine):
  * No PyTorch in the request path -> instant startup, no per-move tensor overhead.
  * Real search strength: negamax + alpha-beta with a transposition table,
    iterative deepening, principal-variation move ordering, killer/history
    heuristics, quiescence search and null-move pruning.
  * A tapered hand-crafted evaluation (material, piece-square tables, bishop
    pair, pawn structure, rook files, king safety) that on its own plays at a
    much higher level than the old "neural net trained to copy material count".
  * Selectable difficulty so the bot can be a gentle ~600 sparring partner or a
    ~2000+ tactician.

The public surface stays compatible with the old module:
    get_best_move(fen_string) -> Optional[str]   # UCI move
plus a richer entry point used by the API:
    ai_instance.search(fen, level) -> SearchResult
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import chess

# ---------------------------------------------------------------------------
# Evaluation constants
# ---------------------------------------------------------------------------

# Piece values (centipawns), midgame / endgame.
PIECE_VALUE_MG = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 950,
    chess.KING: 0,
}
PIECE_VALUE_EG = {
    chess.PAWN: 120,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 540,
    chess.QUEEN: 960,
    chess.KING: 0,
}

# Phase weights used to taper between mid- and end-game evaluation.
PHASE_WEIGHTS = {
    chess.PAWN: 0,
    chess.KNIGHT: 1,
    chess.BISHOP: 1,
    chess.ROOK: 2,
    chess.QUEEN: 4,
    chess.KING: 0,
}
TOTAL_PHASE = 24  # 4 knights/bishops + 4 rooks + 2 queens

MATE_SCORE = 1_000_000
MATE_THRESHOLD = MATE_SCORE - 1000  # scores above this are "mate in n"

# Piece-square tables. Written from White's point of view, rank 8 first
# (index 0 == a8). White reads table[sq ^ 56]; Black reads table[sq].
# fmt: off
PAWN_PST = [
     0,   0,   0,   0,   0,   0,   0,   0,
    50,  50,  50,  50,  50,  50,  50,  50,
    10,  10,  20,  30,  30,  20,  10,  10,
     5,   5,  10,  25,  25,  10,   5,   5,
     0,   0,   0,  20,  20,   0,   0,   0,
     5,  -5, -10,   0,   0, -10,  -5,   5,
     5,  10,  10, -20, -20,  10,  10,   5,
     0,   0,   0,   0,   0,   0,   0,   0,
]

KNIGHT_PST = [
   -50, -40, -30, -30, -30, -30, -40, -50,
   -40, -20,   0,   0,   0,   0, -20, -40,
   -30,   0,  10,  15,  15,  10,   0, -30,
   -30,   5,  15,  20,  20,  15,   5, -30,
   -30,   0,  15,  20,  20,  15,   0, -30,
   -30,   5,  10,  15,  15,  10,   5, -30,
   -40, -20,   0,   5,   5,   0, -20, -40,
   -50, -40, -30, -30, -30, -30, -40, -50,
]

BISHOP_PST = [
   -20, -10, -10, -10, -10, -10, -10, -20,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -10,   0,   5,  10,  10,   5,   0, -10,
   -10,   5,   5,  10,  10,   5,   5, -10,
   -10,   0,  10,  10,  10,  10,   0, -10,
   -10,  10,  10,  10,  10,  10,  10, -10,
   -10,   5,   0,   0,   0,   0,   5, -10,
   -20, -10, -10, -10, -10, -10, -10, -20,
]

ROOK_PST = [
     0,   0,   0,   0,   0,   0,   0,   0,
     5,  10,  10,  10,  10,  10,  10,   5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
    -5,   0,   0,   0,   0,   0,   0,  -5,
     0,   0,   0,   5,   5,   0,   0,   0,
]

QUEEN_PST = [
   -20, -10, -10,  -5,  -5, -10, -10, -20,
   -10,   0,   0,   0,   0,   0,   0, -10,
   -10,   0,   5,   5,   5,   5,   0, -10,
    -5,   0,   5,   5,   5,   5,   0,  -5,
     0,   0,   5,   5,   5,   5,   0,  -5,
   -10,   5,   5,   5,   5,   5,   0, -10,
   -10,   0,   5,   0,   0,   0,   0, -10,
   -20, -10, -10,  -5,  -5, -10, -10, -20,
]

KING_PST_MG = [
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -30, -40, -40, -50, -50, -40, -40, -30,
   -20, -30, -30, -40, -40, -30, -30, -20,
   -10, -20, -20, -20, -20, -20, -20, -10,
    20,  20,   0,   0,   0,   0,  20,  20,
    20,  30,  10,   0,   0,  10,  30,  20,
]

KING_PST_EG = [
   -50, -40, -30, -20, -20, -30, -40, -50,
   -30, -20, -10,   0,   0, -10, -20, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -10,  30,  40,  40,  30, -10, -30,
   -30, -10,  30,  40,  40,  30, -10, -30,
   -30, -10,  20,  30,  30,  20, -10, -30,
   -30, -30,   0,   0,   0,   0, -30, -30,
   -50, -30, -30, -30, -30, -30, -30, -50,
]
# fmt: on

PST_MG = {
    chess.PAWN: PAWN_PST,
    chess.KNIGHT: KNIGHT_PST,
    chess.BISHOP: BISHOP_PST,
    chess.ROOK: ROOK_PST,
    chess.QUEEN: QUEEN_PST,
    chess.KING: KING_PST_MG,
}
PST_EG = {
    chess.PAWN: PAWN_PST,
    chess.KNIGHT: KNIGHT_PST,
    chess.BISHOP: BISHOP_PST,
    chess.ROOK: ROOK_PST,
    chess.QUEEN: QUEEN_PST,
    chess.KING: KING_PST_EG,
}

# Pawn-structure / piece tuning (centipawns).
BISHOP_PAIR_BONUS = 35
DOUBLED_PAWN_PENALTY = 18
ISOLATED_PAWN_PENALTY = 16
PASSED_PAWN_BONUS = [0, 8, 12, 22, 40, 70, 120, 0]  # indexed by rank advanced
ROOK_OPEN_FILE = 22
ROOK_SEMI_OPEN_FILE = 11
TEMPO_BONUS = 12

FILE_MASKS = [chess.BB_FILES[f] for f in range(8)]
ADJACENT_FILES = [
    (FILE_MASKS[f - 1] if f > 0 else 0) | (FILE_MASKS[f + 1] if f < 7 else 0)
    for f in range(8)
]


def _build_passed_masks():
    """For each (color, square): the enemy-pawn-free zone that defines a passer
    (own file + adjacent files, on every rank ahead of the pawn)."""
    white = [0] * 64
    black = [0] * 64
    for sq in range(64):
        f = sq & 7
        r = sq >> 3
        files = FILE_MASKS[f] | ADJACENT_FILES[f]
        ahead_w = 0
        for rr in range(r + 1, 8):
            ahead_w |= chess.BB_RANKS[rr]
        ahead_b = 0
        for rr in range(0, r):
            ahead_b |= chess.BB_RANKS[rr]
        white[sq] = files & ahead_w
        black[sq] = files & ahead_b
    return {chess.WHITE: white, chess.BLACK: black}


PASSED_MASK = _build_passed_masks()


# ---------------------------------------------------------------------------
# Difficulty levels
# ---------------------------------------------------------------------------

@dataclass
class Level:
    """A difficulty preset.

    time_limit  : soft wall-clock budget per move (seconds).
    max_depth   : hard cap on iterative-deepening depth.
    temperature : softmax temperature over root scores (pawns). 0 == always
                  pick the best move; higher == weaker / more human-like.
    blunder     : probability of throwing away the search and playing a random
                  legal move (models a low-rated player's hangs).
    """

    name: str
    approx_elo: int
    time_limit: float
    max_depth: int
    temperature: float
    blunder: float


LEVELS: Dict[str, Level] = {
    "beginner":     Level("beginner",     600,  0.05, 1,  1.60, 0.20),
    "easy":         Level("easy",         1000, 0.15, 2,  0.80, 0.06),
    "intermediate": Level("intermediate", 1400, 0.40, 3,  0.30, 0.0),
    "hard":         Level("hard",         1800, 0.80, 4,  0.0,  0.0),
    "expert":       Level("expert",       2000, 1.50, 8,  0.0,  0.0),
    "max":          Level("max",          2200, 3.00, 64, 0.0,  0.0),
}
DEFAULT_LEVEL = "hard"


@dataclass
class SearchResult:
    move: Optional[str]          # UCI string
    score_cp: int                # centipawns from side-to-move perspective
    depth: int
    nodes: int
    time_ms: int


# ---------------------------------------------------------------------------
# A compact opening book (board FEN piece+turn -> good replies in UCI).
# Keeps the early game sane and varied without a heavy polyglot file.
# ---------------------------------------------------------------------------

def _bk(board: chess.Board) -> str:
    """Book key: piece placement + side to move (ignores clocks/castling/ep)."""
    parts = board.fen().split(" ")
    return parts[0] + " " + parts[1]


OPENING_BOOK: Dict[str, List[str]] = {
    # Start position: e4 / d4 / c4 / Nf3
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w":
        ["e2e4", "d2d4", "c2c4", "g1f3"],
    # 1.e4 -> e5 / c5 / e6 / c6
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b":
        ["e7e5", "c7c5", "e7e6", "c7c6"],
    # 1.d4 -> d5 / Nf6
    "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b":
        ["d7d5", "g8f6", "e7e6"],
    # 1.e4 e5 -> Nf3
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w":
        ["g1f3", "f1c4"],
    # 1.e4 e5 2.Nf3 -> Nc6
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b":
        ["b8c6", "g8f6"],
    # 1.e4 c5 (Sicilian) -> Nf3
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w":
        ["g1f3", "b1c3", "c2c3"],
    # 1.d4 d5 -> c4 (Queen's Gambit) / Nf3
    "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w":
        ["c2c4", "g1f3"],
    # 1.d4 Nf6 -> c4 / Nf3
    "rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w":
        ["c2c4", "g1f3"],
}


# ---------------------------------------------------------------------------
# The engine
# ---------------------------------------------------------------------------

class ChessEngine:
    def __init__(self) -> None:
        self.tt: Dict[int, Tuple[int, int, int, Optional[chess.Move]]] = {}
        # killer moves [ply] -> [move, move]; history[(from,to)] -> score
        self.killers: List[List[Optional[chess.Move]]] = []
        self.history: Dict[Tuple[int, int], int] = {}
        self.nodes = 0
        self.deadline = 0.0
        self.stop = False

    # --- evaluation ------------------------------------------------------

    def evaluate(self, board: chess.Board) -> int:
        """Static evaluation in centipawns from White's perspective.

        Uses raw integer bitboards throughout (no SquareSet / piece_map
        allocation) for speed, since this is the hottest function in search.
        """
        mg = 0
        eg = 0
        phase = 0
        scan = chess.scan_forward

        white = board.occupied_co[chess.WHITE]

        # Material + piece-square tables, by piece type.
        for pt in range(1, 7):
            bb = board.pieces_mask(pt, chess.WHITE) | board.pieces_mask(pt, chess.BLACK)
            vmg = PIECE_VALUE_MG[pt]
            veg = PIECE_VALUE_EG[pt]
            pmg = PST_MG[pt]
            peg = PST_EG[pt]
            ph = PHASE_WEIGHTS[pt]
            for sq in scan(bb):
                phase += ph
                if (1 << sq) & white:
                    idx = sq ^ 56
                    mg += vmg + pmg[idx]
                    eg += veg + peg[idx]
                else:
                    mg -= vmg + pmg[sq]
                    eg -= veg + peg[sq]

        # Bishop pair.
        if board.pieces_mask(chess.BISHOP, chess.WHITE).bit_count() >= 2:
            mg += BISHOP_PAIR_BONUS
            eg += BISHOP_PAIR_BONUS
        if board.pieces_mask(chess.BISHOP, chess.BLACK).bit_count() >= 2:
            mg -= BISHOP_PAIR_BONUS
            eg -= BISHOP_PAIR_BONUS

        # Pawn structure + rook files.
        wp = board.pieces_mask(chess.PAWN, chess.WHITE)
        bp = board.pieces_mask(chess.PAWN, chess.BLACK)
        for own, enemy, sign, color in ((wp, bp, 1, chess.WHITE), (bp, wp, -1, chess.BLACK)):
            file_counts = [(own & FILE_MASKS[f]).bit_count() for f in range(8)]
            for sq in scan(own):
                f = sq & 7
                if file_counts[f] > 1:  # doubled
                    mg -= sign * DOUBLED_PAWN_PENALTY
                    eg -= sign * DOUBLED_PAWN_PENALTY
                if not (own & ADJACENT_FILES[f]):  # isolated
                    mg -= sign * ISOLATED_PAWN_PENALTY
                    eg -= sign * ISOLATED_PAWN_PENALTY
                if not (enemy & PASSED_MASK[color][sq]):  # passed
                    advanced = (sq >> 3) if color == chess.WHITE else 7 - (sq >> 3)
                    bonus = PASSED_PAWN_BONUS[advanced]
                    mg += sign * bonus
                    eg += sign * (bonus * 3 // 2)

            for sq in scan(board.pieces_mask(chess.ROOK, color)):
                f = sq & 7
                if file_counts[f] == 0:
                    if (enemy & FILE_MASKS[f]) == 0:
                        mg += sign * ROOK_OPEN_FILE
                        eg += sign * (ROOK_OPEN_FILE // 2)
                    else:
                        mg += sign * ROOK_SEMI_OPEN_FILE

        # Taper between phases.
        if phase > TOTAL_PHASE:
            phase = TOTAL_PHASE
        score = (mg * phase + eg * (TOTAL_PHASE - phase)) // TOTAL_PHASE

        # Tempo (small bonus for the side to move).
        score += TEMPO_BONUS if board.turn == chess.WHITE else -TEMPO_BONUS
        return score

    # --- move ordering ---------------------------------------------------

    def _order_moves(
        self, board: chess.Board, moves: List[chess.Move], tt_move: Optional[chess.Move], ply: int
    ) -> List[chess.Move]:
        killers = self.killers[ply] if ply < len(self.killers) else [None, None]

        def score(m: chess.Move) -> int:
            if tt_move is not None and m == tt_move:
                return 1_000_000
            if board.is_capture(m):
                victim = board.piece_type_at(m.to_square)
                attacker = board.piece_type_at(m.from_square)
                vv = PIECE_VALUE_MG.get(victim, 100) if victim else 100  # en passant
                av = PIECE_VALUE_MG.get(attacker, 100)
                return 100_000 + vv * 10 - av
            if m.promotion:
                return 90_000 + PIECE_VALUE_MG.get(m.promotion, 0)
            if m == killers[0]:
                return 80_000
            if m == killers[1]:
                return 79_000
            return self.history.get((m.from_square, m.to_square), 0)

        return sorted(moves, key=score, reverse=True)

    # --- quiescence ------------------------------------------------------

    def _quiescence(self, board: chess.Board, alpha: int, beta: int, qdepth: int = 0) -> int:
        self.nodes += 1

        if self.nodes & 2047 == 0 and time.perf_counter() >= self.deadline:
            self.stop = True
            return alpha

        in_check = board.is_check()
        if in_check and qdepth > -6:
            # In check we must consider every evasion (can't stand pat).
            moves = list(board.legal_moves)
            if not moves:
                return -MATE_SCORE  # checkmate
        else:
            stand_pat = self.evaluate(board)
            if board.turn == chess.BLACK:
                stand_pat = -stand_pat
            if stand_pat >= beta:
                return beta
            if stand_pat > alpha:
                alpha = stand_pat
            # Only search captures / promotions when not in check.
            moves = [m for m in board.legal_moves if board.is_capture(m) or m.promotion]

        def cap_score(m: chess.Move) -> int:
            victim = board.piece_type_at(m.to_square)
            vv = PIECE_VALUE_MG.get(victim, 100) if victim else 100
            attacker = board.piece_type_at(m.from_square)
            av = PIECE_VALUE_MG.get(attacker, 100)
            return vv * 10 - av + (PIECE_VALUE_MG.get(m.promotion, 0) if m.promotion else 0)

        moves.sort(key=cap_score, reverse=True)

        for m in moves:
            board.push(m)
            score = -self._quiescence(board, -beta, -alpha, qdepth - 1)
            board.pop()
            if self.stop:
                return alpha
            if score >= beta:
                return beta
            if score > alpha:
                alpha = score
        return alpha

    # --- negamax ---------------------------------------------------------

    def _negamax(
        self, board: chess.Board, depth: int, alpha: int, beta: int, ply: int, allow_null: bool
    ) -> int:
        self.nodes += 1

        if self.nodes & 2047 == 0 and time.perf_counter() >= self.deadline:
            self.stop = True
            return 0

        # Cheap draw checks (avoid the move-generating is_* helpers).
        if board.halfmove_clock >= 100 or board.is_insufficient_material():
            return 0

        alpha_orig = alpha
        key = board._transposition_key()
        tt_entry = self.tt.get(key)
        tt_move = None
        if tt_entry is not None:
            tt_depth, tt_flag, tt_score, tt_move = tt_entry
            if tt_depth >= depth:
                if tt_flag == 0:  # exact
                    return tt_score
                if tt_flag == 1 and tt_score >= beta:  # lower bound
                    return tt_score
                if tt_flag == 2 and tt_score <= alpha:  # upper bound
                    return tt_score

        if depth <= 0:
            return self._quiescence(board, alpha, beta)

        in_check = board.is_check()

        # Terminal detection (single move generation, reused below).
        legal = list(board.legal_moves)
        if not legal:
            return -MATE_SCORE + ply if in_check else 0  # checkmate vs stalemate

        # Null-move pruning: give the opponent a free move; if we're still
        # winning, prune. Disabled in check and in likely-zugzwang endgames.
        if (
            allow_null
            and not in_check
            and depth >= 3
            and self._has_non_pawn_material(board)
            and beta < MATE_THRESHOLD
        ):
            board.push(chess.Move.null())
            score = -self._negamax(board, depth - 3, -beta, -beta + 1, ply + 1, False)
            board.pop()
            if self.stop:
                return 0
            if score >= beta:
                return beta

        moves = self._order_moves(board, legal, tt_move, ply)

        best_score = -MATE_SCORE - 1
        best_move: Optional[chess.Move] = None

        for i, m in enumerate(moves):
            board.push(m)
            # Check extension keeps tactics sharp.
            ext = 1 if board.is_check() else 0
            new_depth = depth - 1 + ext

            # Late-move reductions for quiet moves deep in the list.
            if (
                ext == 0
                and depth >= 3
                and i >= 4
                and not board.is_capture(m)
                and not m.promotion
            ):
                score = -self._negamax(board, new_depth - 1, -alpha - 1, -alpha, ply + 1, True)
                if score > alpha:
                    score = -self._negamax(board, new_depth, -beta, -alpha, ply + 1, True)
            else:
                score = -self._negamax(board, new_depth, -beta, -alpha, ply + 1, True)
            board.pop()

            if self.stop:
                return 0

            if score > best_score:
                best_score = score
                best_move = m
            if score > alpha:
                alpha = score
            if alpha >= beta:
                # Beta cutoff: record killer / history for quiet moves.
                if not board.is_capture(m) and not m.promotion:
                    self._store_killer(m, ply)
                    self.history[(m.from_square, m.to_square)] = (
                        self.history.get((m.from_square, m.to_square), 0) + depth * depth
                    )
                break

        # Store in transposition table.
        if not self.stop:
            if best_score <= alpha_orig:
                flag = 2  # upper bound
            elif best_score >= beta:
                flag = 1  # lower bound
            else:
                flag = 0  # exact
            self.tt[key] = (depth, flag, best_score, best_move)

        return best_score

    def _store_killer(self, move: chess.Move, ply: int) -> None:
        while len(self.killers) <= ply:
            self.killers.append([None, None])
        if self.killers[ply][0] != move:
            self.killers[ply][1] = self.killers[ply][0]
            self.killers[ply][0] = move

    @staticmethod
    def _has_non_pawn_material(board: chess.Board) -> bool:
        color = board.turn
        return bool(
            board.pieces(chess.KNIGHT, color)
            or board.pieces(chess.BISHOP, color)
            or board.pieces(chess.ROOK, color)
            or board.pieces(chess.QUEEN, color)
        )

    # --- root search -----------------------------------------------------

    def search(self, fen: str, level: str = DEFAULT_LEVEL) -> SearchResult:
        try:
            board = chess.Board(fen)
        except ValueError:
            return SearchResult(None, 0, 0, 0, 0)

        if board.is_game_over():
            return SearchResult(None, 0, 0, 0, 0)

        legal = list(board.legal_moves)
        if not legal:
            return SearchResult(None, 0, 0, 0, 0)

        cfg = LEVELS.get(level, LEVELS[DEFAULT_LEVEL])
        start = time.perf_counter()

        # Opening book (skip on the strongest level's deepest study? keep it -
        # book moves are sound and add variety on every level).
        book_moves = OPENING_BOOK.get(_bk(board))
        if book_moves:
            legal_uci = {mv.uci() for mv in legal}
            choices = [u for u in book_moves if u in legal_uci]
            if choices:
                return SearchResult(random.choice(choices), 0, 0, 0,
                                    int((time.perf_counter() - start) * 1000))

        # Occasional deliberate blunder for low difficulty levels.
        if cfg.blunder and random.random() < cfg.blunder:
            return SearchResult(random.choice(legal).uci(), 0, 0, 0,
                                int((time.perf_counter() - start) * 1000))

        if len(legal) == 1:
            return SearchResult(legal[0].uci(), 0, 1, 0,
                                int((time.perf_counter() - start) * 1000))

        # Fresh search state.
        self.tt = {}
        self.killers = []
        self.history = {}
        self.nodes = 0
        self.stop = False
        self.deadline = start + cfg.time_limit

        best_move = legal[0]
        best_score = 0
        completed_depth = 0
        # Root scores from the deepest completed iteration (for difficulty softmax).
        root_scores: Dict[chess.Move, int] = {}

        # When weakening the bot with softmax sampling we need EXACT scores for
        # every root move, so we must not let one move's result narrow the
        # window for the next. Strong levels keep the alpha-beta narrowing for
        # speed and simply track the best move.
        exact_scores = cfg.temperature > 0

        for depth in range(1, cfg.max_depth + 1):
            full = -MATE_SCORE - 1
            alpha, beta = full, MATE_SCORE + 1
            tt_entry = self.tt.get(board._transposition_key())
            tt_move = tt_entry[3] if tt_entry else best_move
            ordered = self._order_moves(board, legal, tt_move, 0)

            iter_best_move = None
            iter_best_score = full
            iter_scores: Dict[chess.Move, int] = {}

            for m in ordered:
                board.push(m)
                root_alpha = full if exact_scores else alpha
                score = -self._negamax(board, depth - 1, -beta, -root_alpha, 1, True)
                board.pop()
                if self.stop:
                    break
                iter_scores[m] = score
                if score > iter_best_score:
                    iter_best_score = score
                    iter_best_move = m
                if score > alpha:
                    alpha = score

            if self.stop:
                break

            best_move = iter_best_move or best_move
            best_score = iter_best_score
            root_scores = iter_scores
            completed_depth = depth

            # Stop early on forced mate.
            if abs(best_score) >= MATE_THRESHOLD:
                break
            # Predictive cutoff: the next iteration costs several times the last,
            # so don't start one we almost certainly can't finish in budget.
            if time.perf_counter() - start > cfg.time_limit * 0.45:
                break

        # Difficulty: optionally pick a weaker move via softmax over root scores.
        chosen = best_move
        if cfg.temperature > 0 and root_scores:
            chosen = self._sample_move(root_scores, cfg.temperature)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return SearchResult(chosen.uci(), best_score, completed_depth, self.nodes, elapsed_ms)

    @staticmethod
    def _sample_move(scores: Dict[chess.Move, int], temperature: float) -> chess.Move:
        """Boltzmann sampling over root move scores (temperature in pawns)."""
        items = list(scores.items())
        best = max(s for _, s in items)
        # Scale by 100 cp = 1 pawn; temperature is in pawns.
        t = max(temperature, 1e-3) * 100.0
        weights = [math.exp(min(0.0, (s - best)) / t) for _, s in items]
        total = sum(weights)
        r = random.random() * total
        acc = 0.0
        for (mv, _), w in zip(items, weights):
            acc += w
            if r <= acc:
                return mv
        return items[0][0]


# ---------------------------------------------------------------------------
# Module-level singleton + backwards-compatible API
# ---------------------------------------------------------------------------

engine = ChessEngine()
ai_instance = engine  # backwards-compatible alias


def get_best_move(fen_string: str, level: str = DEFAULT_LEVEL) -> Optional[str]:
    """Return the best move (UCI) for the given FEN, or None."""
    return engine.search(fen_string, level).move


if __name__ == "__main__":
    # Quick self-test.
    tests = [
        ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "start"),
        ("6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1", "rook endgame"),
        ("rnbqkbnr/ppp2ppp/8/3pp3/6PQ/8/PPPPPP1P/RNB1KBNR b KQkq - 1 3", "tactic"),
    ]
    for fen, name in tests:
        r = engine.search(fen, "expert")
        print(f"{name:14s} -> {r.move}  score={r.score_cp}cp depth={r.depth} "
              f"nodes={r.nodes} {r.time_ms}ms")
