from pymongo import MongoClient
import json
import os

# 读取config.json
CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.json')
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
	config = json.load(f)

MONGO_URI = config.get("mongo_uri", "<Azure DocumentDB Connection String>")
DB_NAME = config.get("mongo_db_name", "chat_db")
COLLECTION_NAME = config.get("mongo_collection_name", "chat_history")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
chat_collection = db[COLLECTION_NAME]
