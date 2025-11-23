from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime, timedelta
from logger import setup_logger
from config import MONGO_URI, DB_NAME, COLLECTION_NAME
import uuid

# Setup logging
logger = setup_logger(__name__)

class Database:
    def __init__(self):
        if not MONGO_URI:
            logger.warning("MONGO_URI not found. Chat history will not be saved.")
            self.client = None
            self.db = None
            self.collection = None
            self.bots_collection = None
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
                self.bots_collection = self.db['bots']
                
                # Create indexes for better performance
                self._create_indexes()
                
                logger.info("Connected to MongoDB successfully")
            except Exception as e:
                logger.error(f"Error connecting to MongoDB: {e}")
                logger.warning("  Chat history will not be saved")
                self.client = None
                self.db = None
                self.collection = None
                self.bots_collection = None

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
                
                # Index for bot sessions
                self.collection.create_index([("bot_id", ASCENDING)])
            except Exception as e:
                logger.warning(f"Could not create indexes: {e}")

    def save_message(self, session_id, role, content, bot_id=None):
        """Save a message to the database"""
        if self.collection is None:
            return None
        
        try:
            message = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow(),
                "message_id": str(uuid.uuid4())
            }
            
            if bot_id:
                message["bot_id"] = bot_id
                
            result = self.collection.insert_one(message)
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None

    def get_history(self, session_id, limit=50):
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
            logger.error(f"Error retrieving history: {e}")
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
                    "message_count": {"$sum": 1},
                    "preview": {"$first": "$content"}, # Simple preview
                    "bot_id": {"$first": "$bot_id"}
                }},
                {"$sort": {"last_message": -1}},
                {"$limit": limit}
            ]
            
            sessions = list(self.collection.aggregate(pipeline))
            return sessions
        except Exception as e:
            logger.error(f"Error retrieving sessions: {e}")
            return []

    # --- Bot Management Methods ---

    def create_bot(self, name, url, namespace):
        """Create or update a bot profile"""
        if self.bots_collection is None:
            return None
        
        try:
            bot_id = str(uuid.uuid4())
            bot = {
                "id": bot_id,
                "name": name,
                "url": url,
                "namespace": namespace,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Upsert based on URL to avoid duplicates
            self.bots_collection.update_one(
                {"url": url},
                {"$set": bot},
                upsert=True
            )
            return bot
        except Exception as e:
            logger.error(f"Error creating bot: {e}")
            return None

    def get_bots(self):
        """Get all bot profiles"""
        if self.bots_collection is None:
            return []
        
        try:
            return list(self.bots_collection.find({}, {"_id": 0}))
        except Exception as e:
            logger.error(f"Error fetching bots: {e}")
            return []

    def get_bot(self, bot_id):
        """Get a specific bot profile"""
        if self.bots_collection is None:
            return None
        
        try:
            return self.bots_collection.find_one({"id": bot_id}, {"_id": 0})
        except Exception as e:
            logger.error(f"Error fetching bot: {e}")
            return None

    def get_sessions_by_bot(self, bot_id):
        """Get chat sessions for a specific bot"""
        if self.collection is None:
            return []
        
        try:
            pipeline = [
                {"$match": {"bot_id": bot_id}},
                {"$sort": {"timestamp": 1}}, # Sort by time to get first message as preview
                {"$group": {
                    "_id": "$session_id",
                    "last_message": {"$max": "$timestamp"},
                    "message_count": {"$sum": 1},
                    "preview": {"$first": "$content"} 
                }},
                {"$sort": {"last_message": -1}},
                {"$limit": 50}
            ]
            
            sessions = list(self.collection.aggregate(pipeline))
            return sessions
        except Exception as e:
            logger.error(f"Error fetching bot sessions: {e}")
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
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} old messages")
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting old messages: {e}")
            return 0

    def close(self):
        """Close database connection"""
        if self.client:
            try:
                self.client.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing database: {e}")

# Global database instance
db = Database()

# Cleanup old messages on startup (optional)
if db.collection is not None:
    try:
        db.delete_old_messages(days=30)
    except Exception as e:
        logger.error(f"Could not perform cleanup: {e}")