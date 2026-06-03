# Chess AI Model Training Guide

This guide explains how to train the neural network model for the chess AI bot.

## Quick Start

### Option 1: Train with Default Settings (Recommended for First-Time Users)

```bash
cd backend
python train_model.py
```

This will:
- Generate 8,000 training positions and 2,000 validation positions
- Train for 50 epochs
- Save the model to `chess_model.pth`
- Create checkpoints in the `checkpoints/` directory
- Display loss plot as `training_losses.png`

### Option 2: Custom Training Parameters

```bash
python train_model.py --epochs 100 --train-size 15000 --batch-size 32 --learning-rate 0.0005
```

## Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--epochs` | 50 | Number of training epochs |
| `--train-size` | 8000 | Number of training positions to generate |
| `--val-size` | 2000 | Number of validation positions to generate |
| `--batch-size` | 64 | Batch size for training (higher = faster, lower = more memory) |
| `--learning-rate` | 0.001 | Learning rate for optimizer |
| `--model-path` | chess_model.pth | Path to save trained model |
| `--checkpoint-dir` | checkpoints | Directory to save checkpoints |
| `--test` | — | Test the model after training |
| `--no-save` | — | Don't save the model (training only) |

## Examples

### Fast Training (Lower Quality)
```bash
python train_model.py --epochs 20 --train-size 4000 --batch-size 128
```

### High-Quality Training (Longer Duration)
```bash
python train_model.py --epochs 200 --train-size 20000 --val-size 5000 --batch-size 32
```

### Train and Test Immediately
```bash
python train_model.py --epochs 50 --test
```

### Save Checkpoints at Different Epochs
```bash
python train_model.py --epochs 100 --checkpoint-dir my_checkpoints
```

## Training Features

### 1. **Position Evaluation Heuristic**
The model learns to evaluate chess positions using:
- Material balance (piece values)
- Positional factors:
  - Pawn advancement (more advanced = better)
  - Knight centralization
  - Bishop diagonal control
  - Rook open file/rank bonuses
  - Development bonus in opening phase

### 2. **Learning Rate Scheduling**
- Uses ReduceLROnPlateau scheduler
- Automatically reduces learning rate if validation loss plateaus
- Prevents overfitting

### 3. **Early Stopping**
- Stops training if no improvement for 5 epochs
- Saves the best model automatically
- Prevents wasting computation

### 4. **Gradient Clipping**
- Prevents exploding gradients
- Max norm: 1.0

### 5. **Checkpointing**
- Saves model at every improvement
- Saves complete training state for resuming

### 6. **Loss Visualization**
- Automatically generates `training_losses.png`
- Shows training vs validation loss over epochs
- Requires matplotlib (optional)

## Training Tips

### 1. **GPU Acceleration**
The model will automatically use GPU if available. To verify:

```bash
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}')"
```

If you have an NVIDIA GPU but it's not being used:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 2. **Memory Optimization**

If you run out of memory, reduce batch size:
```bash
python train_model.py --batch-size 32
```

Or reduce training size:
```bash
python train_model.py --train-size 4000 --val-size 1000
```

### 3. **Training Duration**

Typical times on different hardware:
- **CPU**: ~1-2 hours for 50 epochs with 8000 positions
- **GPU (NVIDIA)**: ~5-10 minutes for 50 epochs with 8000 positions
- **GPU (Apple Silicon)**: ~10-20 minutes for 50 epochs with 8000 positions

### 4. **Model Quality vs. Speed Trade-off**

Better model (slower AI):
```bash
python train_model.py --epochs 200 --train-size 30000 --learning-rate 0.0001
```

Faster AI (lower quality):
```bash
python train_model.py --epochs 20 --train-size 4000 --learning-rate 0.001
```

## Using the Trained Model

### 1. **In the Game**

The trained model will be automatically used if `chess_model.pth` exists in the `backend/` directory.

To use a specific model:
1. Copy the model file: `cp my_model.pth chess_model.pth`
2. Run the game normally

### 2. **In Python**

```python
from ai_engine import NeuralNetworkChessAI

# Load the trained model
ai = NeuralNetworkChessAI(model_path='chess_model.pth')

# Get best move for a position
fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
best_move = ai.get_best_move(fen)
print(f"Best move: {best_move}")
```

## Monitoring Training Progress

While training is running, you can monitor:

1. **Loss values**: Should decrease over time
2. **Validation loss**: Should decrease and plateau
3. **Time per epoch**: Should be consistent
4. **Checkpoint saves**: ✓ indicates improvement

## Understanding the Output

```
Epoch [ 25/ 50] | Train Loss: 0.025634 | Val Loss: 0.028945 | Time: 12.5s
  ✓ Saved best model with val_loss: 0.028945
```

- **Train Loss**: Error on training data (should decrease)
- **Val Loss**: Error on validation data (should decrease then plateau)
- **Time**: Seconds per epoch
- **✓ Saved**: Model improved - checkpoint saved

## Troubleshooting

### Problem: "ModuleNotFoundError: No module named 'torch'"
**Solution**: Install requirements
```bash
pip install -r requirements.txt
```

### Problem: "CUDA out of memory"
**Solution**: Reduce batch size or dataset size
```bash
python train_model.py --batch-size 16 --train-size 4000
```

### Problem: Training is very slow
**Solution**: Ensure GPU is being used
```bash
python train_model.py --batch-size 128  # Larger batch = better GPU utilization
```

### Problem: Model not being used by the game
**Solution**: Ensure `chess_model.pth` is in the `backend/` directory
```bash
ls -la backend/chess_model.pth  # Check if file exists
```

## Advanced: Fine-tuning an Existing Model

If you have a pre-trained model and want to improve it:

```python
from train_model import ChessModelTrainer
from ai_engine import NeuralNetworkChessAI

# Load existing model
model = NeuralNetworkChessAI(model_path='chess_model.pth').model

# Continue training
trainer = ChessModelTrainer(model=model, learning_rate=0.0001)
trainer.train(epochs=50)
```

## Model Architecture

The neural network consists of:
- **Input**: 781 features (board position, castling rights, side to move, en passant)
- **Layer 1**: 512 neurons (ReLU + Dropout)
- **Layer 2**: 256 neurons (ReLU + Dropout)
- **Layer 3**: 128 neurons (ReLU + Dropout)
- **Layer 4**: 64 neurons (ReLU + Dropout)
- **Output**: 1 value (position score from -1 to 1)

Total parameters: ~500,000

## Next Steps

1. **Train the model** using the commands above
2. **Test it in the game** to see the AI play
3. **Evaluate performance** on different positions
4. **Fine-tune** parameters for better results
5. **Share your best model!**

## Resources

- [PyTorch Documentation](https://pytorch.org/docs/stable/index.html)
- [Chess.py Documentation](https://python-chess.readthedocs.io/)
- [Deep Learning Basics](https://www.deeplearningbook.org/)
