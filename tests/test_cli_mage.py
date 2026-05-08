from unittest.mock import patch

from click.testing import CliRunner

from kismet.cli import cli


def _runner():
    return CliRunner()


def test_mage_start_gui_calls_ensure_running():
    with patch("kismet.config.load_config") as mock_cfg, \
         patch("kismet.presence.detect_mage_mode", return_value="gui"), \
         patch("kismet.presence.ensure_mage_running") as mock_ensure:
        mock_cfg.return_value.mage_mode = "auto"
        result = _runner().invoke(cli, ["mage", "start"])
    assert result.exit_code == 0
    mock_ensure.assert_called_once()
    assert "已啟動" in result.output


def test_mage_start_off_prints_warning():
    with patch("kismet.config.load_config") as mock_cfg, \
         patch("kismet.presence.detect_mage_mode", return_value="off"), \
         patch("kismet.presence.ensure_mage_running") as mock_ensure:
        mock_cfg.return_value.mage_mode = "off"
        result = _runner().invoke(cli, ["mage", "start"])
    assert result.exit_code == 0
    mock_ensure.assert_not_called()
    assert "無法在此環境啟動" in result.output


def test_mage_stop_calls_stop_mage():
    with patch("kismet.presence.stop_mage") as mock_stop:
        result = _runner().invoke(cli, ["mage", "stop"])
    assert result.exit_code == 0
    mock_stop.assert_called_once()


def test_mage_set_valid_state():
    with patch("kismet.presence.write_state") as mock_write:
        result = _runner().invoke(cli, ["mage", "set", "divine"])
    assert result.exit_code == 0
    mock_write.assert_called_once_with("divine")
    assert "divine" in result.output


def test_mage_set_invalid_state():
    result = _runner().invoke(cli, ["mage", "set", "badstate"])
    assert result.exit_code != 0
