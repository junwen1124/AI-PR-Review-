"""Tests for GitHub PR URL parsing and client."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from github_client import parse_pr_url


class TestParsePRUrl(unittest.TestCase):
    """Test PR URL parsing."""

    def test_standard_url(self):
        owner, repo, num = parse_pr_url("https://github.com/owner/repo/pull/123")
        self.assertEqual(owner, "owner")
        self.assertEqual(repo, "repo")
        self.assertEqual(num, 123)

    def test_url_with_trailing_slash(self):
        owner, repo, num = parse_pr_url("https://github.com/owner/repo/pull/123/")
        self.assertEqual(owner, "owner")
        self.assertEqual(repo, "repo")
        self.assertEqual(num, 123)

    def test_url_with_git_suffix(self):
        owner, repo, num = parse_pr_url("https://github.com/owner/repo.git/pull/123")
        self.assertEqual(owner, "owner")
        self.assertEqual(repo, "repo")
        self.assertEqual(num, 123)

    def test_url_with_dashes_and_dots(self):
        owner, repo, num = parse_pr_url("https://github.com/my-org/my.repo/pull/999")
        self.assertEqual(owner, "my-org")
        self.assertEqual(repo, "my.repo")
        self.assertEqual(num, 999)

    def test_url_with_underscore(self):
        owner, repo, num = parse_pr_url("https://github.com/my_org/my_repo/pull/42")
        self.assertEqual(owner, "my_org")
        self.assertEqual(repo, "my_repo")
        self.assertEqual(num, 42)

    def test_large_pr_number(self):
        owner, repo, num = parse_pr_url("https://github.com/owner/repo/pull/12345678")
        self.assertEqual(num, 12345678)

    def test_invalid_url_no_pull(self):
        with self.assertRaises(ValueError):
            parse_pr_url("https://github.com/owner/repo")

    def test_invalid_url_issues(self):
        with self.assertRaises(ValueError):
            parse_pr_url("https://github.com/owner/repo/issues/123")

    def test_invalid_url_empty(self):
        with self.assertRaises(ValueError):
            parse_pr_url("")

    def test_invalid_url_not_github(self):
        with self.assertRaises(ValueError):
            parse_pr_url("https://gitlab.com/owner/repo/pull/123")


class TestReviewPrompt(unittest.TestCase):
    """Test prompt building."""

    def test_build_user_prompt_basic(self):
        from reviewer import build_user_prompt
        pr_info = {
            "title": "Fix bug",
            "author": "dev",
            "base_branch": "main",
            "head_branch": "fix/bug",
            "commits": 1,
            "additions": 10,
            "deletions": 5,
            "changed_files": 2,
            "description": "Fixes a critical bug.",
            "files": [
                {"filename": "app.py", "status": "modified", "additions": 8, "deletions": 3},
                {"filename": "test.py", "status": "added", "additions": 2, "deletions": 2},
            ],
        }
        diff = "--- a/app.py\n+++ b/app.py\n@@ -1,3 +1,8 @@\n import os\n+import sys\n"
        prompt = build_user_prompt(pr_info, diff)
        self.assertIn("Fix bug", prompt)
        self.assertIn("dev", prompt)
        self.assertIn("app.py", prompt)
        self.assertIn("import sys", prompt)
        self.assertIn("PR 信息", prompt)
        self.assertIn("变更文件列表", prompt)
        self.assertIn("Diff", prompt)

    def test_build_user_prompt_truncation(self):
        from reviewer import build_user_prompt
        pr_info = {"title": "T", "author": "A", "description": "", "files": [],
                   "base_branch": "main", "head_branch": "feat",
                   "commits": 1, "additions": 0, "deletions": 0, "changed_files": 0}
        long_diff = "x" * 20000
        prompt = build_user_prompt(pr_info, long_diff, max_diff_length=100)
        self.assertIn("截断", prompt)


class TestParseReviewResponse(unittest.TestCase):
    """Test review response parsing."""

    def test_parse_valid_json(self):
        from reviewer import parse_review_response
        response = '{"summary": {"overview": "test"}, "risks": [], "suggestions": []}'
        result = parse_review_response(response)
        self.assertEqual(result["summary"]["overview"], "test")
        self.assertEqual(result["risks"], [])
        self.assertEqual(result["suggestions"], [])

    def test_parse_json_in_markdown(self):
        from reviewer import parse_review_response
        response = '''```json
{"summary": {"overview": "test"}, "risks": [], "suggestions": []}
```'''
        result = parse_review_response(response)
        self.assertEqual(result["summary"]["overview"], "test")

    def test_parse_invalid_json(self):
        from reviewer import parse_review_response
        response = "This is not JSON at all"
        result = parse_review_response(response)
        self.assertTrue(result.get("parse_error"))
        self.assertIn("raw_review", result)


class TestFormatter(unittest.TestCase):
    """Test output formatter."""

    def test_format_plain_review(self):
        from formatter import format_review
        pr_info = {"title": "Test PR", "author": "dev",
                   "changed_files": 1, "additions": 5, "deletions": 3,
                   "commits": 1}
        review_text = '{"summary": {"overview": "A test PR"}, "risks": [], "suggestions": []}'
        output = format_review(pr_info, review_text, use_color=False)
        self.assertIn("AI PR Review Report", output)
        self.assertIn("Test PR", output)
        self.assertIn("A test PR", output)
        self.assertIn("End of Review", output)

    def test_format_with_risks(self):
        from formatter import format_review
        pr_info = {"title": "Test", "author": "dev",
                   "changed_files": 1, "additions": 1, "deletions": 1,
                   "commits": 1}
        review_text = """{
            "summary": {"overview": "test"},
            "risks": [{
                "severity": "Critical",
                "file": "app.py",
                "category": "bug",
                "description": "A serious bug",
                "suggestion": "Fix it"
            }],
            "suggestions": []
        }"""
        output = format_review(pr_info, review_text, use_color=False)
        self.assertIn("Risk Identification", output)
        self.assertIn("Critical", output)
        self.assertIn("A serious bug", output)

    def test_format_with_suggestions(self):
        from formatter import format_review
        pr_info = {"title": "Test", "author": "dev",
                   "changed_files": 1, "additions": 1, "deletions": 1,
                   "commits": 1}
        review_text = """{
            "summary": {"overview": "test"},
            "risks": [],
            "suggestions": [{
                "file": "app.py",
                "type": "style",
                "description": "Improve naming",
                "suggestion": "Use better names"
            }]
        }"""
        output = format_review(pr_info, review_text, use_color=False)
        self.assertIn("Review Suggestions", output)
        self.assertIn("Improve naming", output)


if __name__ == "__main__":
    unittest.main()
