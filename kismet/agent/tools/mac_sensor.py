from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any


def _base_url() -> str:
    port = os.environ.get("MAC_SENSOR_AGENT_HOOK_PORT", "38661")
    return os.environ.get("MAC_SENSOR_AGENT_BASE_URL", f"http://127.0.0.1:{port}")


def get_sensor_snapshot(timeout: float = 0.15) -> dict[str, Any]:
    """Fetch MacSensorAgent's local sensor snapshot.

    The integration is fail-open: if MacSensorAgent is not running, KISMET
    mining continues normally without waiting on sensors.
    """
    url = os.environ.get("MAC_SENSOR_AGENT_SNAPSHOT_URL", f"{_base_url()}/snapshot")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return {}
            return json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return {}


def post_kismet_event(event_name: str, summary: str = "", timeout: float = 0.15, **extra: Any) -> None:
    """Post KISMET status to MacSensorAgent's Vibe Island intake.

    This is also fail-open so KISMET never blocks when the local agent is off.
    """
    url = os.environ.get("MAC_SENSOR_AGENT_EVENTS_URL", f"{_base_url()}/events")
    payload = {
        "source": "kismet",
        "eventName": event_name,
        "summary": summary,
        **{key: value for key, value in extra.items() if value is not None},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-Mac-Sensor-Source": "kismet"},
        method="POST",
    )
    try:
        urllib.request.urlopen(request, timeout=timeout).close()
    except (OSError, urllib.error.URLError):
        return


def is_prayer_pose_active(snapshot: dict[str, Any], min_confidence: float = 0.7) -> bool:
    """Return True when MacSensorAgent sees a two-hand prayer pose."""
    return (
        snapshot.get("latestPrayerPoseActive") is True
        and isinstance(snapshot.get("latestPrayerPoseConfidence"), (int, float))
        and snapshot["latestPrayerPoseConfidence"] >= min_confidence
        and isinstance(snapshot.get("latestPrayerPoseHandCount"), int)
        and snapshot["latestPrayerPoseHandCount"] >= 2
    )


def prayer_pose_status(snapshot: dict[str, Any]) -> str:
    if not snapshot:
        return "MacSensorAgent snapshot unavailable; start MacSensorAgent and grant camera permission"

    camera = snapshot.get("camera") if isinstance(snapshot.get("camera"), dict) else {}
    auth = camera.get("authorizationStatus") if isinstance(camera, dict) else None
    if auth and not _camera_authorized(auth):
        return f"camera authorization is {auth}; grant camera permission to MacSensorAgent"

    hand_count = snapshot.get("latestPrayerPoseHandCount", 0)
    confidence = snapshot.get("latestPrayerPoseConfidence", 0)
    return f"prayer pose not confirmed; hands={hand_count} confidence={confidence}"


def _camera_authorized(auth: Any) -> bool:
    auth_text = str(auth)
    return auth_text == "authorized" or auth_text == "AVAuthorizationStatus(rawValue: 3)"


def wait_for_prayer_pose(timeout: float, poll_interval: float = 0.25) -> tuple[bool, str, dict[str, Any]]:
    """Poll MacSensorAgent until the user is holding a two-hand prayer pose."""
    deadline = time.monotonic() + max(0, timeout)
    last_snapshot: dict[str, Any] = {}
    while True:
        last_snapshot = get_sensor_snapshot()
        if is_prayer_pose_active(last_snapshot):
            return True, "prayer pose confirmed", last_snapshot

        if time.monotonic() >= deadline:
            return False, prayer_pose_status(last_snapshot), last_snapshot

        time.sleep(poll_interval)


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

    prayer_active = snapshot.get("latestPrayerPoseActive")
    prayer_confidence = snapshot.get("latestPrayerPoseConfidence")
    if prayer_active is True and isinstance(prayer_confidence, (int, float)):
        parts.append(f"prayer pose {prayer_confidence:.2f}")

    camera = snapshot.get("camera") if isinstance(snapshot.get("camera"), dict) else {}
    devices = camera.get("devices") if isinstance(camera, dict) else []
    if isinstance(devices, list):
        parts.append(f"camera devices {len(devices)}")
    if isinstance(camera, dict):
        auth = camera.get("authorizationStatus")
        if isinstance(auth, str):
            parts.append(f"camera {auth}")

    return " | ".join(parts)
