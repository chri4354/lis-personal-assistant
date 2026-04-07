"""Typer CLI for the LIS Personal Assistant."""

from __future__ import annotations

import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from assistant.llm import LLMClient
from assistant.repo import get_project_root, write_text
from assistant.runner import list_skills, load_input, run_skill
from assistant.schemas import InputMetadata
from assistant.settings import get_settings

app = typer.Typer(
    name="assistant",
    help="LIS Personal Assistant — run skills over text inputs.",
    no_args_is_help=True,
)
console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


def _get_llm_client() -> LLMClient:
    settings = get_settings()
    return LLMClient(
        api_key=settings.openai_api_key or None,
        default_model=settings.openai_model,
    )


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------


@app.command()
def run(
    skill_name: str = typer.Argument(help="Name of the skill to run (e.g. meeting_to_actions)"),
    input_file: Optional[Path] = typer.Option(
        None, "--input", "-i", help="Path to input markdown file"
    ),
    stdin: bool = typer.Option(False, "--stdin", help="Read input from stdin"),
    module: Optional[str] = typer.Option(None, "--module", "-m", help="Module name"),
    module_code: Optional[str] = typer.Option(None, "--module-code", help="Module code"),
    week: Optional[int] = typer.Option(None, "--week", "-w", help="Week number"),
    session: Optional[int] = typer.Option(None, "--session", "-s", help="Session number"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    """Run a skill on text input and produce structured output."""
    _setup_logging(verbose)
    root = get_project_root()

    # Resolve input text and metadata
    if input_file:
        path = input_file if input_file.is_absolute() else root / input_file
        if not path.exists():
            console.print(f"[red]Input file not found:[/red] {path}")
            raise typer.Exit(1)
        input_text, file_metadata = load_input(path)
        source = str(input_file)
        # CLI flags override file metadata
        metadata = InputMetadata(
            module=module or file_metadata.module,
            module_code=module_code or file_metadata.module_code,
            date=file_metadata.date,
            week=week if week is not None else file_metadata.week,
            session=session if session is not None else file_metadata.session,
        )
    elif stdin:
        console.print("[dim]Reading from stdin (paste text, then Ctrl-D)...[/dim]")
        input_text = sys.stdin.read().strip()
        if not input_text:
            console.print("[red]No input received from stdin.[/red]")
            raise typer.Exit(1)
        source = None
        metadata = InputMetadata(module=module, module_code=module_code, week=week, session=session)
    else:
        console.print("[red]Provide --input <file> or --stdin[/red]")
        raise typer.Exit(1)

    # Run the skill
    console.print(f"\n[bold]Running skill:[/bold] {skill_name}")
    if metadata.module:
        console.print(f"[dim]Module: {metadata.module}[/dim]")

    try:
        llm_client = _get_llm_client()
        result = run_skill(
            skill_name=skill_name,
            input_text=input_text,
            metadata=metadata,
            source_file=source,
            llm_client=llm_client,
            base_dir=root,
        )
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    except Exception as exc:
        console.print(f"[red]Error running skill:[/red] {exc}")
        raise typer.Exit(1) from exc

    # Display result
    if result.warnings:
        for w in result.warnings:
            console.print(f"[yellow]Warning:[/yellow] {w}")

    if result.output_file:
        console.print(f"\n[green]Output written to:[/green] {result.output_file}")

    if result.usage:
        console.print(
            f"[dim]Tokens: {result.usage.input_tokens} in / {result.usage.output_tokens} out "
            f"| Cost: ${result.usage.estimated_cost_usd:.4f} "
            f"| Model: {result.usage.model}[/dim]"
        )

    # Print a summary of the output
    console.print("\n[bold]Output preview:[/bold]")
    console.print_json(json.dumps(result.output_data, indent=2, default=str))


# ---------------------------------------------------------------------------
# skills command
# ---------------------------------------------------------------------------


@app.command(name="skills")
def skills_list() -> None:
    """List all available skills."""
    skills = list_skills()

    if not skills:
        console.print("[yellow]No skills found.[/yellow]")
        raise typer.Exit(0)

    table = Table(title="Available Skills")
    table.add_column("Name", style="bold cyan")
    table.add_column("Description")
    table.add_column("Input Type", style="dim")

    for skill in skills:
        table.add_row(skill.name, skill.description, skill.input_type)

    console.print(table)


# ---------------------------------------------------------------------------
# inbox command
# ---------------------------------------------------------------------------


@app.command()
def inbox(
    input_type: str = typer.Option(
        "notes", "--type", "-t", help="Input type: transcripts, emails, or notes"
    ),
    title: Optional[str] = typer.Option(None, "--title", help="Title for the note"),
    module: Optional[str] = typer.Option(None, "--module", "-m", help="Module name"),
) -> None:
    """Quick-capture text into the inbox (reads from stdin)."""
    root = get_project_root()
    valid_types = ("transcripts", "emails", "notes")

    if input_type not in valid_types:
        console.print(f"[red]Invalid type. Choose from: {', '.join(valid_types)}[/red]")
        raise typer.Exit(1)

    console.print(f"[dim]Paste your {input_type[:-1]} text, then press Ctrl-D...[/dim]")
    text = sys.stdin.read().strip()
    if not text:
        console.print("[red]No text received.[/red]")
        raise typer.Exit(1)

    today = date.today().isoformat()
    slug = title.lower().replace(" ", "-") if title else input_type[:-1]
    filename = f"{today}-{slug}.md"
    out_path = root / "inbox" / input_type / filename

    meta = {"title": title or f"Untitled {input_type[:-1]}", "type": input_type[:-1], "date": today}
    if module:
        meta["module"] = module

    import frontmatter as fm

    post = fm.Post(text, **meta)
    content = fm.dumps(post) + "\n"
    write_text(out_path, content)

    console.print(f"[green]Saved to:[/green] inbox/{input_type}/{filename}")


# ---------------------------------------------------------------------------
# usage command
# ---------------------------------------------------------------------------


@app.command()
def usage() -> None:
    """Show LLM usage summary from the log."""
    root = get_project_root()
    log_path = root / "outputs" / ".usage_log.jsonl"

    if not log_path.exists():
        console.print("[yellow]No usage data yet.[/yellow]")
        raise typer.Exit(0)

    total_cost = 0.0
    total_input = 0
    total_output = 0
    call_count = 0
    model_costs: dict[str, float] = {}

    for line in log_path.read_text().strip().splitlines():
        try:
            record = json.loads(line)
            total_cost += record.get("estimated_cost_usd", 0)
            total_input += record.get("input_tokens", 0)
            total_output += record.get("output_tokens", 0)
            call_count += 1
            model = record.get("model", "unknown")
            model_costs[model] = model_costs.get(model, 0) + record.get("estimated_cost_usd", 0)
        except json.JSONDecodeError:
            continue

    table = Table(title="LLM Usage Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total calls", str(call_count))
    table.add_row("Total input tokens", f"{total_input:,}")
    table.add_row("Total output tokens", f"{total_output:,}")
    table.add_row("Total estimated cost", f"${total_cost:.4f}")

    console.print(table)

    if model_costs:
        model_table = Table(title="Cost by Model")
        model_table.add_column("Model", style="cyan")
        model_table.add_column("Cost", justify="right")
        for model, cost in sorted(model_costs.items()):
            model_table.add_row(model, f"${cost:.4f}")
        console.print(model_table)


# ---------------------------------------------------------------------------
# serve command
# ---------------------------------------------------------------------------


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
) -> None:
    """Start the web UI server."""
    import uvicorn

    console.print(f"[bold]Starting web UI at[/bold] http://{host}:{port}")
    uvicorn.run(
        "assistant.api:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
