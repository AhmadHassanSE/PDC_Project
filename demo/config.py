# Shared settings for the Live Delivery Tracker demo.
# Edit the values in this file before running the scripts.

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

STEP_METERS = 80        # how far the truck moves per update (keep above 30, see the tracker's filtering)
SEND_INTERVAL = 1.0     # seconds between updates

# Optional: an Amazon Location API key for the map (guide, Part F).
# Leave empty to use OpenStreetMap tiles instead.
MAP_API_KEY = ""
# v1.public.eyJqdGkiOiJmYzhlNTg2Yi01YTYwLTQ3ZDUtYTNkNy1kNmViMDhmYzY4NmEifQOpBmz6smh_lHbJ-Ka8J1kdmKdWJCrT8wMi-gSGJljo4WaQ3ZWchqfvf0zzL9tlBctWvVBoA7DMw6mHYCstFIe6X_vTSQvUJJTcIPSvxq6gm_NaFzdd6V6Yel57yM-P6V3Lqm3YkP1r4zZOzxm-NtbjgyFBsY6e8i7L4vtyK-O6A0dAh8ABoxaP2_hElNaSzFAWKMCOq6FvGZ6DNJ1WEEYrcYlF5d_mWKNKeSr8Fhz_mjT2w1YmR4DOOYTKcyIaK_6XMeomRoTqV87UInjFOLkPmDOLh2pUvjtjQz4bZcesCcMW7R7PKwuTnz4sJSkaOxhkACerzPY6ZW72dFwD7SQ.ZWU0ZWIzMTktMWRhNi00Mzg0LTllMzYtNzlmMDU3MjRmYTkx
# Only used by: py truck_simulator.py --mode mqtt
CERT_FILE = "certs/truck01.cert.pem"
KEY_FILE = "certs/truck01.private.key"
CA_FILE = "certs/AmazonRootCA1.pem"
