#!/usr/bin/env python3
import json
import os
import sys
from urllib.parse import quote_plus

from couchdb import Server
from dotenv import load_dotenv


def connect_to_db():
    """Connect to CouchDB using environment variables."""
    load_dotenv()
    username = os.getenv("COUCHDB_USER")
    password = os.getenv("COUCHDB_PASSWORD")
    host = os.getenv("COUCHDB_HOST", "localhost")
    port = os.getenv("COUCHDB_PORT", "5984")

    if not all([username, password]):
        raise ValueError("Missing CouchDB credentials. Please check your .env file.")

    try:
        # URL encode the username and password
        username = quote_plus(str(username))
        password = quote_plus(str(password))

        server = Server(f"http://{username}:{password}@{host}:{port}")
        return server["ai_personal_trainer"]
    except Exception as e:
        print(f"Error connecting to CouchDB: {str(e)}")
        print("Please check your .env file and CouchDB connection settings.")
        sys.exit(1)


def list_all_docs(include_design_docs=False):
    """List all documents in the database."""
    db = connect_to_db()
    doc_count = 0

    print(f"Database name: {db.name}")
    print(f"Database info: {db.info()}")

    for doc_id in db:
        # Skip design documents unless specifically requested
        if not include_design_docs and doc_id.startswith("_design/"):
            continue

        doc = db[doc_id]
        doc_count += 1
        print(f"\nDocument ID: {doc_id}")
        print(f"Type: {doc.get('type', 'N/A')}")
        if doc.get("type") == "user_profile":
            print(f"Username: {doc.get('username', 'N/A')}")
            print(f"Email: {doc.get('email', 'N/A')}")
        print("-" * 50)

    if doc_count == 0:
        if include_design_docs:
            print("No documents found in the database.")
        else:
            print("No regular documents found. Use --all to include design documents.")


def get_doc(doc_id):
    """Get a specific document by ID."""
    db = connect_to_db()
    try:
        doc = db[doc_id]
        print(json.dumps(doc, indent=2))
    except Exception as e:
        print(f"Error: {str(e)}")


def find_users():
    """Find all user documents in the database."""
    db = connect_to_db()
    users = []

    try:
        # Query the users view
        results = db.view("users/by_username", include_docs=True)
        for row in results:
            users.append(row.doc)
            print(f"User: {row.doc.get('username', 'Unknown')}")
            print(f"  ID: {row.doc.get('_id', 'Unknown')}")
            print(f"  Email: {row.doc.get('email', 'Unknown')}")
            print(f"  Created: {row.doc.get('created_at', 'Unknown')}")
            print(f"  Last Login: {row.doc.get('last_login', 'Unknown')}")
            print("")

        return users
    except Exception as e:
        print(f"Error finding users: {str(e)}")
        return []


def find_workouts(user_id=None, include_details=False):
    """
    Find all workout documents in the database.

    Args:
        user_id: Optional user ID to filter workouts by
        include_details: Whether to include full workout details
    """
    db = connect_to_db()
    workouts = []

    try:
        if user_id:
            # Query the workouts by user view
            print(f"Finding workouts for user ID: {user_id}")
            results = db.view("workouts/by_user", key=user_id, include_docs=True)
        else:
            # Query all workouts
            print("Finding all workouts")
            results = db.view("workouts/by_date", include_docs=True)

        for row in results:
            workout = row.doc
            workouts.append(workout)

            # Print basic workout info
            print(f"Workout: {workout.get('title', 'Untitled')}")
            print(f"  ID: {workout.get('_id', 'Unknown')}")
            print(f"  User ID: {workout.get('user_id', 'Unknown')}")
            print(f"  Start Time: {workout.get('start_time', 'Unknown')}")
            print(f"  End Time: {workout.get('end_time', 'Unknown')}")
            print(f"  Exercise Count: {workout.get('exercise_count', 0)}")

            # Print more details if requested
            if include_details:
                print(f"  Description: {workout.get('description', 'No description')}")
                print(f"  Created At: {workout.get('created_at', 'Unknown')}")
                print(f"  Updated At: {workout.get('updated_at', 'Unknown')}")
                print(f"  Last Synced: {workout.get('last_synced', 'Unknown')}")

                # Print exercises
                print("  Exercises:")
                for i, exercise in enumerate(workout.get("exercises", [])):
                    print(f"    {i+1}. {exercise.get('name', 'Unknown')}")
                    print(f"       Sets: {len(exercise.get('sets', []))}")

            print("")

        print(f"Found {len(workouts)} workouts")
        return workouts
    except Exception as e:
        print(f"Error finding workouts: {str(e)}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        return []


def main():
    """Main function to run the script."""
    if len(sys.argv) < 2:
        print("Usage: python query_db.py <command> [args]")
        print("Commands:")
        print("  list_docs [include_design_docs] - List all documents")
        print("  get_doc <doc_id> - Get a specific document")
        print("  find_users - Find all user documents")
        print(
            "  find_workouts [user_id] [include_details] - Find all workout documents"
        )
        sys.exit(1)

    command = sys.argv[1]

    if command == "list_docs":
        include_design_docs = len(sys.argv) > 2 and sys.argv[2].lower() == "true"
        list_all_docs(include_design_docs)
    elif command == "get_doc":
        if len(sys.argv) < 3:
            print("Error: Missing document ID")
            sys.exit(1)
        doc_id = sys.argv[2]
        get_doc(doc_id)
    elif command == "find_users":
        find_users()
    elif command == "find_workouts":
        user_id = sys.argv[2] if len(sys.argv) > 2 else None
        include_details = len(sys.argv) > 3 and sys.argv[3].lower() == "true"
        find_workouts(user_id, include_details)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
