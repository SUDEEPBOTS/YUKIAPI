from flask import Flask, jsonify, request, render_template
from pymongo import MongoClient
import os
import time
import requests
import random
from datetime import datetime

app = Flask(__name__, template_folder='templates')

# 🛠️ DATABASE CONNECTION
MONGO_URL = os.getenv("MONGO_DB_URI")
client = MongoClient(MONGO_URL)
db = client["MusicAPI_DB12"]
keys_col = db["api_users"]
videos_col = db["videos_cacht"]
alert_col = db["system_alerts"]

# ==========================================
# 🌐 WEBSITE ROUTE
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

# ==========================================
# 🚀 USER DASHBOARD API (Updated with Latency)
# ==========================================
@app.route('/api/user/stats')
def user_stats():
    key = request.args.get("key")
    start = time.time()
    
    # 1. User Validate
    user = keys_col.find_one({"api_key": key})
    if not user: return jsonify({"status": 401, "error": "Invalid Key"})

    # 2. Global Stats
    total_songs = videos_col.estimated_document_count()
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$total_usage"}}}]
    cursor = keys_col.aggregate(pipeline)
    res = list(cursor)
    global_hits = res[0]["total"] if res else 0

    # 3. LEADERBOARD
    top_users_cursor = keys_col.find().sort("total_usage", -1).limit(5)
    leaderboard = []
    for u in top_users_cursor:
        masked_key = (u.get("username", "User")[:10])
        if not u.get("username"): masked_key = "..." + u["api_key"][-4:]
        leaderboard.append({"name": masked_key, "hits": u.get("total_usage", 0)})

    # 4. GRAPHS DATA (Smart Generation - Purana Logic)
    current_hits = user.get("total_usage", 0)
    
    # Generate Monthly Data
    monthly_data = []
    temp_hits = current_hits
    for i in range(30):
        val = random.randint(0, int(temp_hits * 0.1) + 1)
        monthly_data.append(val)
        temp_hits -= val
        if temp_hits <= 0: break
    monthly_data.reverse()

    # Generate Today's Hourly Data
    today_hits = user.get("used_today", 0)
    today_data = [0] * 24
    current_hour = datetime.now().hour
    for _ in range(today_hits):
        hr = random.randint(0, current_hour)
        today_data[hr] += 1

    # 5. CATBOX SERVER CHECK (Updated with Speed) 🟣
    catbox_status = "ONLINE"
    catbox_latency = 0
    try:
        t1 = time.time()
        r = requests.head("https://files.catbox.moe", timeout=2)
        catbox_latency = round((time.time() - t1) * 1000, 2)
        if r.status_code >= 400: catbox_status = "DOWN"
    except:
        catbox_status = "DOWN"
        catbox_latency = 0

    alert = alert_col.find_one({"id": "main_alert"})
    alert_msg = alert.get("message") if alert and alert.get("active") else None
    latency = round((time.time() - start) * 1000, 2)

    return jsonify({
        "status": 200,
        "user_data": {
            "hits": user.get("total_usage", 0),
            "today": user.get("used_today", 0),
            "limit": user.get("daily_limit", 50),
            "active": user.get("active", True),
            "plan": user.get("plan", "Free"),
            "username": user.get("username", "User")
        },
        "global_data": {
            "total_songs": total_songs,
            "total_requests": global_hits,
            "leaderboard": leaderboard
        },
        "graphs": {
            "monthly": monthly_data,
            "today": today_data
        },
        "system": {
            "api_speed": latency,
            "catbox_status": catbox_status,
            "catbox_latency": catbox_latency, # <-- Added for Purple Graph
            "alert": alert_msg
        }
    })

# ==========================================
# 🟠 NEW: EXTERNAL MONITOR ROUTE (For Orange Graph)
# ==========================================
@app.route('/api/monitor/external')
def monitor_external():
    # Tera External API URL
    target_url = "https://fastapi2-wdtl.onrender.com/getvideo?query=kesariya&key=YUKI-D48896353AE8"
    status = "ONLINE"
    latency = 0
    timestamp = datetime.now().strftime("%H:%M:%S")

    try:
        start = time.time()
        # Request bhej ke check kar rahe hain
        r = requests.get(target_url, timeout=10)
        latency = round((time.time() - start) * 1000, 2)
        
        # Agar 200 OK nahi aaya toh Down maano
        if r.status_code != 200:
            status = "DOWN"
    except Exception as e:
        status = "DOWN"
        latency = 0
    
    return jsonify({
        "status": status,
        "latency": latency,
        "timestamp": timestamp
    })

# ==========================================
# ✏️ UPDATE USERNAME
# ==========================================
@app.route('/api/user/update_profile', methods=['POST'])
def update_profile():
    data = request.json
    key = data.get("key")
    new_name = data.get("username")
    
    if not key or not new_name: return jsonify({"status": 400})
    
    keys_col.update_one({"api_key": key}, {"$set": {"username": new_name}})
    return jsonify({"status": 200, "message": "Updated"})

# ==========================================
# 🔄 TOGGLE API
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
# 🚨 ADMIN ALERT
# ==========================================
@app.route('/api/admin/set-alert', methods=['POST'])
def set_alert():
    data = request.json
    alert_col.update_one(
        {"id": "main_alert"},
        {"$set": {"message": data.get("message"), "active": data.get("active", True)}},
        upsert=True
    )
    return jsonify({"status": "updated"})
    
