import subprocess
import pytest


@pytest.fixture
def git_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    # Initial commit so HEAD exists
    (tmp_path / "file.txt").write_text("hello world")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=tmp_path, check=True)
    # Stage new changes so tests have a diff to work with
    (tmp_path / "file.txt").write_text("hello world updated")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    return tmp_path
