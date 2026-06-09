import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Chessboard } from 'react-chessboard';
import { Chess } from 'chess.js';

// ---- Sound Controller ----
class SoundController {
  constructor() { this.audioContext = null; }

  init() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (this.audioContext.state === 'suspended') this.audioContext.resume();
  }

  playMoveSound() {
    this.init();
    const t = this.audioContext.currentTime;
    const osc = this.audioContext.createOscillator();
    const gain = this.audioContext.createGain();
    const filter = this.audioContext.createBiquadFilter();
    osc.connect(filter); filter.connect(gain); gain.connect(this.audioContext.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(180, t);
    osc.frequency.exponentialRampToValueAtTime(80, t + 0.08);
    filter.type = 'lowpass'; filter.frequency.setValueAtTime(400, t);
    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(0.5, t + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.08);
    osc.start(t); osc.stop(t + 0.1);
  }

  playCaptureSound() {
    this.init();
    const t = this.audioContext.currentTime;
    const osc1 = this.audioContext.createOscillator();
    const osc2 = this.audioContext.createOscillator();
    const gain = this.audioContext.createGain();
    const filter = this.audioContext.createBiquadFilter();
    osc1.connect(filter); osc2.connect(filter); filter.connect(gain); gain.connect(this.audioContext.destination);
    osc1.type = 'sine'; osc1.frequency.setValueAtTime(300, t); osc1.frequency.exponentialRampToValueAtTime(120, t + 0.12);
    osc2.type = 'triangle'; osc2.frequency.setValueAtTime(600, t); osc2.frequency.exponentialRampToValueAtTime(240, t + 0.12);
    filter.type = 'lowpass'; filter.frequency.setValueAtTime(800, t);
    gain.gain.setValueAtTime(0, t); gain.gain.linearRampToValueAtTime(0.6, t + 0.02); gain.gain.exponentialRampToValueAtTime(0.01, t + 0.12);
    osc1.start(t); osc2.start(t); osc1.stop(t + 0.15); osc2.stop(t + 0.15);
  }

  playCheckSound() {
    this.init();
    const t = this.audioContext.currentTime;
    const osc = this.audioContext.createOscillator();
    const gain = this.audioContext.createGain();
    osc.connect(gain); gain.connect(this.audioContext.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(520, t); osc.frequency.setValueAtTime(780, t + 0.08);
    osc.frequency.setValueAtTime(520, t + 0.16); osc.frequency.setValueAtTime(780, t + 0.24);
    gain.gain.setValueAtTime(0.4, t); gain.gain.setValueAtTime(0.4, t + 0.07); gain.gain.setValueAtTime(0, t + 0.08);
    gain.gain.setValueAtTime(0.4, t + 0.15); gain.gain.setValueAtTime(0.4, t + 0.23); gain.gain.setValueAtTime(0, t + 0.24);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.35);
    osc.start(t); osc.stop(t + 0.35);
  }

  playGameOverSound() {
    this.init();
    const t = this.audioContext.currentTime;
    const osc = this.audioContext.createOscillator();
    const gain = this.audioContext.createGain();
    osc.connect(gain); gain.connect(this.audioContext.destination);
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(523, t); osc.frequency.setValueAtTime(392, t + 0.2);
    osc.frequency.setValueAtTime(330, t + 0.4); osc.frequency.exponentialRampToValueAtTime(165, t + 0.8);
    gain.gain.setValueAtTime(0.5, t); gain.gain.linearRampToValueAtTime(0.5, t + 0.55);
    gain.gain.exponentialRampToValueAtTime(0.01, t + 1.0);
    osc.start(t); osc.stop(t + 1.0);
  }

  playClockSound() {
    this.init();
    const t = this.audioContext.currentTime;
    const osc = this.audioContext.createOscillator();
    const gain = this.audioContext.createGain();
    osc.connect(gain); gain.connect(this.audioContext.destination);
    osc.type = 'square'; osc.frequency.setValueAtTime(800, t);
    gain.gain.setValueAtTime(0.3, t); gain.gain.exponentialRampToValueAtTime(0.01, t + 0.05);
    osc.start(t); osc.stop(t + 0.05);
  }
}

const soundController = new SoundController();
const API_URL = '';

const TIME_CONTROLS = {
  bullet:    { label: 'Bullet 1min',    seconds: 60 },
  blitz:     { label: 'Blitz 3min',     seconds: 180 },
  rapid:     { label: 'Rapid 10min',    seconds: 600 },
  classical: { label: 'Classical 30min', seconds: 1800 },
};

const DIFFICULTIES = [
  { key: 'beginner',     label: 'Beginner', elo: 600 },
  { key: 'easy',         label: 'Easy',     elo: 1000 },
  { key: 'intermediate', label: 'Club',     elo: 1400 },
  { key: 'hard',         label: 'Hard',     elo: 1800 },
  { key: 'expert',       label: 'Expert',   elo: 2000 },
  { key: 'max',          label: 'Maximum',  elo: 2200 },
];

const PIECE_GLYPHS = { p: '♟', n: '♞', b: '♝', r: '♜', q: '♛' };
const PIECE_WORTH  = { p: 1, n: 3, b: 3, r: 5, q: 9 };
const START_COUNT  = { p: 8, n: 2, b: 2, r: 2, q: 1 };

function getCaptured(game) {
  if (!game) return { white: [], black: [], advantage: 0 };
  const remaining = { w: { p: 0, n: 0, b: 0, r: 0, q: 0 }, b: { p: 0, n: 0, b: 0, r: 0, q: 0 } };
  for (const row of game.board())
    for (const sq of row)
      if (sq && sq.type !== 'k') remaining[sq.color][sq.type]++;

  const whiteCaptured = [], blackCaptured = [];
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

function evalToWhitePct(cp) {
  if (cp > 90000) return 100;
  if (cp < -90000) return 0;
  return 100 / (1 + Math.pow(10, -(cp / 100) / 4));
}

function formatEval(cp, playerColor) {
  if (cp === null || cp === undefined) return '0.0';
  if (Math.abs(cp) > 90000) return cp > 0 ? 'W mate' : 'B mate';
  const pawns = (playerColor === 'w' ? cp : -cp) / 100;
  return (pawns >= 0 ? '+' : '') + pawns.toFixed(1);
}

// ---- Responsive board width ----
function useBoardWidth() {
  const compute = () => {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    // Eval bar (8-12px) + gap (8px) + padding (12-40px)
    const evalBarTotal = vw < 480 ? 18 : 22;
    const hPad = vw < 480 ? 12 : vw < 768 ? 32 : 48;
    // Leave vertical room: clocks (~80px) + title (~36px) + status/buttons (~80px)
    const vReserve = vw < 480 ? 230 : 200;
    const byWidth = vw - evalBarTotal - hPad;
    const byHeight = vh - vReserve;
    return Math.max(240, Math.min(byWidth, byHeight, 520));
  };
  const [width, setWidth] = useState(compute);
  useEffect(() => {
    const handler = () => setWidth(compute());
    window.addEventListener('resize', handler);
    window.addEventListener('orientationchange', () => setTimeout(handler, 100));
    return () => window.removeEventListener('resize', handler);
  }, []);
  return width;
}

// ---- App ----
function App() {
  const [game, setGame]                   = useState(null);
  const [moveHistory, setMoveHistory]     = useState([]);
  const [gameStatus, setGameStatus]       = useState({ isCheck: false, isCheckmate: false, isDraw: false });
  const [isThinking, setIsThinking]       = useState(false);
  const [gameRef, setGameRef]             = useState(null);
  const [selectedSquare, setSelectedSquare] = useState(null);
  const [legalMoves, setLegalMoves]       = useState([]);
  const [premove, setPremove]             = useState(null); // { from, to } | null

  const [gameSetup, setGameSetup]         = useState(true);
  const [playerColor, setPlayerColor]     = useState('w');
  const [timeControl, setTimeControl]     = useState('rapid');
  const [difficulty, setDifficulty]       = useState('hard');
  const [whiteTime, setWhiteTime]         = useState(TIME_CONTROLS.rapid.seconds);
  const [blackTime, setBlackTime]         = useState(TIME_CONTROLS.rapid.seconds);
  const [lastMove, setLastMove]           = useState(null);
  const [moveNotifications, setMoveNotifications] = useState([]);
  const [evalCp, setEvalCp]               = useState(0);
  const [thinkInfo, setThinkInfo]         = useState(null);

  // Refs that stay current for async callbacks
  const difficultyRef  = useRef('hard');  difficultyRef.current  = difficulty;
  const playerColorRef = useRef('w');     playerColorRef.current = playerColor;
  const premoveRef     = useRef(null);    premoveRef.current     = premove;

  const timerRef   = useRef(null);
  const abortRef   = useRef(null); // AbortController for the in-flight fetch
  const moveLogRef = useRef(null);
  const boardWidth = useBoardWidth();

  // Auto-scroll move log
  useEffect(() => {
    if (moveLogRef.current) moveLogRef.current.scrollTop = moveLogRef.current.scrollHeight;
  }, [moveHistory]);

  // Cancel premove on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') setPremove(null); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

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
    setPremove(null);
    const time = TIME_CONTROLS[timeControl].seconds;
    setWhiteTime(time);
    setBlackTime(time);
    setGameSetup(false);
    soundController.playMoveSound();
    if (playerColor === 'b') setTimeout(() => makeBotMove(newGame.fen()), 500);
  };

  // Countdown timer
  useEffect(() => {
    if (gameSetup || !game || gameStatus.isCheckmate || gameStatus.isDraw) {
      if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
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
          if (prev <= 10 && prev % 5 === 0) soundController.playClockSound();
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
          if (prev <= 10 && prev % 5 === 0) soundController.playClockSound();
          return prev - 1;
        });
      }
    }, 1000);
    return () => { if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; } };
  }, [gameSetup, game, gameStatus]);

  const addNotification = (message) => {
    const id = Date.now();
    setMoveNotifications(prev => [...prev.slice(-4), { id, message }]);
    setTimeout(() => setMoveNotifications(prev => prev.filter(n => n.id !== id)), 3000);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const makeBotMove = async (fen) => {
    // Abort any stale in-flight request before starting a new one
    if (abortRef.current) abortRef.current.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    // Client-side sanity check (backend validates fully; this stops obviously bad calls)
    if (!fen || fen.length > 200) {
      addNotification('Error: invalid board state.');
      return;
    }

    setIsThinking(true);
    try {
      const response = await fetch(`${API_URL}/api/bot-move`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_fen: fen, level: difficultyRef.current }),
        signal: ctrl.signal,
      });
      if (!response.ok) {
        let msg = 'Failed to get bot move';
        try { const d = await response.json(); msg = d.detail || msg; } catch { msg = `Server error: ${response.status}`; }
        throw new Error(msg);
      }

      const data = await response.json();
      const botGame = new Chess(data.new_fen);
      setGame(botGame);
      setGameRef(botGame);
      setSelectedSquare(null);
      setLegalMoves([]);

      const san = data.bot_move_san || data.bot_move;
      setMoveHistory(prev => [...prev, san]);
      addNotification(`Bot: ${san}`);
      setGameStatus({ isCheck: data.is_check, isCheckmate: data.is_checkmate, isDraw: data.is_draw });

      const whiteEval = botGame.turn() === 'b' ? data.eval_cp : -data.eval_cp;
      setEvalCp(whiteEval);
      setThinkInfo({ depth: data.depth, nodes: data.nodes, time_ms: data.time_ms });

      const boardBeforeMove = new Chess(fen);
      const capturedPiece = boardBeforeMove.get(data.bot_move.slice(2, 4));
      if (data.is_checkmate)     soundController.playGameOverSound();
      else if (data.is_check)    soundController.playCheckSound();
      else if (capturedPiece)    soundController.playCaptureSound();
      else                       soundController.playMoveSound();
      setLastMove(data.bot_move);

      // Execute queued premove — keep isThinking=true so it flows straight into the next bot call
      const pm = premoveRef.current;
      premoveRef.current = null;
      if (pm && !data.is_checkmate && !data.is_draw) {
        setPremove(null);
        try {
          const testGame = new Chess(botGame.fen());
          const pmMove = testGame.move({ from: pm.from, to: pm.to, promotion: 'q' });
          if (pmMove) {
            const afterPremove = new Chess(testGame.fen());
            setGame(afterPremove);
            setGameRef(afterPremove);
            setMoveHistory(prev => [...prev, pmMove.san]);
            addNotification(`You: ${pmMove.san}`);
            setLastMove(pmMove.from + pmMove.to);
            if (pmMove.flags.includes('c') || pmMove.flags.includes('e')) soundController.playCaptureSound();
            else if (afterPremove.inCheck())                               soundController.playCheckSound();
            else                                                           soundController.playMoveSound();
            // Stay in thinking state; schedule next bot move
            setTimeout(() => makeBotMove(afterPremove.fen()), 350);
            return;
          }
        } catch { /* premove was illegal — fall through */ }
      }
      setIsThinking(false);
    } catch (error) {
      if (error.name === 'AbortError') return; // request was intentionally cancelled
      console.error('Bot move error:', error);
      // Show a safe generic message — don't reflect raw server error text to the user
      addNotification('Error: could not reach the AI server.');
      setIsThinking(false);
    }
  };

  const clearSelection = useCallback(() => {
    setSelectedSquare(null);
    setLegalMoves([]);
  }, []);

  const tryMove = useCallback((from, to) => {
    if (gameSetup || !gameRef || isThinking) return false;
    if (gameStatus.isCheckmate || gameStatus.isDraw) return false;
    if (gameRef.turn() !== playerColor) return false;

    let move = null;
    try { move = gameRef.move({ from, to, promotion: 'q' }); } catch { move = null; }
    if (!move) return false;

    const newGame = new Chess(gameRef.fen());
    setGame(newGame);
    setGameRef(newGame);
    clearSelection();
    setMoveHistory(prev => [...prev, move.san]);
    addNotification(`You: ${move.san}`);
    if (move.flags.includes('c') || move.flags.includes('e')) soundController.playCaptureSound();
    else if (newGame.inCheck())                               soundController.playCheckSound();
    else                                                      soundController.playMoveSound();
    setLastMove(move.from + move.to);
    setTimeout(() => makeBotMove(newGame.fen()), 350);
    return true;
  }, [clearSelection, gameSetup, gameRef, isThinking, playerColor, gameStatus]);

  const onSquareClick = useCallback((square) => {
    if (gameSetup || !gameRef) return;
    const isPlayerTurn = gameRef.turn() === playerColor;

    // Premove handling (bot's turn)
    if (!isPlayerTurn) {
      if (gameStatus.isCheckmate || gameStatus.isDraw) return;
      const piece = gameRef.get(square);

      // Have a premove source set — pick destination
      if (premove && !premove.to) {
        if (premove.from === square) { setPremove(null); return; }
        const target = gameRef.get(square);
        if (target && target.color === playerColor) { setPremove({ from: square, to: null }); return; }
        setPremove({ from: premove.from, to: square });
        return;
      }
      // Have a full premove — allow changing source
      if (premove && premove.to) {
        if (piece && piece.color === playerColor) setPremove({ from: square, to: null });
        else setPremove(null);
        return;
      }
      // No premove yet — select source
      if (piece && piece.color === playerColor) setPremove({ from: square, to: null });
      return;
    }

    // Normal turn
    if (isThinking) return;
    if (selectedSquare && legalMoves.some(m => m.to === square)) { tryMove(selectedSquare, square); return; }
    if (selectedSquare === square) { clearSelection(); return; }
    const piece = gameRef.get(square);
    if (!piece || piece.color !== playerColor) { clearSelection(); return; }
    try {
      setSelectedSquare(square);
      setLegalMoves(gameRef.moves({ square, verbose: true }) || []);
    } catch { clearSelection(); }
  }, [clearSelection, gameSetup, gameRef, isThinking, playerColor, selectedSquare, legalMoves, tryMove, premove, gameStatus]);

  const onPieceDrop = useCallback((sourceSquare, targetSquare) => {
    if (gameSetup || !gameRef) return false;
    const isPlayerTurn = gameRef.turn() === playerColor;

    if (!isPlayerTurn) {
      if (gameStatus.isCheckmate || gameStatus.isDraw) return false;
      const piece = gameRef.get(sourceSquare);
      if (piece && piece.color === playerColor) {
        setPremove({ from: sourceSquare, to: targetSquare });
        return true; // prevent snap-back
      }
      return false;
    }
    if (isThinking) return false;
    return tryMove(sourceSquare, targetSquare);
  }, [tryMove, gameSetup, gameRef, isThinking, playerColor, gameStatus]);

  const resetGame = () => {
    if (abortRef.current) { abortRef.current.abort(); abortRef.current = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setGameSetup(true); setGame(null); setGameRef(null);
    setMoveHistory([]); setGameStatus({ isCheck: false, isCheckmate: false, isDraw: false });
    setLastMove(null); setMoveNotifications([]); setIsThinking(false);
    setEvalCp(0); setThinkInfo(null); setPremove(null);
  };

  const selectedDifficulty = DIFFICULTIES.find(d => d.key === difficulty) || DIFFICULTIES[3];

  // ---- Setup Screen ----
  if (gameSetup) {
    return (
      <div className="min-h-screen bg-[#161512] flex items-center justify-center p-4">
        <div className="w-full max-w-md rounded-2xl bg-[#262421] p-6 sm:p-8 shadow-2xl ring-1 ring-white/5">
          <div className="mb-6 text-center">
            <div className="mb-1 text-4xl select-none">♞</div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">Chess vs AI</h1>
            <p className="mt-1 text-sm text-[#9b998f]">Play a tunable engine — from beginner to ~2200.</p>
          </div>

          <SetupSection title="Choose Your Color">
            <div className="grid grid-cols-2 gap-3">
              {[['w', 'White', '♔'], ['b', 'Black', '♚']].map(([val, label, glyph]) => (
                <button key={val} onClick={() => setPlayerColor(val)}
                  className={`flex items-center justify-center gap-2 rounded-lg py-3 px-4 font-bold transition-colors ${
                    playerColor === val ? 'bg-[#81b64c] text-white' : 'bg-[#3a3836] text-[#d6d4cf] hover:bg-[#4a4846]'
                  }`}>
                  <span className="text-xl select-none">{glyph}</span>{label}
                </button>
              ))}
            </div>
          </SetupSection>

          <SetupSection title="Difficulty">
            <div className="grid grid-cols-3 gap-2">
              {DIFFICULTIES.map(d => (
                <button key={d.key} onClick={() => setDifficulty(d.key)}
                  className={`rounded-lg py-2 px-2 text-sm font-semibold transition-colors ${
                    difficulty === d.key ? 'bg-[#81b64c] text-white' : 'bg-[#3a3836] text-[#d6d4cf] hover:bg-[#4a4846]'
                  }`}>
                  <div>{d.label}</div>
                  <div className="text-[11px] font-normal opacity-70">~{d.elo}</div>
                </button>
              ))}
            </div>
          </SetupSection>

          <SetupSection title="Time Control">
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(TIME_CONTROLS).map(([key, control]) => (
                <button key={key} onClick={() => setTimeControl(key)}
                  className={`rounded-lg py-3 px-4 font-bold transition-colors ${
                    timeControl === key ? 'bg-[#81b64c] text-white' : 'bg-[#3a3836] text-[#d6d4cf] hover:bg-[#4a4846]'
                  }`}>
                  {control.label}
                </button>
              ))}
            </div>
          </SetupSection>

          <button onClick={startGame}
            className="mt-2 w-full rounded-lg bg-[#81b64c] py-4 text-lg font-bold text-white transition-colors hover:bg-[#6a9c3e]">
            Start Game
          </button>
        </div>
      </div>
    );
  }

  // ---- Game Screen ----
  const captured     = getCaptured(game);
  const whitePct     = evalToWhitePct(evalCp);
  const playerIsWhite = playerColor === 'w';
  const bottomTray   = playerIsWhite ? captured.white : captured.black;
  const topTray      = playerIsWhite ? captured.black : captured.white;
  const bottomAdv    = playerIsWhite ? captured.advantage : -captured.advantage;

  // Build square highlight styles
  const squareStyles = (() => {
    const s = {};
    if (lastMove) {
      s[lastMove.slice(0, 2)] = { backgroundColor: 'rgba(255,255,0,0.4)' };
      s[lastMove.slice(2, 4)] = { backgroundColor: 'rgba(255,255,0,0.4)' };
    }
    // Premove squares — blue/violet
    if (premove?.from) s[premove.from] = { ...s[premove.from], backgroundColor: 'rgba(100,120,255,0.55)' };
    if (premove?.to)   s[premove.to]   = { ...s[premove.to],   backgroundColor: 'rgba(100,120,255,0.55)' };
    // Selected square
    if (selectedSquare && !s[selectedSquare])
      s[selectedSquare] = { backgroundColor: 'rgba(129,182,76,0.35)' };
    // Legal move dots/rings
    for (const m of legalMoves) {
      if (!m.to) continue;
      const isCap = typeof m.flags === 'string' && (m.flags.includes('c') || m.flags.includes('e'));
      s[m.to] = {
        ...(s[m.to] || {}),
        ...(isCap
          ? { boxShadow: 'inset 0 0 0 4px rgba(0,0,0,0.35)' }
          : { backgroundImage: 'radial-gradient(circle at center,rgba(0,0,0,0.35) 18%,transparent 20%)' }),
      };
    }
    return s;
  })();

  const CapturedTray = ({ pieces, adv }) => (
    <div className="flex items-center overflow-hidden leading-none text-[#b9b7b0]" style={{ gap: '1px' }}>
      {pieces.map((p, i) => (
        <span key={i} className="select-none" style={{ fontSize: boardWidth < 360 ? '0.7rem' : '0.9rem', marginRight: '-4px' }}>
          {PIECE_GLYPHS[p]}
        </span>
      ))}
      {adv > 0 && <span className="ml-2 text-xs font-semibold text-[#9b998f]">+{adv}</span>}
    </div>
  );

  const evalBarW = boardWidth < 400 ? 6 : 10;

  return (
    <div className="min-h-screen bg-[#161512] flex flex-col items-center justify-start sm:justify-center py-3 px-2 sm:p-4 overflow-x-hidden">

      {/* Toast notifications */}
      <div className="fixed top-3 right-3 z-50 flex flex-col gap-1.5 items-end pointer-events-none" style={{ maxWidth: 220 }}>
        {moveNotifications.map(n => (
          <div key={n.id}
            className="rounded-lg border-l-4 border-[#81b64c] bg-[#262421] px-3 py-1.5 text-xs sm:text-sm text-white shadow-lg w-full">
            {n.message}
          </div>
        ))}
      </div>

      {/* Layout: stacks on mobile, side-by-side on lg+ */}
      <div className="flex flex-col items-center gap-4 lg:flex-row lg:items-start lg:gap-5">

        {/* Left: eval bar + board */}
        <div className="flex flex-col items-center">
          <h1 className="mb-2 text-lg sm:text-xl font-bold text-white tracking-tight select-none">Chess vs AI</h1>

          <div className="flex items-stretch" style={{ gap: 8 }}>
            {/* Vertical eval bar */}
            <div className="relative overflow-hidden rounded-full bg-[#3a3836] flex-shrink-0"
              style={{ width: evalBarW, height: boardWidth }}
              title={`Eval: ${formatEval(evalCp, 'w')}`}>
              <div
                className="absolute left-0 w-full bg-[#e9e7df] transition-[height] duration-500 ease-out"
                style={{ height: `${whitePct}%`, [playerIsWhite ? 'bottom' : 'top']: 0 }}
              />
            </div>

            {/* Board column */}
            <div className="flex flex-col" style={{ width: boardWidth }}>
              {/* Opponent info row */}
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0 overflow-hidden">
                  <span className="text-xs sm:text-sm font-semibold text-[#d6d4cf] select-none flex-shrink-0">
                    {playerIsWhite ? '♚ Black' : '♔ White'}
                  </span>
                  <CapturedTray pieces={topTray} adv={-bottomAdv} />
                </div>
                <Clock
                  active={game?.turn() === (playerIsWhite ? 'b' : 'w')}
                  time={formatTime(playerIsWhite ? blackTime : whiteTime)}
                  compact={boardWidth < 380}
                />
              </div>

              {/* Board */}
              <div className="relative">
                <Chessboard
                  id="BasicBoard"
                  position={game?.fen() || ''}
                  onPieceDrop={onPieceDrop}
                  onSquareClick={onSquareClick}
                  boardOrientation={playerIsWhite ? 'white' : 'black'}
                  customBoardStyle={{ borderRadius: '4px', boxShadow: '0 4px 20px rgba(0,0,0,0.6)' }}
                  customDarkSquareStyle={{ backgroundColor: '#769656' }}
                  customLightSquareStyle={{ backgroundColor: '#eeeed2' }}
                  animationDuration={200}
                  boardWidth={boardWidth}
                  customSquareStyles={squareStyles}
                />
                {/* AI thinking indicator */}
                {isThinking && (
                  <div className="absolute left-2 top-2 flex items-center gap-1.5 rounded-md bg-black/75 px-2.5 py-1 text-xs text-white backdrop-blur-sm">
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#81b64c]" />
                    AI thinking…
                  </div>
                )}
                {/* Premove indicator */}
                {premove?.to && (
                  <div className="absolute right-2 top-2 flex items-center gap-1 rounded-md bg-[#5465ff]/80 px-2 py-0.5 text-xs text-white backdrop-blur-sm select-none">
                    Premove
                    <button onClick={() => setPremove(null)} className="ml-0.5 opacity-70 hover:opacity-100 leading-none">×</button>
                  </div>
                )}
              </div>

              {/* Player info row */}
              <div className="mt-1.5 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2 min-w-0 overflow-hidden">
                  <span className="text-xs sm:text-sm font-semibold flex-shrink-0 select-none">
                    <span className="text-[#d6d4cf]">{playerIsWhite ? '♔ White' : '♚ Black'}</span>
                    <span className="text-[#81b64c]"> (You)</span>
                  </span>
                  <CapturedTray pieces={bottomTray} adv={bottomAdv} />
                </div>
                <Clock
                  active={game?.turn() === playerColor}
                  time={formatTime(playerIsWhite ? whiteTime : blackTime)}
                  compact={boardWidth < 380}
                />
              </div>
            </div>
          </div>

          {/* Status bar */}
          <div className="mt-3 flex min-h-8 items-center gap-2 flex-wrap justify-center">
            {gameStatus.isCheckmate && (
              <div className="rounded-md bg-red-700/90 px-3 py-1.5 text-sm font-bold text-white">Checkmate — Game Over</div>
            )}
            {gameStatus.isDraw && (
              <div className="rounded-md bg-yellow-700/90 px-3 py-1.5 text-sm font-bold text-white">Draw!</div>
            )}
            {gameStatus.isCheck && !gameStatus.isCheckmate && (
              <div className="rounded-md bg-orange-600/90 px-3 py-1.5 text-sm font-bold text-white">Check!</div>
            )}
          </div>

          {/* Action buttons */}
          <div className="mt-2 flex gap-2">
            <button onClick={resetGame}
              className="rounded-lg bg-[#81b64c] px-5 py-2 text-sm font-bold text-white transition-colors hover:bg-[#6a9c3e] active:scale-95">
              New Game
            </button>
            <button onClick={() => setGameSetup(true)}
              className="rounded-lg bg-[#3a3836] px-5 py-2 text-sm font-bold text-[#d6d4cf] transition-colors hover:bg-[#4a4846] active:scale-95">
              Settings
            </button>
          </div>
        </div>

        {/* Right: side panel — full width below board on mobile, fixed sidebar on lg+ */}
        <div className="w-full lg:w-64 xl:w-72 rounded-2xl bg-[#262421] p-4 ring-1 ring-white/5"
          style={{ maxWidth: boardWidth + evalBarW + 8 }}>

          <div className="mb-3 flex items-center justify-between border-b border-[#3a3836] pb-2">
            <h2 className="font-bold text-white text-sm">Move History</h2>
            <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
              evalCp > 50 ? 'text-white bg-[#9b998f]/30' : evalCp < -50 ? 'text-[#262421] bg-[#e9e7df]' : 'text-[#9b998f]'
            }`}>
              {formatEval(evalCp, playerColor)}
            </span>
          </div>

          <div className="move-log mb-4 overflow-y-auto" style={{ maxHeight: Math.min(boardWidth * 0.45, 200) }} ref={moveLogRef}>
            <div className="font-mono text-xs sm:text-sm text-white">
              {moveHistory.length === 0 ? (
                <p className="italic text-[#5a5855] text-xs">No moves yet…</p>
              ) : (
                <div className="grid grid-cols-[1.8rem_1fr_1fr] gap-x-2 gap-y-0.5">
                  {Array.from({ length: Math.ceil(moveHistory.length / 2) }).map((_, row) => (
                    <React.Fragment key={row}>
                      <span className="text-[#5a5855] text-xs pt-0.5">{row + 1}.</span>
                      <span className="hover:text-[#81b64c] cursor-default transition-colors">{moveHistory[row * 2]}</span>
                      <span className="hover:text-[#81b64c] cursor-default transition-colors">{moveHistory[row * 2 + 1] || ''}</span>
                    </React.Fragment>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-1.5 border-t border-[#3a3836] pt-3 text-sm">
            <h3 className="mb-2 font-semibold text-white text-xs uppercase tracking-wider opacity-60">Game Info</h3>
            <InfoRow label="You play"   value={playerIsWhite ? 'White' : 'Black'} />
            <InfoRow label="Difficulty" value={`${selectedDifficulty.label} (~${selectedDifficulty.elo})`} />
            <InfoRow label="Time"       value={TIME_CONTROLS[timeControl].label} />
            {thinkInfo && (
              <InfoRow label="Last think" value={`d${thinkInfo.depth} · ${thinkInfo.time_ms}ms`} />
            )}
            <div className="pt-1.5 text-[10px] text-[#5a5855]">
              Tip: drag or click a piece during the bot&apos;s turn to queue a <span className="text-[#5465ff]">premove</span>. Press Esc to cancel.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- Presentational helpers ----
function SetupSection({ title, children }) {
  return (
    <div className="mb-5">
      <h2 className="mb-2.5 text-sm font-semibold text-[#9b998f] uppercase tracking-wide">{title}</h2>
      {children}
    </div>
  );
}

function Clock({ active, time, compact }) {
  return (
    <div className={`flex-shrink-0 rounded-md px-3 py-1.5 transition-colors ${
      active
        ? 'bg-[#81b64c] text-white shadow-md shadow-[#81b64c]/30'
        : 'bg-[#1e1c1a] text-[#d6d4cf] ring-1 ring-white/5'
    }`}>
      <span className={`font-mono font-bold tabular-nums ${compact ? 'text-sm' : 'text-base'}`}>{time}</span>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="flex justify-between items-baseline text-xs sm:text-sm">
      <span className="text-[#6b6965]">{label}</span>
      <span className="font-semibold text-[#c8c6bf] ml-2 text-right">{value}</span>
    </div>
  );
}

export default App;
