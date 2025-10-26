"""Package initialization for src.

Set up a package-level logger so other modules can import `from src import logger`.
"""
from .utils import setup_logging

# Initialize a package logger at INFO level by default
logger = setup_logging()

__all__ = ["logger"]
