"""Build structured review prompts for the LLM."""

import json

SYSTEM_PROMPT = """你是一位资深软件工程师，正在进行全面的代码审查。请分析提供的 Pull Request diff，并使用中文输出结构化的审查报告。

## 审查指南
1. **PR 变更总结**：总结本次 PR 改了什么、涉及哪些文件、整体目的是什么。
2. **风险代码识别**：识别潜在的 bug、安全漏洞、性能问题、错误处理缺失、竞态条件等风险。每个风险标注严重程度（🔴 严重 / 🟡 中等 / 🟢 轻微）。
3. **Review 建议**：提供具体、可操作的改进建议。涵盖代码风格、逻辑优化、命名、测试覆盖、文档等方面。

## 输出格式（必须严格遵守）
请返回以下 JSON 结构，所有文本内容使用中文：

{
  "summary": {
    "overview": "一段话概括本次 PR 做了什么",
    "files_changed": ["文件1.py", "文件2.py"],
    "key_changes": ["变更1", "变更2"]
  },
  "risks": [
    {
      "severity": "🔴 严重",
      "file": "路径/文件名.py",
      "line_hint": "大致行号或代码片段",
      "category": "security安全/bug缺陷/performance性能/error-handling错误处理/race-condition竞态条件",
      "description": "风险描述",
      "suggestion": "修复建议"
    }
  ],
  "suggestions": [
    {
      "file": "路径/文件名.py",
      "type": "style代码风格/logic逻辑优化/naming命名/testing测试/documentation文档",
      "description": "需要改进的地方",
      "suggestion": "具体的代码或方案建议"
    }
  ]
}

## 规则
- 只报告真实存在的问题，不要编造。
- 如果 diff 很大，聚焦最重要的变更。
- 每个风险都要给出具体的修复建议。
- 建议要具体可操作。
- 如果没有发现风险，返回空数组 []。
- 如果没有改进建议，返回空数组 []。
- 所有描述文字必须使用中文。
"""


def build_user_prompt(pr_info: dict, diff_text: str, max_diff_length: int = 15000) -> str:
    """Build the user prompt with PR metadata and diff."""
    diff = diff_text
    if len(diff) > max_diff_length:
        diff = diff[:max_diff_length] + f"\n\n... [diff 已截断，仅展示前 {max_diff_length} 字符]"

    files_summary = []
    for f in pr_info.get("files", []):
        files_summary.append(f"  - {f['filename']} ({f['status']}) +{f['additions']} -{f['deletions']}")

    prompt = f"""## PR 信息
- **标题**: {pr_info.get('title', 'N/A')}
- **作者**: {pr_info.get('author', 'N/A')}
- **源分支**: {pr_info.get('base_branch', 'N/A')} → **目标分支**: {pr_info.get('head_branch', 'N/A')}
- **提交数**: {pr_info.get('commits', 'N/A')}
- **变更文件数**: {pr_info.get('changed_files', 'N/A')}
- **新增行数**: {pr_info.get('additions', 'N/A')} | **删除行数**: {pr_info.get('deletions', 'N/A')}

## PR 描述
{pr_info.get('description', '无描述。')}

## 变更文件列表
{chr(10).join(files_summary)}

## Diff
```diff
{diff}
```

请按照指定的 JSON 输出格式，用中文提供结构化的代码审查报告。"""
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
