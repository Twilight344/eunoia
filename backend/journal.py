from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from bson import ObjectId
from datetime import datetime, timedelta
from db import db

bp = Blueprint('journal', __name__)

# Collection for journal entries
journal_entries = db["journal_entries"]

@bp.route("/entries", methods=["POST"])
@jwt_required()
def create_entry():
    """Create a new journal entry"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    entry = {
        "user_id": ObjectId(user_id),
        "title": data.get("title", ""),
        "content": data.get("content", ""),
        "mood": data.get("mood", ""),
        "tags": data.get("tags", []),
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    result = journal_entries.insert_one(entry)
    entry["_id"] = str(result.inserted_id)
    entry["user_id"] = str(entry["user_id"])
    entry["created_at"] = entry["created_at"].isoformat()
    entry["updated_at"] = entry["updated_at"].isoformat()
    
    return jsonify(entry), 201

@bp.route("/entries", methods=["GET"])
@jwt_required()
def get_entries():
    """Get all journal entries for the current user"""
    user_id = get_jwt_identity()
    
    # Get query parameters for filtering
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 10))
    mood_filter = request.args.get("mood", "")
    search_query = request.args.get("search", "")
    
    # Build filter
    filter_query = {"user_id": ObjectId(user_id)}
    if mood_filter:
        filter_query["mood"] = mood_filter
    if search_query:
        filter_query["$or"] = [
            {"title": {"$regex": search_query, "$options": "i"}},
            {"content": {"$regex": search_query, "$options": "i"}}
        ]
    
    # Get total count for pagination
    total = journal_entries.count_documents(filter_query)
    
    # Get entries with pagination
    entries = list(journal_entries.find(filter_query)
                  .sort("created_at", -1)
                  .skip((page - 1) * limit)
                  .limit(limit))
    
    # Format entries
    formatted_entries = []
    for entry in entries:
        entry["_id"] = str(entry["_id"])
        entry["user_id"] = str(entry["user_id"])
        entry["created_at"] = entry["created_at"].isoformat()
        entry["updated_at"] = entry["updated_at"].isoformat()
        formatted_entries.append(entry)
    
    return jsonify({
        "entries": formatted_entries,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    })

@bp.route("/entries/<entry_id>", methods=["GET"])
@jwt_required()
def get_entry(entry_id):
    """Get a specific journal entry"""
    user_id = get_jwt_identity()
    
    entry = journal_entries.find_one({
        "_id": ObjectId(entry_id),
        "user_id": ObjectId(user_id)
    })
    
    if not entry:
        return jsonify({"error": "Entry not found"}), 404
    
    entry["_id"] = str(entry["_id"])
    entry["user_id"] = str(entry["user_id"])
    entry["created_at"] = entry["created_at"].isoformat()
    entry["updated_at"] = entry["updated_at"].isoformat()
    
    return jsonify(entry)

@bp.route("/entries/<entry_id>", methods=["PUT"])
@jwt_required()
def update_entry(entry_id):
    """Update a journal entry"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    update_data = {
        "title": data.get("title", ""),
        "content": data.get("content", ""),
        "mood": data.get("mood", ""),
        "tags": data.get("tags", []),
        "updated_at": datetime.now()
    }
    
    result = journal_entries.update_one(
        {"_id": ObjectId(entry_id), "user_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Entry not found"}), 404
    
    # Return the updated entry
    entry = journal_entries.find_one({"_id": ObjectId(entry_id)})
    entry["_id"] = str(entry["_id"])
    entry["user_id"] = str(entry["user_id"])
    entry["created_at"] = entry["created_at"].isoformat()
    entry["updated_at"] = entry["updated_at"].isoformat()
    
    return jsonify(entry)

@bp.route("/entries/<entry_id>", methods=["DELETE"])
@jwt_required()
def delete_entry(entry_id):
    """Delete a journal entry"""
    user_id = get_jwt_identity()
    
    result = journal_entries.delete_one({
        "_id": ObjectId(entry_id),
        "user_id": ObjectId(user_id)
    })
    
    if result.deleted_count == 0:
        return jsonify({"error": "Entry not found"}), 404
    
    return jsonify({"message": "Entry deleted successfully"})

@bp.route("/entries/stats", methods=["GET"])
@jwt_required()
def get_journal_stats():
    """Get journal statistics for the user"""
    user_id = get_jwt_identity()
    
    # Total entries
    total_entries = journal_entries.count_documents({"user_id": ObjectId(user_id)})
    
    # Entries by mood
    mood_stats = list(journal_entries.aggregate([
        {"$match": {"user_id": ObjectId(user_id)}},
        {"$group": {"_id": "$mood", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]))
    
    # Entries by month (last 6 months)
    six_months_ago = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    for _ in range(6):
        six_months_ago = six_months_ago.replace(month=six_months_ago.month - 1)
    
    monthly_stats = list(journal_entries.aggregate([
        {"$match": {
            "user_id": ObjectId(user_id),
            "created_at": {"$gte": six_months_ago}
        }},
        {"$group": {
            "_id": {
                "year": {"$year": "$created_at"},
                "month": {"$month": "$created_at"}
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}}
    ]))
    
    # Entries by day (last 7 days)
    seven_days_ago = datetime.now() - timedelta(days=7)
    
    daily_stats = list(journal_entries.aggregate([
        {"$match": {
            "user_id": ObjectId(user_id),
            "created_at": {"$gte": seven_days_ago}
        }},
        {"$group": {
            "_id": {
                "year": {"$year": "$created_at"},
                "month": {"$month": "$created_at"},
                "day": {"$dayOfMonth": "$created_at"}
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1, "_id.day": 1}}
    ]))
    
    return jsonify({
        "total_entries": total_entries,
        "mood_stats": mood_stats,
        "monthly_stats": monthly_stats,
        "daily_stats": daily_stats
    })
