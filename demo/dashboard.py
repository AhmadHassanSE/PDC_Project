"""Live map of the truck's trip, read from the Amazon Location tracker.

Usage:
    py dashboard.py      then open http://localhost:8000 in your browser
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import boto3

import config

PORT = 8000
geo = boto3.client("location", region_name=config.REGION)


def get_positions():
    """All positions stored for the truck in the last 24 hours, oldest first."""
    kwargs = {"TrackerName": config.TRACKER_NAME, "DeviceId": config.DEVICE_ID, "MaxResults": 100}
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


PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Live Delivery Tracker</title>
<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<style>
  html, body { margin: 0; height: 100%; font-family: system-ui, sans-serif; }
  #map { position: absolute; inset: 0; }
  #panel { position: absolute; top: 12px; left: 12px; z-index: 1; background: #fff; padding: 14px 16px;
           border-radius: 10px; box-shadow: 0 2px 12px rgba(0,0,0,.2); max-width: 300px; }
  #panel h1 { font-size: 18px; margin: 0 0 6px; }
  #panel .flow { font-size: 12px; color: #555; margin: 6px 0 10px; }
  #status { font-size: 14px; }
  #status.error { color: #b91c1c; }
  .truck { font-size: 30px; line-height: 1; }
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <h1>&#128666; Live Delivery Tracker</h1>
  <div>Device: <b>__DEVICE__</b></div>
  <div class="flow">Truck &rarr; AWS IoT Core (MQTT) &rarr; IoT rule &rarr; Amazon Location tracker &rarr; this map</div>
  <div id="status">Waiting for positions...</div>
  <label style="font-size:13px"><input type="checkbox" id="follow" checked> Follow truck</label>
</div>
<script>
const REGION = "__REGION__", API_KEY = __API_KEY__;
const START = __START__, END = __END__;

const style = API_KEY
  ? `https://maps.geo.${REGION}.amazonaws.com/v2/styles/Standard/descriptor?key=${API_KEY}`
  : { version: 8,
      sources: { osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
                        tileSize: 256, attribution: "&copy; OpenStreetMap contributors" } },
      layers: [{ id: "osm", type: "raster", source: "osm" }] };

const map = new maplibregl.Map({ container: "map", style, center: START, zoom: 13 });
map.addControl(new maplibregl.NavigationControl());
new maplibregl.Marker({ color: "#16a34a" }).setLngLat(START)
  .setPopup(new maplibregl.Popup().setText(__START_NAME__)).addTo(map);
new maplibregl.Marker({ color: "#dc2626" }).setLngLat(END)
  .setPopup(new maplibregl.Popup().setText(__END_NAME__)).addTo(map);

const truckEl = document.createElement("div");
truckEl.className = "truck";
truckEl.textContent = "\\u{1F69A}";
const truck = new maplibregl.Marker({ element: truckEl });
let truckShown = false;
const statusEl = document.getElementById("status");

function trail(coords) {
  return coords.length < 2
    ? { type: "FeatureCollection", features: [] }
    : { type: "Feature", geometry: { type: "LineString", coordinates: coords } };
}

async function refresh() {
  try {
    const data = await (await fetch("/api/positions")).json();
    if (data.error) throw new Error(data.error);
    const coords = data.positions.map(p => [p.lon, p.lat]);
    map.getSource("trail").setData(trail(coords));
    if (coords.length) {
      const last = coords[coords.length - 1];
      truck.setLngLat(last);
      if (!truckShown) { truck.addTo(map); truckShown = true; }
      if (document.getElementById("follow").checked) map.easeTo({ center: last, duration: 800 });
      const t = new Date(data.positions[data.positions.length - 1].time).toLocaleTimeString();
      statusEl.textContent = `${coords.length} positions stored · last at ${t}`;
    } else {
      if (truckShown) { truck.remove(); truckShown = false; }
      statusEl.textContent = "Waiting for positions...";
    }
    statusEl.className = "";
  } catch (e) {
    statusEl.textContent = "Error: " + e.message;
    statusEl.className = "error";
  }
}

map.on("load", () => {
  map.addSource("trail", { type: "geojson", data: trail([]) });
  map.addLayer({ id: "trail", type: "line", source: "trail",
                 layout: { "line-cap": "round", "line-join": "round" },
                 paint: { "line-color": "#2563eb", "line-width": 5 } });
  refresh();
  setInterval(refresh, 2000);
});
</script>
</body>
</html>
"""

PAGE = (PAGE
        .replace("__REGION__", config.REGION)
        .replace("__API_KEY__", json.dumps(config.MAP_API_KEY))
        .replace("__DEVICE__", config.DEVICE_ID)
        .replace("__START_NAME__", json.dumps(config.START_NAME))
        .replace("__END_NAME__", json.dumps(config.END_NAME))
        .replace("__START__", json.dumps([config.START[1], config.START[0]]))
        .replace("__END__", json.dumps([config.END[1], config.END[0]])))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/positions"):
            try:
                self._reply(200, "application/json", json.dumps({"positions": get_positions()}))
            except Exception as e:
                self._reply(500, "application/json", json.dumps({"error": str(e)}))
        elif self.path in ("/", "/index.html"):
            self._reply(200, "text/html; charset=utf-8", PAGE)
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
        print(f"Tracker currently holds {len(get_positions())} positions for {config.DEVICE_ID}")
    except Exception as e:
        raise SystemExit(f"Could not read the tracker: {e}")
    print(f"Dashboard running at http://localhost:{PORT}  (Ctrl+C to stop)")
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
