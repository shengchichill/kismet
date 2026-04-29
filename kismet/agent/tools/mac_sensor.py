from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def get_sensor_snapshot(timeout: float = 0.15) -> dict[str, Any]:
    """Fetch MacSensorAgent's local sensor snapshot.

    The integration is fail-open: if MacSensorAgent is not running, KISMET
    mining continues normally without waiting on sensors.
    """
    port = os.environ.get("MAC_SENSOR_AGENT_HOOK_PORT", "38661")
    url = os.environ.get("MAC_SENSOR_AGENT_SNAPSHOT_URL", f"http://127.0.0.1:{port}/snapshot")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return {}
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return {}


def format_mining_omen(snapshot: dict[str, Any]) -> str:
    """Convert MacSensorAgent snapshot data into a short ritual status."""
    if not snapshot:
        return ""

    parts: list[str] = []
    pressure = snapshot.get("latestTrackpadPressure")
    if isinstance(pressure, (int, float)) and pressure > 0:
        parts.append(f"trackpad pressure {pressure:.2f}")

    lid_angle = snapshot.get("latestLidAngleDegrees")
    if isinstance(lid_angle, (int, float)):
        parts.append(f"lid {lid_angle:.0f}deg")

    impact = snapshot.get("latestChassisImpactIntensity")
    if isinstance(impact, (int, float)):
        parts.append(f"impact {impact:.2f}")

    blow = snapshot.get("latestBlowIntensity")
    if isinstance(blow, (int, float)):
        parts.append(f"blow {blow:.2f}")

    camera = snapshot.get("camera") if isinstance(snapshot.get("camera"), dict) else {}
    devices = camera.get("devices") if isinstance(camera, dict) else []
    if isinstance(devices, list):
        parts.append(f"camera devices {len(devices)}")
    if isinstance(camera, dict):
        auth = camera.get("authorizationStatus")
        if isinstance(auth, str):
            parts.append(f"camera {auth}")

    return " | ".join(parts)
