"""
Test configuration file. Setup Python path so imports work correctly
from any test directory level.
"""
import os
import sys

# Get absolute path to root of project
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

# Add project root to Python path if not already there
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Allows both "from utils.x import y" and "from bot.utils.x import y" to work
# in test files, making tests runnable from any directory level
