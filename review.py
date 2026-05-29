#!/usr/bin/env python
"""Convenience entry point: python review.py --pr <URL>"""
import sys
import os

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.main import main

if __name__ == "__main__":
    main()
