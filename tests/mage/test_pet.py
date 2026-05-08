import json
import pytest
import kismet.mage.pet as pet_mod


@pytest.fixture
def pos_file(tmp_path, monkeypatch):
    f = tmp_path / "pos.json"
    monkeypatch.setattr(pet_mod, "POS_FILE", f)
    return f


def test_load_pos_missing(pos_file):
    assert pet_mod._load_pos() is None


def test_save_and_load_pos(pos_file):
    pet_mod._save_pos(100, 200)
    assert pet_mod._load_pos() == (100, 200)


def test_load_pos_bad_json(pos_file):
    pos_file.write_text("not json")
    assert pet_mod._load_pos() is None
