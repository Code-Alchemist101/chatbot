import os
from pymongo import MongoClient, ASCENDING
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "klbot_chat"
COLLECTION_NAME = "chat_history"

class Database:
    def __init__(self):
        if not MONGO_URI:
            print("Warning: MONGO_URI not found. Chat history will not be saved.")
            self.client = None
            self.db = None
            self.collection = None
        else:
            try:
                self.client = MongoClient(
                    MONGO_URI,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=10000
                )
                
                # Test connection
                self.client.admin.command('ping')
                
                self.db = self.client[DB_NAME]
                self.collection = self.db[COLLECTION_NAME]
                
                # Create indexes for better performance
                self._create_indexes()
                
                print("✓ Connected to MongoDB successfully")
            except Exception as e:
                print(f"✗ Error connecting to MongoDB: {e}")
                print("  Chat history will not be saved")
                self.client = None
                self.db = None
                self.collection = None

    def _create_indexes(self):
        """Create indexes for optimized queries"""
        if self.collection is not None:
            try:
                # Index on session_id for faster queries
                self.collection.create_index([("session_id", ASCENDING)])
                
                # Index on timestamp for sorting
                self.collection.create_index([("timestamp", ASCENDING)])
                
                # Compound index for session queries
                self.collection.create_index([
                    ("session_id", ASCENDING),
                    ("timestamp", ASCENDING)
                ])
                
                print("✓ Database indexes created")
            except Exception as e:
                print(f"⚠️  Warning: Could not create indexes: {e}")

    def save_message(self, session_id, role, content):
        """Save a message to the database"""
        if self.collection is None:
            return False
        
        try:
            message = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow(),
                "content_length": len(content)
            }
            
            self.collection.insert_one(message)
            return True
            
        except Exception as e:
            print(f"Error saving message: {e}")
            return False

    def get_history(self, session_id, limit=100):
        """Get chat history for a session"""
        if self.collection is None:
            return []
        
        try:
            messages = list(
                self.collection
                .find({"session_id": session_id}, {"_id": 0})
                .sort("timestamp", 1)
                .limit(limit)
            )
            return messages
            
        except Exception as e:
            print(f"Error retrieving history: {e}")
            return []

    def get_recent_sessions(self, days=7, limit=50):
        """Get recent active sessions"""
        if self.collection is None:
            return []
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            pipeline = [
                {"$match": {"timestamp": {"$gte": cutoff_date}}},
                {"$group": {
                    "_id": "$session_id",
                    "last_message": {"$max": "$timestamp"},
                    "message_count": {"$sum": 1}
                }},
                {"$sort": {"last_message": -1}},
                {"$limit": limit}
            ]
            
            sessions = list(self.collection.aggregate(pipeline))
            return sessions
            
        except Exception as e:
            print(f"Error retrieving sessions: {e}")
            return []

    def delete_old_messages(self, days=30):
        """Delete messages older than specified days"""
        if self.collection is None:
            return 0
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            result = self.collection.delete_many(
                {"timestamp": {"$lt": cutoff_date}}
            )
            
            deleted_count = result.deleted_count
            print(f"Deleted {deleted_count} old messages")
            return deleted_count
            
        except Exception as e:
            print(f"Error deleting old messages: {e}")
            return 0

    def get_session_stats(self, session_id):
        """Get statistics for a session"""
        if self.collection is None:
            return None
        
        try:
            pipeline = [
                {"$match": {"session_id": session_id}},
                {"$group": {
                    "_id": "$role",
                    "count": {"$sum": 1},
                    "avg_length": {"$avg": "$content_length"}
                }}
            ]
            
            stats = list(self.collection.aggregate(pipeline))
            return stats
            
        except Exception as e:
            print(f"Error getting session stats: {e}")
            return None

    def close(self):
        """Close database connection"""
        if self.client is not None:
            self.client.close()
            print("Database connection closed")

# Global database instance
db = Database()

# Cleanup old messages on startup (optional)
if db.collection is not None:
    try:
        db.delete_old_messages(days=30)
    except Exception as e:
        print(f"Could not perform cleanup: {e}")