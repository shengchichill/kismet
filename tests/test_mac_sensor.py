import json
from unittest.mock import MagicMock, patch

from kismet.agent.tools.mac_sensor import format_mining_omen, get_sensor_snapshot


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


def test_format_mining_omen_includes_sensor_and_camera_metadata():
    omen = format_mining_omen(
        {
            "latestTrackpadPressure": 0.72,
            "latestLidAngleDegrees": 63.2,
            "latestChassisImpactIntensity": 0.44,
            "camera": {
                "authorizationStatus": "authorized",
                "devices": [{"localizedName": "FaceTime HD Camera"}],
            },
        }
    )

    assert "trackpad pressure 0.72" in omen
    assert "lid 63deg" in omen
    assert "impact 0.44" in omen
    assert "camera devices 1" in omen
    assert "camera authorized" in omen
