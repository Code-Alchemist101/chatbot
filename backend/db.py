import os
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "skytrade_chat"
COLLECTION_NAME = "chat_history"

class Database:
    def __init__(self):
        if not MONGO_URI:
            print("Warning: MONGO_URI not found in environment variables.")
            self.client = None
            self.db = None
            self.collection = None
        else:
            try:
                self.client = MongoClient(MONGO_URI)
                self.db = self.client[DB_NAME]
                self.collection = self.db[COLLECTION_NAME]
                print("Connected to MongoDB.")
            except Exception as e:
                print(f"Error connecting to MongoDB: {e}")
                self.client = None
                self.db = None
                self.collection = None

    def save_message(self, session_id, role, content):
        if self.collection is not None:
            message = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow()
            }
            self.collection.insert_one(message)

    def get_history(self, session_id):
        if self.collection is not None:
            return list(self.collection.find({"session_id": session_id}, {"_id": 0}).sort("timestamp", 1))
        return []

db = Database()
