"""GitHub API client for fetching PR details and diff."""

import re
import os
from github import Github, GithubException
from dotenv import load_dotenv

load_dotenv()


def parse_pr_url(url: str) -> tuple[str, str, int]:
    """Parse a GitHub PR URL into (owner, repo, pr_number)."""
    pattern = r"github\.com[:/]([^/]+)/([^/]+)/pull/(\d+)"
    match = re.search(pattern, url)
    if not match:
        raise ValueError(f"Invalid GitHub PR URL: {url}")
    return match.group(1), match.group(2).removesuffix(".git"), int(match.group(3))


class GitHubPRClient:
    """Fetches PR details and diff from GitHub API."""

    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token required. Set GITHUB_TOKEN env var or pass token.")
        self._gh = Github(self.token)

    def get_pr(self, owner: str, repo: str, pr_number: int):
        """Fetch the PR object."""
        repo_obj = self._gh.get_repo(f"{owner}/{repo}")
        return repo_obj.get_pull(pr_number)

    def get_pr_from_url(self, url: str):
        """Fetch PR from a GitHub PR URL."""
        owner, repo, pr_number = parse_pr_url(url)
        return self.get_pr(owner, repo, pr_number)

    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Get the unified diff of a PR."""
        pr = self.get_pr(owner, repo, pr_number)
        # PyGithub returns diff as bytes, decode to string
        diff = pr.get_files()
        return self._format_diff(diff)

    def get_pr_diff_from_url(self, url: str) -> str:
        """Get PR diff from a URL."""
        owner, repo, pr_number = parse_pr_url(url)
        return self.get_pr_diff(owner, repo, pr_number)

    def get_pr_info(self, owner: str, repo: str, pr_number: int) -> dict:
        """Get PR metadata and file list."""
        pr = self.get_pr(owner, repo, pr_number)
        files = pr.get_files()
        file_list = []
        for f in files:
            file_list.append({
                "filename": f.filename,
                "status": f.status,
                "additions": f.additions,
                "deletions": f.deletions,
                "changes": f.changes,
                "patch": f.patch or "",
            })
        return {
            "title": pr.title,
            "description": pr.body or "",
            "author": pr.user.login if pr.user else "unknown",
            "base_branch": pr.base.ref,
            "head_branch": pr.head.ref,
            "commits": pr.commits,
            "additions": pr.additions,
            "deletions": pr.deletions,
            "changed_files": pr.changed_files,
            "files": file_list,
            "url": pr.html_url,
        }

    def get_pr_info_from_url(self, url: str) -> dict:
        """Get PR info from a URL."""
        owner, repo, pr_number = parse_pr_url(url)
        return self.get_pr_info(owner, repo, pr_number)

    def get_full_diff_text(self, owner: str, repo: str, pr_number: int) -> str:
        """Get the complete raw diff text from a PR."""
        pr = self.get_pr(owner, repo, pr_number)
        # Build diff from individual file patches for more control
        files = pr.get_files()
        parts = []
        for f in files:
            if f.patch:
                parts.append(f"--- a/{f.filename}\n+++ b/{f.filename}\n{f.patch}")
            else:
                parts.append(f"# File: {f.filename} (status: {f.status}, binary or too large)")
        return "\n".join(parts)

    def get_full_diff_from_url(self, url: str) -> str:
        """Get full diff text from a URL."""
        owner, repo, pr_number = parse_pr_url(url)
        return self.get_full_diff_text(owner, repo, pr_number)

    @staticmethod
    def _format_diff(files) -> str:
        """Format file list into a readable diff summary."""
        lines = []
        for f in files:
            lines.append(f"### {f.filename} ({f.status}) +{f.additions} -{f.deletions}")
            if f.patch:
                lines.append(f.patch)
            lines.append("")
        return "\n".join(lines)
