#!/usr/bin/env python3
"""
Single launcher for the phishing detection system.

Replaces the previous run.py / run_hybrid.py / run_interactive.py / start.py /
start_simple.py, which had all diverged into calling different (and by now
deleted) predictor variants. Importing src.predictor already triggers the
SSL patch and NLTK data download (see src/preprocessing.py), so this file
doesn't need to duplicate that setup.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def train():
    print("\n🚀 Starting training pipeline...")
    from main import train_pipeline
    train_pipeline()


def predict(use_rules=True):
    from src.predictor import PhishingPredictor, run_interactive
    run_interactive(PhishingPredictor(use_rules=use_rules))


def show_menu():
    print("\n" + "=" * 60)
    print("🔍 PHISHING EMAIL DETECTION SYSTEM")
    print("=" * 60)
    print("\nOptions:")
    print("1. Train new model")
    print("2. Run interactive prediction mode")
    print("3. Exit")

    choice = input("\nChoice (1-3): ").strip()

    if choice == '1':
        train()
    elif choice == '2':
        predict()
    else:
        print("\n👋 Goodbye!")


def main():
    parser = argparse.ArgumentParser(description="Phishing email detection system")
    parser.add_argument('--train', action='store_true', help="Run the training pipeline")
    parser.add_argument('--predict', action='store_true', help="Launch interactive prediction mode")
    parser.add_argument('--no-rules', action='store_true',
                         help="Disable rule-based augmentation (pure ML scoring)")
    args = parser.parse_args()

    if args.train:
        train()
    elif args.predict:
        predict(use_rules=not args.no_rules)
    else:
        show_menu()


if __name__ == "__main__":
    main()
