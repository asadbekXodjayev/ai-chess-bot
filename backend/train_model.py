"""
Comprehensive Neural Network Chess Model Training Script
Trains the chess position evaluator using self-play and position evaluation.
"""

import chess
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import random
import os
import time
import argparse
from pathlib import Path
from datetime import datetime

from ai_engine import ChessNeuralNetwork, BoardEncoder, NeuralNetworkChessAI, DEVICE, PIECE_VALUES


class ChessPositionDataset(Dataset):
    """Generate random chess positions for training."""
    
    def __init__(self, num_positions=10000, min_moves=5, max_moves=50):
        self.num_positions = num_positions
        self.min_moves = min_moves
        self.max_moves = max_moves
        self.encoder = BoardEncoder()
        self.positions = []
        self.values = []
        self._generate_positions()
    
    def _generate_positions(self):
        """Generate random legal chess positions."""
        print(f"Generating {self.num_positions} training positions...")
        for i in range(self.num_positions):
            if (i + 1) % 1000 == 0:
                print(f"  Generated {i + 1}/{self.num_positions} positions")
            
            board = chess.Board()
            move_count = random.randint(self.min_moves, self.max_moves)
            
            # Make random moves to reach a position
            for _ in range(move_count):
                if board.is_game_over():
                    break
                legal_moves = list(board.legal_moves)
                if not legal_moves:
                    break
                move = random.choice(legal_moves)
                board.push(move)
            
            # Store position and its evaluation
            features = self.encoder.encode_board(board)
            value = self._evaluate_position(board)
            
            self.positions.append(features)
            self.values.append(value)
    
    def _evaluate_position(self, board: chess.Board) -> float:
        """
        Heuristic evaluation combining material balance and position.
        Returns value from -1 (black winning) to 1 (white winning).
        """
        # Material balance
        material = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = PIECE_VALUES.get(piece.piece_type, 0)
                
                # Positional bonuses
                if piece.piece_type == chess.PAWN:
                    rank = chess.square_rank(square)
                    if piece.color == chess.WHITE:
                        value += rank * 15  # Bonus for advanced pawns
                    else:
                        value += (7 - rank) * 15
                
                elif piece.piece_type == chess.KNIGHT:
                    # Centralization bonus
                    file = chess.square_file(square)
                    rank = chess.square_rank(square)
                    center_dist = min(abs(file - 3.5), abs(rank - 3.5))
                    value += (4 - center_dist) * 10
                
                elif piece.piece_type == chess.BISHOP:
                    # Long diagonal control
                    file = chess.square_file(square)
                    rank = chess.square_rank(square)
                    diagonal_control = 7 - abs(file - rank)
                    value += diagonal_control * 5
                
                elif piece.piece_type == chess.ROOK:
                    # Open file/rank bonus
                    file = chess.square_file(square)
                    rank = chess.square_rank(square)
                    open_file = sum(1 for s in range(8) if board.piece_at(chess.square(file, s)) is None) / 8
                    value += open_file * 20
                
                if piece.color == chess.WHITE:
                    material += value
                else:
                    material -= value
        
        # Normalize to [-1, 1]
        material_norm = max(-1, min(1, material / 5000))
        
        # Bonus for having more pieces developed in opening
        if len(board.move_stack) < 20:
            white_pieces = len([p for p in board.pieces(chess.PAWN, chess.WHITE)] +
                              [p for p in board.pieces(chess.KNIGHT, chess.WHITE)] +
                              [p for p in board.pieces(chess.BISHOP, chess.WHITE)])
            black_pieces = len([p for p in board.pieces(chess.PAWN, chess.BLACK)] +
                              [p for p in board.pieces(chess.KNIGHT, chess.BLACK)] +
                              [p for p in board.pieces(chess.BISHOP, chess.BLACK)])
            development_bonus = (white_pieces - black_pieces) / 16 * 0.1
            material_norm += development_bonus
        
        # Adjust for side to move
        if board.turn == chess.BLACK:
            material_norm = -material_norm
        
        return np.clip(material_norm, -1, 1)
    
    def __len__(self):
        return len(self.positions)
    
    def __getitem__(self, idx):
        features = self.positions[idx]
        value = torch.tensor([[self.values[idx]]], dtype=torch.float32)
        return features, value


class ChessModelTrainer:
    """Trainer for the chess neural network."""
    
    def __init__(
        self,
        model=None,
        learning_rate=0.001,
        batch_size=64,
        device=None
    ):
        self.device = device or DEVICE
        print(f"Using device: {self.device}")
        
        if model is None:
            self.model = ChessNeuralNetwork().to(self.device)
        else:
            self.model = model.to(self.device)
        
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=3,
            verbose=True
        )
        
        self.train_losses = []
        self.val_losses = []
    
    def train_epoch(self, dataloader):
        """Train for one epoch."""
        self.model.train()
        total_loss = 0
        batch_count = 0
        
        for features, targets in dataloader:
            features = features.to(self.device)
            targets = targets.to(self.device)
            
            self.optimizer.zero_grad()
            outputs = self.model(features)
            loss = self.criterion(outputs, targets)
            loss.backward()
            
            # Gradient clipping to prevent exploding gradients
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            
            total_loss += loss.item()
            batch_count += 1
        
        avg_loss = total_loss / max(batch_count, 1)
        return avg_loss
    
    def validate(self, dataloader):
        """Validate the model."""
        self.model.eval()
        total_loss = 0
        batch_count = 0
        
        with torch.no_grad():
            for features, targets in dataloader:
                features = features.to(self.device)
                targets = targets.to(self.device)
                outputs = self.model(features)
                loss = self.criterion(outputs, targets)
                total_loss += loss.item()
                batch_count += 1
        
        avg_loss = total_loss / max(batch_count, 1)
        return avg_loss
    
    def train(
        self,
        epochs=100,
        train_size=8000,
        val_size=2000,
        batch_size=64,
        save_path='chess_model.pth',
        checkpoint_dir='checkpoints'
    ):
        """Train the model with validation and checkpointing."""
        print(f"\n{'='*60}")
        print(f"Training Chess Neural Network")
        print(f"{'='*60}")
        print(f"Epochs: {epochs}")
        print(f"Training size: {train_size}")
        print(f"Validation size: {val_size}")
        print(f"Batch size: {batch_size}")
        print(f"Device: {self.device}")
        print(f"{'='*60}\n")
        
        # Create checkpoint directory
        Path(checkpoint_dir).mkdir(exist_ok=True)
        
        # Generate datasets
        print("Preparing datasets...")
        train_dataset = ChessPositionDataset(train_size)
        val_dataset = ChessPositionDataset(val_size)
        
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=0
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=0
        )
        
        best_val_loss = float('inf')
        patience_counter = 0
        start_time = time.time()
        
        for epoch in range(epochs):
            epoch_start = time.time()
            
            # Training phase
            train_loss = self.train_epoch(train_loader)
            self.train_losses.append(train_loss)
            
            # Validation phase
            val_loss = self.validate(val_loader)
            self.val_losses.append(val_loss)
            
            # Learning rate scheduling
            self.scheduler.step(val_loss)
            
            epoch_time = time.time() - epoch_start
            
            # Print progress
            print(f"Epoch [{epoch+1:3d}/{epochs}] | "
                  f"Train Loss: {train_loss:.6f} | "
                  f"Val Loss: {val_loss:.6f} | "
                  f"Time: {epoch_time:.1f}s")
            
            # Save best model
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                
                # Save best model
                torch.save(self.model.state_dict(), save_path)
                print(f"  ✓ Saved best model with val_loss: {best_val_loss:.6f}")
                
                # Save checkpoint
                checkpoint_path = Path(checkpoint_dir) / f"model_epoch_{epoch+1}.pth"
                torch.save({
                    'epoch': epoch + 1,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'train_loss': train_loss,
                    'val_loss': val_loss,
                }, checkpoint_path)
            else:
                patience_counter += 1
                if patience_counter >= 5:
                    print(f"\n⚠ Early stopping at epoch {epoch+1} (no improvement for 5 epochs)")
                    break
        
        total_time = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"Training Complete!")
        print(f"Best Validation Loss: {best_val_loss:.6f}")
        print(f"Total Training Time: {total_time/60:.1f} minutes")
        print(f"Model saved to: {save_path}")
        print(f"Checkpoints saved to: {checkpoint_dir}/")
        print(f"{'='*60}\n")
        
        return self.model
    
    def plot_losses(self, save_path='training_losses.png'):
        """Plot training and validation losses."""
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(10, 6))
            plt.plot(self.train_losses, label='Training Loss', alpha=0.7)
            plt.plot(self.val_losses, label='Validation Loss', alpha=0.7)
            plt.xlabel('Epoch')
            plt.ylabel('Loss')
            plt.title('Chess Model Training Progress')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig(save_path, dpi=100, bbox_inches='tight')
            print(f"Loss plot saved to: {save_path}")
            plt.close()
        except ImportError:
            print("Matplotlib not available for plotting")


def evaluate_model(model_path, num_test_positions=10):
    """Evaluate the trained model on test positions."""
    print(f"\n{'='*60}")
    print("Testing Trained Model")
    print(f"{'='*60}\n")
    
    ai = NeuralNetworkChessAI(model_path=model_path)
    
    # Test positions with expected good moves
    test_positions = [
        ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "Starting position"),
        ("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "Fried Liver Attack"),
        ("rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", "Sicilian Defense"),
        ("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 4 4", "Italian Game"),
        ("rnbqkb1r/pp1p1ppp/5n2/2p1p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 4", "Center Game"),
    ]
    
    print(f"Testing on {len(test_positions)} positions:\n")
    
    for fen, description in test_positions:
        move = ai.get_best_move(fen)
        board = chess.Board(fen)
        
        if move:
            move_obj = chess.Move.from_uci(move)
            san = board.san(move_obj)
            print(f"✓ {description}")
            print(f"  Best move: {san} ({move})")
        else:
            print(f"✗ {description}")
            print(f"  Failed to find move")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Train the Chess Neural Network Model'
    )
    parser.add_argument('--epochs', type=int, default=50,
                       help='Number of training epochs (default: 50)')
    parser.add_argument('--train-size', type=int, default=8000,
                       help='Number of training positions (default: 8000)')
    parser.add_argument('--val-size', type=int, default=2000,
                       help='Number of validation positions (default: 2000)')
    parser.add_argument('--batch-size', type=int, default=64,
                       help='Batch size (default: 64)')
    parser.add_argument('--learning-rate', type=float, default=0.001,
                       help='Learning rate (default: 0.001)')
    parser.add_argument('--model-path', type=str, default='chess_model.pth',
                       help='Path to save the trained model (default: chess_model.pth)')
    parser.add_argument('--checkpoint-dir', type=str, default='checkpoints',
                       help='Directory for model checkpoints (default: checkpoints)')
    parser.add_argument('--test', action='store_true',
                       help='Test the trained model')
    parser.add_argument('--no-save', action='store_true',
                       help='Do not save the model')
    
    args = parser.parse_args()
    
    try:
        # Create trainer
        trainer = ChessModelTrainer(
            learning_rate=args.learning_rate,
            batch_size=args.batch_size
        )
        
        # Train model
        trainer.train(
            epochs=args.epochs,
            train_size=args.train_size,
            val_size=args.val_size,
            batch_size=args.batch_size,
            save_path=args.model_path,
            checkpoint_dir=args.checkpoint_dir
        )
        
        # Plot losses if training completed
        trainer.plot_losses()
        
        # Test if requested
        if args.test and os.path.exists(args.model_path):
            evaluate_model(args.model_path)
        
        print("\n✓ Training script completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Training interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
