import hashlib
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class GitContext:
    tree_sha: str
    parent_sha: Optional[str]
    author_name: str
    author_email: str
    fixed_timestamp: str  # "unix_epoch +tz"


class GitTool:
    def __init__(self, cwd: Optional[str] = None):
        self.cwd = cwd

    def _run(self, cmd: list[str], check: bool = True, env: Optional[dict] = None) -> str:
        result = subprocess.run(
            cmd,
            cwd=self.cwd,
            capture_output=True,
            text=True,
            env=env,
        )
        if check and result.returncode != 0:
            raise RuntimeError(f"git command failed: {' '.join(cmd)}\n{result.stderr}")
        return result.stdout.strip()

    def get_staged_diff(self) -> str:
        diff = self._run(["git", "diff", "--cached"])
        if not diff:
            raise RuntimeError("No staged changes found. Stage files with `git add` first.")
        return diff

    def get_context(self) -> GitContext:
        tree_sha = self._run(["git", "write-tree"])

        parent_result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=self.cwd,
            capture_output=True,
            text=True,
        )
        parent_sha = parent_result.stdout.strip() if parent_result.returncode == 0 else None

        author_name = self._run(["git", "config", "user.name"])
        author_email = self._run(["git", "config", "user.email"])

        now = datetime.now().astimezone()
        unix_ts = int(now.timestamp())
        tz_str = now.strftime("%z")
        fixed_timestamp = f"{unix_ts} {tz_str}"

        return GitContext(
            tree_sha=tree_sha,
            parent_sha=parent_sha,
            author_name=author_name,
            author_email=author_email,
            fixed_timestamp=fixed_timestamp,
        )

    def compute_hash(self, message: str, ctx: GitContext) -> str:
        obj = self._build_commit_object(message, ctx)
        return hashlib.sha1(obj).hexdigest()

    def commit(self, message: str, ctx: GitContext) -> str:
        env = os.environ.copy()
        env["GIT_COMMITTER_DATE"] = ctx.fixed_timestamp
        env["GIT_AUTHOR_DATE"] = ctx.fixed_timestamp
        self._run(
            ["git", "-c", "commit.gpgsign=false", "commit", "-m", message, f"--date={ctx.fixed_timestamp}"],
            env=env,
        )
        return self._run(["git", "rev-parse", "HEAD"])

    def _build_commit_object(self, message: str, ctx: GitContext) -> bytes:
        author_str = f"{ctx.author_name} <{ctx.author_email}> {ctx.fixed_timestamp}"
        lines = [f"tree {ctx.tree_sha}"]
        if ctx.parent_sha:
            lines.append(f"parent {ctx.parent_sha}")
        lines.append(f"author {author_str}")
        lines.append(f"committer {author_str}")
        lines.append("")
        lines.append(message)
        content = "\n".join(lines).encode() + b"\n"
        header = f"commit {len(content)}\0".encode()
        return header + content
