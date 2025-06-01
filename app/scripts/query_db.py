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


def remove_duplicate_workouts(user_id=None, dry_run=True, use_alternative_ids=True):
    """
    Remove duplicate workouts from the database.

    Duplicates are identified by having the same Hevy ID. When duplicates are found,
    the oldest one is kept and the others are deleted.

    Args:
        user_id: Optional user ID to filter workouts by
        dry_run: If True, only report duplicates without removing them
        use_alternative_ids: If True, try to identify duplicates using alternative fields
                           when Hevy ID is not available
    """
    db = connect_to_db()
    workouts = []
    total_duplicates = 0  # Initialize the counter at the beginning

    try:
        # Get all workouts
        if user_id:
            print(f"Finding workouts for user ID: {user_id}")
            # Try to use the view first
            try:
                results = db.view("workouts/by_user", key=user_id, include_docs=True)
                all_workouts = [row.doc for row in results]
                print(f"Found {len(all_workouts)} workouts using view")

                # If no workouts found, try the fallback
                if len(all_workouts) == 0:
                    print(
                        "No workouts found using view, falling back to direct query..."
                    )
                    # Fall back to direct query
                    all_docs = db.view("_all_docs", include_docs=True)
                    all_workouts = [
                        row.doc
                        for row in all_docs
                        if row.doc.get("type") == "workout"
                        and row.doc.get("user_id") == user_id
                    ]
                    print(f"Found {len(all_workouts)} workouts using direct query")
            except Exception as e:
                print(f"Error using view: {str(e)}")
                print("Falling back to direct query...")
                # Fall back to direct query
                all_docs = db.view("_all_docs", include_docs=True)
                all_workouts = [
                    row.doc
                    for row in all_docs
                    if row.doc.get("type") == "workout"
                    and row.doc.get("user_id") == user_id
                ]
                print(f"Found {len(all_workouts)} workouts using direct query")
        else:
            print("Finding all workouts")
            # Try to use the view first
            try:
                results = db.view("workouts/by_date", include_docs=True)
                all_workouts = [row.doc for row in results]
                print(f"Found {len(all_workouts)} workouts using view")

                # If no workouts found, try the fallback
                if len(all_workouts) == 0:
                    print(
                        "No workouts found using view, falling back to direct query..."
                    )
                    # Fall back to direct query
                    all_docs = db.view("_all_docs", include_docs=True)
                    all_workouts = [
                        row.doc for row in all_docs if row.doc.get("type") == "workout"
                    ]
                    print(f"Found {len(all_workouts)} workouts using direct query")
            except Exception as e:
                print(f"Error using view: {str(e)}")
                print("Falling back to direct query...")
                # Fall back to direct query
                all_docs = db.view("_all_docs", include_docs=True)
                all_workouts = [
                    row.doc for row in all_docs if row.doc.get("type") == "workout"
                ]
                print(f"Found {len(all_workouts)} workouts using direct query")

        # Count total workouts
        print(f"Total workouts found: {len(all_workouts)}")

        # Group workouts by Hevy ID
        workouts_by_hevy_id = {}
        workouts_without_hevy_id = []

        for workout in all_workouts:
            hevy_id = workout.get("hevy_id")

            if not hevy_id:
                workouts_without_hevy_id.append(workout)
                continue

            if hevy_id in workouts_by_hevy_id:
                workouts_by_hevy_id[hevy_id].append(workout)
            else:
                workouts_by_hevy_id[hevy_id] = [workout]

        print(f"Workouts with Hevy ID: {len(workouts_by_hevy_id)}")
        print(f"Workouts without Hevy ID: {len(workouts_without_hevy_id)}")

        # Simple check for workouts with the same title, user ID, and start time
        print("\nChecking for workouts with the same title, user ID, and start time...")
        title_user_time_groups = {}

        for workout in all_workouts:
            title = workout.get("title")
            user_id = workout.get("user_id")
            start_time = workout.get("start_time")

            if title and user_id and start_time:
                key = (title, user_id, start_time)
                if key in title_user_time_groups:
                    title_user_time_groups[key].append(workout)
                else:
                    title_user_time_groups[key] = [workout]

        # Find groups with more than one workout
        duplicate_groups = {
            k: v for k, v in title_user_time_groups.items() if len(v) > 1
        }

        if duplicate_groups:
            print(
                f"Found {len(duplicate_groups)} groups with the same title, user ID, and start time:"
            )
            for (title, user_id, start_time), workouts in duplicate_groups.items():
                print(f"  Title: {title}")
                print(f"  User ID: {user_id}")
                print(f"  Start Time: {start_time}")
                print(f"  Contains {len(workouts)} workouts:")
                for i, workout in enumerate(workouts):
                    print(
                        f"    {i+1}. ID: {workout.get('_id')}, Created: {workout.get('created_at')}"
                    )
        else:
            print("No workouts found with the same title, user ID, and start time.")

        # Report workouts without Hevy IDs
        if workouts_without_hevy_id:
            print(f"\nFound {len(workouts_without_hevy_id)} workouts without Hevy IDs:")
            for workout in workouts_without_hevy_id:
                print(f"  ID: {workout.get('_id', 'Unknown')}")
                print(f"  Title: {workout.get('title', 'Untitled')}")
                print(f"  User ID: {workout.get('user_id', 'Unknown')}")
                print(f"  Start Time: {workout.get('start_time', 'Unknown')}")
                print(f"  Created At: {workout.get('created_at', 'Unknown')}")
                print("")

        # Find duplicates by Hevy ID
        duplicates = {
            hevy_id: workouts
            for hevy_id, workouts in workouts_by_hevy_id.items()
            if len(workouts) > 1
        }

        if duplicates:
            print(f"Found {len(duplicates)} Hevy IDs with duplicate workouts.")

            # Process duplicates
            for hevy_id, workouts in duplicates.items():
                print(f"\nHevy ID: {hevy_id}")
                print(f"Found {len(workouts)} duplicate workouts:")

                # Sort by creation date (oldest first)
                workouts.sort(key=lambda w: w.get("created_at", ""))

                # Keep the oldest workout
                keep_workout = workouts[0]
                print(
                    f"  Keeping: {keep_workout.get('_id')} (created: {keep_workout.get('created_at', 'Unknown')})"
                )

                # Delete the rest
                for workout in workouts[1:]:
                    print(
                        f"  Deleting: {workout.get('_id')} (created: {workout.get('created_at', 'Unknown')})"
                    )
                    if not dry_run:
                        db.delete(workout)
                    total_duplicates += 1
        else:
            print("No duplicate workouts found by Hevy ID.")

        # Try to identify duplicates using alternative fields if requested
        if use_alternative_ids and workouts_without_hevy_id:
            print("\nTrying to identify duplicates using alternative fields...")
            print(
                f"Found {len(workouts_without_hevy_id)} workouts without Hevy IDs to analyze"
            )

            # Group workouts by user_id, title, and start_time
            workouts_by_user_title_and_time = {}
            skipped_workouts = 0

            for workout in workouts_without_hevy_id:
                user_id = workout.get("user_id")
                title = workout.get("title")
                start_time = workout.get("start_time")

                if not user_id or not start_time:
                    skipped_workouts += 1
                    continue

                # Use a more specific key that includes the title
                key = (user_id, title, start_time)
                if key in workouts_by_user_title_and_time:
                    workouts_by_user_title_and_time[key].append(workout)
                else:
                    workouts_by_user_title_and_time[key] = [workout]

            print(
                f"Grouped workouts into {len(workouts_by_user_title_and_time)} unique groups"
            )
            print(
                f"Skipped {skipped_workouts} workouts due to missing user_id or start_time"
            )

            # Debug: Print all groups with more than one workout
            groups_with_duplicates = {
                k: v for k, v in workouts_by_user_title_and_time.items() if len(v) > 1
            }
            if groups_with_duplicates:
                print(
                    f"\nFound {len(groups_with_duplicates)} groups with potential duplicates:"
                )
                for (
                    user_id,
                    title,
                    start_time,
                ), workouts in groups_with_duplicates.items():
                    print(
                        f"  Group: User ID: {user_id}, Title: {title}, Start Time: {start_time}"
                    )
                    print(f"  Contains {len(workouts)} workouts:")
                    for i, workout in enumerate(workouts):
                        print(
                            f"    {i+1}. ID: {workout.get('_id')}, Created: {workout.get('created_at')}"
                        )
            else:
                print(
                    "\nNo groups with multiple workouts found. Checking individual fields..."
                )

                # Debug: Check if there are any workouts with the same title
                titles = {}
                for workout in workouts_without_hevy_id:
                    title = workout.get("title")
                    if title:
                        if title in titles:
                            titles[title].append(workout)
                        else:
                            titles[title] = [workout]

                duplicate_titles = {
                    title: workouts
                    for title, workouts in titles.items()
                    if len(workouts) > 1
                }
                if duplicate_titles:
                    print(
                        f"\nFound {len(duplicate_titles)} titles with multiple workouts:"
                    )
                    for title, workouts in duplicate_titles.items():
                        print(f"  Title: {title}")
                        print(f"  Contains {len(workouts)} workouts:")
                        for i, workout in enumerate(workouts):
                            print(
                                f"    {i+1}. ID: {workout.get('_id')}, User ID: {workout.get('user_id')}, Start Time: {workout.get('start_time')}"
                            )

            # Find potential duplicates
            potential_duplicates = {
                key: workouts
                for key, workouts in workouts_by_user_title_and_time.items()
                if len(workouts) > 1
            }

            if potential_duplicates:
                print(
                    f"Found {len(potential_duplicates)} potential duplicate groups using user_id, title, and start_time."
                )

                # Process potential duplicates
                alt_duplicates = 0
                for (
                    user_id,
                    title,
                    start_time,
                ), workouts in potential_duplicates.items():
                    print(
                        f"\nUser ID: {user_id}, Title: {title}, Start Time: {start_time}"
                    )
                    print(f"Found {len(workouts)} potential duplicate workouts:")

                    # Sort by creation date (oldest first)
                    workouts.sort(key=lambda w: w.get("created_at", ""))

                    # Keep the oldest workout
                    keep_workout = workouts[0]
                    print(
                        f"  Keeping: {keep_workout.get('_id')} (created: {keep_workout.get('created_at', 'Unknown')})"
                    )
                    print(f"  Title: {keep_workout.get('title', 'Untitled')}")

                    # Delete the rest
                    for workout in workouts[1:]:
                        print(
                            f"  Deleting: {workout.get('_id')} (created: {workout.get('created_at', 'Unknown')})"
                        )
                        print(f"  Title: {workout.get('title', 'Untitled')}")
                        if not dry_run:
                            db.delete(workout)
                        alt_duplicates += 1

                if alt_duplicates > 0:
                    total_duplicates += alt_duplicates
                    print(
                        f"\nFound {alt_duplicates} additional potential duplicates using alternative fields."
                    )
            else:
                print("No potential duplicates found using alternative fields.")

        if dry_run:
            print(
                f"\nDRY RUN: Would have deleted {total_duplicates} duplicate workouts."
            )
            print("Run with dry_run=False to actually delete the duplicates.")
        else:
            print(f"\nSuccessfully deleted {total_duplicates} duplicate workouts.")

    except Exception as e:
        print(f"Error removing duplicate workouts: {str(e)}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")


def analyze_workout_structure(user_id=None, sample_size=5):
    """
    Analyze the structure of workouts in the database to help identify issues.

    Args:
        user_id: Optional user ID to filter workouts by
        sample_size: Number of workouts to analyze in detail
    """
    db = connect_to_db()

    try:
        # Get workouts
        if user_id:
            print(f"Analyzing workouts for user ID: {user_id}")
            results = db.view("workouts/by_user", key=user_id, include_docs=True)
        else:
            print("Analyzing all workouts")
            results = db.view("workouts/by_date", include_docs=True)

        # Count workouts with and without Hevy IDs
        workouts_with_hevy_id = 0
        workouts_without_hevy_id = 0
        all_workouts = []

        for row in results:
            workout = row.doc
            all_workouts.append(workout)

            if workout.get("hevy_id"):
                workouts_with_hevy_id += 1
            else:
                workouts_without_hevy_id += 1

        total_workouts = len(all_workouts)
        print(f"\nTotal workouts: {total_workouts}")
        print(
            f"Workouts with Hevy ID: {workouts_with_hevy_id} ({workouts_with_hevy_id/total_workouts*100:.1f}%)"
        )
        print(
            f"Workouts without Hevy ID: {workouts_without_hevy_id} ({workouts_without_hevy_id/total_workouts*100:.1f}%)"
        )

        # Analyze sample workouts in detail
        print("\nAnalyzing sample workouts in detail:")
        sample_workouts = all_workouts[:sample_size]

        for i, workout in enumerate(sample_workouts):
            print(f"\nWorkout {i+1}:")
            print(f"  ID: {workout.get('_id', 'Unknown')}")
            print(f"  Title: {workout.get('title', 'Untitled')}")
            print(f"  User ID: {workout.get('user_id', 'Unknown')}")
            print(f"  Hevy ID: {workout.get('hevy_id', 'None')}")
            print(f"  Start Time: {workout.get('start_time', 'Unknown')}")
            print(f"  End Time: {workout.get('end_time', 'Unknown')}")
            print(f"  Created At: {workout.get('created_at', 'Unknown')}")
            print(f"  Updated At: {workout.get('updated_at', 'Unknown')}")
            print(f"  Last Synced: {workout.get('last_synced', 'Unknown')}")
            print(f"  Exercise Count: {workout.get('exercise_count', 0)}")

            # Check for potential duplicate identifiers
            print("  Potential identifiers:")
            for key in workout.keys():
                if key in [
                    "_id",
                    "_rev",
                    "type",
                    "user_id",
                    "hevy_id",
                    "title",
                    "start_time",
                    "end_time",
                    "created_at",
                    "updated_at",
                    "last_synced",
                    "exercise_count",
                    "exercises",
                ]:
                    continue
                print(f"    {key}: {workout.get(key)}")

        # Check for potential alternative ID fields
        print("\nChecking for potential alternative ID fields:")
        id_fields = set()
        for workout in all_workouts:
            for key in workout.keys():
                if "id" in key.lower() and key not in ["_id", "user_id", "hevy_id"]:
                    id_fields.add(key)

        if id_fields:
            print(f"Found potential ID fields: {', '.join(id_fields)}")

            # Count workouts with these fields
            for field in id_fields:
                count = sum(1 for w in all_workouts if w.get(field))
                print(f"  {field}: {count} workouts ({count/total_workouts*100:.1f}%)")
        else:
            print("No alternative ID fields found.")

    except Exception as e:
        print(f"Error analyzing workout structure: {str(e)}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")


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
        print(
            "  remove_duplicates [user_id] [dry_run] [use_alternative_ids] - Remove duplicate workouts"
        )
        print("  analyze_workouts [user_id] [sample_size] - Analyze workout structure")
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
    elif command == "remove_duplicates":
        user_id = sys.argv[2] if len(sys.argv) > 2 else None
        dry_run = len(sys.argv) > 3 and sys.argv[3].lower() == "true"
        use_alternative_ids = len(sys.argv) > 4 and sys.argv[4].lower() == "true"
        remove_duplicate_workouts(user_id, dry_run, use_alternative_ids)
    elif command == "analyze_workouts":
        user_id = sys.argv[2] if len(sys.argv) > 2 else None
        sample_size = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        analyze_workout_structure(user_id, sample_size)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
