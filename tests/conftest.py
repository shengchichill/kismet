import subprocess
import pytest


@pytest.fixture
def git_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    (tmp_path / "file.txt").write_text("hello world")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    return tmp_path
