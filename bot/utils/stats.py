"""
Statistics manager for the OpenGov bot.
Tracks and logs various bot operations and performance metrics.
"""

import time
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class StatsManager:
    """
    Manages statistics tracking for the OpenGov bot.
    Records operation counts, timing information, and success rates.
    """

    def __init__(self):
        """Initialize the stats manager with empty counters."""
        self.stats = {
            "operations": {},
            "start_time": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        self.stats_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "bot_stats.json")
        self._load_stats()

    def _load_stats(self) -> None:
        """Load existing stats from file if available."""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    self.stats = json.load(f)
        except Exception as e:
            print(f"Error loading stats: {e}")

    def _save_stats(self) -> None:
        """Save current stats to file."""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.stats_file), exist_ok=True)

            self.stats["last_updated"] = datetime.now().isoformat()
            with open(self.stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"Error saving stats: {e}")

    def record_run(self, operation: str, success: bool = True) -> None:
        """
        Record a run of a specific operation.

        Args:
            operation: Name of operation
            success: Whether operation was successful
        """
        if operation not in self.stats["operations"]:
            self.stats["operations"][operation] = {
                "total_runs": 0,
                "successful_runs": 0,
                "last_run": None,
                "average_time_ms": 0
            }

        self.stats["operations"][operation]["total_runs"] += 1
        if success:
            self.stats["operations"][operation]["successful_runs"] += 1
        self.stats["operations"][operation]["last_run"] = datetime.now().isoformat()

        self._save_stats()

    def log_run(self, operation: str) -> None:
        """
        Log a successful run of an operation.
        Simplified version of record_run with success=True.

        Args:
            operation: Name of the operation
        """
        self.record_run(operation, True)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current statistics.

        Returns:
            Dict containing all tracked statistics
        """
        return self.stats

    def get_operation_stats(self, operation: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific operation.

        Args:
            operation: Name of the operation

        Returns:
            Dict containing operation statistics or None if not found
        """
        return self.stats["operations"].get(operation)

    def get_last_run_time(self, operation: str) -> Optional[str]:
        """
        Get the last run time of a specific operation.

        Args:
            operation: Name of the operation

        Returns:
            ISO formatted timestamp of last run or None if not found
        """
        op_stats = self.get_operation_stats(operation)
        return op_stats.get("last_run") if op_stats else None

    def clear_stats(self) -> None:
        """Reset all statistics."""
        self.stats = {
            "operations": {},
            "start_time": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        self._save_stats()
