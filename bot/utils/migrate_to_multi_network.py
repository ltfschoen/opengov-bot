#!/usr/bin/env python3
"""
Migration script to convert single-network vote counts to multi-network format.

This script takes existing vote_counts.json and archived_votes.json files
and converts them to the new multi-network format, where votes are organized
by network ID.
"""

import os
import json
import argparse
import shutil
from datetime import datetime


def backup_file(file_path):
    """Create a backup of a file with timestamp."""
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist. No backup created.")
        return False

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{file_path}.{timestamp}.bak"

    try:
        shutil.copy2(file_path, backup_path)
        print(f"Created backup at {backup_path}")
        return True
    except Exception as e:
        print(f"Error creating backup: {e}")
        return False


def migrate_vote_counts(vote_counts_path, network_id="polkadot"):
    """
    Migrate vote_counts.json from single-network format to multi-network format.

    Args:
        vote_counts_path: Path to vote_counts.json
        network_id: Network ID to assign to existing votes

    Returns:
        True if migration successful, False otherwise
    """
    # Check if file exists
    if not os.path.exists(vote_counts_path):
        print(f"Vote counts file {vote_counts_path} does not exist.")
        return False

    try:
        # Create backup
        if not backup_file(vote_counts_path):
            return False

        # Load existing data
        with open(vote_counts_path, 'r') as file:
            try:
                vote_counts = json.load(file)
            except json.JSONDecodeError:
                print("Error: vote_counts.json is not valid JSON.")
                return False

        # Check if already migrated (has network IDs)
        if network_id in vote_counts:
            print("Vote counts file appears to already be in multi-network format.")
            return True

        # Convert to multi-network format
        new_vote_counts = {network_id: vote_counts}

        # Write back to file
        with open(vote_counts_path, 'w') as file:
            json.dump(new_vote_counts, file, indent=4)

        print(f"Successfully migrated {vote_counts_path} to multi-network format under '{network_id}' network.")
        return True
    except Exception as e:
        print(f"Error migrating vote counts: {e}")
        return False


def migrate_archived_votes(archived_votes_path, network_id="polkadot"):
    """
    Migrate archived_votes.json from single-network format to multi-network format.

    Args:
        archived_votes_path: Path to archived_votes.json
        network_id: Network ID to assign to existing archived votes

    Returns:
        True if migration successful, False otherwise
    """
    # Check if file exists - it's fine if it doesn't
    if not os.path.exists(archived_votes_path):
        print(f"Archived votes file {archived_votes_path} does not exist. Creating new file.")
        with open(archived_votes_path, 'w') as file:
            json.dump({network_id: {}}, file, indent=4)
        return True

    try:
        # Create backup
        if os.path.exists(archived_votes_path):
            if not backup_file(archived_votes_path):
                return False

        # Load existing data
        with open(archived_votes_path, 'r') as file:
            try:
                archived_votes = json.load(file)
            except json.JSONDecodeError:
                print("Error: archived_votes.json is not valid JSON.")
                return False

        # Check if already migrated (has network IDs)
        if network_id in archived_votes:
            print("Archived votes file appears to already be in multi-network format.")
            return True

        # Convert to multi-network format
        new_archived_votes = {network_id: archived_votes}

        # Write back to file
        with open(archived_votes_path, 'w') as file:
            json.dump(new_archived_votes, file, indent=4)

        print(f"Successfully migrated {archived_votes_path} to multi-network format under '{network_id}' network.")
        return True
    except Exception as e:
        print(f"Error migrating archived votes: {e}")
        return False


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description='Migrate vote data to multi-network format')
    parser.add_argument('--votes-path', default='../data/vote_counts.json',
                       help='Path to vote_counts.json (default: ../data/vote_counts.json)')
    parser.add_argument('--archive-path', default='../data/archived_votes.json',
                       help='Path to archived_votes.json (default: ../data/archived_votes.json)')
    parser.add_argument('--network-id', default='polkadot',
                       help='Network ID to assign to existing votes (default: polkadot)')

    args = parser.parse_args()

    print(f"Starting migration of vote data to multi-network format under '{args.network_id}' network...")

    vote_success = migrate_vote_counts(args.votes_path, args.network_id)
    archive_success = migrate_archived_votes(args.archive_path, args.network_id)

    if vote_success and archive_success:
        print("\n✅ Migration completed successfully!")
        print("\nNext Steps:")
        print("1. Create a networks.json file in the data directory")
        print("2. Switch to using main_multi_network.py instead of main.py")
        print("3. Add additional networks using the /network add command in Discord")
    else:
        print("\n❌ Migration failed. Please check the errors above.")


if __name__ == '__main__':
    main()
