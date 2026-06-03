"""
Training script for the Neural Network Chess AI.
This script trains the model on chess positions using self-play.
"""

import chess
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import random
from tqdm import tqdm
import os

from ai_engine import ChessNeuralNetwork, BoardEncoder, PIECE_VALUES


class ChessPositionDataset(Dataset):
    """Dataset for chess positions."""
    
    def __init__(self, num_positions=10000):
        self.num_positions = num_positions
        self.positions = []
        self.targets = []
        self.encoder = BoardEncoder()
        
    def generate_random_position(self):
        """Generate a random legal chess position."""
        board = chess.Board()
        
        # Make random moves to reach a position
        max_moves = random.randint(10, 40)
        for _ in range(max_moves):
            if board.is_game_over():
                break
            moves = list(board.legal_moves)
            if not moves:
                break
            move = random.choice(moves)
            board.push(move)
        
        return board
    
    def evaluate_with_stockfish_heuristic(self, board):
        """
        Evaluate position using a simple heuristic as target.
        In production, you would use Stockfish or grandmaster games.
        """
        # Material balance
        material = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = PIECE_VALUES[piece.piece_type]
                # Positional bonuses
                if piece.piece_type == chess.PAWN:
                    value += square // 8 * 10  # Advance pawns
                elif piece.piece_type == chess.KNIGHT:
                    value += min(square // 8, 7 - square // 8) * 5  # Centralize
                    value += min(square % 8, 7 - square % 8) * 5
                
                if piece.color == chess.WHITE:
                    material += value
                else:
                    material -= value
        
        # Normalize to [-1, 1]
        return max(-1, min(1, material / 5000))
    
    def __len__(self):
        return self.num_positions
    
    def __getitem__(self, idx):
        board = self.generate_random_position()
        features = self.encoder.encode_board(board)
        target = self.evaluate_with_stockfish_heuristic(board)
        
        if board.turn == chess.BLACK:
            target = -target
        
        return features, torch.tensor([[target]], dtype=torch.float32)


class Trainer:
    """Trainer class for the chess neural network."""
    
    def __init__(
        self,
        model=None,
        learning_rate=0.001,
        batch_size=64,
        device=None
    ):
        self.device = device or (torch.device('cuda' if torch.cuda.is_available() else 'cpu'))
        print(f"Using device: {self.device}")
        
        if model is None:
            self.model = ChessNeuralNetwork().to(self.device)
        else:
            self.model = model.to(self.device)
        
        self.criterion = nn.MSELoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=5
        )
    
    def train_epoch(self, dataloader):
        """Train for one epoch."""
        self.model.train()
        total_loss = 0
        
        for features, targets in dataloader:
            features = features.to(self.device)
            targets = targets.to(self.device)
            
            self.optimizer.zero_grad()
            outputs = self.model(features)
            loss = self.criterion(outputs, targets)
            loss.backward()
            self.optimizer.step()
            
            total_loss += loss.item()
        
        return total_loss / len(dataloader)
    
    def evaluate(self, dataloader):
        """Evaluate the model."""
        self.model.eval()
        total_loss = 0
        
        with torch.no_grad():
            for features, targets in dataloader:
                features = features.to(self.device)
                targets = targets.to(self.device)
                outputs = self.model(features)
                loss = self.criterion(outputs, targets)
                total_loss += loss.item()
        
        return total_loss / len(dataloader)
    
    def train(
        self,
        epochs=100,
        train_size=8000,
        val_size=2000,
        batch_size=64,
        save_path='chess_model.pth'
    ):
        """Train the model."""
        print(f"Generating training data...")
        
        # Create datasets ONCE instead of recreating them
        train_dataset = ChessPositionDataset(train_size)
        val_dataset = ChessPositionDataset(val_size)
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
        
        best_loss = float('inf')
        
        for epoch in range(epochs):
            train_loss = self.train_epoch(train_loader)
            val_loss = self.evaluate(val_loader)
            self.scheduler.step(val_loss)
            
            print(f"Epoch [{epoch+1}/{epochs}]")
            print(f"  Train Loss: {train_loss:.6f}")
            print(f"  Val Loss: {val_loss:.6f}")
            
            if val_loss < best_loss:
                best_loss = val_loss
                torch.save(self.model.state_dict(), save_path)
                print(f"  Saved new best model with loss {best_loss:.6f}")
        
        print(f"\nTraining complete! Best model saved to {save_path}")
        return self.model


def main():
    """Main training function."""
    print("=" * 50)
    print("Chess Neural Network Training")
    print("=" * 50)
    
    # Create trainer
    trainer = Trainer(
        learning_rate=0.001,
        batch_size=64
    )
    
    # Train
    trainer.train(
        epochs=100,
        train_size=8000,
        val_size=2000,
        batch_size=64,
        save_path='chess_model.pth'
    )
    
    # Test the trained model
    print("\n" + "=" * 50)
    print("Testing Trained Model")
    print("=" * 50)
    
    from ai_engine import NeuralNetworkChessAI
    
    # Load the trained model
    ai = NeuralNetworkChessAI(model_path='chess_model.pth')
    
    # Test positions
    test_positions = [
        ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "Starting position"),
        ("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "Fried Liver attack"),
        ("rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", "Sicilian defense"),
    ]
    
    for fen, description in test_positions:
        move = ai.get_best_move(fen)
        print(f"\n{description}:")
        print(f"  FEN: {fen}")
        print(f"  Best move: {move}")


if __name__ == "__main__":
    main()