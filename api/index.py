from flask import Flask, jsonify, request, render_template
from pymongo import MongoClient
import os
import time
import requests

# Template folder ka path set karna padta hai Vercel ke liye
app = Flask(__name__, template_folder='templates')

# 🛠️ DATABASE CONNECTION
MONGO_URL = os.getenv("MONGO_DB_URI")
client = MongoClient(MONGO_URL)
db = client["MusicAPI_DB12"]
keys_col = db["api_users"]
videos_col = db["videos_cacht"]
alert_col = db["system_alerts"]

# ==========================================
# 🌐 1. WEBSITE ROUTE (Jo 404 aa raha tha wo fix)
# ==========================================
@app.route('/')
def home():
    # Ye templates/index.html file ko dhund kar dikha dega
    return render_template('index.html')

# ==========================================
# 🚀 2. USER DASHBOARD API
# ==========================================
@app.route('/api/user/stats')
def user_stats():
    key = request.args.get("key")
    start = time.time()
    
    user = keys_col.find_one({"api_key": key})
    if not user: return jsonify({"status": 401, "error": "Invalid Key"})

    total_songs = videos_col.estimated_document_count()
    
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$total_usage"}}}]
    cursor = keys_col.aggregate(pipeline)
    res = list(cursor)
    global_hits = res[0]["total"] if res else 0

    catbox_status = "ONLINE"
    try:
        r = requests.head("https://files.catbox.moe", timeout=2)
        if r.status_code >= 400: catbox_status = "DOWN"
    except:
        catbox_status = "DOWN"

    alert = alert_col.find_one({"id": "main_alert"})
    alert_msg = alert.get("message") if alert and alert.get("active") else None

    latency = round((time.time() - start) * 1000, 2)

    return jsonify({
        "status": 200,
        "user_data": {
            "hits": user.get("total_usage", 0),
            "limit": user.get("daily_limit", 0),
            "active": user.get("active", True),
            "plan": user.get("plan", "Free")
        },
        "global_data": {
            "total_songs": total_songs,
            "total_requests": global_hits
        },
        "system": {
            "api_speed": latency,
            "server_status": "ONLINE",
            "catbox_status": catbox_status,
            "alert": alert_msg
        }
    })

# ==========================================
# 🔄 3. TOGGLE API
# ==========================================
@app.route('/api/user/toggle')
def toggle_key():
    key = request.args.get("key")
    action = request.args.get("action")
    
    user = keys_col.find_one({"api_key": key})
    if not user: return jsonify({"status": 401})

    new_status = True if action == "on" else False
    keys_col.update_one({"api_key": key}, {"$set": {"active": new_status}})
    return jsonify({"status": 200, "active": new_status})

# ==========================================
# 🚨 4. ADMIN ALERT
# ==========================================
@app.route('/api/admin/set-alert', methods=['POST'])
def set_alert():
    data = request.json
    msg = data.get("message")
    active = data.get("active", True)
    
    alert_col.update_one(
        {"id": "main_alert"},
        {"$set": {"message": msg, "active": active}},
        upsert=True
    )
    return jsonify({"status": "updated"})
