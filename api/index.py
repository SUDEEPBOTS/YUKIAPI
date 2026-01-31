from flask import Flask, jsonify, request
from pymongo import MongoClient
import os
import time
import requests

app = Flask(__name__)

# 🛠️ DATABASE CONNECTION (Vercel Env Var se lega)
MONGO_URL = os.getenv("MONGO_DB_URI")
client = MongoClient(MONGO_URL)
db = client["MusicAPI_DB12"]
keys_col = db["api_users"]
videos_col = db["videos_cacht"]
alert_col = db["system_alerts"]

# -----------------------------------
# 🚀 1. USER DASHBOARD DATA
# -----------------------------------
@app.route('/api/user/stats')
def user_stats():
    key = request.args.get("key")
    start = time.time()
    
    # 1. User Validate
    user = keys_col.find_one({"api_key": key})
    if not user: return jsonify({"status": 401, "error": "Invalid Key"})

    # 2. Global Stats (Aggregate for speed)
    total_songs = videos_col.estimated_document_count()
    
    # Total Hits (Sabka Jod)
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$total_usage"}}}]
    cursor = keys_col.aggregate(pipeline)
    res = list(cursor)
    global_hits = res[0]["total"] if res else 0

    # 3. Server Checks
    catbox_status = "ONLINE"
    try:
        r = requests.head("https://files.catbox.moe", timeout=2)
        if r.status_code >= 400: catbox_status = "DOWN"
    except:
        catbox_status = "DOWN"

    # 4. Alert Check
    alert = alert_col.find_one({"id": "main_alert"})
    alert_msg = alert.get("message") if alert and alert.get("active") else None

    # 5. Speed Calc
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

# -----------------------------------
# 🔄 2. TOGGLE API (ON/OFF)
# -----------------------------------
@app.route('/api/user/toggle')
def toggle_key():
    key = request.args.get("key")
    action = request.args.get("action") # 'on' or 'off'
    
    user = keys_col.find_one({"api_key": key})
    if not user: return jsonify({"status": 401})

    new_status = True if action == "on" else False
    keys_col.update_one({"api_key": key}, {"$set": {"active": new_status}})
    return jsonify({"status": 200, "active": new_status})

# -----------------------------------
# 🚨 3. ADMIN SET ALERT (Bot se call karna)
# -----------------------------------
@app.route('/api/admin/set-alert', methods=['POST'])
def set_alert():
    # Security: Add a secret header check here if needed
    data = request.json
    msg = data.get("message")
    active = data.get("active", True)
    
    alert_col.update_one(
        {"id": "main_alert"},
        {"$set": {"message": msg, "active": active}},
        upsert=True
    )
    return jsonify({"status": "updated"})
  
