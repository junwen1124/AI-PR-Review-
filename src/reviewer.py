"""Build structured review prompts for the LLM."""

import json

SYSTEM_PROMPT = """You are an expert senior software engineer conducting a thorough code review.
Analyze the provided Pull Request diff and produce a structured review in the following format.

## Review Guidelines
1. **PR Summary**: Summarize what this PR changes, which files are affected, and the overall purpose.
2. **Risk Identification**: Identify potential bugs, security vulnerabilities, performance issues, missing error handling, race conditions, and other risks. For each risk, assign a severity level (🔴 Critical / 🟡 Medium / 🟢 Low).
3. **Review Suggestions**: Provide specific, actionable suggestions for improvement. Cover code style, logic optimization, naming, test coverage, and documentation where applicable.

## Output Format (MUST follow exactly)
Return your review in the following JSON structure:

{
  "summary": {
    "overview": "One paragraph summary of what this PR does",
    "files_changed": ["file1.py", "file2.py"],
    "key_changes": ["change 1", "change 2"]
  },
  "risks": [
    {
      "severity": "🔴 Critical",
      "file": "path/to/file.py",
      "line_hint": "approx line or code snippet",
      "category": "security/bug/performance/error-handling/race-condition",
      "description": "What the risk is",
      "suggestion": "How to fix it"
    }
  ],
  "suggestions": [
    {
      "file": "path/to/file.py",
      "type": "style/logic/naming/testing/documentation",
      "description": "What to improve",
      "suggestion": "Concrete code or approach suggestion"
    }
  ]
}

## Rules
- Only report real issues. Do not fabricate problems.
- If the diff is large, focus on the most important changes.
- For each risk, provide a concrete suggestion for fixing it.
- Keep suggestions actionable and specific.
- If there are no risks found, return an empty risks array.
- If there are no suggestions, return an empty suggestions array.
"""


def build_user_prompt(pr_info: dict, diff_text: str, max_diff_length: int = 15000) -> str:
    """Build the user prompt with PR metadata and diff."""
    # Truncate diff if too long to fit in context window
    diff = diff_text
    if len(diff) > max_diff_length:
        diff = diff[:max_diff_length] + "\n\n... [diff truncated, showing first {max_diff_length} chars]"

    files_summary = []
    for f in pr_info.get("files", []):
        files_summary.append(f"  - {f['filename']} ({f['status']}) +{f['additions']} -{f['deletions']}")

    prompt = f"""## PR Information
- **Title**: {pr_info.get('title', 'N/A')}
- **Author**: {pr_info.get('author', 'N/A')}
- **Base Branch**: {pr_info.get('base_branch', 'N/A')} → **Head Branch**: {pr_info.get('head_branch', 'N/A')}
- **Commits**: {pr_info.get('commits', 'N/A')}
- **Files Changed**: {pr_info.get('changed_files', 'N/A')}
- **Additions**: {pr_info.get('additions', 'N/A')} | **Deletions**: {pr_info.get('deletions', 'N/A')}

## PR Description
{pr_info.get('description', 'No description provided.')}

## Changed Files
{chr(10).join(files_summary)}

## Diff
```diff
{diff}
```

Please provide your structured code review following the output format specified."""
    return prompt


def build_review_prompt(pr_info: dict, diff_text: str) -> str:
    """Legacy wrapper — returns the user prompt. System prompt is handled by AIClient."""
    return build_user_prompt(pr_info, diff_text)


def parse_review_response(response_text: str) -> dict:
    """Parse the LLM JSON response into a structured review dict."""
    # Try to extract JSON block if wrapped in markdown
    text = response_text.strip()
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # If JSON parsing fails, return raw text as fallback
        return {"raw_review": response_text, "parse_error": True}
