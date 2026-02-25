#!/usr/bin/env python3
import os
import sys

# Add the parent directory to sys.path to allow imports from the backend
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import clear_database

def main():
    """
    CLI utility for performing a complete reset of the assessment database.

    Drops all existing tables and recreates the schema to provide a clean 
    workspace for new evaluation sessions.
    """
    print("WARNING: This will permanently delete all session data, events, and files.")
    confirm = input("Are you sure you want to reset the database? (y/N): ")
    if confirm.lower() == 'y':
        try:
            clear_database()
            print("Database reset successfully.")
        except Exception as e:
            print(f"Error resetting database: {e}")
    else:
        print("Reset cancelled.")

if __name__ == "__main__":
    main()
