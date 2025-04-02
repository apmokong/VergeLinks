import random, string
from flask import Flask, render_template, request, redirect, jsonify
from pymongo import MongoClient
from datetime import datetime
import requests

app = Flask(__name__)

MONGO_URI = "mongodb://localhost:27017/urlshortener"
client = MongoClient(MONGO_URI)
db = client["urlshortener"]
collection = db["shortlinks"]
visits = db["visits"]

app.config['SECRET_KEY'] = 'e9a1b3d2c4e5f6a7b8c9d0e1f2a3b4c5'

def generate_short_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_location(ip):
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json")
        
        if (response.status_code == 200):
            data = response.json()

            return {
                "ip": ip,
                "city": data.get("city", "Unknown"),
                "region": data.get("region", "Unknown"),
                "country": data.get("country", "Unknown"),
                "loc": data.get("loc", "Unknown")
            }
        return {"ip": ip, "city": "Unknown", "region": "Unknown", "country": "Unknown"}
    except Exception as e:
        return {
            "ip": ip,
            "error": str(e)
        }


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        original_url = request.form.get("url")
        browser_info = request.user_agent.string 
        short_code = generate_short_code()

        collection.insert_one({
            "original_url": original_url,
            "short_code": short_code,
            "browser_info": browser_info
        })

        return f"Short URL: {request.host}/{short_code}"

    return render_template("index.html")

@app.route("/<short_code>")
def redirect_short_url(short_code):
    url_entry = collection.find_one({"short_code": short_code})
    
    if url_entry:
        ip = request.remote_addr or "Unknown"
        location = get_location(ip)

        # Save visit data
        visits.insert_one({
            "short_code": short_code,
            "ip": ip,
            "location": location,
            "browser_info": request.user_agent.string,
            "referrer": request.referrer,
            "visited_at": datetime.utcnow()
        })

        return redirect(url_entry["original_url"])
    return "URL not found", 404

# analytics
@app.route("/analytics/<short_code>")
def view_analytics(short_code):
    url_entry = collection.find_one({"short_code": short_code})
    
    if not url_entry:
        return "URL not found", 404

    visits_data = list(visits.find({"short_code": short_code}, {"_id": 0}))

    return jsonify({
        "short_code": short_code,
        "original_url": url_entry["original_url"],
        "visits": visits_data
    })

if __name__ == "__main__":
    app.run(debug=True)