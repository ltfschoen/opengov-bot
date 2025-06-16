import json
import os
import time
import shutil
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Union

class CacheManager:
    """
    Enhanced version of CacheManager that supports multi-network operations.
    """

    @staticmethod
    def save_data_to_cache(filename: str, data: dict):
        """Save data to a cache file."""
        with open(filename, 'w') as file:
            json.dump(data, file)

    @staticmethod
    def get_cache_difference(filename: str, data: dict):
        """
        Compare current data with cached data and return differences.
        Used to identify new referenda.
        """
        try:
            with open(filename, 'r') as file:
                try:
                    saved_data = json.load(file)
                except json.JSONDecodeError:
                    saved_data = {}

            if not saved_data:
                return {"dictionary_item_added": ["root[]"]}

            from deepdiff import DeepDiff

            diff = DeepDiff(saved_data, data)
            return diff
        except FileNotFoundError:
            return {"dictionary_item_added": ["root[]"]}

    @staticmethod
    def rotating_backup_file(source_path: str, backup_dir: str, max_backups=10):
        """Create rotating backups of important files."""
        if not os.path.exists(source_path):
            logging.warning(f"Source file {source_path} does not exist, cannot create backup.")
            return False

        os.makedirs(backup_dir, exist_ok=True)

        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(source_path)
        backup_path = os.path.join(backup_dir, f"{filename}.{timestamp}")

        # Create backup
        shutil.copy2(source_path, backup_path)
        logging.info(f"Backup created: {backup_path}")

        # Remove old backups if exceeding max_backups
        backups = []
        for f in os.listdir(backup_dir):
            if f.startswith(filename + '.'):
                backups.append(os.path.join(backup_dir, f))

        if len(backups) > max_backups:
            backups.sort()
            for old_backup in backups[:-max_backups]:
                os.remove(old_backup)
                logging.info(f"Removed old backup: {old_backup}")

        return True

    @staticmethod
    def multi_network_archive(json_file_path: str, active_proposals: Dict[str, List[str]], archive_filename: str):
        """
        Archive and remove proposals that are no longer active across multiple networks.

        Args:
            json_file_path: Path to vote_counts.json
            active_proposals: Dict mapping network_id to list of active proposal indexes
            archive_filename: Path to archive file

        Returns:
            List of thread IDs to lock
        """
        threads_to_lock = []

        try:
            # Load vote counts
            with open(json_file_path, 'r') as file:
                vote_counts = json.load(file)

            # Load archive
            try:
                with open(archive_filename, 'r') as archive_file:
                    archived_votes = json.load(archive_file)
            except (FileNotFoundError, json.JSONDecodeError):
                archived_votes = {}

            # Process each network
            for network_id in list(vote_counts.keys()):
                # Initialize network in archive if needed
                if network_id not in archived_votes:
                    archived_votes[network_id] = {}

                # Skip if network not in active_proposals since might be disabled
                if network_id not in active_proposals:
                    continue

                # Get active proposals for this network
                network_active = active_proposals[network_id]

                # Check each referendum in network
                for ref_index in list(vote_counts[network_id].keys()):
                    # If referendum not active then archive it
                    if ref_index not in network_active:
                        # Get thread ID before moving
                        if 'thread_id' in vote_counts[network_id][ref_index]:
                            threads_to_lock.append(vote_counts[network_id][ref_index]['thread_id'])

                        # Move to archive
                        archived_votes[network_id][ref_index] = vote_counts[network_id][ref_index]
                        del vote_counts[network_id][ref_index]
                        logging.info(f"Archived {network_id} referendum {ref_index}")

            # Save updated files
            with open(json_file_path, 'w') as file:
                json.dump(vote_counts, file, indent=4)

            with open(archive_filename, 'w') as archive_file:
                json.dump(archived_votes, archive_file, indent=4)

            return threads_to_lock
        except Exception as e:
            logging.error(f"Error in multi_network_archive: {e}")
            return []

    @staticmethod
    def delete_executed_keys_and_archive(json_file_path: str, active_proposals: List[str], archive_filename: str):
        """
        Original single-network archive method.
        Kept for backward compatibility.
        """
        threads_to_lock = []

        try:
            # Load vote counts and archive
            with open(json_file_path, 'r') as file:
                vote_counts = json.load(file)

            try:
                with open(archive_filename, 'r') as archive_file:
                    archived_votes = json.load(archive_file)
            except (FileNotFoundError, json.JSONDecodeError):
                archived_votes = {}

            # Create a temporary single-network structure for backward compatibility
            temp_active_proposals = {
                "default_network": active_proposals
            }

            # Call multi-network version with temp structure
            return CacheManager.multi_network_archive(
                json_file_path,
                temp_active_proposals,
                archive_filename
            )
        except Exception as e:
            logging.error(f"Error in delete_executed_keys_and_archive: {e}")
            return []
