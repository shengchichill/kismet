import json
from unittest.mock import MagicMock, patch

from kismet.agent.tools.mac_sensor import (
    format_mining_omen,
    get_sensor_snapshot,
    is_prayer_pose_active,
    post_kismet_event,
    prayer_pose_status,
    wait_for_prayer_pose,
)


def test_get_sensor_snapshot_returns_empty_when_unavailable():
    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        assert get_sensor_snapshot() == {}


def test_get_sensor_snapshot_parses_json():
    response = MagicMock()
    response.status = 200
    response.read.return_value = json.dumps({"latestTrackpadPressure": 0.7}).encode()
    response.__enter__.return_value = response

    with patch("urllib.request.urlopen", return_value=response):
        assert get_sensor_snapshot() == {"latestTrackpadPressure": 0.7}


def test_post_kismet_event_sends_json_payload():
    response = MagicMock()
    response.close.return_value = None

    with patch("urllib.request.urlopen", return_value=response) as urlopen:
        post_kismet_event("MiningAttempt", "1/3 abc no omen", attempt=1, lucky=False)

    request = urlopen.call_args.args[0]
    payload = json.loads(request.data.decode())
    assert payload["source"] == "kismet"
    assert payload["eventName"] == "MiningAttempt"
    assert payload["summary"] == "1/3 abc no omen"
    assert payload["attempt"] == 1
    assert payload["lucky"] is False


def test_post_kismet_event_ignores_unavailable_agent():
    with patch("urllib.request.urlopen", side_effect=OSError("offline")):
        post_kismet_event("MiningEnd", "offline is fine")


def test_format_mining_omen_includes_sensor_and_camera_metadata():
    omen = format_mining_omen(
        {
            "latestTrackpadPressure": 0.72,
            "latestLidAngleDegrees": 63.2,
            "latestChassisImpactIntensity": 0.44,
            "latestPrayerPoseActive": True,
            "latestPrayerPoseConfidence": 0.88,
            "latestPrayerPoseHandCount": 2,
            "camera": {
                "authorizationStatus": "authorized",
                "devices": [{"localizedName": "FaceTime HD Camera"}],
            },
        }
    )

    assert "trackpad pressure 0.72" in omen
    assert "lid 63deg" in omen
    assert "impact 0.44" in omen
    assert "prayer pose 0.88" in omen
    assert "camera devices 1" in omen
    assert "camera authorized" in omen


def test_is_prayer_pose_active_requires_two_hands_and_confidence():
    assert is_prayer_pose_active(
        {
            "latestPrayerPoseActive": True,
            "latestPrayerPoseConfidence": 0.8,
            "latestPrayerPoseHandCount": 2,
        }
    ) is True
    assert is_prayer_pose_active(
        {
            "latestPrayerPoseActive": True,
            "latestPrayerPoseConfidence": 0.6,
            "latestPrayerPoseHandCount": 2,
        }
    ) is False
    assert is_prayer_pose_active(
        {
            "latestPrayerPoseActive": True,
            "latestPrayerPoseConfidence": 0.8,
            "latestPrayerPoseHandCount": 1,
        }
    ) is False


def test_prayer_pose_status_reports_camera_permission():
    assert "camera authorization is denied" in prayer_pose_status({"camera": {"authorizationStatus": "denied"}})


def test_prayer_pose_status_accepts_legacy_swift_authorized_value():
    status = prayer_pose_status(
        {
            "latestPrayerPoseHandCount": 1,
            "latestPrayerPoseConfidence": 0.4,
            "camera": {"authorizationStatus": "AVAuthorizationStatus(rawValue: 3)"},
        }
    )

    assert "camera authorization" not in status
    assert "prayer pose not confirmed" in status


def test_wait_for_prayer_pose_returns_confirmed_snapshot():
    snapshot = {
        "latestPrayerPoseActive": True,
        "latestPrayerPoseConfidence": 0.9,
        "latestPrayerPoseHandCount": 2,
    }
    with patch("kismet.agent.tools.mac_sensor.get_sensor_snapshot", return_value=snapshot):
        assert wait_for_prayer_pose(timeout=0) == (True, "prayer pose confirmed", snapshot)


def test_wait_for_prayer_pose_times_out_when_offline():
    with patch("kismet.agent.tools.mac_sensor.get_sensor_snapshot", return_value={}):
        ok, reason, snapshot = wait_for_prayer_pose(timeout=0)

    assert ok is False
    assert snapshot == {}
    assert "snapshot unavailable" in reason
