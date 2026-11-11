"""Live map of the fleet, read from the Amazon Location tracker.

Usage:
    py dashboard.py      then open http://localhost:8000 in your browser
"""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import boto3

import config
from truck_simulator import distance_m, get_route

PORT = 8000
PAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")
geo = boto3.client("location", region_name=config.REGION)


def get_positions(device_id):
    """All positions stored for one truck in the last 24 hours, oldest first."""
    kwargs = {"TrackerName": config.TRACKER_NAME, "DeviceId": device_id, "MaxResults": 100}
    positions = []
    while True:
        resp = geo.get_device_position_history(**kwargs)
        positions.extend(resp["DevicePositions"])
        if not resp.get("NextToken"):
            break
        kwargs["NextToken"] = resp["NextToken"]
    positions.sort(key=lambda p: p["SampleTime"])
    return [
        {"lon": p["Position"][0], "lat": p["Position"][1], "time": p["SampleTime"].isoformat()}
        for p in positions
    ]


def all_positions():
    """Positions for every truck in the fleet, read from the tracker in parallel."""
    ids = [t["id"] for t in config.FLEET]
    with ThreadPoolExecutor(len(ids)) as pool:
        return dict(zip(ids, pool.map(get_positions, ids)))


def build_fleet():
    """Delivery sheet and planned road route for every truck. Built once at startup."""
    trucks = []
    for t in config.FLEET:
        route = get_route(config.START, t["end"])
        trucks.append({
            **t,
            "end": [t["end"][1], t["end"][0]],  # the map uses [longitude, latitude]
            "route": [[lon, lat] for lat, lon in route],
            "routeKm": sum(distance_m(a, b) for a, b in zip(route, route[1:])) / 1000,
        })
    return json.dumps({
        "region": config.REGION, "apiKey": config.MAP_API_KEY, "tracker": config.TRACKER_NAME,
        "topic": config.TOPIC,
        "depot": {"name": config.START_NAME, "at": [config.START[1], config.START[0]]},
        "trucks": trucks,
    })


FLEET_JSON = ""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/positions"):
            try:
                self._reply(200, "application/json", json.dumps({"trucks": all_positions()}))
            except Exception as e:
                self._reply(500, "application/json", json.dumps({"error": str(e)}))
        elif self.path.startswith("/api/fleet"):
            self._reply(200, "application/json", FLEET_JSON)
        elif self.path in ("/", "/index.html"):
            with open(PAGE_FILE, encoding="utf-8") as fh:
                self._reply(200, "text/html; charset=utf-8", fh.read())
        else:
            self._reply(404, "text/plain", "Not found")

    def _reply(self, status, content_type, body):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass  # keep the console quiet


if __name__ == "__main__":
    try:
        for device_id, positions in all_positions().items():
            print(f"Tracker currently holds {len(positions)} positions for {device_id}")
    except Exception as e:
        raise SystemExit(f"Could not read the tracker: {e}")
    FLEET_JSON = build_fleet()
    print(f"Dashboard running at http://localhost:{PORT}  (Ctrl+C to stop)")
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
