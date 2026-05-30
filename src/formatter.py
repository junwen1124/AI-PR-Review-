"""Format review output for CLI display using Rich."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich import box


def format_review(pr_info: dict, review_text: str, use_color: bool = True) -> str:
    """Format the review output. Returns plain text when use_color=False."""
    if not use_color:
        return _format_plain(pr_info, review_text)

    console = Console(record=True, width=100)
    _render_rich(console, pr_info, review_text)
    return console.export_text()


def _render_rich(console: Console, pr_info: dict, review_text: str):
    """Render the review using Rich formatting."""
    # Header
    console.print()
    console.rule("[bold blue]AI PR Review Report[/bold blue]")
    console.print()

    # PR Info panel
    info_text = (
        f"[bold]Title:[/bold] {pr_info.get('title', 'N/A')}\n"
        f"[bold]Author:[/bold] {pr_info.get('author', 'N/A')}\n"
        f"[bold]Files:[/bold] {pr_info.get('changed_files', 'N/A')} "
        f"(+{pr_info.get('additions', 'N/A')} -{pr_info.get('deletions', 'N/A')})\n"
        f"[bold]Commits:[/bold] {pr_info.get('commits', 'N/A')}"
    )
    console.print(Panel(info_text, title="PR Info", border_style="blue"))

    # Try to parse structured JSON, fall back to raw markdown
    try:
        try:
            from .reviewer import parse_review_response
        except ImportError:
            from reviewer import parse_review_response
        review_data = parse_review_response(review_text)

        if review_data.get("parse_error"):
            # Fall back to raw output
            console.print(Markdown(review_text))
            return

        # Summary section
        summary = review_data.get("summary", {})
        console.rule("[bold green]Summary[/bold green]")
        console.print(f"[bold]Overview:[/bold] {summary.get('overview', 'N/A')}")
        console.print()
        if summary.get("key_changes"):
            console.print("[bold]Key Changes:[/bold]")
            for change in summary["key_changes"]:
                console.print(f"  • {change}")
        console.print()

        # Risks section
        risks = review_data.get("risks", [])
        console.rule("[bold red]Risk Identification[/bold red]")
        if not risks:
            console.print("[green]No significant risks identified.[/green]")
        else:
            for i, risk in enumerate(risks, 1):
                severity = risk.get("severity", "N/A")
                severity_style = _severity_style(severity)
                console.print(f"[bold]{i}. [{severity_style}]{severity}[/{severity_style}][/bold] "
                              f"[bold]{risk.get('category', '')}[/bold] - "
                              f"{risk.get('file', '')}")
                console.print(f"   {risk.get('description', '')}")
                if risk.get("suggestion"):
                    console.print(f"   [italic]Fix: {risk['suggestion']}[/italic]")
                console.print()

        # Suggestions section
        suggestions = review_data.get("suggestions", [])
        console.rule("[bold yellow]Review Suggestions[/bold yellow]")
        if not suggestions:
            console.print("[green]No additional suggestions.[/green]")
        else:
            for i, sug in enumerate(suggestions, 1):
                console.print(f"[bold]{i}.[/bold] [{sug.get('type', 'general')}] "
                              f"{sug.get('file', '')}")
                console.print(f"   {sug.get('description', '')}")
                if sug.get("suggestion"):
                    console.print(f"   [italic]Suggestion: {sug['suggestion']}[/italic]")
                console.print()

    except Exception:
        # Fall back to raw markdown
        console.print(Markdown(review_text))

    console.rule("[bold blue]End of Review[/bold blue]")


def _severity_style(severity: str) -> str:
    """Map severity to Rich color style."""
    if "Critical" in severity or "🔴" in severity:
        return "bold red"
    elif "Medium" in severity or "🟡" in severity:
        return "bold yellow"
    elif "Low" in severity or "🟢" in severity:
        return "green"
    return "white"


def _format_plain(pr_info: dict, review_text: str) -> str:
    """Format review as plain text (no Rich markup)."""
    lines = []
    lines.append("=" * 60)
    lines.append("AI PR Review Report")
    lines.append("=" * 60)
    lines.append(f"Title: {pr_info.get('title', 'N/A')}")
    lines.append(f"Author: {pr_info.get('author', 'N/A')}")
    lines.append(f"Files: {pr_info.get('changed_files', 'N/A')} "
                 f"(+{pr_info.get('additions', 'N/A')} -{pr_info.get('deletions', 'N/A')})")
    lines.append("=" * 60)

    try:
        try:
            from .reviewer import parse_review_response
        except ImportError:
            from reviewer import parse_review_response
        review_data = parse_review_response(review_text)

        if review_data.get("parse_error"):
            lines.append("\n" + review_text)
            return "\n".join(lines)

        # Summary
        summary = review_data.get("summary", {})
        lines.append("\n--- Summary ---")
        lines.append(summary.get("overview", "N/A"))
        if summary.get("key_changes"):
            lines.append("\nKey Changes:")
            for c in summary["key_changes"]:
                lines.append(f"  - {c}")

        # Risks
        lines.append("\n--- Risk Identification ---")
        risks = review_data.get("risks", [])
        if not risks:
            lines.append("No significant risks identified.")
        else:
            for i, risk in enumerate(risks, 1):
                lines.append(f"\n{i}. [{risk.get('severity', 'N/A')}] {risk.get('category', '')} - {risk.get('file', '')}")
                lines.append(f"   {risk.get('description', '')}")
                if risk.get("suggestion"):
                    lines.append(f"   Fix: {risk['suggestion']}")

        # Suggestions
        lines.append("\n--- Review Suggestions ---")
        suggestions = review_data.get("suggestions", [])
        if not suggestions:
            lines.append("No additional suggestions.")
        else:
            for i, sug in enumerate(suggestions, 1):
                lines.append(f"\n{i}. [{sug.get('type', 'general')}] {sug.get('file', '')}")
                lines.append(f"   {sug.get('description', '')}")
                if sug.get("suggestion"):
                    lines.append(f"   Suggestion: {sug['suggestion']}")

    except Exception:
        lines.append("\n" + review_text)

    lines.append("\n" + "=" * 60)
    lines.append("End of Review")
    return "\n".join(lines)
