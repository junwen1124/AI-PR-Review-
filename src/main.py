"""AI PR Review Assistant - CLI entry point.

Usage:
    python -m src.main --pr https://github.com/owner/repo/pull/123
    python -m src.main --pr https://github.com/owner/repo/pull/123 --output review.md
"""

import argparse
import sys
import os
from dotenv import load_dotenv

load_dotenv()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aipr-review",
        description="AI PR Review Assistant - Automated code review for GitHub Pull Requests",
    )
    parser.add_argument(
        "--pr", "-p",
        type=str,
        required=True,
        help="GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: print to stdout)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="LLM model name (default: deepseek-chat)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="LLM API base URL (default: https://api.deepseek.com/v1)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Max tokens for AI response (default: 4096)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    parser.add_argument(
        "--max-diff-length",
        type=int,
        default=15000,
        help="Max diff characters sent to model (default: 15000)",
    )
    return parser


def check_env() -> tuple[str, str]:
    """Check required environment variables. Returns (github_token, ai_api_key)."""
    github_token = os.getenv("GITHUB_TOKEN")
    ai_api_key = os.getenv("AI_API_KEY") or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not github_token:
        print("[ERROR] GITHUB_TOKEN environment variable not set.")
        print("  Create a token at: https://github.com/settings/tokens")
        print("  Required scope: repo (for private repos) or public_repo")
        sys.exit(1)

    if not ai_api_key:
        print("[ERROR] AI_API_KEY (or DEEPSEEK_API_KEY / OPENAI_API_KEY) environment variable not set.")
        print("  DeepSeek: https://platform.deepseek.com/api_keys")
        print("  OpenAI: https://platform.openai.com/api-keys")
        sys.exit(1)

    return github_token, ai_api_key


def main():
    parser = build_parser()
    args = parser.parse_args()

    print("=" * 55)
    print("  AI PR Review Assistant")
    print("=" * 55)

    # Check environment
    github_token, ai_api_key = check_env()

    print(f"  PR: {args.pr}")
    print(f"  Model: {args.model or os.getenv('AI_MODEL', 'deepseek-chat')}")
    print()

    # Import modules (lazy to avoid import errors when just checking env)
    from github_client import GitHubPRClient
    from reviewer import build_user_prompt
    from ai_client import AIClient
    from formatter import format_review

    # Step 1: Fetch PR from GitHub
    print("[1/3] Fetching PR from GitHub...")
    gh = GitHubPRClient(token=github_token)
    try:
        pr_info = gh.get_pr_info_from_url(args.pr)
        diff_text = gh.get_full_diff_from_url(args.pr)
    except Exception as e:
        print(f"[ERROR] Failed to fetch PR: {e}")
        sys.exit(1)

    print(f"  Title: {pr_info['title']}")
    print(f"  Author: {pr_info['author']}")
    print(f"  Files: {pr_info['changed_files']} (+{pr_info['additions']} -{pr_info['deletions']})")

    # Step 2: Build review prompt
    print("[2/3] Building review prompt...")
    prompt = build_user_prompt(pr_info, diff_text, max_diff_length=args.max_diff_length)

    # Step 3: Call AI API
    print("[3/3] Sending to AI model for review...")
    ai_model = args.model or os.getenv("AI_MODEL", "deepseek-chat")
    ai_base_url = args.base_url or os.getenv("AI_BASE_URL", "https://api.deepseek.com/v1")
    ai = AIClient(api_key=ai_api_key, model=ai_model, base_url=ai_base_url)

    try:
        review_text = ai.review(prompt, max_tokens=args.max_tokens)
    except Exception as e:
        print(f"[ERROR] AI API call failed: {e}")
        sys.exit(1)

    # Format and output
    output = format_review(pr_info, review_text, use_color=not args.no_color)

    if args.output:
        # Strip Rich markup for file output
        plain_output = format_review(pr_info, review_text, use_color=False)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(plain_output)
        print(f"\n[OK] Review saved to: {args.output}")
        # Still print colored to terminal
        print()
        print(output)
    else:
        print()
        print(output)


if __name__ == "__main__":
    main()
