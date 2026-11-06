"""Saves the truck's road route from Amazon Location Routes to route.json for make_video.py."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "demo"))
import config  # noqa: E402
from truck_simulator import get_route, resample  # noqa: E402

points = resample(get_route(), config.STEP_METERS)
with open(os.path.join(HERE, "route.json"), "w") as fh:
    json.dump(points, fh)
print(f"Saved {len(points)} points to route.json")
