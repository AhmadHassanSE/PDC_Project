# Shared settings for the Live Delivery Tracker demo.
# Edit the values in this file before running the scripts.
import os

# AWS keys live in demo/aws_credentials (no AWS CLI needed). boto3 reads this file automatically.
os.environ.setdefault("AWS_SHARED_CREDENTIALS_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "aws_credentials"))

REGION = "us-east-1"            # every AWS resource in the guide is created in this region
TRACKER_NAME = "DeliveryTracker"
DEVICE_ID = "truck01"
TOPIC = "trucks/location"

# Start and end of the trip as (latitude, longitude), the order Google Maps shows.
# In Google Maps, right-click a place and click the numbers at the top of the menu to copy them.
START = (33.6563, 73.0153)     # FAST-NUCES Islamabad, H-11/4 (check in Google Maps)
END = (33.7295, 73.0372)       # Faisal Mosque
START_NAME = "FAST-NUCES Islamabad"
END_NAME = "Faisal Mosque"

# The fleet. Every truck leaves START and drives to its own "end" point.
# "id" is the deviceId each truck reports to IoT Core; the rest is the delivery sheet shown on the map.
# cargo rows are (item, quantity, weight in kg).
FLEET = [
    {"id": "truck01", "color": "#FF9F1C", "destination": END_NAME, "end": END,
     "load": "Mosque supplies", "order": "DL-2041", "receiver": "Mosque administration office",
     "driver": "Bilal Ahmed", "vehicle": "Hino Dutro, LES-4127", "window": "Before 5:00 pm",
     "cargo": [("Prayer mats", "120 pieces", 180), ("Water coolers", "6 units", 210), ("Quran stands", "40 pieces", 96)],
     "note": "Unload at the east gate."},
    {"id": "truck02", "color": "#2EC4B6", "destination": "PIMS Hospital", "end": (33.7040, 73.0530),
     "load": "Medical supplies", "order": "DL-2042", "receiver": "Central pharmacy store",
     "driver": "Usman Tariq", "vehicle": "Isuzu NPR reefer, RIZ-3310", "window": "Before 4:30 pm",
     "cargo": [("Insulin vials", "40 cartons", 120), ("IV fluids", "90 cartons", 810), ("Surgical gloves", "60 cartons", 150)],
     "note": "Cold chain: keep the insulin at 2 to 8 °C."},
    {"id": "truck03", "color": "#B9A5FF", "destination": "Saddar, Rawalpindi", "end": (33.5969, 73.0528),
     "load": "Groceries", "order": "DL-2043", "receiver": "Kareem Wholesale, Bank Road",
     "driver": "Hamza Sheikh", "vehicle": "Hino 500, LEB-7752", "window": "Before 6:00 pm",
     "cargo": [("Flour, 20 kg bags", "80 bags", 1600), ("Cooking oil, 16 L tins", "60 tins", 960), ("Rice, 25 kg bags", "40 bags", 1000)],
     "note": "Receiver unloads with their own crew."},
    {"id": "truck04", "color": "#FF8FA3", "destination": "Centaurus Mall", "end": (33.7077, 73.0498),
     "load": "Electronics", "order": "DL-2044", "receiver": "Loading dock B, ground floor",
     "driver": "Saad Malik", "vehicle": "JAC X200, ICT-618", "window": "Before 5:30 pm",
     "cargo": [("LED TVs", "24 units", 384), ("Laptops", "60 units", 132), ("Phone accessories", "30 cartons", 150)],
     "note": "Fragile. Get a signature on delivery."},
]

STEP_METERS = 80       # how far the truck moves per update (keep above 30, see the tracker's filtering)
SEND_INTERVAL = 1.0     # seconds between updates
DEPART_GAP = 6          # seconds between one truck leaving the depot and the next

# Optional: an Amazon Location API key for the map (guide, Part F).
# Leave empty to use OpenStreetMap tiles instead.
MAP_API_KEY = ""
# v1.public.eyJqdGkiOiJmYzhlNTg2Yi01YTYwLTQ3ZDUtYTNkNy1kNmViMDhmYzY4NmEifQOpBmz6smh_lHbJ-Ka8J1kdmKdWJCrT8wMi-gSGJljo4WaQ3ZWchqfvf0zzL9tlBctWvVBoA7DMw6mHYCstFIe6X_vTSQvUJJTcIPSvxq6gm_NaFzdd6V6Yel57yM-P6V3Lqm3YkP1r4zZOzxm-NtbjgyFBsY6e8i7L4vtyK-O6A0dAh8ABoxaP2_hElNaSzFAWKMCOq6FvGZ6DNJ1WEEYrcYlF5d_mWKNKeSr8Fhz_mjT2w1YmR4DOOYTKcyIaK_6XMeomRoTqV87UInjFOLkPmDOLh2pUvjtjQz4bZcesCcMW7R7PKwuTnz4sJSkaOxhkACerzPY6ZW72dFwD7SQ.ZWU0ZWIzMTktMWRhNi00Mzg0LTllMzYtNzlmMDU3MjRmYTkx
# Only used by: py truck_simulator.py --mode mqtt
CERT_FILE = "certs/truck01.cert.pem"
KEY_FILE = "certs/truck01.private.key"
CA_FILE = "certs/AmazonRootCA1.pem"
