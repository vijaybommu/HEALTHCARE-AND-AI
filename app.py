
from flask import Flask, request, jsonify
from flask_cors import CORS
import math
from datetime import datetime

# Initialize Flask App
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for frontend integration

# ==========================================
# 1. HACKATHON DATABASE (Mock Hospital Network)
# ==========================================
HOSPITALS = [
    {
        "id": 1, 
        "name": "City General Hospital", 
        "lat": 13.0827, 
        "lng": 80.2707, 
        "totalIcu": 20, 
        "availIcu": 1, 
        "waitMins": 45,
        "specialty": "General & Trauma"
    },
    {
        "id": 2, 
        "name": "Apollo Specialty Care", 
        "lat": 13.0524, 
        "lng": 80.2508, 
        "totalIcu": 15, 
        "availIcu": 6, 
        "waitMins": 10,
        "specialty": "Cardiology & Emergency"
    },
    {
        "id": 3, 
        "name": "Metro Emergency Center", 
        "lat": 13.0382, 
        "lng": 80.2158, 
        "totalIcu": 12, 
        "availIcu": 4, 
        "waitMins": 15,
        "specialty": "Critical Care & Pulmonology"
    }
]

# Default Incident / Ambulance Location (GPS Coordinates)
INCIDENT_LOCATION = {"lat": 13.0600, "lng": 80.2400}

# ==========================================
# 2. CORE UTILITY FUNCTIONS
# ==========================================
def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Haversine formula to compute the great-circle distance 
    between two points on Earth in kilometers.
    """
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon1 - lon2)
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# ==========================================
# 3. API ROUTES & ENDPOINTS
# ==========================================

@app.route('/', methods=['GET'])
def home():
    """Health check endpoint to verify backend is live."""
    return jsonify({
        "status": "online",
        "system": "TriageAI Global Dispatch API",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/hospitals', methods=['GET'])
def get_hospitals():
    """Fetch live data for all hospitals in the network grid."""
    return jsonify({
        "status": "success",
        "count": len(HOSPITALS),
        "data": HOSPITALS
    })

@app.route('/api/triage', methods=['POST'])
def process_triage():
    """
    Main Triage Engine Endpoint:
    - Receives patient vitals (SpO2, Heart Rate, BP, Symptoms)
    - Computes Emergency Severity Index (ESI)
    - Determines optimal hospital routing based on distance and available ICU beds
    """
    try:
        req_data = request.json or {}
        
        # Extract patient vitals safely with fallback values
        age = int(req_data.get('age', 30))
        spo2 = float(req_data.get('spo2', 98))
        heart_rate = float(req_data.get('heartRate', 75))
        symptoms = req_data.get('symptoms', 'General checkup')

        # ----------------------------------
        # STEP A: ESI Triage Scoring Algorithm
        # ----------------------------------
        if spo2 < 90 or heart_rate > 130:
            level = 1
            badge_class = "badge-critical"
            level_text = "ESI Level 1 - Critical"
            description = "Immediate life-saving resuscitation required. Priority ICU dispatch activated."
        elif spo2 <= 94 or heart_rate >= 100:
            level = 2
            badge_class = "badge-urgent"
            level_text = "ESI Level 2 - Urgent"
            description = "High-risk condition. Urgent medical intervention required within minutes."
        else:
            level = 3
            badge_class = "badge-standard"
            level_text = "ESI Level 3 - Standard"
            description = "Stable vitals. Standard emergency intake protocol assigned."

        # ----------------------------------
        # STEP B: Hospital Routing Optimization
        # ----------------------------------
        # Filter hospitals that have available ICU beds
        valid_hospitals = [h for h in HOSPITALS if h['availIcu'] > 0]
        if not valid_hospitals:
            valid_hospitals = HOSPITALS  # Fallback to all hospitals if capacity is full everywhere

        # Scoring function: Distance (km) + Wait Time Penalty
        def routing_score(hospital):
            dist = calculate_distance(
                INCIDENT_LOCATION['lat'], INCIDENT_LOCATION['lng'], 
                hospital['lat'], hospital['lng']
            )
            # Weighting factor: distance matters most, but high wait times add friction
            return dist + (hospital['waitMins'] * 0.05)

        # Sort hospitals by optimal score (lowest combined score is best)
        valid_hospitals.sort(key=routing_score)

        best_hospital = valid_hospitals[0]
        best_distance = round(
            calculate_distance(
                INCIDENT_LOCATION['lat'], INCIDENT_LOCATION['lng'], 
                best_hospital['lat'], best_hospital['lng']
            ), 1
        )

        # ----------------------------------
        # STEP C: Return Structured JSON Response
        # ----------------------------------
        return jsonify({
            "status": "success",
            "patientSummary": {
                "age": age,
                "spo2": spo2,
                "heartRate": heart_rate,
                "symptoms": symptoms
            },
            "triage": {
                "level": level,
                "badgeClass": badge_class,
                "levelText": level_text,
                "description": description
            },
            "recommendedHospital": {
                "id": best_hospital['id'],
                "name": best_hospital['name'],
                "lat": best_hospital['lat'],
                "lng": best_hospital['lng'],
                "availIcu": best_hospital['availIcu'],
                "totalIcu": best_hospital['totalIcu'],
                "waitMins": best_hospital['waitMins'],
                "specialty": best_hospital['specialty'],
                "distanceKm": best_distance
            },
            "alternativeHospitals": [
                {
                    "name": h['name'],
                    "availIcu": h['availIcu'],
                    "distanceKm": round(calculate_distance(INCIDENT_LOCATION['lat'], INCIDENT_LOCATION['lng'], h['lat'], h['lng']), 1)
                } for h in valid_hospitals[1:]
            ]
        })

    except Exception as err:
        return jsonify({
            "status": "error",
            "message": str(err)
        }), 400

# ==========================================
# 4. RUN SERVER
# ==========================================
if __name__ == '__main__':
    print("Starting TriageAI Python Backend Server on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)
    