#!/usr/bin/env python3
"""
OpenGov Bot PostgreSQL Database Viewer
-------------------------------------
This script allows you to view and explore vote data stored in the PostgreSQL database.
It provides several query options to examine referendum threads, user votes, and statistics.
"""
import psycopg2
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import argparse

def load_env():
    """Load environment variables from .env file"""
    # Try to load from different locations
    if os.path.exists(".env"):
        load_dotenv(".env")
    elif os.path.exists("../.env"):
        load_dotenv("../.env")
    elif os.path.exists("../../.env"):
        load_dotenv("../../.env")

def get_db_params():
    """Get database connection parameters from environment or use defaults"""
    return {
        'dbname': os.getenv('DB_NAME', 'opengov_bot'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', ''),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432')
    }

def connect_to_db():
    """Connect to PostgreSQL database"""
    db_params = get_db_params()
    try:
        conn = psycopg2.connect(**db_params)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def format_timestamp(epoch):
    """Convert epoch timestamp to human-readable date"""
    if epoch:
        return datetime.fromtimestamp(epoch).strftime('%Y-%m-%d %H:%M:%S')
    return "N/A"

def list_threads(conn, show_archived=False):
    """List all referendum threads"""
    cursor = conn.cursor()

    query = """
        SELECT thread_id, aye, nay, recuse, abstain, epoch, archived
        FROM referenda_thread
    """

    if not show_archived:
        query += " WHERE archived = FALSE"

    cursor.execute(query)
    threads = cursor.fetchall()

    print("\n== Referendum Threads ==")
    if not threads:
        print("No threads found.")
        return

    for thread in threads:
        print(f"Thread ID: {thread[0]}")
        print(f"Votes: Aye={thread[1]}, Nay={thread[2]}, Recuse={thread[3]}, Abstain={thread[4] or 0}")
        print(f"Date: {format_timestamp(thread[5])}")
        print(f"Archived: {thread[6]}")
        print("---")

    cursor.close()

def view_thread_votes(conn, thread_id):
    """View all votes for a specific thread"""
    cursor = conn.cursor()

    # First check if thread exists
    cursor.execute("SELECT 1 FROM referenda_thread WHERE thread_id = %s", (thread_id,))
    if not cursor.fetchone():
        print(f"No thread found with ID: {thread_id}")
        cursor.close()
        return

    # Get thread info
    cursor.execute("""
        SELECT thread_id, aye, nay, recuse, abstain, epoch, archived
        FROM referenda_thread
        WHERE thread_id = %s
    """, (thread_id,))
    thread = cursor.fetchone()

    print(f"\n== Thread {thread_id} ==")
    print(f"Votes: Aye={thread[1]}, Nay={thread[2]}, Recuse={thread[3]}, Abstain={thread[4] or 0}")
    print(f"Date: {format_timestamp(thread[5])}")
    print(f"Archived: {thread[6]}")

    # Get votes for this thread
    cursor.execute("""
        SELECT u.username, vo.description
        FROM users u
        JOIN vote_options vo ON u.vote_type = vo.vote_id
        WHERE u.thread_id = %s
        ORDER BY vo.description, u.username;
    """, (thread_id,))
    votes = cursor.fetchall()

    print("\n-- Individual Votes --")
    if votes:
        for vote in votes:
            print(f"User: {vote[0]}, Vote: {vote[1]}")
    else:
        print("No individual votes recorded for this thread.")

    cursor.close()

def vote_summary(conn):
    """Show vote summary across all threads"""
    cursor = conn.cursor()

    print("\n== Vote Summary ==")

    # Count votes by type
    cursor.execute("""
        SELECT vo.description, COUNT(*)
        FROM users u
        JOIN vote_options vo ON u.vote_type = vo.vote_id
        GROUP BY vo.description
        ORDER BY COUNT(*) DESC;
    """)
    vote_counts = cursor.fetchall()

    if vote_counts:
        for vote_type in vote_counts:
            print(f"{vote_type[0]}: {vote_type[1]}")
    else:
        print("No votes recorded.")

    # Count active and archived threads
    cursor.execute("""
        SELECT archived, COUNT(*)
        FROM referenda_thread
        GROUP BY archived;
    """)
    thread_counts = cursor.fetchall()

    print("\n-- Thread Statistics --")
    active = next((count for status, count in thread_counts if status is False), 0)
    archived = next((count for status, count in thread_counts if status is True), 0)
    print(f"Active threads: {active}")
    print(f"Archived threads: {archived}")
    print(f"Total threads: {active + archived}")

    cursor.close()

def check_tables(conn):
    """Check if required database tables exist"""
    cursor = conn.cursor()

    # Check for all expected tables
    tables = ['referenda_thread', 'users', 'vote_options']
    missing_tables = []

    for table in tables:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename = %s
            );
        """, (table,))

        if not cursor.fetchone()[0]:
            missing_tables.append(table)

    if missing_tables:
        print(f"Warning: Missing tables: {', '.join(missing_tables)}")
        print("Database schema may not be initialized correctly.")

    cursor.close()
    return len(missing_tables) == 0

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="OpenGov Bot PostgreSQL Database Viewer")
    parser.add_argument("-a", "--all", action="store_true", help="Show all threads including archived")
    parser.add_argument("-t", "--thread", help="View votes for a specific thread ID")
    parser.add_argument("-s", "--summary", action="store_true", help="Show vote summary statistics")
    args = parser.parse_args()

    load_env()
    conn = connect_to_db()

    # Check if tables exist
    if not check_tables(conn):
        print("Please ensure the database is properly initialized.")
        conn.close()
        return

    if args.thread:
        view_thread_votes(conn, args.thread)
    elif args.summary:
        vote_summary(conn)
    else:
        list_threads(conn, args.all)

        # In interactive mode, allow viewing specific threads
        if not sys.argv[1:]:  # No command line args provided
            while True:
                thread_id = input("\nEnter thread ID to view details (or press Enter to quit): ").strip()
                if not thread_id:
                    break
                view_thread_votes(conn, thread_id)

    conn.close()

if __name__ == "__main__":
    # If no args provided, show help message first
    if len(sys.argv) == 1:
        print(__doc__)
        print("Running in interactive mode. Use -h for command-line options.")
    main()
