#!/usr/bin/env python3
"""
Quick Training Script - Easiest Way to Train Your Chess AI
Just run: python quick_train.py
"""

import subprocess
import sys
import os

def run_training():
    """Run the training with sensible defaults."""
    
    print("\n" + "="*60)
    print("🎯 Chess AI Model Training")
    print("="*60 + "\n")
    
    print("Select training preset:\n")
    print("1. Quick Train (5 min) - Demo only")
    print("2. Standard Train (30 min) - Good quality")
    print("3. Best Train (2-3 hours) - Highest quality")
    print("4. Custom - Specify your own parameters\n")
    
    choice = input("Enter choice (1-4): ").strip()
    
    args = []
    
    if choice == "1":
        print("\n🚀 Starting Quick Training (20 epochs, 4000 positions)...")
        args = ["--epochs", "20", "--train-size", "4000", "--val-size", "1000"]
    
    elif choice == "2":
        print("\n🚀 Starting Standard Training (50 epochs, 8000 positions)...")
        args = ["--epochs", "50", "--train-size", "8000", "--val-size", "2000"]
    
    elif choice == "3":
        print("\n🚀 Starting Best Training (100 epochs, 20000 positions)...")
        args = ["--epochs", "100", "--train-size", "20000", "--val-size", "5000"]
    
    elif choice == "4":
        epochs = input("Number of epochs (default 50): ").strip() or "50"
        train_size = input("Training positions (default 8000): ").strip() or "8000"
        batch_size = input("Batch size (default 64): ").strip() or "64"
        lr = input("Learning rate (default 0.001): ").strip() or "0.001"
        
        args = [
            "--epochs", epochs,
            "--train-size", train_size,
            "--batch-size", batch_size,
            "--learning-rate", lr
        ]
        print(f"\n🚀 Starting training with custom parameters...")
    
    else:
        print("Invalid choice!")
        return
    
    # Add test flag
    test = input("\nTest model after training? (y/n, default y): ").strip().lower() != "n"
    if test:
        args.append("--test")
    
    # Run training
    cmd = ["python", "train_model.py"] + args
    print(f"\n📊 Running: {' '.join(cmd)}\n")
    print("="*60 + "\n")
    
    try:
        result = subprocess.run(cmd, check=True)
        
        print("\n" + "="*60)
        print("✅ Training Complete!")
        print("="*60 + "\n")
        
        print("📁 Your model is saved as: chess_model.pth")
        print("🎮 The game will automatically use it next time you play!\n")
        
        print("To start the game:")
        print("  cd backend")
        print("  uvicorn main:app --reload")
        print("\nThen in another terminal:")
        print("  cd frontend") 
        print("  npm run dev")
        print("\nThen open: http://localhost:5173\n")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Training failed with error code {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Training interrupted by user")
        sys.exit(0)

if __name__ == "__main__":
    os.chdir("backend")
    run_training()
