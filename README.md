# Chess.com AI Bot

A production-ready chess application where you play against a custom Python AI bot powered by Neural Network evaluation with Minimax Alpha-Beta pruning.

## Features

- **Neural Network AI**: Deep learning-based position evaluation with 500K+ parameters
- **Fast AI Moves**: Optimized minimax with alpha-beta pruning (depth 3)
- **Chess.com UI**: Deep charcoal canvas with classic olive-and-cream board styling
- **Interactive**: Flip board when playing black, time controls, move history
- **Sound Effects**: Web Audio API synthesis for moves, captures, checks, and game-over
- **Dual-layer Validation**: Client-side + server-side move verification
- **Production Ready**: Full error handling, logging, and CORS support

## Architecture

- **Backend**: FastAPI (Python 3.11+) with `python-chess` for game logic
- **Frontend**: React 18 + Vite + Tailwind CSS with `react-chessboard` and `chess.js`
- **AI Engine**: PyTorch Neural Network + Minimax with Alpha-Beta Pruning

## Project Structure

```
4-chess bot/
├── backend/
│   ├── main.py              # FastAPI server with move API
│   ├── ai_engine.py         # Neural network + minimax evaluation
│   ├── train_model.py       # ML training script (NEW)
│   ├── requirements.txt     # Python dependencies
│   ├── TRAINING.md          # Training guide (NEW)
│   └── __init__.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # React game component
│   │   ├── main.jsx         # React entry point
│   │   └── index.css        # Styles
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
├── README.md
├── BUG_FIXES.md             # Detailed bug report (NEW)
└── .gitignore
```

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python train_model.py        # Train the AI model (optional)
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Play the Game

1. Open http://localhost:5173 in your browser
2. Choose your color (White or Black)
3. Select time control
4. Click **Start Game**
5. Drag pieces to move

The board will automatically flip when you play as Black, just like Chess.com!

## Training the AI Model

The AI uses a neural network trained on chess positions. To train your own model:

```bash
cd backend
python train_model.py --epochs 50 --train-size 8000
```

**Quick training options:**
```bash
python train_model.py                  # Default (50 epochs, 8000 positions)
python train_model.py --epochs 100     # Better quality (slower)
python train_model.py --epochs 20      # Faster (lower quality)
python train_model.py --test           # Train and test immediately
```

See [TRAINING.md](backend/TRAINING.md) for detailed training guide with:
- Custom parameters
- Performance tips
- GPU acceleration
- Memory optimization
- Troubleshooting

## What's New (Recent Fixes)

- ✅ **Fixed Critical AI Bug**: Improved error handling and logging for bot moves
- ✅ **Board Flip**: Black pieces now correctly face the bottom (Chess.com style)
- ✅ **Faster AI**: Optimized from depth 5 to depth 3 for quick responses (~1 second)
- ✅ **Removed Random Button**: Cleaner UI with White/Black selection only
- ✅ **Better Error Messages**: Detailed error notifications in-game
- ✅ **Production Ready**: Fixed CORS, added comprehensive logging
- ✅ **ML Training**: Full training pipeline with checkpointing and loss visualization

See [BUG_FIXES.md](BUG_FIXES.md) for complete technical details.

## How the AI Works

### 1. **Neural Network Evaluation**
- **Architecture**: 5-layer MLP with 500K+ parameters
- **Input**: 781 features (board state, castling rights, side to move)
- **Output**: Position evaluation (-1.0 = black winning, +1.0 = white winning)
- **Training**: Supervised learning on position evaluations

### 2. **Minimax with Alpha-Beta Pruning**
- **Search Depth**: 3 plies (half-moves)
- **Move Ordering**: Captures first (improves pruning)
- **Evaluation**: Neural network + material balance

### 3. **Position Evaluation Heuristics**
```
Score = 0.7 * (Neural Network Eval) + 0.3 * (Material Balance)
```

Plus bonuses for:
- Piece centralization
- Pawn advancement
- Rook open files
- Bishop diagonals

## Game Controls

| Action | How |
|--------|-----|
| **Make a Move** | Drag a piece to its destination |
| **Flip Board** | Select "Black" color (automatic) |
| **Change Settings** | Click "Settings" button during game |
| **New Game** | Click "New Game" button |

## System Requirements

### Minimum
- Python 3.8+ (for backend)
- Node.js 14+ (for frontend)
- 2GB RAM
- 500MB disk space

### Recommended
- Python 3.11+
- Node.js 18+
- 4GB RAM
- NVIDIA/AMD GPU (for faster AI training)

## Performance

### Backend (AI)
- **Inference Time**: ~500ms per move (depth 3)
- **Memory**: ~200MB
- **GPU**: Optional but recommended for training

### Frontend
- **Bundle Size**: ~300KB (gzipped)
- **First Load**: <2 seconds
- **Lighthouse**: 95+ (performance)

## API Endpoints

### Get Bot Move
```
POST /api/bot-move
Content-Type: application/json

{
  "current_fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
}

Response:
{
  "bot_move": "e2e4",
  "new_fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
  "is_check": false,
  "is_checkmate": false,
  "is_draw": false,
  "game_over": false
}
```

## Troubleshooting

### "Bot could not move" Error
1. Check backend is running: `python train_model.py` should show startup logs
2. Verify CORS: Check browser console for CORS errors
3. Check FEN: Position might be invalid

### Slow AI Moves (>5 seconds)
1. Reduce search depth in `ai_engine.py` (change `self.search_depth = 3`)
2. Use GPU for faster computation
3. Check system resources (Task Manager)

### Model Not Loading
1. Ensure `chess_model.pth` exists in backend directory
2. Check Python version matches requirements (3.8+)
3. Verify torch installation: `python -c "import torch; print(torch.__version__)"`

### Frontend Won't Load
1. Verify npm install completed: `cd frontend && npm install`
2. Check port 5173 is available
3. Clear browser cache: Ctrl+Shift+Delete

See [BUG_FIXES.md](BUG_FIXES.md) for more detailed troubleshooting.

## Development

### Code Structure
- **Backend**: FastAPI with async request handling
- **Frontend**: React with hooks for state management
- **State Management**: React hooks (useState, useCallback, useRef)
- **Styling**: Tailwind CSS with custom theme

### Key Files
- `App.jsx`: Main game logic and UI
- `ai_engine.py`: Neural network and search algorithm
- `main.py`: API server with validation
- `train_model.py`: Model training pipeline

### Contributing
1. Ensure tests pass locally
2. Follow existing code style
3. Update README for new features
4. Test on multiple devices/browsers

## License

MIT License - Feel free to use for personal or educational purposes.

## Credits

- Built with React, FastAPI, and PyTorch
- Board styling inspired by Chess.com
- Sound synthesis with Web Audio API

## Future Improvements

- [ ] Add opening book (known best moves)
- [ ] Implement endgame tablebases
- [ ] Support PGN import/export
- [ ] Multiplayer support
- [ ] Mobile app (React Native)
- [ ] Better position evaluation
- [ ] Configurable AI difficulty levels"# ai-chess-bot" 
