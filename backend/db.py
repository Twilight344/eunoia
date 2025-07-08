from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os
client = MongoClient(os.environ.get("MONGO_URI"))
db = client["mydatabase"]

# Collections
users = db["users"]
chats = db["chat_sessions"]

# 🧾 Save a new user
def save_user(username, password, email=None, provider=None, name=None, picture=None):
    user_data = {
        "username": username,
        "password": password
    }
    
    if email:
        user_data["email"] = email
    if provider:
        user_data["provider"] = provider
    if name:
        user_data["name"] = name
    if picture:
        user_data["picture"] = picture
        
    users.insert_one(user_data)

# 🔍 Get user by username
def get_user_by_username(username):
    return users.find_one({"username": username})

# 🔍 Get user by email
def get_user_by_email(email):
    return users.find_one({"email": email})

# 🔍 Get or create OAuth user
def get_or_create_oauth_user(email, provider, name=None, picture=None):
    # Check if user exists
    user = get_user_by_email(email)
    
    if user:
        return user
    
    # Create new user with email as username if no name provided
    username = name or email.split('@')[0]
    # Ensure unique username
    base_username = username
    counter = 1
    while get_user_by_username(username):
        username = f"{base_username}{counter}"
        counter += 1
    
    # Create user without password for OAuth
    user_data = {
        "username": username,
        "email": email,
        "provider": provider,
        "password": None  # OAuth users don't have passwords
    }
    
    if name:
        user_data["name"] = name
    if picture:
        user_data["picture"] = picture
        
    result = users.insert_one(user_data)
    return users.find_one({"_id": result.inserted_id})

# 🆕 Create a new empty chat session for a user, set as active and deactivate others
def create_empty_chat_session(user_id):
    chats.update_many({"user_id": ObjectId(user_id)}, {"$set": {"active": False}})
    session = {
        "user_id": ObjectId(user_id),
        "timestamp": datetime.now(),
        "messages": [],
        "active": True
    }
    result = chats.insert_one(session)
    return str(result.inserted_id)

# ➕ Append a message to a specific session
def append_message_to_session(session_id, sender, text):
    chats.update_one(
        {"_id": ObjectId(session_id)},
        {"$push": {"messages": {"sender": sender, "text": text, "timestamp": datetime.now()}}}
    )

# 📜 Get all chat sessions for a user
def get_user_sessions(user_id):
    return list(chats.find(
        {"user_id": ObjectId(user_id)},
        {"_id": 1, "timestamp": 1, "messages": 1, "active": 1}
    ))

# Get a single session by ID (for loading a session)
def get_session_by_id(session_id):
    return chats.find_one({"_id": ObjectId(session_id)})

# Get the user's active session
def get_active_session(user_id):
    return chats.find_one({"user_id": ObjectId(user_id), "active": True})

# (Optional) For admin/testing: get all chats
def get_all_chats():
    return list(chats.find({}, {"_id": 0}))
