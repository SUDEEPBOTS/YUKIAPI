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
# 🚀 USER DASHBOARD API
# ==========================================
@app.route('/api/user/stats')
def user_stats():
    key = request.args.get("key")
    start = time.time()
    
    user = keys_col.find_one({"api_key": key})
    if not user: return jsonify({"status": 401, "error": "Invalid Key"})

    total_songs = videos_col.estimated_document_count()
    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$total_usage"}}}]
    res = list(keys_col.aggregate(pipeline))
    global_hits = res[0]["total"] if res else 0

    top_users = keys_col.find().sort("total_usage", -1).limit(5)
    leaderboard = [{"name": (u.get("username", "User")[:10]) if u.get("username") else "..." + u["api_key"][-4:], "hits": u.get("total_usage", 0)} for u in top_users]

    # Graph Data
    current_hits = user.get("total_usage", 0)
    monthly_data = []
    temp_hits = current_hits
    for i in range(30):
        val = random.randint(0, int(temp_hits * 0.1) + 1)
        monthly_data.append(val)
        temp_hits -= val
        if temp_hits <= 0: break
    monthly_data.reverse()

    today_hits = user.get("used_today", 0)
    today_data = [0] * 24
    for _ in range(today_hits): today_data[random.randint(0, datetime.now().hour)] += 1

    # Catbox Check
    catbox_status = "ONLINE"
    catbox_latency = 0
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    try:
        t1 = time.time()
        r = requests.head("https://files.catbox.moe", headers=headers, timeout=5)
        catbox_latency = round((time.time() - t1) * 1000, 2)
        if r.status_code >= 500: catbox_status = "DOWN"
    except:
        catbox_status = "DOWN"

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
        "global_data": { "total_songs": total_songs, "total_requests": global_hits, "leaderboard": leaderboard },
        "graphs": { "monthly": monthly_data, "today": today_data },
        "system": { "api_speed": latency, "catbox_status": catbox_status, "catbox_latency": catbox_latency, "alert": alert_msg }
    })

# ==========================================
# 🟠 EXTERNAL MONITOR (SUPER STRICT MODE) 🔥
# ==========================================
@app.route('/api/monitor/external')
def monitor_external():
    target_url = "https://fastapi2-wdtl.onrender.com/getvideo?query=kesariya&key=YUKI-51982BB77950"
    
    status = "DOWN"
    latency = 0
    timestamp = datetime.now().strftime("%H:%M:%S")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

    try:
        start = time.time()
        r = requests.get(target_url, headers=headers, timeout=10)
        current_latency = round((time.time() - start) * 1000, 2)
        
        # 🛑 STAGE 1: Check HTTP Code
        if r.status_code == 200:
            # 🛑 STAGE 2: Check JSON Body (Internal Status)
            try:
                data = r.json()
                # Agar JSON mein "status" field hai aur wo 200 nahi hai, toh DOWN hai
                if data.get("status") == 200 or data.get("status") == "success":
                    status = "ONLINE"
                    latency = current_latency
                elif "link" in data or "id" in data:
                    # Agar link mil gaya toh pakka Online hai
                    status = "ONLINE"
                    latency = current_latency
                else:
                    # HTTP 200 hai par JSON mein gadbad hai (e.g. status: 404 or error)
                    status = "DOWN"
                    latency = 0
            except:
                # JSON parse nahi hua (HTML error page wagra aa gaya)
                status = "DOWN"
                latency = 0
        else:
            # HTTP Code hi 200 nahi hai (404, 500, 502)
            status = "DOWN"
            latency = 0

    except Exception as e:
        status = "DOWN"
        latency = 0
    
    return jsonify({
        "status": status,
        "latency": latency,
        "timestamp": timestamp
    })

# ... (Update Profile & Toggle Routes - Same as before) ...
@app.route('/api/user/update_profile', methods=['POST'])
def update_profile():
    data = request.json
    keys_col.update_one({"api_key": data.get("key")}, {"$set": {"username": data.get("username")}})
    return jsonify({"status": 200})

@app.route('/api/user/toggle')
def toggle_key():
    key = request.args.get("key")
    action = request.args.get("action")
    new_status = True if action == "on" else False
    keys_col.update_one({"api_key": key}, {"$set": {"active": new_status}})
    return jsonify({"status": 200})

@app.route('/api/admin/set-alert', methods=['POST'])
def set_alert():
    data = request.json
    alert_col.update_one({"id": "main_alert"}, {"$set": {"message": data.get("message"), "active": data.get("active", True)}}, upsert=True)
    return jsonify({"status": "updated"})
    
