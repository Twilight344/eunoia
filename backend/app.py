import os
from dotenv import load_dotenv
from flask import Flask, request, Response, stream_with_context, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from bson import ObjectId
from ollama_chat import stream_gemma_response
from db import (
    get_all_chats, save_user, get_user_by_username, get_user_by_email, get_or_create_oauth_user,
    create_empty_chat_session, append_message_to_session, get_user_sessions, get_session_by_id, get_active_session
)
from oauth_config import verify_google_token
from emotion import bp as emotion_bp
from journal import bp as journal_bp
from planner import bp as planner_bp

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)
load_dotenv()
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
jwt = JWTManager(app)

app.register_blueprint(emotion_bp)
app.register_blueprint(journal_bp)
app.register_blueprint(planner_bp)

# ✅ SIGNUP
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    password = bcrypt.generate_password_hash(data.get("password")).decode("utf-8")

    if get_user_by_username(username):
        return jsonify({"error": "User already exists"}), 409

    save_user(username, password)
    return jsonify({"message": "Signup successful"}), 201

# ✅ LOGIN
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = get_user_by_username(username)
    if user and bcrypt.check_password_hash(user["password"], password):
        token = create_access_token(identity=str(user["_id"]))
        return jsonify({"token": token}), 200
    return jsonify({"error": "Invalid credentials"}), 401

# ✅ GOOGLE OAUTH LOGIN
@app.route("/auth/google", methods=["POST"])
def google_login():
    data = request.get_json()
    code = data.get("code")
    
    if not code:
        return jsonify({"error": "No authorization code provided"}), 400
    
    try:
        # Exchange authorization code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': os.getenv('GOOGLE_REDIRECT_URI')
        }
        
        import requests
        token_response = requests.post(token_url, data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()
        
        # Get user info using the access token
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {'Authorization': f'Bearer {tokens["access_token"]}'}
        user_response = requests.get(user_info_url, headers=headers)
        user_response.raise_for_status()
        user_info = user_response.json()
        
        # Get or create user
        user = get_or_create_oauth_user(
            email=user_info['email'],
            provider='google',
            name=user_info.get('name'),
            picture=user_info.get('picture')
        )
        
        # Create JWT token
        jwt_token = create_access_token(identity=str(user["_id"]))
        return jsonify({"token": jwt_token}), 200
        
    except Exception as e:
        print(f"Google OAuth error: {e}")
        return jsonify({"error": "Google authentication failed"}), 401

# ✅ START NEW SESSION 
@app.route("/start_session", methods=["POST"])
@jwt_required()
def start_session():
    user_id = get_jwt_identity()
    session_id = create_empty_chat_session(user_id)
    return jsonify({"session_id": session_id})

# ✅ STREAMING CHAT — now requires session_id
@app.route("/chat", methods=["POST"])
@jwt_required()
def chat():
    data = request.get_json()
    user_msg = data.get("message", "")
    user_id = get_jwt_identity()
    session_id = data.get("session_id")

    if not user_msg or not session_id:
        return jsonify({"error": "No message or session_id provided"}), 400

    # Append user message, get session so far, build prompt
    append_message_to_session(session_id, "user", user_msg)
    session = get_session_by_id(session_id)
    prompt = "You are a kind and empathetic mental health bot, all you need to do is reply to the user's message kindly.\n"
    for msg in session["messages"]:
        if msg["sender"] == "user":
            prompt += f"User: {msg['text']}\n"
        else:
            prompt += f"AI: {msg['text']}\n"
    prompt += "AI:"
    def generate():
        full_reply = ""
        for chunk in stream_gemma_response(prompt):
            full_reply += chunk
            yield f"data: {chunk}\n\n"
        append_message_to_session(session_id, "bot", full_reply)
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

# ✅ PER-USER HISTORY (all sessions)
@app.route("/history", methods=["GET"])
@jwt_required()
def history():
    user_id = get_jwt_identity()
    sessions = get_user_sessions(user_id)
    # Format for frontend: id, timestamp, first user message, last message time
    formatted = []
    for s in sessions:
        if not s["messages"]:
            continue
        formatted.append({
            "session_id": str(s["_id"]),
            "timestamp": s["timestamp"].isoformat() if "timestamp" in s else "",
            "first_user_message": next((m["text"] for m in s["messages"] if m["sender"] == "user"), ""),
            "last_message_time": s["messages"][-1]["timestamp"].isoformat() if s["messages"] else "",
            "messages": s["messages"]
        })
    # Most recent first
    formatted.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify(formatted)

if __name__ == "__main__":
    app.run(port=5000, debug=True)








# # app.py
# from flask import Flask, request, jsonify
# import requests
# import json

# app = Flask(__name__)

# OLLAMA_URL = "http://34.131.29.49:11434/api/generate"
# MODEL = "gemma3"

# @app.route('/chat', methods=['POST'])
# def chat():
#     user_prompt = request.json.get('message', '')
#     response = requests.post(OLLAMA_URL, json={
#         "model": MODEL,
#         "prompt": user_prompt,
#         "stream": True
#     }, stream=True)

#     full_reply = ""
#     for line in response.iter_lines():
#         if line:
#             try:
#                 data = json.loads(line.decode('utf-8'))
#                 full_reply += data.get("response", "")
#             except Exception as e:
#                 return jsonify({"reply": f"[ERROR parsing response]: {str(e)}"})

#     return jsonify({"reply": full_reply.strip()})

# if __name__ == '__main__':
#     app.run(debug=True)
