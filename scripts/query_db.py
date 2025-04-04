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
    username = os.getenv("COUCHDB_USERNAME")
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
    """Find all user profile documents."""
    db = connect_to_db()

    print(f"Database name: {db.name}")
    print(f"Database info: {db.info()}")

    # Using Mango query for better filtering
    selector = {
        "selector": {"type": {"$eq": "user_profile"}},
        "use_index": ["type-index"],
    }

    try:
        print(f"Executing query: {selector}")
        results = list(db.find(selector))
        print(f"Query returned {len(results)} results")

        if not results:
            print("No user profiles found in the database.")
            return

        for doc in results:
            print(f"\nUser Profile:")
            print(f"Username: {doc.get('username', 'N/A')}")
            print(f"Email: {doc.get('email', 'N/A')}")
            print(f"Created: {doc.get('created_at', 'N/A')}")
            if doc.get("injuries"):
                print(f"Number of injuries: {len(doc['injuries'])}")
            print("-" * 50)

    except Exception as e:
        print(f"Error querying users: {str(e)}")
        print("You may need to create an index first. Creating index...")
        try:
            # Create an index on the type field
            db.create_index(["type"], name="type-index")
            print("Index created. Please try the query again.")
        except Exception as e:
            print(f"Error creating index: {str(e)}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python query_db.py list         - List regular documents")
        print(
            "  python query_db.py list --all   - List all documents including design docs"
        )
        print("  python query_db.py users        - List all user profiles")
        print("  python query_db.py get <id>     - Get specific document")
        return

    command = sys.argv[1]

    if command == "list":
        include_design = len(sys.argv) > 2 and sys.argv[2] == "--all"
        list_all_docs(include_design)
    elif command == "users":
        find_users()
    elif command == "get" and len(sys.argv) > 2:
        get_doc(sys.argv[2])
    else:
        print("Invalid command")


if __name__ == "__main__":
    main()
