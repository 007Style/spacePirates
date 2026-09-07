"""main.py — Entry point for Space Pirates."""
import sys
import os

# Ensure imports resolve from project root
sys.path.insert(0, os.path.dirname(__file__))

import pygame
from core.game import Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
