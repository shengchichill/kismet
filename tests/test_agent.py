from unittest.mock import MagicMock

from kismet.agent.agent import KismetAgent
from kismet.agent.session import KismetSession
from kismet.agent.tools.mine import MineResult, MineStatus


def _make_session() -> KismetSession:
    return KismetSession(
        diff="diff content",
        original_message="feat: add feature",
        current_message="feat: add feature",
        predicted_hash="3f7a404d8c2b1e5f",
        tree_sha="a" * 40,
        parent_sha="b" * 40,
        author_name="Test",
        author_email="t@t.com",
        fixed_timestamp="1714300000 +0800",
    )


def test_mine_and_commit_does_not_commit_when_prayer_pose_blocked():
    agent = KismetAgent.__new__(KismetAgent)
    agent.config = MagicMock(max_mine_attempts=10)
    agent.miner = MagicMock()
    agent.miner.mine.return_value = MineResult(MineStatus.BLOCKED, reason="no prayer")
    agent.renderer = MagicMock()
    agent.git = MagicMock()

    agent._mine_and_commit(_make_session(), targets=[])

    agent.git.commit.assert_not_called()
    agent.renderer.show_success.assert_not_called()
    agent.renderer.show_blessing.assert_not_called()
