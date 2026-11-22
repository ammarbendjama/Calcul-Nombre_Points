#!/usr/bin/env python
"""Point d'entrée : python main.py video.mp4 --moteur pytesseract."""

from app.pipeline import main

if __name__ == "__main__":
    raise SystemExit(main())
