from pymongo import MongoClient, ASCENDING
import json
import os

# Read config.json
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

MONGO_URI = config.get("mongo_uri", "<Azure DocumentDB Connection String>")
DB_NAME = config.get("mongo_db_name", "chat_db")

# Connect to MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    print(f"[MongoDB] Successfully connected to {DB_NAME}")
except Exception as e:
    print(f"[MongoDB] Connection failed: {e}")
    raise

# Collections for V2 schema
users_collection = db["users"]
projects_collection = db["projects"]
conversations_collection = db["conversations"]
messages_collection = db["messages"]

# Create indexes
try:
    # Users indexes
    users_collection.create_index("email", unique=True)
    users_collection.create_index("id", unique=True)

    # Projects indexes
    projects_collection.create_index([("user_id", ASCENDING), ("sort_order", ASCENDING)])
    projects_collection.create_index("id", unique=True)

    # Conversations indexes
    conversations_collection.create_index([("user_id", ASCENDING), ("updated_at", ASCENDING)])
    conversations_collection.create_index([("project_id", ASCENDING)])
    conversations_collection.create_index("id", unique=True)

    # Messages indexes
    messages_collection.create_index([("conversation_id", ASCENDING), ("created_at", ASCENDING)])
    messages_collection.create_index("id", unique=True)

    print("[MongoDB] Indexes created successfully")
except Exception as e:
    print(f"[MongoDB] Index creation warning: {e}")
