import subprocess
import pytest
from kismet.agent.tools.git import GitTool, GitContext


def test_get_staged_diff(git_repo):
    tool = GitTool(cwd=str(git_repo))
    diff = tool.get_staged_diff()
    assert "hello world" in diff


def test_get_staged_diff_raises_if_nothing_staged(git_repo):
    subprocess.run(["git", "reset", "HEAD", "--", "."], cwd=git_repo, check=True)
    tool = GitTool(cwd=str(git_repo))
    with pytest.raises(RuntimeError, match="No staged changes"):
        tool.get_staged_diff()


def test_get_context_returns_git_context(git_repo):
    tool = GitTool(cwd=str(git_repo))
    ctx = tool.get_context()
    assert len(ctx.tree_sha) == 40
    assert ctx.parent_sha is not None  # fixture has initial commit
    assert ctx.author_name == "Test User"
    assert ctx.author_email == "test@example.com"
    assert " " in ctx.fixed_timestamp  # "unix_epoch +tz"


def test_compute_hash_is_deterministic(git_repo):
    tool = GitTool(cwd=str(git_repo))
    ctx = tool.get_context()
    h1 = tool.compute_hash("feat: hello", ctx)
    h2 = tool.compute_hash("feat: hello", ctx)
    assert h1 == h2
    assert len(h1) == 40


def test_compute_hash_differs_with_different_messages(git_repo):
    tool = GitTool(cwd=str(git_repo))
    ctx = tool.get_context()
    h1 = tool.compute_hash("feat: hello", ctx)
    h2 = tool.compute_hash("feat: world", ctx)
    assert h1 != h2


def test_commit_produces_matching_hash(git_repo):
    tool = GitTool(cwd=str(git_repo))
    ctx = tool.get_context()
    message = "feat: initial commit"
    predicted = tool.compute_hash(message, ctx)
    actual = tool.commit(message, ctx)
    assert actual == predicted
