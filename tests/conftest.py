"""conftest.py — Shared pytest configuration for spacePirates tests."""
import os
import sys

# Ensure the package root is on the path so all game modules can be imported
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Set dummy SDL drivers before anything imports pygame
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
