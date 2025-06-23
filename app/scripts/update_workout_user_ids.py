import couchdb

COUCHDB_URL = "http://localhost:5984"
COUCHDB_USER = "ai_trainer_admin"
COUCHDB_PASSWORD = "dev_KTq29pZuEi1VsoNqf2mJMPTg"
COUCHDB_HOST = "couchdb"
COUCHDB_DB = "ai_trainer"
COUCHDB_PORT = "5984"
# The correct user doc _id (get this from your user profile)
CORRECT_USER_ID = "82f3c49a7beaaa7430f25b035a0009ae"

server = couchdb.Server(COUCHDB_URL)
server.resource.credentials = (COUCHDB_USER, COUCHDB_PASSWORD)
db = server[COUCHDB_DB]

updated = 0
for row in db.view("workouts/by_date", include_docs=True):
    doc = row.doc
    if doc.get("type") == "workout" and doc.get("user_id") != CORRECT_USER_ID:
        doc["user_id"] = CORRECT_USER_ID
        db.save(doc)
        updated += 1

print(f"Updated {updated} workout docs to user_id {CORRECT_USER_ID}")
