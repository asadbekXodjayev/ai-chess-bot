"""
Fast Training Script for the Optimized Chess AI
Architecture: 768 -> 64 -> 32 -> 1 (matches EfficientChessNetwork)
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

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Piece values
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}


class EfficientChessNetwork(nn.Module):
    """
    Optimized neural network for fast inference.
    Architecture: 768 -> 64 -> 32 -> 1
    """
    
    def __init__(self):
        super(EfficientChessNetwork, self).__init__()
        self.input_size = 768  # 12 piece types * 64 squares
        
        # Small network for fast inference
        self.fc1 = nn.Linear(self.input_size, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 1)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        x = torch.tanh(self.fc3(x))
        return x


class BoardEncoder:
    """Encodes chess board positions into feature vectors."""
    
    @staticmethod
    def encode_board(board: chess.Board) -> torch.Tensor:
        features = []
        
        # Piece placement encoding (64 squares * 12 piece types)
        for piece_type in range(1, 7):
            for color in [chess.WHITE, chess.BLACK]:
                bitboard = board.pieces(piece_type, color)
                for square in chess.SQUARES:
                    features.append(1.0 if bitboard & (1 << square) else 0.0)
        
        return torch.tensor([features], dtype=torch.float32)


class FastChessDataset(Dataset):
    """Fast dataset with better chess position generation."""
    
    def __init__(self, num_positions=10000):
        self.num_positions = num_positions
        
    def generate_position(self):
        """Generate a more realistic chess position."""
        board = chess.Board()
        
        # Make more moves to reach mid-game positions
        max_moves = random.randint(8, 35)
        move_count = 0
        
        while move_count < max_moves and not board.is_game_over():
            moves = list(board.legal_moves)
            if not moves:
                break
            
            # Bias toward capturing and checking moves for tactical positions
            capture_moves = [m for m in moves if board.is_capture(m)]
            check_moves = [m for m in moves if board.gives_check(m)]
            
            if capture_moves and random.random() < 0.3:
                move = random.choice(capture_moves)
            elif check_moves and random.random() < 0.2:
                move = random.choice(check_moves)
            else:
                move = random.choice(moves)
                
            board.push(move)
            move_count += 1
            
        return board
    
    def evaluate_heuristic(self, board):
        """Material + positional evaluation as target."""
        score = 0
        
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = PIECE_VALUES[piece.piece_type]
                
                # Positional bonuses
                if piece.piece_type == chess.PAWN:
                    # Pawns advance
                    if piece.color == chess.WHITE:
                        value += square // 8 * 5
                    else:
                        value -= (7 - square // 8) * 5
                elif piece.piece_type == chess.KNIGHT:
                    # Centralize knights
                    center_dist = abs(square % 8 - 3.5) + abs(square // 8 - 3.5)
                    value += (7 - center_dist) * 2
                elif piece.piece_type == chess.BISHOP:
                    # Bishops like diagonals
                    value += min(square % 8, 7 - square % 8) * 2
                
                if piece.color == chess.WHITE:
                    score += value
                else:
                    score -= value
        
        # Normalize to [-1, 1]
        return max(-1, min(1, score / 5000))
    
    def __len__(self):
        return self.num_positions
    
    def __getitem__(self, idx):
        board = self.generate_position()
        features = BoardEncoder.encode_board(board)
        target = self.evaluate_heuristic(board)
        
        # Adjust for side to move
        if board.turn == chess.BLACK:
            target = -target
            
        return features, torch.tensor([[target]], dtype=torch.float32)


def train_fast_model(epochs=80, batch_size=128):
    """Train the efficient model."""
    print("=" * 50)
    print("Fast Chess AI Training (Efficient Network)")
    print("Architecture: 768 -> 64 -> 32 -> 1")
    print("=" * 50)
    print(f"Using device: {DEVICE}")
    
    # Create model
    model = EfficientChessNetwork().to(DEVICE)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.002)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)
    
    # Create dataset
    print("Generating training data...")
    dataset = FastChessDataset(num_positions=10000)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    best_loss = float('inf')
    
    for epoch in range(epochs):
        model.train()
        total_loss = 0
        
        for features, targets in tqdm(dataloader, desc=f"Epoch {epoch+1}/{epochs}"):
            features = features.to(DEVICE)
            targets = targets.to(DEVICE)
            
            optimizer.zero_grad()
            outputs = model(features)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        avg_loss = total_loss / len(dataloader)
        scheduler.step(avg_loss)
        
        if avg_loss < best_loss:
            best_loss = avg_loss
            torch.save(model.state_dict(), 'chess_model_fast.pth')
            print(f"  Epoch [{epoch+1}/{epochs}] Loss: {avg_loss:.6f} - Saved best model")
        else:
            print(f"  Epoch [{epoch+1}/{epochs}] Loss: {avg_loss:.6f}")
    
    print(f"\nTraining complete! Best model saved to chess_model_fast.pth")
    print(f"Final loss: {best_loss:.6f}")
    
    # Test the model
    print("\n" + "=" * 50)
    print("Testing Trained Model")
    print("=" * 50)
    
    model.eval()
    test_positions = [
        ("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "Starting position"),
        ("r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "Fried Liver"),
        ("rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2", "Sicilian"),
    ]
    
    encoder = BoardEncoder()
    with torch.no_grad():
        for fen, desc in test_positions:
            board = chess.Board(fen)
            features = encoder.encode_board(board).to(DEVICE)
            output = model(features)
            print(f"{desc}: Score: {output.item():.4f}")
    
    return model


if __name__ == "__main__":
    train_fast_model(epochs=80, batch_size=128)