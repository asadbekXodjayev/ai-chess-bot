import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Chessboard } from 'react-chessboard';
import { Chess } from 'chess.js';

// Web Audio API Sound Controller (Chess.com-style sounds)
class SoundController {
  constructor() {
    this.audioContext = null;
  }

  init() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (this.audioContext.state === 'suspended') {
      this.audioContext.resume();
    }
  }

  playMoveSound() {
    this.init();
    const t = this.audioContext.currentTime;
    const osc = this.audioContext.createOscillator();
    const gain = this.audioContext.createGain();
    const filter = this.audioContext.createBiquadFilter();

    osc.connect(filter);
    filter.connect(gain);
    gain.connect(this.audioContext.destination);

    osc.type = 'sine';
    osc.frequency.setValueAtTime(180, t);
    osc.frequency.exponentialRampToValueAtTime(80, t + 0.08);

    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(400, t);

    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(0.5, t + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.08);

    osc.start(t);
    osc.stop(t + 0.1);
  }

  playCaptureSound() {
    this.init();
    const t = this.audioContext.currentTime;
    const osc1 = this.audioContext.createOscillator();
    const osc2 = this.audioContext.createOscillator();
    const gain = this.audioContext.createGain();
    const filter = this.audioContext.createBiquadFilter();

    osc1.connect(filter);
    osc2.connect(filter);
    filter.connect(gain);
    gain.connect(this.audioContext.destination);

    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(300, t);
    osc1.frequency.exponentialRampToValueAtTime(120, t + 0.12);

    osc2.type = 'triangle';
    osc2.frequency.setValueAtTime(600, t);
    osc2.frequency.exponentialRampToValueAtTime(240, t + 0.12);

    filter.type = 'lowpass';
    filter.frequency.setValueAtTime(800, t);

    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(0.6, t + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.12);

    osc1.start(t);
    osc2.start(t);
    osc1.stop(t + 0.15);
    osc2.stop(t + 0.15);
  }

  playCheckSound() {
    this.init();
    const t = this.audioContext.currentTime;
    const osc = this.audioContext.createOscillator();
    const gain = this.audioContext.createGain();

    osc.connect(gain);
    gain.connect(this.audioContext.destination);

    osc.type = 'sine';
    osc.frequency.setValueAtTime(520, t);
    osc.frequency.setValueAtTime(780, t + 0.08);
    osc.frequency.setValueAtTime(520, t + 0.16);
    osc.frequency.setValueAtTime(780, t + 0.24);

    gain.gain.setValueAtTime(0.4, t);
    gain.gain.setValueAtTime(0.4, t + 0.07);
    gain.gain.setValueAtTime(0, t + 0.08);
    gain.gain.setValueAtTime(0.4, t + 0.15);
    gain.gain.setValueAtTime(0.4, t + 0.23);
    gain.gain.setValueAtTime(0, t + 0.24);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.35);

    osc.start(t);
    osc.stop(t + 0.35);
  }

  playGameOverSound() {
    this.init();
    const t = this.audioContext.currentTime;
    const osc = this.audioContext.createOscillator();
    const gain = this.audioContext.createGain();

    osc.connect(gain);
    gain.connect(this.audioContext.destination);

    osc.type = 'triangle';
    osc.frequency.setValueAtTime(523, t);
    osc.frequency.setValueAtTime(392, t + 0.2);
    osc.frequency.setValueAtTime(330, t + 0.4);
    osc.frequency.exponentialRampToValueAtTime(165, t + 0.8);

    gain.gain.setValueAtTime(0.5, t);
    gain.gain.linearRampToValueAtTime(0.5, t + 0.15);
    gain.gain.linearRampToValueAtTime(0.5, t + 0.35);
    gain.gain.linearRampToValueAtTime(0.5, t + 0.55);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 1.0);

    osc.start(t);
    osc.stop(t + 1.0);
  }

  playClockSound() {
    this.init();
    const t = this.audioContext.currentTime;
    const osc = this.audioContext.createOscillator();
    const gain = this.audioContext.createGain();

    osc.connect(gain);
    gain.connect(this.audioContext.destination);

    osc.type = 'square';
    osc.frequency.setValueAtTime(800, t);

    gain.gain.setValueAtTime(0.3, t);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.05);

    osc.start(t);
    osc.stop(t + 0.05);
  }
}

const soundController = new SoundController();

const API_URL = 'http://34.9.1.205:8000';

// Time control configurations (in seconds)
const TIME_CONTROLS = {
  bullet: { label: 'Bullet 1min', seconds: 60 },
  blitz: { label: 'Blitz 3min', seconds: 180 },
  rapid: { label: 'Rapid 10min', seconds: 600 },
  classical: { label: 'Classical 30min', seconds: 1800 }
};

// Difficulty levels (keys must match the backend ai_engine LEVELS).
const DIFFICULTIES = [
  { key: 'beginner', label: 'Beginner', elo: 600 },
  { key: 'easy', label: 'Easy', elo: 1000 },
  { key: 'intermediate', label: 'Club', elo: 1400 },
  { key: 'hard', label: 'Hard', elo: 1800 },
  { key: 'expert', label: 'Expert', elo: 2000 },
  { key: 'max', label: 'Maximum', elo: 2200 },
];

// Unicode glyphs for captured-piece trays.
const PIECE_GLYPHS = { p: '♟', n: '♞', b: '♝', r: '♜', q: '♛' };
const PIECE_WORTH = { p: 1, n: 3, b: 3, r: 5, q: 9 };
const START_COUNT = { p: 8, n: 2, b: 2, r: 2, q: 1 };

// Compare current board to the starting army to find captured pieces and the
// running material balance (positive == White is up material).
function getCaptured(game) {
  if (!game) return { white: [], black: [], advantage: 0 };
  const remaining = { w: { p: 0, n: 0, b: 0, r: 0, q: 0 }, b: { p: 0, n: 0, b: 0, r: 0, q: 0 } };
  for (const row of game.board()) {
    for (const sq of row) {
      if (sq && sq.type !== 'k') remaining[sq.color][sq.type]++;
    }
  }
  const whiteCaptured = []; // black pieces White has taken
  const blackCaptured = []; // white pieces Black has taken
  let advantage = 0;
  for (const t of ['q', 'r', 'b', 'n', 'p']) {
    const wMissing = START_COUNT[t] - remaining.w[t];
    const bMissing = START_COUNT[t] - remaining.b[t];
    for (let i = 0; i < bMissing; i++) whiteCaptured.push(t);
    for (let i = 0; i < wMissing; i++) blackCaptured.push(t);
    advantage += (remaining.w[t] - remaining.b[t]) * PIECE_WORTH[t];
  }
  return { white: whiteCaptured, black: blackCaptured, advantage };
}

// Map an evaluation (centipawns, White's perspective) to a 0-100 white-share
// for the eval bar. Uses a smooth logistic so big swings don't peg instantly.
function evalToWhitePct(cp) {
  if (cp > 90000) return 100;
  if (cp < -90000) return 0;
  const pawns = cp / 100;
  return 100 / (1 + Math.pow(10, -pawns / 4));
}

function formatEval(cp, playerColor) {
  if (cp === null || cp === undefined) return '0.0';
  if (Math.abs(cp) > 90000) {
    const mover = cp > 0 ? 'W' : 'B';
    return `${mover} mate`;
  }
  const pawns = (playerColor === 'w' ? cp : -cp) / 100;
  return (pawns >= 0 ? '+' : '') + pawns.toFixed(1);
}

function App() {
  const [game, setGame] = useState(null);
  const [moveHistory, setMoveHistory] = useState([]);
  const [gameStatus, setGameStatus] = useState({ isCheck: false, isCheckmate: false, isDraw: false });
  const [isThinking, setIsThinking] = useState(false);
  const [gameRef, setGameRef] = useState(null);
  const [selectedSquare, setSelectedSquare] = useState(null);
  const [legalMoves, setLegalMoves] = useState([]);

  // Game setup state
  const [gameSetup, setGameSetup] = useState(true);
  const [playerColor, setPlayerColor] = useState('w');
  const [timeControl, setTimeControl] = useState('rapid');
  const [difficulty, setDifficulty] = useState('hard');
  const [whiteTime, setWhiteTime] = useState(TIME_CONTROLS.rapid.seconds);
  const [blackTime, setBlackTime] = useState(TIME_CONTROLS.rapid.seconds);
  const [lastMove, setLastMove] = useState(null);
  const [moveNotifications, setMoveNotifications] = useState([]);
  const [evalCp, setEvalCp] = useState(0);          // White's perspective
  const [thinkInfo, setThinkInfo] = useState(null); // { depth, nodes, time_ms }

  const difficultyRef = useRef('hard');
  difficultyRef.current = difficulty;

  const timerRef = useRef(null);

  // Initialize game when setup is complete
  const startGame = () => {
    const newGame = new Chess();
    setGame(newGame);
    setGameRef(newGame);
    setMoveHistory([]);
    setGameStatus({ isCheck: false, isCheckmate: false, isDraw: false });
    setLastMove(null);
    setMoveNotifications([]);
    setIsThinking(false);
    setEvalCp(0);
    setThinkInfo(null);

    // Set time based on selection
    const time = TIME_CONTROLS[timeControl].seconds;
    setWhiteTime(time);
    setBlackTime(time);

    setGameSetup(false);
    soundController.playMoveSound();

    // If player chose Black, let the bot (White) make the first move.
    if (playerColor === 'b') {
      setTimeout(() => makeBotMove(newGame.fen()), 500);
    }
  };

  // Timer for time controls
  useEffect(() => {
    if (gameSetup || !game || gameStatus.isCheckmate || gameStatus.isDraw) {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      return;
    }

    timerRef.current = setInterval(() => {
      if (game.turn() === 'w') {
        setWhiteTime(prev => {
          if (prev <= 1) {
            setGameStatus({ isCheckmate: true, isCheck: false, isDraw: false });
            addNotification('Time! White ran out of time.');
            soundController.playGameOverSound();
            return 0;
          }
          if (prev <= 10 && prev % 5 === 0) {
            soundController.playClockSound();
          }
          return prev - 1;
        });
      } else {
        setBlackTime(prev => {
          if (prev <= 1) {
            setGameStatus({ isCheckmate: true, isCheck: false, isDraw: false });
            addNotification('Time! Black ran out of time.');
            soundController.playGameOverSound();
            return 0;
          }
          if (prev <= 10 && prev % 5 === 0) {
            soundController.playClockSound();
          }
          return prev - 1;
        });
      }
    }, 1000);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [gameSetup, game, gameStatus]);

  const addNotification = (message) => {
    const id = Date.now();
    setMoveNotifications(prev => [...prev.slice(-4), { id, message }]);
    setTimeout(() => {
      setMoveNotifications(prev => prev.filter(n => n.id !== id));
    }, 3000);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const makeBotMove = async (fen) => {
    setIsThinking(true);
    try {
      const response = await fetch(`${API_URL}/api/bot-move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_fen: fen, level: difficultyRef.current }),
      });

      if (!response.ok) {
        let errorMsg = 'Failed to get bot move';
        try {
          const errorData = await response.json();
          errorMsg = errorData.detail || errorMsg;
        } catch (e) {
          errorMsg = `Server error: ${response.status}`;
        }
        console.error('Bot move error response:', errorMsg);
        throw new Error(errorMsg);
      }

      const data = await response.json();

      const newGame = new Chess(data.new_fen);
      setGame(newGame);
      setGameRef(newGame);
      setSelectedSquare(null);
      setLegalMoves([]);

      // SAN comes straight from the backend (computed before the move was
      // applied), so the move log is always correct for the bot too.
      const san = data.bot_move_san || data.bot_move;
      setMoveHistory((prev) => [...prev, san]);
      addNotification(`Bot: ${san}`);

      // Update game status
      setGameStatus({
        isCheck: data.is_check,
        isCheckmate: data.is_checkmate,
        isDraw: data.is_draw,
      });

      // Evaluation is from the bot's perspective; convert to White's.
      // After the bot moves it is the player's turn, so the mover was White
      // iff it is now Black to move.
      const whiteEval = newGame.turn() === 'b' ? data.eval_cp : -data.eval_cp;
      setEvalCp(whiteEval);
      setThinkInfo({ depth: data.depth, nodes: data.nodes, time_ms: data.time_ms });

      // Play appropriate sound - check if it's a capture by examining the board before the move
      const boardBeforeMove = new Chess(fen);
      const toSquare = data.bot_move.slice(2, 4);
      const capturedPiece = boardBeforeMove.get(toSquare);

      if (data.is_checkmate) {
        soundController.playGameOverSound();
      } else if (data.is_check) {
        soundController.playCheckSound();
      } else if (capturedPiece) {
        soundController.playCaptureSound();
      } else {
        soundController.playMoveSound();
      }

      setLastMove(data.bot_move);
      setIsThinking(false);
    } catch (error) {
      console.error('Bot move error:', error);
      addNotification(`Error: ${error.message}`);
      setIsThinking(false);
    }
  };

  const clearSelection = useCallback(() => {
    setSelectedSquare(null);
    setLegalMoves([]);
  }, []);

  // Shared move executor used by both drag-and-drop and click-to-move.
  const tryMove = useCallback(
    (from, to) => {
      if (gameSetup || !gameRef || isThinking) return false;
      if (gameStatus.isCheckmate || gameStatus.isDraw) return false;

      const isPlayerTurn = gameRef.turn() === playerColor;
      if (!isPlayerTurn) return false;

      let move = null;
      try {
        move = gameRef.move({ from, to, promotion: 'q' });
      } catch (e) {
        move = null;
      }
      if (move === null) return false;

      const newGame = new Chess(gameRef.fen());
      setGame(newGame);
      setGameRef(newGame);
      clearSelection();

      setMoveHistory((prev) => [...prev, move.san]);
      addNotification(`You: ${move.san}`);

      if (move.flags.includes('c') || move.flags.includes('e')) {
        soundController.playCaptureSound();
      } else if (newGame.inCheck()) {
        soundController.playCheckSound();
      } else {
        soundController.playMoveSound();
      }

      setLastMove(move.from + move.to);

      // Trigger bot response.
      setTimeout(() => makeBotMove(newGame.fen()), 350);
      return true;
    },
    [clearSelection, gameSetup, gameRef, isThinking, playerColor, gameStatus]
  );

  const onSquareClick = useCallback((square) => {
    if (gameSetup || !gameRef || isThinking) return;
    if (gameRef.turn() !== playerColor) return;

    // If a piece is already selected and this square is a legal destination,
    // complete the move (click-to-move).
    if (selectedSquare && legalMoves.some((m) => m.to === square)) {
      tryMove(selectedSquare, square);
      return;
    }

    if (selectedSquare === square) {
      clearSelection();
      return;
    }

    const piece = gameRef.get(square);
    if (!piece || piece.color !== playerColor) {
      clearSelection();
      return;
    }

    try {
      const moves = gameRef.moves({ square, verbose: true }) || [];
      setSelectedSquare(square);
      setLegalMoves(moves);
    } catch (e) {
      clearSelection();
    }
  }, [clearSelection, gameSetup, gameRef, isThinking, playerColor, selectedSquare, legalMoves, tryMove]);

  const onPieceDrop = useCallback(
    (sourceSquare, targetSquare) => tryMove(sourceSquare, targetSquare),
    [tryMove]
  );

  const resetGame = () => {
    setGameSetup(true);
    setGame(null);
    setGameRef(null);
    setMoveHistory([]);
    setGameStatus({ isCheck: false, isCheckmate: false, isDraw: false });
    setLastMove(null);
    setMoveNotifications([]);
    setIsThinking(false);
    setEvalCp(0);
    setThinkInfo(null);
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const selectedDifficulty = DIFFICULTIES.find((d) => d.key === difficulty) || DIFFICULTIES[3];

  // ---- Game Setup Screen ----
  if (gameSetup) {
    return (
      <div className="min-h-screen bg-[#161512] flex items-center justify-center p-4">
        <div className="w-full max-w-md rounded-2xl bg-[#262421] p-8 shadow-2xl ring-1 ring-white/5">
          <div className="mb-8 text-center">
            <div className="mb-1 text-4xl">♞</div>
            <h1 className="text-3xl font-bold tracking-tight text-white">Chess vs AI</h1>
            <p className="mt-1 text-sm text-[#9b998f]">Play a tunable engine — from beginner to ~2200.</p>
          </div>

          {/* Color Selection */}
          <SetupSection title="Choose Your Color">
            <div className="grid grid-cols-2 gap-3">
              {[['w', 'White', '♔'], ['b', 'Black', '♚']].map(([val, label, glyph]) => (
                <button
                  key={val}
                  onClick={() => setPlayerColor(val)}
                  className={`flex items-center justify-center gap-2 rounded-lg py-3 px-4 font-bold transition-colors ${playerColor === val ? 'bg-[#81b64c] text-white' : 'bg-[#3a3836] text-[#d6d4cf] hover:bg-[#4a4846]'}`}
                >
                  <span className="text-xl">{glyph}</span>{label}
                </button>
              ))}
            </div>
          </SetupSection>

          {/* Difficulty Selection */}
          <SetupSection title="Difficulty">
            <div className="grid grid-cols-3 gap-2">
              {DIFFICULTIES.map((d) => (
                <button
                  key={d.key}
                  onClick={() => setDifficulty(d.key)}
                  className={`rounded-lg py-2 px-2 text-sm font-semibold transition-colors ${difficulty === d.key ? 'bg-[#81b64c] text-white' : 'bg-[#3a3836] text-[#d6d4cf] hover:bg-[#4a4846]'}`}
                >
                  <div>{d.label}</div>
                  <div className="text-[11px] font-normal opacity-70">~{d.elo}</div>
                </button>
              ))}
            </div>
          </SetupSection>

          {/* Time Control Selection */}
          <SetupSection title="Time Control">
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(TIME_CONTROLS).map(([key, control]) => (
                <button
                  key={key}
                  onClick={() => setTimeControl(key)}
                  className={`rounded-lg py-3 px-4 font-bold transition-colors ${timeControl === key ? 'bg-[#81b64c] text-white' : 'bg-[#3a3836] text-[#d6d4cf] hover:bg-[#4a4846]'}`}
                >
                  {control.label}
                </button>
              ))}
            </div>
          </SetupSection>

          <button
            onClick={() => startGame()}
            className="mt-2 w-full rounded-lg bg-[#81b64c] py-4 text-lg font-bold text-white transition-colors hover:bg-[#6a9c3e]"
          >
            Start Game
          </button>
        </div>
      </div>
    );
  }

  // ---- Game Screen ----
  const captured = getCaptured(game);
  const whitePct = evalToWhitePct(evalCp);
  const playerIsWhite = playerColor === 'w';

  // Trays: pieces captured by the side shown at the bottom vs top of the board.
  const bottomTray = playerIsWhite ? captured.white : captured.black;
  const topTray = playerIsWhite ? captured.black : captured.white;
  const bottomAdv = playerIsWhite ? captured.advantage : -captured.advantage;

  const CapturedTray = ({ pieces, adv }) => (
    <div className="flex h-6 items-center gap-0.5 text-lg leading-none text-[#b9b7b0]">
      {pieces.map((p, i) => (
        <span key={i} className="-mr-1.5">{PIECE_GLYPHS[p]}</span>
      ))}
      {adv > 0 && <span className="ml-2 text-xs font-semibold text-[#9b998f]">+{adv}</span>}
    </div>
  );

  return (
    <div className="min-h-screen bg-[#161512] flex items-center justify-center p-4">
      {/* Notifications */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {moveNotifications.map((notification) => (
          <div
            key={notification.id}
            className="rounded-lg border-l-4 border-[#81b64c] bg-[#262421] px-4 py-2 text-white shadow-lg"
          >
            {notification.message}
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        {/* Eval bar + Board column */}
        <div className="flex flex-col items-center">
          <h1 className="mb-4 text-2xl font-bold text-white">Chess vs AI</h1>

          <div className="flex items-stretch gap-3">
            {/* Eval bar: the light fill is White's share, anchored to the side
                where White's pieces sit given the board orientation. */}
            <div className="relative h-[500px] w-3 overflow-hidden rounded bg-[#403e3a]" title={formatEval(evalCp, 'w')}>
              <div
                className="absolute left-0 w-full bg-[#e9e7df] transition-[height] duration-500 ease-out"
                style={{ height: `${whitePct}%`, [playerIsWhite ? 'bottom' : 'top']: 0 }}
              />
            </div>

            <div className="flex flex-col">
              {/* Top: opponent clock + captures */}
              <div className="mb-2 flex w-[500px] items-center justify-between">
                <CapturedTray pieces={topTray} adv={-bottomAdv} />
                <Clock
                  active={game?.turn() === (playerIsWhite ? 'b' : 'w')}
                  time={formatTime(playerIsWhite ? blackTime : whiteTime)}
                  label={playerIsWhite ? 'Black' : 'White'}
                />
              </div>

              <div className="relative">
                <Chessboard
                  id="BasicBoard"
                  position={game?.fen() || ''}
                  onPieceDrop={onPieceDrop}
                  onSquareClick={onSquareClick}
                  boardOrientation={playerIsWhite ? 'white' : 'black'}
                  customBoardStyle={{ borderRadius: '4px', boxShadow: '0 4px 18px rgba(0,0,0,0.55)' }}
                  customDarkSquareStyle={{ backgroundColor: '#769656' }}
                  customLightSquareStyle={{ backgroundColor: '#eeeed2' }}
                  animationDuration={200}
                  boardWidth={500}
                  customSquareStyles={(() => {
                    const styles = {};
                    if (lastMove) {
                      styles[lastMove.slice(0, 2)] = { backgroundColor: 'rgba(255, 255, 0, 0.4)' };
                      styles[lastMove.slice(2, 4)] = { backgroundColor: 'rgba(255, 255, 0, 0.4)' };
                    }
                    if (selectedSquare && !styles[selectedSquare]) {
                      styles[selectedSquare] = { backgroundColor: 'rgba(129, 182, 76, 0.35)' };
                    }
                    for (const move of legalMoves) {
                      const to = move.to;
                      if (!to) continue;
                      const isCapture = typeof move.flags === 'string' && (move.flags.includes('c') || move.flags.includes('e'));
                      styles[to] = {
                        ...(styles[to] || {}),
                        ...(isCapture
                          ? { boxShadow: 'inset 0 0 0 4px rgba(0, 0, 0, 0.35)' }
                          : { backgroundImage: 'radial-gradient(circle at center, rgba(0, 0, 0, 0.35) 18%, transparent 20%)' }),
                      };
                    }
                    return styles;
                  })()}
                />
                {isThinking && (
                  <div className="absolute left-2 top-2 flex items-center gap-2 rounded bg-black/70 px-3 py-1 text-sm text-white">
                    <span className="h-2 w-2 animate-pulse rounded-full bg-[#81b64c]" />
                    AI thinking…
                  </div>
                )}
              </div>

              {/* Bottom: player clock + captures */}
              <div className="mt-2 flex w-[500px] items-center justify-between">
                <CapturedTray pieces={bottomTray} adv={bottomAdv} />
                <Clock
                  active={game?.turn() === playerColor}
                  time={formatTime(playerIsWhite ? whiteTime : blackTime)}
                  label={playerIsWhite ? 'White' : 'Black'}
                />
              </div>
            </div>
          </div>

          {/* Game Status */}
          <div className="mt-4 flex h-10 items-center gap-4 text-white">
            {gameStatus.isCheckmate && (
              <div className="rounded bg-red-600 px-4 py-2 font-bold">Checkmate! Game Over</div>
            )}
            {gameStatus.isDraw && (
              <div className="rounded bg-yellow-600 px-4 py-2 font-bold">Draw!</div>
            )}
            {gameStatus.isCheck && !gameStatus.isCheckmate && (
              <div className="rounded bg-orange-600 px-4 py-2 font-bold">Check!</div>
            )}
          </div>

          <div className="mt-2 flex gap-3">
            <button
              onClick={resetGame}
              className="rounded-lg bg-[#81b64c] px-6 py-2 font-bold text-white transition-colors hover:bg-[#6a9c3e]"
            >
              New Game
            </button>
            <button
              onClick={() => setGameSetup(true)}
              className="rounded-lg bg-[#3a3836] px-6 py-2 font-bold text-white transition-colors hover:bg-[#4a4846]"
            >
              Settings
            </button>
          </div>
        </div>

        {/* Side Panel */}
        <div className="w-72 rounded-2xl bg-[#262421] p-4 ring-1 ring-white/5">
          <div className="mb-3 flex items-center justify-between border-b border-[#3a3836] pb-2">
            <h2 className="font-bold text-white">Move History</h2>
            <span className="text-xs font-semibold text-[#9b998f]">
              {formatEval(evalCp, playerColor)}
            </span>
          </div>

          <div className="move-log mb-4 max-h-64 overflow-y-auto">
            <div className="font-mono text-sm text-white">
              {moveHistory.length === 0 ? (
                <p className="italic text-gray-500">No moves yet</p>
              ) : (
                <div className="grid grid-cols-[2rem_1fr_1fr] gap-x-2 gap-y-1">
                  {Array.from({ length: Math.ceil(moveHistory.length / 2) }).map((_, row) => (
                    <React.Fragment key={row}>
                      <span className="text-gray-500">{row + 1}.</span>
                      <span>{moveHistory[row * 2]}</span>
                      <span>{moveHistory[row * 2 + 1] || ''}</span>
                    </React.Fragment>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-1 border-t border-[#3a3836] pt-3 text-sm">
            <h3 className="mb-2 font-semibold text-white">Game Info</h3>
            <InfoRow label="You play" value={playerIsWhite ? 'White' : 'Black'} />
            <InfoRow label="Difficulty" value={`${selectedDifficulty.label} (~${selectedDifficulty.elo})`} />
            <InfoRow label="Time" value={TIME_CONTROLS[timeControl].label} />
            {thinkInfo && (
              <InfoRow
                label="Last think"
                value={`d${thinkInfo.depth} · ${thinkInfo.time_ms}ms`}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- Small presentational helpers ----
function SetupSection({ title, children }) {
  return (
    <div className="mb-6">
      <h2 className="mb-3 font-semibold text-white">{title}</h2>
      {children}
    </div>
  );
}

function Clock({ active, time, label }) {
  return (
    <div
      className={`rounded px-4 py-2 transition-colors ${active ? 'bg-[#81b64c] text-white' : 'bg-[#262421] text-[#d6d4cf] ring-1 ring-white/5'}`}
    >
      <span className="text-xs opacity-70">{label}</span>
      <span className="ml-2 font-mono font-bold tabular-nums">{time}</span>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <p className="flex justify-between text-[#9b998f]">
      <span>{label}</span>
      <span className="font-semibold text-white">{value}</span>
    </p>
  );
}

export default App;
