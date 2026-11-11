"""Simulated delivery fleet: every truck in config.FLEET drives its route and sends its GPS position to AWS IoT Core.

Usage:
    py truck_simulator.py               publish over HTTPS using the keys in aws_credentials
    py truck_simulator.py --mode mqtt   connect over MQTT as the IoT thing (one connection relays every truck)
    py truck_simulator.py --keep        keep the previous trips instead of clearing it first
"""
import argparse
import json
import math
import os
import sys
import threading
import time
from datetime import datetime, timezone

import boto3

import config

HERE = os.path.dirname(os.path.abspath(__file__))


def distance_m(a, b):
    """Distance in metres between two (lat, lon) points."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * 6371000 * math.asin(math.sqrt(h))


def get_route(start=config.START, end=config.END):
    """Ask Amazon Location Routes for a road route; fall back to a straight line."""
    try:
        routes = boto3.client("geo-routes", region_name=config.REGION)
        resp = routes.calculate_routes(
            Origin=[start[1], start[0]],  # AWS uses [longitude, latitude]
            Destination=[end[1], end[0]],
            TravelMode="Car",
            LegGeometryFormat="Simple",
        )
        line = []
        for leg in resp["Routes"][0]["Legs"]:
            line.extend(leg["Geometry"]["LineString"])
        print(f"Road route from Amazon Location Routes: {len(line)} points")
        # The router snaps start/end to the nearest road it knows, so join the real points on.
        return [start] + [(lat, lon) for lon, lat in line] + [end]
    except Exception as e:
        print(f"Could not get a road route ({e})")
        print("Using a straight line instead.")
        return [start, end]


def resample(route, step):
    """Return points spaced about `step` metres apart along the route."""
    out = [route[0]]
    carry = 0.0  # distance covered since the last emitted point
    for a, b in zip(route, route[1:]):
        seg = distance_m(a, b)
        pos = step - carry
        while pos <= seg:
            t = pos / seg
            out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
            pos += step
        carry = seg - (pos - step)
    if out[-1] != route[-1]:
        out.append(route[-1])
    return out


def iot_endpoint():
    iot = boto3.client("iot", region_name=config.REGION)
    return iot.describe_endpoint(endpointType="iot:Data-ATS")["endpointAddress"]


def https_publisher():
    endpoint = iot_endpoint()
    data = boto3.client("iot-data", region_name=config.REGION, endpoint_url=f"https://{endpoint}")
    print(f"Publishing over HTTPS to {endpoint}")

    def publish(msg):
        data.publish(topic=config.TOPIC, qos=1, payload=json.dumps(msg))

    return publish


def mqtt_publisher():
    import paho.mqtt.client as mqtt

    endpoint = iot_endpoint()
    connected = threading.Event()

    def on_connect(client, userdata, flags, reason_code, properties):
        print(f"MQTT connect result: {reason_code}")
        if not reason_code.is_failure:
            connected.set()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=config.DEVICE_ID)
    client.on_connect = on_connect
    client.tls_set(
        ca_certs=os.path.join(HERE, config.CA_FILE),
        certfile=os.path.join(HERE, config.CERT_FILE),
        keyfile=os.path.join(HERE, config.KEY_FILE),
    )
    client.connect(endpoint, 8883)
    client.loop_start()
    if not connected.wait(10):
        sys.exit("Could not connect over MQTT. Check the files in certs/, the thing's policy, "
                 "and that the policy is attached to the certificate.")
    print(f"Connected over MQTT to {endpoint} as {config.DEVICE_ID}")

    def publish(msg):
        client.publish(config.TOPIC, json.dumps(msg), qos=1).wait_for_publish(timeout=10)

    return publish


def drive(truck, points, publish, wait):
    """One truck's trip: leave after `wait` seconds, then publish a position, wait, repeat."""
    time.sleep(wait)
    print(f"{truck['id']} left for {truck['destination']}")
    for i, (lat, lon) in enumerate(points, 1):
        msg = {
            "deviceId": truck["id"],
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        publish(msg)
        print(f"{truck['id']} [{i}/{len(points)}] sent {msg['latitude']}, {msg['longitude']}")
        time.sleep(config.SEND_INTERVAL)
    print(f"{truck['id']} arrived at {truck['destination']}")


def main():
    parser = argparse.ArgumentParser(description="Simulated delivery fleet")
    parser.add_argument("--mode", choices=["https", "mqtt"], default="https")
    parser.add_argument("--keep", action="store_true", help="don't clear the previous trips")
    args = parser.parse_args()

    if not args.keep:
        try:
            geo = boto3.client("location", region_name=config.REGION)
            geo.batch_delete_device_position_history(
                TrackerName=config.TRACKER_NAME, DeviceIds=[t["id"] for t in config.FLEET])
            print("Cleared the previous trips from the tracker")
        except Exception as e:
            print(f"Could not clear the previous trips ({e})")

    trips = []
    for truck in config.FLEET:
        points = resample(get_route(config.START, truck["end"]), config.STEP_METERS)
        km = sum(distance_m(a, b) for a, b in zip(points, points[1:])) / 1000
        print(f"{truck['id']} to {truck['destination']}: {km:.1f} km in {len(points)} updates, about "
              f"{len(points) * config.SEND_INTERVAL / 60:.1f} minutes")
        trips.append((truck, points))

    publish = mqtt_publisher() if args.mode == "mqtt" else https_publisher()

    # One thread per truck, so every truck reports once a second like independent devices would.
    threads = [threading.Thread(target=drive, args=(truck, points, publish, i * config.DEPART_GAP), daemon=True)
               for i, (truck, points) in enumerate(trips)]
    for t in threads:
        t.start()
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(0.2)
        print("All trucks have arrived")
    except KeyboardInterrupt:
        print("\nStopped")


if __name__ == "__main__":
    main()
