import json
from unittest.mock import MagicMock, patch

from kismet.agent.tools.mac_sensor import (
    format_mining_omen,
    get_sensor_snapshot,
    is_forbidden_kuai_kuai_offering,
    is_green_kuai_kuai_offering,
    is_prayer_pose_active,
    is_ritual_music_accepted,
    is_ritual_spell_accepted,
    post_kismet_event,
    prayer_pose_status,
    ritual_music_status,
    ritual_spell_status,
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
            "latestKuaiKuaiDetected": True,
            "latestKuaiKuaiColor": "green",
            "latestKuaiKuaiConfidence": 0.78,
            "ritualMusic": {
                "accepted": True,
                "reason": "matched ritual song: Queen - Don't Stop Me Now",
                "matchedRule": "Queen - Don't Stop Me Now",
            },
            "ritualSpell": {
                "accepted": True,
                "phrase": "kismet open",
                "reason": "recognized ritual spell: kismet open",
            },
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
    assert "Kuai Kuai green 0.78" in omen
    assert "ritual music Queen - Don't Stop Me Now" in omen
    assert "ritual spell kismet open" in omen
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
            "latestPrayerPoseConfidence": 0.65,
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


def test_green_kuai_kuai_opens_ritual_gate_without_prayer_pose():
    snapshot = {
        "latestPrayerPoseActive": False,
        "latestPrayerPoseConfidence": 0.0,
        "latestPrayerPoseHandCount": 0,
        "latestKuaiKuaiDetected": True,
        "latestKuaiKuaiColor": "green",
        "latestKuaiKuaiConfidence": 0.7,
    }

    assert is_green_kuai_kuai_offering(snapshot) is True
    assert is_prayer_pose_active(snapshot) is True


def test_ritual_music_opens_ritual_gate_without_camera():
    snapshot = {
        "latestPrayerPoseActive": False,
        "latestPrayerPoseConfidence": 0.0,
        "latestPrayerPoseHandCount": 0,
        "ritualMusic": {
            "accepted": True,
            "reason": "matched ritual song: Darude - Sandstorm",
            "matchedRule": "Darude - Sandstorm",
        },
    }

    assert is_ritual_music_accepted(snapshot) is True
    assert is_prayer_pose_active(snapshot) is True
    assert ritual_music_status(snapshot) == "matched ritual song: Darude - Sandstorm"
    assert prayer_pose_status(snapshot) == "matched ritual song: Darude - Sandstorm"


def test_ritual_spell_opens_ritual_gate_without_camera():
    snapshot = {
        "latestPrayerPoseActive": False,
        "latestPrayerPoseConfidence": 0.0,
        "latestPrayerPoseHandCount": 0,
        "ritualSpell": {
            "accepted": True,
            "phrase": "unlock ritual",
            "reason": "recognized ritual spell: unlock ritual",
        },
    }

    assert is_ritual_spell_accepted(snapshot) is True
    assert is_prayer_pose_active(snapshot) is True
    assert ritual_spell_status(snapshot) == "recognized ritual spell: unlock ritual"
    assert prayer_pose_status(snapshot) == "recognized ritual spell: unlock ritual"


def test_non_green_kuai_kuai_is_status_only():
    snapshot = {
        "latestKuaiKuaiDetected": True,
        "latestKuaiKuaiColor": "yellow",
        "latestKuaiKuaiConfidence": 0.74,
    }

    assert is_forbidden_kuai_kuai_offering(snapshot) is True
    assert is_prayer_pose_active(snapshot) is False
    assert "forbidden yellow Kuai Kuai" in prayer_pose_status(snapshot)
    assert "not blocking" in prayer_pose_status(snapshot)


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


def test_wait_for_prayer_pose_accepts_green_kuai_kuai():
    snapshot = {
        "latestKuaiKuaiDetected": True,
        "latestKuaiKuaiColor": "green",
        "latestKuaiKuaiConfidence": 0.9,
    }
    with patch("kismet.agent.tools.mac_sensor.get_sensor_snapshot", return_value=snapshot):
        assert wait_for_prayer_pose(timeout=0) == (True, "green Kuai Kuai offering confirmed", snapshot)


def test_wait_for_prayer_pose_accepts_ritual_music():
    snapshot = {
        "ritualMusic": {
            "accepted": True,
            "reason": "matched ritual song: Rick Astley - Never Gonna Give You Up",
            "matchedRule": "Rick Astley - Never Gonna Give You Up",
        }
    }
    with patch("kismet.agent.tools.mac_sensor.get_sensor_snapshot", return_value=snapshot):
        assert wait_for_prayer_pose(timeout=0) == (
            True,
            "matched ritual song: Rick Astley - Never Gonna Give You Up",
            snapshot,
        )


def test_wait_for_prayer_pose_accepts_ritual_spell():
    snapshot = {
        "ritualSpell": {
            "accepted": True,
            "phrase": "bless this hash",
            "reason": "recognized ritual spell: bless this hash",
        }
    }
    with patch("kismet.agent.tools.mac_sensor.get_sensor_snapshot", return_value=snapshot):
        assert wait_for_prayer_pose(timeout=0) == (
            True,
            "recognized ritual spell: bless this hash",
            snapshot,
        )


def test_wait_for_prayer_pose_does_not_veto_accepted_gate_with_forbidden_kuai_kuai():
    snapshot = {
        "latestKuaiKuaiDetected": True,
        "latestKuaiKuaiColor": "red",
        "latestKuaiKuaiConfidence": 0.82,
        "ritualSpell": {
            "accepted": True,
            "phrase": "unlock ritual",
            "reason": "recognized ritual spell: unlock ritual",
        },
    }
    with patch("kismet.agent.tools.mac_sensor.get_sensor_snapshot", return_value=snapshot):
        ok, reason, result_snapshot = wait_for_prayer_pose(timeout=15)

    assert ok is True
    assert result_snapshot == snapshot
    assert reason == "recognized ritual spell: unlock ritual"


def test_wait_for_prayer_pose_times_out_with_forbidden_kuai_kuai_when_no_gate_passes():
    snapshot = {
        "latestKuaiKuaiDetected": True,
        "latestKuaiKuaiColor": "red",
        "latestKuaiKuaiConfidence": 0.82,
    }
    with patch("kismet.agent.tools.mac_sensor.get_sensor_snapshot", return_value=snapshot):
        ok, reason, result_snapshot = wait_for_prayer_pose(timeout=0)

    assert ok is False
    assert result_snapshot == snapshot
    assert "forbidden red Kuai Kuai" in reason
    assert "not blocking" in reason


def test_wait_for_prayer_pose_times_out_when_offline():
    with patch("kismet.agent.tools.mac_sensor.get_sensor_snapshot", return_value={}):
        ok, reason, snapshot = wait_for_prayer_pose(timeout=0)

    assert ok is False
    assert snapshot == {}
    assert "snapshot unavailable" in reason


def test_wait_for_prayer_pose_keeps_last_non_empty_snapshot_for_timeout_reason():
    snapshots = [
        {"latestPrayerPoseActive": False, "latestPrayerPoseConfidence": 0.4, "latestPrayerPoseHandCount": 1},
        {},
    ]
    with patch("kismet.agent.tools.mac_sensor.get_sensor_snapshot", side_effect=snapshots):
        ok, reason, snapshot = wait_for_prayer_pose(timeout=0.01, poll_interval=0.02)

    assert ok is False
    assert snapshot == snapshots[0]
    assert "hands=1" in reason
